# Capstone compliance matrix

Source of requirements: the Day 5 scoring guide and final-prep checklist (SDAIA Academy, Agentic AI Systems Engineering). Status: ✅ verified by running it · 🟢 verified by reading/static checks only · 🟡 partly met · ⬜ outside the repository.

**How this was checked (2026-10-29 review).** The review machine could not install `langgraph`, `fastapi`, `openai` or `httpx` (package index blocked) and had no OpenRouter access. So:
- Run for real: 44 pipeline tests that need none of those (guard, signing, MCP over a live stdio session, LLM client with fakes, embeddings, AGENTS.md sync).
- Run against a **local stand-in for langgraph** (a ~100-line emulation of `StateGraph`/`interrupt`/SQLite checkpoints, kept outside the repository): the graph tests, `evals.run` (output byte-identical to the recorded `results.md`), `evals.ablation`, all 19 agent tests, `evals.agent_run`, the CLI chat, and the agent web app in Chromium (1280 px and 390 px, Arabic and English: audit → approval → signed commit, MCP on, no console errors, no horizontal scroll).
- Not run: `tests/test_api.py` and the agent's mount inside FastAPI (`api.py`), real LangGraph, the real model. **Run `uv sync --extra dev && uv run pytest` and the three eval commands on your machine before presenting.**

## 1. Working system and live demo (25%)

| Requirement | Evidence | Status |
|---|---|---|
| Multi-step task, 3+ tools | Agent: 6 tools; one request runs `load_skill` → `audit_document` (8-node graph) → answer; next `request_publication` → signed commit | ✅ |
| At least one tool over MCP | `search_regulations`, `check_claim` over stdio MCP; the graph's retrieval, verification and **write** also over MCP; MCP is the default for `serve`/`agent`/`chat` | ✅ |
| Runs from a clean start | `uv sync` → `uv run mijhar init-env` → `uv run mijhar agent` | 🟢 (clean-clone test still to do) |
| Approval shown | Approval card (risk stamp, threats, verdicts, reviewer key) and CLI prompt | ✅ |
| Live model | Agent and pipeline LLM paths tested with scripted fakes only | 🟡 run once with your key |

## 2. Context and harness engineering (25%)

| Requirement | Evidence | Status |
|---|---|---|
| Spec / AGENTS.md | Part 1 pipeline, Part 2 agent (prompt verbatim, context plan, tools, budgets, fallbacks, done criteria); drift tests | ✅ |
| Memory or retrieval | Hybrid retrieval; `/memories` preferences (officer-written, model read-only); skills loaded on demand | ✅ |
| Compaction or budget rule | Pipeline 128k plan + extractive compaction; agent: trimmed tool results, turn compaction at 24k est. tokens (test) | ✅ |
| Permissions | allow-list, Pydantic args, no write/sign tool for any model, session-scoped jobs, vault | ✅ |
| Budgets | model calls, tool calls, wall clock, session tokens, repeated calls, model requests (tests + evals B01-B02) | ✅ |
| Choices justified | README "Why an agent outside and a graph inside", PRD risk table | ✅ |

## 3. Evaluation and error analysis (20%)

| Requirement | Evidence | Status |
|---|---|---|
| 15+ tasks, automatic graders | Pipeline 33 tasks; agent harness 20 tasks; **`backend/tasks.jsonl` (18 tasks, course format)** run by `uv run mijhar eval tasks.jsonl --config A B`, which writes `eval_A.csv` / `eval_B.csv` | ✅ offline · 🟡 live run needs your key |
| Two configurations | Pipeline A/B 73%→100%; agent harness A/B 70%→100% | ✅ |
| Root causes counted | `results.md`, `agent_results.md`, `ERROR_ANALYSIS.md` | ✅ |
| One change explained by the data | Ablation: guard alone explains all 9 pipeline flips; retrieval none | ✅ |
| pass^k / noise | Deterministic offline (pass^3 = pass@1); live pass^k not measured | 🟡 |

## 4. Security, governance and operability (20%)

| Requirement | Evidence | Status |
|---|---|---|
| Trifecta mapped | SECURITY.md §1 (pipeline), §6 (agent) | ✅ |
| Attack before/after | Pipeline S02-S12; agent X01, X03, X04, X05, X08 (compromised model) | ✅ |
| Defence in code | guard, signing, tool-less pipeline LLM nodes, agent allow-list, scrub, vault | ✅ |
| PDPL considered | Live mode is an operator opt-in for both layers; traces hold no text | ✅ |
| Traces or logs | `traces.jsonl` (nodes), `agent_traces.jsonl` (model and tool spans, `gen_ai.*`), hash-chained ledger | ✅ |
| No secrets in repo | `.env` ignored; keys in the agent page only in memory; demo link uses the URL fragment | ✅ |

## 5. Presentation and reproducibility (10%)

| Requirement | Evidence | Status |
|---|---|---|
| README run with `uv run` and a key | Quickstart | 🟢 |
| Eval tables in README | pipeline, ablation, agent | ✅ |
| 8-minute plan + Q&A | `docs/PRESENTATION.md` | ✅ |
| Eval CSVs for both configurations (submission item) | `mijhar eval` → `evals/live/eval_A.csv`, `eval_B.csv`; offline-planner CSVs in `evals/offline_planner/` | 🟡 run live |
| README from the course template | all template sections (track, team, model, problem, how to run, ladder, tools with trifecta leg, evaluation, error analysis, security note, limitations) | ✅ |
| Slides, backup recording, clean-clone test, warm-up run | — | ⬜ |
