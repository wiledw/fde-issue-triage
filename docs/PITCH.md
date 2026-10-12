# Pitch outlines

Two versions of the same story for two audiences. These are outlines to rehearse from, not scripts: put them in your own words.

## Executive version (~2 minutes): problem, outcome, evidence, risk

1. **Problem.** "uv's maintainers spend their scarcest resource, expert attention, on first-pass triage. A third of issues need the reporter's label corrected. The slowest 10% wait over five days for a first reply."
2. **What we built.** "An assistant that reads each new issue, checks the docs, package metadata and past issues, and drafts a triage card: the right label, whether a reproduction is missing, whether the cause is outside uv, and likely duplicates. It cannot post or change anything."
3. **Outcome.** "On 20 real issues it had never seen, it handled 60% on its own and got 10 of 11 of those right. It sent the other 40% to a maintainer with a reason. A newcomer doing the same task scored about 45%. It costs under a cent per issue."
4. **Evidence.** "Seven evaluation runs on 70 real issues, checked against what maintainers actually decided, plus a human review of disputed labels."
5. **Risk and how it's contained.** "It's read-only by construction. Any time it disagrees with the reporter, a human decides. Its one confident mistake was agreeing with a convincing but wrong bug report."
6. **Ask.** "Run it in shadow mode for a month: it drafts, maintainers decide, and we compare. Then we decide how much autonomy to give it."

Likely questions:
- *"Why not use the bigger model?"* We tested it on the same issues: it was 20× the cost and less accurate (68% vs. 84%).
- *"What if it's wrong?"* Nothing it produces takes effect without a maintainer. Relabels always go to a human.
- *"How do you know the numbers are real?"* They come from held-out issues, it can't see answers, and every run was audited for leaks.

## Engineering version (~5 minutes): architecture, decisions, tradeoffs

1. **Framing the task.** The audit showed template labels are reporter guesses. Ground truth = maintainer actions, only on issues a maintainer touched.
2. **Architecture.** Snapshot (original post, no comments) → hand-written tool loop → read-only tools (time-bounded issue search, local docs mirror, PyPI metadata) → JSON-schema output → Pydantic validation → code guardrails → suggestion card. Full audit log.
3. **Key decision: escalation in code.** Prompt wording swung escalation between 10% and 70%. Model confidence was uninformative on Haiku. "Overrode the reporter" predicted errors, so it became a deterministic guardrail.
4. **Eval discipline.** Holdouts, leakage controls, two metrics that trade off, human review, and same-set controls. The v0.3 regression was diagnosed with a control run: 17 of 20 calls were identical, and the 3 that changed traced to one over-specific rule.
5. **Model choice.** Sonnet's confidence was better calibrated, but its classification was worse, at 20× the price. Haiku plus code guardrails won.
6. **Tradeoffs I'd defend.**
   - Low escalation precision (6 of 8 escalations were already right), in exchange for few confident misses.
   - Small samples: I report directions, not decimals.
   - Prototype harness vs. live API: same prompt, tools, schema and guardrails; the next step is a side-by-side run.
7. **What I'd do next.** Review holdout 3, run the live-API comparison, add checkpointing, improve escalation precision, then shadow mode.
