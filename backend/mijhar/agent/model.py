"""Models that drive the agent loop.

 ChatModel      OpenRouter chat.completions with native tool calling; falls back to a JSON text protocol
                when the model has no tool support. Hardened like llm.LLM: no retry on 401/403, counted
                retries, per-run request cap, optional fallback model, failures surface as exceptions.
 OfflinePlanner a deterministic policy with the same interface. It lets the whole system run with no
                key and no network (demo backup, CI, evals of the harness). It is NOT a language model:
                the UI and the CLI label it "offline planner".
"""
from __future__ import annotations

import json
import re
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from .. import cache
from ..config import OpenRouterSettings, env
from ..llm import _first_json, _status

_ARABIC = re.compile(r"[؀-ۿ]")


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str          # JSON text, exactly as the model produced it


@dataclass
class ModelReply:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens: int = 0
    model: str = ""
    protocol: str = "native"
    extra: dict = field(default_factory=dict)   # provider fields some models need back (reasoning_details, ...)
    cached: bool = False


class ModelUnavailable(RuntimeError):
    """Provider unreachable, key rejected, request cap hit: the loop degrades to the offline planner."""


class ToolsUnsupported(RuntimeError):
    """The model/provider cannot do native tool calling: the loop switches to the JSON protocol."""


def clean_messages(messages: list[dict]) -> list[dict]:
    out = []
    for m in messages:
        d = {k: v for k, v in m.items() if not k.startswith("x_")}
        if m.get("x_extra"):
            d |= m["x_extra"]                      # hand reasoning fields back, as the provider expects
        if d.get("role") == "assistant" and d.get("tool_calls") and not d.get("content"):
            d["content"] = None
        out.append(d)
    return out


def json_messages(messages: list[dict]) -> list[dict]:
    """Native tool-call transcript -> plain text turns for a model without tool support."""
    out = []
    for m in messages:
        if m["role"] == "assistant" and m.get("tool_calls"):
            calls = [{"tool": c["function"]["name"], "args": json.loads(c["function"]["arguments"] or "{}")} for c in m["tool_calls"]]
            out.append({"role": "assistant", "content": json.dumps(calls[0], ensure_ascii=False)})
        elif m["role"] == "tool":
            out.append({"role": "user", "content": f"TOOL_RESULT {m.get('x_name', '')}: {m['content']}"})
        else:
            out.append({"role": m["role"], "content": m.get("content") or ""})
    return out


# Same choice as the course's agentkit (free models WITH tool calling, checked on
# openrouter.ai/models?max_price=0&supported_parameters=tools). Free lists change: override with env vars.
DEFAULT_AGENT_MODEL = "google/gemma-4-31b-it:free"
DEFAULT_AGENT_FALLBACKS = "google/gemma-4-26b-a4b-it:free,nvidia/nemotron-3-super-120b-a12b:free"
_KEEP_EXTRA = ("reasoning", "reasoning_details", "reasoning_content")


