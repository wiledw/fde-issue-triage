"""Read-only access to the GitHub and PyPI data the agent may see.

The central rule: **the agent only sees what a maintainer could have seen at
triage time.** For a historical issue that means the *original* title and first
post (before any later edits), and the label the reporter's template applied.
Never the comments, never the maintainers' labels. Otherwise evals on past
issues would leak the answer.
"""

import os
import re
import subprocess
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import httpx

REPO = "astral-sh/uv"
MAX_BODY_CHARS = 30_000
MAX_DOC_CHARS = 20_000
DOCS_CACHE = Path(os.environ.get("TRIAGE_CACHE", Path.home() / ".cache" / "fde-triage")) / "docs"
MAX_RETRIES = 4
MAX_WAIT_S = 60


@dataclass
class IssueSnapshot:
    number: int
    title: str
    body: str
    reporter: str
    created_at: str  # ISO-8601, e.g. "2026-09-14T08:12:55Z"
    reporter_labels: list[str]
    body_truncated_chars: int = 0  # >0 means we cut the body; the agent is told so
    edited_after_posting: bool = False  # title or body was changed later; we show the original


@dataclass
class SearchHit:
    number: int
    title: str
    state: str
    state_reason: str | None
    labels: list[str]
    created_at: str
    body_excerpt: str = field(repr=False)


def _gh_cli_token() -> str | None:
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() or None


def _retry_wait(r: httpx.Response, attempt: int) -> float | None:
    """Seconds to wait before retrying, or None if the response should not be retried."""
    if r.status_code in (500, 502, 503, 504):
        return min(2**attempt, MAX_WAIT_S)
    rate_limited = r.status_code == 429 or (
        r.status_code == 403 and (r.headers.get("x-ratelimit-remaining") == "0" or "rate limit" in r.text.lower())
    )
    if not rate_limited:
        return None
    if "retry-after" in r.headers:
        return min(float(r.headers["retry-after"]), MAX_WAIT_S)
    if "x-ratelimit-reset" in r.headers:
        return min(max(float(r.headers["x-ratelimit-reset"]) - time.time(), 1), MAX_WAIT_S)
    return min(2**attempt * 5, MAX_WAIT_S)


