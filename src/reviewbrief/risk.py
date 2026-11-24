"""Risk ranking: named factors, visible arithmetic, review-minute estimates.

Risk factors (each 0..N points, from config `risk_weights`, with defaults):
  kind            — migration/infra/feature base weights
  auth_or_secret  — path/description touches auth|secret|credential|permission
  lines_changed   — >400: 3, >150: 2, >50: 1
  no_tests        — change declares tests_added False and kind != docs/test
  contradicted    — the change's path is the subject of a cross-agent
                    contradiction
  grader_flag     — the change's path is a test file whose author rewrote it
                    (grader-trust flag)

Reject criteria are generated per change from the same facts: a migration
gets "no reversible up/down pair" etc. Generated criteria must never be a
bypass ("skip review") — a forbidden-vocabulary guard asserts that.

Review minutes = base_by_kind + lines/25 + 10 if no tests + 15 if
contradicted/grader-flagged. The formula is printed with the estimate.
"""
from __future__ import annotations

from .contradictions import find_contradictions
from .model import SourceDoc

DEFAULT_WEIGHTS = {
    "kind": {"migration": 4, "infra": 3, "feature": 2, "fix": 1,
             "refactor": 1, "test": 1, "docs": 0},
    "auth_or_secret": 3,
    "contradicted": 4,
    "grader_flag": 3,
}

MIGRATION_REJECT = [
    "reject unless the migration has a reversible down() path",
    "reject if it touches rows without a backup/rollout note",
]
AUTH_REJECT = [
    "reject unless the permission check has a test proving both allow and "
    "deny paths",
    "reject if any secret/credential appears inline (config, log, or "
    "default value)",
]
GENERAL_REJECT = [
    "reject if the description does not match what the diff does",
    "reject if error paths swallow exceptions silently",
]


def _auth_hit(change) -> bool:
    blob = (change.path + " " + change.description).lower()
    return any(k in blob for k in ("auth", "secret", "credential",
                                   "permission", "login", "token"))


def _is_grader_flagged(change, flagged_paths: set[str]) -> bool:
    return change.path in flagged_paths


def risk_score(change, contradicted_paths: set[str],
               flagged_paths: set[str],
               weights: dict | None = None) -> tuple[int, list[str]]:
    w = {**DEFAULT_WEIGHTS, **(weights or {})}
    factors = []
    score = w["kind"].get(change.kind, 1)
    factors.append(f"kind={change.kind}:{score}")
    if _auth_hit(change):
        score += w["auth_or_secret"]
        factors.append(f"auth/secret:+{w['auth_or_secret']}")
    lc = change.lines_changed
    if lc > 400:
        score += 3
        factors.append(f"lines={lc}:+3")
    elif lc > 150:
        score += 2
        factors.append(f"lines={lc}:+2")
    elif lc > 50:
        score += 1
        factors.append(f"lines={lc}:+1")
    if not change.tests_added and change.kind not in ("docs", "test"):
        score += 2
        factors.append("no_tests:+2")
    if change.path in contradicted_paths:
        score += w["contradicted"]
        factors.append(f"contradicted:+{w['contradicted']}")
    if _is_grader_flagged(change, flagged_paths):
        score += w["grader_flag"]
        factors.append(f"grader_flag:+{w['grader_flag']}")
    return score, factors


def reject_criteria(change) -> list[str]:
    out = []
    if change.kind == "migration":
        out += MIGRATION_REJECT
    if _auth_hit(change):
        out += AUTH_REJECT
    out += GENERAL_REJECT
    if not change.tests_added and change.kind not in ("docs", "test"):
        out.append("reject unless tests covering the new behaviour are "
                   "included in this change")
    # safety guard: never generate a bypass
    joined = " ".join(out).lower()
    for bad in ("skip review", "approve without", "bypass"):
        assert bad not in joined, f"unsafe reject criterion generated: {bad}"
    return out


def review_minutes(change, score: int,
                   contradicted: bool) -> tuple[int, str]:
    base = {"migration": 30, "infra": 20, "feature": 15, "fix": 10,
            "refactor": 15, "test": 8, "docs": 5}.get(change.kind, 15)
    mins = base + change.lines_changed // 25
    arith = [f"base({change.kind})={base}", f"+lines/{25}="
             f"{change.lines_changed // 25}"]
    if not change.tests_added and change.kind not in ("docs", "test"):
        mins += 10
        arith.append("+no_tests=10")
    if contradicted:
        mins += 15
        arith.append("+contradicted=15")
    return mins, " ".join(arith)


def build_queue(docs: list[SourceDoc], weights: dict | None = None) -> dict:
    con = find_contradictions(docs)
    contradicted_paths = {c["subject"] for c in con["contradictions"]}
    flagged_paths = {t.path for d in docs for t in d.tests_touched
                     if not t.prev_author
                     or t.rewritten_by == t.prev_author}
    rows = []
    for d in docs:
        for ch in d.changes:
            score, factors = risk_score(ch, contradicted_paths,
                                        flagged_paths, weights)
            mins, arith = review_minutes(
                ch, score, ch.path in contradicted_paths)
            rows.append({
                "id": ch.id, "agent": ch.agent, "path": ch.path,
                "description": ch.description, "kind": ch.kind,
                "lines_changed": ch.lines_changed,
                "risk": score, "risk_factors": factors,
                "reject_criteria": reject_criteria(ch),
                "review_minutes_est": mins, "minutes_arithmetic": arith,
                "contradicted": ch.path in contradicted_paths,
                "grader_flag": ch.path in flagged_paths,
            })
    rows.sort(key=lambda r: (-r["risk"], r["id"]))
    return {"queue": rows, "contradictions": con,
            "grader_flagged_paths": sorted(flagged_paths)}
