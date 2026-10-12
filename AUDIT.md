# Audit: GitHub issue triage for astral-sh/uv

**Phase 1 of the FDE loop.** Data: the 300 most recent issues (2026-06-23 → 2026-10-12) plus their full event timelines, pulled with `gh`.

## How triage really works today (not the documented version)

1. A reporter picks an issue template. **The template auto-applies the type label** (`bug`, `enhancement`, `question`).
   → The type label on an issue is the *reporter's* guess, not a triage decision.
2. A maintainer (7 people do almost all triage; one does ~40% of label changes) reads it, usually within hours.
3. The maintainer does one or more of:
   - **Corrects the type**, most often `bug → question` (22 of 34 type corrections): the reporter thought it was a bug, but it's a usage/support question.
   - Adds **`needs-mre`**: can't act without a minimal reproducible example (12).
   - Adds **`external`**: the cause is outside uv (another tool, the OS, a package) (14).
   - Closes as **duplicate** of an existing issue (15, ~5%).
   - Adds `needs-decision` / `needs-design` (product calls only maintainers can make).
4. `area:*` labels are applied rarely (11% of issues), so they are **not** a reliable target.

## Existing systems (open question)

uv **already has some triage automation**: a maintainer on #21824 wrote "our triage bot has identified this as a bug in hatchling", and labels like `bot:needs-mre-comment` and `bot:ai-policy-comment` exist. Before building, find out what it does and where it falls short. An FDE builds on existing systems rather than duplicating them.

## Numbers

| Metric | Value |
|---|---|
| Volume | ~3 new issues/day |
| Issues a maintainer re-labeled | 99 / 300 (33%) |
| Median time to first maintainer reply | 6.1 h |
| p90 time to first maintainer reply | 131 h (~5.5 days) |
| Issues with no maintainer reply yet | 96 / 300 (32%) |

## Pain point

Maintainers spend their scarcest resource (expert attention) on routine first-pass decisions: *is this really a bug? is a repro missing? is this someone else's problem? has this been reported before?* The long tail (p90 ≈ 5.5 days, a third unanswered) is where reporters go quiet and duplicates pile up.

## Operating map

| Step | Today | With the agent (v1) |
|---|---|---|
| Classify type | Reporter guesses via template; maintainer corrects ~1 in 9 | Agent proposes a type + rationale; flags when it disagrees with the template |
| Repro check | Maintainer reads and adds `needs-mre` | Agent checks for version, OS, command, full output; lists what's missing |
| External cause | Maintainer recognizes it from experience | Agent flags *likely external* with evidence |
| Duplicates | Maintainer remembers or searches | Agent searches existing issues and proposes candidates with links |
| Product decisions | Maintainer | **Always escalated.** Agent never decides `needs-decision` / `wontfix` |
| Action on GitHub | Maintainer labels/comments/closes | **None.** v1 is read-only; output is a recommendation for a human |

## v1 scope (the smallest real slice)

**Input:** an issue number. **Output:** a structured triage recommendation:
`type`, `needs_mre` (+ what's missing), `likely_external`, `possible_duplicates`, `confidence`, `escalate_to_human`, `rationale`.

**Guardrails:** read-only GitHub access. Never posts, labels, or closes. Low confidence or a product question → escalate.

## Ground truth for the golden dataset (Week 3)

The **final state after a maintainer acted** (relabeled, added `needs-mre`/`external`, or closed as duplicate). Use only issues a maintainer actually touched: silence is not confirmation that the reporter's template label was right.
