"""Tools the agent can call. Every one is read-only by construction.

That is the first guardrail: there is no tool that can comment, label, or close,
so no prompt (and no prompt injection inside an issue) can make the agent do it.
"""

import json
from dataclasses import asdict

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .github import GitHub, IssueSnapshot


def _tool(name: str, description: str, properties: dict, required: list[str]) -> dict:
    return {
        "name": name,
        "description": description,
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


TOOLS = [
    _tool(
        "search_issues",
        "Search earlier astral-sh/uv issues (only ones filed before the issue being triaged) to find "
        "duplicates or related reports. Use a few distinctive keywords, e.g. an error message fragment "
        "or a flag name, not a whole sentence; try a second phrasing if the first finds nothing. "
        "Returns number, title, state, labels, and a body excerpt.",
        {"query": {"type": "string", "description": "GitHub search keywords"}},
        ["query"],
    ),
    _tool(
        "search_uv_docs",
        "Search the uv documentation (docs/*.md) for a setting, flag, or concept. Pages are ranked by how many "
        "of your keywords they contain, so use a few distinctive terms (e.g. 'environments universal' or "
        "'no-hashes export'). Returns paths with a snippet; read the most relevant one with read_uv_doc. Use "
        "this to check whether reported behaviour is documented / intended, or whether a config key or flag "
        "the reporter used actually exists.",
        {"query": {"type": "string"}},
        ["query"],
    ),
    _tool(
        "read_uv_doc",
        "Read one uv documentation page returned by search_uv_docs.",
        {"path": {"type": "string", "description": "e.g. docs/concepts/projects/config.md"}},
        ["path"],
    ),
    _tool(
        "get_package_metadata",
        "Look up a Python package on PyPI: its declared dependencies (requires_dist) and requires_python. "
        "Use this when uv's resolution looks wrong, to check whether a dependency's own constraints explain it.",
        {
            "name": {"type": "string"},
            "version": {"type": "string", "description": "Exact version, or empty string for latest"},
        },
        ["name", "version"],
    ),
]
TOOL_NAMES = {t["name"] for t in TOOLS}


class _Query(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=1, max_length=200)


class _Path(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=1, max_length=300)


class _Package(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    version: str = Field(max_length=50)


class ToolResult(BaseModel):
    content: str
    is_error: bool = False
    seen_issue_numbers: list[int] = []  # issues the agent legitimately saw (for the duplicate guardrail)


def run_tool(name: str, raw_input: dict, *, gh: GitHub, issue: IssueSnapshot) -> ToolResult:
    """Execute one tool call. Failures come back as `is_error` results the model can react to,
    never as exceptions that kill the run."""
    if name not in TOOL_NAMES:
        return ToolResult(content=f"Unknown tool {name!r}. Available: {sorted(TOOL_NAMES)}", is_error=True)
    try:
        if name == "search_issues":
            args = _Query.model_validate(raw_input)
            hits = gh.search_issues(args.query, before=issue.created_at, exclude=issue.number)
            if not hits:
                return ToolResult(content="No matching earlier issues.")
            return ToolResult(
                content=json.dumps([asdict(h) for h in hits], indent=1),
                seen_issue_numbers=[h.number for h in hits],
            )
        if name == "search_uv_docs":
            args = _Query.model_validate(raw_input)
            hits = gh.search_docs(args.query)
            if not hits:
                return ToolResult(content="No matching docs pages.")
            return ToolResult(content="\n".join(f"{p}\n    …{snip}…" for p, snip in hits))
        if name == "read_uv_doc":
            args = _Path.model_validate(raw_input)
            text, cut = gh.read_doc(args.path)
            note = f"\n\n[truncated: {cut} more characters not shown]" if cut else ""
            return ToolResult(content=text + note)
        if name == "get_package_metadata":
            args = _Package.model_validate(raw_input)
            meta = gh.package_metadata(args.name, args.version or None)
            return ToolResult(content=json.dumps(meta, indent=1))
    except ValidationError as e:
        return ToolResult(content=f"Invalid input: {e.errors(include_url=False)}", is_error=True)
    except ValueError as e:
        return ToolResult(content=f"Rejected: {e}", is_error=True)
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:300]
        return ToolResult(content=f"Upstream returned HTTP {e.response.status_code}: {detail}", is_error=True)
    except httpx.HTTPError as e:
        return ToolResult(content=f"Network error ({type(e).__name__}); try again or proceed without it", is_error=True)
    raise AssertionError("unreachable")
