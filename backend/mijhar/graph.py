"""MIJHAR audit workflow as a LangGraph StateGraph (8 nodes, one human gate).

    ingest -> guardrail -> extract -> retrieve -> verify -> score -> hitl_gate -> commit

Properties enforced in code (tested in tests/ and measured in evals/):
  * the guardrail runs BEFORE any model sees the text; a guard failure ends the run (fail closed);
  * LLM nodes (extract, verify) are given no tools;
  * hitl_gate calls interrupt(); the run stops and is checkpointed to SQLite until a signed
    human decision arrives; the signature is verified here and again inside the write tool;
  * `commit` is reachable only through an approved, verified decision, and the write tool
    independently refuses anything else;
  * step and token budgets end the run with status "blocked" instead of continuing.
"""
from __future__ import annotations

import functools
import hashlib
import json
import operator
import sqlite3
import time
import uuid
from dataclasses import asdict
from typing import Annotated, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from . import guard, signing
from .budget import ALLOCATION, BudgetExceeded, ContextBudget, RunBudget, estimate_tokens
from .config import RunConfig, data_dir
from .documents import split_overlap
from .llm import LLM
from .reasoning import _overlap, extract_claims_rules, numbers
from .toolbox import ToolBox, ToolError

TERMINAL = {"blocked", "error", "rejected", "revise_requested", "refused", "committed"}


class State(TypedDict, total=False):
    job_id: str
    cfg: dict
    raw_text: str
    filename: str
    sha256: str
    chunks: list
    sanitized_text: str
    llm_input: str
    threats: list
    quarantined: bool
    claims: list
    internal_conflicts: list
    risk_score: int
    report: dict
    report_sha256: str
    hitl: dict
    commit: dict
    status: str
    error: str
    context_usage: dict
    budget: dict
    trace: Annotated[list, operator.add]


class Runtime:
    """Everything a node needs besides state. Injected so tests can swap the LLM or transport."""

    def __init__(self, toolbox: ToolBox | None = None, llm: LLM | None = None, trace_file: str | None = None):
        self.toolbox = toolbox or ToolBox(False)
        self.llm = llm
        self.trace_file = trace_file or str(data_dir() / "traces.jsonl")
        self.span_listeners: dict = {}     # job_id -> callback(span): lets the agent stream node progress


