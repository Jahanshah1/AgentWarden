"""A runnable coding agent for exercising AgentWarden end to end."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any
from uuid import uuid4

from openai import OpenAI

from demo_agent.tools import DemoToolbox, ToolResult


DEFAULT_TASK = (
    "Inspect the repository, fix the bugs, and make all tests pass. "
    "Use list_dir, read_file, grep, write_file, and run_tests as needed."
)
DEFAULT_MODEL = "gpt-5.6-terra"
SAMPLE_REPO = Path(__file__).resolve().parent / "sample_repo"


@dataclass(frozen=True)
class DemoRunResult:
    session_id: str
    workspace: str
    model: str
    steps: int
    final_message: str
    tests_passed: bool
    test_output: str
    tool_call_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_workspace(parent_dir: Path | None = None) -> Path:
    root = Path(
        tempfile.mkdtemp(prefix="agentwarden-demo-", dir=parent_dir)
    ).resolve()
    workspace = root / "sample_repo"
    shutil.copytree(SAMPLE_REPO, workspace)
    return workspace


def run_demo_task(
    *,
    api_key: str,
    base_url: str,
    model: str = DEFAULT_MODEL,
    task: str = DEFAULT_TASK,
    session_id: str | None = None,
    max_steps: int = 12,
    workspace_parent: Path | None = None,
) -> DemoRunResult:
    workspace = make_workspace(workspace_parent)
    toolbox = DemoToolbox(workspace)
    client = OpenAI(api_key=api_key, base_url=base_url.rstrip("/"))
    session = session_id or f"demo-{uuid4().hex[:8]}"
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": (
                "You are a precise coding agent working in a small Python repository. "
                "Use tools to inspect files, run tests, and write fixes. "
                "Keep changes minimal and aim to make the test suite pass."
            ),
        },
        {"role": "user", "content": task},
    ]
    final_message = ""
    tool_call_count = 0

    for step in range(1, max_steps + 1):
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=DemoToolbox.openai_tools(),
            reasoning_effort="none",
            extra_headers={"X-AgentWarden-Session": session},
        )
        message = completion.choices[0].message
        tool_calls = list(message.tool_calls or [])
        if tool_calls:
            messages.append(_assistant_tool_call_message(message))
            for tool_call in tool_calls:
                tool_call_count += 1
                tool_result = toolbox.execute(
                    tool_call.function.name,
                    tool_call.function.arguments or "{}",
                )
                messages.append(_tool_message(tool_call.id, tool_result))
            continue

        final_message = message.content or ""
        messages.append(
            {
                "role": "assistant",
                "content": final_message,
            }
        )
        break

    final_tests = toolbox.run_tests()
    return DemoRunResult(
        session_id=session,
        workspace=str(workspace),
        model=model,
        steps=step,
        final_message=final_message,
        tests_passed=final_tests.ok,
        test_output=final_tests.output,
        tool_call_count=tool_call_count,
    )


def _assistant_tool_call_message(message: Any) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": message.content,
        "tool_calls": [
            {
                "id": tool_call.id,
                "type": tool_call.type,
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            }
            for tool_call in message.tool_calls or []
        ],
    }


def _tool_message(tool_call_id: str, result: ToolResult) -> dict[str, Any]:
    output = result.output
    if not result.ok:
        output = f"ERROR: {output}"
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": output,
    }


if __name__ == "__main__":
    import os

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is required")
    base_url = os.environ.get("AGENTWARDEN_BASE_URL", "http://127.0.0.1:8080/v1")
    result = run_demo_task(
        api_key=api_key,
        base_url=base_url,
        model=os.environ.get("AGENTWARDEN_MODEL", DEFAULT_MODEL),
    )
    print(json.dumps(result.to_dict(), indent=2))
