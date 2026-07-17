"""Trace metadata should distinguish enabled passes from actual mutations."""

from __future__ import annotations

from typing import Any, Mapping

from proxy.config import OptimizerFlags
from proxy.pipeline import OptimizationPipeline


class _NoopOptimizer:
    def apply(
        self, request: dict[str, Any], trace_context: Mapping[str, Any]
    ) -> dict[str, Any]:
        return request


class _ChangingOptimizer:
    def apply(
        self, request: dict[str, Any], trace_context: Mapping[str, Any]
    ) -> dict[str, Any]:
        return {**request, "optimized": True}


def test_pipeline_records_only_passes_that_change_the_request() -> None:
    result = OptimizationPipeline(
        OptimizerFlags(tool_prune=True, history_trim=True),
        {"tool_prune": _NoopOptimizer(), "history_trim": _ChangingOptimizer()},
    ).apply({"model": "test"}, {})

    assert result.request == {"model": "test", "optimized": True}
    assert result.applied == ("history_trim",)
