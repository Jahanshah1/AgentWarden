"""Deduplicate identical older history content blocks deterministically."""

from __future__ import annotations

import copy
import json
from typing import Any, Mapping


DUPLICATE_MARKER = "[duplicate of earlier content — see above]"


class ContextDedupOptimizer:
    """Replace repeated older history content with a deterministic marker."""

    name = "context_dedup"

    def apply(
        self,
        request: dict[str, Any],
        trace_context: Mapping[str, Any],
    ) -> dict[str, Any]:
        messages = request.get("messages")
        if not isinstance(messages, list) or len(messages) < 2:
            return request

        updated_messages = copy.deepcopy(messages)
        seen_contents: set[str] = set()
        changed = False
        current_index = len(updated_messages) - 1

        for index, message in enumerate(updated_messages):
            if index == current_index:
                continue
            if not isinstance(message, Mapping):
                continue
            if message.get("role") in {"system", "developer"}:
                continue
            if "tool_calls" in message or "function_call" in message:
                continue

            key = _content_key(message.get("content"))
            if key is None:
                continue
            if key in seen_contents:
                updated_messages[index] = {**message, "content": DUPLICATE_MARKER}
                changed = True
                continue
            seen_contents.add(key)

        if not changed:
            return request

        updated_request = copy.deepcopy(request)
        updated_request["messages"] = updated_messages
        return updated_request


def _content_key(content: Any) -> str | None:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return json.dumps(content, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return None
