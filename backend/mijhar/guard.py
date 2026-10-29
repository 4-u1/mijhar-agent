"""Injection guardrail. Two levels so the evals can measure what the hardening buys.

basic    : a faithful port of the original TypeScript scanner (8 English regexes on the
           raw text). Detected spans are redacted; nothing is normalised. This is the
           best case for that design, used as the baseline "Config A".
hardened : Unicode + Arabic normalisation first, then English and Arabic rules, then
           sentence-level redaction. Fails closed: any exception => the document is
           blocked, never passed on.

Neither level is a complete defence (models cannot reliably tell data from
instructions). The real containment is structural: LLM nodes get no tools and no
network, and every write needs a signed human decision. See SECURITY.md.
"""
from __future__ import annotations

import base64
import re
import unicodedata
from dataclasses import dataclass, field

# ---------- normalisation ----------
_ARABIC_MARKS = re.compile("[\u064b-\u065f\u0670\u0640\u06d6-\u06ed]")  # tashkeel, tatweel, quranic marks
_ALEF = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ؤ": "و", "ئ": "ي"})
# A small confusables map (Cyrillic/Greek look-alikes -> Latin). Not exhaustive.
_CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x", "у": "y", "і": "i", "ј": "j", "һ": "h",
    "ѕ": "s", "ԁ": "d", "ɡ": "g", "ο": "o", "ν": "v", "ρ": "p", "α": "a", "ε": "e", "ι": "i", "κ": "k",
})


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text)
    # drop zero-width / bidi / other format characters (category Cf) but keep newlines
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")
    t = _ARABIC_MARKS.sub("", t).translate(_ALEF).translate(_CONFUSABLES)
    t = re.sub(r"[ \t\u00a0]+", " ", t)
    return t


# ---------- rules ----------
@dataclass(frozen=True)
class Rule:
    rid: str
    attack: str      # AttackVector from the UI types
    severity: str    # critical | high | medium
    pattern: re.Pattern


def _r(rid, attack, sev, pat, flags=re.I | re.S):
    return Rule(rid, attack, sev, re.compile(pat, flags))


_VERBS_OVERRIDE = r"(?:ignore|disregard|forget|override|bypass|skip|neglect)"
_OBJ = r"(?:all\s+|any\s+|the\s+|your\s+|every\s+)*"
_WHAT = r"(?:(?:previous|prior|above|earlier|system|security|safety|ethics?|compliance)\s+){1,3}(?:instructions?|rules?|prompts?|guidelines?|checks?|polic(?:y|ies)|contradictions?|evaluations?)"

