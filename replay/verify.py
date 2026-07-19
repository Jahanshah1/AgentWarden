"""Replay the demo task with optimizations off and on, then compare outcomes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any

import httpx
from openai import OpenAI

from demo_agent.agent import DEFAULT_MODEL, DEFAULT_TASK, run_demo_task


@dataclass(frozen=True)
class ReplayReport:
    off_run: dict[str, Any]
    on_run: dict[str, Any]
    off_stats: dict[str, Any]
    on_stats: dict[str, Any]
    tool_call_sequence_match: bool
    tests_passed_match: bool
    answer_similarity: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def verify_demo_task(
    *,
    api_key: str,
    model: str = DEFAULT_MODEL,
    task: str = DEFAULT_TASK,
    workspace_parent: Path | None = None,
    include_judge: bool = True,
) -> ReplayReport:
    off_port = _free_port()
    on_port = _free_port()
    with tempfile.TemporaryDirectory(prefix="agentwarden-verify-") as directory:
        database_dir = Path(directory)
        off_process = _launch_proxy(
            off_port,
            {
                "AGENTWARDEN_ENABLE_TOOL_PRUNE": "false",
                "AGENTWARDEN_ENABLE_HISTORY_TRIM": "false",
                "AGENTWARDEN_ENABLE_CONTEXT_DEDUP": "false",
                "AGENTWARDEN_ENABLE_CACHE_ORDER": "false",
                "AGENTWARDEN_DB_PATH": str(database_dir / "off.sqlite3"),
            },
        )
        on_process = _launch_proxy(
            on_port,
            {
                "AGENTWARDEN_ENABLE_TOOL_PRUNE": "true",
                "AGENTWARDEN_ENABLE_HISTORY_TRIM": "true",
                "AGENTWARDEN_ENABLE_CONTEXT_DEDUP": "true",
                "AGENTWARDEN_ENABLE_CACHE_ORDER": "true",
                "AGENTWARDEN_SESSION_BUDGET_USD": "0.02",
                "AGENTWARDEN_DB_PATH": str(database_dir / "on.sqlite3"),
            },
        )
        try:
            off_run = run_demo_task(
                api_key=api_key,
                base_url=f"http://127.0.0.1:{off_port}/v1",
                model=model,
                task=task,
                session_id="verify-off",
                workspace_parent=workspace_parent,
            )
            on_run = run_demo_task(
                api_key=api_key,
                base_url=f"http://127.0.0.1:{on_port}/v1",
                model=model,
                task=task,
                session_id="verify-on",
                workspace_parent=workspace_parent,
            )
            off_stats = _get_json(f"http://127.0.0.1:{off_port}/stats", {"session_id": "verify-off"})
            on_stats = _get_json(f"http://127.0.0.1:{on_port}/stats", {"session_id": "verify-on"})
            off_traces = _get_json(f"http://127.0.0.1:{off_port}/traces", {"session_id": "verify-off"})
            on_traces = _get_json(f"http://127.0.0.1:{on_port}/traces", {"session_id": "verify-on"})
            similarity = None
            if include_judge:
                similarity = _judge_similarity(api_key, model, off_run.final_message, on_run.final_message)
            return ReplayReport(
                off_run=off_run.to_dict(),
                on_run=on_run.to_dict(),
                off_stats=off_stats,
                on_stats=on_stats,
                tool_call_sequence_match=_tool_sequence(off_traces) == _tool_sequence(on_traces),
                tests_passed_match=off_run.tests_passed == on_run.tests_passed,
                answer_similarity=similarity,
            )
        finally:
            off_process.terminate()
            on_process.terminate()
            off_process.wait(timeout=5)
            on_process.wait(timeout=5)


def _launch_proxy(port: int, extra_env: dict[str, str]) -> subprocess.Popen[str]:
    env = os.environ.copy()
    env.update(extra_env)
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "proxy.server:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    _wait_for_server(f"http://127.0.0.1:{port}/stats")
    return process


def _wait_for_server(url: str, timeout_seconds: float = 15.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=1.0)
            if response.status_code < 500:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.2)
    raise RuntimeError(f"Timed out waiting for {url}")


def _get_json(url: str, params: dict[str, str]) -> dict[str, Any]:
    response = httpx.get(url, params=params, timeout=10.0)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected object payload from {url}")
    return payload


def _tool_sequence(traces_payload: dict[str, Any]) -> list[str]:
    sequence: list[str] = []
    for trace in reversed(traces_payload.get("traces", [])):
        for name in trace.get("tools_called", []):
            if isinstance(name, str):
                sequence.append(name)
    return sequence


def _judge_similarity(
    api_key: str,
    model: str,
    off_answer: str,
    on_answer: str,
) -> dict[str, Any] | None:
    if not off_answer and not on_answer:
        return {"verdict": "both_empty", "score": 1.0}
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You compare two agent answers. Return strict JSON with keys "
                    "verdict, score, and rationale. Score is from 0 to 1."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Answer A:\n{off_answer}\n\nAnswer B:\n{on_answer}\n\n"
                    "Judge whether they are effectively equivalent for the same coding task."
                ),
            },
        ],
        response_format={"type": "json_object"},
    )
    content = completion.choices[0].message.content or "{}"
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return {"verdict": "unparseable", "raw": content}
    return payload if isinstance(payload, dict) else {"verdict": "invalid_payload", "raw": payload}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


if __name__ == "__main__":
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required")
    report = verify_demo_task(api_key=api_key)
    print(json.dumps(report.to_dict(), indent=2))
