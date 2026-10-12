"""The schema sent to the API and the Pydantic model must agree, the issue snapshot must not
leak answers or later edits, and the GitHub client must survive rate limits."""

import json

import httpx

from triage.github import GitHub
from triage.schema import TRIAGE_JSON_SCHEMA, TriageResult


def test_json_schema_matches_pydantic_model():
    assert set(TRIAGE_JSON_SCHEMA["properties"]) == set(TriageResult.model_fields)
    assert set(TRIAGE_JSON_SCHEMA["required"]) == set(TriageResult.model_fields)


def issue_handler(edits=(), renames=()):
    def handler(req: httpx.Request):
        if req.url.path == "/graphql":
            return httpx.Response(200, json={"data": {"repository": {"issue": {"userContentEdits": {"nodes": list(edits)}}}}})
        if req.url.path.endswith("/timeline"):
            return httpx.Response(200, json=[
                {"event": "labeled", "actor": {"login": "alice"}, "label": {"name": "bug"}},
                *[{"event": "renamed", "rename": {"from": f, "to": t}} for f, t in renames],
                {"event": "unlabeled", "actor": {"login": "maintainer"}, "label": {"name": "bug"}},
                {"event": "labeled", "actor": {"login": "maintainer"}, "label": {"name": "question"}},
                {"event": "commented", "actor": {"login": "maintainer"}, "body": "this is a config typo"},
            ])
        return httpx.Response(200, json={
            "title": "final title (found the cause)", "body": "edited body with the answer",
            "user": {"login": "alice"}, "created_at": "2026-09-01T00:00:00Z", "labels": [{"name": "question"}],
        })
    return handler


def test_snapshot_keeps_only_reporter_labels():
    snap = GitHub(token="x", transport=httpx.MockTransport(issue_handler())).issue_snapshot(1)
    assert snap.reporter_labels == ["bug"]  # not the maintainer's "question"
    assert "typo" not in snap.body
    assert snap.edited_after_posting is False


def test_snapshot_shows_original_title_and_body():
    edits = [{"editedAt": "2026-09-02T00:00:00Z", "diff": "edited body with the answer"},
             {"editedAt": "2026-09-01T00:00:00Z", "diff": "original body"}]
    renames = [("original title", "middle title"), ("middle title", "final title (found the cause)")]
    snap = GitHub(token="x", transport=httpx.MockTransport(issue_handler(edits, renames))).issue_snapshot(1)
    assert snap.title == "original title"
    assert snap.body == "original body"
    assert snap.edited_after_posting is True


def test_rate_limit_is_retried_after_waiting():
    calls, waits = [], []

    def handler(req):
        calls.append(req.url.path)
        if len(calls) == 1:
            return httpx.Response(403, headers={"x-ratelimit-remaining": "0", "retry-after": "3"},
                                  json={"message": "API rate limit exceeded"})
        return httpx.Response(200, json={"items": []})

    gh = GitHub(token="x", transport=httpx.MockTransport(handler), sleep=waits.append)
    assert gh.search_issues("x", before="2026-01-01T00:00:00Z", exclude=1) == []
    assert len(calls) == 2 and waits == [3.0]


def test_plain_403_is_not_retried():
    def handler(req):
        return httpx.Response(403, json={"message": "Resource not accessible"})

    gh = GitHub(token="x", transport=httpx.MockTransport(handler), sleep=lambda s: None)
    try:
        gh.search_issues("x", before="2026-01-01T00:00:00Z", exclude=1)
    except httpx.HTTPStatusError as e:
        assert e.response.status_code == 403
    else:
        raise AssertionError("expected HTTPStatusError")


def test_docs_are_mirrored_once_and_searched_locally(tmp_path):
    pages = {
        "concepts/resolution.md": "Universal resolution. Restrict platforms with `environments` in [tool.uv].",
        "guides/tools.md": "Run tools with uvx in an isolated environment.",
    }
    fetched = []

    def handler(req):
        p = req.url.path
        if p.endswith("/git/trees/main"):
            return httpx.Response(200, json={"tree": [{"path": "docs", "type": "tree", "sha": "abc"}]})
        if p.endswith("/commits/main"):
            return httpx.Response(200, json={"sha": "c0ffee"})
        if p.endswith("/git/trees/abc"):
            return httpx.Response(200, json={"tree": [{"path": k, "type": "blob"} for k in pages]})
        if req.url.host == "raw.githubusercontent.com":
            fetched.append(p)
            return httpx.Response(200, text=pages[p.split("/docs/", 1)[1]])
        raise AssertionError(p)

    gh = GitHub(token="x", transport=httpx.MockTransport(handler), docs_cache=tmp_path)
    hits = gh.search_docs("--environments universal")  # leading dashes must not break search
    assert hits[0][0] == "docs/concepts/resolution.md" and "environments" in hits[0][1]
    assert gh.read_doc("docs/guides/tools.md")[0].startswith("Run tools")
    GitHub(token="x", transport=httpx.MockTransport(handler), docs_cache=tmp_path).search_docs("uvx")
    assert len(fetched) == 2  # second client reused the on-disk mirror
    assert json.dumps(hits)  # plain data, safe to log
