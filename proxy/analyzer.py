"""Token accounting and response observation for Chat Completions requests."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

import tiktoken


SYSTEM_ROLES = frozenset({"system", "developer"})


@dataclass(frozen=True)
class RequestAnalysis:
    """Input-token split used in a persisted request trace."""

    model: str
    tokens_system: int
    tokens_tools: int
    tokens_history: int
    tokens_current: int
    tools_offered: tuple[str, ...]

    @property
    def tokens_total_input(self) -> int:
        return (
            self.tokens_system
            + self.tokens_tools
            + self.tokens_history
            + self.tokens_current
        )


@dataclass(frozen=True)
class OutputAnalysis:
    """Output-token and tool-call information recovered from a response."""

    tokens_output: int
    tools_called: tuple[str, ...]


def analyze_request(payload: Mapping[str, Any]) -> RequestAnalysis:
    """Split a Chat Completions payload into stable, countable segments."""

    model = payload.get("model")
    model_name = model if isinstance(model, str) and model else "unknown"
    messages = payload.get("messages")
    message_list = [
        message for message in messages if isinstance(message, Mapping)
    ] if isinstance(messages, list) else []

    system_messages: list[Mapping[str, Any]] = []
    conversation_messages: list[Mapping[str, Any]] = []
    for message in message_list:
        role = message.get("role")
        if role in SYSTEM_ROLES:
            system_messages.append(message)
        else:
            conversation_messages.append(message)

    current_messages = conversation_messages[-1:]
    history_messages = conversation_messages[:-1]
    tools = payload.get("tools")
    tools_list = tools if isinstance(tools, list) else []

    return RequestAnalysis(
        model=model_name,
        tokens_system=count_json(system_messages, model_name),
        tokens_tools=count_json(tools_list, model_name),
        tokens_history=count_json(history_messages, model_name),
        tokens_current=count_json(current_messages, model_name),
        tools_offered=tuple(extract_tool_names(tools_list)),
    )


def analyze_completion_response(
    payload: Mapping[str, Any], model: str
) -> OutputAnalysis:
    """Use provider usage when present, otherwise count generated output."""

    tool_names: list[str] = []
    generated: list[dict[str, Any]] = []
    choices = payload.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, Mapping):
                continue
            message = choice.get("message")
            if not isinstance(message, Mapping):
                continue
            generated_message: dict[str, Any] = {}
            content = message.get("content")
            if content is not None:
                generated_message["content"] = content
            tool_calls = message.get("tool_calls")
            if isinstance(tool_calls, list):
                generated_message["tool_calls"] = tool_calls
                tool_names.extend(extract_tool_call_names(tool_calls))
            function_call = message.get("function_call")
            if isinstance(function_call, Mapping):
                generated_message["function_call"] = function_call
                name = function_call.get("name")
                if isinstance(name, str):
                    tool_names.append(name)
            if generated_message:
                generated.append(generated_message)

    usage = payload.get("usage")
    completion_tokens = usage.get("completion_tokens") if isinstance(usage, Mapping) else None
    if isinstance(completion_tokens, int) and not isinstance(completion_tokens, bool):
        token_count = completion_tokens
    else:
        token_count = count_json(generated, model)
    return OutputAnalysis(
        tokens_output=token_count,
        tools_called=tuple(_unique_in_order(tool_names)),
    )


class StreamTraceObserver:
    """Observes SSE events incrementally without retaining or changing relay bytes."""

    def __init__(self, model: str) -> None:
        self._model = model
        self._line_buffer = bytearray()
        self._event_data_lines: list[bytes] = []
        self._content_by_choice: dict[int, list[str]] = {}
        self._tools_by_choice: dict[tuple[int, int], dict[str, Any]] = {}
        self._usage_completion_tokens: int | None = None

    def feed(self, chunk: bytes) -> None:
        """Accept an unmodified chunk before it is relayed to the client."""

        self._line_buffer.extend(chunk)
        while True:
            try:
                newline_index = self._line_buffer.index(10)
            except ValueError:
                return
            line = bytes(self._line_buffer[:newline_index]).rstrip(b"\r")
            del self._line_buffer[: newline_index + 1]
            self._consume_line(line)

    def finish(self) -> OutputAnalysis:
        """Flush a partially terminated stream and return its accumulated trace."""

        if self._line_buffer:
            self._consume_line(bytes(self._line_buffer).rstrip(b"\r"))
            self._line_buffer.clear()
        self._dispatch_event()

        tools_called = _unique_in_order(
            tool["name"]
            for tool in self._tools_by_choice.values()
            if isinstance(tool.get("name"), str)
        )
        if self._usage_completion_tokens is not None:
            token_count = self._usage_completion_tokens
        else:
            generated = [
                {
                    "content": "".join(parts),
                    "tool_calls": [
                        tool
                        for (tool_choice, _), tool in self._tools_by_choice.items()
                        if tool_choice == choice
                    ],
                }
                for choice, parts in sorted(self._content_by_choice.items())
            ]
            choices_with_only_tools = {
                choice for choice, _ in self._tools_by_choice
            } - set(self._content_by_choice)
            generated.extend(
                {
                    "tool_calls": [
                        tool
                        for (tool_choice, _), tool in self._tools_by_choice.items()
                        if tool_choice == choice
                    ]
                }
                for choice in sorted(choices_with_only_tools)
            )
            token_count = count_json(generated, self._model)
        return OutputAnalysis(
            tokens_output=token_count,
            tools_called=tuple(tools_called),
        )

    def _consume_line(self, line: bytes) -> None:
        if not line:
            self._dispatch_event()
            return
        if not line.startswith(b"data:"):
            return
        data = line[5:]
        if data.startswith(b" "):
            data = data[1:]
        self._event_data_lines.append(data)

    def _dispatch_event(self) -> None:
        if not self._event_data_lines:
            return
        payload = b"\n".join(self._event_data_lines)
        self._event_data_lines.clear()
        if payload == b"[DONE]":
            return
        try:
            event = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return
        if not isinstance(event, Mapping):
            return

        usage = event.get("usage")
        completion_tokens = usage.get("completion_tokens") if isinstance(usage, Mapping) else None
        if isinstance(completion_tokens, int) and not isinstance(completion_tokens, bool):
            self._usage_completion_tokens = completion_tokens

        choices = event.get("choices")
        if not isinstance(choices, list):
            return
        for choice in choices:
            if not isinstance(choice, Mapping):
                continue
            choice_index = choice.get("index", 0)
            if not isinstance(choice_index, int):
                choice_index = 0
            delta = choice.get("delta")
            if not isinstance(delta, Mapping):
                continue
            content = delta.get("content")
            if isinstance(content, str):
                self._content_by_choice.setdefault(choice_index, []).append(content)
            tool_calls = delta.get("tool_calls")
            if isinstance(tool_calls, list):
                self._record_tool_call_deltas(choice_index, tool_calls)
            function_call = delta.get("function_call")
            if isinstance(function_call, Mapping):
                self._record_function_delta(choice_index, 0, function_call, "function")

    def _record_tool_call_deltas(
        self, choice_index: int, tool_calls: list[Any]
    ) -> None:
        for fallback_index, tool_call in enumerate(tool_calls):
            if not isinstance(tool_call, Mapping):
                continue
            tool_index = tool_call.get("index", fallback_index)
            if not isinstance(tool_index, int):
                tool_index = fallback_index
            function = tool_call.get("function")
            if isinstance(function, Mapping):
                self._record_function_delta(
                    choice_index,
                    tool_index,
                    function,
                    tool_call.get("type", "function"),
                    tool_id=tool_call.get("id"),
                )

    def _record_function_delta(
        self,
        choice_index: int,
        tool_index: int,
        function: Mapping[str, Any],
        tool_type: Any,
        tool_id: Any = None,
    ) -> None:
        key = (choice_index, tool_index)
        tool = self._tools_by_choice.setdefault(
            key,
            {"type": tool_type if isinstance(tool_type, str) else "function", "name": "", "arguments": ""},
        )
        if isinstance(tool_id, str):
            tool["id"] = tool_id
        name = function.get("name")
        if isinstance(name, str):
            tool["name"] += name
        arguments = function.get("arguments")
        if isinstance(arguments, str):
            tool["arguments"] += arguments


def count_json(value: Any, model: str) -> int:
    """Count a JSON value with the model encoding or the o200k fallback."""

    return count_text(_canonical_json(value), model)


def count_text(text: str, model: str) -> int:
    """Count text without rejecting special-token-like user content."""

    encoding = _encoding_for_model(model)
    return len(encoding.encode(text, disallowed_special=()))


def trim_text_to_tokens(text: str, model: str, max_tokens: int) -> str:
    """Return a prefix of text that fits in max_tokens under the model encoding."""

    if max_tokens <= 0:
        return ""
    encoding = _encoding_for_model(model)
    tokens = encoding.encode(text, disallowed_special=())
    if len(tokens) <= max_tokens:
        return text
    return encoding.decode(tokens[:max_tokens])


def extract_tool_names(tools: list[Any]) -> list[str]:
    """Return offered function/custom-tool names without retaining schemas."""

    names: list[str] = []
    for tool in tools:
        if not isinstance(tool, Mapping):
            continue
        for descriptor_name in ("function", "custom"):
            descriptor = tool.get(descriptor_name)
            if not isinstance(descriptor, Mapping):
                continue
            name = descriptor.get("name")
            if isinstance(name, str):
                names.append(name)
    return _unique_in_order(names)


def extract_tool_call_names(tool_calls: list[Any]) -> list[str]:
    names: list[str] = []
    for tool_call in tool_calls:
        if not isinstance(tool_call, Mapping):
            continue
        function = tool_call.get("function")
        if not isinstance(function, Mapping):
            continue
        name = function.get("name")
        if isinstance(name, str):
            names.append(name)
    return _unique_in_order(names)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _unique_in_order(values: list[str] | Any) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _encoding_for_model(model: str) -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("o200k_base")
