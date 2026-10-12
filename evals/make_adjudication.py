"""Build a human review sheet of every disagreement between the agent and the answer key.

    uv run python evals/make_adjudication.py runs/holdout/results.json evals/holdout_key.json evals/adjudication_v0.2.md

Only disagreements are listed. For each one the reviewer decides whether the agent
or the label was wrong, judged on what the first post supports.
"""

import json
import sys

FLAGS = (("needs_mre", "needs-mre"), ("likely_external", "external"))


def disagreements(r: dict, k: dict) -> list[str]:
    out = []
    if k["type"] is not None and r["type"] != k["type"]:
        out.append(f"type: agent `{r['type']}` vs label `{k['type']}`")
    for field, label in FLAGS:
        if r[field] != (label in k["flags"]):
            out.append(f"{label}: agent {'yes' if r[field] else 'no'} vs label {'yes' if label in k['flags'] else 'no'}")
    agent_dups = [d["number"] for d in r["possible_duplicates"]]
    is_dup = "duplicate" in k["flags"]
    if bool(agent_dups) != is_dup or (is_dup and k.get("duplicate_of") not in agent_dups):
        target = f"#{k['duplicate_of']}" if k.get("duplicate_of") else "none"
        listed = ", ".join(f"#{n}" for n in agent_dups) or "none"
        out.append(f"duplicate: agent listed {listed} vs maintainer's target {target}")
    return out


def main() -> None:
    results = json.load(open(sys.argv[1]))
    key = json.load(open(sys.argv[2]))
    lines = [
        "# Adjudication sheet",
        "",
        "For each disagreement, open the issue, read **the first post only**, and decide:",
        "",
        "- **agent wrong**: the first post supports the maintainer's call",
        "- **label wrong**: the first post supports the agent's call (label noise, or hindsight the agent couldn't see)",
        "- **ambiguous**: a reasonable maintainer could go either way",
        "",
        "Then read the thread and add a short *why*. Mark one box per disagreement line with `x`.",
        "",
    ]
    i = 0
    for k in key:
        r = results.get(str(k["issue"]))
        if r is None:
            continue
        diffs = disagreements(r, k)
        if not diffs:
            continue
        i += 1
        n = k["issue"]
        lines += [
            f"## {i}. #{n}: {k['title']}",
            f"https://github.com/astral-sh/uv/issues/{n} · reporter's label: `{k['reporter_label'] or 'none'}` · "
            f"agent escalated: **{'yes' if r['escalate_to_human'] else 'no'}** (confidence {r['confidence']})",
            "",
            f"**Agent's reasoning:** {r['rationale']}",
        ]
        if r["escalate_to_human"]:
            lines.append(f"**Why it escalated:** {r['escalation_reason']}")
        lines += [
            f"**Maintainer's first reply:** \"{k['maintainer_first_reply']}…\"",
            "",
            "| Disagreement | agent wrong | label wrong | ambiguous |",
            "|---|---|---|---|",
            *[f"| {d} | [ ] | [ ] | [ ] |" for d in diffs],
            "",
            "Why:",
            "",
        ]
    lines += [
        "---",
        "",
        "## Patterns",
        "After all items: which failure types repeat? Which would a prompt, tool, or guardrail change fix?",
        "",
    ]
    open(sys.argv[3], "w").write("\n".join(lines))
    print(f"{i} issues with disagreements -> {sys.argv[3]}")


if __name__ == "__main__":
    main()
