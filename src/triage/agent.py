"""The triage agent: a hand-written tool-use loop.

Why a manual loop instead of the SDK's tool runner: we need to log every
request and response as it happens, change behaviour on the last turn, and
(Week 2) checkpoint between turns. Owning the loop makes all of that explicit.
"""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import anthropic
from pydantic import ValidationError

from .audit import AuditLog
from .github import GitHub, IssueSnapshot
from .pricing import cost_usd
from .schema import TRIAGE_JSON_SCHEMA, TriageResult
from .tools import TOOLS, run_tool

MODEL = "claude-haiku-5-5"  # v0.4 evals: Haiku beat Sonnet (84% vs 68% type accuracy) at ~1/20th the price
EFFORT = "medium"  # Haiku 5.5's default; set explicitly so a default change can't move our evals
# Server-side refusal fallback exists for these models only (Haiku has none).
FALLBACK_MODELS = ("claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1")
MAX_TURNS = 8
FALLBACK_BETA = "server-side-fallback-2026-07-01"
ESCALATE_ON_RELABEL = True  # see apply_guardrails

_PROMPTS = Path(__file__).parent / "prompts"
_NOT_A_DUPLICATE = re.compile(
    r"\bno (exact |true |real )?duplicates?\b|\bnot (an? )?(exact |true )?duplicates?\b|\bno duplicate (was )?found\b",
    re.IGNORECASE,
)


def system_prompt() -> str:
    return (_PROMPTS / "system.md").read_text() + "\n\n" + (_PROMPTS / "playbook.md").read_text()


def render_issue(issue: IssueSnapshot) -> str:
    labels = ", ".join(issue.reporter_labels) or "(none)"
    note = (
        f"\n[Body truncated: the last {issue.body_truncated_chars} characters are not shown.]"
        if issue.body_truncated_chars
        else ""
    )
    return (
        f"Triage this issue.\n\n"
        f'<issue number="{issue.number}" created_at="{issue.created_at}" reporter_template_label="{labels}">\n'
        f"<title>{issue.title}</title>\n<body>\n{issue.body}\n</body>{note}\n</issue>"
    )


@dataclass
class RunResult:
    issue: int
    status: str  # "ok" | "escalated" (agent could not finish; a human must triage)
    triage: TriageResult | None
    run_id: str
    audit_path: str
    turns: int = 0
    tool_calls: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    guardrail_notes: list[str] = field(default_factory=list)
    error: str | None = None


def _final_text(response) -> str | None:
    texts = [b.text for b in response.content if b.type == "text"]
    return texts[-1] if texts else None


def apply_guardrails(t: TriageResult, *, issue: IssueSnapshot, seen: set[int]) -> tuple[TriageResult, list[str]]:
    """Deterministic checks in code. Prompts ask; code enforces."""
    notes = []

    def verified(refs, field_name):
        kept = []
        for d in refs:
            if d.number == issue.number:
                notes.append(f"dropped self-reference #{d.number} from {field_name}")
            elif d.number not in seen:
                notes.append(f"dropped #{d.number} from {field_name}: never returned by search_issues (unverified)")
            else:
                kept.append(d)
        return kept

    dups = verified(t.possible_duplicates, "duplicates")
    related = verified(t.related_issues, "related")
    # The agent's own prose saying "not a duplicate" beats the field it filled in.
    if dups and _NOT_A_DUPLICATE.search(t.rationale):
        notes.append(f"moved {[d.number for d in dups]} to related: rationale says they are not duplicates")
        related, dups = related + dups, []
    update: dict = {"possible_duplicates": dups, "related_issues": related}
    if t.confidence == "low" and not t.escalate_to_human:
        update |= {"escalate_to_human": True, "escalation_reason": "low confidence (forced by guardrail)"}
        notes.append("forced escalation: confidence was low")
    reporter_types = set(issue.reporter_labels) & {"bug", "enhancement", "question", "documentation"}
    differs = bool(reporter_types) and t.type not in reporter_types
    if differs != t.type_differs_from_reporter:
        update["type_differs_from_reporter"] = differs
        notes.append(f"corrected type_differs_from_reporter to {differs}")
    # Overriding the reporter's label was wrong 4 of 5 times in v0.3 evals, and the model's
    # own confidence did not predict it. Until evals say otherwise, a relabel needs a human.
    if ESCALATE_ON_RELABEL and differs and not update.get("escalate_to_human", t.escalate_to_human):
        reporter_label = ", ".join(sorted(reporter_types))
        update |= {"escalate_to_human": True, "escalation_reason": f"changes the reporter's label ({reporter_label} → {t.type})"}
        notes.append("forced escalation: type differs from the reporter's label")
    return t.model_copy(update=update), notes


