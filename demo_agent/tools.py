"""Deterministic local tools for the AgentWarden demo coding agent."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
from typing import Any


DECOY_TOOLS = ("open_browser", "deploy_service", "query_warehouse")


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    output: str


class DemoToolbox:
    """A small, safe tool surface constrained to the sample repository."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def list_dir(self, path: str = ".") -> ToolResult:
        target = self._resolve(path)
        if not target.is_dir():
            return ToolResult(False, f"Not a directory: {path}")
        entries = sorted(entry.name for entry in target.iterdir())
        return ToolResult(True, "\n".join(entries))

    def read_file(self, path: str) -> ToolResult:
        target = self._resolve(path)
        if not target.is_file():
            return ToolResult(False, f"Not a file: {path}")
        return ToolResult(True, target.read_text(encoding="utf-8"))

    def write_file(self, path: str, content: str) -> ToolResult:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return ToolResult(True, f"Wrote {path}")

    def grep(self, pattern: str) -> ToolResult:
        matches: list[str] = []
        for file_path in sorted(self.repo_root.rglob("*")):
            if not file_path.is_file():
                continue
            try:
                text = file_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    matches.append(
                        f"{file_path.relative_to(self.repo_root)}:{line_number}:{line}"
                    )
        return ToolResult(True, "\n".join(matches))

    def run_tests(self) -> ToolResult:
        completed = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        output = completed.stdout.strip() or completed.stderr.strip()
        if completed.stderr.strip() and completed.stdout.strip():
            output = f"{completed.stdout.strip()}\n{completed.stderr.strip()}"
        return ToolResult(completed.returncode == 0, output)

    @classmethod
    def openai_tools(cls) -> list[dict[str, Any]]:
        """Expose a plausible coding-agent tool list, including decoys."""

        tools = [
            _function_tool(
                "list_dir",
                "List files in a repository directory.",
                {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                },
            ),
            _function_tool(
                "read_file",
                "Read a repository file.",
                {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            ),
            _function_tool(
                "write_file",
                "Overwrite a repository file with new content.",
                {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            ),
            _function_tool(
                "grep",
                "Search repository text for a fixed substring.",
                {
                    "type": "object",
                    "properties": {"pattern": {"type": "string"}},
                    "required": ["pattern"],
                },
            ),
            _function_tool(
                "run_tests",
                "Run the sample repository pytest suite.",
                {"type": "object", "properties": {}},
            ),
        ]
        tools.extend(
            _function_tool(
                name,
                "Unused decoy tool included to exercise pruning behavior.",
                {"type": "object", "properties": {}},
            )
            for name in DECOY_TOOLS
        )
        return tools

    def _resolve(self, path: str) -> Path:
        candidate = (self.repo_root / path).resolve()
        if self.repo_root not in candidate.parents and candidate != self.repo_root:
            raise ValueError(f"Path escapes sample repo: {path}")
        return candidate


def _function_tool(name: str, description: str, parameters: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        },
    }
