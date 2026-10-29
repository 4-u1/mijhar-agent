# PRD: MIJHAR (مِجهر), evidence audit workflow

> Scope note: two layers. (1) A **tool-using agent** the officer talks to: the model chooses tools and the order, explains findings and asks for approval, inside allow-lists and budgets (AGENTS.md §11-16). (2) The **audit itself stays a fixed graph** (guard → extract → retrieve → verify → score → human gate → commit) that the agent runs as one tool, because a regulated process needs testable, auditable paths. Neither layer can write without a human signature (README, "Why an agent outside and a graph inside").

## 1. Vision
Help an officer decide whether a submitted document's factual and normative claims hold against reference regulations, quickly and with evidence, without letting the document (or a model) take any action on its own.

## 2. Personas
| Persona | Need | Success looks like |
|---|---|---|
| Regulatory auditor | Triage many submissions | Contradicted claims surfaced first, each with the passage and rationale |
| Compliance officer | Sign off with accountability | One action: approve/reject/revise, signed, tamper-evident ledger |
| AI-safety evaluator | Show the system resists hostile documents | Attack suite, before/after numbers, traces |

## 3. Functional requirements
| ID | Requirement | Where / how verified |
|---|---|---|
| FR-1 | Decompose a document into claims (sentence level; LLM optional, grounded) | `reasoning.py`, `llm.py`; tests, V-tasks |
| FR-2 | Hybrid retrieval: BM25 + dense, fused by RRF, over 3 corpora, AR + EN | `retrieval.py`; V-tasks |
| FR-3 | Stance per claim/passage: supports / refutes / neutral with rationale | `reasoning.py` (rules-v1), live LLM judge |
| FR-4 | Claim status: verified / contradicted / unsubstantiated / inconclusive | `graph.py::verify`; V-tasks |
| FR-5 | Guardrail: normalise, detect, redact, quarantine; fail closed | `guard.py`; S-tasks, `test_guard.py` |
| FR-6 | Deterministic risk score and internal-conflict detection | `graph.py::score` |
| FR-7 | Human gate: run halts (`interrupt`), checkpointed, resumable after restart | `test_graph.py` |
| FR-8 | Write only with a signed, unexpired, unused, report-bound approval; hash-chained ledger | `signing.py`; G-tasks, `test_signing.py` |
| FR-9 | Conversational agent: chooses tools, explains claims, answers regulation questions, requests approval; Arabic and English | `agent/`; `test_agent.py`, agent evals C01-C10 |
| FR-10 | Agent cannot write, sign or reach the network; raw documents never in its context; replies scrubbed | `agent/tools.py`, `loop.py`, `service.py`; agent evals X01-X08 |
| FR-11 | Responsive web app for the officer (phone to desktop), live step streaming, approval card | `data/agent/web/`; checked in Chromium at 390 and 1280 px |

## 4. Non-functional requirements
| ID | Requirement | Measured (offline, this build) |
|---|---|---|
| NFR-1 | Retrieval latency < 1,500 ms | p50 1.6 ms, p95 1.9 ms, max 4.5 ms (21 passages, hashing encoder, local). A neural encoder and a live LLM will cost more; not measured |
| NFR-2 | Deterministic and reproducible offline | 3 trials per eval task identical (`Deterministic: True`) |
| NFR-3 | WCAG AA, RTL | **Not audited.** UI uses Arabic fonts and RTL; no contrast or screen-reader audit was done |
| NFR-4 | Zero credential exposure | No secret in repo, bundle or responses; tests assert tokens are absent from API output |
| NFR-5 | Bounded resources | Step, token, size and per-key job limits enforced; tests `test_step_budget_blocks`, `B01/B02` |

Cost note: offline runs cost $0. A 3-4 claim document is about 1-1.4k estimated tokens in the pipeline (measured by the budget counter); live mode adds one extraction call and up to `claims x top_k` judge calls. At 1,000 audits/day on a free model the binding limit is the provider rate limit, not money; plan a paid fallback.

## 5. Risk and mitigation
| Risk | Failure mode | Countermeasure | Residual |
|---|---|---|---|
| Prompt injection in document | Model follows hidden instructions | Guard before model; tool-less LLM nodes; wrapped untrusted text; signed writes | Regex guard does not generalise (6/10 contaminated hold-out); containment is structural |
| Hallucinated claims/verdicts | Fabricated claim or stance | Grounding check; stance from rules or schema-validated judge; inconclusive on failure | Rules-v1 is not a trained NLI |
| Forged/replayed approval | Unauthorised write | HMAC token, nonce, expiry, report-hash binding, re-verify in write tool | Symmetric key; single host |
| Free model disappears / rate-limits / provider unreachable | Live mode unavailable | Offline rules path always works; model id in env; client disables itself after 3 failed requests with no HTTP status; CLI shows `ok: 0` and a warning | Lower quality offline; in the HTTP API the first affected audit finishes on `rules-v1` with no warning in its response (later requests get 503) |
| Personal data to third party | PDPL exposure in live mode | Offline default; documented warning | Operator discipline |
| Stale/incorrect corpus | Wrong verdicts | Corpora are labelled synthetic; versioned in repo | Needs authoritative source before real use |
| Tool or retrieval failure | Silent "verified" | Failure maps to inconclusive; run ends blocked on guard failure | |
| Agent model hijacked by document text | Model tries to publish, exfiltrate, or mislead | No write/sign tool; allow-list; session-scoped jobs; reply scrub; vault; approval card built by the harness | Model can still word a misleading summary; officer reviews the card |
| Free model has no tool calling / is rate-limited | Agent cannot act | JSON tool protocol; offline planner with visible notice | Lower quality without a model |
| Agent loops or runs long | Cost, latency | 10 model calls, 16 tool calls, 150 s per request; repeated-call stop; 200k tokens per session | |
