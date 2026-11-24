# reviewbrief 2.0 — multi-agent review triage

When three agents work the same repo, the reviewer's problem is not volume —
it is that the agents disagree with each other and grade their own work.
`reviewbrief 2.0` ingests outputs from Claude Code, Codex and planner agents
in one queue and produces the three things a human reviewer needs:

1. **Cross-agent contradiction report** — agent A says the rate limiter is
   in `login.py`, agent B says it is not. Detected deterministically from
   claim records (kind + subject key pairing), never from prose similarity;
   each contradiction carries a resolution: verify the subject directly, do
   not ask either agent to adjudicate itself.
2. **Risk-ranked review queue** — every change scored from named factors
   (kind weights, auth/secret touch, diff size, no tests, contradicted,
   grader-flagged), each with **per-item reject criteria** (what would make
   a reviewer reject it — migrations need reversible `down()`, auth needs
   allow+deny tests) and **estimated review minutes** with the arithmetic
   printed.
3. **Grader-trust check** — tests rewritten by the agent that wrote the code
   are flagged `rewritten_by_author`: that grader is a claim, not
   independent evidence. Unknown provenance is flagged too, never assumed
   clean.

## Usage

```
$ reviewbrief all examples/multi_agent_sources.json
# reviewbrief — multi-agent triage summary

- contradictions: 2 cross-agent, 0 self
- review queue: 4 item(s), ~110 min total (est)
- grader trust: 1 authored re-writes, 1 unknown

# cross-agent contradiction report
...
## src/auth/login.py (file_contains)
- claude claims: login.py contains the rate limiter
- codex claims: rate limiter not present in login
resolution: both cannot be true; verify src/auth/login.py directly ...
```

Commands: `contradictions`, `queue`, `grader`, `all`; every command takes
`--json`. Exit codes: `0` clean, `1` contradictions found / grader warn,
`2` grader fail or usage error — never a traceback.

## Source document format

```json
{"agent": "claude", "source_kind": "claude_code",
 "claims": [{"claim": "...", "kind": "file_contains", "subject": "path"}],
 "changes": [{"id": "C1", "path": "...", "description": "...",
              "lines_changed": 45, "tests_added": true, "kind": "feature"}],
 "tests_touched": [{"path": "tests/x.py", "rewritten_by": "claude",
                    "prev_author": "human"}]}
```

`source_kind` selects the adapter — `claude_code`, `codex` (uses
`statements`/`filepath`/`lines`), `planner` (uses `assertions`/`tasks`), or
`generic`. Adapters normalise field names so one pipeline sees every agent.
Unknown kinds are errors, not guesses.

Claim kinds: `file_contains`, `file_absent`, `tests_pass`, `tests_fail`,
`task_done`, `task_blocked`. Opposite-kind pairs on the same subject from
different agents are contradictions; the same agent's opposing pair is
reported as a self-contradiction.

## Design rules

- **Contradictions are structural.** Same-subject opposite-kind pairing
  only; unmatched subjects are never force-paired.
- **Scores show their arithmetic.** Risk factors and minutes formulas are
  printed, not buried.
- **Reject criteria never bypass.** A forbidden-vocabulary guard (skip
  review / approve without / bypass) asserts no generated criterion is a
  review bypass.
- **Ungraded graders are flagged, not trusted.** Missing provenance is
  `unknown_provenance`, not silent acceptance.
- `main` never leaks a traceback: `reviewbrief: <message>`, exit 2.

## Scope and limitations

- Source documents are what the harness/agents wrote to disk; reviewbrief
  does not fetch them from anywhere.
- Contradiction detection is exact-subject pairing; agents referring to the
  same file by different paths are unmatched (reported as separate claims,
  not a false pair).
- Risk weights are defaults and can be tuned via the module API; CLI
  overrides are a planned flag.
- Review minutes assume a competent reviewer; the estimate's formula is
  printed so you can distrust it precisely.
