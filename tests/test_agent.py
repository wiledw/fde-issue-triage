"""Offline tests for the loop, guardrails, and audit trail: a scripted fake model, no API calls."""

import json
from types import SimpleNamespace as NS

from triage.agent import run_triage
from triage.github import IssueSnapshot, SearchHit

ISSUE = IssueSnapshot(
    number=500, title="uv sync fails", body="It fails. Is this a bug?", reporter="alice",
    created_at="2026-09-01T00:00:00Z", reporter_labels=["bug"],
)


def usage():
    return NS(input_tokens=1000, output_tokens=200, cache_read_input_tokens=0, cache_creation_input_tokens=0)


def tool_call(name, inp, id_="t1"):
    return NS(stop_reason="tool_use", usage=usage(), content=[NS(type="tool_use", id=id_, name=name, input=inp)])


def final(**overrides):
    body = {
        "type": "question", "type_differs_from_reporter": True, "needs_mre": False, "missing_info": [],
        "likely_external": False, "external_evidence": "", "possible_duplicates": [], "related_issues": [],
        "confidence": "high", "escalate_to_human": False, "escalation_reason": "", "rationale": "r",
    } | overrides
    return NS(stop_reason="end_turn", usage=usage(), content=[NS(type="text", text=json.dumps(body))])


class FakeClient:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw | {"messages": list(kw["messages"])})  # snapshot: the loop keeps appending
        return self.responses.pop(0)


class FakeGitHub:
    def __init__(self, fail_search=False):
        self.fail_search = fail_search

    def issue_snapshot(self, n):
        return ISSUE

    def search_issues(self, query, *, before, exclude, limit=8):
        if self.fail_search:
            import httpx
            raise httpx.ConnectTimeout("boom")
        assert before == ISSUE.created_at and exclude == ISSUE.number  # no peeking at the future
        return [SearchHit(number=42, title="same thing", state="open", state_reason=None, labels=[],
                          created_at="2026-01-01T00:00:00Z", body_excerpt="")]


def events(res):
    return [json.loads(line)["event"] for line in open(res.audit_path)]


def test_tool_loop_then_valid_answer_with_dup_guardrail(tmp_path):
    client = FakeClient([
        tool_call("search_issues", {"query": "sync fails"}),
        final(possible_duplicates=[{"number": 42, "reason": "same"}, {"number": 999, "reason": "made up"}]),
    ])
    res = run_triage(500, client=client, gh=FakeGitHub(), log_dir=tmp_path)
    assert res.status == "ok"
    assert [d.number for d in res.triage.possible_duplicates] == [42]  # 999 was never seen -> dropped
    assert any("999" in n for n in res.guardrail_notes)
    assert res.tool_calls == ["search_issues"] and res.turns == 2
    assert res.cost_usd > 0
    ev = events(res)
    assert ev[0] == "run_start" and ev[-1] == "run_end"
    assert {"tool_call", "tool_result", "model_response", "guardrail"} <= set(ev)


def test_rationale_saying_not_duplicate_moves_dups_to_related(tmp_path):
    client = FakeClient([
        tool_call("search_issues", {"query": "x"}),
        final(possible_duplicates=[{"number": 42, "reason": "similar"}], rationale="#42 is related; no exact duplicate."),
    ])
    res = run_triage(500, client=client, gh=FakeGitHub(), log_dir=tmp_path)
    assert res.triage.possible_duplicates == []
    assert [d.number for d in res.triage.related_issues] == [42]


def test_unseen_related_issue_is_dropped(tmp_path):
    res = run_triage(500, client=FakeClient([final(related_issues=[{"number": 7, "reason": "made up"}])]),
                     gh=FakeGitHub(), log_dir=tmp_path)
    assert res.triage.related_issues == []


def test_low_confidence_forces_escalation(tmp_path):
    res = run_triage(500, client=FakeClient([final(confidence="low")]), gh=FakeGitHub(), log_dir=tmp_path)
    assert res.status == "ok" and res.triage.escalate_to_human is True


def test_type_differs_is_recomputed_in_code(tmp_path):
    res = run_triage(500, client=FakeClient([final(type="bug", type_differs_from_reporter=True)]),
                     gh=FakeGitHub(), log_dir=tmp_path)
    assert res.triage.type_differs_from_reporter is False  # reporter said bug, agent said bug


def test_relabel_forces_escalation_but_agreement_does_not(tmp_path):
    relabel = run_triage(500, client=FakeClient([final(type="question")]), gh=FakeGitHub(), log_dir=tmp_path)
    assert relabel.triage.escalate_to_human is True
    assert "bug → question" in relabel.triage.escalation_reason
    agree = run_triage(500, client=FakeClient([final(type="bug", type_differs_from_reporter=False)]),
                       gh=FakeGitHub(), log_dir=tmp_path)
    assert agree.triage.escalate_to_human is False


def test_fallback_params_only_sent_to_models_that_support_them(tmp_path):
    haiku = FakeClient([final()])
    run_triage(500, client=haiku, gh=FakeGitHub(), log_dir=tmp_path)  # default model
    assert "fallbacks" not in haiku.calls[0] and haiku.calls[0]["model"] == "claude-haiku-5-5"
    opus = FakeClient([final()])
    run_triage(500, client=opus, gh=FakeGitHub(), log_dir=tmp_path, model="claude-opus-5-5")
    assert opus.calls[0]["fallbacks"] == "default"


def test_refusal_escalates(tmp_path):
    refusal = NS(stop_reason="refusal", usage=usage(), content=[])
    res = run_triage(500, client=FakeClient([refusal]), gh=FakeGitHub(), log_dir=tmp_path)
    assert res.status == "escalated" and "refus" in res.error


def test_tool_failure_is_reported_to_model_not_raised(tmp_path):
    client = FakeClient([tool_call("search_issues", {"query": "x"}), final()])
    res = run_triage(500, client=client, gh=FakeGitHub(fail_search=True), log_dir=tmp_path)
    assert res.status == "ok"
    tool_result = client.calls[1]["messages"][-1]["content"][0]
    assert tool_result["is_error"] is True


def test_invalid_output_gets_one_repair_then_escalates(tmp_path):
    bad = NS(stop_reason="end_turn", usage=usage(), content=[NS(type="text", text='{"type": "bug"}')])
    res = run_triage(500, client=FakeClient([bad, bad]), gh=FakeGitHub(), log_dir=tmp_path)
    assert res.status == "escalated" and "invalid final output" in res.error
    assert events(res).count("validation_error") == 2


def test_last_turn_disables_tools(tmp_path):
    client = FakeClient([tool_call("search_issues", {"query": "x"}, id_=f"t{i}") for i in range(2)] + [final()])
    res = run_triage(500, client=client, gh=FakeGitHub(), log_dir=tmp_path, max_turns=3)
    assert res.status == "ok"
    assert [c["tool_choice"]["type"] for c in client.calls] == ["auto", "auto", "none"]


def test_unknown_tool_is_rejected(tmp_path):
    client = FakeClient([tool_call("close_issue", {"number": 500}), final()])
    res = run_triage(500, client=client, gh=FakeGitHub(), log_dir=tmp_path)
    assert client.calls[1]["messages"][-1]["content"][0]["is_error"] is True
    assert res.status == "ok"
