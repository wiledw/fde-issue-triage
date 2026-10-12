# Adjudication sheet

For each disagreement, open the issue, read **the first post only**, and decide:

- **agent wrong**: the first post supports the maintainer's call
- **label wrong**: the first post supports the agent's call (label noise, or hindsight the agent couldn't see)
- **ambiguous**: a reasonable maintainer could go either way

Then read the thread and add a short *why*. Mark one box per disagreement line with `x`.

## 1. #21009: Add `--active` flag for `uv lock`
https://github.com/astral-sh/uv/issues/21009 · reporter's label: `enhancement` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter asks for a new --active flag on uv lock so it can ignore an invalid .venv, which is a request for new behaviour, so enhancement; this matches the template label. The docs (concepts/projects/sync.md) describe locking as project-level and do not say uv lock needs the project environment, so the failure the reporter sees is arguably a separate bug, and the referenced #19832 did not appear in any of my searches, so I did not list it as a duplicate. No external cause is shown. Searches for --active and for uv lock with a broken .venv found only related issues (#17780, #15603, #11315), none with the same requested outcome. The reporter gives no error text or uv version, but a maintainer can reproduce by creating a .venv with no interpreter, so no MRE is required. Tool coverage was limited to 7 calls and #19832 was not retrievable, so confidence is medium.
**Maintainer's first reply:** "I think `uv lock` should just not fail if the environment is invalid. I don't think we should add an `--active` flag to it.…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `enhancement` vs label `bug` | [ ] | [ ] | [ ] |
| duplicate: agent listed none vs maintainer's target #19832 | [ ] | [ ] | [ ] |

Why:

## 2. #20875: Cannot opt into prerelease build requirements in uv 0.12
https://github.com/astral-sh/uv/issues/20875 · reporter's label: `bug` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter says --prerelease, --prerelease-package, UV_PRERELEASE, tool.uv.prerelease and uv.toml prerelease have no effect on build-system.requires resolution after the 0.12 if-necessary default change, and that the flags are silently ignored. The uv pre-release compatibility docs state that --prerelease allow considers pre-releases 'for every package', so a flag documented to apply to every package not applying to build requirements (and failing silently) is a misbehaviour against a documented contract, not a design choice the docs spell out. The docs have no page saying build dependencies are exempt from prerelease settings. Reproduction is straightforward from the issue (a build-system requires with a prerelease-only solution), so no MRE is needed. No duplicate found in search. Confidence is medium because the 'every package' wording is the only contract, and the reporter's ask partly reads as a new option (--build-prerelease), which would be an enhancement.
**Maintainer's first reply:** "Thanks for the report, we'll look into a solution here.…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `bug` vs label `enhancement` | [ ] | [ ] | [ ] |

Why:

## 3. #20917: workspace groups no longer additive for members
https://github.com/astral-sh/uv/issues/20917 · reporter's label: `bug` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter names a concrete regression point (worked before, changed in 0.12.1) for dependency-group resolution when syncing a workspace member that has a dev group of the same name as the workspace root. Playbook rule 2 treats a release-named regression as a strong bug signal, and the report is specific enough to reproduce (root and member each declare dev, run sync from the member directory). The docs page for workspaces (docs/concepts/projects/workspaces.md) does not state whether root dependency groups merge into members, so the contract is not documented, which lowers confidence to medium. Nothing points outside uv, and the report does not hinge on an enforcement change, so rule 2's exception does not apply. search_issues for the override/additive symptom returned no matching earlier issues, and the only search hit (#8148, cyclic dev deps) is a different problem, so it is not listed. The search tool returned no duplicates; this is not verified against the full tracker.
**Maintainer's first reply:** "Hm, the former behavior you're describing does not match my understanding of what should have been happening. If we were merging those groups, that sounds like a bug? …"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `bug` vs label `enhancement` | [ ] | [ ] | [ ] |

Why:

