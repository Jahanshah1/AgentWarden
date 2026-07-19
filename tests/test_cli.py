"""Small contract tests for the install-facing CLI helpers."""

from __future__ import annotations

import sys
from typing import Any

from demo_agent.agent import DEFAULT_TASK
from proxy.cli import _doctor, main


def test_doctor_reports_unreachable_proxy(capsys: object) -> None:
    assert _doctor("http://127.0.0.1:1/v1") == 1
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "not reachable" in output
    assert "agentwarden serve" in output


def test_verify_uses_the_canonical_demo_task(monkeypatch: Any) -> None:
    captured: dict[str, Any] = {}

    class FakeReport:
        def to_dict(self) -> dict[str, str]:
            return {"status": "ok"}

    def fake_verify(**kwargs: Any) -> FakeReport:
        captured.update(kwargs)
        return FakeReport()

    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(sys, "argv", ["agentwarden", "verify", "--no-judge"])
    monkeypatch.setattr("proxy.cli.verify_demo_task", fake_verify)

    assert main() == 0
    assert captured["task"] == DEFAULT_TASK
    assert captured["include_judge"] is False
