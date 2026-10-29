"""The agent loop: model -> tool calls -> results -> model ... until an answer, an approval, or a limit.

Everything that keeps this safe and bounded is code here, not instructions to the model:
  * allow-list: a tool name that is not in the registry is refused and traced (blocked_tool);
  * arguments are validated with Pydantic before any tool runs; bad arguments come back as an error
    result so the model can correct itself;
  * budgets: iterations, tool calls, wall clock, session tokens, repeated identical calls;
  * context: old tool results are trimmed to stubs, old turns are compacted into a summary;
  * egress: the final text is scrubbed of links, images, tags and token-shaped strings;
  * the loop ends on `request_publication`: the human decides, the model does not continue.
Events are yielded as they happen, so a UI can show each step live.
"""
from __future__ import annotations

import json
import queue
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from typing import Iterator

from pydantic import ValidationError

from ..budget import compact, estimate_tokens
from ..config import data_dir
from ..graph import Auditor
from .config import AgentConfig
from .model import ChatModel, ModelReply, ModelUnavailable, OfflinePlanner, ToolsUnsupported
from .spec import build_system
from .store import Session, Store
from .tools import Tool, ToolContext, ToolFailure, default_registry, job_summary

_AR = re.compile(r"[؀-ۿ]")
_IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MDLINK = re.compile(r"\[([^\]]*)\]\(\s*(?:https?:)?//[^)]*\)")
_URL = re.compile(r"(?:https?:)?//[^\s)>\]]+|data:[^\s)]+", re.I)
_TAG = re.compile(r"</?\s*[a-zA-Z][^>]{0,200}>")
_TOKEN = re.compile(r"\b[A-Za-z0-9_-]{24,}\.[A-Za-z0-9_-]{20,}\b|\b0x[0-9a-fA-F]{16,}\b")


def scrub_output(text: str) -> tuple[str, bool]:
    """Egress filter for text that goes to the officer. A model that was talked into leaking data
    still cannot use markdown images or links to carry it out, and cannot print a signed token."""
    t = _IMG.sub("[image removed]", text or "")
    t = _MDLINK.sub(r"\1 [link removed]", t)
    t = _URL.sub("[link removed]", t)
    t = _TAG.sub("", t)
    t = _TOKEN.sub("[redacted]", t)
    return t.strip(), t.strip() != (text or "").strip()


def _msg_tokens(m: dict) -> int:
    n = estimate_tokens(m.get("content") or "")
    for c in m.get("tool_calls") or []:
        n += estimate_tokens(c["function"]["arguments"]) + 8
    return n + 4


def summarize(name: str, r: dict) -> str:
    if "error" in r:
        return f"error: {str(r['error'])[:120]}"
    if name == "audit_document":
        c = r.get("claim_counts", {})
        return f"risk {r.get('risk_score')}/100 · {c.get('contradicted', 0)} contradicted · {len(r.get('threats', []))} threats"
    if name == "search_regulations":
        return f"{len(r.get('results', []))} passages: " + ", ".join(h["id"] for h in r.get("results", [])[:3])
    if name == "check_claim":
        return f"{r.get('passage_id')}: {r.get('stance')}"
    if name == "get_audit_report":
        return f"claim {r['claim']['id']}: {r['claim']['status']}" if "claim" in r else f"risk {r.get('risk_score')}/100"
    if name == "request_publication":
        return "approval requested from the officer"
    if name == "load_skill":
        return f"skill {r.get('name')} loaded"
    return "ok"


