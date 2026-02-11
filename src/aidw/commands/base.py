"""Base command class with shared workflow logic."""

import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from aidw.database import Database, Session, SessionStatus
from aidw.env import ensure_config_dir, get_settings
from aidw.github import GitHubClient, ContextBuilder
from aidw.github.context import PromptRenderer, TriggerInfo, GitState, WorkflowContext
from aidw.github.progress import ProgressReporter, ProgressTracker, ProgressStep, StepStatus
from aidw.sandbox import SandboxManager, SandboxExecutor
from aidw.sandbox.manager import SandboxConfig
from aidw.server.webhook import ParsedCommand

logger = logging.getLogger(__name__)


class BaseCommand(ABC):
    """Base class for workflow commands."""

    command_name: str = ""
    prompt_template: str = ""
    should_push: bool = True

    def __init__(self):
        """Initialize the command with empty component references.

        Components (db, github, sandbox_manager) are initialized during execute().
        """
        self.db: Database | None = None
        self.github: GitHubClient | None = None
        self.sandbox_manager: SandboxManager | None = None

    @abstractmethod
    def get_progress_steps(self) -> list[ProgressStep]:
        """Get the progress steps for this command."""
        pass

    @abstractmethod
    async def run_workflow(
        self,
        session: Session,
        context: WorkflowContext,
        executor: SandboxExecutor,
        progress: ProgressReporter,
        tracker: ProgressTracker,
    ) -> dict[str, Any]:
        """Run the command-specific workflow.

        Returns a dict with results (e.g., pr_url, branch).
        """
        pass

    async def execute(self, cmd: ParsedCommand) -> None:
        """Execute the command from a webhook trigger.

        This is the main entry point for all commands. It orchestrates the complete lifecycle:
        1. Initialize database and GitHub client
        2. Create session for tracking
        3. Build context from issue/PR/comments
        4. Create E2B sandbox and clone repo
        5. Run command-specific workflow (subclass implements run_workflow)
        6. Push changes to GitHub (unless should_push=False)
        7. Update progress and post results
        8. Handle errors and cleanup

        Progress is tracked via GitHub comments and reactions are added to the trigger comment.
        Session state is persisted in SQLite for debugging and status checks.

        Args:
            cmd: Parsed command from webhook containing repo, issue, PR, instruction, etc.
        """
        ensure_config_dir()

        # Initialize components
        self.db = Database()
        await self.db.connect()

        try:
            async with GitHubClient() as github:
                self.github = github
                self.sandbox_manager = SandboxManager()

                # Create session
                session = await self.db.create_session(
                    command=self.command_name,
                    repo=cmd.repo,
                    issue_number=cmd.issue_number,
                    pr_number=cmd.pr_number,
                    triggered_by=cmd.author,
                    instruction=cmd.instruction,
                )

                # Add reaction to indicate we received the command
                if cmd.comment_id:
                    await github.add_reaction(cmd.repo, cmd.comment_id, "eyes")

                # Set up progress tracking
                tracker = ProgressTracker(
                    command=self.command_name,
                    session_id=session.id,
                    steps=self.get_progress_steps(),
                )

                progress = ProgressReporter(
                    github=github,
                    repo=cmd.repo,
                    issue_number=cmd.pr_number or cmd.issue_number,
                )

                await progress.start(tracker)
                await self.db.update_session(session.id, status=SessionStatus.RUNNING)

                try:
                    # Build trigger info
                    trigger = TriggerInfo(
                        author=cmd.author,
                        body=cmd.body,
                        command=self.command_name,
                        instruction=cmd.instruction,
                    )

                    # Build context
                    context_builder = ContextBuilder(github)
                    context = await context_builder.build_context(
                        repo=cmd.repo,
                        issue_number=cmd.issue_number,
                        pr_number=cmd.pr_number,
                        trigger=trigger,
                    )

                    # Compute plan path from issue context
                    context.plan_path = self._get_plan_path(context)
                    logger.debug(f"Plan path for issue #{context.issue.number}: {context.plan_path}")

                    # Determine branch name
                    branch = self._get_branch_name(cmd, context)

                    # Create sandbox
                    sandbox_config = SandboxConfig(
                        repo_url=f"https://github.com/{cmd.repo}.git",
                        branch=branch if cmd.pr_number else None,
                        claude_auth_path=Path.home(),
                    )

                    instance = await self.sandbox_manager.create_sandbox(sandbox_config)
                    await self.db.update_session(
                        session.id,
                        sandbox_id=instance.sandbox_id,
                        branch=branch,
                    )
                    # Update in-memory session object
                    session.sandbox_id = instance.sandbox_id
                    session.branch = branch

                    try:
                        # Create new branch if needed (for plan/oneshot)
                        if not cmd.pr_number:
                            from aidw.sandbox import git as sandbox_git

                            await sandbox_git.create_branch(instance, branch)

                        # Get git state
                        git_state_dict = await self.sandbox_manager.get_git_state(instance)
                        context.git_state = GitState(
                            branch=git_state_dict["branch"],
                            log=git_state_dict["log"],
                            diff_stat=git_state_dict["diff_stat"],
                        )

                        # Create executor with Claude token
                        settings = get_settings()
                        executor = SandboxExecutor(instance, claude_token=settings.claude_token)

                        # Run command-specific workflow
                        result = await self.run_workflow(
                            session, context, executor, progress, tracker
                        )

                        # Push changes
                        if self.should_push:
                            await self.sandbox_manager.push_changes(instance, branch)

                        # Mark complete
                        await self.db.update_session(
                            session.id,
                            status=SessionStatus.COMPLETED,
                            pr_number=result.get("pr_number"),
                        )

                        await progress.complete(result.get("pr_url"))

                        # Add success reaction
                        if cmd.comment_id:
                            await github.add_reaction(cmd.repo, cmd.comment_id, "rocket")

                    finally:
                        await self.sandbox_manager.kill_sandbox(instance)

                except Exception as e:
                    logger.exception(f"Workflow failed: {e}")
                    await self.db.update_session(
                        session.id,
                        status=SessionStatus.FAILED,
                        error=str(e),
                    )
                    await progress.fail(str(e))

                    # Add failure reaction
                    if cmd.comment_id:
                        await github.add_reaction(cmd.repo, cmd.comment_id, "confused")

        finally:
            await self.db.close()

    async def execute_manual(self, repo: str, issue_or_pr: int, instruction: str = "") -> None:
        """Execute the command manually from CLI (aidw run <command>).

        Creates a synthetic ParsedCommand and delegates to execute(). Used for testing
        and manual triggers outside of webhook flow.

        Args:
            repo: Repository in "owner/repo" format
            issue_or_pr: Issue or PR number
            instruction: Optional instruction text (e.g., "make it blue")
        """
        # Create a fake ParsedCommand
        cmd = ParsedCommand(
            command=self.command_name,
            instruction=instruction,
            author="manual",
            body=f"@aidw {self.command_name} {instruction}".strip(),
            repo=repo,
            issue_number=issue_or_pr,
            pr_number=None,  # Will be set by subclass if needed
            comment_id=0,
        )

        await self.execute(cmd)

    @staticmethod
    def _slugify_title(title: str) -> str:
        """Convert a title to a filename-safe slug.

        Lowercase, hyphens for spaces/special chars, collapse runs, strip, truncate to 60 chars.

        Examples:
            "Add user authentication" -> "add-user-authentication"
            "Fix bug in parser (urgent!)" -> "fix-bug-in-parser-urgent"
            "Support UTF-8 文字" -> "support-utf-8"

        Args:
            title: The issue title or text to slugify

        Returns:
            URL-safe slug (max 60 chars), or "plan" if empty after processing
        """
        slug = title.lower()
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        slug = slug[:60].rstrip("-")
        return slug or "plan"

    @staticmethod
    def _get_plan_path(context: WorkflowContext) -> str:
        """Compute the plan file path from the issue title.

        Uses the issue number as a prefix for guaranteed uniqueness, followed by
        a slugified version of the issue title for readability.

        Examples:
            Issue #13 "Clean up documentation" -> "docs/plans/13-clean-up-documentation.md"
            Issue #42 "Add OAuth support" -> "docs/plans/42-add-oauth-support.md"

        Args:
            context: Workflow context containing issue information

        Returns:
            Path to plan file in docs/plans/{number}-{slug}.md format
        """
        slug = BaseCommand._slugify_title(context.issue.title)
        return f"docs/plans/{context.issue.number}-{slug}.md"

    def _get_branch_name(self, cmd: ParsedCommand, context: WorkflowContext) -> str:
        """Get the branch name for this command.

        For PR-based commands (refine, build, iterate), uses the existing PR branch.
        For issue-based commands (plan, oneshot), creates new branch aidw/issue-{number}.

        Args:
            cmd: Parsed command containing PR number if applicable
            context: Workflow context with PR info if available

        Returns:
            Branch name to use for this workflow
        """
        if cmd.pr_number and context.pr:
            return context.pr.branch

        return f"aidw/issue-{cmd.issue_number}"

    async def _render_prompt(self, context: WorkflowContext) -> str:
        """Render the prompt template with context.

        Uses Jinja2 to render the command-specific prompt template (e.g., plan.md, build.md)
        with the full workflow context (issue, PR, comments, git state, etc.).

        Args:
            context: Complete workflow context for template rendering

        Returns:
            Rendered prompt text ready to pass to Claude Code
        """
        renderer = PromptRenderer()
        return renderer.render(self.prompt_template, context)

    async def _update_step(
        self,
        tracker: ProgressTracker,
        progress: ProgressReporter,
        step_index: int,
        status: StepStatus,
        duration: int | None = None,
    ) -> None:
        """Update a step's status and refresh progress comment on GitHub.

        Args:
            tracker: Progress tracker holding all steps
            progress: Progress reporter for posting updates
            step_index: Index of step to update (0-based)
            status: New status (running, completed, failed)
            duration: Optional duration in seconds if step completed
        """
        tracker.steps[step_index].status = status
        if duration is not None:
            tracker.steps[step_index].duration_seconds = duration
        await progress.update()
