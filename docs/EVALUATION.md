# Evaluation method

How the numbers in the README were produced, and how to reproduce them.

## Ground truth

The answer for each issue is **what a uv maintainer actually did**: relabelled the type, added `needs-mre` or `external`, or closed it as a duplicate. The reporter's template label is *not* ground truth (templates apply it automatically). Only issues a maintainer touched (relabelled, closed, or replied to) are eligible, because silence is not confirmation.

Known bias: some labels encode hindsight the agent can't have. For example, `needs-mre` gets added after a maintainer fails to reproduce. These are graded against the label anyway, and resolved in human review.

## Data sets

| Set | Issues | Source | Used for |
|---|---|---|---|
| Round 1 (`audit/answer_key.json`) | 10 | audit pool, Jun–Oct 2026 | hand-triage baseline; writing the first rules (so **not** a test set) |
| Holdout 1 (`evals/holdout_key.json`) | 20 | audit pool | v0.2 score, then human review; patterns → v0.3 |
| Holdout 2 (`evals/holdout2_key.json`) | 20 | audit pool | v0.3 score, v0.2 control, Sonnet comparison; used to choose v0.4, so now retired |
| Holdout 3 (`evals/holdout3_key.json`) | 20 | new pool, Apr–Jun 2026 | v0.4 Haiku vs. Sonnet; nothing tuned on it |

Each holdout is stratified across outcomes (5 confirmed bugs, 4 bug→question, 3 accepted features, 2 bug→enhancement, 2 needs-mre, 2 external, 2 duplicates). It excludes every issue in an earlier key and every issue number cited in the repo's prompts, notes, review sheets, or earlier agent outputs. Built with `evals/build_holdout.py`.

## Leakage controls

- **Snapshot** (`src/triage/github.py`): original title (undoing `renamed` events), original body (oldest edit revision), reporter-applied labels only. No comments, no maintainer labels. Tested in `tests/test_contracts.py`.
- **Time-bounded search:** `search_issues` adds `created:<issue time>`.
- **Run audit:** after every eval, each run's transcript is checked for `gh`/`curl`/WebFetch use and for reads of `audit/`, `evals/` or `runs/`. No violations in 130 runs.
- **Known, accepted leaks:** labels and state on *other* earlier issues are their current values; the docs mirror is the current default branch.

## Metrics (`evals/score.py`)

1. **Escalation rate:** share of issues sent to a maintainer.
2. **Accuracy when autonomous:** type correct on non-escalated issues with a graded type.
3. **Confident misses:** wrong and not escalated.

Also reported: type accuracy across all graded issues; true and false positives for `needs_mre`, `external` and `duplicate`; whether the maintainer's actual duplicate target was found.

## Human review (adjudication)

`evals/make_adjudication.py` lists every disagreement with the agent's reasoning and the maintainer's first reply. The reviewer reads the **first post only** and marks each line as *agent wrong*, *label wrong* or *ambiguous*. `evals/apply_adjudication.py` turns those marks into a reviewed key: *label wrong* takes the agent's value, and *ambiguous* fields are left out of grading. Holdout 1 review: 12 agent wrong, 1 label wrong, 7 ambiguous.

## Harness

Evals ran with Claude Code subagents as the model (no API key during this project). Each subagent:
1. read the frozen prompt (`prompts/vX/`),
2. got the issue via `triage show-input N`,
3. could only call the project's read-only tools via `triage tool N <name> '<json>' --log runs/<set>/N.jsonl`, with a budget of 8 calls (6 before v0.3),
4. wrote a `TriageResult` JSON.

`evals/collect_proto.py` validates every answer with the same Pydantic model and applies the same `apply_guardrails` used by the production loop. The production loop (`src/triage/agent.py`) uses the same prompt, tools, schema and guardrails, but calls the Messages API directly. It is unit-tested with a fake model and not yet run live.

## Reproduce

```bash
# score an existing run
uv run python evals/score.py runs/holdout3_haiku/results.json evals/holdout3_key.json

# re-collect a run from raw per-issue files (re-applies guardrails)
uv run python evals/collect_proto.py runs/holdout3_haiku evals/holdout3_key.json

# build a new holdout
uv run python evals/build_holdout.py fetch --created 2026-01-01..2026-03-31 --pool data/pool4
uv run python evals/build_holdout.py pick  --pool data/pool4 --seed 4 --out evals/holdout4_key.json

# review sheet for disagreements, then a reviewed key
uv run python evals/make_adjudication.py runs/<set>/results.json evals/<key>.json evals/adjudication_<v>.md
uv run python evals/apply_adjudication.py evals/adjudication_<v>.md evals/<key>.json runs/<set>/results.json evals/<key>_adjudicated.json
```

Run directories: `runs/holdout` (v0.2 Haiku), `runs/holdout2` (v0.3 Haiku), `runs/holdout2_v02` (v0.2 Haiku, control), `runs/holdout2_sonnet` (v0.3 Sonnet), `runs/holdout3_haiku` and `runs/holdout3_sonnet` (v0.4).
