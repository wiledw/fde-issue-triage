"""Build a stratified, leak-checked holdout set of real uv issues with maintainer ground truth.

    # 1. download a pool of issues + their event timelines (read-only, via the gh CLI)
    uv run python evals/build_holdout.py fetch --created 2026-04-02..2026-06-22 --pool data/pool3
    # 2. pick 20 issues and write the answer key
    uv run python evals/build_holdout.py pick --pool data/pool3 --seed 20261014 --out evals/holdout3_key.json

Ground truth = what a maintainer actually did (relabels, needs-mre/external labels, closing
as duplicate). Only issues a maintainer touched are eligible: silence is not confirmation.

Excluded automatically: every issue in an existing answer key, every issue number cited in
the repo's docs, prompts, adjudication sheets and earlier agent outputs. A prompt or note that
mentions an issue could otherwise leak its answer.
"""

import argparse
import collections
import json
import random
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = "astral-sh/uv"
TYPES = {"bug", "enhancement", "question", "documentation"}
# Mix of outcomes, roughly following the audit; every category represented.
QUOTA = {
    "confirmed-bug": 5,
    "bug->question": 4,
    "confirmed-enhancement": 3,
    "bug->enhancement": 2,
    "needs-mre": 2,
    "external": 2,
    "duplicate": 2,
}
ROOT = Path(__file__).resolve().parent.parent


def gh(*args: str) -> str:
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def fetch(created: str, pool: Path, limit: int) -> None:
    (pool / "tl").mkdir(parents=True, exist_ok=True)
    fields = "number,title,labels,state,stateReason,createdAt,closedAt,comments,author"
    issues = gh("issue", "list", "-R", REPO, "--state", "all", "--search", f"created:{created}",
                "--limit", str(limit), "--json", fields)
    (pool / "issues.json").write_text(issues)
    numbers = [x["number"] for x in json.loads(issues)]

    def timeline(n: int) -> None:
        out = pool / "tl" / f"{n}.json"
        if not out.exists():
            out.write_text(gh("api", f"repos/{REPO}/issues/{n}/timeline?per_page=100"))

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(timeline, numbers))
    print(f"fetched {len(numbers)} issues into {pool}")


def already_used() -> set[int]:
    """Issues in any answer key, or cited anywhere an agent or a prompt-writer could have seen."""
    used: set[int] = set()
    for key in [*ROOT.glob("evals/*_key*.json"), ROOT / "audit/answer_key.json"]:
        for r in json.loads(key.read_text()):
            used.add(r["issue"])
            if r.get("duplicate_of"):
                used.add(r["duplicate_of"])
            used |= {int(n) for n in re.findall(r"#(\d{3,6})", r.get("maintainer_first_reply") or "")}
    docs = [*ROOT.glob("*.md"), *ROOT.glob("audit/*.md"), *ROOT.glob("evals/*.md"), *ROOT.glob("docs/*.md"),
            *ROOT.glob("prompts/*/*.md"), *ROOT.glob("src/triage/prompts/*.md")]
    for f in docs:
        used |= {int(n) for n in re.findall(r"#(\d{3,6})", f.read_text())}
    for f in ROOT.glob("runs/**/*.json*"):
        used |= {int(n) for n in re.findall(r'"number": ?(\d+)', f.read_text())}
    return used


def ground_truth(issue: dict, events: list) -> dict | None:
    reporter = issue["author"]["login"]
    added, removed, first_reply, maintainer_replied = set(), set(), None, False
    for e in events:
        actor = (e.get("actor") or e.get("user") or {}).get("login", "")
        kind = e.get("event")
        if kind in ("labeled", "unlabeled") and actor != reporter and not actor.endswith("[bot]"):
            (added if kind == "labeled" else removed).add(e["label"]["name"])
        if kind == "commented" and actor != reporter and not actor.endswith("[bot]"):
            maintainer_replied = True
            first_reply = first_reply or e["body"][:240].replace("\n", " ")
    final = {lbl["name"] for lbl in issue["labels"]}
    reporter_type = next(iter(sorted({lbl for lbl in (removed | final) if lbl in TYPES} - added)), None)
    final_type = next(iter(sorted(final & TYPES)), None)
    flags = sorted({f for f in ("needs-mre", "external") if f in final}
                   | ({"duplicate"} if issue["stateReason"] == "DUPLICATE" else set()))
    touched = bool(added or removed or issue["stateReason"] in ("DUPLICATE", "NOT_PLANNED")
                   or (maintainer_replied and issue["state"] == "CLOSED"))
    if not (touched and maintainer_replied) or (reporter_type is None and final_type is None and not flags):
        return None
    if "bug" in removed and "question" in added:
        cat = "bug->question"
    elif "bug" in removed and "enhancement" in added:
        cat = "bug->enhancement"
    elif "duplicate" in flags:
        cat = "duplicate"
    elif "needs-mre" in flags:
        cat = "needs-mre"
    elif "external" in flags:
        cat = "external"
    elif final_type == "bug" and issue["stateReason"] == "COMPLETED":
        cat = "confirmed-bug"
    elif final_type == "enhancement":
        cat = "confirmed-enhancement"
    else:
        return None
    dup_of = None
    if "duplicate" in flags:
        for e in events:
            actor = (e.get("actor") or e.get("user") or {}).get("login", "")
            if e.get("event") == "commented" and not actor.endswith("[bot]"):
                m = re.search(r"[Dd]uplicate (?:of )?(?:https://github\.com/astral-sh/uv/issues/|#)(\d+)", e["body"])
                hits = [int(m.group(1))] if m else [int(x) for x in re.findall(r"(?:astral-sh/uv/issues/|#)(\d{3,6})\b", e["body"])][:1]
                dup_of = next((h for h in hits if h != issue["number"]), None)
                if dup_of:
                    break
    return dict(issue=issue["number"], category=cat, reporter_label=reporter_type, type=final_type, flags=flags,
                duplicate_of=dup_of, maintainer_first_reply=first_reply, title=issue["title"])


def pick(pool: Path, seed: int, out: Path) -> None:
    exclude = already_used()
    by_cat = collections.defaultdict(list)
    for issue in json.loads((pool / "issues.json").read_text()):
        if issue["number"] in exclude:
            continue
        row = ground_truth(issue, json.loads((pool / "tl" / f"{issue['number']}.json").read_text()))
        if row:
            by_cat[row["category"]].append(row)
    rnd = random.Random(seed)
    chosen = []
    for cat, n in QUOTA.items():
        rows = sorted(by_cat[cat], key=lambda r: r["issue"])
        rnd.shuffle(rows)
        chosen += rows[:n]
        print(f"{cat:22} available={len(rows):3} picked={min(n, len(rows))}")
    rnd.shuffle(chosen)
    out.write_text(json.dumps(chosen, indent=1))
    print(f"{len(chosen)} issues -> {out}  (excluded {len(exclude)} previously used/cited issues)")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch")
    f.add_argument("--created", required=True, help="GitHub date range, e.g. 2026-04-02..2026-06-22")
    f.add_argument("--pool", type=Path, required=True)
    f.add_argument("--limit", type=int, default=300)
    k = sub.add_parser("pick")
    k.add_argument("--pool", type=Path, required=True)
    k.add_argument("--seed", type=int, required=True)
    k.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    fetch(a.created, a.pool, a.limit) if a.cmd == "fetch" else pick(a.pool, a.seed, a.out)


if __name__ == "__main__":
    main()
