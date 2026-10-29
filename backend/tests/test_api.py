from fastapi.testclient import TestClient

from mijhar.api import create_app
from mijhar.graph import Auditor
from tests.conftest import CKEY, DOC, RKEY

H = {"X-API-Key": CKEY}


def client(env):
    return TestClient(create_app(Auditor(checkpoint_path=str(env / "cp.sqlite"))))


def test_requires_api_key(env):
    c = client(env)
    assert c.post("/v1/audits", json={"text": "x"}).status_code == 401
    assert c.post("/v1/audits", json={"text": "x"}, headers={"X-API-Key": "nope"}).status_code == 401


def test_full_flow_and_no_secret_leakage(env):
    c = client(env)
    r = c.post("/v1/audits", json={"text": DOC}, headers=H).json()
    assert r["awaiting_human"] and "raw_text" not in r and "CANARY" not in str(r["claims"])
    assert len(r["report_sha256"]) == 64
    body = {"reviewer": "eng.test", "decision": "approve", "report_sha256": r["report_sha256"]}
    assert c.post(f"/v1/audits/{r['job_id']}/decision", json=body).status_code == 403  # no reviewer key
    assert c.post(f"/v1/audits/{r['job_id']}/decision", json=body, headers={"X-Reviewer-Key": "wrong"}).status_code == 403


def test_approval_binds_to_report_hash(env):
    from mijhar.graph import Auditor as A
    aud = A(checkpoint_path=str(env / "cp.sqlite"))
    c = TestClient(create_app(aud))
    r = c.post("/v1/audits", json={"text": DOC}, headers=H).json()
    h = aud.pending_report_hash(r["job_id"])
    bad = c.post(f"/v1/audits/{r['job_id']}/decision", json={"reviewer": "eng.test", "decision": "approve", "report_sha256": "0" * 64}, headers={"X-Reviewer-Key": RKEY})
    assert bad.status_code == 409
    wrong_key = c.post(f"/v1/audits/{r['job_id']}/decision", json={"reviewer": "eng.test", "decision": "approve", "report_sha256": h}, headers={"X-Reviewer-Key": "bad"})
    assert wrong_key.status_code == 403
    ok = c.post(f"/v1/audits/{r['job_id']}/decision", json={"reviewer": "eng.test", "decision": "approve", "report_sha256": h}, headers={"X-Reviewer-Key": RKEY})
    out = ok.json()
    assert ok.status_code == 200 and out["status"] == "committed" and "token" not in str(out["hitl"])


def test_input_limits(env):
    c = client(env)
    assert c.post("/v1/audits", json={"text": "x" * 200_001}, headers=H).status_code == 422


def test_live_is_off_unless_server_opts_in(env, monkeypatch):
    monkeypatch.delenv("MIJHAR_ALLOW_LIVE", raising=False)
    c = client(env)
    r = c.post("/v1/audits", json={"text": DOC, "live": True}, headers=H)
    assert r.status_code == 403 and "disabled" in r.json()["detail"]
    ok = c.post("/v1/audits", json={"text": DOC}, headers=H).json()
    assert ok["live"] is False


def test_live_without_key_is_a_clear_503_not_a_crash(env, monkeypatch):
    monkeypatch.setenv("MIJHAR_ALLOW_LIVE", "1")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    r = client(env).post("/v1/audits", json={"text": DOC, "live": True}, headers=H)
    assert r.status_code == 503 and "OPENROUTER_API_KEY" in r.json()["detail"]


def test_live_run_uses_the_model_and_reports_live(env, monkeypatch):
    import json
    from types import SimpleNamespace as NS
    from mijhar.config import OpenRouterSettings
    from mijhar.graph import Runtime
    from mijhar.llm import LLM

    class Fake:
        def __init__(self):
            self.chat = NS(completions=NS(create=self.create))

        def create(self, **kw):
            sysmsg = kw["messages"][0]["content"]
            body = ({"claims": [{"text": "Data is stored on servers outside the Kingdom."}]} if "extract" in sysmsg
                    else {"stance": "refutes", "rationale": "residency"})
            return NS(choices=[NS(message=NS(content=json.dumps(body)))], usage=NS(total_tokens=5))

    monkeypatch.setenv("MIJHAR_ALLOW_LIVE", "1")
    llm = LLM(OpenRouterSettings(api_key="x"), client=Fake())
    aud = Auditor(Runtime(llm=llm), checkpoint_path=str(env / "cp.sqlite"))
    r = TestClient(create_app(aud)).post("/v1/audits", json={"text": DOC, "live": True}, headers=H).json()
    assert r["live"] is True and r["claims"][0]["extractor"] == "llm"
    assert r["claims"][0]["status"] == "contradicted" and llm.calls >= 2


def test_live_is_auto_when_server_has_key_and_opt_in(env, monkeypatch):
    import json
    from types import SimpleNamespace as NS
    from mijhar.config import OpenRouterSettings
    from mijhar.graph import Runtime
    from mijhar.llm import LLM

    class Fake:
        def __init__(self):
            self.chat = NS(completions=NS(create=self.create))

        def create(self, **kw):
            body = ({"claims": [{"text": "Data is stored on servers outside the Kingdom."}]}
                    if "extract" in kw["messages"][0]["content"] else {"stance": "refutes", "rationale": "x"})
            return NS(choices=[NS(message=NS(content=json.dumps(body)))], usage=NS(total_tokens=1))

    monkeypatch.setenv("MIJHAR_ALLOW_LIVE", "1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    aud = Auditor(Runtime(llm=LLM(OpenRouterSettings(api_key="k"), client=Fake())), checkpoint_path=str(env / "cp.sqlite"))
    c = TestClient(create_app(aud))
    assert c.post("/v1/audits", json={"text": DOC}, headers=H).json()["live"] is True            # no flag needed
    assert c.post("/v1/audits", json={"text": DOC, "live": False}, headers=H).json()["live"] is False   # explicit offline
