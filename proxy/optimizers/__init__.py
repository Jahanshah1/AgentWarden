"""Interfaces for future request optimizer passes.

No optimizer is implemented or enabled in the Day 1 milestone.
"""

from __future__ import annotations

from typing import Any, Mapping, Protocol


class Optimizer(Protocol):
    """A behavior-preserving request transformation used by the pipeline."""

    name: str

    def apply(
        self,
        request: dict[str, Any],
        trace_context: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Return an optimized request or raise for pipeline fallback."""

