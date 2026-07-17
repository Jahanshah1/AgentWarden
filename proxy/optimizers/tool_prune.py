"""Prune unused tool schemas once a session has enough trace history."""

from __future__ import annotations

import copy
import re
from typing import Any, Mapping

from proxy.analyzer import extract_tool_names
from proxy.store import TraceStore


class ToolPruneOptimizer:
    """Keep only previously used or explicitly mentioned tools."""

    name = "tool_prune"

    def __init__(self, store: TraceStore | None, warmup_requests: int = 3) -> None:
        self._store = store
        self._warmup_requests = max(0, warmup_requests)

    def apply(
        self,
        request: dict[str, Any],
        trace_context: Mapping[str, Any],
    ) -> dict[str, Any]:
        tools = request.get("tools")
        if not isinstance(tools, list) or not tools:
            return request

        if self._store is None:
            return request

        session_id = trace_context.get("session_id")
        if not isinstance(session_id, str) or not session_id:
            return request

        prior_request_count = self._store.count_requests(session_id)
        if prior_request_count < self._warmup_requests:
            return request

        learned_tools = set(self._store.list_called_tools(session_id))
        mentioned_tools = _mentioned_tools(request, extract_tool_names(tools))
        allowed_names = learned_tools | mentioned_tools
        if not allowed_names:
            return request

        pruned_tools = [
            copy.deepcopy(tool)
            for tool in tools
            if _tool_name(tool) in allowed_names
        ]
        if len(pruned_tools) == len(tools) or not pruned_tools:
            return request

        updated_request = copy.deepcopy(request)
        updated_request["tools"] = pruned_tools
        return updated_request


def _mentioned_tools(request: Mapping[str, Any], tool_names: list[str]) -> set[str]:
    messages = request.get("messages")
    if not isinstance(messages, list) or not messages:
        return set()

    # Tool-result turns follow the active user request. Keep reading that
    # request throughout the loop rather than treating a tool result as the
    # current turn.
    current_message = next(
        (
            message
            for message in reversed(messages)
            if isinstance(message, Mapping) and message.get("role") == "user"
        ),
        None,
    )
    if current_message is None:
        return set()

    current_text = _content_text(current_message.get("content")).lower()
    if not current_text:
        return set()

    mentioned: set[str] = set()
    for tool_name in tool_names:
        pattern = rf"(?<![a-z0-9_]){re.escape(tool_name.lower())}(?![a-z0-9_])"
        if re.search(pattern, current_text):
            mentioned.add(tool_name)
    return mentioned


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if isinstance(item, str):
            parts.append(item)
            continue
        if not isinstance(item, Mapping):
            continue
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            parts.append(item["text"])
    return "\n".join(parts)


def _tool_name(tool: Any) -> str | None:
    if not isinstance(tool, Mapping):
        return None
    for descriptor_name in ("function", "custom"):
        descriptor = tool.get(descriptor_name)
        if not isinstance(descriptor, Mapping):
            continue
        name = descriptor.get("name")
        if isinstance(name, str):
            return name
    return None
