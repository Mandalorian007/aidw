"""Progress comment formatting and updates."""

from dataclasses import dataclass, field
from enum import Enum

from aidw.github.client import GitHubClient


class StepStatus(Enum):
    """Status of a progress step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressStep:
    """A step in the progress tracker."""

    name: str
    status: StepStatus = StepStatus.PENDING
    duration_seconds: int | None = None


@dataclass
class ProgressTracker:
    """Tracks and formats progress updates."""

    command: str
    session_id: str
    steps: list[ProgressStep] = field(default_factory=list)
    error_message: str | None = None

    def format(self) -> str:
        """Format the progress as a GitHub comment."""
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
        """Format the progress as completed."""
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
        """Format the progress as failed."""
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
    """Reports progress to GitHub comments."""

    def __init__(self, github: GitHubClient, repo: str, issue_number: int):
        self.github = github
        self.repo = repo
        self.issue_number = issue_number
        self.comment_id: int | None = None
        self.tracker: ProgressTracker | None = None

    async def start(self, tracker: ProgressTracker) -> None:
        """Start progress reporting by creating a comment."""
        self.tracker = tracker
        comment = await self.github.create_comment(
            self.repo,
            self.issue_number,
            tracker.format(),
        )
        self.comment_id = comment.id

    async def update(self) -> None:
        """Update the progress comment."""
        if not self.comment_id or not self.tracker:
            return

        await self.github.update_comment(
            self.repo,
            self.comment_id,
            self.tracker.format(),
        )

    async def complete(self, pr_url: str | None = None) -> None:
        """Mark progress as completed."""
        if not self.comment_id or not self.tracker:
            return

        await self.github.update_comment(
            self.repo,
            self.comment_id,
            self.tracker.format_completed(pr_url),
        )

    async def fail(self, error: str) -> None:
        """Mark progress as failed."""
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
