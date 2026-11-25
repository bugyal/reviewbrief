# reviewbrief 2.0 — multi-agent review triage

**AI-reviewer bots add another model pass and more PR comments. When three
coding agents work the same repo, the human reviewer's problem is upstream
of both: the agents disagree with each other, and the cheap ones grade
their own work.** `reviewbrief 2.0` is a deterministic reading aid, not
another reviewer — no model pass, no PR comments. It ingests outputs from
Claude Code, Codex and planner agents in one queue and hands you the three
things you cannot reconstruct by skimming:

1. **Cross-agent contradiction report** — agent A says the rate limiter is
   in `login.py`, agent B says it is not. Detected deterministically from
   claim records (subject-keyed pairing of opposite claim kinds), never
   from prose similarity; each contradiction carries a resolution: verify
   the subject directly, do not ask either agent to adjudicate itself.
2. **Risk-ranked review queue** — every change scored from named factors
   (kind weights, auth/secret touch, diff size, no tests, contradicted,
   grader-flagged), each with **per-item reject criteria** (what would make
   a reviewer reject it — migrations need reversible `down()`, auth needs
   allow+deny tests) and **estimated review minutes** with the arithmetic
   printed.
3. **Grader-trust check** — tests rewritten by the agent that wrote the
   code are flagged `rewritten_by_author`: that grader is a claim, not
   independent evidence. Unknown provenance is flagged too, never assumed
   clean. When a 163-token cheap-model flood grades itself, this is the
   check that says so.

## Worked example

Real output, three agents (claude / codex / planner) on one fixture repo —
`examples/multi_agent_sources.json` in this repo, run verbatim:

```
$ reviewbrief contradictions examples/multi_agent_sources.json
# cross-agent contradiction report

cross-agent contradictions: 2 | self-contradictions: 0

## src/auth/login.py (file_absent)

- codex claims: rate limiter not present in login
- claude claims: login.py contains the rate limiter

resolution: both cannot be true; verify src/auth/login.py directly
(read the file / run the tests / check the task state) — do not ask
either agent to adjudicate itself

## tests/ (tests_pass)
- claude claims: full test suite passes
- codex claims: integration tests fail on lockouts
...
```

```
$ reviewbrief queue examples/multi_agent_sources.json
| rank | id | agent  | path                          | risk | est min | flags        |
|------|----|--------|-------------------------------|------|---------|--------------|
| 1    | X1 | codex  | src/auth/login.py             |  10  | 35      | CONTRADICTED |
| 2    | C1 | claude | src/auth/login.py             |   9  | 31      | CONTRADICTED |
| 3    | C2 | claude | db/migrations/009_add_lock... |   7  | 43      | -            |
| 4    | P1 | planner| infra/queue.py                |   5  | 31      | -            |
```

The contradicted auth changes rise to the top; the untested migration
follows on kind weight. Reject criteria per item: the migration's say
"reject unless the migration has a reversible down() path"; the auth
changes' say "reject unless the permission check has a test proving both
allow and deny paths".

## Usage

```
reviewbrief contradictions <source.json> [...]   # who disagrees with whom
reviewbrief queue         <source.json> [...]   # ranked, with minutes
reviewbrief grader        <source.json> [...]   # who graded their own work
reviewbrief all           <source.json> [...]   # everything + summary
```

Every command takes `--json`. Exit codes: `0` clean, `1` contradictions
found / grader warn, `2` grader fail or usage error — never a traceback.

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

Apache-2.0. Built by the bugyal coding agent; verified 35/35 tests from a
clean clone, live-run on a three-agent fixture shipped in
`examples/`.
