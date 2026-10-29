"""Ablation: which half of A -> B explains the flips?   uv run python -m evals.ablation

A -> B changes two things at once (guard level and retrieval mode). RunConfig already has them as
independent switches, so here each is changed ALONE:

    A        basic guard    + bm25     (original design)
    A+guard  hardened guard + bm25     (only the guard changed)
    A+retr   basic guard    + hybrid   (only retrieval changed)
    B        hardened guard + hybrid   (both)

Writes evals/ablation.md. Offline and deterministic, like evals.run (so pass^k = pass@1).
"""
from __future__ import annotations

from collections import defaultdict

from . import run as R
from .run import CONFIG_A, CONFIG_B, OUT, RunConfig

VARIANTS = {
    "A": CONFIG_A,
    "A+guard": RunConfig(**(CONFIG_A.to_dict() | {"guard_level": "hardened"})),
    "A+retr": RunConfig(**(CONFIG_A.to_dict() | {"retrieval_mode": "hybrid"})),
    "B": CONFIG_B,
}


def main() -> None:
    tasks = R.all_tasks()
    table: dict[str, dict[str, list[bool]]] = {v: defaultdict(list) for v in VARIANTS}
    flips: dict[str, list[str]] = {}
    base: dict[str, bool] = {}
    for name, cfg in VARIANTS.items():
        passed = []
        for tid, cat, fn, _ in tasks:
            ok = all(fn(cfg)[0] for _ in range(R.K))      # pass^k
            table[name][cat].append(ok)
            if name == "A":
                base[tid] = ok
            elif not base[tid] and ok:
                passed.append(tid)
        flips[name] = passed
    cats = sorted({c for _, c, _, _ in tasks})
    md = ["# Ablation: what explains A -> B", "",
          "pass^3 per category. Each variant changes ONE of {guard level, retrieval mode} relative to A.", "",
          "| Category | n | " + " | ".join(VARIANTS) + " |", "|---|---|" + "---|" * len(VARIANTS)]
    for c in [*cats, "ALL"]:
        row = []
        for v in VARIANTS:
            xs = [x for k, vals in table[v].items() for x in vals] if c == "ALL" else table[v][c]
            row.append(f"{100 * sum(xs) / len(xs):.0f}%")
        n = sum(len(x) for x in table["A"].values()) if c == "ALL" else len(table["A"][c])
        md.append(f"| {c} | {n} | " + " | ".join(row) + " |")
    md += ["", "Tasks flipped fail -> pass relative to A:", ""]
    md += [f"- **{v}**: {', '.join(t) or 'none'}" for v, t in flips.items() if v != "A"]
    (OUT / "ablation.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