class GitHub:
    def __init__(
        self,
        token: str | None = None,
        transport: httpx.BaseTransport | None = None,
        docs_cache: Path = DOCS_CACHE,
        sleep=time.sleep,
    ):
        token = token or os.environ.get("GITHUB_TOKEN") or _gh_cli_token()
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.http = httpx.Client(base_url="https://api.github.com", headers=headers, timeout=20, transport=transport)
        self.pypi = httpx.Client(base_url="https://pypi.org", timeout=20, transport=transport)
        self.raw = httpx.Client(base_url="https://raw.githubusercontent.com", timeout=20, transport=transport)
        self.docs_cache = docs_cache
        self._sleep = sleep
        self._docs: dict[str, str] | None = None

    def _request(self, client: httpx.Client, method: str, url: str, **kw) -> httpx.Response:
        """Send with retry on rate limits and 5xx. Raises httpx.HTTPStatusError when retries run out."""
        for attempt in range(MAX_RETRIES + 1):
            r = client.request(method, url, **kw)
            wait = _retry_wait(r, attempt) if r.status_code >= 400 else None
            if wait is None or attempt == MAX_RETRIES:
                r.raise_for_status()
                return r
            self._sleep(wait)
        raise AssertionError("unreachable")

    def _get(self, path: str, **params) -> dict | list:
        return self._request(self.http, "GET", path, params=params or None).json()

    def _graphql(self, query: str, **variables) -> dict:
        data = self._request(self.http, "POST", "/graphql", json={"query": query, "variables": variables}).json()
        if data.get("errors"):
            raise httpx.HTTPError(f"GraphQL error: {data['errors'][0].get('message')}")
        return data["data"]

    def _original_body(self, number: int) -> str | None:
        """The first saved revision of the issue body, or None if it was never edited."""
        owner, name = REPO.split("/")
        q = (
            "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){issue(number:$i)"
            "{userContentEdits(last:100){nodes{editedAt diff}}}}}"
        )
        nodes = self._graphql(q, o=owner, n=name, i=number)["repository"]["issue"]["userContentEdits"]["nodes"]
        revisions = [nd for nd in nodes if nd.get("diff") is not None]
        if not revisions:
            return None
        return min(revisions, key=lambda nd: nd["editedAt"])["diff"]

    def issue_snapshot(self, number: int) -> IssueSnapshot:
        issue = self._get(f"/repos/{REPO}/issues/{number}")
        if "pull_request" in issue:
            raise ValueError(f"#{number} is a pull request, not an issue")
        reporter = issue["user"]["login"]
        events = self._get(f"/repos/{REPO}/issues/{number}/timeline", per_page=100)
        # Template labels are applied as the reporter at creation time.
        # Anything a maintainer added later is the answer, so it is excluded.
        reporter_labels = sorted(
            {
                e["label"]["name"]
                for e in events
                if e.get("event") == "labeled" and (e.get("actor") or {}).get("login") == reporter
            }
        )
        # Undo later edits: reporters often retitle or rewrite once they find the cause.
        renames = [e for e in events if e.get("event") == "renamed"]
        title = renames[0]["rename"]["from"] if renames else issue["title"]
        original = self._original_body(number)
        body = original if original is not None else (issue.get("body") or "")
        cut = max(0, len(body) - MAX_BODY_CHARS)
        return IssueSnapshot(
            number=number,
            title=title,
            body=body[:MAX_BODY_CHARS],
            reporter=reporter,
            created_at=issue["created_at"],
            reporter_labels=reporter_labels,
            body_truncated_chars=cut,
            edited_after_posting=bool(renames) or original is not None,
        )

    def search_issues(self, query: str, *, before: str, exclude: int, limit: int = 8) -> list[SearchHit]:
        # `created:<before` stops the agent from "finding" issues filed after the
        # one it is triaging. Known leak: labels/state of those older issues are
        # their *current* values, not their values at triage time.
        q = f"repo:{REPO} is:issue {query} created:<{before}"
        data = self._get("/search/issues", q=q, per_page=limit + 1)
        hits = []
        for it in data.get("items", []):
            if it["number"] == exclude:
                continue
            hits.append(
                SearchHit(
                    number=it["number"],
                    title=it["title"],
                    state=it["state"],
                    state_reason=it.get("state_reason"),
                    labels=[lbl["name"] for lbl in it.get("labels", [])],
                    created_at=it["created_at"],
                    body_excerpt=(it.get("body") or "")[:400],
                )
            )
        return hits[:limit]

    # --- docs: a local copy of docs/*.md, searched offline -----------------
    # GitHub code search is rate-limited (~10/min) and mangles hyphenated terms,
    # so we mirror the docs once and search them locally. Docs are the current
    # default branch, so they may describe features newer than the issue
    # (accepted, documented leak).

    def _load_docs(self) -> dict[str, str]:
        if self._docs is not None:
            return self._docs
        main = self._get(f"/repos/{REPO}/git/trees/main")
        docs_tree = next(t for t in main["tree"] if t["path"] == "docs" and t["type"] == "tree")
        cache = self.docs_cache / docs_tree["sha"]
        if not (cache / ".complete").exists():
            commit = self._get(f"/repos/{REPO}/commits/main")["sha"]
            tree = self._get(f"/repos/{REPO}/git/trees/{docs_tree['sha']}", recursive=1)
            for t in tree["tree"]:
                if t["type"] != "blob" or not t["path"].endswith(".md"):
                    continue
                text = self._request(self.raw, "GET", f"/{REPO}/{commit}/docs/{t['path']}").text
                dest = cache / "docs" / t["path"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(".tmp")
                tmp.write_text(text)
                tmp.replace(dest)  # atomic, so parallel runs never read a half-written file
            (cache / ".complete").touch()
        self._docs = {
            str(p.relative_to(cache)): p.read_text() for p in sorted((cache / "docs").rglob("*.md"))
        }
        return self._docs

    def search_docs(self, query: str, limit: int = 8) -> list[tuple[str, str]]:
        """Rank docs pages by how often the query terms occur. Returns (path, snippet) pairs."""
        terms = [t.lstrip("-").lower() for t in query.split() if t.lstrip("-")]
        if not terms:
            return []
        scored = []
        for path, text in self._load_docs().items():
            low = text.lower()
            counts = Counter({t: low.count(t) for t in terms})
            matched = sum(1 for t in terms if counts[t])
            if not matched:
                continue
            # pages matching more distinct terms win; frequency breaks ties; path hits count extra
            score = matched * 100 + sum(min(c, 20) for c in counts.values()) + 30 * sum(t in path for t in terms)
            first = min((low.find(t) for t in terms if counts[t]), default=0)
            snippet = re.sub(r"\s+", " ", text[max(0, first - 80) : first + 160]).strip()
            scored.append((score, path, snippet))
        scored.sort(key=lambda s: (-s[0], s[1]))
        return [(p, snip) for _, p, snip in scored[:limit]]

    def read_doc(self, path: str) -> tuple[str, int]:
        if not path.startswith("docs/") or not path.endswith(".md") or ".." in path:
            raise ValueError("path must be a .md file under docs/")
        docs = self._load_docs()
        if path not in docs:
            raise ValueError(f"{path} does not exist; use a path returned by search_uv_docs")
        text = docs[path]
        cut = max(0, len(text) - MAX_DOC_CHARS)
        return text[:MAX_DOC_CHARS], cut

    def package_metadata(self, name: str, version: str | None = None) -> dict:
        path = f"/pypi/{name}/{version}/json" if version else f"/pypi/{name}/json"
        info = self._request(self.pypi, "GET", path).json()["info"]
        return {
            "name": info["name"],
            "version": info["version"],
            "requires_python": info.get("requires_python"),
            "requires_dist": info.get("requires_dist") or [],
        }
