"""Multi-source ingestion + adapter tests (all three vendor shapes)."""
import pytest

from reviewbrief.model import SourceDoc, load_source


def test_generic_and_codex_and_planner_adapters(tmp_path):
    g = tmp_path / "g.json"
    g.write_text("""{"agent":"a","source_kind":"generic",
      "claims":[{"claim":"x exists","kind":"file_contains","subject":"p"}],
      "changes":[{"id":"1","path":"p","description":"d","lines_changed":5}],
      "tests_touched":[]}""")
    d1 = load_source(str(g))
    assert d1.claims[0].kind == "file_contains"

    cx = tmp_path / "cx.json"
    cx.write_text("""{"agent":"b","source_kind":"codex",
      "statements":[{"statement":"x exists","kind":"file_contains","subject":"p","filepath":"p"}],
      "changes":[{"id":"2","filepath":"q","summary":"dd","lines":9,"type":"fix"}],
      "tests_touched":[]}""")
    d2 = load_source(str(cx))
    assert d2.claims[0].kind == "file_contains"
    assert d2.changes[0].lines_changed == 9

    pl = tmp_path / "pl.json"
    pl.write_text("""{"agent":"c","source_kind":"planner",
      "assertions":[{"statement":"done","kind":"task_done","subject":"t"}],
      "tasks":[{"id":"3","path":"r","summary":"ddd","lines":3,"kind":"infra"}],
      "tests_touched":[]}""")
    d3 = load_source(str(pl))
    assert d3.claims[0].kind == "task_done"
    assert d3.changes[0].kind == "infra"


def test_unknown_source_kind_rejected(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"agent":"a","source_kind":"unknown_vendor"}')
    with pytest.raises(Exception, match="not supported"):
        load_source(str(p))


def test_missing_agent_rejected(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"source_kind":"generic"}')
    with pytest.raises(Exception, match="missing 'agent'"):
        load_source(str(p))


def test_bad_claim_kind_rejected(tmp_path):
    p = tmp_path / "x.json"
    p.write_text('{"agent":"a","claims":[{"claim":"x","kind":"vibes"}]}')
    with pytest.raises(Exception, match="claim kind"):
        load_source(str(p))


def test_invalid_json_rejected(tmp_path):
    p = tmp_path / "x.json"
    p.write_text("{nope")
    with pytest.raises(Exception, match="invalid"):
        load_source(str(p))
