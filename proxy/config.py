"""Runtime configuration for AgentWarden.

All optimizer flags intentionally default to false for the Day 1 transparent
proxy milestone. Prices are USD per million tokens and can be extended without
touching trace storage or request forwarding.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os
from typing import Mapping


@dataclass(frozen=True)
class ModelPrice:
    """Standard-processing token prices in USD per million tokens."""

    input_per_million: float
    output_per_million: float


# Kept in configuration so pricing changes never affect persisted traces.
DEFAULT_MODEL_PRICES: Mapping[str, ModelPrice] = {
    "gpt-5.6-sol": ModelPrice(input_per_million=5.00, output_per_million=30.00),
    "gpt-5.6-terra": ModelPrice(input_per_million=2.50, output_per_million=15.00),
    "gpt-5.6-luna": ModelPrice(input_per_million=1.00, output_per_million=6.00),
    "gpt-5.5": ModelPrice(input_per_million=5.00, output_per_million=30.00),
    "gpt-5.4": ModelPrice(input_per_million=2.50, output_per_million=15.00),
    "gpt-5.4-mini": ModelPrice(input_per_million=0.75, output_per_million=4.50),
    "gpt-5.4-nano": ModelPrice(input_per_million=0.20, output_per_million=1.25),
    "gpt-5.3-codex": ModelPrice(input_per_million=1.75, output_per_million=14.00),
}


@dataclass(frozen=True)
class OptimizerFlags:
    """The future optimizer switches, deliberately disabled on Day 1."""

    tool_prune: bool = False
    history_trim: bool = False
    context_dedup: bool = False
    cache_order: bool = False

    @property
    def any_enabled(self) -> bool:
        return any(
            (
                self.tool_prune,
                self.history_trim,
                self.context_dedup,
                self.cache_order,
            )
        )


@dataclass(frozen=True)
class Settings:
    """Settings with safe local defaults for one developer workstation."""

    upstream_base_url: str = "https://api.openai.com"
    database_path: Path = Path("agentwarden.sqlite3")
    request_timeout_seconds: float = 120.0
    optimizer_flags: OptimizerFlags = field(default_factory=OptimizerFlags)
    model_prices: Mapping[str, ModelPrice] = field(
        default_factory=lambda: dict(DEFAULT_MODEL_PRICES)
    )

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            upstream_base_url=os.environ.get(
                "AGENTWARDEN_UPSTREAM_BASE_URL", "https://api.openai.com"
            ).rstrip("/"),
            database_path=Path(
                os.environ.get("AGENTWARDEN_DB_PATH", "agentwarden.sqlite3")
            ),
        )

    def price_for(self, model: str) -> ModelPrice | None:
        """Return configured standard pricing, including dated model aliases."""

        if model in self.model_prices:
            return self.model_prices[model]

        parts = model.rsplit("-", 3)
        if len(parts) == 4 and all(part.isdigit() for part in parts[-3:]):
            return self.model_prices.get("-".join(parts[:-3]))
        return None

