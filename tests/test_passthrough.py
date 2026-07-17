"""Contract tests for AgentWarden's transparent forwarding boundary."""

from __future__ import annotations

import asyncio
import gzip
import json
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse
import httpx
import pytest

from proxy.config import Settings
from proxy.server import create_app


AUTHORIZATION = "Bearer sk-test-agentwarden"
NON_STREAM_RESPONSE = {
    "id": "chatcmpl_fake_nonstream",
    "object": "chat.completion",
    "created": 1_700_000_000,
    "model": "gpt-5.6-terra",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "Proxy parity confirmed."},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 20, "completion_tokens": 4, "total_tokens": 24},
}
STREAM_PARTS = (
    b'data: {"id":"chatcmpl_fake_stream","object":"chat.completion.chunk","created":1700000001,"model":"gpt-5.6-terra","choices":[{"index":0,"delta":{"role":"assistant","content":"Hel"},"finish_reason":null}]}\n\n',
    b'data: {"id":"chatcmpl_fake_stream","object":"chat.completion.chunk","created":1700000001,"model":"gpt-5.6-terra","choices":[{"index":0,"delta":{"content":"lo"},"finish_reason":null}]}\n\n',
    b'data: {"id":"chatcmpl_fake_stream","object":"chat.completion.chunk","created":1700000001,"model":"gpt-5.6-terra","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"id":"call_1","type":"function","function":{"name":"read_file","arguments":"{\\"path\\":\\""}}]},"finish_reason":null}]}\n\n',
    b'data: {"id":"chatcmpl_fake_stream","object":"chat.completion.chunk","created":1700000001,"model":"gpt-5.6-terra","choices":[{"index":0,"delta":{"tool_calls":[{"index":0,"function":{"arguments":"README.md\\"}"}}]},"finish_reason":"tool_calls"}]}\n\n',
    b"data: [DONE]\n\n",
)


@pytest.fixture
def fake_openai() -> FastAPI:
    app = FastAPI()
    app.state.requests = []

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Response:
        body = await request.body()
        app.state.requests.append(
            {
                "body": body,
                "authorization": request.headers.get("authorization"),
            }
        )
        payload = json.loads(body)
        if payload["model"] == "error-model":
            return Response(
                content=b'{"error":{"message":"rate limited","type":"rate_limit_error"}}',
                status_code=429,
                media_type="application/json",
                headers={"x-request-id": "req_error"},
            )
        if payload["model"] == "compressed-model":
            body = {
                "id": "chatcmpl_fake_compressed",
                "object": "chat.completion",
                "model": "compressed-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_compressed",
                                    "type": "function",
                                    "function": {
                                        "name": "read_file",
                                        "arguments": '{"path":"README.md"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 7, "total_tokens": 27},
            }
            return Response(
                content=gzip.compress(json.dumps(body).encode("utf-8")),
                media_type="application/json",
                headers={"content-encoding": "gzip"},
            )
        if payload.get("stream") is True:

            async def events() -> Any:
                for part in STREAM_PARTS:
                    yield part

            return StreamingResponse(
                events(),
                media_type="text/event-stream",
                headers={"x-request-id": "req_stream"},
            )
        return Response(
            content=json.dumps(
                NON_STREAM_RESPONSE, separators=(",", ":")
            ).encode("utf-8"),
            media_type="application/json",
            headers={"x-request-id": "req_nonstream"},
        )

    return app


def test_nonstream_proxy_matches_direct_upstream(
    tmp_path: Any, fake_openai: FastAPI
) -> None:
    payload = _request_payload(stream=False)
    raw_request = _raw_json(payload)

    async def run() -> None:
        direct_transport = httpx.ASGITransport(app=fake_openai)
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
            ),
            transport=direct_transport,
        )
        async with httpx.AsyncClient(
            transport=direct_transport, base_url="http://fake-openai"
        ) as direct_client, httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as proxy_client:
            direct = await direct_client.post(
                "/v1/chat/completions",
                content=raw_request,
                headers=_headers("nonstream-session"),
            )
            proxied = await proxy_client.post(
                "/v1/chat/completions",
                content=raw_request,
                headers=_headers("nonstream-session"),
            )

            assert proxied.status_code == direct.status_code
            assert proxied.content == direct.content
            assert proxied.headers["content-type"] == direct.headers["content-type"]
            assert proxied.headers["x-request-id"] == direct.headers["x-request-id"]
            assert fake_openai.state.requests[0]["body"] == fake_openai.state.requests[1]["body"]
            assert fake_openai.state.requests[1]["authorization"] == AUTHORIZATION

            stats = (await proxy_client.get("/stats?session_id=nonstream-session")).json()
            assert stats["request_count"] == 1
            assert stats["totals"]["tokens_output"] == 4
            assert sum(stats["per_segment"].values()) == stats["totals"]["tokens_total_input"]
            assert stats["cost_estimate_usd"] is not None

            traces = (await proxy_client.get("/traces?session_id=nonstream-session")).json()
            assert len(traces["traces"]) == 1
            assert traces["traces"][0]["tools_offered"] == ["read_file"]

            sessions = (await proxy_client.get("/sessions")).json()
            assert sessions["sessions"] == [
                {
                    "session_id": "nonstream-session",
                    "last_seen": sessions["sessions"][0]["last_seen"],
                    "request_count": 1,
                    "tokens_saved": 0,
                }
            ]

    asyncio.run(run())


