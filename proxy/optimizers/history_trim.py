"""Trim stale tool history without touching protected conversation turns."""

from __future__ import annotations

import copy
from typing import Any, Mapping

from proxy.analyzer import trim_text_to_tokens


TRIMMED_MARKER = "…[trimmed by agentwarden]"


class HistoryTrimOptimizer:
    """Keep recent turns verbatim and clip only older tool-role content."""

    name = "history_trim"

    def __init__(self, keep_last_turns: int = 5, max_tool_tokens: int = 300) -> None:
        self._keep_last_turns = max(0, keep_last_turns)
        self._max_tool_tokens = max(1, max_tool_tokens)

    def apply(
        self,
        request: dict[str, Any],
        trace_context: Mapping[str, Any],
    ) -> dict[str, Any]:
        messages = request.get("messages")
        if not isinstance(messages, list) or not messages:
            return request

        model = _request_model(request)
        updated_messages = copy.deepcopy(messages)
        conversation_indexes = [
            index
            for index, message in enumerate(updated_messages)
            if isinstance(message, Mapping) and message.get("role") not in {"system", "developer"}
        ]
        protected_indexes = set(conversation_indexes[-self._keep_last_turns :])

        changed = False
        for index, message in enumerate(updated_messages):
            if index in protected_indexes:
                continue
            if not isinstance(message, Mapping):
                continue
            if message.get("role") != "tool":
                continue
            if _has_tool_call_metadata(message):
                continue

            trimmed = _trim_message_content(message, model, self._max_tool_tokens)
            if trimmed is None:
                continue
            updated_messages[index] = trimmed
            changed = True

        if not changed:
            return request

        updated_request = copy.deepcopy(request)
        updated_request["messages"] = updated_messages
        return updated_request


def _request_model(request: Mapping[str, Any]) -> str:
    model = request.get("model")
    return model if isinstance(model, str) and model else "unknown"


def _has_tool_call_metadata(message: Mapping[str, Any]) -> bool:
    return "tool_calls" in message or "function_call" in message


def _trim_message_content(
    message: Mapping[str, Any],
    model: str,
    max_tool_tokens: int,
) -> dict[str, Any] | None:
    content = message.get("content")
    if isinstance(content, str):
        trimmed_text = trim_text_to_tokens(content, model, max_tool_tokens)
        if trimmed_text == content:
            return None
        updated = dict(message)
        updated["content"] = f"{trimmed_text}{TRIMMED_MARKER}"
        return updated

    if not isinstance(content, list):
        return None

    remaining = max_tool_tokens
    updated_parts: list[Any] = []
    changed = False
    for item in content:
        if not isinstance(item, Mapping) or item.get("type") != "text":
            updated_parts.append(item)
            continue
        text = item.get("text")
        if not isinstance(text, str):
            updated_parts.append(item)
            continue
        if remaining <= 0:
            changed = True
            continue
        trimmed_text = trim_text_to_tokens(text, model, remaining)
        consumed = len(trimmed_text) if trimmed_text else 0
        remaining -= consumed
        if trimmed_text != text:
            changed = True
            updated_parts.append({**item, "text": f"{trimmed_text}{TRIMMED_MARKER}"})
            remaining = 0
        else:
            updated_parts.append(item)

    if not changed:
        return None
    updated = dict(message)
    updated["content"] = updated_parts
    return updated
