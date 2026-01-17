"""GitHub API client using httpx."""

import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

from aidw.env import get_settings

logger = logging.getLogger(__name__)

API_BASE = "https://api.github.com"


@dataclass
class Comment:
    """A GitHub comment."""

    id: int
    author: str
    body: str
    created_at: datetime
    url: str


@dataclass
class Issue:
    """A GitHub issue."""

    number: int
    title: str
    body: str
    author: str
    state: str
    created_at: datetime
    url: str
    comments: list[Comment]


@dataclass
class PullRequest:
    """A GitHub pull request."""

    number: int
    title: str
    body: str
    author: str
    state: str
    branch: str
    base_branch: str
    created_at: datetime
    url: str
    comments: list[Comment]
    linked_issue_number: int | None


class GitHubClient:
    """GitHub API client."""

    def __init__(self, token: str | None = None):
        settings = get_settings()
        self.token = token or settings.gh_token
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "GitHubClient":
        self._client = httpx.AsyncClient(
            base_url=API_BASE,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    async def get_issue(self, repo: str, issue_number: int) -> Issue:
        """Get an issue with all comments."""
        # Get issue
        resp = await self.client.get(f"/repos/{repo}/issues/{issue_number}")
        resp.raise_for_status()
        data = resp.json()

        # Get comments
        comments = await self._get_issue_comments(repo, issue_number)

        return Issue(
            number=data["number"],
            title=data["title"],
            body=data.get("body") or "",
            author=data["user"]["login"],
            state=data["state"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            url=data["html_url"],
            comments=comments,
        )

    async def _get_issue_comments(self, repo: str, issue_number: int) -> list[Comment]:
        """Get all comments on an issue."""
        comments = []
        page = 1
        per_page = 100

        while True:
            resp = await self.client.get(
                f"/repos/{repo}/issues/{issue_number}/comments",
                params={"page": page, "per_page": per_page},
            )
            resp.raise_for_status()
            data = resp.json()

            if not data:
                break

            for c in data:
                comments.append(
                    Comment(
                        id=c["id"],
                        author=c["user"]["login"],
                        body=c.get("body") or "",
                        created_at=datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")),
                        url=c["html_url"],
                    )
                )

            if len(data) < per_page:
                break
            page += 1

        return comments

    async def get_pull_request(self, repo: str, pr_number: int) -> PullRequest:
        """Get a pull request with all comments."""
        # Get PR
        resp = await self.client.get(f"/repos/{repo}/pulls/{pr_number}")
        resp.raise_for_status()
        data = resp.json()

        # Get issue comments (regular comments on PR)
        comments = await self._get_issue_comments(repo, pr_number)

        # Get review comments (inline comments)
        review_comments = await self._get_review_comments(repo, pr_number)
        comments.extend(review_comments)

        # Sort by date
        comments.sort(key=lambda c: c.created_at)

        # Try to find linked issue from body
        linked_issue = self._parse_linked_issue(data.get("body") or "")

        return PullRequest(
            number=data["number"],
            title=data["title"],
            body=data.get("body") or "",
            author=data["user"]["login"],
            state=data["state"],
            branch=data["head"]["ref"],
            base_branch=data["base"]["ref"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            url=data["html_url"],
            comments=comments,
            linked_issue_number=linked_issue,
        )

    async def _get_review_comments(self, repo: str, pr_number: int) -> list[Comment]:
        """Get review comments on a PR."""
        comments = []
        page = 1
        per_page = 100

        while True:
            resp = await self.client.get(
                f"/repos/{repo}/pulls/{pr_number}/comments",
                params={"page": page, "per_page": per_page},
            )
            resp.raise_for_status()
            data = resp.json()

            if not data:
                break

            for c in data:
                comments.append(
                    Comment(
                        id=c["id"],
                        author=c["user"]["login"],
                        body=f"[Review comment on {c.get('path', 'file')}]\n{c.get('body', '')}",
                        created_at=datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")),
                        url=c["html_url"],
                    )
                )

            if len(data) < per_page:
                break
            page += 1

        return comments

    def _parse_linked_issue(self, body: str) -> int | None:
        """Parse linked issue number from PR body."""
        import re

        # Common patterns: Closes #123, Fixes #123, Resolves #123
        patterns = [
            r"(?:closes?|fixes?|resolves?)\s*#(\d+)",
            r"(?:closes?|fixes?|resolves?)\s+.*?#(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return None

    async def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str,
        draft: bool = True,
    ) -> PullRequest:
        """Create a new pull request."""
        resp = await self.client.post(
            f"/repos/{repo}/pulls",
            json={
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": draft,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        return PullRequest(
            number=data["number"],
            title=data["title"],
            body=data.get("body") or "",
            author=data["user"]["login"],
            state=data["state"],
            branch=data["head"]["ref"],
            base_branch=data["base"]["ref"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            url=data["html_url"],
            comments=[],
            linked_issue_number=None,
        )

    async def update_pull_request(
        self,
        repo: str,
        pr_number: int,
        title: str | None = None,
        body: str | None = None,
    ) -> None:
        """Update a pull request."""
        data = {}
        if title is not None:
            data["title"] = title
        if body is not None:
            data["body"] = body

        if data:
            resp = await self.client.patch(f"/repos/{repo}/pulls/{pr_number}", json=data)
            resp.raise_for_status()

    async def create_comment(self, repo: str, issue_number: int, body: str) -> Comment:
        """Create a comment on an issue or PR."""
        resp = await self.client.post(
            f"/repos/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )
        resp.raise_for_status()
        data = resp.json()

        return Comment(
            id=data["id"],
            author=data["user"]["login"],
            body=data.get("body") or "",
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            url=data["html_url"],
        )

    async def update_comment(self, repo: str, comment_id: int, body: str) -> None:
        """Update a comment."""
        resp = await self.client.patch(
            f"/repos/{repo}/issues/comments/{comment_id}",
            json={"body": body},
        )
        resp.raise_for_status()

    async def add_reaction(self, repo: str, comment_id: int, reaction: str) -> None:
        """Add a reaction to a comment.

        reaction: +1, -1, laugh, confused, heart, hooray, rocket, eyes
        """
        resp = await self.client.post(
            f"/repos/{repo}/issues/comments/{comment_id}/reactions",
            json={"content": reaction},
        )
        # 201 = created, 200 = already exists
        if resp.status_code not in (200, 201):
            resp.raise_for_status()

    async def get_default_branch(self, repo: str) -> str:
        """Get the default branch of a repository."""
        resp = await self.client.get(f"/repos/{repo}")
        resp.raise_for_status()
        return resp.json()["default_branch"]
