"""Live agent eval in the course format:  uv run mijhar eval tasks.jsonl --config A B [--trials 3]

Task format (one JSON line, as in the course's data/eval/tasks.jsonl):
    {"id", "category", "lang", "prompt", "graders": [...], "attach": {"sample": NAME} | {"name", "text"}}   # attach optional
Graders (all must pass): contains_any, not_contains, tool_called, tool_not_called (course semantics: case-insensitive,
Arabic digits folded), plus two for this domain: approval {"expect": bool} and ledger_unchanged.

Configurations (ONE change): A = no skills (no skill index, no load_skill);  B = this build (just-in-time skills).
Writes evals/live/eval_A.csv, eval_B.csv and summary.md: pass rate, pass^k, avg requests, avg tokens, root causes.

Uses the real model (needs OPENROUTER_API_KEY; MIJHAR_ALLOW_LIVE is implied for an eval you start yourself).
--offline runs the same suite on the offline planner: it checks the plumbing and graders, not a model.
Free quota: about 3-6 requests per task per config, more when the pipeline also uses the model
(MIJHAR_PIPELINE_LLM=0 keeps the pipeline on rules). Use --limit / --ids on the 50-request free tier.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩٬", "0123456789,")
KNOWN = {"contains_any", "not_contains", "tool_called", "tool_not_called", "approval", "ledger_unchanged"}


def load_tasks(path: Path, ids: list[str] | None = None, limit: int | None = None) -> list[dict]:
    tasks = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    for t in tasks:
        for g in t["graders"]:
            if g["type"] not in KNOWN:
                raise ValueError(f"{t['id']}: unknown grader {g['type']!r}")
    if ids:
        tasks = [t for t in tasks if t["id"] in ids]
    return tasks[:limit] if limit else tasks


_DASHES = str.maketrans({c: "-" for c in "\u2010\u2011\u2012\u2013\u2014\u2212\ufe63\uff0d"})


def _n(s: str) -> str:
    """Course semantics (case-insensitive, Arabic digits folded) plus Unicode dashes folded to '-':
    models often write passage ids with a non-breaking hyphen (AIE\u201106), which is the same id."""
    return (s or "").translate(ARABIC_DIGITS).translate(_DASHES).lower()


def grade(task: dict, final: str, tools: list[str], approval: bool, ledger_delta: int) -> list[dict]:
    out = []
    for g in task["graders"]:
        k = g["type"]
        if k == "contains_any":
            ok = any(_n(v) in _n(final) for v in g["values"]); d = "" if ok else f"none of {g['values'][:4]}"
        elif k == "not_contains":
            hits = [v for v in g["values"] if _n(v) in _n(final)]; ok, d = not hits, (f"contains {hits}" if hits else "")
        elif k == "tool_called":
            ok = g["name"] in tools; d = "" if ok else f"{g['name']} not called"
        elif k == "tool_not_called":
            ok = g["name"] not in tools; d = "" if ok else f"{g['name']} was called"
        elif k == "approval":
            ok = approval == bool(g["expect"]); d = "" if ok else f"approval requested={approval}"
        else:  # ledger_unchanged
            ok = ledger_delta == 0; d = "" if ok else f"ledger +{ledger_delta}"
        out.append({"type": k, "pass": ok, "detail": d})
    return out


def _ledger_rows() -> int:
    from ..config import data_dir
    try:
        return sqlite3.connect(str(data_dir() / "ledger.sqlite")).execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    except sqlite3.OperationalError:
        return 0


def run(tasks_path: Path, configs: list[str], trials: int = 1, offline: bool = False, use_mcp: bool = True,
        ids: list[str] | None = None, limit: int | None = None, out_dir: Path | None = None, client=None) -> dict:
    out_dir = Path(out_dir or Path(tasks_path).resolve().parent / "evals" / "live")
    out_dir.mkdir(parents=True, exist_ok=True)
    os.environ["MIJHAR_DATA_DIR"] = str(out_dir / "data")          # isolated ledger, sessions, cache
    if trials > 1:
        os.environ["MIJHAR_CACHE"] = "0"                           # pass^k needs fresh samples
    from ..config import env
    from ..graph import Auditor, Runtime
    from ..llm import LLM
    from ..toolbox import ToolBox
    from .config import AgentConfig
    from .model import ChatModel
    from .service import AgentService
    from .store import Store

    tasks = load_tasks(tasks_path, ids, limit)
    if not offline and not env("OPENROUTER_API_KEY") and client is None:
        raise SystemExit("live eval needs OPENROUTER_API_KEY in backend/.env (or run with --offline to check the plumbing)")
    pipeline_llm = (not offline) and (env("MIJHAR_PIPELINE_LLM", "1") or "1") == "1" and client is None
    per_req = 4 + (15 if pipeline_llm else 0)
    print(f"{len(tasks)} tasks x {len(configs)} configs x {trials} trials; planner={'offline' if offline else 'llm'}; "
          f"roughly {len(tasks) * len(configs) * trials * per_req} model requests at most (free tier: 50/day; cache replays repeats)")

    rows: list[dict] = []
    for cname in configs:
        aud = Auditor(Runtime(ToolBox(use_mcp), LLM() if pipeline_llm else None), checkpoint_path=str(out_dir / "data" / f"cp_{cname}.sqlite"))
        model = None if offline else ChatModel(client=client, use_cache=None if trials == 1 else False)
        svc = AgentService(aud, Store(out_dir / "data" / f"agent_{cname}.sqlite"), AgentConfig(skills=(cname != "A")),
                           model=model, live_pipeline=pipeline_llm)
        try:
            for t in tasks:
                for k in range(trials):
                    s = svc.new_session(f"eval-{cname}-{t['id']}-{k}-{time.time_ns()}")
                    if t.get("attach"):
                        a = t["attach"]
                        svc.add_document(s.id, s.client, a.get("name", ""), a.get("text"), a.get("sample"))
                    before, t0 = _ledger_rows(), time.perf_counter()
                    calls0 = (model.calls if model else 0) + (aud.rt.llm.calls if aud.rt.llm else 0)
                    tok0 = aud.rt.llm.tokens if aud.rt.llm else 0
                    err, ev = "", []
                    try:
                        ev = list(svc.turn(s.id, s.client, t["prompt"]))
                    except Exception as e:  # a crash is a failed trial, not a failed suite
                        err = f"{type(e).__name__}: {str(e)[:160]}"
                    final = ([e["text"] for e in ev if e["type"] == "final"] or [""])[-1]
                    tools = [e["name"] for e in ev if e["type"] == "tool_call"]
                    approval = any(e["type"] == "approval_required" for e in ev)
                    planner_end = next((e.get("planner") for e in reversed(ev) if e["type"] == "done"), "")
                    if not offline and planner_end == "offline" and not err:
                        why = next((e["text"] for e in ev if e["type"] == "notice" and "unavailable" in e["text"].lower()), "")
                        err = f"model_unavailable: {why or (model.dead if model else '')}"[:300]
                    grades = grade(t, final, tools, approval, _ledger_rows() - before)
                    passed = not err and all(g["pass"] for g in grades)
                    reqs = (model.calls if model else 0) + (aud.rt.llm.calls if aud.rt.llm else 0) - calls0
                    toks = sum(e.get("tokens", 0) for e in ev if e["type"] == "model_call") + ((aud.rt.llm.tokens if aud.rt.llm else 0) - tok0)
                    rows.append({"config": cname, "id": t["id"], "category": t["category"], "lang": t["lang"], "trial": k,
                                 "passed": passed, "failed_graders": err or "; ".join(f"{g['type']}: {g['detail']}" for g in grades if not g["pass"]),
                                 "tools": " ".join(tools), "requests": reqs, "tokens": toks, "seconds": round(time.perf_counter() - t0, 1),
                                 "planner": planner_end or "-", "final": final[:400].replace("\n", " ")})
                    print(f"{'PASS' if passed else 'FAIL'} [{cname}] {t['id']:<26} {rows[-1]['failed_graders'][:90]}")
        finally:
            aud.rt.toolbox.close()
    return _write(rows, configs, trials, out_dir, offline)


def _write(rows: list[dict], configs: list[str], trials: int, out_dir: Path, offline: bool) -> dict:
    cols = list(rows[0].keys()) if rows else []
    for c in configs:
        with open(out_dir / f"eval_{c}.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(r for r in rows if r["config"] == c)
    summ, per_task = {}, defaultdict(dict)
    for c in configs:
        rs = [r for r in rows if r["config"] == c]
        by = defaultdict(list)
        for r in rs:
            by[r["id"]].append(r["passed"])
        for tid, v in by.items():
            per_task[tid][c] = all(v)
        summ[c] = {"tasks": len(by), "pass_rate": sum(r["passed"] for r in rs) / max(1, len(rs)),
                   "pass_hat_k": sum(all(v) for v in by.values()) / max(1, len(by)),
                   "avg_requests": sum(r["requests"] for r in rs) / max(1, len(rs)),
                   "avg_tokens": sum(r["tokens"] for r in rs) / max(1, len(rs)),
                   "causes": Counter(x.split(":")[0].strip() for r in rs if not r["passed"] for x in r["failed_graders"].split(";") if x.strip())}
    pct = lambda x: f"{x * 100:.0f}%"  # noqa: E731
    md = ["# Live agent eval", "", f"Planner: {'OFFLINE planner (plumbing check, not a model)' if offline else 'LLM via OpenRouter'}; "
          f"trials k = {trials}. A = no skills; B = just-in-time skills (this build).", "",
          f"| Config | pass rate | pass^k (k = {trials}) | avg requests | avg tokens |", "|---|---|---|---|---|"]
    md += [f"| {c} | {pct(v['pass_rate'])} | {pct(v['pass_hat_k'])} | {v['avg_requests']:.1f} | {v['avg_tokens']:.0f} |" for c, v in summ.items()]
    if len(configs) == 2:
        a, b = configs
        fl = [t for t, v in per_task.items() if not v.get(a) and v.get(b)]
        rg = [t for t, v in per_task.items() if v.get(a) and not v.get(b)]
        md += ["", f"Flipped {a} -> {b}: {', '.join(fl) or 'none'}", f"Regressed {a} -> {b}: {', '.join(rg) or 'none'}"]
    md += ["", "| Root cause (failed grader) | " + " | ".join(configs) + " |", "|---|" + "---|" * len(configs)]
    keys = sorted(set().union(*[v["causes"] for v in summ.values()]))
    md += [f"| {k} | " + " | ".join(str(summ[c]["causes"].get(k, 0)) for c in configs) + " |" for k in keys] or ["| none | " + " | ".join("0" for _ in configs) + " |"]
    (out_dir / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n" + "\n".join(md) + f"\n\nper-trial rows: {', '.join(str(out_dir / f'eval_{c}.csv') for c in configs)}")
    return {c: {k: v for k, v in s.items() if k != "causes"} for c, s in summ.items()}
