"""Interfaces and installed request optimizer passes."""

from __future__ import annotations

from typing import Any, Mapping, Protocol

from proxy.optimizers.cache_order import CacheOrderOptimizer
from proxy.optimizers.context_dedup import ContextDedupOptimizer
from proxy.optimizers.history_trim import HistoryTrimOptimizer
from proxy.optimizers.tool_prune import ToolPruneOptimizer


class Optimizer(Protocol):
    """A behavior-preserving request transformation used by the pipeline."""

    name: str

    def apply(
        self,
        request: dict[str, Any],
        trace_context: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Return an optimized request or raise for pipeline fallback."""


__all__ = [
    "CacheOrderOptimizer",
    "ContextDedupOptimizer",
    "HistoryTrimOptimizer",
    "Optimizer",
    "ToolPruneOptimizer",
]
