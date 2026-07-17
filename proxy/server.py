"""OpenAI-compatible transparent proxy with request tracing."""

from __future__ import annotations

from dataclasses import asdict, replace
import json
import logging
from pathlib import Path
from time import perf_counter
from typing import Any, AsyncIterator, Mapping

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
import httpx

from proxy.analyzer import (
    OutputAnalysis,
    RequestAnalysis,
    StreamTraceObserver,
    analyze_completion_response,
    analyze_request,
)
from proxy.config import Settings
from proxy.optimizers import (
    CacheOrderOptimizer,
    ContextDedupOptimizer,
    HistoryTrimOptimizer,
    ToolPruneOptimizer,
)
from proxy.pipeline import OptimizationPipeline
from proxy.store import TraceRecord, TraceStore


logger = logging.getLogger(__name__)

HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
)
REQUEST_HEADERS_TO_DROP = HOP_BY_HOP_HEADERS | {"host", "content-length"}
RESPONSE_HEADERS_TO_DROP = HOP_BY_HOP_HEADERS | {"content-length"}


def create_app(
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Build an app, optionally with an in-memory upstream transport for tests."""

    app = FastAPI(title="AgentWarden", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_methods=["GET", "PUT"],
        allow_headers=["content-type"],
    )
    app.state.settings = settings or Settings.from_environment()
    app.state.upstream_transport = transport
    try:
        app.state.trace_store = TraceStore(app.state.settings.database_path)
    except Exception:
        # Observability must not prevent transparent forwarding.
        logger.exception("AgentWarden tracing store is unavailable; forwarding continues")
        app.state.trace_store = None
    app.state.pipeline = _build_pipeline(app.state.settings, app.state.trace_store)

    @app.post("/v1/chat/completions")
    async def chat_completions(request: Request) -> Response:
        started_at = perf_counter()
        raw_request_body = await request.body()
        request_payload = _parse_json_object(raw_request_body)
        session_id = request.headers.get("x-agentwarden-session", "default")
        original_analysis = _safe_analyze_request(request_payload)
        forwarded_payload = request_payload
        forwarded_body = raw_request_body
        optimizations_applied: tuple[str, ...] = ()

        if app.state.settings.optimizer_flags.any_enabled and request_payload:
            pipeline_result = app.state.pipeline.apply(
                request_payload,
                {
                    "request_analysis": asdict(original_analysis),
                    "session_id": session_id,
                },
            )
            forwarded_payload = pipeline_result.request
            optimizations_applied = pipeline_result.applied
            if optimizations_applied:
                forwarded_body = json.dumps(
                    forwarded_payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")

        forwarded_analysis = _safe_analyze_request(forwarded_payload)
        tokens_saved = max(
            0,
            original_analysis.tokens_total_input
            - forwarded_analysis.tokens_total_input,
        )
        upstream_client = httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(
                app.state.settings.request_timeout_seconds,
                read=None,
            ),
            transport=app.state.upstream_transport,
        )

        try:
            upstream_response = await upstream_client.send(
                upstream_client.build_request(
                    "POST",
                    _upstream_chat_completions_url(
                        app.state.settings.upstream_base_url
                    ),
                    content=forwarded_body,
                    headers=_forward_request_headers(request),
                ),
                stream=True,
            )
        except Exception:
            await upstream_client.aclose()
            _persist_trace(
                app,
                session_id,
                forwarded_analysis,
                OutputAnalysis(tokens_output=0, tools_called=()),
                tokens_saved,
                optimizations_applied,
                started_at,
            )
            raise

        is_streaming_request = request_payload.get("stream") is True
        response_headers = _forward_response_headers(upstream_response)
        budget_warning = _budget_warning_header(
            app,
            session_id,
            forwarded_analysis,
        )
        if budget_warning is not None:
            response_headers["X-AgentWarden-Budget-Warning"] = budget_warning
        if is_streaming_request and upstream_response.is_success:
            observer = StreamTraceObserver(forwarded_analysis.model)

            async def relay() -> AsyncIterator[bytes]:
                try:
                    async for chunk in upstream_response.aiter_raw():
                        observer.feed(chunk)
                        yield chunk
                finally:
                    try:
                        output = observer.finish()
                    except Exception:
                        logger.exception(
                            "Unable to finish stream tracing; proxied stream was unaffected"
                        )
                        output = OutputAnalysis(tokens_output=0, tools_called=())
                    try:
                        await upstream_response.aclose()
                    finally:
                        await upstream_client.aclose()
                    _persist_trace(
                        app,
                        session_id,
                        forwarded_analysis,
                        output,
                        tokens_saved,
                        optimizations_applied,
                        started_at,
                    )

            return StreamingResponse(
                relay(),
                status_code=upstream_response.status_code,
                headers=response_headers,
            )

        try:
            raw_response_body = await _read_raw_response(upstream_response)
        finally:
            await upstream_response.aclose()
            await upstream_client.aclose()

        output = (
            _safe_analyze_response(
                raw_response_body,
                forwarded_analysis.model,
                upstream_response.headers,
            )
            if upstream_response.is_success
            else OutputAnalysis(tokens_output=0, tools_called=())
        )
        _persist_trace(
            app,
            session_id,
            forwarded_analysis,
            output,
            tokens_saved,
            optimizations_applied,
            started_at,
        )
        return Response(
            content=raw_response_body,
            status_code=upstream_response.status_code,
            headers=response_headers,
        )

    @app.get("/traces")
    async def traces(session_id: str = Query(default="default")) -> dict[str, Any]:
        store = _get_store(app)
        return {"session_id": session_id, "traces": store.list_traces(session_id)}

    @app.get("/sessions")
    async def sessions(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
        store = _get_store(app)
        return {"sessions": store.list_sessions(limit)}

    @app.get("/config")
    async def config() -> dict[str, Any]:
        return _runtime_config_payload(app.state.settings)

    @app.put("/config")
    async def update_config(request: Request) -> dict[str, Any]:
        """Update local optimizer switches for the lifetime of this server process."""

        try:
            payload = await request.json()
        except json.JSONDecodeError as error:
            raise HTTPException(status_code=400, detail="Configuration must be JSON") from error
        if not isinstance(payload, Mapping):
            raise HTTPException(status_code=400, detail="Configuration must be an object")

        current = app.state.settings
        flag_values = {
            name: payload[name]
            for name in ("tool_prune", "history_trim", "context_dedup", "cache_order")
            if name in payload
        }
        if any(not isinstance(value, bool) for value in flag_values.values()):
            raise HTTPException(status_code=400, detail="Optimizer flags must be booleans")

        budget = payload.get("session_budget_usd", current.session_budget_usd)
        if budget is not None and (
            not isinstance(budget, (int, float))
            or isinstance(budget, bool)
            or budget < 0
        ):
            raise HTTPException(
                status_code=400,
                detail="session_budget_usd must be a non-negative number or null",
            )

        updated = replace(
            current,
            optimizer_flags=replace(current.optimizer_flags, **flag_values),
            session_budget_usd=float(budget) if budget is not None else None,
        )
        app.state.settings = updated
        app.state.pipeline = _build_pipeline(updated, app.state.trace_store)
        return _runtime_config_payload(updated)

    @app.get("/stats")
    async def stats(session_id: str = Query(default="default")) -> dict[str, Any]:
        store = _get_store(app)
        return store.get_stats(session_id, app.state.settings.model_prices)

    dashboard_directory = Path(__file__).with_name("dashboard_static")
    if dashboard_directory.is_dir():
        app.mount(
            "/dashboard",
            StaticFiles(directory=dashboard_directory, html=True),
            name="dashboard",
        )

    return app


def _build_pipeline(
    settings: Settings, trace_store: TraceStore | None
) -> OptimizationPipeline:
    return OptimizationPipeline(
        settings.optimizer_flags,
        {
            "cache_order": CacheOrderOptimizer(),
            "context_dedup": ContextDedupOptimizer(),
            "history_trim": HistoryTrimOptimizer(
                keep_last_turns=settings.history_trim_keep_last_turns,
                max_tool_tokens=settings.history_trim_max_tool_tokens,
            ),
            "tool_prune": ToolPruneOptimizer(
                trace_store,
                warmup_requests=settings.tool_prune_warmup_requests,
            ),
        },
    )


def _runtime_config_payload(settings: Settings) -> dict[str, Any]:
    return {
        "optimizer_flags": asdict(settings.optimizer_flags),
        "session_budget_usd": settings.session_budget_usd,
        "runtime_only": True,
    }


app = create_app()


def _upstream_chat_completions_url(upstream_base_url: str) -> str:
    return f"{upstream_base_url.rstrip('/')}/v1/chat/completions"


def _forward_request_headers(request: Request) -> list[tuple[str, str]]:
    """Forward all client headers except hop-by-hop and recalculated headers."""

    return [
        (name.decode("latin-1"), value.decode("latin-1"))
        for name, value in request.headers.raw
        if name.decode("latin-1").lower() not in REQUEST_HEADERS_TO_DROP
    ]


def _forward_response_headers(response: httpx.Response) -> dict[str, str]:
    """Keep OpenAI response metadata while letting Starlette frame the body."""

    return {
        name: value
        for name, value in response.headers.multi_items()
        if name.lower() not in RESPONSE_HEADERS_TO_DROP
    }


async def _read_raw_response(response: httpx.Response) -> bytes:
    chunks: list[bytes] = []
    async for chunk in response.aiter_raw():
        chunks.append(chunk)
    return b"".join(chunks)


def _parse_json_object(body: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _safe_analyze_request(payload: Mapping[str, Any]) -> RequestAnalysis:
    try:
        return analyze_request(payload)
    except Exception:
        logger.exception("Unable to analyze request; storing an empty trace split")
        model = payload.get("model")
        return RequestAnalysis(
            model=model if isinstance(model, str) else "unknown",
            tokens_system=0,
            tokens_tools=0,
            tokens_history=0,
            tokens_current=0,
            tools_offered=(),
        )


def _safe_analyze_response(
    body: bytes,
    model: str,
    headers: Mapping[str, str] | None = None,
) -> OutputAnalysis:
    """Analyze a decoded copy while preserving the upstream body for the client."""

    decoded_body = body
    if headers is not None and headers.get("content-encoding"):
        try:
            decoded_response = httpx.Response(
                status_code=200,
                headers=headers,
                content=body,
            )
            decoded_body = decoded_response.read()
        except Exception:
            logger.exception("Unable to decode upstream response for tracing")

    payload = _parse_json_object(decoded_body)
    if not payload:
        return OutputAnalysis(tokens_output=0, tools_called=())
    try:
        return analyze_completion_response(payload, model)
    except Exception:
        logger.exception("Unable to analyze response; storing zero output tokens")
        return OutputAnalysis(tokens_output=0, tools_called=())


def _persist_trace(
    app: FastAPI,
    session_id: str,
    request_analysis: RequestAnalysis,
    output_analysis: OutputAnalysis,
    tokens_saved: int,
    optimizations_applied: tuple[str, ...],
    started_at: float,
) -> None:
    store = app.state.trace_store
    if store is None:
        return
    try:
        store.insert(
            TraceRecord(
                session_id=session_id,
                model=request_analysis.model,
                tokens_system=request_analysis.tokens_system,
                tokens_tools=request_analysis.tokens_tools,
                tokens_history=request_analysis.tokens_history,
                tokens_current=request_analysis.tokens_current,
                tokens_total_input=request_analysis.tokens_total_input,
                tokens_output=output_analysis.tokens_output,
                tokens_saved=tokens_saved,
                tools_offered=request_analysis.tools_offered,
                tools_called=output_analysis.tools_called,
                optimizations_applied=optimizations_applied,
                latency_ms=round((perf_counter() - started_at) * 1000),
            )
        )
    except Exception:
        logger.exception("Failed to persist trace; proxied response was unaffected")


def _budget_warning_header(
    app: FastAPI,
    session_id: str,
    request_analysis: RequestAnalysis,
) -> str | None:
    budget = app.state.settings.session_budget_usd
    store = app.state.trace_store
    if budget is None or store is None:
        return None

    prior_estimate = store.get_stats(session_id, app.state.settings.model_prices)[
        "cost_estimate_usd"
    ]
    projected = prior_estimate + _estimated_input_cost(
        request_analysis.model,
        request_analysis.tokens_total_input,
        app.state.settings,
    )
    if projected < budget:
        return None

    logger.warning(
        "Session %s crossed the AgentWarden budget threshold: projected cost %.6f >= %.6f",
        session_id,
        projected,
        budget,
    )
    return f"projected session cost {projected:.6f} exceeds budget {budget:.6f}"


def _get_store(app: FastAPI) -> TraceStore:
    store = app.state.trace_store
    if store is None:
        raise HTTPException(status_code=503, detail="Trace storage is unavailable")
    return store


def _estimated_input_cost(model: str, input_tokens: int, settings: Settings) -> float:
    price = settings.price_for(model)
    if price is None:
        return 0.0
    return (input_tokens * price.input_per_million) / 1_000_000
