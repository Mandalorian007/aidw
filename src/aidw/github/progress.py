"""Progress comment formatting and updates."""

from dataclasses import dataclass, field
from enum import Enum

from aidw.github.client import GitHubClient


class StepStatus(Enum):
    """Status of a progress step.

    Tracks the lifecycle of individual workflow steps as they execute.
    Used to display real-time progress in GitHub comments.

    Values:
        PENDING: Step has not started yet
        RUNNING: Step is currently executing
        COMPLETED: Step finished successfully
        FAILED: Step encountered an error
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressStep:
    """A step in the progress tracker.

    Represents a single step in a workflow with its status and timing.
    Steps are displayed in GitHub comments as checkboxes.

    Attributes:
        name: Human-readable step name (e.g., "Creating sandbox")
        status: Current status of this step
        duration_seconds: How long this step took to complete (if finished)
    """

    name: str
    status: StepStatus = StepStatus.PENDING
    duration_seconds: int | None = None


@dataclass
class ProgressTracker:
    """Tracks and formats progress updates for GitHub comments.

    Maintains a list of steps and their statuses, and provides methods
    to format them as markdown for posting to GitHub. The formatted
    output includes checkboxes, durations, and status indicators.

    Attributes:
        command: The command being executed (plan, build, etc.)
        session_id: Unique session identifier for this workflow run
        steps: List of progress steps with their statuses
        error_message: Error message if workflow failed
    """

    command: str
    session_id: str
    steps: list[ProgressStep] = field(default_factory=list)
    error_message: str | None = None

    def format(self) -> str:
        """Format the progress as a GitHub comment for in-progress workflows.

        Shows which steps are completed, which is running, and which are pending.
        Includes timing information for completed steps.

        Returns:
            Markdown-formatted progress comment
        """
        lines = [f"🤖 **{self.command}** running", ""]

        for step in self.steps:
            if step.status == StepStatus.COMPLETED:
                duration = f" ({step.duration_seconds}s)" if step.duration_seconds else ""
                lines.append(f"- [x] {step.name}{duration}")
            elif step.status == StepStatus.RUNNING:
                lines.append(f"- [ ] {step.name} ← running")
            elif step.status == StepStatus.FAILED:
                lines.append(f"- [ ] {step.name} ← failed")
            else:
                lines.append(f"- [ ] {step.name}")

        lines.append("")
        lines.append(f"_Session: {self.session_id}_")

        if self.error_message:
            lines.append("")
            lines.append(f"❌ **Error:** {self.error_message}")

        return "\n".join(lines)

    def format_completed(self, pr_url: str | None = None) -> str:
        """Format the progress as completed successfully.

        Shows all steps as completed with checkmarks and includes a link
        to the PR if provided.

        Args:
            pr_url: Optional URL to the created/updated PR

        Returns:
            Markdown-formatted success comment
        """
        lines = [f"✅ **{self.command}** completed", ""]

        for step in self.steps:
            duration = f" ({step.duration_seconds}s)" if step.duration_seconds else ""
            if step.status == StepStatus.FAILED:
                lines.append(f"- [ ] {step.name} ← failed")
            else:
                lines.append(f"- [x] {step.name}{duration}")

        if pr_url:
            lines.append("")
            lines.append(f"🔗 [View PR]({pr_url})")

        lines.append("")
        lines.append(f"_Session: {self.session_id}_")

        return "\n".join(lines)

    def format_failed(self) -> str:
        """Format the progress as failed.

        Shows which steps completed successfully and which step failed.
        Includes the error message in a code block for debugging.

        Returns:
            Markdown-formatted failure comment
        """
        lines = [f"❌ **{self.command}** failed", ""]

        for step in self.steps:
            duration = f" ({step.duration_seconds}s)" if step.duration_seconds else ""
            if step.status == StepStatus.COMPLETED:
                lines.append(f"- [x] {step.name}{duration}")
            elif step.status == StepStatus.RUNNING or step.status == StepStatus.FAILED:
                lines.append(f"- [ ] {step.name} ← failed")
            else:
                lines.append(f"- [ ] {step.name}")

        lines.append("")
        lines.append(f"_Session: {self.session_id}_")

        if self.error_message:
            lines.append("")
            lines.append(f"```\n{self.error_message}\n```")

        return "\n".join(lines)


class ProgressReporter:
    """Reports progress to GitHub comments.

    Creates and updates a single GitHub comment to show real-time progress
    of a workflow. The comment is created on first update and then edited
    as the workflow progresses.
    """

    def __init__(self, github: GitHubClient, repo: str, issue_number: int):
        """Initialize the progress reporter.

        Args:
            github: GitHub API client for posting comments
            repo: Repository in "owner/name" format
            issue_number: Issue or PR number to comment on
        """
        self.github = github
        self.repo = repo
        self.issue_number = issue_number
        self.comment_id: int | None = None
        self.tracker: ProgressTracker | None = None

    async def start(self, tracker: ProgressTracker) -> None:
        """Start progress reporting by creating a comment.

        Creates the initial progress comment on GitHub and stores its ID
        for future updates.

        Args:
            tracker: Progress tracker with initial steps
        """
        self.tracker = tracker
        comment = await self.github.create_comment(
            self.repo,
            self.issue_number,
            tracker.format(),
        )
        self.comment_id = comment.id

    async def update(self) -> None:
        """Update the progress comment with current status.

        Edits the existing GitHub comment to show updated progress.
        Does nothing if the comment hasn't been created yet.
        """
        if not self.comment_id or not self.tracker:
            return

        await self.github.update_comment(
            self.repo,
            self.comment_id,
            self.tracker.format(),
        )

    async def complete(self, pr_url: str | None = None) -> None:
        """Mark progress as completed successfully.

        Updates the comment with success formatting, showing all steps
        completed and optionally linking to the PR.

        Args:
            pr_url: Optional URL to the created/updated PR
        """
        if not self.comment_id or not self.tracker:
            return

        await self.github.update_comment(
            self.repo,
            self.comment_id,
            self.tracker.format_completed(pr_url),
        )

    async def fail(self, error: str) -> None:
        """Mark progress as failed with error details.

        Updates the comment with failure formatting, showing which step
        failed and including the error message for debugging.

        Args:
            error: Error message to display
        """
        if not self.tracker:
            return

        self.tracker.error_message = error

        if self.comment_id:
            await self.github.update_comment(
                self.repo,
                self.comment_id,
                self.tracker.format_failed(),
            )
        else:
            # Create comment if we haven't yet
            await self.github.create_comment(
                self.repo,
                self.issue_number,
                self.tracker.format_failed(),
            )
