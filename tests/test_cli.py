"""Small contract tests for the install-facing CLI helpers."""

from __future__ import annotations

from proxy.cli import _doctor


def test_doctor_reports_unreachable_proxy(capsys: object) -> None:
    assert _doctor("http://127.0.0.1:1/v1") == 1
    output = capsys.readouterr().out  # type: ignore[attr-defined]
    assert "not reachable" in output
    assert "agentwarden serve" in output
