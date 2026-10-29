"""HTTP service. Auth by API key; the human decision is signed server-side only after the
reviewer authenticates with their own key and echoes the hash of the report they reviewed."""
from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from . import signing
from .config import CONFIG_A, CONFIG_B, ConfigError, RunConfig, check_secret, env
from .graph import Auditor, Runtime
from .toolbox import ToolBox, ToolError

# Local UI by default; on the cloud set MIJHAR_CORS_ORIGINS="https://your-ui.vercel.app" (comma separated).
ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"] + [
    o.strip().rstrip("/") for o in (env("MIJHAR_CORS_ORIGINS", "") or "").split(",") if o.strip()]
MAX_JOBS_PER_KEY = int(env("MIJHAR_MAX_JOBS_PER_KEY", "50") or 50)


class AuditIn(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    filename: str = Field(default="document.txt", max_length=120)
    config: str = Field(default="B", pattern="^[AB]$")
    live: bool | None = None   # None = auto: real model if the server has a key AND MIJHAR_ALLOW_LIVE=1; true/false forces


class DecisionIn(BaseModel):
    reviewer: str = Field(min_length=1, max_length=64)
    decision: str = Field(pattern="^(approve|reject|revise)$")
    report_sha256: str = Field(min_length=64, max_length=64)


def public_view(v: dict) -> dict:
    """Never return raw_text, tokens or internals the caller does not need."""
    keys = ("job_id", "status", "error", "sha256", "quarantined", "risk_score", "claims", "threats",
            "internal_conflicts", "context_usage", "budget", "report_sha256", "hitl", "commit", "awaiting_human", "trace")
    out = {k: v.get(k) for k in keys}
    out["live"] = bool((v.get("cfg") or {}).get("live_llm"))
    if out.get("hitl"):
        out["hitl"] = {k: x for k, x in out["hitl"].items() if k != "token"}
    out["threats"] = [{k: t[k] for k in ("rule", "attack", "severity", "snippet")} for t in (out.get("threats") or [])]
    return out


def _with_pending_hash(a: Auditor, snap: dict) -> dict:
    """While awaiting a human, expose the hash of the report under review so the reviewer can echo it."""
    out = public_view(snap)
    if snap.get("awaiting_human"):
        out["report_sha256"] = a.pending_report_hash(snap["job_id"])
    return out


def create_app(auditor: Auditor | None = None) -> FastAPI:
    app = FastAPI(title="MIJHAR audit API", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS,
                       allow_methods=["GET", "POST"], allow_headers=["X-API-Key", "X-Reviewer-Key", "Content-Type"])
    state = {"auditor": auditor, "jobs": defaultdict(int)}

    def live_llm():
        """Create the model client on first live request. Fails closed and explains why."""
        from .llm import LLM
        if (env("MIJHAR_ALLOW_LIVE", "0") or "0") != "1":
            raise HTTPException(403, "live mode is disabled on this server (set MIJHAR_ALLOW_LIVE=1; "
                                     "documents then leave the Kingdom, see SECURITY.md)")
        a = aud()
        if a.rt.llm is None:
            try:
                a.rt.llm = LLM()
            except RuntimeError as e:
                raise HTTPException(503, f"live mode unavailable: {e}")
        if a.rt.llm.dead:
            raise HTTPException(503, f"live mode unavailable: {a.rt.llm.dead}")

    def aud() -> Auditor:
        if state["auditor"] is None:
            # Tools run over the stdio MCP server by default (MIJHAR_MCP=0 for in-process).
            # If the MCP subprocess cannot start, fall back to in-process and say so in /healthz.
            tb = None
            if (env("MIJHAR_MCP", "1") or "1") == "1":
                try:
                    tb = ToolBox(True)
                except ToolError as e:
                    state["mcp_error"] = str(e)[:200]
            state["auditor"] = Auditor(Runtime(tb or ToolBox(False)))
        return state["auditor"]

    def agent():
        if state.get("agent") is None:
            from .agent.service import AgentService
            state["agent"] = AgentService.from_env(aud())
        return state["agent"]

    def client(x_api_key: str | None = Header(default=None)) -> str:
        who = check_secret("MIJHAR_CLIENT_KEYS", x_api_key)
        if not who:
            raise HTTPException(401, "invalid or missing X-API-Key")
        return who

    @app.get("/healthz")
    def health():
        out = {"ok": True, "ledger_chain_valid": signing.verify_ledger_chain()}
        if state.get("auditor") is not None:
            out["mcp"] = bool(state["auditor"].rt.toolbox.use_mcp)
        if state.get("mcp_error"):
            out["mcp_error"] = state["mcp_error"]
        return out

    @app.post("/v1/audits")
    def create_audit(body: AuditIn, who: str = Depends(client)):
        if state["jobs"][who] >= MAX_JOBS_PER_KEY:
            raise HTTPException(429, "job budget used up for this key")
        base = CONFIG_B if body.config == "B" else CONFIG_A
        want_live = body.live
        if want_live is None:
            want_live = (env("MIJHAR_ALLOW_LIVE", "0") == "1") and bool(env("OPENROUTER_API_KEY"))
        if want_live:
            live_llm()
        state["jobs"][who] += 1
        a = aud()
        cfg = RunConfig(**base.to_dict() | {"live_llm": bool(want_live)})
        snap = a.start(body.text, body.filename, cfg)
        return _with_pending_hash(a, snap)

    @app.get("/v1/audits/{job_id}")
    def get_audit(job_id: str, who: str = Depends(client)):
        a = aud()
        snap = a.snapshot(job_id)
        if not snap.get("job_id"):
            raise HTTPException(404, "unknown job")
        return _with_pending_hash(a, snap)

    @app.post("/v1/audits/{job_id}/decision")
    def decide(job_id: str, body: DecisionIn, x_reviewer_key: str | None = Header(default=None)):
        a = aud()
        pending = a.pending_report_hash(job_id)
        if pending is None:
            raise HTTPException(409, "job is not awaiting a human decision")
        if body.report_sha256 != pending:
            raise HTTPException(409, "report changed since you reviewed it")
        try:
            token = signing.issue_decision_token(job_id, body.decision, body.reviewer, x_reviewer_key or "", pending)
        except signing.SignatureError:
            raise HTTPException(403, "reviewer authentication failed")
        except ConfigError as e:
            raise HTTPException(503, str(e))
        return public_view(a.resume(job_id, token))

    @app.get("/v1/ledger/verify")
    def ledger(who: str = Depends(client)):
        return {"chain_valid": signing.verify_ledger_chain()}

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse("/agent/")

    @app.get("/agent", include_in_schema=False)
    def agent_slash():
        return RedirectResponse("/agent/")

    from .agent.web import build_agent_app
    app.mount("/agent", build_agent_app(agent))   # the agent UI and its API: /agent/ and /agent/api/...
    return app


app = create_app()