def canonical_hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def build_graph(rt: Runtime, checkpointer):
    def node(name: str):
        def deco(fn):
            @functools.wraps(fn)
            def wrapped(state: State):
                if state.get("status") in TERMINAL:
                    return {}
                cfg = RunConfig(**state["cfg"])
                b = state.get("budget") or {"steps": 0, "tokens": 0}
                t0 = time.perf_counter()
                try:
                    rb = RunBudget(cfg.max_steps, cfg.max_run_tokens, b["steps"], b["tokens"])
                    upd = fn(state, cfg) or {}
                    rb.tick(int(upd.pop("_tokens", 0)))
                    span = {"span": name, "status": "ok", "ms": round((time.perf_counter() - t0) * 1000, 1),
                            "gen_ai.operation.name": "execute_tool" if name in ("retrieve", "verify", "commit") else "workflow_node",
                            "tools": len(rt.toolbox.calls)}
                    upd["budget"] = {"steps": rb.steps, "tokens": rb.tokens}
                except BudgetExceeded as e:
                    upd, span = {"status": "blocked", "error": str(e)}, {"span": name, "status": "budget", "ms": 0}
                except Exception as e:
                    if type(e).__name__ == "GraphInterrupt":
                        raise
                    upd = {"status": "error", "error": f"{name}: {type(e).__name__}: {e}"}
                    span = {"span": name, "status": "error", "ms": round((time.perf_counter() - t0) * 1000, 1)}
                span["trace_id"] = state.get("job_id")
                cb = rt.span_listeners.get(state.get("job_id"))
                if cb:
                    try:
                        cb(span)
                    except Exception:   # a broken listener must never affect the audit
                        pass
                try:
                    with open(rt.trace_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(span) + "\n")
                except OSError:
                    pass
                upd["trace"] = [span]
                return upd
            return wrapped
        return deco

    # 1 ---------------------------------------------------------------- ingest
    @node("ingest")
    def ingest(s: State, cfg: RunConfig):
        raw = s.get("raw_text", "")
        if not isinstance(raw, str) or not raw.strip():
            return {"status": "blocked", "error": "empty document"}
        if len(raw) > cfg.max_doc_chars:
            return {"status": "blocked", "error": f"document exceeds {cfg.max_doc_chars} chars"}
        chunks = [{"offset": o, "chars": n} for o, n in split_overlap(raw)]   # 2000-char windows, 200 overlap
        return {"sha256": hashlib.sha256(raw.encode()).hexdigest(), "chunks": chunks, "_tokens": estimate_tokens(raw)}

    # 2 ------------------------------------------------------------- guardrail
    @node("guardrail")
    def guardrail(s: State, cfg: RunConfig):
        res = guard.scan(s["raw_text"], cfg.guard_level)
        if res.blocked:  # the guard itself failed: stop, never pass raw text on
            return {"status": "blocked", "error": f"guardrail failure: {res.error}"}
        return {"sanitized_text": res.sanitized_text, "threats": [asdict(t) for t in res.threats],
                "quarantined": res.quarantined}

    # 3 ---------------------------------------------------------------- extract
    @node("extract")
    def extract(s: State, cfg: RunConfig):
        cb = ContextBudget()
        text = cb.fit("document_chunks", s["sanitized_text"])
        claims = None
        if cfg.live_llm and rt.llm:
            claims = rt.llm.extract_claims(text, run=s["job_id"])      # tool-less call
        method = "llm" if claims is not None else "rules-v1"
        if claims is None:
            claims = extract_claims_rules(text)
        cb.fit("propositions", "\n".join(c["text"] for c in claims))
        return {"llm_input": text, "claims": [dict(c, extractor=method) for c in claims],
                "context_usage": dict(cb.used, events=cb.events), "_tokens": estimate_tokens(text)}

    # 4 --------------------------------------------------------------- retrieve
    @node("retrieve")
    def retrieve(s: State, cfg: RunConfig):
        claims, cb, tok = [], ContextBudget(), 0
        blob = []
        for c in s["claims"]:
            try:
                r = rt.toolbox.call("hybrid_search_docs", {"query": c["text"], "top_k": cfg.top_k, "mode": cfg.retrieval_mode})
                ev = [e for e in r["results"] if e["score"] >= cfg.min_hybrid_score]
                c = dict(c, evidence=ev, retrieval_error=None)
                blob.extend(e["text_en"] for e in ev)
            except ToolError as e:
                c = dict(c, evidence=[], retrieval_error=str(e)[:200])
            tok += estimate_tokens(c["text"])
            claims.append(c)
        cb.fit("regulatory_corpora", "\n".join(blob))
        usage = dict(s.get("context_usage") or {}, regulatory_corpora=cb.used.get("regulatory_corpora", 0))
        return {"claims": claims, "context_usage": usage, "_tokens": tok + usage["regulatory_corpora"]}

    # 5 ------------------------------------------------------------------ verify
    @node("verify")
    def verify(s: State, cfg: RunConfig):
        out, tok = [], 0
        for c in s["claims"]:
            evs = []
            for e in c["evidence"]:
                res = None
                if cfg.live_llm and rt.llm:
                    # both languages go to the judge: an Arabic claim must see the Arabic passage too
                    res = rt.llm.judge(c["text"], f"{e['text_en']}\n{e['text_ar']}", run=s["job_id"])   # tool-less call
                if res is None:
                    try:
                        res = rt.toolbox.call("verify_evidence", {"claim_text": c["text"], "reference_text": f"{e['text_en']} {e['text_ar']}"})
                    except ToolError as ex:
                        res = {"stance": "neutral", "rationale": f"verification failed: {ex}", "method": "error",
                               "contradiction_probability": 0.0}
                evs.append({"id": e["id"], "title_en": e["title_en"], "score": e["score"], "stance": res["stance"],
                            "rationale": res["rationale"], "method": res["method"], "overlap": res.get("overlap", 1.0)})
                tok += estimate_tokens(c["text"] + e["text_en"])
            stances = {x["stance"] for x in evs}
            best_sup = max((x["overlap"] for x in evs if x["stance"] == "supports"), default=-1.0)
            if c.get("retrieval_error"):
                status = "inconclusive"
            elif not evs:
                status = "unsubstantiated"
            elif any(x["stance"] == "refutes" and x["overlap"] >= best_sup - 0.2 for x in evs):
                # a refutation from a passage clearly less on-topic than a supporting one does not override it
                status = "contradicted"
            elif "supports" in stances:
                status = "verified"
            else:
                status = "inconclusive"
            out.append({k: v for k, v in c.items() if k != "evidence"} | {"status": status, "evidence": evs})
        return {"claims": out, "_tokens": tok}

    # 6 ------------------------------------------------------------------- score
    @node("score")
    def score(s: State, cfg: RunConfig):
        claims = s["claims"]
        conflicts = []
        for i in range(len(claims)):
            for j in range(i + 1, len(claims)):
                a, b = claims[i], claims[j]
                if _overlap(a["text"], b["text"]) >= 0.5:
                    na, nb = numbers(a["text"]), numbers(b["text"])
                    for g in {x for x, _ in na} & {x for x, _ in nb}:
                        if {v for x, v in na if x == g}.isdisjoint({v for x, v in nb if x == g}):
                            conflicts.append({"claims": [a["id"], b["id"]], "unit": g})
                            break
        th = s.get("threats", [])
        sev = lambda k: sum(1 for t in th if t["severity"] == k)  # noqa: E731
        st = lambda k: sum(1 for c in claims if c["status"] == k)  # noqa: E731
        risk = min(100, 35 * sev("critical") + 15 * sev("high") + 6 * sev("medium") + 14 * st("contradicted")
                   + 3 * st("unsubstantiated") + 1 * st("inconclusive") + 10 * len(conflicts))
        return {"risk_score": risk, "internal_conflicts": conflicts}

    # 7 ---------------------------------------------------------------- hitl_gate
    @node("hitl_gate")
    def hitl_gate(s: State, cfg: RunConfig):
        report = {
            "job_id": s["job_id"], "document_sha256": s["sha256"], "filename": s.get("filename", ""),
            "guard_level": cfg.guard_level, "retrieval_mode": cfg.retrieval_mode,
            "threats": [{k: t[k] for k in ("rule", "attack", "severity", "snippet")} for t in s.get("threats", [])],
            "claims": [{"id": c["id"], "text": c["text"], "status": c["status"],
                        "evidence": [{k: e[k] for k in ("id", "stance", "score")} for e in c["evidence"]]} for c in s["claims"]],
            "internal_conflicts": s.get("internal_conflicts", []), "risk_score": s["risk_score"],
            "pending_action": {"action": "PUBLISH_CERTIFICATE", "registry": "national_audit_registry"},
        }
        rsha = canonical_hash(report)
        # Execution stops here. The checkpoint holds the whole state until a human decision is resumed in.
        answer = interrupt({"job_id": s["job_id"], "report_sha256": rsha, "risk_score": s["risk_score"],
                            "message": "awaiting signed human decision"})
        base = {"report": report, "report_sha256": rsha}
        try:
            token = (answer or {}).get("token", "")
            p = signing.parse_token(token)
            if p["job_id"] != s["job_id"] or p["report_sha256"] != rsha:
                raise signing.SignatureError("token does not match this job/report")
        except signing.SignatureError as e:
            return base | {"status": "refused", "error": f"human decision rejected by harness: {e}",
                           "hitl": {"verified": False}}
        hitl = {"verified": True, "decision": p["decision"], "reviewer": p["reviewer"], "token": token}
        status = {"approve": "approved", "reject": "rejected", "revise": "revise_requested"}[p["decision"]]
        return base | {"hitl": hitl, "status": status}

    # 8 -------------------------------------------------------------------- commit
    @node("commit")
    def commit(s: State, cfg: RunConfig):
        try:
            r = rt.toolbox.call("execute_audit_action", {
                "decision_token": s["hitl"]["token"], "action": "PUBLISH_CERTIFICATE", "job_id": s["job_id"],
                "report_sha256": s["report_sha256"], "target_registry": "national_audit_registry"})
        except ToolError as e:
            return {"status": "refused", "error": f"write tool refused: {e}"}
        return {"commit": r, "status": "committed"}

    g = StateGraph(State)
    for name, fn in [("ingest", ingest), ("guardrail", guardrail), ("extract", extract), ("retrieve", retrieve),
                     ("verify", verify), ("score", score), ("hitl_gate", hitl_gate), ("commit", commit)]:
        g.add_node(name, fn)
    order = ["ingest", "guardrail", "extract", "retrieve", "verify", "score", "hitl_gate"]
    g.add_edge(START, "ingest")
    for a, b in zip(order, order[1:]):
        g.add_conditional_edges(a, lambda s, nxt=b: END if s.get("status") in TERMINAL else nxt, [b, END])
    g.add_conditional_edges("hitl_gate", lambda s: "commit" if s.get("status") == "approved" else END, ["commit", END])
    g.add_edge("commit", END)
    return g.compile(checkpointer=checkpointer)


