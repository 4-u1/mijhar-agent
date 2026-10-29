import os

from mijhar import graph as G
from mijhar import guard, signing
from mijhar.config import CONFIG_B, RunConfig
from tests.conftest import DOC, RKEY


def mk(env):
    return G.Auditor(checkpoint_path=str(env / "cp.sqlite"))


def approve(a, job, dec="approve"):
    return a.resume(job, signing.issue_decision_token(job, dec, "eng.test", RKEY, a.pending_report_hash(job)))


def test_stops_at_human_gate_and_writes_nothing(env):
    a = mk(env)
    s = a.start(DOC, cfg=CONFIG_B, job_id="J1")
    assert s["awaiting_human"] and not s.get("commit")
    assert "CANARY" not in s["llm_input"]
    assert not os.path.exists(env / "ledger.sqlite") or not signing.verify_ledger_chain() is False
    assert [t["span"] for t in s["trace"]] == ["ingest", "guardrail", "extract", "retrieve", "verify", "score"]


def test_signed_approval_commits_once(env):
    a = mk(env)
    a.start(DOC, cfg=CONFIG_B, job_id="J2")
    f = approve(a, "J2")
    assert f["status"] == "committed" and f["commit"]["reviewer"] == "eng.test"


def test_forged_resume_is_refused_and_nothing_committed(env):
    a = mk(env)
    a.start(DOC, cfg=CONFIG_B, job_id="J3")
    f = a.resume("J3", "0x" + "a" * 40)
    assert f["status"] == "refused" and not f.get("commit")


def test_reject_does_not_commit(env):
    a = mk(env)
    a.start(DOC, cfg=CONFIG_B, job_id="J4")
    assert approve(a, "J4", "reject")["status"] == "rejected"


def test_resume_after_process_restart(env):
    a = mk(env); a.start(DOC, cfg=CONFIG_B, job_id="J5")
    b = mk(env)                      # new objects, same SQLite checkpoint file = simulated crash/restart
    assert b.snapshot("J5")["awaiting_human"]
    assert approve(b, "J5")["status"] == "committed"


def test_guard_failure_fails_closed(env, monkeypatch):
    monkeypatch.setattr(guard, "scan", lambda t, level="hardened": guard.ScanResult(level, len(t), "", [], blocked=True, error="boom"))
    s = mk(env).start(DOC, cfg=CONFIG_B, job_id="J6")
    assert s["status"] == "blocked" and not s.get("claims")


def test_step_budget_blocks(env):
    s = mk(env).start(DOC, cfg=RunConfig(max_steps=2), job_id="J7")
    assert s["status"] == "blocked" and "budget" in s["error"]


def test_oversize_and_empty_documents_blocked(env):
    assert mk(env).start("x" * 300_000, job_id="J8")["status"] == "blocked"
    assert mk(env).start("   ", job_id="J9")["status"] == "blocked"
