"""Stabilize static-prefix serialization for better upstream prompt caching."""

from __future__ import annotations

import copy
from typing import Any, Mapping


class CacheOrderOptimizer:
    """Recursively sort mapping keys inside static prefix structures."""

    name = "cache_order"

    def apply(
        self,
        request: dict[str, Any],
        trace_context: Mapping[str, Any],
    ) -> dict[str, Any]:
        updated_request = copy.deepcopy(request)

        messages = updated_request.get("messages")
        if isinstance(messages, list):
            for index, message in enumerate(messages):
                if not isinstance(message, Mapping):
                    continue
                if message.get("role") not in {"system", "developer"}:
                    continue
                messages[index] = _normalize_value(message)

        tools = updated_request.get("tools")
        if isinstance(tools, list):
            updated_request["tools"] = [_normalize_value(tool) for tool in tools]

        return updated_request


def _normalize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _normalize_value(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value
