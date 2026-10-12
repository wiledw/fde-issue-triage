For each disagreement, open the issue, read **the first post only**, and decide:

- **agent wrong**: the first post supports the maintainer's call
- **label wrong**: the first post supports the agent's call (label noise, or hindsight the agent couldn't see)
- **ambiguous**: a reasonable maintainer could go either way

Then read the thread and add a short *why*. Mark one box per disagreement line with `x`.

> **Reviewer caveats:** #8441 (referenced in #4) was not opened, so that call relies on the maintainer's statement that the issues share a root cause. In #11, the reference "maintainer reply" is a contributor PR, not a maintainer decision.

## 1. #20854: uvw.exe  0.12 version is marked as malicious by antimalware checkers
https://github.com/astral-sh/uv/issues/20854 · reporter's label: `bug` · agent escalated: **yes** (confidence medium)

**Agent's reasoning:** The report is a Windows antivirus detection of uvw.exe 0.12, not a uv behaviour problem, so the decisive clue is the external cause. Search found #15011, the same Windows Defender false positive on uvw.exe, closed as a duplicate and labelled external. The reporter's template says bug and the report does name a release, so I kept type bug while marking it likely external. The VirusTotal links were not opened, since fetching them was out of bounds, so the detection's details are unverified. Needs_mre is false because the issue is about a vendor's detection, not a reproduction, but the antivirus name and install method are missing.
**Why it escalated:** The issue raises a possible security concern: a published release binary is reported as malicious by VirusTotal. A maintainer should confirm whether this is a false positive, check the release artifact against the build, and decide whether to contact the antivirus vendors or report a false positive. The triage cannot verify the detection itself.
**Maintainer's first reply:** "Please see astral-sh/uv#20792 — these are false positives for new releases.…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `bug` vs label `question` | [x] | [ ] | [ ] |
| external: agent yes vs label no | [ ] | [x] | [ ] |
| duplicate: agent listed #15011, #17344 vs maintainer's target #20792 | [ ] | [ ] | [x] |

Why: The first post is a short VirusTotal report, and the reporter admits not checking whether the file is actually malicious. Nothing describes uv behaving wrongly; the agent said so itself but kept `bug` because of the template. "External" is clearly right (the maintainer calls these vendor false positives on new releases), so the `no` label is noise. #15011 is a genuine match; the agent found an older closed instance instead of the current tracking issue #20792. Right cluster, wrong canonical target.

## 2. #21430: Yanked wheel is retained in `uv.lock` even when a non-yanked wheel exists for the same version
https://github.com/astral-sh/uv/issues/21430 · reporter's label: `bug` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter's template label is bug and the report describes uv behaving contrary to its intended design: uv correctly refuses to select a per-file yanked wheel for install but still writes that wheel's URL and hash into uv.lock's wheels array. The reporter traces this to PrioritizedDist::built_dist() and WheelCompatibility::is_excluded(), which only matches ExcludeNewer and not Yanked, and shows the stale entry survives --locked and --frozen. The report includes versions (uv 0.12.4), platform, a step-by-step reproduction on a devpi index, and symmetric results when the yanked file is swapped, so it is actionable without an extra MRE. The uv resolution docs read did not document yank-based exclusion from the lockfile, so I did not treat this as a config or docs issue. search_issues returned only an unrelated 2023 issue (#592, environment variable expansion), so no duplicate was found. Index-side per-file yanking is a PEP 592 feature, but the defect sits in uv's lock writer, so this is not external.
**Maintainer's first reply:** "Thanks for the report! I don't know if I'd consider this a bug, given the guarantees we provide about the contents of `uv.lock` (none, AFAIK). But I agree it could be better :)…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `bug` vs label `enhancement` | [ ] | [ ] | [x] |

Why: The first post makes a careful bug case: reproduction, a source-level root cause (`is_excluded()` matches `ExcludeNewer` but not `Yanked`), and an argument that lock time is the only place to fix it. The maintainer's objection (uv guarantees nothing about lockfile contents) isn't visible in the first post, and they agree "it could be better." The agent read "docs don't cover this" as support for bug; an undocumented guarantee should lean toward enhancement, but both readings are defensible.

## 3. #19999: uv add --no-index --find-links fails to resolve platform-specific dependencies that are not required on the current platform
https://github.com/astral-sh/uv/issues/19999 · reporter's label: `bug` · agent escalated: **yes** (confidence medium)

