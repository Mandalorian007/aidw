"""GitHub API client using httpx."""

import logging
from dataclasses import dataclass
from datetime import datetime

import httpx

from aidw.env import get_settings

logger = logging.getLogger(__name__)

API_BASE = "https://api.github.com"
"""Base URL for GitHub REST API v3."""


@dataclass
class Comment:
    """A GitHub comment on an issue or pull request.

    Represents both regular issue/PR comments and inline review comments.
    Review comments include file path context in the body field.
    """

    id: int
    author: str
    body: str
    created_at: datetime
    url: str


@dataclass
class Issue:
    """A GitHub issue with metadata and comments.

    Contains the issue's core metadata along with all comments
    fetched from the GitHub API.
    """

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
    """A GitHub pull request with metadata and comments.

    Contains the PR's core metadata along with both regular comments
    and inline review comments, sorted chronologically. May include
    a linked issue number if the PR body references an issue with
    keywords like "Closes #123" or "Fixes #123".
    """

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


@dataclass
class Webhook:
    """A GitHub repository webhook configuration.

    Represents a webhook registered on a repository, including its
    target URL, active status, and subscribed events.
    """

    id: int
    url: str
    config_url: str
    active: bool
    events: list[str]
    created_at: datetime


@dataclass
class WebhookDelivery:
    """A GitHub webhook delivery record.

    Represents a single delivery attempt of a webhook event,
    including response status and timing information.
    """

    id: int
    delivered_at: datetime
    status_code: int
    event: str
    action: str | None
    redelivery: bool


class GitHubClient:
    """GitHub API client for issues, PRs, comments, and webhooks.

    Uses httpx for async HTTP requests. Must be used as an async context
    manager to properly initialize and cleanup the HTTP client.

    Example:
        async with GitHubClient() as client:
            issue = await client.get_issue("owner/repo", 123)
    """

    def __init__(self, token: str | None = None):
        """Initialize the GitHub client.

        Args:
            token: GitHub personal access token. If not provided,
                uses the token from application settings.
        """
        settings = get_settings()
        self.token = token or settings.gh_token
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "GitHubClient":
        """Initialize the HTTP client with GitHub API headers.

        Configures the client with authentication, API version,
        and appropriate timeout settings.

        Returns:
            The initialized GitHubClient instance
        """
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
        """Close the HTTP client and cleanup resources."""
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the underlying httpx client.

        Returns:
            The configured httpx AsyncClient

        Raises:
            RuntimeError: If accessed outside async context manager
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    async def get_issue(self, repo: str, issue_number: int) -> Issue:
        """Get an issue with all comments.

        Fetches the issue metadata and all associated comments using
        GitHub's paginated comments API.

        Args:
            repo: Repository in "owner/name" format
            issue_number: Issue number

        Returns:
            Issue object with complete metadata and comments

        Raises:
            httpx.HTTPStatusError: If the API request fails
        """
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
        """Get all comments on an issue using pagination.

        Fetches comments in batches of 100 until all pages are retrieved.

        Args:
            repo: Repository in "owner/name" format
            issue_number: Issue number

        Returns:
            List of Comment objects in chronological order
        """
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
        """Get a pull request with all comments.

        Fetches the PR metadata along with both regular comments and inline
        review comments. All comments are combined and sorted chronologically.
        Also attempts to parse linked issue numbers from the PR body.

        Args:
            repo: Repository in "owner/name" format
            pr_number: Pull request number

        Returns:
            PullRequest object with complete metadata and all comments

        Raises:
            httpx.HTTPStatusError: If the API request fails
        """
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
        """Get inline review comments on a pull request using pagination.

        Fetches review comments (inline code comments) in batches of 100
        until all pages are retrieved. Each comment's body is prefixed
        with the file path it references.

        Args:
            repo: Repository in "owner/name" format
            pr_number: Pull request number

        Returns:
            List of Comment objects representing review comments
        """
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
        """Parse linked issue number from PR body.

        Searches for common GitHub linking keywords (closes, fixes, resolves)
        followed by an issue number.

        Args:
            body: The pull request body text

        Returns:
            Issue number if found, None otherwise
        """
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

    async def list_webhooks(self, repo: str) -> list[Webhook]:
        """List all webhooks for a repository."""
        resp = await self.client.get(f"/repos/{repo}/hooks")
        resp.raise_for_status()
        data = resp.json()

        return [
            Webhook(
                id=h["id"],
                url=h["config"].get("url", ""),
                config_url=h["url"],
                active=h["active"],
                events=h["events"],
                created_at=datetime.fromisoformat(h["created_at"].replace("Z", "+00:00")),
            )
            for h in data
        ]

    async def create_webhook(
        self,
        repo: str,
        url: str,
        secret: str,
        events: list[str],
    ) -> Webhook:
        """Create a webhook on a repository."""
        resp = await self.client.post(
            f"/repos/{repo}/hooks",
            json={
                "name": "web",
                "active": True,
                "events": events,
                "config": {
                    "url": url,
                    "content_type": "json",
                    "secret": secret,
                    "insecure_ssl": "0",
                },
            },
        )
        resp.raise_for_status()
        data = resp.json()

        return Webhook(
            id=data["id"],
            url=data["config"].get("url", ""),
            config_url=data["url"],
            active=data["active"],
            events=data["events"],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
        )

    async def delete_webhook(self, repo: str, hook_id: int) -> None:
        """Delete a webhook from a repository."""
        resp = await self.client.delete(f"/repos/{repo}/hooks/{hook_id}")
        resp.raise_for_status()

    async def get_webhook_deliveries(
        self, repo: str, hook_id: int, count: int = 10
    ) -> list[WebhookDelivery]:
        """Get recent deliveries for a webhook."""
        resp = await self.client.get(
            f"/repos/{repo}/hooks/{hook_id}/deliveries",
            params={"per_page": count},
        )
        resp.raise_for_status()
        data = resp.json()

        return [
            WebhookDelivery(
                id=d["id"],
                delivered_at=datetime.fromisoformat(d["delivered_at"].replace("Z", "+00:00")),
                status_code=d.get("status_code", 0),
                event=d["event"],
                action=d.get("action"),
                redelivery=d.get("redelivery", False),
            )
            for d in data
        ]