## 4. #21635: Support org formatted README by default
https://github.com/astral-sh/uv/issues/21635 · reporter's label: `enhancement` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter asks uv to accept README.org by default, without a stated defect. Docs (config.md) define no README format allow-list, and the request is for different behaviour, so enhancement, matching the reporter's label. No reproduction is needed because the request is clear and the body states the error is about extension recognition. Search found closed #9821 (README.org build failure, labelled question) as related context; it is not an exact duplicate. I did not confirm which component (uv or the build backend) emits the 'not recognized' error and the issue gives no error text, so likely_external is false with medium confidence; a maintainer should check which backend rejects the .org file before routing.
**Maintainer's first reply:** "What is the error? How would you expect it to be supported?…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| external: agent no vs label yes | [ ] | [ ] | [ ] |

Why:

## 5. #21747: frozen block UV_DEFAULT_INDEX and UV_INDEX_STRATEGY
https://github.com/astral-sh/uv/issues/21747 · reporter's label: `bug` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** Under --frozen uv performs no resolution and installs from the lockfile as-is, so UV_INDEX_STRATEGY has nothing to act on and UV_DEFAULT_INDEX is not applied to locked source URLs. This is consistent with uv's design (the lock records its index URLs) and the docs (indexes.md) define UV_INDEX_STRATEGY only as a resolution setting, so there is no documented contract that --frozen honors index env vars; the reporter's wish that it should is a behaviour change, hence enhancement rather than the reporter's bug label. The report includes the Dockerfile, command, uv version (0.12.15) and platform, so a maintainer can reproduce it without asking. Closest prior issue is 19625 (same symptom and request, closed); I did not confirm its resolution, so confidence is medium.
**Maintainer's first reply:** "`--frozen`'s effect is that archives are downloaded from locations captured in `uv.lock` - if you want to use your own index, you'll have to apply these env vars while `uv.lock` is being produced. Alternatively, you can wait for https://git…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `enhancement` vs label `question` | [ ] | [ ] | [ ] |
| duplicate: agent listed #19625 vs maintainer's target none | [ ] | [ ] | [ ] |

Why:

## 6. #20567: uv venv: Windows PE resource error due to Bitdefender Incident Sensor
https://github.com/astral-sh/uv/issues/20567 · reporter's label: `bug` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter labels this a bug, and I keep that type: uv venv is plainly meant to succeed, and a transient failure with no retry is a robustness gap. The root cause is Bitdefender Incident Sensor interfering with the freshly written trampoline exe. The repro is intermittent and disabling the AV resolves it, so the defect is external (likely_external true). A uv-side bounded retry on transient Windows file errors is a reasonable mitigation the maintainers could consider, but the underlying fault is in the AV product. The report has a repro script, exact error, version and OS, so needs_mre is false. Search found #19873 with the same error text (closed as duplicate of an unidentified canonical), and found no other exact match for the AV-plus-PE-write cause. The related-issue search for Bitdefender turned up only installer false positives. Two calls returned the same results, so the search is stable, though it is a limited sample.
**Maintainer's first reply:** "I’m not completely opposed to implementing workarounds like these, but it seems fairly clear that this issue originates in the endpoint security tool, rather than uv. It's ultimately the responsibility of these tools to achieve their goals …"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| duplicate: agent listed #19873 vs maintainer's target #9543 | [ ] | [ ] | [ ] |

Why:

## 7. #20996: Unable to install `redis[hiredis]` correctly
https://github.com/astral-sh/uv/issues/20996 · reporter's label: `none` · agent escalated: **yes** (confidence low)

**Agent's reasoning:** The report gives no command, lockfile excerpt, or pyproject, only a summary and a screenshot, so there is nothing a maintainer can reproduce. Package metadata shows the current redis (8.1.0) declares hiredis>=3.2.0 for the hiredis extra, so getting hiredis 2.0.0 means some other pin or an older redis in the reporter's project is forcing it; that is a dependency's constraint, which the playbook treats as a question, not a bug. Searches for the redis/hiredis symptom returned no matching uv issues, and hiredis 2.0.0 metadata shows no requirements, so no external defect is evidenced. The reporter's bug label is not supported by the evidence; confidence is low because the reporter's lockfile and pins were not available to check.
**Why it escalated:** low confidence (forced by guardrail)
**Maintainer's first reply:** "What commands did you run? What version of redis is in `uv.lock`?…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| needs-mre: agent yes vs label no | [ ] | [ ] | [ ] |
| external: agent no vs label yes | [ ] | [ ] | [ ] |

