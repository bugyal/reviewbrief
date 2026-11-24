"""Risk queue tests: factor arithmetic, ordering, reject criteria, minutes."""
from reviewbrief.model import Change, SourceDoc, TestTouched
from reviewbrief.risk import (build_queue, reject_criteria, review_minutes,
                              risk_score)


def mk(id="C1", path="src/x.py", desc="thing", lines=30, tests=True,
       kind="feature"):
    return Change(id=id, agent="a", path=path, description=desc,
                  lines_changed=lines, tests_added=tests, kind=kind)


def test_baseline_feature_score():
    s, factors = risk_score(mk(), set(), set())
    assert s == 2          # kind=feature
    assert factors[0] == "kind=feature:2"


def test_auth_path_adds_weight():
    s, _ = risk_score(mk(path="src/auth/login.py"), set(), set())
    assert s == 2 + 3


def test_large_diff_adds_more_than_small():
    s_small, _ = risk_score(mk(lines=60), set(), set())
    s_big, _ = risk_score(mk(lines=500), set(), set())
    assert s_big > s_small


def test_no_tests_penalty():
    s_with, _ = risk_score(mk(tests=True), set(), set())
    s_without, _ = risk_score(mk(tests=False), set(), set())
    assert s_without == s_with + 2


def test_contradiction_and_grader_flags_add():
    s0, _ = risk_score(mk(path="f.py"), set(), set())
    s1, _ = risk_score(mk(path="f.py"), {"f.py"}, set())
    s2, _ = risk_score(mk(path="f.py"), {"f.py"}, {"f.py"})
    assert s1 == s0 + 4
    assert s2 == s1 + 3


def test_docs_kind_immune_to_no_tests():
    s, factors = risk_score(mk(kind="docs", tests=False), set(), set())
    assert not any("no_tests" in f for f in factors)


def test_queue_sorted_by_risk_desc():
    d = SourceDoc(agent="a", source_kind="generic")
    d.changes.extend([
        mk(id="low", lines=10, kind="docs"),
        mk(id="high", path="db/m.py", desc="migration", lines=500,
           tests=False, kind="migration"),
    ])
    q = build_queue([d])
    assert q["queue"][0]["id"] == "high"


def test_reject_criteria_migration_and_auth():
    crit = reject_criteria(mk(path="db/migrations/x.py", kind="migration",
                              desc="auth table"))
    assert any("down()" in c or "reversible" in c for c in crit)
    assert any("allow and deny" in c for c in crit)


def test_reject_criteria_never_bypass():
    for change in (mk(), mk(kind="migration", desc="auth token store",
                            path="db/mig.py")):
        for c in reject_criteria(change):
            assert "skip review" not in c.lower()
            assert "bypass" not in c.lower()
            assert "approve without" not in c.lower()


def test_minutes_arithmetic_visible():
    ch = mk(lines=100, tests=False)
    mins, arith = review_minutes(ch, score=5, contradicted=True)
    # base 15 + 100//25=4 + 10 + 15 = 44
    assert mins == 44
    assert "base(feature)=15" in arith


def test_grader_flag_flows_into_queue():
    d = SourceDoc(agent="a", source_kind="generic")
    d.changes.append(mk(id="C1", path="tests/test_x.py"))
    d.tests_touched.append(TestTouched(path="tests/test_x.py",
                                       rewritten_by="a", prev_author="a"))
    q = build_queue([d])
    assert q["queue"][0]["grader_flag"] is True
    assert "tests/test_x.py" in q["grader_flagged_paths"]
