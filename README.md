# AI issue triage for `astral-sh/uv`: an FDE case study

A read-only triage assistant for the [uv](https://github.com/astral-sh/uv) issue tracker, built and evaluated the way a forward deployed engineer would: audit the real workflow, build on existing systems, measure against real maintainer decisions, and only grant autonomy the evidence supports.

**Status:** v0.4 on Claude Haiku 5.5, recommended for use as a *suggestion tool* (it drafts triage; maintainers decide). Built in a single day as a learning project following the "FDE in 30 Days" plan.

---

## Summary (for decision-makers)

**Problem.** uv gets ~3 new issues a day. A third need a maintainer to fix the reporter's label, and a third of issues had no maintainer reply at audit time (median wait 6 h; slowest 10% wait 5.5+ days). The labels reporters pick are often wrong: the most common correction is "bug" → "question".

**Outcome.** On 20 real issues it was never tuned on, the assistant:
- handled **60%** of issues on its own and got the type right on **10 of 11** of those,
- sent the other **40%** to a maintainer with a stated reason,
- got the type right **84%** of the time overall, versus **~45%** for a newcomer doing the same task by hand,
- costs **under 1 cent per issue** on Claude Haiku. Claude Sonnet cost ~20× more and scored *worse*.

**Evidence.** Seven evaluation runs (130 triage runs in total) on 70 real issues, held-out test sets, a human review of disputed labels, and controlled comparisons of prompt versions and models. Every number below links to the raw outputs in `runs/`.

**Risk.** It cannot act on GitHub: no tool can comment, label, or close. Its main remaining weakness is agreeing with a reporter's wrong label (1 confident miss in 20). Escalation is safe but not yet efficient: 6 of 8 escalations turned out to be cases it had right.

**Recommendation.** Deploy as a suggestion card on new issues: confirm or correct the label, flag missing reproductions and external causes, link duplicates. Every relabel requires a maintainer. Widen autonomy only after a month of shadow-mode data.

---

## Results

| Round | Model + prompt | Issues | Escalation rate | Accuracy when autonomous | Confident misses | Type accuracy |
|---|---|---|---|---|---|---|
| Human baseline | newcomer, by hand | 10 | — | — | — | ~45% (4 right, 2 partial) |
| v0.2 | Haiku | holdout 1 (20) | 55% | 6/9 → **6/7** after review | 3 → **1** after review | 65% → 79% after review |
| v0.3 | Haiku | holdout 2 (20) | 10% | 6/13 | 7 | 53% |
| v0.2 (control) | Haiku | holdout 2 | 70% | 4/5 | 1 | 73% |
| v0.3 | Sonnet | holdout 2 | 40% | 5/8 | 3 | 53% |
| **v0.4** | **Haiku** | **holdout 3 (20)** | **40%** | **10/11 (91%)** | **1** | **84%** |
| v0.4 | Sonnet | holdout 3 | 45% | 9/11 (82%) | 2 | 68% |

*Escalation rate* = share of issues sent to a maintainer. *Accuracy when autonomous* = type correct on the issues it did **not** escalate. *Confident miss* = wrong and not escalated, the failure that costs trust. These two numbers pull against each other on purpose: an agent that escalates everything is never wrong and saves no one any time.

Holdout 3 was drawn from a separate pool and nothing was tuned on it. Rounds on different sets mix version effects with set difficulty; the control rows (same set, one variable changed) are what isolate causes. Details: [`ITERATIONS.md`](ITERATIONS.md).

### Example output

A real v0.4 result where the guardrail sent a relabel to a human ([`docs/examples/18862.md`](docs/examples/18862.md)):

> 🔎 **Needs a maintainer decision**
> - **Type:** `question` (reporter filed as `bug`) · confidence: medium
> - **Why a human should check:** changes the reporter's label (bug → question)
>
> **Why:** … docs/concepts/python-versions.md says that for Python 3.14+ uv allows free-threaded interpreters without explicit selection, and that when both builds are available the GIL build must be required with the +gil specifier … so this is a question about configuration (use 3.14+gil …).

---

## 1. Audit: how triage actually works

Full findings: [`AUDIT.md`](AUDIT.md). The ones that shaped the design:

- **The type label is the reporter's guess, not a decision.** uv's issue templates apply `bug` / `enhancement` / `question` automatically. Using those labels as ground truth would grade the agent on agreeing with reporters.
- **The real triage work is correcting the guess** (`bug → question` is 22 of 34 corrections), adding `needs-mre` / `external`, and closing duplicates. Area labels are rare (11%) and were left out of scope.
- **Ground truth must come from what maintainers did**, and only from issues they touched.
- **uv already has a triage bot**, so the job is to complement existing systems, not replace them.

Before writing any code I triaged 10 issues by hand ([`audit/round1_results.md`](audit/round1_results.md)). My misses fell into two groups. Pattern misses (I had the clue but read it wrong) are fixed with **rules**. Knowledge misses (a config typo, a dependency's version cap, a known duplicate) are fixed with **tools**. That split became the architecture.

## 2. What it does

Input: an issue number. Output: a validated, structured recommendation (`src/triage/schema.py`):

`type` · `needs_mre` + what to ask · `likely_external` + evidence · `possible_duplicates` · `related_issues` · `confidence` · `escalate_to_human` + reason · `rationale`

rendered as a suggestion card for a maintainer (`triage render`, `triage run --markdown`).

## 3. Architecture

```
issue # ──► snapshot (original title/body, reporter's label only; no comments, no maintainer labels)
              │
              ▼
        agent loop (src/triage/agent.py) ◄──► Claude Haiku 5.5 (Messages API, structured output)
              │   tools, all read-only (src/triage/tools.py):
              │     search_issues         only issues filed *before* this one
              │     search_uv_docs        local mirror of docs/*.md, keyword-ranked, snippets
              │     read_uv_doc           one docs page
              │     get_package_metadata  PyPI requires_dist / requires_python
              ▼
        JSON schema output ──► Pydantic validation ──► code guardrails ──► suggestion card
              │                                        (apply_guardrails in agent.py)
              └──► append-only audit log: every prompt, response, tool call, result, guardrail action, cost
```

### Design decisions (and why)

| Decision | Why |
|---|---|
| **Agent sees only what a maintainer saw at triage time:** original title and body (later edits undone), reporter's label, no comments | Otherwise evals on past issues leak the answer. Found and fixed during review: a retitled issue was leaking the cause. |
| **Search only returns earlier issues** | The agent can't "find" a duplicate filed after the issue it's triaging. |
| **Every tool is read-only** | No prompt, and no prompt injection inside an issue, can make it post, label, or close. The capability doesn't exist. |
| **"The prompt asks, the code enforces"** | Duplicates it never actually saw are dropped; a rationale saying "not a duplicate" moves the issue to `related`; low confidence escalates; **changing the reporter's label escalates**. |
| **Escalation decided in code, not prompt wording** | Every prompt-only attempt overshot (escalating 10% or 70% of issues). The model's confidence was meaningless on Haiku (12/13 "medium"). "Overrode the reporter" was the signal that actually predicted errors (wrong 4 of 5 times in v0.3). |
| **Local docs mirror instead of GitHub code search** | Code search was rate-limited, returned 422 on `--flags`, and caused wrong calls. The mirror removed every docs-tool error. |
| **Retry with backoff on rate limits and 5xx** | 20 parallel evals hit GitHub's limits. Tool errors went from 5/20 runs to 1 in 141 calls. |
| **Haiku over Sonnet** | Same prompt and issues: Haiku 84% type accuracy vs. Sonnet 68%, at ~1/20th the price. |
| **Hand-written loop, not the SDK tool runner** | Full control to log every step, force a final answer on the last turn, and add checkpointing. |
| **Every prompt version kept** (`prompts/v0.2` … `v0.4`) | Every score traces to the exact text that produced it. |

## 4. Evaluation method

Full method: [`docs/EVALUATION.md`](docs/EVALUATION.md). Key practices:

1. **Held-out sets.** The first score (5/5 on issues the rules were written from) was inflated; on new issues it fell to 6/9. After that, every version was measured on issues it hadn't seen, and a set used to choose a fix was retired.
2. **Leakage controls.** The agent can't see comments, maintainer labels, later edits, or later issues. Every run was audited for forbidden tool use (none found in 130 runs). Issues cited anywhere in prompts or notes are excluded from future holdouts.
3. **Two numbers:** escalation rate and accuracy when autonomous, plus the list of confident misses.
4. **Human review (adjudication).** I reviewed all 20 disagreements on holdout 1: 12 agent errors, 1 wrong label, 7 genuinely ambiguous. Half the apparent confident misses were ambiguous labels.
5. **Controlled comparisons.** When v0.3 regressed, v0.2 was rerun on the same issues with the same tools. That showed the prompt, not the issue set, caused the drop. The same method was used for Haiku vs. Sonnet.

## 5. What v1 got wrong, and what changed

| Version | What went wrong | What I learned / changed |
|---|---|---|
| v0.1 | Scored 5/5, but on issues the rules were written from | Always hold out data. Real score: 6/9. |
| v0.1 | Docs search failed on any `--flag` | Fixed the query, then replaced code search with a local mirror. |
| v0.2 | Called a dependency's intentional version cap "external" | Redefined `external` the way maintainers use it: a defect elsewhere. |
| v0.2 | Escalated 55%, including every feature request ("needs a product decision") | Labelling it `enhancement` *is* the triage. |
| v0.2 | Over-asked for reproductions; listed "related" issues as duplicates | New `needs_mre` definition (unneeded requests 5 → 1 on the same set); separate `related_issues` field. |
| eval harness | The agent could see an issue's later title edit | Snapshot now rebuilds the original title and body. |
| v0.3 | Changed ~10 things at once and overcorrected: 10% escalation, 7 confident misses | Same-set comparison found the culprits (an over-specific "bug needs a documented contract" rule, and escalation by wording). Lesson: change one thing at a time. |
| v0.3 | The model's confidence didn't predict errors | Moved escalation into code guardrails. |
| v0.4 | Best so far (84%, 1 confident miss) | Remaining blind spot: agreeing with a reporter's wrong label. |

Full log with evidence: [`ITERATIONS.md`](ITERATIONS.md).

## 6. Limitations and risks

- **Small samples.** 19–20 graded issues per round. A difference of 1–2 issues is noise. Treat the numbers as direction, not precision.
- **The evals ran in a prototype harness.** Every evaluated run used Claude Code subagents acting as the model, with the same prompts, the same read-only tools (through `triage tool`), and the same code guardrails applied afterwards (`evals/collect_proto.py`). The production loop (`src/triage/agent.py`) is fully unit-tested with a fake model but has **not yet been run against the live API**.
- **Holdout 3 is not yet human-reviewed.** On holdout 1, review raised accuracy by about 14 points; holdout 3 could move too.
- **Docs-version leak.** The docs mirror is current, so on older issues the agent may read docs that describe later fixes.
- **Escalation precision is low.** 6 of 8 escalations were correct calls a maintainer only had to confirm.
- **The round-1 prototype answers** (`runs/proto/results.json`) were transcribed by hand in shortened form. Later rounds had the model write its own result files.

## 7. Cost

| | Per issue (prototype harness, measured) | Notes |
|---|---|---|
| Haiku v0.4 | **~$0.007** | ~90 logged runs, $0.64 total at list prices |
| Sonnet | ~$0.13 | 40 runs, $5.33 total |

Most tokens are cached context re-reads. The production loop logs exact per-run cost from the API's usage fields (`src/triage/pricing.py`); re-check prices before quoting them.

## 8. Run it

```bash
uv sync
uv run pytest                                  # 20 offline tests, no API key needed
uv run triage show-input 22184                 # exactly what the agent sees (no API key needed)
export ANTHROPIC_API_KEY=...                   # then:
uv run triage run 22184 --markdown             # triage one issue -> suggestion card
uv run triage render docs/examples/19811.result.json --issue 19811
```

Reproduce the evals: [`docs/EVALUATION.md`](docs/EVALUATION.md).

## 9. Repository layout

```
AUDIT.md                 workflow audit: how triage really works, pain points, scope
ITERATIONS.md            every change, the evidence for it, and its measured effect
docs/EVALUATION.md       eval method and how to reproduce
docs/PITCH.md            engineer and executive pitch outlines
docs/examples/           real suggestion cards
src/triage/              agent loop, tools, schema, guardrails, renderer, CLI
  prompts/               current prompt (v0.4) + playbook (the agent's long-term memory)
prompts/v0.2..v0.4/      frozen prompt versions, one per eval round
evals/                   holdout answer keys, adjudication sheets, scorer, holdout builder
audit/                   hand-triage worksheet, round-1 key and results
runs/                    raw outputs and tool-call logs for every evaluated run
tests/                   offline tests (fake model, mocked GitHub)
```

## 10. Next

- Human review of holdout 3.
- Week 2: checkpoint between turns so a run can resume after a crash; run the production loop against the live API and compare it with the prototype harness.
- Improve escalation precision, and target agree-with-reporter misses.
- Shadow mode: run on new issues for a month, compare with maintainer decisions, then decide what autonomy to grant.
