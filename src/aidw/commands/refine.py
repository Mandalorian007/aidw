"""@aidw refine command - Iterate on implementation plan."""

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


class RefineCommand(BaseCommand):
    """Refine the implementation plan based on feedback."""

    command_name = "refine"
    prompt_template = "refine.md"

    def get_progress_steps(self) -> list[ProgressStep]:
        return [
            ProgressStep("Analyze feedback"),
            ProgressStep("Update plan"),
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
        """Refine the plan based on feedback."""
        # Compute plan path from issue title
        context.plan_path = self._get_plan_path(context)

        # Step 1: Analyze feedback
        await self._update_step(tracker, progress, 0, StepStatus.RUNNING)
        start = time.time()

        # Render prompt
        prompt = await self._render_prompt(context)

        await self._update_step(
            tracker, progress, 0, StepStatus.COMPLETED, int(time.time() - start)
        )

        # Step 2: Update plan
        await self._update_step(tracker, progress, 1, StepStatus.RUNNING)
        start = time.time()

        # Run Claude Code
        result = await executor.run_claude(prompt)

        if not result.success:
            raise RuntimeError(f"Claude Code failed: {result.error}")

        # Commit changes
        await executor.commit_changes("Refine plan based on feedback")

        await self._update_step(
            tracker, progress, 1, StepStatus.COMPLETED, int(time.time() - start)
        )

        # Step 3: Push changes
        await self._update_step(tracker, progress, 2, StepStatus.RUNNING)
        start = time.time()

        # No PR creation needed - we're updating an existing PR
        await self._update_step(
            tracker, progress, 2, StepStatus.COMPLETED, int(time.time() - start)
        )

        return {
            "pr_number": session.pr_number,
            "pr_url": f"https://github.com/{session.repo}/pull/{session.pr_number}",
        }

    async def execute_manual(self, repo: str, pr: int, instruction: str = "") -> None:
        """Execute refine command manually."""
        # For refine, the PR is the issue
        cmd = ParsedCommand(
            command=self.command_name,
            instruction=instruction,
            author="manual",
            body=f"@aidw {self.command_name} {instruction}".strip(),
            repo=repo,
            issue_number=pr,  # PR number is also issue number
            pr_number=pr,
            comment_id=0,
        )
        await self.execute(cmd)


# Singleton instance
refine_command = RefineCommand()
