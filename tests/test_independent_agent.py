"""Unit coverage for the copyable consumer-agent example."""

from __future__ import annotations

from examples.independent_agent.agent import execute_tool, support_tools


def test_independent_agent_has_required_and_decoy_tools() -> None:
    names = [tool["function"]["name"] for tool in support_tools()]
    assert names[:5] == [
        "get_ticket",
        "get_customer_plan",
        "search_knowledge_base",
        "get_recent_incidents",
        "get_escalation_policy",
    ]
    assert "refund_invoice" in names
    assert "send_marketing_email" in names


def test_independent_agent_uses_deterministic_local_tool_data() -> None:
    ticket = execute_tool("get_ticket", '{"ticket_id":"SUP-1042"}')
    assert "CSV exports timing out" in ticket
    assert "asynchronous export endpoint" in execute_tool(
        "search_knowledge_base", "{}"
    )
