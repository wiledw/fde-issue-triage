"""Score triage results against an answer key.

    uv run python evals/score.py RESULTS.json KEY.json

RESULTS.json maps issue number -> TriageResult dict (after guardrails).
KEY.json is a list of {issue, reporter_label, type, flags, duplicate_of?}.

Headline = two numbers that pull against each other:
  1. escalation rate          - share of issues a maintainer still has to decide
  2. accuracy when autonomous - type correct on the issues the agent did NOT escalate
Plus the one failure that destroys trust: wrong AND not escalated ("confident misses").

Grading choices (see ITERATIONS.md before changing):
- `type` is graded only where the key has one (some issues never got a type label).
- Flags are graded against the maintainer's final labels, including hindsight labels
  such as needs-mre after a failed reproduction. That is a known bias against the agent.
"""

import json
import sys

from triage.schema import TriageResult


def score(results: dict, key: list[dict]) -> dict:
    rows = []
    for k in key:
        n = str(k["issue"])
        if n not in results:
            rows.append({"issue": k["issue"], "missing": True})
            continue
        t = TriageResult.model_validate(results[n])
        truth_flags = set(k["flags"])
        amb = set(k.get("ambiguous", []))  # adjudicated as ambiguous -> not graded
        dup_numbers = {d.number for d in t.possible_duplicates}
        flags = {
            "needs_mre": (t.needs_mre, "needs-mre" in truth_flags),
            "external": (t.likely_external, "external" in truth_flags),
            "duplicate": (bool(dup_numbers), "duplicate" in truth_flags),
        }
        for f, label in (("needs_mre", "needs-mre"), ("external", "external"), ("duplicate", "duplicate")):
            if label in amb:
                flags[f] = None
        rows.append(
            {
                "issue": k["issue"],
                "missing": False,
                "escalated": t.escalate_to_human,
                "type_pred": t.type,
                "type_true": k["type"],
                "type_ok": None if (k["type"] is None or "type" in amb) else t.type == k["type"],
                "flags": flags,
                "dup_target_hit": (
                    (k.get("duplicate_of") in dup_numbers) if k.get("duplicate_of") and "duplicate" not in amb else None
                ),
                "n_ambiguous": len(amb),
            }
        )

    done = [r for r in rows if not r["missing"]]
    auto = [r for r in done if not r["escalated"] and r["type_ok"] is not None]
    confident_misses = [r["issue"] for r in auto if not r["type_ok"]]
    graded = [r for r in done if r["type_ok"] is not None]

    def pr(flag):
        # ambiguous fields are None and match none of these
        tp = sum(1 for r in done if r["flags"][flag] == (True, True))
        fp = sum(1 for r in done if r["flags"][flag] == (True, False))
        fn = sum(1 for r in done if r["flags"][flag] == (False, True))
        return {"tp": tp, "fp": fp, "fn": fn}

    return {
        "n": len(key),
        "missing": [r["issue"] for r in rows if r["missing"]],
        "escalation_rate": sum(r["escalated"] for r in done) / len(done) if done else None,
        "autonomous_accuracy": sum(r["type_ok"] for r in auto) / len(auto) if auto else None,
        "autonomous_n": len(auto),
        "confident_misses": confident_misses,
        "type_accuracy_all": sum(r["type_ok"] for r in graded) / len(graded) if graded else None,
        "flags": {f: pr(f) for f in ("needs_mre", "external", "duplicate")},
        "dup_target_hits": [r["issue"] for r in done if r["dup_target_hit"]],
        "ambiguous_fields": sum(r["n_ambiguous"] for r in done),
        "rows": rows,
    }


def main() -> None:
    results = json.load(open(sys.argv[1]))
    key = json.load(open(sys.argv[2]))
    s = score(results, key)
    pct = lambda x: "n/a" if x is None else f"{x:.0%}"
    print(f"Issues: {s['n']}  (missing results: {s['missing'] or 'none'})")
    print(f"1. Escalation rate:          {pct(s['escalation_rate'])}")
    print(f"2. Accuracy when autonomous: {pct(s['autonomous_accuracy'])}  (on {s['autonomous_n']} issues)")
    print(f"   Confident misses:         {s['confident_misses'] or 'none'}")
    print(f"   Type accuracy, all:       {pct(s['type_accuracy_all'])}")
    for f, c in s["flags"].items():
        print(f"   {f:10} tp={c['tp']} fp={c['fp']} fn={c['fn']}")
    print(f"   Duplicate target found:   {s['dup_target_hits'] or 'none'}")
    if s["ambiguous_fields"]:
        print(f"   Ungraded (ambiguous):     {s['ambiguous_fields']} fields")
    print("\nissue   esc  type(pred/true)          flags mre/ext/dup (pred,true)")
    for r in s["rows"]:
        if r["missing"]:
            print(f"{r['issue']:<7} MISSING")
            continue
        mark = "-" if r["type_ok"] is None else ("✓" if r["type_ok"] else "✗")
        fl = " ".join("~~" if v is None else f"{int(v[0])}{int(v[1])}" for v in r["flags"].values())
        print(f"{r['issue']:<7} {'Y' if r['escalated'] else '.':3}  {mark} {r['type_pred']}/{r['type_true']!s:22} {fl}")


if __name__ == "__main__":
    main()
