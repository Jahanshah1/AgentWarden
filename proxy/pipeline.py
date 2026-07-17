"""Scaffolding for ordered optimizer passes.

The Day 1 proxy calls this only when a future flag is explicitly enabled. With
the default configuration it is a no-op and server.py forwards raw request
bytes, preserving byte-identical pass-through behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from typing import Any, Mapping

from proxy.config import OptimizerFlags
from proxy.optimizers import Optimizer


logger = logging.getLogger(__name__)

PASS_ORDER = ("tool_prune", "history_trim", "context_dedup", "cache_order")


@dataclass(frozen=True)
class PipelineResult:
    request: dict[str, Any]
    applied: tuple[str, ...]


class OptimizationPipeline:
    """Applies future passes in the constitution-defined order."""

    def __init__(
        self,
        flags: OptimizerFlags,
        optimizers: Mapping[str, Optimizer] | None = None,
    ) -> None:
        self._flags = flags
        self._optimizers = dict(optimizers or {})

    def apply(
        self,
        request: dict[str, Any],
        trace_context: Mapping[str, Any],
    ) -> PipelineResult:
        current = request
        applied: list[str] = []
        for name in PASS_ORDER:
            if not getattr(self._flags, name):
                continue

            optimizer = self._optimizers.get(name)
            if optimizer is None:
                logger.warning("Optimizer %s is enabled but not installed; skipping", name)
                continue

            original = current
            try:
                candidate = optimizer.apply(current, trace_context)
                if _request_changed(original, candidate):
                    applied.append(name)
                current = candidate
            except Exception:
                logger.exception("Optimizer %s failed; forwarding its original request", name)
                current = original
        return PipelineResult(request=current, applied=tuple(applied))


def _request_changed(original: dict[str, Any], candidate: dict[str, Any]) -> bool:
    """Include key-order changes, which matter for provider prompt caching."""

    if original != candidate:
        return True
    return json.dumps(
        original, ensure_ascii=False, separators=(",", ":")
    ) != json.dumps(candidate, ensure_ascii=False, separators=(",", ":"))
