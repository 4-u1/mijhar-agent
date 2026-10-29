# Live agent eval

Planner: OFFLINE planner (plumbing check, not a model); trials k = 1. A = no skills; B = just-in-time skills (this build).

| Config | pass rate | pass^k (k = 1) | avg requests | avg tokens |
|---|---|---|---|---|
| A | 78% | 78% | 0.0 | 0 |
| B | 78% | 78% | 0.0 | 0 |

Flipped A -> B: none
Regressed A -> B: none

| Root cause (failed grader) | A | B |
|---|---|---|
| approval | 1 | 1 |
| contains_any | 2 | 2 |
| tool_called | 2 | 2 |
