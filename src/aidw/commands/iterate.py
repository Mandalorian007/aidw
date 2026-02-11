"""@aidw iterate command - Iterate on implementation based on feedback."""

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


class IterateCommand(BaseCommand):
    """Iterate on implementation based on feedback."""

    command_name = "iterate"
    prompt_template = "iterate.md"

    def get_progress_steps(self) -> list[ProgressStep]:
        """Return the progress steps for the iterate workflow.

        Returns:
            List of four steps: analyze feedback, update implementation,
            update tests, and push changes
        """
        return [
            ProgressStep("Analyze feedback"),
            ProgressStep("Update implementation"),
            ProgressStep("Update tests"),
            ProgressStep("Push changes"),
        ]

    async def run_workflow(
        self,
        session: Session,
        context: WorkflowContext,
        executor: SandboxExecutor,
        progress: ProgressReporter,
        tracker: ProgressTracker,
    ) -> dict[str, Any]:
        """Iterate on the implementation based on user feedback.

        Workflow steps:
        1. Analyze feedback - Renders prompt with user's iteration instructions
           and current PR state
        2. Update implementation - Runs Claude Code to modify code based on feedback
        3. Update tests - Claude Code updates tests to match code changes
        4. Push changes - Commits and pushes updates to existing PR

        This command is for post-build iterations when users request changes
        to an implemented PR.

        Args:
            session: Database session tracking this workflow
            context: Workflow context with PR, issue, and implementation state
            executor: Sandbox executor for running Claude Code
            progress: Progress reporter for posting updates to GitHub
            tracker: Progress tracker for managing step status

        Returns:
            Dictionary with pr_number and pr_url of the updated PR

        Raises:
            RuntimeError: If Claude Code fails
        """
        # Step 1: Analyze feedback
        await self._update_step(tracker, progress, 0, StepStatus.RUNNING)
        start = time.time()

        # Render prompt
        prompt = await self._render_prompt(context)

        await self._update_step(
            tracker, progress, 0, StepStatus.COMPLETED, int(time.time() - start)
        )

        # Steps 2-3: Update implementation and tests (done by Claude Code)
        await self._update_step(tracker, progress, 1, StepStatus.RUNNING)
        start = time.time()

        # Run Claude Code
        result = await executor.run_claude(prompt)

        if not result.success:
            raise RuntimeError(f"Claude Code failed: {result.error}")

        # Mark implementation steps complete
        elapsed = int(time.time() - start)
        await self._update_step(tracker, progress, 1, StepStatus.COMPLETED, elapsed // 2)
        await self._update_step(tracker, progress, 2, StepStatus.COMPLETED, elapsed // 2)

        # Step 4: Push changes
        await self._update_step(tracker, progress, 3, StepStatus.RUNNING)
        start = time.time()

        await self._update_step(
            tracker, progress, 3, StepStatus.COMPLETED, int(time.time() - start)
        )

        return {
            "pr_number": session.pr_number,
            "pr_url": f"https://github.com/{session.repo}/pull/{session.pr_number}",
        }

    async def execute_manual(self, repo: str, pr: int, instruction: str = "") -> None:
        """Execute iterate command manually from CLI or script.

        Args:
            repo: Repository in owner/name format
            pr: PR number containing the implementation to iterate on
            instruction: User feedback to guide the iteration
        """
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
iterate_command = IterateCommand()
