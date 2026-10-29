"""Signed human decisions (HMAC-SHA256) with one-time nonces and a hash-chained ledger.

A decision token binds: job id, decision, reviewer, the SHA-256 of the exact report
that was reviewed, an expiry and a nonce. So an approval cannot be forged without the
server secret, cannot be replayed (nonce is consumed atomically), expires, and is
void if the report changes after review.

Honest limit: this is symmetric signing with a server-side secret, not a PKI
signature with per-reviewer keys. Reviewer identity rests on the reviewer key table.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from pathlib import Path

from .config import check_secret, data_dir, signing_secret

TOKEN_TTL_S = 15 * 60
ACTIONS = {"PUBLISH_CERTIFICATE", "UPDATE_STATUS"}
REGISTRIES = {"national_audit_registry"}


class SignatureError(PermissionError):
    pass


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _db(path: Path | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(str(path or (data_dir() / "ledger.sqlite")), timeout=10)
    con.execute("CREATE TABLE IF NOT EXISTS nonces(nonce TEXT PRIMARY KEY, used_at REAL)")
    con.execute(
        "CREATE TABLE IF NOT EXISTS ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, job_id TEXT,"
        " action TEXT, registry TEXT, reviewer TEXT, report_sha256 TEXT, prev_hash TEXT, entry_hash TEXT)"
    )
    return con


def issue_decision_token(job_id: str, decision: str, reviewer: str, reviewer_key: str,
                         report_sha256: str, now: float | None = None) -> str:
    """Issue a token only for an authenticated reviewer (key checked against MIJHAR_REVIEWERS)."""
    if decision not in ("approve", "reject", "revise"):
        raise SignatureError("invalid decision")
    if check_secret("MIJHAR_REVIEWERS", reviewer_key, who=reviewer) is None:
        raise SignatureError("reviewer authentication failed")
    payload = {"job_id": job_id, "decision": decision, "reviewer": reviewer,
               "report_sha256": report_sha256, "exp": (now or time.time()) + TOKEN_TTL_S,
               "nonce": secrets.token_hex(16)}
    body = _b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    sig = _b64(hmac.new(signing_secret(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


def parse_token(token: str, now: float | None = None) -> dict:
    """Verify signature + expiry. Does NOT consume the nonce."""
    try:
        body, sig = token.split(".", 1)
    except (ValueError, AttributeError):
        raise SignatureError("malformed token")
    expected = _b64(hmac.new(signing_secret(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, sig):
        raise SignatureError("bad signature")
    try:
        payload = json.loads(_unb64(body))
    except Exception:
        raise SignatureError("malformed payload")
    if float(payload.get("exp", 0)) < (now or time.time()):
        raise SignatureError("token expired")
    return payload


def verify_for_commit(token: str, job_id: str, report_sha256: str, now: float | None = None) -> dict:
    payload = parse_token(token, now)
    if payload["job_id"] != job_id:
        raise SignatureError("token is for a different job")
    if payload["report_sha256"] != report_sha256:
        raise SignatureError("report changed after review")
    if payload["decision"] != "approve":
        raise SignatureError("decision is not approve")
    return payload


def commit_action(token: str, action: str, job_id: str, report_sha256: str,
                  registry: str = "national_audit_registry", db_path: Path | None = None,
                  now: float | None = None) -> dict:
    """The only write path. Re-verifies everything, consumes the nonce, appends to a hash chain."""
    if action not in ACTIONS:
        raise SignatureError(f"action not allowed: {action!r}")
    if registry not in REGISTRIES:
        raise SignatureError(f"registry not allowed: {registry!r}")
    payload = verify_for_commit(token, job_id, report_sha256, now)
    con = _db(db_path)
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            con.execute("INSERT INTO nonces(nonce, used_at) VALUES (?, ?)", (payload["nonce"], time.time()))
        except sqlite3.IntegrityError:
            con.execute("ROLLBACK")
            raise SignatureError("token already used")
        row = con.execute("SELECT entry_hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        prev = row[0] if row else "0" * 64
        ts = time.time()
        entry = hashlib.sha256(
            f"{prev}|{ts}|{job_id}|{action}|{registry}|{payload['reviewer']}|{report_sha256}".encode()).hexdigest()
        con.execute(
            "INSERT INTO ledger(ts, job_id, action, registry, reviewer, report_sha256, prev_hash, entry_hash)"
            " VALUES (?,?,?,?,?,?,?,?)", (ts, job_id, action, registry, payload["reviewer"], report_sha256, prev, entry))
        con.execute("COMMIT")
    finally:
        con.close()
    return {"status": "COMMITTED", "job_id": job_id, "action": action, "registry": registry,
            "reviewer": payload["reviewer"], "tx_hash": entry, "prev_hash": prev,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))}


def verify_ledger_chain(db_path: Path | None = None) -> bool:
    con = _db(db_path)
    try:
        prev = "0" * 64
        for ts, job_id, action, registry, reviewer, rsha, p, h in con.execute(
                "SELECT ts, job_id, action, registry, reviewer, report_sha256, prev_hash, entry_hash FROM ledger ORDER BY seq"):
            calc = hashlib.sha256(f"{prev}|{ts}|{job_id}|{action}|{registry}|{reviewer}|{rsha}".encode()).hexdigest()
            if p != prev or h != calc:
                return False
            prev = h
        return True
    finally:
        con.close()
