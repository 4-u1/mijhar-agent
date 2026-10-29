import sqlite3
import time

import pytest

from mijhar import signing as S
from tests.conftest import RKEY


def tok(job="J", dec="approve", rsha="r" * 8, **kw):
    return S.issue_decision_token(job, dec, "eng.test", RKEY, rsha, **kw)


def test_valid_commit_then_replay_refused():
    t = tok()
    assert S.commit_action(t, "PUBLISH_CERTIFICATE", "J", "r" * 8)["status"] == "COMMITTED"
    with pytest.raises(S.SignatureError, match="already used"):
        S.commit_action(t, "PUBLISH_CERTIFICATE", "J", "r" * 8)


@pytest.mark.parametrize("bad", ["0x" + "a" * 40, "", "a.b", None])
def test_forged_tokens_refused(bad):
    with pytest.raises(S.SignatureError):
        S.commit_action(bad, "PUBLISH_CERTIFICATE", "J", "r" * 8)


def test_tampered_payload_refused():
    body, sig = tok().split(".")
    with pytest.raises(S.SignatureError, match="bad signature"):
        S.parse_token(body[:-2] + "AA." + sig)


def test_expired_wrong_job_changed_report_reject_decision():
    with pytest.raises(S.SignatureError, match="expired"):
        S.commit_action(tok(now=time.time() - 9999), "PUBLISH_CERTIFICATE", "J", "r" * 8)
    with pytest.raises(S.SignatureError, match="different job"):
        S.commit_action(tok(), "PUBLISH_CERTIFICATE", "OTHER", "r" * 8)
    with pytest.raises(S.SignatureError, match="report changed"):
        S.commit_action(tok(), "PUBLISH_CERTIFICATE", "J", "x" * 8)
    with pytest.raises(S.SignatureError, match="not approve"):
        S.commit_action(tok(dec="reject"), "PUBLISH_CERTIFICATE", "J", "r" * 8)


def test_unauthenticated_reviewer_cannot_get_token():
    with pytest.raises(S.SignatureError):
        S.issue_decision_token("J", "approve", "eng.test", "wrong-key", "r")
    with pytest.raises(S.SignatureError):
        S.issue_decision_token("J", "approve", "someone.else", RKEY, "r")


def test_disallowed_action_and_registry():
    with pytest.raises(S.SignatureError):
        S.commit_action(tok(), "DROP_TABLE", "J", "r" * 8)
    with pytest.raises(S.SignatureError):
        S.commit_action(tok(), "PUBLISH_CERTIFICATE", "J", "r" * 8, registry="other")


def test_ledger_chain_detects_tampering(env):
    for j in ("A", "B"):
        S.commit_action(tok(j), "PUBLISH_CERTIFICATE", j, "r" * 8)
    assert S.verify_ledger_chain()
    con = sqlite3.connect(env / "ledger.sqlite")
    con.execute("UPDATE ledger SET reviewer='mallory' WHERE seq=1"); con.commit(); con.close()
    assert not S.verify_ledger_chain()


def test_missing_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("MIJHAR_SIGNING_SECRET")
    from mijhar.config import ConfigError
    with pytest.raises(ConfigError):
        tok()
