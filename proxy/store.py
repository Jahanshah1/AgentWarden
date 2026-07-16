"""SQLite persistence for AgentWarden request traces."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from proxy.config import ModelPrice


@dataclass(frozen=True)
class TraceRecord:
    session_id: str
    model: str
    tokens_system: int
    tokens_tools: int
    tokens_history: int
    tokens_current: int
    tokens_total_input: int
    tokens_output: int
    tokens_saved: int
    tools_offered: tuple[str, ...]
    tools_called: tuple[str, ...]
    optimizations_applied: tuple[str, ...]
    latency_ms: int
    ts: str = ""

    def with_timestamp(self) -> "TraceRecord":
        if self.ts:
            return self
        return TraceRecord(
            **{
                **asdict(self),
                "ts": datetime.now(timezone.utc).isoformat(),
            }
        )


class TraceStore:
    """A minimal, per-operation SQLite store safe for localhost use."""

    def __init__(self, database_path: Path | str) -> None:
        self._database_path = Path(database_path)
        self.initialize()

    def initialize(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS traces (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    tokens_system INTEGER NOT NULL,
                    tokens_tools INTEGER NOT NULL,
                    tokens_history INTEGER NOT NULL,
                    tokens_current INTEGER NOT NULL,
                    tokens_total_input INTEGER NOT NULL,
                    tokens_output INTEGER NOT NULL,
                    tokens_saved INTEGER NOT NULL,
                    tools_offered TEXT NOT NULL,
                    tools_called TEXT NOT NULL,
                    optimizations_applied TEXT NOT NULL,
                    latency_ms INTEGER NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_traces_session_ts ON traces(session_id, ts)"
            )

    def insert(self, record: TraceRecord) -> int:
        record = record.with_timestamp()
        with self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO traces (
                    ts, session_id, model, tokens_system, tokens_tools,
                    tokens_history, tokens_current, tokens_total_input,
                    tokens_output, tokens_saved, tools_offered, tools_called,
                    optimizations_applied, latency_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.ts,
                    record.session_id,
                    record.model,
                    record.tokens_system,
                    record.tokens_tools,
                    record.tokens_history,
                    record.tokens_current,
                    record.tokens_total_input,
                    record.tokens_output,
                    record.tokens_saved,
                    json.dumps(record.tools_offered),
                    json.dumps(record.tools_called),
                    json.dumps(record.optimizations_applied),
                    record.latency_ms,
                ),
            )
            return int(cursor.lastrowid)

    def list_traces(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM traces WHERE session_id = ? ORDER BY id DESC",
                (session_id,),
            ).fetchall()
        return [self._deserialize_row(row) for row in rows]

    def get_stats(
        self,
        session_id: str,
        model_prices: Mapping[str, ModelPrice],
    ) -> dict[str, Any]:
        with self._connect() as connection:
            totals_row = connection.execute(
                """
                SELECT
                    COUNT(*) AS request_count,
                    COALESCE(SUM(tokens_system), 0) AS tokens_system,
                    COALESCE(SUM(tokens_tools), 0) AS tokens_tools,
                    COALESCE(SUM(tokens_history), 0) AS tokens_history,
                    COALESCE(SUM(tokens_current), 0) AS tokens_current,
                    COALESCE(SUM(tokens_total_input), 0) AS tokens_total_input,
                    COALESCE(SUM(tokens_output), 0) AS tokens_output,
                    COALESCE(SUM(tokens_saved), 0) AS tokens_saved,
                    COALESCE(SUM(latency_ms), 0) AS latency_ms
                FROM traces
                WHERE session_id = ?
                """,
                (session_id,),
            ).fetchone()
            model_rows = connection.execute(
                """
                SELECT
                    model,
                    COUNT(*) AS request_count,
                    COALESCE(SUM(tokens_total_input), 0) AS tokens_total_input,
                    COALESCE(SUM(tokens_output), 0) AS tokens_output
                FROM traces
                WHERE session_id = ?
                GROUP BY model
                ORDER BY model
                """,
                (session_id,),
            ).fetchall()

        known_cost = 0.0
        unpriced_models: list[str] = []
        models: list[dict[str, Any]] = []
        for row in model_rows:
            model = str(row["model"])
            price = _price_for(model, model_prices)
            input_tokens = int(row["tokens_total_input"])
            output_tokens = int(row["tokens_output"])
            cost = None
            if price is None:
                unpriced_models.append(model)
            else:
                cost = (
                    input_tokens * price.input_per_million
                    + output_tokens * price.output_per_million
                ) / 1_000_000
                known_cost += cost
            models.append(
                {
                    "model": model,
                    "request_count": int(row["request_count"]),
                    "tokens_total_input": input_tokens,
                    "tokens_output": output_tokens,
                    "cost_estimate_usd": round(cost, 8) if cost is not None else None,
                }
            )

        request_count = int(totals_row["request_count"])
        return {
            "session_id": session_id,
            "request_count": request_count,
            "totals": {
                "tokens_total_input": int(totals_row["tokens_total_input"]),
                "tokens_output": int(totals_row["tokens_output"]),
                "tokens_total": int(totals_row["tokens_total_input"])
                + int(totals_row["tokens_output"]),
                "tokens_saved": int(totals_row["tokens_saved"]),
                "latency_ms": int(totals_row["latency_ms"]),
            },
            "per_segment": {
                "system": int(totals_row["tokens_system"]),
                "tools": int(totals_row["tokens_tools"]),
                "history": int(totals_row["tokens_history"]),
                "current": int(totals_row["tokens_current"]),
            },
            "cost_estimate_usd": round(known_cost, 8) if request_count else 0.0,
            "unpriced_models": unpriced_models,
            "models": models,
        }

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _deserialize_row(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        for key in ("tools_offered", "tools_called", "optimizations_applied"):
            result[key] = json.loads(result[key])
        return result


def _price_for(
    model: str, model_prices: Mapping[str, ModelPrice]
) -> ModelPrice | None:
    if model in model_prices:
        return model_prices[model]
    parts = model.rsplit("-", 3)
    if len(parts) == 4 and all(part.isdigit() for part in parts[-3:]):
        return model_prices.get("-".join(parts[:-3]))
    return None