# Original eight patterns, verbatim from agentEngine.ts (baseline).
BASIC_RULES = [
    _r("basic-bracket", "indirect_prompt_injection", "critical", r"\[SYSTEM\s*(?:INSTRUCTION|COMMAND|OVERRIDE).*?\]", re.I),
    _r("basic-ignore", "instruction_override", "critical", r"ignore\s+(?:all\s+)?(?:previous|prior)\s+(?:instructions|rules|prompts)", re.I),
    _r("basic-print", "data_exfiltration_canary", "critical", r"print\s+(?:the\s+)?(?:env|environment|variables|api\s*key|secret)", re.I),
    _r("basic-disregard", "instruction_override", "critical", r"disregard\s+(?:all\s+)?(?:security|ethics|evaluations|contradictions)", re.I),
    _r("basic-comment", "indirect_prompt_injection", "critical", r"<!--\s*IMPORTANT.*?-->", re.I),
    _r("basic-mdimg", "data_exfiltration_canary", "critical", r"!\s*\[.*?\]\(https?:\/\/.*?leak.*?\)", re.I),
    _r("basic-script", "indirect_prompt_injection", "critical", r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", re.I),
    _r("basic-admin", "instruction_override", "critical", r"system_role:\s*admin", re.I),
]

HARDENED_RULES = [
    _r("en-override", "instruction_override", "critical", rf"{_VERBS_OVERRIDE}\s+{_OBJ}{_WHAT}"),
    _r("en-override-2", "instruction_override", "critical", rf"{_VERBS_OVERRIDE}\s+(?:all|everything)\s+(?:above|before|previously)"),
    _r("en-sys-tag", "indirect_prompt_injection", "critical", r"\[\s*(?:system|admin|developer|assistant)\s*(?:instruction|command|override|message|note)?[^\]]{0,300}\]"),
    _r("en-role", "jailbreak_attempt", "critical", r"you\s+are\s+now\s+(?:dan|an?\s+unrestricted|in\s+developer\s+mode|free\s+of)|developer\s+mode|jailbreak|do\s+anything\s+now"),
    _r("en-override-3", "instruction_override", "critical", r"(?:ignore|disregard|forget|override|bypass)\s+(?:all\s+|any\s+|every\s+|the\s+|your\s+)*(?:rules?|directives?|commands?|restrictions?|constraints?)\s+(?:above|before|prior|previous)|(?:disregard|ignore|forget|override)\s+(?:prior|previous|earlier|above)\s+(?:directives?|commands?|orders?|restrictions?)"),
    _r("en-role-2", "jailbreak_attempt", "critical", r"pretend\s+(?:you|to\s+be)\b[^.\n]{0,60}(?:no\s+restrictions|unrestricted|no\s+rules|without\s+limits)"),
    _r("md-link-exfil", "data_exfiltration_canary", "critical", r"(?<!!)\[[^\]]*\]\(\s*https?://[^)]*[?&](?:session|token|key|secret|data|auth)[^)]*\)"),
    _r("json-audience-key", "indirect_prompt_injection", "high", r"[\"']?(?:note|message|instructions?)_?(?:for|to)_?(?:the_)?(?:assistant|ai|model|llm)[\"']?\s*:"),
    _r("en-admin", "instruction_override", "critical", r"system[_\s-]*role\s*[:=]\s*(?:admin|root)"),
    _r("en-exfil", "data_exfiltration_canary", "critical", r"(?:print|reveal|show|output|dump|leak|exfiltrate|email|send|repeat)\s+(?:me\s+)?(?:the\s+|your\s+|all\s+|any\s+)*(?:env(?:ironment)?(?:\s+variables?)?|api[\s_-]*keys?|secrets?|credentials?|tokens?|system\s+prompt|hidden\s+instructions?|initial\s+instructions?)"),
    _r("en-audience", "indirect_prompt_injection", "high", r"(?:note|message|instruction)s?\s+(?:for|to)\s+(?:the\s+)?(?:ai|assistant|model|llm|agent|auditor\s+bot)"),
    _r("html-comment-imperative", "indirect_prompt_injection", "high", r"<!--.{0,600}?(?:assistant|ignore|instruction|system|override|model)\b.{0,600}?-->"),
    _r("script", "indirect_prompt_injection", "high", r"<script\b.*?</script>|javascript\s*:"),
    _r("md-image-exfil", "data_exfiltration_canary", "critical", r"!\s*\[[^\]]*\]\(\s*https?://[^)]*[?&](?:session|token|key|secret|data|id|auth)[^)]*\)"),
    _r("md-image-external", "data_exfiltration_canary", "medium", r"!\s*\[[^\]]*\]\(\s*https?://[^)]*\)"),
    # Arabic (text is normalised first: hamza/alef forms and diacritics are already folded)
    _r("ar-override", "instruction_override", "critical", r"(?:تجاهل|تجاوز|انس|تخط|الغ|الغي|اهمل)\s+(?:\S+\s+){0,3}?(?:التعليمات|الاوامر|القواعد|الضوابط|التوجيهات|السياسات|الفحوص|الفحوصات|التناقضات)"),
    _r("ar-exfil", "data_exfiltration_canary", "critical", r"(?:اطبع|اظهر|اكشف|اعرض|سرب|ارسل|كرر)\s+(?:\S+\s+){0,2}?(?:مفتاح|مفاتيح|الاسرار|السر|متغيرات\s+البيئه|متغيرات\s+البيئة|موجه\s+النظام|تعليمات\s+النظام|التعليمات\s+الداخليه|التعليمات\s+الداخلية|كلمه\s+المرور|كلمة\s+المرور)"),
    _r("ar-role", "jailbreak_attempt", "critical", r"(?:انت|انتَ)\s+الان\s+(?:في\s+)?(?:وضع\s+المطور|نظام\s+بلا\s+قيود|مساعد\s+بلا\s+قيود)|وضع\s+المطور"),
    _r("ar-audience", "indirect_prompt_injection", "high", r"(?:ملاحظه|ملاحظة|رساله|رسالة|تعليمات)\s+(?:الى|الي|إلى|لل)\s*(?:المساعد|النموذج|الذكاء\s+الاصطناعي)"),
]

_B64 = re.compile(r"[A-Za-z0-9+/]{24,}={0,2}")
_SENT_BREAK = re.compile(r"[.!?؟\n]")


@dataclass
class Threat:
    rule: str
    attack: str
    severity: str
    start: int
    end: int
    snippet: str


@dataclass
class ScanResult:
    level: str
    original_len: int
    sanitized_text: str
    threats: list[Threat] = field(default_factory=list)
    blocked: bool = False          # True only when the guard itself failed (fail closed)
    error: str | None = None

    @property
    def quarantined(self) -> bool:
        return any(t.severity in ("critical", "high") for t in self.threats)


_RANK = {"critical": 3, "high": 2, "medium": 1}


def _dedupe(threats: list[Threat]) -> list[Threat]:
    """One finding per overlapping span (several rules often hit the same payload)."""
    out: list[Threat] = []
    for t in sorted(threats, key=lambda t: (t.start, -t.end)):
        if out and t.start < out[-1].end:
            keep = out[-1]
            if _RANK[t.severity] > _RANK[keep.severity]:
                t = Threat(t.rule, t.attack, t.severity, min(t.start, keep.start), max(t.end, keep.end), t.snippet)
            else:
                keep.end = max(keep.end, t.end)
                continue
            out[-1] = t
        else:
            out.append(t)
    return out


def _expand_to_sentence(text: str, s: int, e: int) -> tuple[int, int]:
    left = max((m.end() for m in _SENT_BREAK.finditer(text, 0, s)), default=0)
    m = _SENT_BREAK.search(text, e)
    right = m.end() if m else len(text)
    return left, right


def _redact(text: str, spans: list[tuple[int, int, str]]) -> str:
    spans = sorted(spans)
    merged: list[list] = []
    for s, e, rid in spans:
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e, rid])
    out, pos = [], 0
    for s, e, rid in merged:
        out.append(text[pos:s])
        out.append(f"[REDACTED:{rid}]\n")
        pos = e
    out.append(text[pos:])
    return "".join(out)