def test_stream_proxy_matches_direct_upstream(tmp_path: Any, fake_openai: FastAPI) -> None:
    payload = _request_payload(stream=True)
    raw_request = _raw_json(payload)

    async def run() -> None:
        direct_transport = httpx.ASGITransport(app=fake_openai)
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
            ),
            transport=direct_transport,
        )
        async with httpx.AsyncClient(
            transport=direct_transport, base_url="http://fake-openai"
        ) as direct_client, httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as proxy_client:
            async with direct_client.stream(
                "POST",
                "/v1/chat/completions",
                content=raw_request,
                headers=_headers("stream-session"),
            ) as direct_response:
                direct_body = b"".join(
                    [chunk async for chunk in direct_response.aiter_raw()]
                )
            async with proxy_client.stream(
                "POST",
                "/v1/chat/completions",
                content=raw_request,
                headers=_headers("stream-session"),
            ) as proxied_response:
                proxied_body = b"".join(
                    [chunk async for chunk in proxied_response.aiter_raw()]
                )

            assert proxied_response.status_code == direct_response.status_code
            assert proxied_body == direct_body
            assert proxied_response.headers["content-type"] == direct_response.headers["content-type"]
            assert proxied_response.headers["x-request-id"] == direct_response.headers["x-request-id"]
            assert fake_openai.state.requests[0]["body"] == fake_openai.state.requests[1]["body"]
            assert fake_openai.state.requests[1]["authorization"] == AUTHORIZATION

            stats = (await proxy_client.get("/stats?session_id=stream-session")).json()
            assert stats["request_count"] == 1
            assert stats["totals"]["tokens_output"] > 0
            traces = (await proxy_client.get("/traces?session_id=stream-session")).json()
            assert traces["traces"][0]["tools_called"] == ["read_file"]

    asyncio.run(run())


def test_upstream_errors_pass_through_unchanged(
    tmp_path: Any, fake_openai: FastAPI
) -> None:
    raw_request = _raw_json({"model": "error-model", "messages": []})

    async def run() -> None:
        direct_transport = httpx.ASGITransport(app=fake_openai)
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
            ),
            transport=direct_transport,
        )
        async with httpx.AsyncClient(
            transport=direct_transport, base_url="http://fake-openai"
        ) as direct_client, httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as proxy_client:
            direct = await direct_client.post(
                "/v1/chat/completions", content=raw_request, headers=_headers("errors")
            )
            proxied = await proxy_client.post(
                "/v1/chat/completions", content=raw_request, headers=_headers("errors")
            )

            assert proxied.status_code == direct.status_code == 429
            assert proxied.content == direct.content
            assert proxied.headers["content-type"] == direct.headers["content-type"]
            assert proxied.headers["x-request-id"] == direct.headers["x-request-id"]

    asyncio.run(run())


