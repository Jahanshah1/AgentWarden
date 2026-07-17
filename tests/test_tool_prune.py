"""Focused tests for the first AgentWarden optimizer pass."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import Response
import httpx

from proxy.config import OptimizerFlags, Settings
from proxy.server import create_app
from proxy.store import TraceRecord, TraceStore


AUTHORIZATION = "Bearer sk-test-agentwarden"


def test_tool_prune_skips_the_first_three_requests(tmp_path: Any) -> None:
    payload = _request_payload("Please inspect the repository.")
    upstream = _capture_upstream()

    async def run() -> None:
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
                optimizer_flags=OptimizerFlags(tool_prune=True),
            ),
            transport=httpx.ASGITransport(app=upstream),
        )
        store = TraceStore(tmp_path / "traces.sqlite3")
        _seed_trace(store, "warmup-session", tools_called=("read_file",))
        _seed_trace(store, "warmup-session", tools_called=("read_file",))

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as proxy_client:
            response = await proxy_client.post(
                "/v1/chat/completions",
                content=_raw_json(payload),
                headers=_headers("warmup-session"),
            )

        assert response.status_code == 200
        forwarded = json.loads(upstream.state.last_body)
        assert [tool["function"]["name"] for tool in forwarded["tools"]] == [
            "read_file",
            "write_file",
            "list_dir",
        ]

    asyncio.run(run())


def test_tool_prune_keeps_only_previously_called_tools_after_warmup(
    tmp_path: Any,
) -> None:
    payload = _request_payload("Please inspect the repository.")
    upstream = _capture_upstream()

    async def run() -> None:
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
                optimizer_flags=OptimizerFlags(tool_prune=True),
            ),
            transport=httpx.ASGITransport(app=upstream),
        )
        store = TraceStore(tmp_path / "traces.sqlite3")
        _seed_trace(store, "prune-session", tools_called=("read_file",))
        _seed_trace(store, "prune-session", tools_called=("read_file",))
        _seed_trace(store, "prune-session", tools_called=("read_file",))

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as proxy_client:
            response = await proxy_client.post(
                "/v1/chat/completions",
                content=_raw_json(payload),
                headers=_headers("prune-session"),
            )

        assert response.status_code == 200
        forwarded = json.loads(upstream.state.last_body)
        assert [tool["function"]["name"] for tool in forwarded["tools"]] == ["read_file"]

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as proxy_client:
            stats = (await proxy_client.get("/stats?session_id=prune-session")).json()
        assert stats["totals"]["tokens_saved"] > 0

    asyncio.run(run())


def test_tool_prune_keeps_tools_named_in_the_current_user_message(
    tmp_path: Any,
) -> None:
    payload = _request_payload("Use write_file after read_file to save the fix.")
    upstream = _capture_upstream()

    async def run() -> None:
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
                optimizer_flags=OptimizerFlags(tool_prune=True),
            ),
            transport=httpx.ASGITransport(app=upstream),
        )
        store = TraceStore(tmp_path / "traces.sqlite3")
        _seed_trace(store, "mentioned-session", tools_called=("read_file",))
        _seed_trace(store, "mentioned-session", tools_called=("read_file",))
        _seed_trace(store, "mentioned-session", tools_called=("read_file",))

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as proxy_client:
            response = await proxy_client.post(
                "/v1/chat/completions",
                content=_raw_json(payload),
                headers=_headers("mentioned-session"),
            )

        assert response.status_code == 200
        forwarded = json.loads(upstream.state.last_body)
        assert [tool["function"]["name"] for tool in forwarded["tools"]] == [
            "read_file",
            "write_file",
        ]

    asyncio.run(run())


def test_tool_prune_uses_the_active_user_request_after_tool_messages(
    tmp_path: Any,
) -> None:
    payload = _request_payload("Use write_file after read_file to save the fix.")
    payload["messages"].append(
        {"role": "tool", "tool_call_id": "call_1", "content": "Read result"}
    )
    upstream = _capture_upstream()

    async def run() -> None:
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
                optimizer_flags=OptimizerFlags(tool_prune=True),
            ),
            transport=httpx.ASGITransport(app=upstream),
        )
        store = TraceStore(tmp_path / "traces.sqlite3")
        for _ in range(3):
            _seed_trace(store, "active-user-session", tools_called=("read_file",))

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as proxy_client:
            response = await proxy_client.post(
                "/v1/chat/completions",
                content=_raw_json(payload),
                headers=_headers("active-user-session"),
            )

        assert response.status_code == 200
        forwarded = json.loads(upstream.state.last_body)
        assert [tool["function"]["name"] for tool in forwarded["tools"]] == [
            "read_file",
            "write_file",
        ]

    asyncio.run(run())


def _capture_upstream() -> FastAPI:
    app = FastAPI()
    app.state.last_body = b""

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Response:
        app.state.last_body = await request.body()
        return Response(
            content=b'{"id":"chatcmpl_tool_prune","object":"chat.completion","created":1700000002,"model":"gpt-5.6-terra","choices":[{"index":0,"message":{"role":"assistant","content":"OK"},"finish_reason":"stop"}],"usage":{"prompt_tokens":20,"completion_tokens":1,"total_tokens":21}}',
            media_type="application/json",
        )

    return app


def _seed_trace(
    store: TraceStore,
    session_id: str,
    *,
    tools_called: tuple[str, ...],
) -> None:
    store.insert(
        TraceRecord(
            session_id=session_id,
            model="gpt-5.6-terra",
            tokens_system=1,
            tokens_tools=10,
            tokens_history=1,
            tokens_current=1,
            tokens_total_input=13,
            tokens_output=1,
            tokens_saved=0,
            tools_offered=("read_file", "write_file", "list_dir"),
            tools_called=tools_called,
            optimizations_applied=(),
            latency_ms=10,
        )
    )


def _request_payload(user_message: str) -> dict[str, Any]:
    return {
        "model": "gpt-5.6-terra",
        "messages": [
            {"role": "system", "content": "You are a precise coding assistant."},
            {"role": "user", "content": user_message},
        ],
        "tools": [
            _tool("read_file", "Read a repository file."),
            _tool("write_file", "Write repository changes."),
            _tool("list_dir", "List repository directories."),
        ],
    }


def _tool(name: str, description: str) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    }


def _headers(session_id: str) -> dict[str, str]:
    return {
        "authorization": AUTHORIZATION,
        "content-type": "application/json",
        "x-agentwarden-session": session_id,
    }


def _raw_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
