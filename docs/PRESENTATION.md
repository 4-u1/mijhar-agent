# 8-minute talk + 4-minute Q&A (matches the Day 5 rubric)

**Before you present (in this order):** `uv run pytest` · `uv run python -m evals.run` · `uv run python -m evals.agent_run` · `uv run mijhar eval tasks.jsonl --config A B` with your key (paste `evals/live/summary.md` into the README) · run the demo once (warms caches, gives you a timing) · record a 2-minute screen capture as the backup · check `/healthz` shows `"mcp": true`.

| Min | Part | Show |
|---|---|---|
| 0-1 | Problem and user | An officer receives a draft policy. "Done" = every claim has a verdict with a passage id, injected text never reached a model, and a human signed before anything was written |
| 1-3 | Live demo | `uv run mijhar agent` → open the link (or on your phone). Pick `cloud_sovereignty_draft`, type **دقّق المستند**: the agent loads a skill, runs the audit, the 8 nodes light up, 3 injections redacted, 3 claims contradicted with CSV ids. Type **اشرح CLM-003**. Type **اعتمد**: approval card with the risk stamp. Sign → `COMMITTED` + tx hash. Backup: `mijhar chat --doc cloud_sovereignty_draft --say "audit the document" --say "approve" --yes` or the recording |
| 3-5 | Design across the ladder | Prompt (AGENTS.md §4, §11) · Context (skill index + `load_skill`, `/memories`, trimming and compaction, 128k plan) · Harness (6 allow-listed tools, two over MCP, no write tool for any model, budgets) · Loop (the agent: exits on answer, approval, limit, repetition) · Graph (the audit: 8 nodes, `interrupt()`, checkpoint, signed gate). Not needed: the outer Ralph loop |
| 5-7 | Evals | Pipeline A→B 73%→100%; ablation: the guard explains all 9 flips, retrieval none. Agent harness A→B 70%→100% with a compromised model; **the eval found a real bug** (short pasted text bypassed the guard), fixed and now tested (X08). Honest part: hold-out 1/10→6/10, live pass^k not measured |
| 7-8 | Security | Trifecta for the agent: the third leg is cut in code. Show X01 in `agent_results.md` (A wrote to the ledger, B blocked it) and a `blocked_tool` event in the UI or `tests/test_agent.py::test_compromised_model_cannot_write_publish_or_exfiltrate` |

## Likely questions and the evidence to point at
- *Why an agent here and not a workflow?* Both: the conversation is open-ended (agent with tools, budgets, eval); the audit is a regulated fixed process (graph). README "Why an agent outside and a graph inside".
- *What is in the context on turn 10?* The context meter in the case file (est. tokens / 24,000); `context` events; system prompt + skill index + preferences always, skill bodies on demand, tool results older than the last 4 stubbed, older turns compacted into a summary that keeps job ids (`loop._view`, `loop._compact`). Estimates, not tokenizer counts.
- *Which tool call would you least like the model to get wrong?* Publishing. The model has no tool for it: `request_publication` opens a card; the write needs the officer's reviewer key, is bound to the report hash, used once, verified twice (G01-G06, X01).
- *Is A vs B bigger than noise?* Offline and deterministic, so pass^3 = pass@1; the gaps are whole tasks flipping, not sampling. Live pass^k not measured.
- *Show an injection that worked before your defence. Does the defence depend on the model?* Pipeline S06/S09 on Config A. Agent X01/X03/X08 on harness A. No: the agent attacks were run with a model that obeys the injection.
- *Where does personal data go?* Default: nowhere (offline planner, rules). Live mode is an operator opt-in (`MIJHAR_ALLOW_LIVE=1`): claim excerpts and passages go to OpenRouter, outside KSA, with provider logs. Traces hold no text. SECURITY.md §5-6.
- *What happens when the free model disappears tomorrow?* 404 → fallback model; no tool support → JSON protocol; key/provider failure → offline planner with a visible notice. The demo still runs.
- *What does one conversation cost at 1,000 users a day?* Offline $0. Live: an audit request is ~3 model calls of ~2-4k est. tokens plus the pipeline's judge calls; the binding limit on free models is the rate limit, so plan a paid fallback model (`MIJHAR_FALLBACK_MODEL`).