class ChatModel:
    name = "llm"

    def __init__(self, settings: OpenRouterSettings | None = None, client=None, max_calls: int | None = None,
                 sleep=time.sleep, use_cache: bool | None = None):
        self.s = settings or OpenRouterSettings()
        if client is None:
            if not self.s.api_key:
                raise RuntimeError("OPENROUTER_API_KEY not set")
            from openai import OpenAI
            client = OpenAI(base_url=self.s.base_url, api_key=self.s.api_key, timeout=90, max_retries=0,
                            default_headers={"X-OpenRouter-Title": "MIJHAR audit agent"})
        self.client, self._sleep = client, sleep
        self.model = env("MIJHAR_AGENT_MODEL") or DEFAULT_AGENT_MODEL
        fb = env("MIJHAR_AGENT_FALLBACKS", DEFAULT_AGENT_FALLBACKS) or ""
        self.or_fallbacks = [m.strip() for m in fb.split(",") if m.strip() and m.strip() != self.model]
        self.openrouter = "openrouter.ai" in (self.s.base_url or "")
        self.fallback = self.s.fallback_model
        self.max_calls = int(max_calls or env("MIJHAR_AGENT_MAX_CALLS", "60") or 60)
        self.max_tokens = int(env("MIJHAR_AGENT_MAX_TOKENS", "2048") or 2048)
        self.use_cache = cache.enabled() if use_cache is None else use_cache
        self.calls, self.ok, self.failed, self.cache_hits = 0, 0, 0, 0
        self.run_calls: dict[str, int] = defaultdict(int)
        self.dead: str | None = None
        self.last_error: str | None = None
        self.model_used: str | None = None
        self._net_fail = 0

    def _models(self) -> list[str]:
        return [self.model] + ([self.fallback] if self.fallback and self.fallback != self.model else [])

    def _request(self, model, system, messages, tools, protocol) -> tuple[dict, bool]:
        msgs = [{"role": "system", "content": system}] + (clean_messages(messages) if protocol == "native" else json_messages(messages))
        req = dict(model=model, temperature=0, max_tokens=self.max_tokens, messages=msgs)
        if protocol == "native":
            req |= {"tools": tools, "tool_choice": "auto"}
        extra = {"models": [model] + self.or_fallbacks} if self.openrouter and self.or_fallbacks else None
        k = cache.key("agent-chat", req | {"extra": extra})
        if self.use_cache and (hit := cache.get(k)):
            return hit, True
        r = self.client.chat.completions.create(**req, **({"extra_body": extra} if extra else {}))
        msg = r.choices[0].message
        dump = msg.model_dump(exclude_none=True) if hasattr(msg, "model_dump") else {}
        u = getattr(r, "usage", None)
        data = {"content": (getattr(msg, "content", None) or "").strip(), "model": getattr(r, "model", None) or model,
                "tokens": int(getattr(u, "total_tokens", 0) or 0),
                "tool_calls": [{"id": getattr(tc, "id", None) or f"call_{uuid.uuid4().hex[:8]}", "name": tc.function.name,
                                "arguments": tc.function.arguments or "{}"} for tc in (getattr(msg, "tool_calls", None) or [])],
                "extra": {x: dump[x] for x in _KEEP_EXTRA if x in dump}}
        if self.use_cache:
            cache.put(k, data)
        return data, False

    def complete(self, system: str, messages: list[dict], tools: list[dict], protocol: str = "native", run: str = "default") -> ModelReply:
        if self.dead:
            raise ModelUnavailable(self.dead)
        last: Exception | None = None
        for model in self._models():
            for attempt in range(3):
                if self.run_calls[run] >= self.max_calls:
                    raise ModelUnavailable(f"model request cap reached for this session ({self.max_calls})")
                try:
                    data, hit = self._request(model, system, messages, tools, protocol)
                except Exception as e:
                    self.run_calls[run] += 1
                    self.calls += 1
                    last, code = e, _status(e)
                    self.failed += 1
                    self.last_error = f"{type(e).__name__}: {str(e)[:160]}"
                    if code is None:
                        self._net_fail += 1
                        if self._net_fail >= 3 and self.ok == 0:
                            self.dead = f"provider unreachable ({self.last_error})"
                            raise ModelUnavailable(self.dead) from e
                    if code in (401, 403):
                        self.dead = f"authentication failed (HTTP {code})"
                        raise ModelUnavailable(self.dead) from e
                    if code == 429 and re.search(r"per-day|per day|daily", str(e), re.I):
                        # the DAILY free quota is gone: retrying or switching free models only burns requests
                        self.dead = "daily free-model quota used up (OpenRouter 429); add credits or wait until tomorrow"
                        raise ModelUnavailable(self.dead) from e
                    if protocol == "native" and code in (400, 404, 422) and re.search(r"tool|function", str(e), re.I):
                        raise ToolsUnsupported(self.last_error) from e
                    if code in (400, 422):
                        raise ModelUnavailable(f"provider rejected the request (HTTP {code}): {self.last_error}") from e
                    if code == 404:
                        break                      # model removed: try the fallback model
                    if attempt < 2:
                        self._sleep(min(2 ** (attempt + 1), 8))
                    continue
                if hit:
                    self.cache_hits += 1
                else:
                    self.run_calls[run] += 1
                    self.calls += 1
                self._net_fail, self.ok, self.model_used = 0, self.ok + 1, data["model"]
                return self._parse(data, protocol, hit)
        raise ModelUnavailable(f"model call failed on {', '.join(self._models())}: {last}")

    @staticmethod
    def _parse(d: dict, protocol: str, hit: bool) -> ModelReply:
        text, tokens, model = d["content"], d["tokens"], d["model"]
        if protocol == "native":
            return ModelReply(text, [ToolCall(c["id"], c["name"], c["arguments"]) for c in d["tool_calls"]], tokens, model,
                              protocol, d.get("extra") or {}, hit)
        try:
            obj = _first_json(text, "tool")
            return ModelReply("", [ToolCall(f"call_{uuid.uuid4().hex[:8]}", str(obj["tool"]), json.dumps(obj.get("args") or {}, ensure_ascii=False))],
                              tokens, model, protocol, cached=hit)
        except ValueError:
            pass
        try:
            return ModelReply(str(_first_json(text, "final")["final"]), [], tokens, model, protocol, cached=hit)
        except (ValueError, KeyError):
            return ModelReply(text, [], tokens, model, protocol, cached=hit)


