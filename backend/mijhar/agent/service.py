"""AgentService: sessions, documents, turns and the human decision, with no web framework in sight.

The HTTP layer (web.py) and the CLI (`mijhar chat`) are thin wrappers over this class, so everything
important is testable without a server.
"""
from __future__ import annotations

import re
import threading
import time
from pathlib import Path
from typing import Iterator

from .. import guard, signing
from ..config import ConfigError, env
from ..graph import Auditor
from .config import AgentConfig
from .loop import AgentLoop
from .model import ChatModel
from .store import Session, Store, StoreError
from .tools import Tool

_AR = re.compile(r"[؀-ۿ]")
BENCH = Path(__file__).resolve().parent.parent / "data" / "benchmarks"
MAX_MESSAGE_CHARS = 4_000


class ServiceError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


class AgentService:
    def __init__(self, auditor: Auditor, store: Store | None = None, cfg: AgentConfig | None = None,
                 model: ChatModel | None = None, live_pipeline: bool = False, registry: dict[str, Tool] | None = None):
        self.auditor, self.cfg = auditor, cfg or AgentConfig()
        self.store = store or Store()
        self.model = model
        self.loop = AgentLoop(self.store, auditor, self.cfg, model, registry, live_pipeline)
        self._busy: dict[str, float] = {}
        self._mx = threading.Lock()

    @classmethod
    def from_env(cls, auditor: Auditor, **kw) -> "AgentService":
        """The real model is used only when the operator opted in (MIJHAR_ALLOW_LIVE=1) AND a key is set:
        tool results (claim excerpts) go to the provider, outside the Kingdom."""
        model, live = None, False
        if env("MIJHAR_ALLOW_LIVE", "0") == "1" and env("OPENROUTER_API_KEY"):
            try:
                model = ChatModel()
                # MIJHAR_PIPELINE_LLM=0 keeps the audit pipeline on rules-v1 while the agent uses the model
                # (saves ~15 free requests per audit).
                live = (env("MIJHAR_PIPELINE_LLM", "1") or "1") == "1"
                if live and auditor.rt.llm is None:
                    from ..llm import LLM
                    auditor.rt.llm = LLM()
            except RuntimeError:
                model, live = None, False
        return cls(auditor, model=model, live_pipeline=live, **kw)

    # ------------------------------------------------------------------ info
    def capabilities(self) -> dict:
        llm = bool(self.model and not self.model.dead)
        return {"planner": "llm" if llm else "offline", "model": (self.model.model if llm else "offline-rules"),
                "mcp": bool(self.auditor.rt.toolbox.use_mcp), "live_pipeline": bool(self.loop.live_pipeline),
                "tools": [{"name": t.name, "level": t.level, "transport": t.transport} for t in self.loop.registry.values()],
                "limits": {"iterations": self.cfg.max_iterations, "tool_calls": self.cfg.max_tool_calls_per_turn,
                           "session_tokens": self.cfg.session_token_budget, "context_tokens": self.cfg.context_limit_tokens},
                "reason": (self.model.dead if self.model and self.model.dead else
                           (None if llm else "no OPENROUTER_API_KEY, or MIJHAR_ALLOW_LIVE is not 1"))}

    def samples(self) -> list[str]:
        return sorted(p.stem for p in BENCH.glob("*.md"))

    # ------------------------------------------------------------------ sessions
    def new_session(self, client: str) -> Session:
        if self.store.count(client) >= self.cfg.max_sessions_per_client:
            raise ServiceError(429, "session limit reached for this key")
        s = self.store.create(client)
        s.planner = "llm" if self.model and not self.model.dead else "offline"
        self.store.save(s)
        return s

    def _get(self, sid: str, client: str) -> Session:
        s = self.store.get(sid, client)
        if not s:
            raise ServiceError(404, "unknown session")
        return s

    def view(self, sid: str, client: str) -> dict:
        s = self._get(sid, client)
        return {"id": s.id, "planner": s.planner, "protocol": s.protocol, "usage": s.usage, "docs": self.store.list_docs(s.id),
                "events": s.events[-300:], "pending": self.loop.approval_view(s) if s.pending else None,
                "prefs": self.store.prefs(client), "jobs": s.jobs}

    def add_document(self, sid: str, client: str, name: str = "", text: str | None = None, sample: str | None = None) -> dict:
        s = self._get(sid, client)
        if sample:
            if sample not in self.samples():
                raise ServiceError(404, f"unknown sample {sample!r}")
            text, name = (BENCH / f"{sample}.md").read_text(encoding="utf-8"), f"{sample}.md"
        try:
            meta = self.store.add_doc(s.id, name or "document.txt", text or "")
        except StoreError as e:
            raise ServiceError(422, str(e))
        s.events.append({"type": "document", "doc": meta})
        self.store.save(s)
        return meta

    # ------------------------------------------------------------------ turns
    def _acquire(self, sid: str) -> None:
        with self._mx:
            t = self._busy.get(sid)
            stale = self.cfg.turn_seconds + self.cfg.tool_seconds + 30
            if t and time.monotonic() - t < stale:
                raise ServiceError(409, "a turn is already running in this session")
            self._busy[sid] = time.monotonic()

    def _release(self, sid: str) -> None:
        with self._mx:
            self._busy.pop(sid, None)

    def turn(self, sid: str, client: str, text: str) -> Iterator[dict]:
        """Validates and returns the event stream. Raises ServiceError before streaming starts."""
        s = self._get(sid, client)
        text = (text or "").strip()
        if not text:
            raise ServiceError(422, "empty message")
        self._acquire(sid)
        try:
            shown = text
            # Chat text gets the same guard as uploads: if it is long, or the guard flags it, it is treated
            # as a document (vaulted) and never placed in the model context.
            flagged = guard.scan(text).quarantined if self.cfg.paste_to_vault else False
            if self.cfg.paste_to_vault and (len(text) > self.cfg.paste_threshold_chars or flagged):
                try:
                    meta = self.store.add_doc(s.id, "pasted-text.txt", text)
                except StoreError as e:
                    raise ServiceError(422, str(e))
                s.events.append({"type": "document", "doc": meta})
                text = "(long text attached)"
                shown = text
            elif len(text) > MAX_MESSAGE_CHARS:
                raise ServiceError(422, f"message exceeds {MAX_MESSAGE_CHARS} characters; attach it as a document")
            notes = []
            for d in self.store.list_docs(s.id):
                if d["doc_id"] not in s.announced_docs:
                    s.announced_docs.append(d["doc_id"])
                    notes.append(f"[Attached document {d['doc_id']} «{d['name']}», {d['chars']} chars]")
            content = text + ("\n" + "\n".join(notes) if notes else "")
            prefs = self.store.prefs(client)
        except Exception:
            self._release(sid)
            raise
        return self._stream(s, content, shown, prefs)

    def _stream(self, s: Session, content: str, shown: str, prefs: dict) -> Iterator[dict]:
        try:
            s.events.append({"type": "user", "text": shown})
            for ev in self.loop.run_turn(s, content, prefs):
                s.events.append(ev)
                yield ev
        finally:
            self.store.save(s)
            self._release(s.id)

    def run_turn_blocking(self, sid: str, client: str, text: str) -> list[dict]:
        return list(self.turn(sid, client, text))

    # ------------------------------------------------------------------ human decision
    def decide(self, sid: str, client: str, reviewer: str, reviewer_key: str, decision: str, report_sha256: str) -> list[dict]:
        s = self._get(sid, client)
        if decision not in ("approve", "reject", "revise"):
            raise ServiceError(422, "decision must be approve, reject or revise")
        if not s.pending:
            raise ServiceError(409, "no approval is pending in this session")
        self._acquire(sid)
        try:
            job = s.pending["job_id"]
            pending = self.auditor.pending_report_hash(job)
            if pending is None:
                s.pending = None
                self.store.save(s)
                raise ServiceError(409, "job is not awaiting a human decision")
            if report_sha256 != pending:
                raise ServiceError(409, "report changed since you reviewed it")
            try:
                token = signing.issue_decision_token(job, decision, reviewer, reviewer_key or "", pending)
            except signing.SignatureError:
                raise ServiceError(403, "reviewer authentication failed")
            except ConfigError as e:
                raise ServiceError(503, str(e))
            snap = self.auditor.resume(job, token)
            status, commit = snap.get("status"), snap.get("commit") or {}
            ar = any(_AR.search(m["content"]) for m in s.messages[-6:] if m["role"] == "user" and isinstance(m.get("content"), str) and not m.get("x_harness"))
            text = self._decision_text(ar, decision, status, reviewer, commit, snap.get("error"), job)
            s.pending = None
            ev = [{"type": "decision", "job_id": job, "decision": decision, "status": status, "reviewer": reviewer,
                   "tx_hash": commit.get("tx_hash"), "timestamp": commit.get("timestamp")},
                  {"type": "final", "text": text, "author": "harness"}]
            s.messages += [{"role": "user", "content": f"[HARNESS EVENT] decision={decision} status={status} job={job} tx={commit.get('tx_hash', '-')}", "x_harness": True},
                           {"role": "assistant", "content": text, "x_harness": True}]
            s.events += ev
            self.store.save(s)
            return ev
        finally:
            self._release(sid)

    @staticmethod
    def _decision_text(ar: bool, decision: str, status: str, reviewer: str, commit: dict, err: str | None, job: str) -> str:
        if status == "committed":
            return (f"تم الاعتماد: سجّل {reviewer} قراره في السجل المترابط (COMMITTED). المعاملة {commit.get('tx_hash', '')[:16]}…" if ar
                    else f"Approved and COMMITTED: {reviewer}'s signed decision is in the hash-chained ledger. Transaction {commit.get('tx_hash', '')[:16]}…")
        if status == "rejected":
            return "سجّلتُ رفضك. لم يُكتب شيء في السجل." if ar else "Your rejection is recorded. Nothing was written to the ledger."
        if status == "revise_requested":
            return "سجّلتُ طلب المراجعة. لم يُكتب شيء في السجل." if ar else "Revision requested. Nothing was written to the ledger."
        return (f"رفض النظام الكتابة: {err or status}" if ar else f"The system refused to write: {err or status}")
