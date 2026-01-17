"""GitHub webhook event handling."""

import re
import logging
from dataclasses import dataclass
from typing import Any

from aidw.env import get_settings
from aidw.server.security import is_user_allowed

logger = logging.getLogger(__name__)

# Command pattern: @aidw <command> [instruction]
COMMAND_PATTERN = re.compile(
    r"@(\w+)\s+(plan|refine|build|oneshot|iterate)(?:\s+(.*))?",
    re.IGNORECASE | re.DOTALL,
)


@dataclass
class ParsedCommand:
    """A parsed command from a GitHub comment."""

    command: str  # plan, refine, build, oneshot, iterate
    instruction: str  # Optional additional text
    author: str  # GitHub username
    body: str  # Full comment body
    repo: str  # owner/repo
    issue_number: int  # Issue number
    pr_number: int | None  # PR number if comment is on a PR
    comment_id: int  # Comment ID for reactions


@dataclass
class WebhookContext:
    """Context extracted from a webhook event."""

    event_type: str
    action: str
    repo: str
    issue_number: int | None
    pr_number: int | None
    comment_body: str | None
    comment_author: str | None
    comment_id: int | None
    is_pr_comment: bool


def parse_webhook_event(event_type: str, payload: dict[str, Any]) -> WebhookContext | None:
    """Parse a webhook event into a context object.

    Returns None if the event is not relevant (not a comment event).
    """
    action = payload.get("action", "")

    # We only care about comment creation
    if action != "created":
        return None

    # Issue comment (on issue or PR)
    if event_type == "issue_comment":
        repo = payload.get("repository", {}).get("full_name", "")
        issue = payload.get("issue", {})
        comment = payload.get("comment", {})

        # Check if this is on a PR (issues with pull_request key)
        is_pr = "pull_request" in issue

        return WebhookContext(
            event_type=event_type,
            action=action,
            repo=repo,
            issue_number=issue.get("number"),
            pr_number=issue.get("number") if is_pr else None,
            comment_body=comment.get("body", ""),
            comment_author=comment.get("user", {}).get("login", ""),
            comment_id=comment.get("id"),
            is_pr_comment=is_pr,
        )

    # PR review comment
    if event_type == "pull_request_review_comment":
        repo = payload.get("repository", {}).get("full_name", "")
        pr = payload.get("pull_request", {})
        comment = payload.get("comment", {})

        return WebhookContext(
            event_type=event_type,
            action=action,
            repo=repo,
            issue_number=None,
            pr_number=pr.get("number"),
            comment_body=comment.get("body", ""),
            comment_author=comment.get("user", {}).get("login", ""),
            comment_id=comment.get("id"),
            is_pr_comment=True,
        )

    return None


def parse_command(context: WebhookContext) -> ParsedCommand | None:
    """Parse a command from a webhook context.

    Returns None if:
    - No command found in comment
    - User not allowed
    - Bot name doesn't match
    """
    if not context.comment_body or not context.comment_author:
        return None

    settings = get_settings()
    bot_name = settings.github.bot_name

    # Check for command pattern
    match = COMMAND_PATTERN.search(context.comment_body)
    if not match:
        return None

    # Check bot name matches
    if match.group(1).lower() != bot_name.lower():
        return None

    # Check user is allowed
    if not is_user_allowed(context.comment_author):
        logger.warning(f"Unauthorized user {context.comment_author} attempted command")
        return None

    command = match.group(2).lower()
    instruction = (match.group(3) or "").strip()

    # Determine issue number - for PR comments, we need to fetch the linked issue
    issue_number = context.issue_number or 0

    return ParsedCommand(
        command=command,
        instruction=instruction,
        author=context.comment_author,
        body=context.comment_body,
        repo=context.repo,
        issue_number=issue_number,
        pr_number=context.pr_number,
        comment_id=context.comment_id or 0,
    )


def validate_command_context(cmd: ParsedCommand) -> str | None:
    """Validate that a command can be run in its context.

    Returns an error message if invalid, None if valid.
    """
    # plan and oneshot require an issue (no PR yet)
    if cmd.command in ("plan", "oneshot"):
        if cmd.pr_number is not None:
            return f"`@aidw {cmd.command}` must be run from an issue, not a PR"

    # refine, build, iterate require a PR
    if cmd.command in ("refine", "build", "iterate"):
        if cmd.pr_number is None:
            return f"`@aidw {cmd.command}` must be run from a PR"

    return None
