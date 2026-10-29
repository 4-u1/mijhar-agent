"""Context budget (128k target window) enforced in code, plus step/token run budgets.

Token counts are ESTIMATES (no tokenizer is bundled, so the course's free models'
real counts will differ by roughly +-20%). The estimator is deliberately conservative
for Arabic. Compaction is extractive and deterministic: when a section overflows, the
highest-scoring sentences are kept in original order and a marker records the cut.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Section allocations, in tokens. Sum = 128_000 (asserted below).
ALLOCATION = {
    "system_directives": 6_000,
    "regulatory_corpora": 32_000,
    "document_chunks": 24_000,
    "propositions": 16_000,
    "security_sandbox": 8_000,
    "scratchpad": 34_000,
    "output_report": 8_000,
}
assert sum(ALLOCATION.values()) == 128_000

_AR = re.compile(r"[\u0600-\u06ff]")


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    ar = len(_AR.findall(text))
    other = len(text) - ar
    return int(ar / 2.6 + other / 3.6) + 1


class BudgetExceeded(RuntimeError):
    pass


_SENT = re.compile(r"(?<=[.!?؟\n])\s+")
_SALIENT = re.compile(r"\d|must|shall|may|never|all |no |zero|prohibit|require|يجب|يحظر|لا يجوز|جميع|دون|كل ", re.I)


def compact(text: str, max_tokens: int) -> tuple[str, bool]:
    """Keep the most claim-like sentences that fit. Returns (text, was_compacted)."""
    if estimate_tokens(text) <= max_tokens:
        return text, False
    sents = [s for s in _SENT.split(text) if s.strip()]
    ranked = sorted(range(len(sents)), key=lambda i: (-(1 if _SALIENT.search(sents[i]) else 0), i))
    kept, used = set(), 0
    for i in ranked:
        t = estimate_tokens(sents[i])
        if used + t > max_tokens - 20:
            continue
        kept.add(i)
        used += t
    out = " ".join(sents[i] for i in sorted(kept))
    return out + f"\n[COMPACTED: kept {len(kept)}/{len(sents)} sentences]", True


@dataclass
class ContextBudget:
    used: dict[str, int] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)

    def fit(self, section: str, text: str) -> str:
        cap = ALLOCATION[section]
        out, cut = compact(text, cap)
        self.used[section] = estimate_tokens(out)
        if cut:
            self.events.append(f"{section}: compacted to <= {cap} tokens")
        assert self.used[section] <= cap + 40  # compaction marker slack
        return out

    def total(self) -> int:
        return sum(self.used.values())


@dataclass
class RunBudget:
    max_steps: int
    max_tokens: int
    steps: int = 0
    tokens: int = 0

    def tick(self, tokens: int = 0) -> None:
        self.steps += 1
        self.tokens += tokens
        if self.steps > self.max_steps:
            raise BudgetExceeded(f"step budget exceeded ({self.max_steps})")
        if self.tokens > self.max_tokens:
            raise BudgetExceeded(f"token budget exceeded ({self.max_tokens})")
