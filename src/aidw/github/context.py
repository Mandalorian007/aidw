"""Context assembly for AI workflows."""

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from aidw.github.client import GitHubClient, Issue, PullRequest


@dataclass
class TriggerInfo:
    """Information about the command trigger."""

    author: str
    body: str
    command: str
    instruction: str


@dataclass
class GitState:
    """Git state information."""

    branch: str
    log: str
    diff_stat: str


@dataclass
class WorkflowContext:
    """Full context for a workflow."""

    issue: Issue
    pr: PullRequest | None
    trigger: TriggerInfo
    git_state: GitState | None
    plan_path: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering."""
        return {
            "issue": {
                "number": self.issue.number,
                "title": self.issue.title,
                "body": self.issue.body,
                "author": self.issue.author,
                "state": self.issue.state,
                "url": self.issue.url,
                "comments": [
                    {
                        "author": c.author,
                        "body": c.body,
                        "date": c.created_at.strftime("%Y-%m-%d %H:%M"),
                    }
                    for c in self.issue.comments
                ],
            },
            "pr": (
                {
                    "number": self.pr.number,
                    "title": self.pr.title,
                    "body": self.pr.body,
                    "branch": self.pr.branch,
                    "base_branch": self.pr.base_branch,
                    "comments": [
                        {
                            "author": c.author,
                            "body": c.body,
                            "date": c.created_at.strftime("%Y-%m-%d %H:%M"),
                        }
                        for c in self.pr.comments
                    ],
                }
                if self.pr
                else None
            ),
            "trigger": {
                "author": self.trigger.author,
                "body": self.trigger.body,
                "command": self.trigger.command,
                "instruction": self.trigger.instruction,
            },
            "git_log": self.git_state.log if self.git_state else "",
            "git_diff_stat": self.git_state.diff_stat if self.git_state else "",
            "plan_path": self.plan_path,
        }


class ContextBuilder:
    """Builds workflow context from GitHub data."""

    def __init__(self, github_client: GitHubClient):
        self.github = github_client

    async def build_context(
        self,
        repo: str,
        issue_number: int,
        pr_number: int | None,
        trigger: TriggerInfo,
        git_state: GitState | None = None,
    ) -> WorkflowContext:
        """Build full workflow context."""
        # Get issue
        issue = await self.github.get_issue(repo, issue_number)

        # Get PR if exists
        pr = None
        if pr_number:
            pr = await self.github.get_pull_request(repo, pr_number)

            # If we have a PR but no issue number, try to find linked issue
            if issue_number == pr_number and pr.linked_issue_number:
                issue = await self.github.get_issue(repo, pr.linked_issue_number)

        return WorkflowContext(
            issue=issue,
            pr=pr,
            trigger=trigger,
            git_state=git_state,
        )


class PromptRenderer:
    """Renders prompts from templates."""

    def __init__(self, prompts_dir: Path | None = None):
        if prompts_dir is None:
            # Default to prompts/ inside the aidw package
            prompts_dir = Path(__file__).parent.parent / "prompts"

        self.env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, context: WorkflowContext) -> str:
        """Render a prompt template with context."""
        template = self.env.get_template(template_name)
        return template.render(**context.to_dict())

    def render_context(self, context: WorkflowContext) -> str:
        """Render just the context template."""
        return self.render("context.md", context)
