# Hand-triage worksheet: 10 real uv issues

**Rules**
1. Open the issue and read **only the first post**. Stop before the comments and ignore the labels in the sidebar (they show the answer).
2. Fill in your call *before* you scroll down.
3. Then read the thread, write down what the maintainer actually did, and note where you were wrong and why.

The answers are in `answer_key.json`. Don't open it until you've finished all 10.

**Possible calls** (pick one type, plus any flags that apply):
- Type: `bug` · `enhancement` · `question` · `documentation`
- Flags: `needs-mre` (can't act without a reproduction) · `external` (the cause is outside uv) · `duplicate` (of #?) · `escalate` (needs a maintainer's product decision)

"Reporter's label" is the label the reporter's template applied. It's their guess, not the answer.

---

## 1. #21824: uv lock fails to pick up direct dependencies
https://github.com/astral-sh/uv/issues/21824 · Reporter's label: `bug`
- My call:
- My reasoning (which clues?):
- What the maintainer did:
- Where I was wrong / what I learned:

## 2. #22111: uv sync produces incorrect warning about entry points (project.scripts)
https://github.com/astral-sh/uv/issues/22111 · Reporter's label: `bug`
- My call:
- My reasoning:
- What the maintainer did:
- Lesson:

## 3. #21694: `uv pip install --target=.` fails for every wheel
https://github.com/astral-sh/uv/issues/21694 · Reporter's label: `bug`
- My call:
- My reasoning:
- What the maintainer did:
- Lesson:

## 4. #20931: `uv add` fails with "Expected `--hash`"
https://github.com/astral-sh/uv/issues/20931 · Reporter's label: `bug`
- My call:
- My reasoning:
- What the maintainer did:
- Lesson:

## 5. #21972: uv sync accesses unavailable files even when told not to
https://github.com/astral-sh/uv/issues/21972 · Reporter's label: `bug`
- My call:
- My reasoning:
- What the maintainer did:
- Lesson:

## 6. #22006: uv tool install --force --reinstall mutates the tool environment in place
https://github.com/astral-sh/uv/issues/22006 · Reporter's label: `bug`
- My call:
- My reasoning:
- What the maintainer did:
- Lesson:

## 7. #21641: uv seems to fail unpacking a source distribution's tar file
https://github.com/astral-sh/uv/issues/21641 · Reporter's label: `bug`
- My call:
- My reasoning:
- What the maintainer did:
- Lesson:

## 8. #21122: `uv export --format cyclonedx1.5` omits component hashes
https://github.com/astral-sh/uv/issues/21122 · Reporter's label: *(none)*
- My call:
- My reasoning:
- What the maintainer did:
- Lesson:

## 9. #21273: uv sync --upgrade does not upgrade a transitive dependency (setuptools)
https://github.com/astral-sh/uv/issues/21273 · Reporter's label: `bug`
- My call:
- My reasoning:
- What the maintainer did:
- Lesson:

## 10. #22262: Export sometimes does not respect conditional platforms on extra packages
https://github.com/astral-sh/uv/issues/22262 · Reporter's label: `bug`
- My call:
- My reasoning:
- What the maintainer did:
- Lesson:

---

## After all 10: your triage rules
Write 3–6 rules you found yourself using (e.g. "If the first maintainer reply is a config fix, it was a question"). These become the first draft of the agent's system prompt.
1.
2.
3.
