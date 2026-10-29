import pytest

from mijhar.toolbox import ToolBox, ToolError
from tests.conftest import RKEY


@pytest.fixture
def tb():
    t = ToolBox(use_mcp=True)
    yield t
    t.close()


def test_three_tools_exposed(tb):
    assert sorted(tb.bridge.list_tools()) == ["execute_audit_action", "hybrid_search_docs", "verify_evidence"]


def test_search_and_verify_over_mcp(tb):
    r = tb.call("hybrid_search_docs", {"query": "incidents reported within 72 hours", "top_k": 2})
    assert r["results"][0]["id"] == "AIE-06"
    v = tb.call("verify_evidence", {"claim_text": "reported within 7 days", "reference_text": r["results"][0]["text_en"]})
    assert v["stance"] == "refutes"


@pytest.mark.parametrize("args", [{"query": ""}, {"query": "x", "top_k": 99}, {"query": "x", "corpus_id": "nope"}, {"query": "x", "mode": "zzz"}])
def test_invalid_arguments_propagate_as_errors(tb, args):
    with pytest.raises(ToolError):
        tb.call("hybrid_search_docs", args)


def test_write_tool_refuses_forged_token_over_mcp(tb):
    with pytest.raises(ToolError):
        tb.call("execute_audit_action", {"decision_token": "0x" + "a" * 40, "action": "PUBLISH_CERTIFICATE", "job_id": "J", "report_sha256": "r" * 64})