**Agent's reasoning:** The reporter labelled this a bug, but uv add produces a universal (all-platform) lock by design, so it needs pywin32 metadata for sys_platform == 'win32' even on Linux. The offline --no-index --find-links index has no such wheel, so resolution fails. uv pip install only resolves for the current platform, which explains why it succeeds. The reproduction steps are complete, so no MRE is needed. The external-cause check is negative because the failure is in uv's resolver. Search_issues returned no matching earlier issues. search_uv_docs was rate-limited (HTTP 403) and returned no result, so the docs were not checked. The confidence is medium for that reason and because the bug-versus-enhancement call is close.
**Why it escalated:** Whether uv add should produce a universal lock that needs metadata for all platforms (e.g. pywin32 for win32) when resolving against an offline --find-links index is a product decision for maintainers. The inconsistent resolver message ('only pywin32<304 is available' vs 'no versions of pywin32>=304') may be a separate small bug worth a look.
**Maintainer's first reply:** "I think this is broadly intentional. `uv add` does a [universal resolution](https://docs.astral.sh/uv/concepts/resolution/#universal-resolution), so it doesn't special-case the current platform in any way -- it solves in the same way regard…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `enhancement` vs label `question` | [x] | [ ] | [ ] |

Why: The first post's "expected behaviour" option 1 (ignore other platforms when locking) already exists as `[tool.uv] environments = ["sys_platform == 'linux'"]`, which is exactly what the maintainer pointed to. The answer is existing config, so it's a question. The agent understood universal resolution but never saw the docs (rate-limited 403), so it assumed the behaviour wasn't configurable. The tool failure directly caused the wrong call.

## 4. #21287: Having a git credentials helper configured per-project (not globally) for `uv` to use
https://github.com/astral-sh/uv/issues/21287 · reporter's label: `question` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter asks how to scope a git credential helper to one project, which is a usage question rather than a defect. The uv git-credentials docs (docs/concepts/authentication/git.md) say that when no credentials are in the URL, the git credential helper is queried, and they recommend a helper or gh auth setup-git; they do not describe project-level helper config. A repo-local git config only applies when git runs inside that repository, and uv fetches git dependencies outside the project tree, so the local helper is likely never read. This last point is my inference and was not checked against uv's source. The one search hit, #1514 (URL-embedded credentials not resolving, closed), describes a different failure and is not a duplicate.
**Maintainer's first reply:** "This shares the root cause of #8441.…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| duplicate: agent listed none vs maintainer's target #8441 | [x] | [ ] | [ ] |

Why: The first post says a project-level helper fails and a global one works. The agent inferred the likely root cause itself (uv runs git outside the project tree, so repo-local config is never read), presumably the shared root cause the maintainer means. But it only searched the symptom (credential helpers). A search on its own hypothesis ("uv ignores local git config") would likely have found #8441. Caveat: #8441 was not opened; downgrade to ambiguous if it isn't findable that way.

## 5. #20871: uvx should not use the project's dependencies
https://github.com/astral-sh/uv/issues/20871 · reporter's label: `bug` · agent escalated: **yes** (confidence medium)

**Agent's reasoning:** The reporter gives a complete, version-pinned reproduction (uv 0.12.1, RHEL9.6): the same uvx tool resolves fastapi 0.120.0 from outside a project and 0.136.0 from inside one, and --isolated does not change this. That points to uvx leaking the project environment, which is a defect rather than a config mistake, so the type is bug. The search_issues call found #7186 (uvx should use a project dependency if available), which describes the same project-environment behaviour and is labelled needs-decision. The search_uv_docs call failed with an HTTP 403 rate-limit error, so the docs were not checked. Confidence is medium because the intended behaviour is unclear and a maintainer should confirm it.
**Why it escalated:** Torn between bug and question/enhancement. Reporter gives a complete reproduction on uv 0.12.1, and uvx picking up the cwd project's dependencies contradicts the isolation the reporter expects. Related issue #7186 is labelled needs-decision, so whether uvx should respect project dependencies is a product decision for maintainers.
**Maintainer's first reply:** "This doesn't sound like the expected behavior and isn't reproducible in a trivial example. Do you have `PYTHONPATH` set? What Python executable is being used?…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| needs-mre: agent no vs label yes | [x] | [ ] | [ ] |
| duplicate: agent listed #7186 vs maintainer's target none | [x] | [ ] | [ ] |

