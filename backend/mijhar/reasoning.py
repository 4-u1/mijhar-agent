"""Offline reasoning baselines: claim extraction and stance (NLI-style) judgement.

These are RULE-BASED (rules-v1). They are deterministic and testable and make the
whole pipeline runnable without a model, but they are not a trained NLI model and
their probabilities are fixed constants, not calibrated. In live mode (OpenRouter)
the LLM judge replaces them; the evals report both.
"""
from __future__ import annotations

import re

from .guard import normalize
from .retrieval import tokenize

_DIG = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_SPLIT = re.compile(r"(?<=[.!?؟])\s+|\n+")
_CLAIMY = re.compile(
    r"\d|%|\b(?:must|shall|may|should|never|always|all|no|none|zero|without|prohibit\w*|require\w*|"
    r"permitted|allowed|optional|only|fully|automatic\w*|abroad|overseas|outside|foreign|stored|transferred|shared|retained|deleted|awarded|reported|unencrypted)\b|يجب|يحظر|يجوز|لا يجوز|جميع|دون|بلا|كل |اختياري|فقط|بالكامل|يتم",
    re.I)


def extract_claims_rules(text: str, max_claims: int = 25) -> list[dict]:
    """Sentence-level atomic-ish claims from SANITISED text. Redacted spans are never claims."""
    claims, pos = [], 0
    for sent in _SPLIT.split(text):
        s = sent.strip()
        start = text.find(sent, pos) if sent else pos
        pos = max(pos, start + len(sent)) if start >= 0 else pos
        if len(s) < 12 or "[REDACTED:" in s or s.startswith("#"):
            continue
        if _CLAIMY.search(s):
            claims.append({"id": f"CLM-{len(claims) + 1:03d}", "text": s[:400], "offset": max(start, 0)})
        if len(claims) >= max_claims:
            break
    return claims


# ---------- numbers ----------
_UNITS = [  # (regex, group, factor-to-base)
    (r"hours?|ساعة|ساعات", "time", 1.0),
    (r"working\s+days?|days?|يوم|أيام|ايام|يوماً|يوما", "time", 24.0),
    (r"months?|شهر|أشهر|اشهر|شهراً|شهرا", "time", 24.0 * 30),
    (r"years?|سنة|سنوات|سنه", "time", 24.0 * 365),
    (r"sar|riyals?|ريال", "sar", 1.0),
    (r"bidders?|bids|متنافسين|متنافس|عروض", "bidders", 1.0),
    (r"%|percent|بالمئة|٪", "pct", 1.0),
]
_NUM = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(" + "|".join(u[0] for u in _UNITS) + r")", re.I)
_PRE_SAR = re.compile(r"(?:sar|ريال)\s*(\d[\d,]*(?:\.\d+)?)", re.I)
_WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "واحد": 1, "اثنين": 2, "ثلاثة": 3, "اثنان": 2}
_MAXB = re.compile(r"within|no later than|up to|limited to|at most|not exceed|خلال|يقتصر|حتى|لا تزيد|بحد أقصى", re.I)
_MINB = re.compile(r"at least|minimum|above|exceed|more than|over |على الأقل|تتجاوز|لا تقل|أكثر من", re.I)


def numbers(text: str) -> list[tuple[str, float]]:
    t = text.translate(_DIG)
    out = []
    for m in _NUM.finditer(t):
        val = float(m.group(1).replace(",", ""))
        unit = m.group(2).lower()
        for rx, grp, fac in _UNITS:
            if re.fullmatch(rx, unit, re.I):
                out.append((grp, val * fac))
                break
    for m in _PRE_SAR.finditer(t):
        out.append(("sar", float(m.group(1).replace(",", ""))))
    for w, v in _WORDNUM.items():
        if re.search(rf"\b{w}\s+(?:bidders?|bids|vendors?)|{w}\s+(?:متنافسين|عروض)", t, re.I):
            out.append(("bidders", float(v)))
    return out


def _bounded_numbers(evidence: str) -> list[tuple[str, float, str]]:
    """(group, value, bound) per clause, so 'within 10 days, then 5 days' keeps each bound with its number."""
    out = []
    for part in re.split(r"[,;،]|\band\b|\bthen\b|\bfollowed by\b|تليها|ثم", evidence.translate(_DIG), flags=re.I):
        bound = "min" if _MINB.search(part) else "max" if _MAXB.search(part) else "eq"
        out += [(g, v, bound) for g, v in numbers(part)]
    return out