def test_runtime_config_can_be_updated_without_restarting_proxy(
    tmp_path: Any, fake_openai: FastAPI
) -> None:
    async def run() -> None:
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
            ),
            transport=httpx.ASGITransport(app=fake_openai),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as proxy_client:
            initial = (await proxy_client.get("/config")).json()
            updated = (
                await proxy_client.put(
                    "/config",
                    json={
                        "tool_prune": True,
                        "history_trim": True,
                        "session_budget_usd": 0.03,
                    },
                )
            ).json()

        assert initial["optimizer_flags"]["tool_prune"] is False
        assert updated == {
            "optimizer_flags": {
                "tool_prune": True,
                "history_trim": True,
                "context_dedup": False,
                "cache_order": False,
            },
            "session_budget_usd": 0.03,
            "runtime_only": True,
        }

    asyncio.run(run())


def test_bundled_dashboard_is_served_by_the_proxy(tmp_path: Any) -> None:
    async def run() -> None:
        proxy_app = create_app(settings=Settings(database_path=tmp_path / "traces.sqlite3"))
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as client:
            response = await client.get("/dashboard/")

        assert response.status_code == 200
        assert b"AgentWarden" in response.content

    asyncio.run(run())


def test_compressed_upstream_response_is_decoded_for_trace_accounting(
    tmp_path: Any, fake_openai: FastAPI
) -> None:
    payload = _request_payload(stream=False)
    payload["model"] = "compressed-model"

    async def run() -> None:
        proxy_app = create_app(
            settings=Settings(
                upstream_base_url="http://fake-openai",
                database_path=tmp_path / "traces.sqlite3",
            ),
            transport=httpx.ASGITransport(app=fake_openai),
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as proxy_client:
            response = await proxy_client.post(
                "/v1/chat/completions",
                content=_raw_json(payload),
                headers=_headers("compressed-session"),
            )
            assert response.status_code == 200
            stats = (await proxy_client.get("/stats?session_id=compressed-session")).json()
            traces = (await proxy_client.get("/traces?session_id=compressed-session")).json()

        assert stats["totals"]["tokens_output"] == 7
        assert traces["traces"][0]["tools_called"] == ["read_file"]

    asyncio.run(run())


@pytest.mark.live
def test_live_openai_proxy_request(tmp_path: Any) -> None:
    """Optional manual check against the real API; skipped without an API key."""

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY is required for live proxy testing")

    async def run() -> None:
        proxy_app = create_app(
            settings=Settings(database_path=tmp_path / "live-traces.sqlite3")
        )
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=proxy_app), base_url="http://agentwarden"
        ) as client:
            response = await client.post(
                "/v1/chat/completions",
                content=_raw_json(
                    {
                        "model": os.environ.get(
                            "AGENTWARDEN_LIVE_MODEL", "gpt-5.6-terra"
                        ),
                        "messages": [{"role": "user", "content": "Reply with OK."}],
                    }
                ),
                headers={"authorization": f"Bearer {api_key}"},
            )
            assert response.status_code == 200, response.text

    asyncio.run(run())


def _request_payload(stream: bool) -> dict[str, Any]:
    return {
        "model": "gpt-5.6-terra",
        "messages": [
            {"role": "system", "content": "You are a precise coding assistant."},
            {"role": "user", "content": "What does the repository contain?"},
            {"role": "assistant", "content": "I will inspect it."},
            {"role": "user", "content": "Please inspect it now."},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a repository file.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            }
        ],
        "stream": stream,
    }


def _headers(session_id: str) -> dict[str, str]:
    return {
        "authorization": AUTHORIZATION,
        "content-type": "application/json",
        "x-agentwarden-session": session_id,
    }


def _raw_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
