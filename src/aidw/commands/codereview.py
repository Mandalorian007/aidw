"""@aidw codereview command - Analyze a PR and post a review comment."""

import logging
import time
from typing import Any

from aidw.commands.base import BaseCommand
from aidw.database import Session
from aidw.github.context import WorkflowContext
from aidw.github.progress import ProgressReporter, ProgressStep, ProgressTracker, StepStatus
from aidw.sandbox import SandboxExecutor
from aidw.server.webhook import ParsedCommand

logger = logging.getLogger(__name__)

REVIEW_FILE = "AIDW_REVIEW.md"


class CodeReviewCommand(BaseCommand):
    """Analyze a PR and post a structured review comment."""

    command_name = "codereview"
    prompt_template = "codereview.md"
    should_push = False

    def get_progress_steps(self) -> list[ProgressStep]:
        return [
            ProgressStep("Analyze PR"),
            ProgressStep("Run code review"),
            ProgressStep("Post review"),
        ]

    async def run_workflow(
        self,
        session: Session,
        context: WorkflowContext,
        executor: SandboxExecutor,
        progress: ProgressReporter,
        tracker: ProgressTracker,
    ) -> dict[str, Any]:
        """Run the code review workflow."""
        # Step 1: Analyze PR
        await self._update_step(tracker, progress, 0, StepStatus.RUNNING)
        start = time.time()

        prompt = await self._render_prompt(context)

        await self._update_step(
            tracker, progress, 0, StepStatus.COMPLETED, int(time.time() - start)
        )

        # Step 2: Run code review via Claude Code
        await self._update_step(tracker, progress, 1, StepStatus.RUNNING)
        start = time.time()

        result = await executor.run_claude(prompt)

        if not result.success:
            raise RuntimeError(f"Claude Code failed: {result.error}")

        await self._update_step(
            tracker, progress, 1, StepStatus.COMPLETED, int(time.time() - start)
        )

        # Step 3: Post review comment
        await self._update_step(tracker, progress, 2, StepStatus.RUNNING)
        start = time.time()

        # Read the review file from the sandbox
        review_content = await self.sandbox_manager.read_file(
            executor.instance, f"/home/user/repo/{REVIEW_FILE}"
        )

        if not review_content:
            raise RuntimeError(f"Review file {REVIEW_FILE} not found in sandbox")

        # Post as a comment on the PR
        comment_body = f"## AIDW Code Review\n\n{review_content}"
        await self.github.create_comment(
            session.repo,
            session.pr_number,
            comment_body,
        )

        await self._update_step(
            tracker, progress, 2, StepStatus.COMPLETED, int(time.time() - start)
        )

        return {}

    async def execute_manual(self, repo: str, pr: int, instruction: str = "") -> None:
        """Execute codereview command manually."""
        cmd = ParsedCommand(
            command=self.command_name,
            instruction=instruction,
            author="manual",
            body=f"@aidw {self.command_name} {instruction}".strip(),
            repo=repo,
            issue_number=pr,
            pr_number=pr,
            comment_id=0,
        )
        await self.execute(cmd)


# Singleton instance
codereview_command = CodeReviewCommand()
