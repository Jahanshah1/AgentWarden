"""CLI entry points for serving, stats, demo runs, and replay verification."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import httpx
import uvicorn

from demo_agent.agent import DEFAULT_MODEL, DEFAULT_TASK, run_demo_task
from lead_agent.agent import DEFAULT_MODEL as LEAD_DEFAULT_MODEL
from lead_agent.agent import run_lead_task
from proxy.config import Settings
from proxy.store import TraceStore
from replay.verify import verify_demo_task


def main() -> int:
    parser = argparse.ArgumentParser(prog="agentwarden")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the AgentWarden proxy server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)

    dashboard = subparsers.add_parser(
        "dashboard", help="Run the local proxy and show its bundled dashboard URL"
    )
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8080)

    stats = subparsers.add_parser("stats", help="Print stored session stats")
    stats.add_argument("--session-id", default="default")
    stats.add_argument("--db", default=os.environ.get("AGENTWARDEN_DB_PATH", "agentwarden.sqlite3"))

    doctor = subparsers.add_parser(
        "doctor", help="Check that a running AgentWarden proxy is reachable"
    )
    doctor.add_argument(
        "--base-url",
        default=os.environ.get("AGENTWARDEN_BASE_URL", "http://127.0.0.1:8080/v1"),
        help="The OpenAI SDK base URL configured for the agent",
    )

    demo = subparsers.add_parser("demo", help="Run the demo coding agent through a proxy")
    demo.add_argument("--base-url", default=os.environ.get("AGENTWARDEN_BASE_URL", "http://127.0.0.1:8080/v1"))
    demo.add_argument("--model", default=os.environ.get("AGENTWARDEN_MODEL", DEFAULT_MODEL))
    demo.add_argument("--task", default=os.environ.get("AGENTWARDEN_TASK"))
    demo.add_argument("--session-id", default=None)

    verify = subparsers.add_parser("verify", help="Replay the demo task with optimizations off and on")
    verify.add_argument("--model", default=os.environ.get("AGENTWARDEN_MODEL", DEFAULT_MODEL))
    verify.add_argument("--task", default=os.environ.get("AGENTWARDEN_TASK"))
    verify.add_argument("--no-judge", action="store_true")

    lead_demo = subparsers.add_parser(
        "lead-demo", help="Run the deterministic lead-enrichment demo through a proxy"
    )
    lead_demo.add_argument(
        "--base-url", default=os.environ.get("AGENTWARDEN_BASE_URL", "http://127.0.0.1:8080/v1")
    )
    lead_demo.add_argument("--model", default=os.environ.get("AGENTWARDEN_MODEL", LEAD_DEFAULT_MODEL))
    lead_demo.add_argument("--session-id", default=None)
    lead_demo.add_argument("--max-steps", type=int, default=16)

    args = parser.parse_args()
    if args.command == "serve":
        uvicorn.run("proxy.server:app", host=args.host, port=args.port)
        return 0
    if args.command == "dashboard":
        print(f"Dashboard: http://{args.host}:{args.port}/dashboard")
        uvicorn.run("proxy.server:app", host=args.host, port=args.port)
        return 0
    if args.command == "stats":
        settings = Settings.from_environment()
        store = TraceStore(Path(args.db))
        print(json.dumps(store.get_stats(args.session_id, settings.model_prices), indent=2))
        return 0
    if args.command == "doctor":
        return _doctor(args.base_url)
    if args.command == "demo":
        api_key = _require_api_key()
        result = run_demo_task(
            api_key=api_key,
            base_url=args.base_url,
            model=args.model,
            task=args.task or DEFAULT_TASK,
            session_id=args.session_id,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return 0
    if args.command == "verify":
        api_key = _require_api_key()
        report = verify_demo_task(
            api_key=api_key,
            model=args.model,
            task=args.task or DEFAULT_TASK,
            include_judge=not args.no_judge,
        )
        print(json.dumps(report.to_dict(), indent=2))
        return 0
    if args.command == "lead-demo":
        result = run_lead_task(
            api_key=_require_api_key(),
            base_url=args.base_url,
            model=args.model,
            session_id=args.session_id,
            max_steps=args.max_steps,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return 0
    raise AssertionError("unreachable")


def _require_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required")
    return api_key


def _doctor(base_url: str) -> int:
    """Confirm that the local proxy exposes its observability endpoint."""

    proxy_root = base_url.rstrip("/").removesuffix("/v1")
    try:
        response = httpx.get(f"{proxy_root}/stats", timeout=2.0)
        response.raise_for_status()
    except httpx.HTTPError as error:
        print(
            f"AgentWarden is not reachable at {proxy_root}. "
            "Start it with: agentwarden serve"
        )
        print(f"Details: {error}")
        return 1

    print(f"AgentWarden is ready at {proxy_root}.")
    print(f"SDK base_url: {proxy_root}/v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
