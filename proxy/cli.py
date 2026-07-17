"""CLI entry points for serving, stats, demo runs, and replay verification."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import uvicorn

from demo_agent.agent import DEFAULT_MODEL, run_demo_task
from proxy.config import Settings
from proxy.store import TraceStore
from replay.verify import verify_demo_task


def main() -> int:
    parser = argparse.ArgumentParser(prog="agentwarden")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Run the AgentWarden proxy server")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)

    stats = subparsers.add_parser("stats", help="Print stored session stats")
    stats.add_argument("--session-id", default="default")
    stats.add_argument("--db", default=os.environ.get("AGENTWARDEN_DB_PATH", "agentwarden.sqlite3"))

    demo = subparsers.add_parser("demo", help="Run the demo coding agent through a proxy")
    demo.add_argument("--base-url", default=os.environ.get("AGENTWARDEN_BASE_URL", "http://127.0.0.1:8080/v1"))
    demo.add_argument("--model", default=os.environ.get("AGENTWARDEN_MODEL", DEFAULT_MODEL))
    demo.add_argument("--task", default=os.environ.get("AGENTWARDEN_TASK"))
    demo.add_argument("--session-id", default=None)

    verify = subparsers.add_parser("verify", help="Replay the demo task with optimizations off and on")
    verify.add_argument("--model", default=os.environ.get("AGENTWARDEN_MODEL", DEFAULT_MODEL))
    verify.add_argument("--task", default=os.environ.get("AGENTWARDEN_TASK"))
    verify.add_argument("--no-judge", action="store_true")

    args = parser.parse_args()
    if args.command == "serve":
        uvicorn.run("proxy.server:app", host=args.host, port=args.port)
        return 0
    if args.command == "stats":
        settings = Settings.from_environment()
        store = TraceStore(Path(args.db))
        print(json.dumps(store.get_stats(args.session_id, settings.model_prices), indent=2))
        return 0
    if args.command == "demo":
        api_key = _require_api_key()
        result = run_demo_task(
            api_key=api_key,
            base_url=args.base_url,
            model=args.model,
            task=args.task or "Inspect the repository, fix the bugs, and make all tests pass.",
            session_id=args.session_id,
        )
        print(json.dumps(result.to_dict(), indent=2))
        return 0
    if args.command == "verify":
        api_key = _require_api_key()
        report = verify_demo_task(
            api_key=api_key,
            model=args.model,
            task=args.task or "Inspect the repository, fix the bugs, and make all tests pass.",
            include_judge=not args.no_judge,
        )
        print(json.dumps(report.to_dict(), indent=2))
        return 0
    raise AssertionError("unreachable")


def _require_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required")
    return api_key


if __name__ == "__main__":
    raise SystemExit(main())
