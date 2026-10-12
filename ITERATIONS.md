# Iteration log

One entry per change to prompts, tools, or guardrails: what failed, the evidence, the change, and how it was (or will be) measured. Source material for the Week 4 case study.

## v0.1 → v0.2 (2026-10-12)

Prototype run: Haiku via Claude Code subagents on the 10 hand-triaged issues (`runs/proto/`). Type 7/10, flags 24/30, escalation rate 40%, accuracy when not escalated 6/6. Not a clean score: the playbook was written from these same 10 issues.

| # | Failure | Evidence | Change |
|---|---|---|---|
| 1 | `search_uv_docs` returned HTTP 422 on any query containing a CLI flag | #21694, #20931 logs: queries `pip install --target`, `... --config-settings ...` | Strip leading dashes from search terms; tool description asks for 1–3 keywords; upstream error text now returned to the model |
| 2 | `likely_external` set for a dependency's intentional constraint | #21273: pyramid's `setuptools<82` flagged external; maintainers use `external` for defects elsewhere (#21824 hatchling, #21336 Netskope) | Redefined `likely_external` in `system.md` and playbook rule 5 as a defect outside uv; intentional constraints are `question` |

**Not yet measured.** Re-run on a held-out set before claiming either change helped.

## v0.2 holdout baseline (2026-10-12)

First clean score: 20 held-out issues (`evals/holdout_key.json`), Haiku via Claude Code subagents, prompts v0.2, `runs/holdout/`. Leakage check clean (no gh/curl/WebFetch, no reads of audit/, evals/, runs/).

| Metric | Round 1 (seen issues) | Holdout v0.2 |
|---|---|---|
| Escalation rate | 40% | **55%** |
| Accuracy when autonomous | 5/5 | **6/9 (67%)** |
| Confident misses | none | **#21430, #20850, #22184** |
| Type accuracy, all graded | 67% | 65% |

The drop from round 1 is the train/test gap: round-1 rules were written from those issues. n=20 is small; 6/9 is consistent with anything from roughly 35% to 90%.

Seen on holdout (not yet changed):
- 2 of 3 confident misses are bug vs enhancement ("is this designed behaviour?"): #21430, #22184.
- Duplicates over-listed again (4 false positives); related issues being listed as duplicates. Real duplicate target found for 2 of 4.
- `needs_mre` over-asked again (3 false positives).
- 5/20 runs hit GitHub code-search rate limits (HTTP 403) from running 20 in parallel → needs retry with backoff (Week 2).

### Adjudication (human review of all 20 disagreements, `evals/adjudication_v0.2.md`)

Verdicts: 12 agent wrong, 1 label wrong, 7 ambiguous. Ambiguous fields are left out of grading; label-wrong fields take the agent's value (`evals/holdout_key_adjudicated.json`).

| Metric | Raw key | Adjudicated key |
|---|---|---|
| Escalation rate | 55% | 55% |
| Accuracy when autonomous | 6/9 (67%) | **6/7 (86%)** |
| Confident misses | 3 | **1** (#22184) |
| Type accuracy, all graded | 65% | 79% |
| `external` false positives | 3 | 0 |

2 of the 3 "confident misses" were genuinely ambiguous calls (#21430: maintainer said "I don't know if I'd consider this a bug"; #20850: unresolved in the thread). The real problems are now clear: escalation rate, `needs_mre` (4/4 adjudicated wrong), and duplicate-vs-related.

**Eval-harness bug found in review:** `issue_snapshot` uses the issue's *current* title/body. #22184's title was edited after the reporter found the cause, so the agent saw hindsight. Fix: reconstruct title from timeline `renamed` events and body from GraphQL `userContentEdits`.

### v0.3 backlog (from the reviewer's pattern analysis, in priority order)
1. `needs_mre` redefined as "can a maintainer act without asking anything?", with counter-examples.
2. Split `possible_duplicates` into `duplicate_of` + `related`; guardrail rejects a duplicate when the rationale says "related" / "no exact duplicate".
3. Second search on the agent's own root-cause hypothesis; prefer open/recent tracking issues.
4. Field-vs-reasoning consistency check before output.
5. Docs tool: retry with backoff or a cached index; reserve budget to read one page; no "not configurable" claims when the docs check failed.
6. No documented guarantee → lean enhancement/question.
7. Short glossary of core uv concepts (universal resolution, editable cache, uvx isolation).
8. Mark noisy references (#20945 contributor PR, #22184 edited post, #20871 reporter-confirmed) in the key.

Open issues seen but not changed yet:
- Over-asks for reproductions (`needs_mre` on #21824, #22111).
- Lists "related, not the same" issues under `possible_duplicates` (#22111) → needs a separate `related_issues` field or a clearer definition.
- Docs search still returns nothing for some hyphenated terms (`no-hashes`, `config-settings`).

## v0.2 → v0.3 (2026-10-12)

| # | Backlog item | Change |
|---|---|---|
| — | Snapshot leaked later edits (#22184 retitled after the cause was found) | `issue_snapshot` shows the original title (first `renamed` event) and original body (oldest `userContentEdits` revision). Test added. |
| 5 | Docs tool rate-limited / mangled hyphens | GitHub code search replaced by a local mirror of `docs/*.md` (81 pages, cached on disk), ranked keyword search with snippets. All GitHub/PyPI calls retry on rate limits and 5xx with backoff. Tests added. |
| 2 | "Duplicate" used for "related" | New `related_issues` field. Guardrail moves duplicates to related when the rationale says "no exact duplicate" / "not a duplicate"; unseen related issues are dropped. |
| — | 4 of 11 escalations were correct enhancements escalated as "a product decision" | Prompt: `escalate_to_human` = "don't trust this triage at a glance", not "a maintainer decides later". Escalate only for a real type tie, security, or missing evidence. |
| 1 | `needs_mre` 4/4 wrong | Redefined as "can a maintainer act without asking anything?", with counter-examples. |
| 3 | Searched symptoms only | Prompt: second search on the root-cause hypothesis; prefer open/recent tracking issues. |
| 4 | Fields contradicted rationale | Prompt: final field-vs-rationale consistency check (plus the duplicate guardrail above). |
| 6 | Undocumented behaviour called a bug | Prompt: a bug needs a documented or obviously intended contract. |
| 7 | Inconsistent use of core concepts | Playbook glossary: universal resolution, `--locked`/`--frozen`, uvx isolation, editable cache keys, `[tool.uv]`. |
| — | Tool budget too small to read docs | Prototype budget raised from 6 to 8 tool calls. |

**Measurement:** fresh holdout `evals/holdout2_key.json` (20 issues, disjoint from all 30 earlier issues and from every issue cited in prompts, notes, or earlier agent output; seed 20261013). Caveat: v0.2 and v0.3 are scored on *different* issue sets, so a change in score mixes the effect of the changes with differences in set difficulty.

## v0.3 holdout2 result (2026-10-12, raw key, not yet adjudicated)

Haiku via Claude Code subagents, prompts/tools v0.3, `runs/holdout2/`. Leakage check clean.

| Metric | v0.2 on holdout1 (raw) | v0.3 on holdout2 (raw) |
|---|---|---|
| Escalation rate | 55% | **10%** |
| Accuracy when autonomous | 6/9 (67%) | **6/13 (46%)** |
| Confident misses | 3 | **7** |
| Type accuracy, all graded | 65% | 53% |
| needs_mre fp / fn | 3 / 1 | 1 / 0 |
| Tool errors | 5 rate-limit failures | 1 (PyPI 404) |
| Runs that read a docs page | — | 15/20 |

**Verdict: overcorrected.** The escalation change worked too well: the agent stopped escalating close calls and now gets them wrong confidently. The tooling and `needs_mre` changes look like real improvements.

Diagnosis from the 13 autonomous calls:
- `confidence` carries no signal: 12/13 are "medium", right or wrong.
- When the agent overrode the reporter's label it was wrong 4 of 5 times (#21747, #19988, #20613, #21065); when it kept the label it was right 5 of 8.
- Misses cluster on the enhancement/question boundary ("existing setting does this" vs "wants new behaviour") and bug/enhancement.

Caveats: different issue set from v0.2 (can't separate version effect from set difficulty); raw key not adjudicated (round 2 showed ~half of apparent misses can be ambiguous labels).

## Ablation: v0.2 vs v0.3 prompts on the same holdout2 (2026-10-12)

Same 20 issues, same v0.3 tools, same 8-call budget; only the prompt text differs (`prompts/v0.2/` vs `prompts/v0.3/`). Raw key. Leakage check clean; no v0.2 run read the v0.3 prompts.

| Metric | v0.2 prompts | v0.3 prompts |
|---|---|---|
| Escalation rate | 70% | 10% |
| Accuracy when autonomous | 4/5 (80%) | 6/13 (46%) |
| Confident misses | 1 | 7 |
| Type accuracy, all graded (n=15) | 73% (11) | 53% (8) |
| needs_mre false positives | 5 | **1** |

Findings:
- **Set difficulty is not the explanation.** v0.2 behaves the same on holdout2 as on holdout1 (55–70% escalation, 65–73% type accuracy). The v0.3 drop comes from the v0.3 prompt.
- **17/20 type calls are identical across versions.** The prompt mostly changed *escalation*, not classification.
- **The 3 calls that changed all went wrong under v0.3**, and the rationales show why: the new "a bug needs a documented contract" / "works as designed → enhancement" wording.
  - #21747, #21065: the agent found the behaviour is by design, so it said `enhancement`. But the reporter did not ask for a change; they were confused, so it is a `question`.
  - #19988: the reporter used the *documented* PyTorch config and it failed. That is a contract violation (bug), but the agent read "matches the docs" as "uv is fine".
- **v0.2's "torn" escalation has ~50% precision:** it flagged 5 of v0.3's 7 eventual misses, but also 5 calls that were right.
- **Confirmed win on a paired set:** the v0.3 `needs_mre` definition (5 → 1 false positives).

v0.4 plan: keep v0.3 tools, `needs_mre`, duplicates/related. Fix the question/enhancement line ("did the reporter ask for different behaviour?"), say that documented config failing is a bug, and bring back escalation for genuine type ties (middle ground). Measure on a fresh holdout pulled from GitHub, since holdout2 has now been used to choose a fix.

## Model comparison: Haiku vs Sonnet, same v0.3 prompts, same holdout2 (2026-10-12)

Same 20 issues, tools, budget and prompt (`prompts/v0.3/`); only the model differs. Raw key. Leakage check clean.

| Metric | Haiku v0.2 | Haiku v0.3 | **Sonnet v0.3** |
|---|---|---|---|
| Escalation rate | 70% | 10% | **40%** |
| Accuracy when autonomous | 4/5 | 6/13 (46%) | **5/8 (62%)** |
| Confident misses | 1 | 7 | **3** |
| Type accuracy, all graded (n=15) | **73%** | 53% | 53% |
| needs_mre false positives | 5 | 1 | 4 |
| Confidence spread | — | 12/13 "medium" | 11 medium, 7 low, 2 high |
| Price per token vs Haiku | 1× | 1× | ~20× |

Findings:
- **Sonnet does not classify better** with this prompt: same 53% type accuracy. It fixed #20875 and broke #20050; net zero.
- **Sonnet's confidence is informative; Haiku's is not.** 4 of Sonnet's 7 type misses were self-rated "low", so the existing low-confidence guardrail escalated them. That is why its escalation lands in the middle (40%) with only 3 confident misses.
- **The v0.3 prompt errors replicate across models.** #21747, #21065 and #19988 are wrong on both Haiku and Sonnet under v0.3 and right on Haiku under v0.2. That confirms they are prompt-caused, so fixing the prompt comes before upgrading the model.
- At ~20× the token price, Sonnet buys calibration, not accuracy. Differences of 1–2 issues on n=15 are within noise.

Decision for v0.4: v0.2-style type definitions + v0.3 tools/`needs_mre`/duplicates. Escalation via code guardrails rather than prompt wording: low confidence → escalate (works on Sonnet); type differs from reporter label → escalate (Haiku's only usable signal). Compare Haiku-v0.4 vs Sonnet-v0.4 on a fresh holdout3 pulled from GitHub.

## v0.4 on fresh holdout3: Haiku vs Sonnet (2026-10-12)

Holdout3 = 20 issues from a new pool (2026-04-02 → 06-22), disjoint from all 50 earlier issues and from every issue cited in prompts, notes, or earlier agent output; seed 20261014. Nothing in v0.4 was tuned on it. Same prompts (`prompts/v0.4/`), tools and budget for both models. Haiku and Sonnet were run in sequence to keep rate limits equal. Raw key. Leakage check clean.

| Metric | Haiku v0.4 | Sonnet v0.4 |
|---|---|---|
| Escalation rate | 40% | 45% |
| Accuracy when autonomous | **10/11 (91%)** | 9/11 (82%) |
| Confident misses | **1** (#19207) | 2 (#19207, #18862) |
| Type accuracy, all graded (n=19) | **84%** | 68% |
| Real duplicate target found | 1 of 2 | **2 of 2** |
| needs_mre false positives | 3 | 2 |
| Tool calls / errors | 90 / 1 | 51 / 0 |
| Escalations forced by relabel guardrail | 4 | 5 |
| Price per token | 1× | ~20× |

Findings:
- **Best result so far, on issues nothing was tuned on.** Haiku v0.4: 84% type accuracy, 91% when autonomous, 1 confident miss.
- **The relabel guardrail works as designed:** it caught 2 of Haiku's 3 type misses. Its cost is precision: of Haiku's 8 escalations, 6 were already correct (escalation precision 2/8). Maintainers review 40% of issues, and 3 in 4 of those reviews only confirm the agent.
- **Sonnet is not worth ~20× here.** It classified worse, investigated less (51 vs 90 tool calls), and only beat Haiku on duplicate targets.
- **Shared confident miss #19207:** a complete, high-confidence bug report that maintainers treated as an enhancement. Both models agreed with the reporter's `bug` label, so no guardrail fired. Agree-with-reporter misses are the remaining blind spot.

Caveats: n=19 graded; raw key not yet adjudicated; holdout3 is older than the docs mirror (Oct), so docs may describe later fixes, which is a possible advantage for the agent. v0.2→v0.4 differences mix version and set effects (different sets).

Recommendation: ship v0.4 on Haiku in "suggest + escalate relabels" mode. Next levers: adjudicate holdout3, then work on escalation precision (6 of 8 escalations unnecessary) and agree-with-reporter misses.

## v0.4 shipped as a suggestion tool (2026-10-12)

- Production default model set to `claude-haiku-5-5`, per the holdout-3 comparison. The server-side refusal fallback is only sent to models that support it (Haiku has none). Test added.
- `triage render` / `triage run --markdown` produce a maintainer-facing suggestion card (`src/triage/render.py`). Nothing is ever posted.
- `evals/build_holdout.py` replaces the one-off holdout scripts, so holdout construction is reproducible.
