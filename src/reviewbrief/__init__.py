"""reviewbrief 2.0 — multi-agent review triage.

Ingest outputs from several coding agents (Claude Code, Codex, planner —
each a JSON document with its own schema adapter), then produce the three
things a reviewer of agent fleets actually needs:

1. **Cross-agent contradiction report** — agent A claims X, agent B claims
   not-X (file states, test results, task status). Deterministic: subjects
   are matched by path/subject key, claims classified into a fixed
   vocabulary (file_contains / file_absent / tests_pass / tests_fail /
   task_done / task_blocked), contradictions detected by pairing opposing
   claims on the same subject. Never "the model said" — the claim records
   are what the agents wrote to their output documents.
2. **Risk-ranked review queue** — every ingested hunk/task gets a risk
   score from named factors (touches auth/migrations/infra; large diff;
   untested; contradicted by another agent; grader-trust flag), a
   per-item **reject criteria** list (what would make a reviewer reject
   this), and an **estimated review minutes** with the arithmetic shown.
3. **Grader-trust check** — when an agent both writes code and rewrites the
   tests grading that code, the tests are not independent evidence.
   Flagged per test file: author agent vs previous attested author.

Honesty rules:

- Contradictions are computed from claim records, not from prose similarity;
  unmatched subjects are reported as unmatched, never force-paired.
- Risk scores show their factor arithmetic. Review minutes are estimates
  with the formula printed.
- The grader-trust check compares declared authors; missing provenance is
  flagged as unknown, not assumed clean.
- `main` returns exit codes and never leaks a traceback: usage problems
  render as `reviewbrief: <message>` on stderr, exit 2.
"""

__version__ = "2.0.0"
