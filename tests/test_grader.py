"""Grader-trust tests."""
from reviewbrief.grader import grader_trust
from reviewbrief.model import SourceDoc, TestTouched


def doc(*tests):
    d = SourceDoc(agent="a", source_kind="generic")
    d.tests_touched.extend(tests)
    return d


def test_author_rewrite_flagged():
    t = grader_trust([doc(TestTouched(path="t.py", rewritten_by="claude",
                                      prev_author="claude"))])
    assert t["results"][0]["status"] == "rewritten_by_author"
    assert t["verdict"] == "fail"


def test_independent_ok():
    t = grader_trust([doc(TestTouched(path="t.py", rewritten_by="codex",
                                      prev_author="claude"))])
    assert t["verdict"] == "pass"


def test_unknown_provenance_flagged():
    t = grader_trust([doc(TestTouched(path="t.py", rewritten_by="planner",
                                      prev_author=None))])
    assert t["results"][0]["status"] == "unknown_provenance"
    assert t["verdict"] == "fail"


def test_mixed_counts():
    t = grader_trust([doc(
        TestTouched(path="a.py", rewritten_by="codex", prev_author="claude"),
        TestTouched(path="b.py", rewritten_by="claude", prev_author="claude"),
        TestTouched(path="c.py", rewritten_by="planner", prev_author=None),
    )])
    assert t["counts"] == {"rewritten_by_author": 1,
                           "unknown_provenance": 1, "ok": 1}
    assert t["verdict"] == "fail"


def test_empty():
    t = grader_trust([doc()])
    assert t["verdict"] == "pass"
    assert t["results"] == []
