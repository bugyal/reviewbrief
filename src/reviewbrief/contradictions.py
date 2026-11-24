"""Cross-agent contradiction detection.

Pairing rule: two claims contradict when they are from DIFFERENT agents,
share the same (kind, subject) key, and their kinds are opposed:

  file_contains  <-> file_absent
  tests_pass     <-> tests_fail
  task_done      <-> task_blocked

Same-agent contradictions are a different signal (self-inconsistency) and
are reported separately, not as cross-agent contradictions. Claims with no
opposing partner are simply not contradictions; there is no fuzzy pairing.
"""
from __future__ import annotations

from collections import defaultdict

from .model import SourceDoc

OPPOSITES = {
    "file_contains": "file_absent",
    "file_absent": "file_contains",
    "tests_pass": "tests_fail",
    "tests_fail": "tests_pass",
    "task_done": "task_blocked",
    "task_blocked": "task_done",
}


def find_contradictions(docs: list[SourceDoc]) -> dict:
    by_key: dict[tuple, list] = defaultdict(list)
    for d in docs:
        for c in d.claims:
            by_key[c.key()].append(c)

    cross, self_contra = [], []
    seen = set()
    for (subject,), claims in by_key.items():
        for kind in {c.kind for c in claims}:
            opp = OPPOSITES.get(kind)
            if not opp:
                continue
            for a in claims:
                if a.kind != kind:
                    continue
                for b in claims:
                    if b is a or b.kind != opp:
                        continue
                    pair_id = (subject,
                               tuple(sorted([a.agent, b.agent])),
                               tuple(sorted([a.claim, b.claim])),
                               tuple(sorted([a.kind, b.kind])))
                    if pair_id in seen:
                        continue
                    seen.add(pair_id)
                    item = {
                        "subject": subject, "kind": kind,
                        "agent_a": a.agent, "claim_a": a.claim,
                        "agent_b": b.agent, "claim_b": b.claim,
                    }
                    if a.agent != b.agent:
                        item["resolution"] = (
                            f"both cannot be true; verify {subject} "
                            "directly (read the file / run the tests / "
                            "check the task state) — do not ask either "
                            "agent to adjudicate itself")
                        cross.append(item)
                    else:
                        item["agent"] = a.agent
                        self_contra.append(item)

    return {
        "contradictions": cross,
        "self_contradictions": self_contra,
        "counts": {"cross_agent": len(cross), "self": len(self_contra)},
    }
