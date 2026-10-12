import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .agent import render_issue, run_triage
from .audit import AuditLog
from .github import GitHub
from .render import suggestion_card
from .schema import TriageResult
from .tools import ToolResult, run_tool


def main() -> None:
    p = argparse.ArgumentParser(prog="triage", description="Read-only triage agent for astral-sh/uv issues")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="triage one issue (calls the Claude API)")
    r.add_argument("issue", type=int)
    r.add_argument("--log-dir", default="runs")
    r.add_argument("--markdown", action="store_true", help="print a suggestion card instead of JSON")
    c = sub.add_parser("render", help="render a saved triage result as a suggestion card")
    c.add_argument("result_json")
    c.add_argument("--issue", type=int, required=True)
    c.add_argument("--reporter-label")
    s = sub.add_parser("show-input", help="print exactly what the agent would see (no API key needed)")
    s.add_argument("issue", type=int)
    t = sub.add_parser("tool", help="run one agent tool for an issue (lets an external model host use the same tools)")
    t.add_argument("issue", type=int)
    t.add_argument("name")
    t.add_argument("input_json")
    t.add_argument("--log", required=True, help="JSONL audit file to append to")
    args = p.parse_args()

    if args.cmd == "show-input":
        print(render_issue(GitHub().issue_snapshot(args.issue)))
        return

    if args.cmd == "tool":
        gh = GitHub()
        issue = gh.issue_snapshot(args.issue)
        log_path = Path(args.log)
        log = AuditLog(log_path.parent, run_id=log_path.stem)
        try:
            raw = json.loads(args.input_json)
        except json.JSONDecodeError as e:
            raw = None
            out = ToolResult(content=f"input_json is not valid JSON: {e}", is_error=True)
        if raw is not None:
            out = run_tool(args.name, raw, gh=gh, issue=issue)
        log.write("tool_call", name=args.name, input=raw)
        log.write("tool_result", is_error=out.is_error, content=out.content, seen_issue_numbers=out.seen_issue_numbers)
        print(("ERROR: " if out.is_error else "") + out.content)
        return

    if args.cmd == "render":
        triage = TriageResult.model_validate_json(Path(args.result_json).read_text())
        print(suggestion_card(args.issue, triage, args.reporter_label))
        return

    res = run_triage(args.issue, log_dir=args.log_dir)
    if args.markdown and res.triage:
        print(suggestion_card(res.issue, res.triage))
        sys.exit(0 if res.status == "ok" else 2)
    out = asdict(res)
    out["triage"] = res.triage.model_dump() if res.triage else None
    print(json.dumps(out, indent=2))
    sys.exit(0 if res.status == "ok" else 2)
