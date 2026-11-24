"""Rendering."""
from __future__ import annotations

import json


def render_contradictions(con: dict) -> str:
    out = ["# cross-agent contradiction report", ""]
    c = con["counts"]
    out.append(f"cross-agent contradictions: {c['cross_agent']} | "
               f"self-contradictions: {c['self']}")
    if con["contradictions"]:
        for x in con["contradictions"]:
            out += ["", f"## {x['subject']} ({x['kind']})", "",
                    f"- {x['agent_a']} claims: {x['claim_a']}",
                    f"- {x['agent_b']} claims: {x['claim_b']}", "",
                    f"resolution: {x['resolution']}"]
    else:
        out += ["", "No opposing claims on shared subjects."]
    if con["self_contradictions"]:
        out += ["", "self-contradictions (one agent, opposing claims):"]
        out += [f"- {s['agent']} on {s['subject']}: {s['claim_a']} vs "
                f"{s['claim_b']}" for s in con["self_contradictions"]]
    return "\n".join(out)


def render_queue(queue: dict) -> str:
    out = ["# risk-ranked review queue", ""]
    out.append("| rank | id | agent | path | risk | est min | flags |")
    out.append("|---|---|---|---|---|---|---|")
    for i, r in enumerate(queue["queue"], 1):
        flags = []
        if r["contradicted"]:
            flags.append("CONTRADICTED")
        if r["grader_flag"]:
            flags.append("GRADER")
        out.append(f"| {i} | {r['id']} | {r['agent']} | {r['path']} | "
                   f"{r['risk']} | {r['review_minutes_est']} | "
                   f"{','.join(flags) or '-'} |")
    for i, r in enumerate(queue["queue"], 1):
        out += ["", f"## {i}. {r['id']} — {r['path']} "
                    f"(risk {r['risk']}, ~{r['review_minutes_est']} min)", "",
                f"{r['description']}  _({r['agent']})_", "",
                "risk factors: " + ", ".join(r["risk_factors"]),
                "minutes arithmetic: " + r["minutes_arithmetic"],
                "reject criteria:"]
        out += [f"- {c}" for c in r["reject_criteria"]]
    out += ["", "_Review minutes are estimates (base + lines/25 + penalties), "
                "printed with their arithmetic._"]
    return "\n".join(out)


def render_grader(grader: dict) -> str:
    out = ["# grader-trust check", ""]
    c = grader["counts"]
    out.append(f"rewritten_by_author={c['rewritten_by_author']} "
               f"unknown_provenance={c['unknown_provenance']} ok={c['ok']}")
    flagged = [r for r in grader["results"] if r["status"] != "ok"]
    if flagged:
        out += ["", "flagged:"]
        out += [f"- [{r['status']}] {r['path']}: {r['reason']}"
                for r in flagged]
    out += ["", f"verdict: {grader['verdict'].upper()}"]
    out += [f"- {r}" for r in grader["reasons"]]
    out += ["", "A test rewritten by the agent that wrote the code is not "
                "independent evidence. Treat flagged graders as claims, not "
                "verification."]
    return "\n".join(out)


def render_summary(parts: dict) -> str:
    out = ["# reviewbrief — multi-agent triage summary", ""]
    if "contradictions" in parts:
        c = parts["contradictions"]["counts"]
        out.append(f"- contradictions: {c['cross_agent']} cross-agent, "
                   f"{c['self']} self")
    if "queue" in parts:
        q = parts["queue"]["queue"]
        total_min = sum(r["review_minutes_est"] for r in q)
        out.append(f"- review queue: {len(q)} item(s), "
                   f"~{total_min} min total (est)")
    if "grader" in parts:
        g = parts["grader"]["counts"]
        out.append(f"- grader trust: {g['rewritten_by_author']} authored "
                   f"re-writes, {g['unknown_provenance']} unknown")
    return "\n".join(out)


def dumps(data) -> str:
    return json.dumps(data, indent=1)
