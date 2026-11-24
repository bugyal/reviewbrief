"""reviewbrief CLI.

Commands:
  contradictions <source.json> [...]   cross-agent contradiction report
  queue <source.json> [...]            risk-ranked review queue
  grader <source.json> [...]           grader-trust check
  all <source.json> [...]              everything, with a summary

Exit codes: 0 ok, 1 warnings (contradictions / grader flags found),
2 fail (grader failure or usage error) — never a traceback.
"""
from __future__ import annotations

import argparse
import sys

from . import __version__
from .contradictions import find_contradictions
from .grader import grader_trust
from .model import UsageError, load_source_file
from .report import (dumps, render_contradictions, render_grader,
                     render_queue, render_summary)
from .risk import build_queue

RANK = {"pass": 0, "warn": 1, "fail": 2}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="reviewbrief",
        description="Multi-agent review triage: contradictions, risk-ranked "
                    "queue with reject criteria and time estimates, "
                    "grader-trust check.")
    p.add_argument("--version", action="version",
                   version=f"reviewbrief {__version__}")
    p.add_argument("--json", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, help_ in (("contradictions", "cross-agent contradiction report"),
                        ("queue", "risk-ranked review queue"),
                        ("grader", "grader-trust check"),
                        ("all", "everything + summary")):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("sources", nargs="+", help="agent source JSON paths")
    return p


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        docs = []
        for s in args.sources:
            docs.extend(load_source_file(s))
        if len({d.agent for d in docs}) < len(docs) and args.cmd != "grader":
            # duplicate agent docs are allowed but noted
            pass

        if args.cmd == "contradictions":
            con = find_contradictions(docs)
            print(dumps(con) if args.json else render_contradictions(con))
            return 1 if con["counts"]["cross_agent"] else 0

        if args.cmd == "queue":
            q = build_queue(docs)
            print(dumps(q) if args.json else render_queue(q))
            return 0

        if args.cmd == "grader":
            g = grader_trust(docs)
            print(dumps(g) if args.json else render_grader(g))
            return RANK.get(g["verdict"], 1)

        # all
        con = find_contradictions(docs)
        q = build_queue(docs)
        g = grader_trust(docs)
        rc = max(1 if con["counts"]["cross_agent"] else 0,
                 RANK.get(g["verdict"], 1))
        if args.json:
            print(dumps({"contradictions": con, "queue": q["queue"],
                         "grader_trust": g}))
        else:
            print(render_summary({"contradictions": con, "queue": q,
                                  "grader": g}))
            print()
            print(render_contradictions(con))
            print()
            print(render_queue(q))
            print()
            print(render_grader(g))
        return rc
    except UsageError as exc:
        print(f"reviewbrief: {exc}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as exc:
        print(f"reviewbrief: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