def make_checkpointer(path: str | None = None) -> SqliteSaver:
    return SqliteSaver(sqlite3.connect(path or str(data_dir() / "checkpoints.sqlite"), check_same_thread=False))


class Auditor:
    """Convenience wrapper: start a run (stops at the human gate) and resume with a signed decision."""

    def __init__(self, rt: Runtime | None = None, checkpoint_path: str | None = None):
        self.rt = rt or Runtime()
        self.graph = build_graph(self.rt, make_checkpointer(checkpoint_path))

    @staticmethod
    def _cfg(job_id: str):
        return {"configurable": {"thread_id": job_id}}

    def start(self, text: str, filename: str = "document.txt", cfg: RunConfig | None = None, job_id: str | None = None) -> dict:
        job_id = job_id or f"JOB-{uuid.uuid4().hex[:8]}"
        self.graph.invoke({"job_id": job_id, "cfg": (cfg or RunConfig()).to_dict(), "raw_text": text,
                           "filename": filename, "trace": []}, self._cfg(job_id))
        return self.snapshot(job_id)

    def snapshot(self, job_id: str) -> dict:
        snap = self.graph.get_state(self._cfg(job_id))
        v = dict(snap.values)
        v["awaiting_human"] = tuple(snap.next) == ("hitl_gate",)
        if v["awaiting_human"] and not v.get("status"):
            v["status"] = "awaiting_human"
        return v

    def pending_report_hash(self, job_id: str) -> str | None:
        for t in self.graph.get_state(self._cfg(job_id)).tasks:
            for i in getattr(t, "interrupts", ()):
                return i.value.get("report_sha256")
        return None

    def resume(self, job_id: str, token: str) -> dict:
        self.graph.invoke(Command(resume={"token": token}), self._cfg(job_id))
        return self.snapshot(job_id)