Why: The reproduction looks complete but requires publishing a package to PyPI, the claim contradicts uvx's design even with `--isolated`, and the reporter hedges that it may be "a skill issue". All point to needing an MRE. The thread confirms it: building a minimal example, the reporter found their own tool ran `uv run` internally, so not a uv bug. #7186 asks for the opposite behaviour (uvx *should* use project deps), so it is related at most, and its needs-decision label wrongly drove the escalation.

## 6. #21424: Regression: conflicts definition in root project are not inherited
https://github.com/astral-sh/uv/issues/21424 · reporter's label: `bug` · agent escalated: **yes** (confidence low)

**Agent's reasoning:** The reporter names a regression (works on 0.9, errors from 0.11 onward), which is a strong bug signal per the playbook. The error 'Expected package field in conflicting entry' fires on a root-level [tool.uv] conflicts entry that uses group references without a package key, so it may be intended stricter validation in workspaces rather than a defect. search_issues returned no matching duplicate. The docs on configuring projects did not cover conflicts, so the intended behaviour could not be confirmed from the docs consulted. Without the workspace layout and exact command, a maintainer cannot reproduce the inheritance claim, hence needs_mre.
**Why it escalated:** Torn between bug (regression between 0.9 and 0.11, hard error on a config that previously worked) and question (uv may intentionally require a 'package' field on group conflict entries in workspaces, making this a config mistake). Whether uv should enforce that requirement is a maintainer decision.
**Maintainer's first reply:** "uv 0.11.4 started actually reading that `conflicts` field in the root pyproject. Previous versions of uv simply ignored it (assuming you don't have a `[project]` entry in there).  The error message is correct though. You can simply specify …"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `bug` vs label `question` | [ ] | [ ] | [x] |
| needs-mre: agent yes vs label no | [x] | [ ] | [ ] |

Why: "Worked on 0.9, fails on 0.11" reads as a regression; the key fact (pre-0.11.4 silently ignored the root `conflicts` field) is maintainer hindsight. But the quoted error itself names the fix ("Expected `package` field"), which hints at a config question. The agent escalated with exactly this tension, which was right. The MRE call is wrong: config, exact error and versions were in the first post, and the maintainer answered fully from them.

## 7. #21773: uv upgrade cannot authenticate while uv sync --upgrade does
https://github.com/astral-sh/uv/issues/21773 · reporter's label: `bug` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter says uv sync --upgrade authenticates with the same UV_EXTRA_INDEX_URL credentials that uv upgrade ignores, and uv upgrade re-resolves dependencies, so the same credentials should apply. That points to a uv defect rather than a config mistake or a dependency constraint, so bug matches the reporter's label. The repro (pyproject, env var, commands, version, platform) is specific enough for a maintainer to act on. Search found two closed, related 401 issues (14969, 18611) but no exact duplicate. The docs search was rate-limited and the index-docs read returned 404, so the docs check for the documented env var behaviour was not completed. Confidence is medium for that reason.
**Maintainer's first reply:** "Thanks for the report! This indeed looks like a bug…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| duplicate: agent listed #14969, #18611 vs maintainer's target none | [x] | [ ] | [ ] |

Why: The first post is specifically about `uv upgrade`, which doesn't accept the index/auth options the other resolving commands do. Older closed 401 issues can't duplicate a problem in that specific command. The agent's own reasoning says "no exact duplicate", yet it filled the duplicate field. The maintainer confirmed and fixed the bug quickly.