# ============================================================================== offline planner
_PUBLISH = re.compile(r"publish|approve|certif|\bsign\b|اعتمد|اعتماد|انشر|نشر|شهاد|وقع|توقيع", re.I)
_AUDIT = re.compile(r"audit|check|review|scan|verify|تدقيق|دقق|دقّق|افحص|فحص|راجع|تحقق", re.I)
_CLAIM = re.compile(r"CLM-\d{3}", re.I)
_DOC = re.compile(r"DOC-[0-9a-f]{8}")
_NOTE = re.compile(r"\[Attached[^\]]*\]")
_LANG_PREF = re.compile(r"- language: (\w+)")

_ST_AR = {"contradicted": "متناقض", "unsubstantiated": "بلا سند", "verified": "مؤكَّد", "inconclusive": "غير حاسم"}
_STANCE_AR = {"supports": "يدعم", "refutes": "ينقض", "neutral": "محايد"}


def _claim_text(wrapped: str) -> str:
    return re.sub(r"<[^>]+>", "", wrapped or "").strip()


class OfflinePlanner:
    name = "offline-rules"
    model = "offline-rules"

    # ---- helpers over the transcript
    @staticmethod
    def _parse(m: dict) -> dict:
        try:
            return json.loads(m["content"])
        except Exception:
            return {}

    def complete(self, system: str, messages: list[dict], tools: list[dict], protocol: str = "native", run: str = "default") -> ModelReply:
        last_user = max((i for i, m in enumerate(messages) if m["role"] == "user" and not m.get("x_harness")), default=-1)
        text = messages[last_user].get("content", "") if last_user >= 0 else ""
        this_turn = [(m.get("x_name", ""), self._parse(m)) for m in messages[last_user + 1:] if m["role"] == "tool"]
        prior = [(m.get("x_name", ""), self._parse(m)) for m in messages[:last_user + 1] if m["role"] == "tool"]
        all_res = prior + this_turn
        pref = (_LANG_PREF.search(system) or [None, "auto"])[1]
        ar = pref == "ar" or (pref == "auto" and bool(_ARABIC.search(_NOTE.sub("", text))))
        detailed = "detail: detailed" in system
        body = _NOTE.sub("", text).strip()
        job = next((r["job_id"] for n, r in reversed(all_res) if n == "audit_document" and r.get("job_id")), None)
        docs = _DOC.findall(" ".join(m.get("content", "") for m in messages if m["role"] == "user" and isinstance(m.get("content"), str)))
        doc_now = (_DOC.findall(text) or [None])[0]
        skills_loaded = {r.get("name") for n, r in prior if n == "load_skill"}

        if this_turn and "error" in this_turn[-1][1]:
            return ModelReply(self._say(ar, "err", this_turn[-1][1]["error"]), model=self.model)

        if "Skill index" not in system:          # skills switched off (eval config A): never plan load_skill
            skills_loaded = {"explain-claim", "publication-approval", "audit-document", "regulation-lookup"}
        steps = self._steps(body, text, job, docs, doc_now, skills_loaded)
        k = len(this_turn)
        if k < len(steps):
            name, args = steps[k]
            return ModelReply("", [ToolCall(f"call_{uuid.uuid4().hex[:8]}", name, json.dumps(args))], model=self.model)
        return ModelReply(self._final(ar, detailed, this_turn, body, job), model=self.model)

    def _steps(self, body, text, job, docs, doc_now, loaded) -> list[tuple[str, dict]]:
        def skill(n):
            return [] if n in loaded else [("load_skill", {"name": n})]
        if _CLAIM.search(body) and job:
            return skill("explain-claim") + [("get_audit_report", {"job_id": job, "claim_id": _CLAIM.search(body).group(0).upper()})]
        if _PUBLISH.search(body) and job:
            return skill("publication-approval") + [("request_publication", {"job_id": job, "note": "requested by the officer"})]
        if doc_now or (docs and _AUDIT.search(body)):
            return skill("audit-document") + [("audit_document", {"doc_id": doc_now or docs[-1]})]
        if _PUBLISH.search(body):
            return []
        if len(body) >= 3 and (re.search(r"[?؟]|what|which|how|when|must|should|ما |ماذا|كم|هل|متى|كيف|يجب|متطلب", body, re.I)):
            return skill("regulation-lookup") + [("search_regulations", {"query": body[:400]})]
        return []

    # ---- answers
    def _say(self, ar: bool, key: str, arg: str = "") -> str:
        t = {
            "err": ("تعذّر تنفيذ الخطوة: {a}", "The step failed: {a}"),
            "nojob": ("ما فيه تدقيق مكتمل بعد. أرفق مستنداً وأطلب مني تدقيقه، ثم أرفع لك طلب الاعتماد.",
                      "There is no completed audit yet. Attach a document and ask me to audit it; then I can request approval."),
            "help": ("أنا مِجهر. أرفق مستنداً لأدققه، أو اسألني عن مادة في الأنظمة المرجعية (مثال: كم مدة الإبلاغ عن الحوادث؟).",
                     "I am MIJHAR. Attach a document and I will audit it, or ask what the reference regulations say (for example: how long to report incidents?)."),
        }[key]
        return (t[0] if ar else t[1]).format(a=arg)

    def _final(self, ar: bool, detailed: bool, res: list, body: str, job: str | None) -> str:
        if not res:
            return self._say(ar, "nojob" if _PUBLISH.search(body) else "help")
        name, r = res[-1]
        if name == "audit_document":
            return self._audit_text(ar, detailed, r)
        if name == "search_regulations":
            hits = r.get("results", [])
            if not hits:
                return "لم أجد مادة مرجعية مطابقة لسؤالك." if ar else "No reference passage matched your question."
            lines = [f"• {h['id']} — {h['title_ar' if ar else 'title_en']}: {h['text_ar' if ar else 'text_en']}" for h in hits[:3]]
            tail = "المراجع اصطناعية للتجربة وليست نصاً نظامياً." if ar else "The corpora are synthetic benchmark text, not official law."
            return "\n".join(lines + ["", tail])
        if name == "get_audit_report" and "claim" in r:
            c = r["claim"]
            ev = [f"• {e['id']}: {_STANCE_AR[e['stance']] if ar else e['stance']} (score {e['score']})" for e in r["evidence"]] or ["• —"]
            head = (f"{c['id']} حالته {_ST_AR[c['status']]}: «{_claim_text(c['text'])}»" if ar else f"{c['id']} is {c['status']}: \"{_claim_text(c['text'])}\"")
            return "\n".join([head, *ev])
        if name == "request_publication":
            return ""
        if name == "load_skill":
            return self._say(ar, "help")
        return json.dumps(r, ensure_ascii=False)[:500]

    def _audit_text(self, ar: bool, detailed: bool, r: dict) -> str:
        cc = r.get("claim_counts", {})
        notable = [c for c in r.get("claims", []) if detailed or c["status"] in ("contradicted", "unsubstantiated")][:8]
        lines = []
        for c in notable:
            ev = next((e["id"] for e in c["evidence"] if e["stance"] == "refutes"), None) or (c["evidence"][0]["id"] if c["evidence"] else "")
            if ar:
                lines.append(f"• {c['id']} ({_ST_AR[c['status']]}){' ' + ev if ev else ''}: «{_claim_text(c['text'])}»")
            else:
                lines.append(f"• {c['id']} ({c['status']}){' ' + ev if ev else ''}: \"{_claim_text(c['text'])}\"")
        n_thr = len(r.get("threats", []))
        q = r.get("quarantined")
        name = (r.get("document") or {}).get("name", "")
        if ar:
            head = [f"دققتُ «{name}» (المهمة {r['job_id']}).",
                    f"مؤشر الخطر: {r['risk_score']}/100." + (f" رُصدت {n_thr} محاولة حقن وحُجبت جملها قبل أي نموذج." if q else ""),
                    f"الادعاءات: {cc.get('contradicted', 0)} متناقضة، {cc.get('unsubstantiated', 0)} بلا سند، {cc.get('verified', 0)} مؤكدة، {cc.get('inconclusive', 0)} غير حاسمة."]
            tail = ["", "الخطوة التالية: قل «اعتمد» لأرفع طلب توقيع لقرارك. لن يُنشر شيء قبل توقيعك."]
        else:
            head = [f"Audited \"{name}\" (job {r['job_id']}).",
                    f"Risk score: {r['risk_score']}/100." + (f" {n_thr} injection attempt(s) were redacted before any model saw them." if q else ""),
                    f"Claims: {cc.get('contradicted', 0)} contradicted, {cc.get('unsubstantiated', 0)} unsubstantiated, {cc.get('verified', 0)} verified, {cc.get('inconclusive', 0)} inconclusive."]
            tail = ["", "Next step: say \"approve\" and I will ask for your signed decision. Nothing is published before you sign."]
        return "\n".join(head + lines + tail)
