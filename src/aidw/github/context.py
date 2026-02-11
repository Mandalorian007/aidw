"""Context assembly for AI workflows."""

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from aidw.github.client import GitHubClient, Issue, PullRequest


@dataclass
class TriggerInfo:
    """Information about the command trigger.

    Captures who triggered the command, what they said, and what they want.
    This is extracted from GitHub issue/PR comments and used to provide
    context to the AI agent about the user's intent.

    Attributes:
        author: GitHub username who triggered the command
        body: Full text of the triggering comment
        command: The command name (plan, refine, build, etc.)
        instruction: Additional instruction text provided with the command
    """

    author: str
    body: str
    command: str
    instruction: str


@dataclass
class GitState:
    """Git state information from the repository.

    Provides a snapshot of the current git state including branch,
    commit history, and diff statistics. This is passed to the AI
    agent to inform decision-making about what changes to make.

    Attributes:
        branch: Current branch name
        log: Recent commit history (git log output)
        diff_stat: Statistics of changes since base branch (git diff --stat)
    """

    branch: str
    log: str
    diff_stat: str


@dataclass
class WorkflowContext:
    """Full context for a workflow execution.

    Aggregates all information needed for an AI workflow: the GitHub issue,
    optional PR, trigger information, git state, and plan file path. This
    context is converted to a dictionary for template rendering.

    Attributes:
        issue: The GitHub issue driving this workflow
        pr: The GitHub PR if this workflow is running on a PR
        trigger: Information about the command trigger
        git_state: Current git state (branch, log, diff)
        plan_path: Path to the plan file (e.g., "docs/plans/13-slug.md")
    """

    issue: Issue
    pr: PullRequest | None
    trigger: TriggerInfo
    git_state: GitState | None
    plan_path: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for template rendering.

        Transforms all context data into a flat dictionary suitable for Jinja2
        template rendering. Issue and PR comments are formatted with dates,
        and git state is included if available.

        Returns:
            Dictionary with keys: issue, pr, trigger, git_log, git_diff_stat, plan_path
        """
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
    """Builds workflow context from GitHub data.

    Fetches issue and PR information from GitHub and assembles it into
    a WorkflowContext suitable for AI processing. Handles linked issues
    and comment fetching automatically.
    """

    def __init__(self, github_client: GitHubClient):
        """Initialize the context builder.

        Args:
            github_client: GitHub API client for fetching data
        """
        self.github = github_client

    async def build_context(
        self,
        repo: str,
        issue_number: int,
        pr_number: int | None,
        trigger: TriggerInfo,
        git_state: GitState | None = None,
    ) -> WorkflowContext:
        """Build full workflow context from GitHub data.

        Fetches issue and PR information, handles linked issues (when a PR
        references an issue), and assembles everything into a WorkflowContext.
        This is the main entry point for context assembly.

        Args:
            repo: Repository in "owner/name" format
            issue_number: Issue number to fetch
            pr_number: PR number if this workflow is on a PR
            trigger: Information about the command trigger
            git_state: Optional git state from sandbox

        Returns:
            Complete workflow context ready for template rendering
        """
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
    """Renders prompts from Jinja2 templates.

    Uses the template files in src/aidw/prompts/ to generate prompts
    for the AI agent. Supports template inheritance and includes.
    """

    def __init__(self, prompts_dir: Path | None = None):
        """Initialize the prompt renderer.

        Args:
            prompts_dir: Directory containing prompt templates. Defaults to
                        src/aidw/prompts/ if not specified.
        """
        if prompts_dir is None:
            # Default to prompts/ inside the aidw package
            prompts_dir = Path(__file__).parent.parent / "prompts"

        self.env = Environment(
            loader=FileSystemLoader(str(prompts_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_name: str, context: WorkflowContext) -> str:
        """Render a prompt template with context.

        Args:
            template_name: Name of template file (e.g., "plan.md", "build.md")
            context: Workflow context containing all data for rendering

        Returns:
            Rendered prompt text ready to pass to the AI agent
        """
        template = self.env.get_template(template_name)
        return template.render(**context.to_dict())

    def render_context(self, context: WorkflowContext) -> str:
        """Render just the context template.

        The context template (context.md) is included by other templates
        to provide common context about the issue, PR, and trigger.

        Args:
            context: Workflow context to render

        Returns:
            Rendered context section
        """
        return self.render("context.md", context)