## 8. #20850: uv add from GCP artifact registry returning HTTP status client error (403 Forbidden)
https://github.com/astral-sh/uv/issues/20850 · reporter's label: `bug` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter labels this a bug, but the decisive clue is that a single wheel returns 403 from the Google Artifact Registry download endpoint while other packages from the same repo install, which points to a registry-side permission or missing-file problem outside uv, so I classed it as a question and likely_external. The platform is also inconsistent (Windows reporter, macOS wheel) and no verbose output or credential check was given, so needs_mre is true. Search found 2025 and 11244 as 403-from-private-index symptom matches, and 16662 as a related request for clearer 403 messages. The docs search returned docs/guides/integration/google.md, which I did not open because the tool-call budget was used up.
**Maintainer's first reply:** "Can you share more information about how you're authenticating to the registry? Are you using the [Google integration](https://docs.astral.sh/uv/guides/integration/google/), or something else?  …"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `question` vs label `bug` | [ ] | [ ] | [x] |
| external: agent yes vs label no | [ ] | [ ] | [x] |
| duplicate: agent listed #2025, #11244 vs maintainer's target none | [x] | [ ] | [ ] |

Why: One package fails with 403 while others from the same registry install, which fits either a registry-side or a uv-side cause. In the thread, one maintainer suggests the index may list a file that doesn't exist (external); another asks about auth setup (possibly uv-side). Unresolved, so type and external are genuinely open. The agent called a macOS wheel on Windows an "inconsistency", but that is expected under universal resolution, the concept it handled correctly in #3. The listed duplicates are generic 403-from-private-index symptom matches, not the same cause.

## 9. #20336: Publishing package to Artifactory subfolder
https://github.com/astral-sh/uv/issues/20336 · reporter's label: `question` · agent escalated: **yes** (confidence medium)

**Agent's reasoning:** The reporter asks how to publish to an Artifactory subfolder with uv, and the template label is question. The search_issues tool found no earlier duplicates. The search_uv_docs call returned only doc paths (indexes.md, package.md, resolution.md) and I did not read them, so the publish-URL documentation was not checked directly. The reporter's own analysis says the subfolder endpoint returns 404 on the classic PyPI API, so the path cannot be fixed on uv's side without a registry-specific change. The report is a question about configuration, with a possible enhancement request hidden inside it.
**Why it escalated:** Torn between question and enhancement: the reporter's need (publishing into a registry-specific subfolder layout that uv's publish flow does not model) could be answered by a documented --publish-url configuration, or could be a feature request for a subfolder-aware publish option. A maintainer should decide whether uv should support this.
**Maintainer's first reply:** "This sounds like a deficiency in Artifactory: based on that link they're not using PyPI's upload API for their "subfolder" concept:  > When attempting to upload specific PyPI packages to designated subfolders for permission control and orga…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| external: agent no vs label yes | [x] | [ ] | [ ] |

Why: The first post says the subfolder endpoint doesn't exist in the standard PyPI API and that JFrog's own workaround bypasses it via REST API and curl. That is direct evidence of an external cause. The agent restated it in its reasoning ("cannot be fixed on uv's side") and still marked external as no. The maintainer called it an Artifactory deficiency and the reporter agreed.

## 10. #22184: Python 3.14.8 missing from `uv python list` on x86_64 macOS with `python-downloads = "manual"`
https://github.com/astral-sh/uv/issues/22184 · reporter's label: `bug` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter's template says bug and the core complaint (3.14.8 absent from `uv python list` while `uv python install 3.14.8` succeeds on the same platform) is inconsistent with the documented behaviour that the listing shows the latest patch of available downloads, so it reads as a real defect, though the pasted output shows installed interpreters only and cannot prove the download entry was missing. The `uv python install 3` / `install 3.14` 'already installed' result is documented behaviour (uv verifies an existing managed install and does not upgrade patch versions), so that part is not a bug on its own. Searching issues found no matching duplicate. Docs (python-versions.md) say available Python versions are frozen per uv release and python-downloads=manual only restricts downloads to `uv python install`. A full listing and the architecture/config details are needed before a maintainer can reproduce.
**Maintainer's first reply:** "`uv python list` is intended to show installed versions and when you have automatic downloads enabled we show the downloadable versions since they are transparently available. I think it's as-designed that `--only-downloads` opts you in to …"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `bug` vs label `enhancement` | [x] | [ ] | [ ] |
| needs-mre: agent yes vs label no | [x] | [ ] | [ ] |

Why: Timing caveat: the original first post doesn't mention `python-downloads = "manual"`; the reporter added it to the title and a follow-up comment after finding the cause. On the original body alone this would be "label wrong" (hindsight). But the agent's reasoning shows it saw the `manual` setting and misread the docs, assuming the listing always shows downloads when they're only shown with automatic downloads enabled. The maintainer called it as-designed; labels became enhancement + needs-decision. Steps, output and version were enough, so no MRE was needed.

