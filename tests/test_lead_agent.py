from __future__ import annotations

import json

from lead_agent.agent import DEFAULT_TASK, LeadToolbox


def test_lead_demo_catalog_has_named_workflow_tools_and_decoys() -> None:
    names = [tool["function"]["name"] for tool in LeadToolbox.openai_tools()]
    required = [
        "search_companies",
        "get_company_profile",
        "find_decision_maker",
        "verify_email",
        "score_lead",
        "save_lead",
        "draft_outreach",
    ]
    assert names[: len(required)] == required
    assert len(names) == 15
    for name in required:
        assert name in DEFAULT_TASK


def test_lead_demo_tools_save_qualified_fixture_lead_and_draft_outreach() -> None:
    toolbox = LeadToolbox()
    companies = toolbox.execute("search_companies", "{}")
    assert companies["ok"] is True
    assert [company["company_id"] for company in companies["companies"]] == ["nova-pay", "ledgerloop"]

    contact = toolbox.execute("find_decision_maker", '{"company_id":"nova-pay"}')["contact"]
    score = toolbox.execute("score_lead", '{"company_id":"nova-pay"}')["score"]
    saved = toolbox.execute(
        "save_lead",
        json.dumps({"company_id": "nova-pay", "contact": contact, "score": score}),
    )
    draft = toolbox.execute(
        "draft_outreach",
        json.dumps({"company_id": "nova-pay", "contact_name": contact["name"]}),
    )

    assert saved["ok"] is True
    assert draft["ok"] is True
    assert toolbox.saved_leads[0]["company"] == "NovaPay"
    assert "NovaPay" in toolbox.outreach_drafts[0]["subject"]


def test_lead_demo_rejects_decoy_tools() -> None:
    result = LeadToolbox().execute("send_bulk_campaign", "{}")
    assert result["ok"] is False
    assert "unavailable" in result["error"]
