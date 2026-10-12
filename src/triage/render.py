"""Render a triage result as a suggestion card for a maintainer.

The card is a draft for a human. The tool never posts it: there is no write access to
GitHub anywhere in this codebase.
"""

from .schema import TriageResult

REPO_URL = "https://github.com/astral-sh/uv/issues"


def _refs(refs) -> str:
    return ", ".join(f"[#{d.number}]({REPO_URL}/{d.number}) ({d.reason})" for d in refs)


def suggestion_card(issue: int, t: TriageResult, reporter_label: str | None = None) -> str:
    action = "🔎 **Needs a maintainer decision**" if t.escalate_to_human else "✅ **Suggested triage**"
    label = f"`{t.type}`"
    if reporter_label and t.type_differs_from_reporter:
        label += f" (reporter filed as `{reporter_label}`)"
    lines = [f"### Triage suggestion for [#{issue}]({REPO_URL}/{issue})", "", action, "",
             f"- **Type:** {label}  ·  confidence: {t.confidence}"]
    if t.escalate_to_human and t.escalation_reason:
        lines.append(f"- **Why a human should check:** {t.escalation_reason}")
    if t.needs_mre:
        asks = "; ".join(t.missing_info) or "a minimal reproducible example"
        lines.append(f"- **Needs a reproduction.** Ask for: {asks}")
    if t.likely_external:
        lines.append(f"- **Likely external:** {t.external_evidence}")
    if t.possible_duplicates:
        lines.append(f"- **Possible duplicate of:** {_refs(t.possible_duplicates)}")
    if t.related_issues:
        lines.append(f"- **Related:** {_refs(t.related_issues)}")
    lines += ["", f"**Why:** {t.rationale}", "", "<sub>Draft from an AI triage assistant; not posted, labelled, or closed.</sub>"]
    return "\n".join(lines)
