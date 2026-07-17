"""Focused tests for history trimming, deduplication, cache ordering, and budget guard."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import Response
import httpx

from proxy.config import ModelPrice, OptimizerFlags, Settings
from proxy.server import create_app


AUTHORIZATION = "Bearer sk-test-agentwarden"


def test_history_trim_clips_only_older_tool_messages(tmp_path: Any) -> None:
    payload = {
        "model": "gpt-5.6-terra",
        "messages": [
            {"role": "system", "content": "Keep instructions."},
            {"role": "tool", "content": "A" * 4000, "tool_call_id": "call_old"},
            {"role": "assistant", "content": "Observed output."},
            {"role": "user", "content": "continue 1"},
            {"role": "assistant", "content": "continue 2"},
            {"role": "user", "content": "continue 3"},
            {"role": "assistant", "content": "continue 4"},
            {"role": "user", "content": "continue 5"},
        ],
    }
    upstream = _capture_upstream()

    async def run() -> None:
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
                optimizer_flags=OptimizerFlags(history_trim=True),
                history_trim_keep_last_turns=5,
                history_trim_max_tool_tokens=10,
            ),
            transport=httpx.ASGITransport(app=upstream),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as client:
            response = await client.post(
                "/v1/chat/completions",
                content=_raw_json(payload),
                headers=_headers("trim-session"),
            )
        assert response.status_code == 200

        forwarded = json.loads(upstream.state.last_body)
        assert forwarded["messages"][0]["content"] == "Keep instructions."
        assert forwarded["messages"][1]["content"].endswith("…[trimmed by agentwarden]")
        assert len(forwarded["messages"][1]["content"]) < len(payload["messages"][1]["content"])
        assert forwarded["messages"][-1]["content"] == "continue 5"

    asyncio.run(run())


def test_context_dedup_replaces_only_later_history_duplicates(tmp_path: Any) -> None:
    payload = {
        "model": "gpt-5.6-terra",
        "messages": [
            {"role": "system", "content": "Keep instructions."},
            {"role": "user", "content": "same block"},
            {"role": "assistant", "content": "same block"},
            {"role": "user", "content": "same block"},
            {"role": "assistant", "content": "current stays same block"},
        ],
    }
    upstream = _capture_upstream()

    async def run() -> None:
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
                optimizer_flags=OptimizerFlags(context_dedup=True),
            ),
            transport=httpx.ASGITransport(app=upstream),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as client:
            response = await client.post(
                "/v1/chat/completions",
                content=_raw_json(payload),
                headers=_headers("dedup-session"),
            )
        assert response.status_code == 200

        forwarded = json.loads(upstream.state.last_body)
        assert forwarded["messages"][1]["content"] == "same block"
        assert forwarded["messages"][2]["content"] == "[duplicate of earlier content — see above]"
        assert forwarded["messages"][3]["content"] == "[duplicate of earlier content — see above]"
        assert forwarded["messages"][4]["content"] == "current stays same block"

    asyncio.run(run())


def test_cache_order_normalizes_static_prefix_key_order(tmp_path: Any) -> None:
    payload = {
        "model": "gpt-5.6-terra",
        "messages": [
            {"content": "Keep instructions.", "role": "system"},
            {"role": "user", "content": "hello"},
        ],
        "tools": [
            {
                "function": {
                    "parameters": {
                        "required": ["path"],
                        "properties": {"path": {"type": "string"}},
                        "type": "object",
                    },
                    "description": "Read a repository file.",
                    "name": "read_file",
                },
                "type": "function",
            }
        ],
    }
    upstream = _capture_upstream()

    async def run() -> None:
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
                optimizer_flags=OptimizerFlags(cache_order=True),
            ),
            transport=httpx.ASGITransport(app=upstream),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as client:
            response = await client.post(
                "/v1/chat/completions",
                content=_raw_json(payload),
                headers=_headers("cache-order-session"),
            )
        assert response.status_code == 200

        forwarded_text = upstream.state.last_body.decode("utf-8")
        assert '"messages":[{"content":"Keep instructions.","role":"system"}' in forwarded_text
        assert (
            '"function":{"description":"Read a repository file.","name":"read_file","parameters":'
            in forwarded_text
        )

    asyncio.run(run())


def test_budget_guard_adds_warning_header_once_projected_threshold_is_crossed(
    tmp_path: Any,
) -> None:
    payload = {
        "model": "gpt-5.6-terra",
        "messages": [{"role": "user", "content": "hello"}],
    }
    upstream = _capture_upstream()

    async def run() -> None:
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
                session_budget_usd=0.000001,
                model_prices={"gpt-5.6-terra": ModelPrice(2.5, 15.0)},
            ),
            transport=httpx.ASGITransport(app=upstream),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as client:
            response = await client.post(
                "/v1/chat/completions",
                content=_raw_json(payload),
                headers=_headers("budget-session"),
            )
        assert response.status_code == 200
        assert "X-AgentWarden-Budget-Warning" in response.headers

    asyncio.run(run())


def _capture_upstream() -> FastAPI:
    app = FastAPI()
    app.state.last_body = b""

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Response:
        app.state.last_body = await request.body()
        return Response(
            content=b'{"id":"chatcmpl_efficiency","object":"chat.completion","created":1700000003,"model":"gpt-5.6-terra","choices":[{"index":0,"message":{"role":"assistant","content":"OK"},"finish_reason":"stop"}],"usage":{"prompt_tokens":20,"completion_tokens":1,"total_tokens":21}}',
            media_type="application/json",
        )

    return app


def _headers(session_id: str) -> dict[str, str]:
    return {
        "authorization": AUTHORIZATION,
        "content-type": "application/json",
        "x-agentwarden-session": session_id,
    }


def _raw_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
