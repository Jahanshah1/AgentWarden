from __future__ import annotations

from pathlib import Path

from demo_agent.agent import DEFAULT_TASK
from demo_agent.tools import DECOY_TOOLS, DemoToolbox


SAMPLE_REPO = Path(__file__).resolve().parents[1] / "demo_agent" / "sample_repo"


def test_tool_catalog_contains_real_tools_and_decoys() -> None:
    tool_names = [tool["function"]["name"] for tool in DemoToolbox.openai_tools()]
    assert tool_names[:5] == ["list_dir", "read_file", "write_file", "grep", "run_tests"]
    assert list(DECOY_TOOLS) == tool_names[5:]


def test_default_demo_task_retains_required_coding_tools() -> None:
    for tool_name in ("list_dir", "read_file", "grep", "write_file", "run_tests"):
        assert tool_name in DEFAULT_TASK


def test_run_tests_reports_the_intentionally_broken_fixture_repo() -> None:
    toolbox = DemoToolbox(SAMPLE_REPO)
    result = toolbox.run_tests()
    assert result.ok is False
    assert "failed" in result.output.lower()


def test_read_file_and_list_dir_are_scoped_to_sample_repo() -> None:
    toolbox = DemoToolbox(SAMPLE_REPO)
    assert "app.py" in toolbox.list_dir(".").output
    assert "build_release_summary" in toolbox.read_file("app.py").output


def test_execute_routes_arguments_and_rejects_decoy_tools() -> None:
    toolbox = DemoToolbox(SAMPLE_REPO)
    assert "inventory.py" in toolbox.execute("list_dir", '{"path":"."}').output
    decoy = toolbox.execute("open_browser", "{}")
    assert decoy.ok is False
    assert "unavailable" in decoy.output
