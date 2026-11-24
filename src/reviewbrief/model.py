"""Shared types + multi-source schema adapters.

Every source document is JSON: {"agent", "source_kind", "claims": [...],
"changes": [...], "tests_touched": [...]}. Claims: {"claim", "kind",
"subject"}. Changes (hunks/tasks): {"id", "path", "description",
"lines_changed", "tests_added", "kind"}. Tests touched: {"path",
"rewritten_by", "prev_author"}.

source_kind selects the adapter: "claude_code" | "codex" | "planner" |
"generic". Adapters normalise field names (e.g. codex uses " filepath",
claude "path"; planner nests under "tasks") so the rest of the pipeline
sees one shape. Unknown source_kind is an error, not a guess.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


class UsageError(Exception):
    """User-facing CLI misuse: rendered as `reviewbrief: <msg>`, exit 2."""


CLAIM_KINDS = ("file_contains", "file_absent", "tests_pass", "tests_fail",
               "task_done", "task_blocked")
CHANGE_KINDS = ("feature", "fix", "refactor", "test", "infra", "migration",
                "docs")


@dataclass
class Claim:
    agent: str
    kind: str
    subject: str
    claim: str

    def key(self) -> tuple:
        # subject-only key: opposing kinds must land in the same bucket to
        # be paired as contradictions (the kind comparison happens at
        # pairing time in contradictions.py)
        return (self.subject,)


@dataclass
class Change:
    id: str
    agent: str
    path: str
    description: str
    lines_changed: int = 0
    tests_added: bool = False
    kind: str = "feature"


@dataclass
class TestTouched:
    # pytest tries to collect any class named Test*; this is a data model,
    # not a test class
    __test__ = False

    path: str
    rewritten_by: str          # agent that rewrote the test file
    prev_author: str | None    # previous attested author, if known


@dataclass
class SourceDoc:
    agent: str
    source_kind: str
    claims: list[Claim] = field(default_factory=list)
    changes: list[Change] = field(default_factory=list)
    tests_touched: list[TestTouched] = field(default_factory=list)


# ---- adapters: normalise each vendor's field names to the canonical shape

def _norm_claim(agent: str, c: dict) -> Claim:
    kind = c.get("kind") or c.get("type") or ""
    if kind not in CLAIM_KINDS:
        raise UsageError(
            f"claim kind {kind!r} not in {CLAIM_KINDS} (agent {agent})")
    subject = c.get("subject") or c.get("path") or ""
    claim = c.get("claim") or c.get("statement") or ""
    if not claim:
        raise UsageError(f"claim without text (agent {agent})")
    return Claim(agent=agent, kind=kind, subject=str(subject), claim=str(claim))


def _norm_change(agent: str, c: dict) -> Change:
    cid = c.get("id") or c.get("change_id") or ""
    if not cid:
        raise UsageError(f"change without id (agent {agent})")
    kind = c.get("kind") or c.get("type") or "feature"
    if kind not in CHANGE_KINDS:
        raise UsageError(
            f"change kind {kind!r} not in {CHANGE_KINDS} (agent {agent})")
    return Change(
        id=str(cid), agent=agent,
        path=str(c.get("path") or c.get("filepath") or ""),
        description=str(c.get("description") or c.get("summary") or ""),
        lines_changed=int(c.get("lines_changed") or c.get("lines") or 0),
        tests_added=bool(c.get("tests_added") or c.get("with_tests") or False),
        kind=kind)


def _norm_test(agent: str, t: dict) -> TestTouched:
    path = t.get("path") or t.get("filepath") or ""
    if not path:
        raise UsageError(f"tests_touched entry without path (agent {agent})")
    return TestTouched(
        path=str(path),
        rewritten_by=str(t.get("rewritten_by") or agent),
        prev_author=t.get("prev_author") or t.get("previous_author"))


_ADAPTERS = {
    "generic": {
        "claims": "claims", "changes": "changes", "tests": "tests_touched"},
    "claude_code": {
        "claims": "claims", "changes": "changes", "tests": "tests_touched"},
    "codex": {
        # codex outputs use "statements" for claims
        "claims": "statements", "changes": "changes", "tests": "tests_touched"},
    "planner": {
        # planner nests tasks under "tasks" and calls them plan items
        "claims": "assertions", "changes": "tasks", "tests": "tests_touched"},
}


def load_source(path: str) -> SourceDoc:
    """Load ONE source document. For a file containing a top-level list,
    use load_source_file()."""
    docs = load_source_file(path)
    if len(docs) != 1:
        raise UsageError(
            f"{path} contains {len(docs)} documents; pass it once per "
            "document or use the CLI which accepts lists")
    return docs[0]


def load_source_file(path: str) -> list[SourceDoc]:
    """Load one or many source documents from a file (object or list)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as exc:
        raise UsageError(f"source JSON invalid: {path} ({exc})") from exc
    items = data if isinstance(data, list) else [data]
    return [_load_one(item, f"{path}[{i}]") for i, item in enumerate(items)]


def _load_one(data, path: str) -> SourceDoc:
    if not isinstance(data, dict):
        raise UsageError(f"source must be a JSON object: {path}")
    agent = data.get("agent")
    if not agent:
        raise UsageError(f"source missing 'agent': {path}")
    source_kind = data.get("source_kind", "generic")
    if source_kind not in _ADAPTERS:
        raise UsageError(
            f"source_kind {source_kind!r} not supported "
            f"(known: {sorted(_ADAPTERS)}) in {path}")
    ad = _ADAPTERS[source_kind]
    doc = SourceDoc(agent=str(agent), source_kind=source_kind)
    for item in data.get(ad["claims"], []) or []:
        doc.claims.append(_norm_claim(str(agent), item))
    for item in data.get(ad["changes"], []) or []:
        doc.changes.append(_norm_change(str(agent), item))
    for item in data.get(ad["tests"], []) or []:
        doc.tests_touched.append(_norm_test(str(agent), item))
    return doc
