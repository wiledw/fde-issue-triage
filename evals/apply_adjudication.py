"""Turn a filled adjudication sheet into an adjudicated answer key.

    uv run python evals/apply_adjudication.py evals/adjudication_v0.2.md evals/holdout_key.json \
        runs/holdout/results.json evals/holdout_key_adjudicated.json

Per disagreement line:
  agent wrong -> key unchanged
  label wrong -> key takes the agent's value
  ambiguous   -> field listed in `ambiguous`; score.py leaves it out of grading
"""

import copy
import json
import re
import sys

FIELD_OF = {"type": "type", "needs-mre": "needs-mre", "external": "external", "duplicate": "duplicate"}
VERDICTS = ("agent wrong", "label wrong", "ambiguous")


def parse(md: str) -> dict[int, dict[str, str]]:
    out: dict[int, dict[str, str]] = {}
    issue = None
    for line in md.splitlines():
        m = re.match(r"## \d+\. #(\d+):", line)
        if m:
            issue = int(m.group(1))
            out[issue] = {}
            continue
        m = re.match(r"\| (type|needs-mre|external|duplicate):.*\|(.*)\|(.*)\|(.*)\|\s*$", line)
        if m and issue is not None:
            marks = [("[x]" in c.lower()) for c in m.groups()[1:]]
            if sum(marks) != 1:
                raise SystemExit(f"#{issue} {m.group(1)}: expected exactly one [x], found {sum(marks)}")
            out[issue][FIELD_OF[m.group(1)]] = VERDICTS[marks.index(True)]
    return out


def main() -> None:
    sheet, key_path, results_path, out_path = sys.argv[1:5]
    verdicts = parse(open(sheet).read())
    key = json.load(open(key_path))
    results = json.load(open(results_path))
    new = []
    for k in key:
        k = copy.deepcopy(k)
        v = verdicts.get(k["issue"], {})
        r = results.get(str(k["issue"]))
        k["adjudication"] = v
        k["ambiguous"] = sorted(f for f, verdict in v.items() if verdict == "ambiguous")
        for field, verdict in v.items():
            if verdict != "label wrong":
                continue
            if field == "type":
                k["type"] = r["type"]
            elif field == "duplicate":
                dups = [d["number"] for d in r["possible_duplicates"]]
                k["flags"] = sorted(set(k["flags"]) - {"duplicate"} | ({"duplicate"} if dups else set()))
                k["duplicate_of"] = dups[0] if dups else None
            else:
                agent_says = r["needs_mre"] if field == "needs-mre" else r["likely_external"]
                k["flags"] = sorted(set(k["flags"]) - {field} | ({field} if agent_says else set()))
        new.append(k)
    json.dump(new, open(out_path, "w"), indent=1)
    n = sum(len(v) for v in verdicts.values())
    counts = {x: sum(1 for v in verdicts.values() for y in v.values() if y == x) for x in VERDICTS}
    print(f"{n} verdicts on {len(verdicts)} issues: {counts} -> {out_path}")


if __name__ == "__main__":
    main()
