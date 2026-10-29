"""The agent's tools. This registry is the allow-list: anything not in it does not exist for the model.

 name                 level    over MCP   what it does
 load_skill           read     no         returns a skill body (just-in-time context)
 search_regulations   read     yes        hybrid_search_docs
 check_claim          read     yes        verify_evidence against one named passage
 audit_document       compute  no         runs the governed graph up to the human gate (writes nothing)
 get_audit_report     read     no         findings, optionally for one claim
 request_publication  gated    no         opens an approval card for the human; writes nothing

There is deliberately no tool that signs, approves or publishes. The write (`execute_audit_action`)
is called by the graph's `commit` node, only after a human-signed decision arrives through the API.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Callable, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..config import RunConfig
from ..graph import Auditor
from ..retrieval import load_passages
from ..toolbox import ToolError
from .config import AgentConfig
from .spec import load_skills
from .store import Session, Store

MIN_SCORE = 0.15   # same cut-off the graph uses for evidence


class ToolFailure(Exception):
    """Expected, model-recoverable problem. Becomes {"error": ...} in the tool result."""


@dataclass
class ToolContext:
    session: Session
    store: Store
    auditor: Auditor
    cfg: AgentConfig
    live_pipeline: bool = False
    emit: Callable[[dict], None] = lambda e: None


def wrap_claim(cid: str, text: str, cfg: AgentConfig) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()[:200]
    if not cfg.wrap_untrusted:
        return t
    t = re.sub(r"</?\s*untrusted_claim[^>]*>", "[tag-removed]", t, flags=re.I)
    return f'<untrusted_claim id="{cid}">{t}</untrusted_claim>'


def job_summary(snap: dict, cfg: AgentConfig) -> dict:
    claims = snap.get("claims") or []
    counts = {k: sum(1 for c in claims if c["status"] == k) for k in ("contradicted", "unsubstantiated", "verified", "inconclusive")}
    return {
        "job_id": snap["job_id"], "status": snap.get("status"), "awaiting_human": bool(snap.get("awaiting_human")),
        "risk_score": snap.get("risk_score"), "quarantined": bool(snap.get("quarantined")),
        "threats": [{"rule": t["rule"], "attack": t["attack"], "severity": t["severity"]} for t in snap.get("threats", [])][:10],
        "claim_counts": counts,
        "claims": [{"id": c["id"], "status": c["status"], "text": wrap_claim(c["id"], c["text"], cfg),
                    "evidence": [{"id": e["id"], "stance": e["stance"], "score": e["score"]} for e in c["evidence"][:2]]}
                   for c in claims[:25]],
        "internal_conflicts": snap.get("internal_conflicts", []),
        "report_sha256": snap.get("report_sha256"),
        **({"pipeline_error": snap["error"]} if snap.get("error") else {}),
    }


# ----------------------------------------------------------------------------- argument models
class _A(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoadSkillArgs(_A):
    name: str = Field(max_length=60, description="skill name from the skill index")


class SearchArgs(_A):
    query: str = Field(min_length=2, max_length=500, description="short query, Arabic or English")
    corpus_id: Literal["all", "ai_ethics", "cloud_sovereignty", "govtech_procurement"] = "all"
    top_k: int = Field(default=3, ge=1, le=5)


class CheckClaimArgs(_A):
    claim_text: str = Field(min_length=3, max_length=600)
    passage_id: str = Field(max_length=20, description="id such as CSV-01")


class AuditArgs(_A):
    doc_id: str = Field(max_length=24, description="id from the attachment note, e.g. DOC-1a2b3c4d")
    config: Literal["A", "B"] = "B"


class ReportArgs(_A):
    job_id: str = Field(max_length=40)
    claim_id: str | None = Field(default=None, max_length=20)


class PublishArgs(_A):
    job_id: str = Field(max_length=40)
    note: str = Field(default="", max_length=300, description="one line for the officer")


# ----------------------------------------------------------------------------- tool functions
def _passages() -> dict:
    return {p["id"]: p for p in load_passages()}


def t_load_skill(ctx: ToolContext, a: LoadSkillArgs) -> dict:
    sk = load_skills()
    if a.name not in sk:
        raise ToolFailure(f"unknown skill {a.name!r}; available: {sorted(sk)}")
    return {"name": a.name, "instructions": sk[a.name]["body"]}


def t_search(ctx: ToolContext, a: SearchArgs) -> dict:
    try:
        r = ctx.auditor.rt.toolbox.call("hybrid_search_docs", {"query": a.query, "corpus_id": a.corpus_id, "top_k": a.top_k, "mode": "hybrid"})
    except ToolError as e:
        raise ToolFailure(f"search failed: {e}")
    hits = [{"id": x["id"], "title_en": x["title_en"], "title_ar": x["title_ar"], "score": x["score"],
             "text_en": x["text_en"][:400], "text_ar": x["text_ar"][:400]} for x in r["results"] if x["score"] >= MIN_SCORE]
    return {"results": hits, "encoder": r.get("encoder"), "notice": r.get("corpus_notice"),
            **({} if hits else {"note": "no passage scored above the cut-off"})}


def t_check(ctx: ToolContext, a: CheckClaimArgs) -> dict:
    p = _passages().get(a.passage_id)
    if not p:
        raise ToolFailure(f"unknown passage_id {a.passage_id!r}")
    try:
        r = ctx.auditor.rt.toolbox.call("verify_evidence", {"claim_text": a.claim_text, "reference_text": f"{p['text_en']} {p['text_ar']}"})
    except ToolError as e:
        raise ToolFailure(f"verification failed: {e}")
    return {"passage_id": a.passage_id, "stance": r["stance"], "rationale": r["rationale"][:300], "method": r["method"]}


def t_audit(ctx: ToolContext, a: AuditArgs) -> dict:
    s = ctx.session
    meta = ctx.store.doc_meta(s.id, a.doc_id)
    if not meta:
        raise ToolFailure(f"unknown doc_id {a.doc_id!r} in this session")
    if s.usage["audits"] >= ctx.cfg.max_audits_per_session:
        raise ToolFailure(f"audit limit reached for this session ({ctx.cfg.max_audits_per_session})")
    text = ctx.store.doc_text(s.id, a.doc_id)             # harness-only: the model never receives this
    job_id = f"JOB-{uuid.uuid4().hex[:8]}"
    rt = ctx.auditor.rt
    rt.span_listeners[job_id] = lambda sp: ctx.emit({"type": "tool_progress", "node": sp["span"], "status": sp["status"], "ms": sp.get("ms", 0)})
    base = RunConfig(guard_level="basic", retrieval_mode="bm25") if a.config == "A" else RunConfig()
    cfg = RunConfig(**(base.to_dict() | {"live_llm": bool(ctx.live_pipeline and rt.llm), "use_mcp": rt.toolbox.use_mcp}))
    try:
        snap = ctx.auditor.start(text, meta["name"], cfg, job_id)
    finally:
        rt.span_listeners.pop(job_id, None)
    s.jobs.append(job_id)
    s.usage["audits"] += 1
    out = job_summary(snap, ctx.cfg)
    out["document"] = {"doc_id": a.doc_id, "name": meta["name"]}
    return out


def _own_job(ctx: ToolContext, job_id: str) -> dict:
    if job_id not in ctx.session.jobs:
        raise ToolFailure(f"unknown job_id {job_id!r} in this session")
    snap = ctx.auditor.snapshot(job_id)
    if not snap.get("job_id"):
        raise ToolFailure(f"job {job_id} has no state")
    if snap.get("awaiting_human"):
        snap["report_sha256"] = ctx.auditor.pending_report_hash(job_id)
    return snap


def t_report(ctx: ToolContext, a: ReportArgs) -> dict:
    snap = _own_job(ctx, a.job_id)
    if not a.claim_id:
        return job_summary(snap, ctx.cfg)
    c = next((x for x in snap.get("claims", []) if x["id"] == a.claim_id), None)
    if not c:
        raise ToolFailure(f"unknown claim_id {a.claim_id!r}")
    return {"job_id": a.job_id, "claim": {"id": c["id"], "status": c["status"], "text": wrap_claim(c["id"], c["text"], ctx.cfg)},
            "evidence": [{"id": e["id"], "title_en": e["title_en"], "stance": e["stance"], "score": e["score"], "method": e["method"],
                          "rationale": wrap_claim(c["id"], e["rationale"], ctx.cfg)} for e in c["evidence"]]}


def t_publish(ctx: ToolContext, a: PublishArgs) -> dict:
    s = ctx.session
    snap = _own_job(ctx, a.job_id)
    if not snap.get("awaiting_human"):
        raise ToolFailure(f"job {a.job_id} is {snap.get('status')!r}, not awaiting a human decision; nothing to approve")
    if s.pending and s.pending["job_id"] != a.job_id:
        raise ToolFailure(f"another approval is pending for {s.pending['job_id']}; the officer must decide it first")
    rsha = ctx.auditor.pending_report_hash(a.job_id)
    s.pending = {"job_id": a.job_id, "report_sha256": rsha, "risk_score": snap.get("risk_score"),
                 "quarantined": bool(snap.get("quarantined")), "note": a.note[:300]}
    return {"status": "approval_requested", "job_id": a.job_id, "report_sha256": rsha,
            "message": "The officer was asked to review and sign. You cannot approve or publish. Stop and wait."}


# ----------------------------------------------------------------------------- registry
@dataclass
class Tool:
    name: str
    description: str
    args: type[BaseModel]
    level: str
    fn: Callable[[ToolContext, BaseModel], dict]
    transport: str = "local"

    def spec(self) -> dict:
        def strip(o):
            if isinstance(o, dict):
                return {k: strip(v) for k, v in o.items() if k != "title"}
            return [strip(x) for x in o] if isinstance(o, list) else o
        return {"type": "function", "function": {"name": self.name, "description": self.description,
                                                  "parameters": strip(self.args.model_json_schema())}}


def default_registry() -> dict[str, Tool]:
    tools = [
        Tool("load_skill", "Load the instructions of one skill from the skill index.", LoadSkillArgs, "read", t_load_skill),
        Tool("search_regulations", "Search the reference corpora (synthetic regulations, Arabic and English). Returns passages with ids.",
             SearchArgs, "read", t_search, "mcp"),
        Tool("check_claim", "Test one claim against ONE named reference passage; returns supports, refutes or neutral.",
             CheckClaimArgs, "read", t_check, "mcp"),
        Tool("audit_document", "Audit an attached document by doc_id: guard, claims, evidence, verdicts, risk. Stops at the human gate; writes nothing.",
             AuditArgs, "compute", t_audit),
        Tool("get_audit_report", "Get the findings of an audit job, or the evidence for one claim_id.", ReportArgs, "read", t_report),
        Tool("request_publication", "Ask the human officer to review and sign publication of the certificate for an audited job. You cannot publish.",
             PublishArgs, "gated", t_publish),
    ]
    return {t.name: t for t in tools}
