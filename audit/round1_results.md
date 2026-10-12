# Round 1: hand-triage by a newcomer (human baseline)

Triager: project author, no prior uv knowledge. Read first posts only.

**Score: 4 correct, 2 partial, 4 wrong out of 10** (~40–50%). This is the newcomer baseline the agent must beat.

| # | Issue | My call | Maintainer | Result | Miss type |
|---|---|---|---|---|---|
| 1 | 21824 | bug or external | bug + external | partial | committed to neither |
| 2 | 22111 | bug | question (config typo `[tools.uv]`) | wrong | needs knowledge → docs tool |
| 3 | 21694 | bug | bug | correct | |
| 4 | 20931 | question | bug + duplicate of #3636 | partial | needs memory → issue search; label noise |
| 5 | 21972 | question | question | correct | |
| 6 | 22006 | (unclear) | enhancement | wrong | reading pattern → rule 3 |
| 7 | 21641 | bug | needs-mre | wrong | reading pattern → rules 4–5 |
| 8 | 21122 | improvement | enhancement | correct | |
| 9 | 21273 | bug | question (pyramid pins setuptools<82) | wrong | needs knowledge → PyPI tool |
| 10 | 22262 | bug | bug | correct | |

## Lessons
- **Misses split in two.** Pattern misses (#6, #7) are fixed by rules → `src/triage/prompts/playbook.md`. Knowledge misses (#2, #9, #4) are fixed by tools → `search_uv_docs`, `get_package_metadata`, `search_issues`.
- **Labels are noisy.** #20931 kept `bug` although the maintainer said "we don't support this". Some eval failures will be label disagreements, not agent errors.
- **Hindsight leakage in ground truth.** #21641's `needs-mre` exists only because the maintainer tried and failed to reproduce. From the first post alone, the defensible call is "probably environmental (network: `connection reset`, failing file changes each run, local tarball installs fine); ask about proxy/antivirus/other network." Grade the agent on what is knowable from its input.
- **One type, not two.** Uncertainty belongs in `confidence` / `escalate_to_human`, not in a second label.