## 11. #20945: ModuleNotFound when run 'uv run <project_name>' in mac
https://github.com/astral-sh/uv/issues/20945 · reporter's label: `bug` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter labels this a bug, and I keep the type as bug because uv reports the package as installed when the import path is broken. The decisive clue is that the install is correct per uv's own cache heuristic: the docs (cache.md) say local directory editables are only rebuilt when pyproject.toml changes, and touching the file forces a rebuild, so this matches documented behaviour. The failure lies in the .pth link not being honoured at import time, which points to macOS or Python (hidden .pth files, plausibly from the Desktop/iCloud location) rather than uv. Search found 16977 and 9902 with the same macOS ModuleNotFound pattern. Needs an MRE with verbose output and a .pth/hidden-flag check before any action.
**Maintainer's first reply:** "Opened PR #20954 with a fix: uv now verifies that the .pth files recorded in the editable install RECORD are still present, and repairs the install (re-syncs) when one is missing.…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| needs-mre: agent yes vs label no | [x] | [ ] | [ ] |
| external: agent yes vs label no | [ ] | [ ] | [x] |
| duplicate: agent listed #16977, #9902 vs maintainer's target none | [ ] | [ ] | [x] |

Why: The first post has repro steps, verbose logs of failing and recovering runs, and the version, so an MRE request was unnecessary. The external call is more defensible than it looks: on macOS, `.venv` files can get the hidden flag, recent CPython skips hidden `.pth` files, and the project sits under `~/Desktop` (fits the iCloud hypothesis). Still, uv owns the stale "already installed" check, and the PR fixes that by repairing *missing* `.pth` files (not hidden ones, so it may not fix this cause). The reference "maintainer reply" is a contributor PR, not a maintainer decision. Check #16977/#9902 before scoring: if they're hidden-`.pth` reports, they may be true duplicates.

---

## Patterns
After all items: which failure types repeat? Which would a prompt, tool, or guardrail change fix?

**Tally (20 lines):** 12 agent wrong, 1 label wrong, 7 ambiguous.

| Field | Agent wrong | Label wrong | Ambiguous |
|---|---|---|---|
| needs-mre (4) | 4 | 0 | 0 |
| duplicate (6) | 4 | 0 | 2 |
| type (6) | 3 | 0 | 3 |
| external (4) | 1 | 1 | 2 |

**1. needs-mre is the weakest field (4/4 wrong).** Over-requested in #6, #10, #11 (#11 had full verbose logs); under-requested in #5 (repro needed a PyPI publish and contradicted known design). The agent scores how complete the post looks, not whether a maintainer can act. *Fix (prompt):* redefine as "can a maintainer diagnose or act without asking anything?" with counter-examples: an error that names its own fix needs no MRE; a repro needing external publishing, or a claim contradicting core design, does.

**2. "Duplicate" used for "related"** (#5, #7, #8, plus #1's stale target). The reasoning often says "related" or "no exact duplicate" while the field is filled. *Fix (schema + guardrail):* split into `duplicate_of` and `related`; require same root cause and same requested outcome; reject a duplicate when the reasoning says "related" / "no exact duplicate".

**3. Search on symptoms, not causes or canonical trackers** (#1, #4). In #4 the agent had the right root-cause hypothesis and never searched for it. *Fix (prompt/tool):* require a second search on the agent's own root-cause hypothesis; rank open, recent or pinned tracking issues above old closed ones (matters for recurring topics like AV false positives).

**4. Reasoning contradicts output fields** (#1 type, #7, #9). The right answer is already in the prose. *Fix (guardrail):* a final field-vs-reasoning consistency pass: "can't be fixed on uv's side" → external; "not a uv behaviour problem" → not bug; "no exact duplicate" → empty duplicate field.

**5. Docs tool failures cause wrong calls, not just lower confidence** (#3 directly; also #5, #7, #8, #9, #10). In #3 the existing `environments` setting was the whole answer and a rate-limited docs search hid it; in #8 the budget ran out before reading the Google integration guide the maintainer later linked. *Fix (tooling):* retry with backoff or a cached docs index; reserve budget to read at least one returned doc page; when the docs check fails, forbid "not configurable" conclusions in the prompt.

**6. Undocumented behaviour treated as a bug** (#2, #10). *Fix (prompt):* no documented guarantee → lean enhancement/question; a bug needs a documented or obviously intended contract to violate.

**7. Inconsistent use of known concepts.** Universal resolution was applied correctly in #3 but called an "inconsistency" in #8. *Fix (prompt):* a short glossary of core uv concepts (universal resolution, editable-install cache, uvx isolation).

**8. Eval-data hygiene (not agent errors).** #10's first post was edited after the reporter found the cause (snapshot issues at triage time); #11's reference reply is a contributor PR; #5's reference was confirmed only by the reporter's later admission. Flag these as noisy references so they don't skew scores.