def scan(text: str, level: str = "hardened") -> ScanResult:
    """Scan untrusted text. Never raises: on any internal error the result is `blocked`."""
    try:
        if level == "basic":
            rules, body = BASIC_RULES, text            # no normalisation: the baseline
            expand = False
        elif level == "hardened":
            rules, body = HARDENED_RULES, normalize(text)
            expand = True
        else:
            raise ValueError(f"unknown guard level {level!r}")

        threats: list[Threat] = []
        spans: list[tuple[int, int, str]] = []
        for rule in rules:
            for m in rule.pattern.finditer(body):
                threats.append(Threat(rule.rid, rule.attack, rule.severity, m.start(), m.end(), m.group(0)[:160]))
                s, e = (_expand_to_sentence(body, m.start(), m.end()) if expand and rule.severity != "medium" else (m.start(), m.end()))
                spans.append((s, e, rule.rid))
        if level == "hardened":  # decode base64-looking blobs and re-scan the decoded text
            for m in _B64.finditer(body):
                try:
                    dec = normalize(base64.b64decode(m.group(0), validate=True).decode("utf-8"))
                except Exception:
                    continue
                if any(r.pattern.search(dec) for r in rules if r.severity == "critical"):
                    threats.append(Threat("encoded-payload", "indirect_prompt_injection", "critical", m.start(), m.end(), m.group(0)[:80]))
                    spans.append((*_expand_to_sentence(body, m.start(), m.end()), "encoded-payload"))
        return ScanResult(level, len(text), _redact(body, spans), _dedupe(threats))
    except Exception as exc:  # fail closed
        return ScanResult(level, len(text), "", [], blocked=True, error=f"{type(exc).__name__}: {exc}")
