"""Collect prototype (Claude Code subagent) answers and apply the same code guardrails as agent.py.

    uv run python evals/collect_proto.py runs/holdout evals/holdout_key.json

Reads <dir>/<issue>.result.json and the tool log <dir>/<issue>.jsonl, writes <dir>/results.json.
Invalid or missing answers are reported, never silently dropped.
"""

import json
import sys
from pathlib import Path

from pydantic import ValidationError

from triage.agent import apply_guardrails
from triage.github import IssueSnapshot
from triage.schema import TriageResult


def main() -> None:
    run_dir, key_path = Path(sys.argv[1]), sys.argv[2]
    key = json.load(open(key_path))
    out, problems = {}, []
    for k in key:
        n = k["issue"]
        f = run_dir / f"{n}.result.json"
        if not f.exists():
            problems.append(f"#{n}: no result file")
            continue
        try:
            t = TriageResult.model_validate(json.loads(f.read_text()))
        except (json.JSONDecodeError, ValidationError) as e:
            problems.append(f"#{n}: invalid result ({str(e).splitlines()[0]})")
            continue
        seen: set[int] = set()
        log = run_dir / f"{n}.jsonl"
        if log.exists():
            for line in log.read_text().splitlines():
                seen.update(json.loads(line).get("seen_issue_numbers") or [])
        labels = [k["reporter_label"]] if k["reporter_label"] else []
        snap = IssueSnapshot(number=n, title="", body="", reporter="", created_at="", reporter_labels=labels)
        t, notes = apply_guardrails(t, issue=snap, seen=seen)
        for note in notes:
            print(f"#{n} guardrail: {note}")
        out[str(n)] = t.model_dump()
    (run_dir / "results.json").write_text(json.dumps(out, indent=1))
    print(f"collected {len(out)}/{len(key)} -> {run_dir / 'results.json'}")
    for p in problems:
        print("PROBLEM", p)


if __name__ == "__main__":
    main()