Why:

## 8. #19988: uv resolves torchvision to 0.27.1+df56172 on Linux from the PyTorch CPU index
https://github.com/astral-sh/uv/issues/19988 · reporter's label: `bug` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter's pyproject matches the documented PyTorch CPU-index configuration in docs/guides/integration/pytorch.md, so the config is valid and uv is not violating a documented contract. uv's lock is universal, so it resolves torchvision across all platforms and picks the highest version, which is the +df56172 local build whose only wheels are win_arm64; the install then fails on Linux. That points to the PyTorch index publishing a mis-labelled platform-specific build, which is outside uv. Possible uv-side mitigation is restricting the lock with [tool.uv] environments, or the reporter pinning torchvision to a +cpu version. No duplicate was found in search. Tool limits: the package metadata lookup returned HTTP 404 and no issue on the local-version ordering was found, so confidence is medium.
**Maintainer's first reply:** "I have to look when I’m at my desk but this is technically correct… for local versions, you’re supposed to sort lexicographically. I have to imagine it’s a mistake that it was included on the index?  You can likely fix this by setting requi…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `question` vs label `bug` | [ ] | [ ] | [ ] |
| external: agent yes vs label no | [ ] | [ ] | [ ] |

Why:

## 9. #20613: Add support for single-file environment
https://github.com/astral-sh/uv/issues/20613 · reporter's label: `enhancement` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter wants to declare the Python version and dependencies inside a single script and run it with `uv run main.py`. uv already does this through PEP 723 inline metadata: a `# /// script` block with `requires-python` and `dependencies` is honored by `uv run`, which selects the interpreter and builds a per-script environment (docs/guides/scripts.md, 'Declaring script dependencies' and 'Using different Python versions'). The reporter's `# -*- ... -*-` comment syntax is not a recognized format, and `env_name` has no counterpart because uv manages per-script environments automatically. The reporter's template says enhancement, but the existing setting covers the request, so I classify it as a question. The lack of an exact duplicate in search results is noted. Remaining uncertainty is whether a maintainer would still treat named environments as a feature request, hence medium confidence.
**Maintainer's first reply:** "Isn't this already implemented, just with different syntax?  https://docs.astral.sh/uv/guides/scripts/#declaring-script-dependencies…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `question` vs label `enhancement` | [ ] | [ ] | [ ] |

Why:

## 10. #21065: author field in pyproject.toml is being interpret as TOML 1.1 by uv build
https://github.com/astral-sh/uv/issues/21065 · reporter's label: `bug` · agent escalated: **no** (confidence medium)

**Agent's reasoning:** The reporter labels this a bug, but uv's build-backend docs (docs/concepts/build-backend.md, 'File inclusion and exclusion') state that a source distribution includes the pyproject.toml rewritten to TOML 1.0-compatible syntax with the original kept as pyproject.toml.orig. So the file's presence is documented, intended behaviour, and the report asks for a change to it, which makes this an enhancement. The reporter's TOML 1.1 hypothesis does not explain the .orig file; the rewrite is documented as a TOML 1.0 normalization step. The post does not say which build backend was used (uv_build or another), and that would change the picture, but a maintainer can act on the documented behaviour without asking. No duplicate found; #20049 is only related. Search tool results were consistent and the docs page was read in full.
**Maintainer's first reply:** "As of uv 0.12, we always rewrite the `pyproject.toml` for consistency, even if you're only using TOML 1.0 syntax.…"

| Disagreement | agent wrong | label wrong | ambiguous |
|---|---|---|---|
| type: agent `enhancement` vs label `question` | [ ] | [ ] | [ ] |

Why:

---

## Patterns
After all items: which failure types repeat? Which would a prompt, tool, or guardrail change fix?
