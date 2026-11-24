"""Grader-trust check: tests rewritten by their author are not independent evidence.

A test file whose current author == its previous attested author, or whose
provenance is missing entirely, cannot serve as independent verification of
the code it grades. Flag levels:
  rewritten_by_author  — same agent wrote the code and re-graded it
  unknown_provenance   — no prev_author recorded: cannot establish
                         independence
  ok                   — different attested authors on both sides
"""
from __future__ import annotations

from .model import SourceDoc


def grader_trust(docs: list[SourceDoc]) -> dict:
    results = []
    counts = {"rewritten_by_author": 0, "unknown_provenance": 0, "ok": 0}
    for d in docs:
        for t in d.tests_touched:
            if not t.prev_author:
                status = "unknown_provenance"
                reason = ("no previous attested author recorded; "
                          "independence unverifiable")
            elif t.prev_author == t.rewritten_by:
                status = "rewritten_by_author"
                reason = (f"{t.rewritten_by} rewrote the test that grades "
                          f"its own change (prev author {t.prev_author})")
            else:
                status = "ok"
                reason = (f"independent: {t.prev_author} -> "
                          f"{t.rewritten_by}")
            results.append({"path": t.path, "rewritten_by": t.rewritten_by,
                            "prev_author": t.prev_author, "status": status,
                            "reason": reason})
            counts[status] += 1
    # the code-side pairing: does the same agent have changes in the same
    # paths? handled at queue level via grader_flag; here we just report.
    if counts["rewritten_by_author"] or counts["unknown_provenance"]:
        verdict = "fail"
        reasons = [f"{counts['rewritten_by_author']} test file(s) rewritten "
                   f"by their own author",
                   f"{counts['unknown_provenance']} with unknown provenance"]
    else:
        verdict = "pass"
        reasons = ["all touched test files have independent attested "
                   "authors"]
    return {"results": results, "counts": counts, "verdict": verdict,
            "reasons": reasons}