# ---------- semantic cue pairs ----------
_ABROAD = re.compile(r"outside the kingdom|abroad|overseas|foreign (?:server|data cent)|خارج المملكة|في الخارج|خوادم أجنبية|خوادم اجنبيه", re.I)
_INSIDE = re.compile(r"inside the kingdom|within the kingdom|داخل المملكة", re.I)
_PROHIB = re.compile(r"prohibited|not permitted|must not|يحظر|يُحظر|لا يجوز", re.I)
_APPROVAL = re.compile(r"approv|authori[sz]|permission|موافقة|ترخيص|بإذن", re.I)
_NO_APPROVAL = re.compile(r"(?:without|no|lacking|lack of|absent|دون|بلا|بدون)\s+(?:\w+\s+)?(?:approv\w*|authori[sz]\w*|permission|موافقة|ترخيص|إذن|اذن)", re.I)
_NOHUMAN = re.compile(r"(?:no|without|zero|never)\s+(?:any\s+)?human|full(?:y)?\s+autonom|100\s*%\s*(?:automat|autonom)|no appeal|without (?:human )?(?:review|appeal)|دون (?:أي )?(?:مراجعة|تدخل|استئناف) بشري|بلا (?:مراجعة|استئناف|تدخل)|استئناف بشري", re.I)
_NEEDHUMAN = re.compile(r"human review|human appeal|review and appeal|مراجعة (?:و|وال)?(?:استئناف )?بشري|استئناف بشري|المراجعة والاستئناف", re.I)
_ANYWHERE = re.compile(r"any (?:region|country|location|jurisdiction|data cent\w+)|anywhere|worldwide|أي (?:منطقة|دولة|موقع)|في أي مكان", re.I)
_OPTIONAL = re.compile(r"not required|no need|optional|unnecessary|may skip|can skip|need not|غير ملزم|اختياري|لا حاجة|ليس مطلوب|غير مطلوب", re.I)
_OBLIG = re.compile(r"\bmust\b|\bshall\b|\brequired?\b|يجب|يتطلب", re.I)
_DIRECT = re.compile(r"direct(?:ly)?\s+award|awarded directly|sole[- ]source|single vendor|شراء مباشر|ترسية مباشرة|مورد واحد", re.I)
_COMPET = re.compile(r"competitive|tender|bidders|منافسة|متنافسين", re.I)
_UNENC = re.compile(r"unencrypted|plaintext|without encryption|no encryption|غير مشفر|دون تشفير", re.I)
_ENC = re.compile(r"encrypt|تشفير", re.I)


def _overlap(claim: str, ev: str) -> float:
    c, e = set(tokenize(claim)), set(tokenize(ev))
    return len(c & e) / len(c) if c else 0.0


def stance_rules(claim: str, reference: str) -> dict:
    c, r = normalize(claim), normalize(reference)
    ov = _overlap(c, r)
    reasons: list[str] = []
    refute = support = False

    # numeric comparison, per unit group. A claim number that appears in the reference matches it exactly;
    # otherwise it must satisfy at least one reference bound, or it is a numeric contradiction.
    cn, rn = numbers(c), _bounded_numbers(r)
    for grp in {g for g, _ in cn} & {g for g, _, _ in rn}:
        refs = [(v, b) for g, v, b in rn if g == grp]
        for cv in [v for g, v in cn if g == grp]:
            if any(abs(cv - rv) < 1e-9 for rv, _ in refs):
                support = True
                continue
            ok = any((cv <= rv) if b == "max" else (cv >= rv) if b == "min" else False for rv, b in refs)
            if ok:
                support = True
            else:
                refute = True
                reasons.append(f"{grp}: claim {cv:,.10g} vs reference " + "/".join(f"{b} {rv:,.10g}" for rv, b in refs))

    # semantic cue conflicts
    if _ABROAD.search(c) and (_INSIDE.search(r) or _PROHIB.search(r)) and (not _APPROVAL.search(c) or _NO_APPROVAL.search(c)):
        refute = True
        reasons.append("claim moves/keeps data outside the Kingdom; reference requires residency or prohibits transfer")
    if _ANYWHERE.search(c) and (_INSIDE.search(r) or _PROHIB.search(r)) and not _NO_APPROVAL.search(r):
        refute = True
        reasons.append("claim allows any location; reference requires residency inside the Kingdom")
    if _NOHUMAN.search(c) and _NEEDHUMAN.search(r):
        refute = True
        reasons.append("claim removes human review/appeal; reference requires it")
    if _OPTIONAL.search(c) and _OBLIG.search(r) and ov >= 0.15:
        refute = True
        reasons.append("claim makes optional what the reference makes obligatory")
    if _DIRECT.search(c) and _COMPET.search(r) and _OBLIG.search(r):
        refute = True
        reasons.append("claim describes direct award where the reference requires competitive tendering")
    if _UNENC.search(c) and _ENC.search(r) and _OBLIG.search(r):
        refute = True
        reasons.append("claim describes unencrypted storage; reference requires encryption")

    if refute:
        stance, p = "refutes", (0.90, 0.04, 0.06)
    elif ov >= 0.25 and (support or ov >= 0.4):
        stance, p = "supports", (0.04, 0.80, 0.16)
        reasons.append(f"consistent with reference (token overlap {ov:.2f})")
    else:
        stance, p = "neutral", (0.05, 0.10, 0.85)
        reasons.append(f"no clear relation (token overlap {ov:.2f})")
    return {"stance": stance, "contradiction_probability": p[0], "entailment_probability": p[1],
            "neutral_probability": p[2], "rationale": "; ".join(reasons), "method": "rules-v1",
            "overlap": round(ov, 3)}