def run_triage(
    number: int,
    *,
    client: anthropic.Anthropic | None = None,
    gh: GitHub | None = None,
    log_dir: str | Path = "runs",
    model: str = MODEL,
    max_turns: int = MAX_TURNS,
) -> RunResult:
    client = client or anthropic.Anthropic()
    gh = gh or GitHub()
    log = AuditLog(log_dir)
    system = system_prompt()

    issue = gh.issue_snapshot(number)
    messages: list[dict] = [{"role": "user", "content": render_issue(issue)}]
    log.write("run_start", issue=number, model=model, effort=EFFORT, max_turns=max_turns, system=system, tools=TOOLS)
    log.write("issue_snapshot", snapshot=issue)
    log.write("message", message=messages[0])

    result = RunResult(issue=number, status="escalated", triage=None, run_id=log.run_id, audit_path=str(log.path))
    seen: set[int] = set()
    repaired = False

    def escalate(reason: str) -> RunResult:
        result.status, result.error = "escalated", reason
        log.write("run_end", status=result.status, error=reason, cost_usd=result.cost_usd)
        return result

    for turn in range(max_turns):
        result.turns = turn + 1
        last_turn = turn == max_turns - 1
        fallback = {"betas": [FALLBACK_BETA], "fallbacks": "default"} if model in FALLBACK_MODELS else {}
        try:
            response = client.beta.messages.create(
                **fallback,  # a safety-classifier decline is retried server-side on another model
                model=model,
                max_tokens=16000,
                system=system,
                tools=TOOLS,
                # On the last turn, forbid tools so the model must answer.
                tool_choice={"type": "none"} if last_turn else {"type": "auto"},
                messages=messages,
                thinking={"type": "adaptive", "display": "summarized"},  # summaries land in the audit log
                output_config={"effort": EFFORT, "format": {"type": "json_schema", "schema": TRIAGE_JSON_SCHEMA}},
                cache_control={"type": "ephemeral"},
            )
        except anthropic.APIStatusError as e:
            log.write("error", where="messages.create", status=e.status_code, message=str(e))
            return escalate(f"API error {e.status_code}")
        except anthropic.APIConnectionError as e:
            log.write("error", where="messages.create", message=str(e))
            return escalate("API connection failed after SDK retries")

        log.write("model_response", turn=turn, response=response)
        u = response.usage
        result.input_tokens += (u.input_tokens or 0) + (u.cache_read_input_tokens or 0) + (u.cache_creation_input_tokens or 0)
        result.output_tokens += u.output_tokens or 0
        result.cost_usd += cost_usd(model, u)
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "refusal":
            return escalate("model declined the request (refusal, after fallback)")
        if response.stop_reason == "max_tokens":
            return escalate("response hit max_tokens")

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                log.write("tool_call", turn=turn, name=block.name, input=block.input, tool_use_id=block.id)
                out = run_tool(block.name, block.input, gh=gh, issue=issue)
                seen.update(out.seen_issue_numbers)
                result.tool_calls.append(block.name)
                log.write("tool_result", turn=turn, tool_use_id=block.id, is_error=out.is_error, content=out.content)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": out.content, "is_error": out.is_error}
                )
            messages.append({"role": "user", "content": tool_results})
            continue

        # end_turn: the final answer should be schema-shaped JSON. Verify anyway.
        text = _final_text(response)
        try:
            triage = TriageResult.model_validate(json.loads(text or ""))
        except (json.JSONDecodeError, ValidationError) as e:
            log.write("validation_error", turn=turn, text=text, error=str(e))
            if repaired or last_turn:
                return escalate(f"invalid final output: {e}")
            repaired = True
            fix = f"Your answer did not validate: {e}. Reply with only the corrected JSON object."
            messages.append({"role": "user", "content": fix})
            log.write("message", message=messages[-1])
            continue

        triage, notes = apply_guardrails(triage, issue=issue, seen=seen)
        for n in notes:
            log.write("guardrail", note=n)
        result.triage, result.guardrail_notes, result.status = triage, notes, "ok"
        log.write("run_end", status="ok", triage=triage, cost_usd=result.cost_usd, turns=result.turns)
        return result

    return escalate(f"no final answer within {max_turns} turns")
