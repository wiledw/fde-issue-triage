from triage.render import suggestion_card
from triage.schema import TriageResult


def result(**kw):
    base = dict(
        type="question", type_differs_from_reporter=True, needs_mre=False, missing_info=[], likely_external=False,
        external_evidence="", possible_duplicates=[], related_issues=[], confidence="medium",
        escalate_to_human=False, escalation_reason="", rationale="docs say so",
    )
    return TriageResult.model_validate(base | kw)


def test_escalated_card_says_why_and_shows_relabel():
    card = suggestion_card(1, result(escalate_to_human=True, escalation_reason="changes the reporter's label"), "bug")
    assert "Needs a maintainer decision" in card
    assert "changes the reporter's label" in card
    assert "reporter filed as `bug`" in card
    assert "not posted" in card


def test_card_lists_only_the_flags_that_apply():
    card = suggestion_card(
        2,
        result(needs_mre=True, missing_info=["uv version"], possible_duplicates=[{"number": 9, "reason": "same"}]),
    )
    assert "Suggested triage" in card and "Ask for: uv version" in card and "[#9]" in card
    assert "Likely external" not in card and "Related" not in card