class AgentLoop:
    def __init__(self, store: Store, auditor: Auditor, cfg: AgentConfig | None = None, model: ChatModel | None = None,
                 registry: dict[str, Tool] | None = None, live_pipeline: bool = False, trace_file: str | None = None):
        self.store, self.auditor, self.cfg = store, auditor, cfg or AgentConfig()
        self.model, self.registry = model, registry or default_registry()
        if not self.cfg.skills:
            self.registry = {k: v for k, v in self.registry.items() if k != "load_skill"}
        self.live_pipeline = live_pipeline
        self.planner = OfflinePlanner()
        self.trace_file = trace_file or str(data_dir() / "agent_traces.jsonl")
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="mijhar-tool")

    # ------------------------------------------------------------------ tracing
    def _trace(self, s: Session, span: str, op: str, ms: float, status: str = "ok", **attrs) -> None:
        rec = {"ts": round(time.time(), 3), "trace_id": s.id, "span": span, "gen_ai.operation.name": op,
               "ms": round(ms, 1), "status": status, "turn": s.usage["turns"]} | attrs
        try:
            with open(self.trace_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except OSError:
            pass

    # ------------------------------------------------------------------ context
    def _stub(self, m: dict) -> dict:
        try:
            r = json.loads(m["content"])
        except Exception:
            r = {}
        keep = {k: r[k] for k in ("job_id", "name", "status", "risk_score", "passage_id", "error") if k in r}
        return {**m, "content": json.dumps({"trimmed": True, "tool": m.get("x_name", ""), **keep}, ensure_ascii=False)}

    def _view(self, s: Session) -> tuple[list[dict], dict]:
        """Messages as the model will see them: summary first, older tool results trimmed to stubs."""
        last_user = max((i for i, m in enumerate(s.messages) if m["role"] == "user" and not m.get("x_harness")), default=0)
        tool_idx = [i for i, m in enumerate(s.messages) if m["role"] == "tool" and i < last_user]
        keep_from = set(tool_idx[-self.cfg.trim_keep_last:]) if self.cfg.trim_keep_last else set()
        out, trimmed = [], 0
        if s.summary:
            out.append({"role": "user", "content": "[CONTEXT SUMMARY of earlier turns]\n" + s.summary, "x_harness": True})
        for i, m in enumerate(s.messages):
            if i in tool_idx and i not in keep_from:
                out.append(self._stub(m)); trimmed += 1
            else:
                out.append(m)
        return out, {"trimmed": trimmed, "tokens": sum(_msg_tokens(m) for m in out) + 900}

    def _compact(self, s: Session) -> Iterator[dict]:
        before = sum(_msg_tokens(m) for m in s.messages) + 900
        starts = [i for i, m in enumerate(s.messages) if m["role"] == "user" and not m.get("x_harness")]
        dropped = 0
        while before > self.cfg.context_limit_tokens and len(starts) > 1:
            cut = starts[1]
            old = s.messages[:cut]
            names = [m.get("x_name") for m in old if m["role"] == "tool"]
            ask = next((m["content"] for m in old if m["role"] == "user" and not m.get("x_harness")), "")
            ans = next((m["content"] for m in reversed(old) if m["role"] == "assistant" and m.get("content")), "")
            jobs = sorted({j for m in old if m["role"] == "tool" for j in re.findall(r"JOB-[0-9a-f]{8}", m["content"])})
            s.summary = (s.summary + f"\n- officer: {ask[:160]} | tools: {', '.join(n for n in names if n) or 'none'}"
                         f"{' | jobs: ' + ', '.join(jobs) if jobs else ''} | answer: {ans[:200]}").strip()
            s.summary = compact(s.summary, 600)[0]
            s.messages = s.messages[cut:]
            starts = [i - cut for i in starts[1:]]
            before = sum(_msg_tokens(m) for m in s.messages) + 900
            dropped += 1
        if dropped:
            yield {"type": "context_compacted", "turns": dropped, "tokens": before, "limit": self.cfg.context_limit_tokens}

    # ------------------------------------------------------------------ model step
    def _think(self, s: Session, prefs: dict) -> Iterator[dict]:
        tools = [t.spec() for t in self.registry.values()]
        use_llm = s.planner == "llm" and self.model is not None
        while True:
            msgs, ctx = self._view(s)
            yield {"type": "context", "tokens": ctx["tokens"], "limit": self.cfg.context_limit_tokens, "trimmed": ctx["trimmed"],
                   "summary": bool(s.summary)}
            t0 = time.monotonic()
            if use_llm:
                try:
                    reply = self.model.complete(build_system(prefs, s.protocol, tools, self.cfg.skills), msgs, tools, s.protocol, run=s.id)
                except ToolsUnsupported as e:
                    s.protocol = "json"
                    yield {"type": "notice", "level": "warn", "text": "This model has no native tool calling; switched to the JSON tool protocol."}
                    continue
                except ModelUnavailable as e:
                    s.planner, use_llm = "offline", False
                    yield {"type": "notice", "level": "warn", "text": f"Model unavailable ({e}). Continuing with the offline planner."}
                    continue
            else:
                reply = self.planner.complete(build_system(prefs, "native", tools, self.cfg.skills), msgs, tools, "native", s.id)
            ms = (time.monotonic() - t0) * 1000
            self._trace(s, "model", "chat", ms, **{"gen_ai.request.model": reply.model, "gen_ai.usage.total_tokens": reply.tokens,
                                                   "gen_ai.tool_calls": len(reply.tool_calls), "protocol": reply.protocol})
            s.usage["model_calls"] += 1
            s.usage["tokens"] += reply.tokens or sum(_msg_tokens(m) for m in msgs[-2:]) + estimate_tokens(reply.content)
            yield {"type": "model_call", "planner": s.planner, "model": reply.model, "ms": round(ms), "tool_calls": len(reply.tool_calls),
                   "protocol": s.protocol if s.planner == "llm" else "offline", "cached": reply.cached, "tokens": reply.tokens}
            return reply

    # ------------------------------------------------------------------ tools
    def _exec(self, s: Session, tool: Tool, args, tc_id: str) -> Iterator[dict]:
        q: queue.Queue = queue.Queue()
        ctx = ToolContext(s, self.store, self.auditor, self.cfg, self.live_pipeline, emit=lambda e: q.put(e | {"id": tc_id}))
        done = object()
        fut = self.pool.submit(tool.fn, ctx, args)
        fut.add_done_callback(lambda _f: q.put(done))      # wake up the moment the tool finishes
        deadline = time.monotonic() + self.cfg.tool_seconds
        while True:
            left = deadline - time.monotonic()
            if left <= 0:
                return {"error": f"tool timed out after {self.cfg.tool_seconds:.0f}s"}
            try:
                item = q.get(timeout=min(left, 1.0))
            except queue.Empty:
                continue
            if item is done:
                break
            yield item
        while not q.empty():
            item = q.get_nowait()
            if item is not done:
                yield item
        try:
            return fut.result()
        except ToolFailure as e:
            return {"error": str(e)}
        except Exception as e:  # a crash in a tool is an error result, never a crash of the loop
            return {"error": f"{type(e).__name__}: {str(e)[:160]}"}

    def _cap(self, r: dict) -> str:
        text = json.dumps(r, ensure_ascii=False)
        if len(text) <= self.cfg.max_tool_result_chars:
            return text
        r = dict(r)
        for k in ("claims", "results", "evidence"):
            if isinstance(r.get(k), list):
                r[k] = r[k][:8]
        r["truncated"] = True
        text = json.dumps(r, ensure_ascii=False)
        return text if len(text) <= self.cfg.max_tool_result_chars else json.dumps({"truncated": True, "preview": text[:self.cfg.max_tool_result_chars - 60]})

    def _tool_step(self, s: Session, tc, seen: Counter, n_calls: int, skip: str | None) -> Iterator[dict]:
        """Runs one tool call and appends its tool message. Returns (executed_ok, flags)."""
        name = tc.name
        flags = {"stop": None}
        try:
            raw = json.loads(tc.arguments or "{}")
            if not isinstance(raw, dict):
                raise ValueError("arguments must be a JSON object")
        except ValueError as e:
            raw, bad = {}, f"arguments are not a valid JSON object: {e}"
        else:
            bad = None
        yield {"type": "tool_call", "id": tc.id, "name": name, "args": raw if isinstance(raw, dict) else {},
               "level": self.registry[name].level if name in self.registry else "unknown",
               "transport": self.registry[name].transport if name in self.registry else "-"}
        t0 = time.monotonic()
        res: dict
        status = "ok"
        tool = self.registry.get(name)
        if skip:
            res, status = {"error": skip}, "skipped"
        elif tool is None:
            res, status = {"error": f"unknown tool {name!r}. Available: {sorted(self.registry)}"}, "blocked"
            yield {"type": "blocked_tool", "name": name, "reason": "not in the allow-list"}
        elif bad:
            res, status = {"error": bad}, "error"
        else:
            try:
                args = tool.args.model_validate(raw)
            except ValidationError as e:
                msg = "; ".join(f"{'.'.join(map(str, x['loc'])) or 'args'}: {x['msg']}" for x in e.errors()[:3])
                res, status = {"error": f"invalid arguments: {msg}"}, "error"
            else:
                key = (name, json.dumps(raw, sort_keys=True, ensure_ascii=False))
                seen[key] += 1
                if seen[key] >= 3:
                    flags["stop"] = "loop_detected"
                    res, status = {"error": "same call repeated three times; stopping"}, "blocked"
                elif seen[key] == 2:
                    res, status = {"error": "duplicate call: reuse the earlier result instead of repeating it"}, "blocked"
                else:
                    s.usage["tool_calls"] += 1
                    res = yield from self._exec(s, tool, args, tc.id)
                    status = "error" if "error" in res else "ok"
        ms = (time.monotonic() - t0) * 1000
        content = self._cap(res)
        s.usage["tokens"] += estimate_tokens(content)
        s.messages.append({"role": "tool", "tool_call_id": tc.id, "content": content, "x_name": name})
        self._trace(s, f"tool:{name}", "execute_tool", ms, status, **{"gen_ai.tool.name": name})
        yield {"type": "tool_result", "id": tc.id, "name": name, "ok": status == "ok", "status": status, "ms": round(ms),
               "summary": summarize(name, res), "result": res if name != "audit_document" else {k: v for k, v in res.items() if k != "claims"}}
        if status == "ok" and name == "request_publication":
            flags["stop"] = "approval"
        return flags

    # ------------------------------------------------------------------ turn
    def approval_view(self, s: Session) -> dict:
        p = s.pending or {}
        snap = self.auditor.snapshot(p["job_id"])
        return {"job_id": p["job_id"], "report_sha256": p["report_sha256"], "risk_score": p.get("risk_score"),
                "quarantined": p.get("quarantined"), "note": p.get("note", ""),
                "threats": [{k: t[k] for k in ("rule", "attack", "severity", "snippet")} for t in snap.get("threats", [])],
                "claims": [{"id": c["id"], "text": c["text"][:300], "status": c["status"],
                            "evidence": [{"id": e["id"], "stance": e["stance"], "score": e["score"]} for e in c["evidence"][:2]]}
                           for c in snap.get("claims", [])],
                "internal_conflicts": snap.get("internal_conflicts", []), "filename": snap.get("filename", "")}

    def _harness_say(self, s: Session, text: str, ar: bool, key: str, **kw) -> str:
        msgs = {
            "approval": ("جهّزتُ طلب الاعتماد للمهمة {job}. راجع الملخص ووقّع قرارك من بطاقة الاعتماد. لن يُنشر شيء قبل توقيعك.",
                         "I prepared the approval request for job {job}. Review the summary and sign your decision on the approval card. Nothing is published before you sign."),
            "limit": ("توقفتُ لأني بلغت حد الخطوات المسموح في هذا الطلب. اكتب طلبك بصيغة أبسط أو قسّمه.",
                      "I stopped because I reached the step limit for this request. Rephrase it or split it into smaller asks."),
            "budget": ("وصلت هذه الجلسة إلى حد الاستهلاك المسموح. ابدأ جلسة جديدة للمتابعة.",
                       "This session reached its usage budget. Start a new session to continue."),
            "loop": ("أوقفتُ التنفيذ لأن الوكيل كرّر الاستدعاء نفسه. جرّب صياغة أخرى.", "I stopped because the agent kept repeating the same call. Try rephrasing."),
            "empty": ("ما وصلني رد من النموذج. أعد المحاولة.", "The model returned no answer. Please try again."),
            "timeout": ("استغرق الطلب أكثر من الوقت المسموح فأوقفته.", "The request took longer than allowed and was stopped."),
        }[key]
        return (msgs[0] if ar else msgs[1]).format(**kw)

    def run_turn(self, s: Session, user_content: str, prefs: dict) -> Iterator[dict]:
        cfg = self.cfg
        if s.usage["turns"] >= cfg.max_turns_per_session:
            yield {"type": "notice", "level": "error", "text": "Turn limit for this session reached."}
            yield {"type": "done", "reason": "turn_limit", "usage": s.usage}
            return
        s.usage["turns"] += 1
        ar = prefs.get("language") == "ar" or (prefs.get("language", "auto") == "auto" and bool(_AR.search(re.sub(r"\[Attached[^\]]*\]", "", user_content))))
        s.messages.append({"role": "user", "content": user_content})
        yield {"type": "turn_start", "turn": s.usage["turns"], "planner": s.planner}
        t_start, seen, n_calls, reason = time.monotonic(), Counter(), 0, "final"
        try:
            for _ in range(cfg.max_iterations):
                if time.monotonic() - t_start > cfg.turn_seconds:
                    reason = "timeout"
                    break
                if s.usage["tokens"] > cfg.session_token_budget:
                    reason = "budget"
                    break
                yield from self._compact(s)
                reply: ModelReply = yield from self._think(s, prefs)
                text, changed = scrub_output(reply.content) if cfg.scrub_output else (reply.content, False)
                if changed:
                    yield {"type": "notice", "level": "info", "text": "Links, images or token-like strings were removed from the reply."}
                am: dict = {"role": "assistant", "content": text}
                if reply.tool_calls:
                    am["tool_calls"] = [{"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}} for c in reply.tool_calls]
                if reply.extra:
                    am["x_extra"] = reply.extra
                s.messages.append(am)
                if not reply.tool_calls:
                    if not text:
                        reason, text = "empty", self._harness_say(s, "", ar, "empty")
                        s.messages[-1]["content"] = text
                    yield {"type": "final", "text": text, "author": "agent"}
                    break
                if text:
                    yield {"type": "assistant_text", "text": text}
                stop = None
                for tc in reply.tool_calls:
                    n_calls += 1
                    skip = None
                    if stop:
                        skip = "skipped: the turn is ending"
                    elif n_calls > cfg.max_tool_calls_per_turn:
                        skip = "tool call budget for this turn reached"
                    flags = yield from self._tool_step(s, tc, seen, n_calls, skip)
                    stop = stop or flags["stop"]
                if stop == "approval":
                    reason = "approval"
                    msg = self._harness_say(s, "", ar, "approval", job=s.pending["job_id"])
                    s.messages.append({"role": "assistant", "content": msg, "x_harness": True})
                    yield {"type": "approval_required", **self.approval_view(s)}
                    yield {"type": "final", "text": msg, "author": "harness"}
                    break
                if stop == "loop_detected":
                    reason = "loop_detected"
                    msg = self._harness_say(s, "", ar, "loop")
                    s.messages.append({"role": "assistant", "content": msg, "x_harness": True})
                    yield {"type": "final", "text": msg, "author": "harness"}
                    break
                if n_calls > cfg.max_tool_calls_per_turn:
                    reason = "tool_budget"
                    break
            else:
                reason = "iterations"
            if reason in ("timeout", "budget", "iterations", "tool_budget"):
                key = {"timeout": "timeout", "budget": "budget"}.get(reason, "limit")
                msg = self._harness_say(s, "", ar, key)
                s.messages.append({"role": "assistant", "content": msg, "x_harness": True})
                yield {"type": "final", "text": msg, "author": "harness"}
        finally:
            self.store.save(s)
        yield {"type": "done", "reason": reason, "usage": s.usage, "planner": s.planner}
