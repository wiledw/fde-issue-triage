"""The agent's output contract.

Two definitions of the same shape:
- `TRIAGE_JSON_SCHEMA` is sent to the API as a structured-output format, so the
  model can only emit JSON in this shape.
- `TriageResult` (Pydantic) re-validates what comes back. Never trust that the
  constraint held; check it. `tests/test_schema.py` keeps the two in sync.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

IssueType = Literal["bug", "enhancement", "question", "documentation"]
Confidence = Literal["low", "medium", "high"]


class DuplicateCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    number: int
    reason: str


class TriageResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: IssueType
    type_differs_from_reporter: bool
    needs_mre: bool
    missing_info: list[str] = Field(description="What a maintainer would need to reproduce or act")
    likely_external: bool
    external_evidence: str = Field(description="Empty string when likely_external is false")
    possible_duplicates: list[DuplicateCandidate] = Field(description="Same root cause AND same requested outcome")
    # Default only so pre-v0.3 outputs (no such field) still validate; the API schema requires it.
    related_issues: list[DuplicateCandidate] = Field(
        default_factory=list, description="Useful context, but not the same problem"
    )
    confidence: Confidence
    escalate_to_human: bool
    escalation_reason: str = Field(description="Empty string when escalate_to_human is false")
    rationale: str


_STR = {"type": "string"}
_BOOL = {"type": "boolean"}
_ISSUE_REFS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"number": {"type": "integer"}, "reason": {"type": "string"}},
        "required": ["number", "reason"],
        "additionalProperties": False,
    },
}

TRIAGE_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": ["bug", "enhancement", "question", "documentation"]},
        "type_differs_from_reporter": _BOOL,
        "needs_mre": _BOOL,
        "missing_info": {"type": "array", "items": _STR},
        "likely_external": _BOOL,
        "external_evidence": _STR,
        "possible_duplicates": _ISSUE_REFS,
        "related_issues": _ISSUE_REFS,
        "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        "escalate_to_human": _BOOL,
        "escalation_reason": _STR,
        "rationale": _STR,
    },
    "required": [
        "type",
        "type_differs_from_reporter",
        "needs_mre",
        "missing_info",
        "likely_external",
        "external_evidence",
        "possible_duplicates",
        "related_issues",
        "confidence",
        "escalate_to_human",
        "escalation_reason",
        "rationale",
    ],
    "additionalProperties": False,
}
