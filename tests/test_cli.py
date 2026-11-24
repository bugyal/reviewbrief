"""CLI end-to-end against the multi-agent example."""
import json
import os

import pytest

from reviewbrief.cli import main

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLE = os.path.join(HERE, "..", "examples", "multi_agent_sources.json")


def test_contradictions_found(capsys):
    rc = main(["contradictions", EXAMPLE])
    out = capsys.readouterr().out
    assert rc == 1
    # login.py: claude says file_contains, codex says file_absent
    assert "src/auth/login.py" in out
    assert "both cannot be true" in out
    assert "do not ask either agent" in out


def test_contradictions_json(capsys):
    rc = main(["--json", "contradictions", EXAMPLE])
    d = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert d["counts"]["cross_agent"] >= 2   # login.py + tests/


def test_queue_risk_order(capsys):
    rc = main(["queue", EXAMPLE])
    out = capsys.readouterr().out
    assert rc == 0
    assert "risk-ranked review queue" in out
    assert "reject criteria" in out
    assert "estimates" in out
    # migration with no tests must outrank the small feature
    assert "009_add_lockouts" in out


def test_queue_json_has_minutes_and_criteria(capsys):
    rc = main(["--json", "queue", EXAMPLE])
    d = json.loads(capsys.readouterr().out)
    assert rc == 0
    row = d["queue"][0]
    assert {"id", "risk", "risk_factors", "reject_criteria",
            "review_minutes_est", "minutes_arithmetic"} <= set(row)
    assert row["review_minutes_est"] > 0


def test_grader_flags_author_rewrite(capsys):
    rc = main(["grader", EXAMPLE])
    out = capsys.readouterr().out
    assert rc == 2   # fail
    assert "rewritten_by_author" in out
    assert "not independent evidence" in out


def test_all_summary(capsys):
    rc = main(["all", EXAMPLE])
    out = capsys.readouterr().out
    assert rc == 2
    assert "multi-agent triage summary" in out
    assert "contradictions:" in out
    assert "grader trust:" in out


def test_bad_source_is_usage_error(capsys, tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"agent":"a","source_kind":"mystery"}')
    rc = main(["queue", str(p)])
    assert rc == 2
    assert capsys.readouterr().err.startswith("reviewbrief:")


def test_single_source_no_contradictions(capsys, tmp_path):
    p = tmp_path / "one.json"
    p.write_text(json.dumps({
        "agent": "solo", "source_kind": "generic",
        "claims": [{"claim": "x", "kind": "file_contains",
                    "subject": "f"}],
        "changes": [{"id": "1", "path": "f", "description": "d",
                     "lines_changed": 5}],
        "tests_touched": []}))
    rc = main(["contradictions", str(p)])
    assert rc == 0
    assert "No opposing claims" in capsys.readouterr().out
