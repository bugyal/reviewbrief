"""Contradiction detection tests."""
from reviewbrief.contradictions import find_contradictions
from reviewbrief.model import Claim, SourceDoc


def doc(agent, *claims):
    d = SourceDoc(agent=agent, source_kind="generic")
    d.claims.extend(claims)
    return d


def test_cross_agent_contradiction_detected():
    docs = [
        doc("claude", Claim("claude", "file_contains", "f.py", "has it")),
        doc("codex", Claim("codex", "file_absent", "f.py", "not there")),
    ]
    out = find_contradictions(docs)
    assert out["counts"]["cross_agent"] == 1
    x = out["contradictions"][0]
    assert x["subject"] == "f.py"
    assert {x["agent_a"], x["agent_b"]} == {"claude", "codex"}


def test_agreement_is_not_contradiction():
    docs = [
        doc("claude", Claim("claude", "file_contains", "f.py", "has it")),
        doc("codex", Claim("codex", "file_contains", "f.py", "also has")),
    ]
    out = find_contradictions(docs)
    assert out["counts"]["cross_agent"] == 0


def test_self_contradiction_reported_separately():
    docs = [doc("claude",
                Claim("claude", "tests_pass", "tests/", "green"),
                Claim("claude", "tests_fail", "tests/", "red"))]
    out = find_contradictions(docs)
    assert out["counts"]["cross_agent"] == 0
    assert out["counts"]["self"] == 1
    assert out["self_contradictions"][0]["agent"] == "claude"


def test_unmatched_subjects_not_force_paired():
    docs = [
        doc("claude", Claim("claude", "file_contains", "f.py", "has it")),
        doc("codex", Claim("codex", "file_absent", "g.py", "not there")),
    ]
    out = find_contradictions(docs)
    assert out["counts"]["cross_agent"] == 0


def test_three_way_only_pairs_opposites():
    docs = [
        doc("claude", Claim("claude", "tests_pass", "t/", "green")),
        doc("codex", Claim("codex", "tests_fail", "t/", "red")),
        doc("planner", Claim("planner", "tests_fail", "t/", "also red")),
    ]
    out = find_contradictions(docs)
    # codex-vs-claude, planner-vs-claude; codex-vs-planner agree
    assert out["counts"]["cross_agent"] == 2


def test_resolution_never_self_adjudication():
    docs = [
        doc("claude", Claim("claude", "task_done", "t1", "done")),
        doc("codex", Claim("codex", "task_blocked", "t1", "blocked")),
    ]
    out = find_contradictions(docs)
    assert "do not ask either agent to adjudicate itself" \
        in out["contradictions"][0]["resolution"]
