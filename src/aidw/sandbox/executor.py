"""Execute Claude Code in E2B sandbox."""

import json
import logging
from dataclasses import dataclass
from typing import Callable

from aidw.sandbox.manager import SandboxInstance

logger = logging.getLogger(__name__)

# Claude Code command timeout in seconds (30 minutes).
# This extended timeout accommodates long-running AI-assisted development tasks
# that may involve multiple file edits, tests, and complex reasoning.
CLAUDE_TIMEOUT = 1800


@dataclass
class ExecutionResult:
    """Result of a Claude Code execution.

    Captures the outcome of running Claude Code in the sandbox, including
    success status, output, errors, and exit code for diagnostic purposes.

    Attributes:
        success: Whether the execution completed successfully
        output: Standard output from the command
        error: Error message if execution failed, None otherwise
        exit_code: Process exit code (0 for success)
    """

    success: bool
    output: str
    error: str | None = None
    exit_code: int = 0


class SandboxExecutor:
    """Executes Claude Code in a sandbox."""

    def __init__(self, instance: SandboxInstance, claude_token: str = ""):
        """Initialize the executor for a sandbox instance.

        Args:
            instance: The sandbox instance to execute commands in
            claude_token: OAuth token for Claude Code authentication (optional)
        """
        self.instance = instance
        self.claude_token = claude_token
        self._claude_installed = False

    async def _ensure_claude_installed(self) -> None:
        """Ensure Claude Code is installed in the sandbox.

        Checks if Claude Code CLI is available, and if not, installs it globally
        via npm. Uses a cached flag to avoid redundant installation checks.

        The installation uses sudo to install globally at /usr/local/bin/claude,
        which is necessary for the sandboxed environment.

        Raises:
            RuntimeError: If installation fails
        """
        if self._claude_installed:
            return

        # Check if claude is already available
        try:
            check = self.instance.sandbox.commands.run(
                "which claude",
                timeout=30,
            )
            if check.exit_code == 0:
                self._claude_installed = True
                logger.info("Claude Code already installed")
                return
        except Exception:
            # which returns non-zero when not found, which may raise
            pass

        # Install Claude Code via npm
        logger.info("Installing Claude Code in sandbox...")
        try:
            result = self.instance.sandbox.commands.run(
                "sudo npm install -g @anthropic-ai/claude-code",
                timeout=300,
            )
            if result.exit_code != 0:
                raise RuntimeError(f"Failed to install Claude Code: {result.stderr}")
        except Exception as e:
            raise RuntimeError(f"Failed to install Claude Code: {e}")

        self._claude_installed = True
        logger.info("Claude Code installed successfully")

    async def run_claude(
        self,
        prompt: str,
        working_dir: str | None = None,
        on_output: Callable[[str], None] | None = None,
    ) -> ExecutionResult:
        """Run Claude Code with the given prompt.

        Args:
            prompt: The prompt to send to Claude Code
            working_dir: Working directory (defaults to repo path)
            on_output: Optional callback for streaming output

        Returns:
            ExecutionResult with success status and output
        """
        if working_dir is None:
            working_dir = self.instance.repo_path

        # Ensure Claude Code is installed
        await self._ensure_claude_installed()

        # Write prompt to a file to avoid shell escaping issues
        prompt_file = "/tmp/claude_prompt.txt"
        self.instance.sandbox.files.write(prompt_file, prompt)

        # Build the command - read prompt from file
        # Set auth token via environment variable if available
        # Use CLAUDE_CODE_OAUTH_TOKEN for subscription auth (from `claude setup-token`)
        # Use --dangerously-skip-permissions since we're in an isolated sandbox
        env_prefix = ""
        if self.claude_token:
            env_prefix = f"CLAUDE_CODE_OAUTH_TOKEN={self.claude_token} "
        command = f'cd {working_dir} && {env_prefix}claude -p "$(cat {prompt_file})" --output-format json --dangerously-skip-permissions'

        logger.info("Running Claude Code in sandbox")
        logger.debug(f"Prompt length: {len(prompt)} chars")

        try:
            # Run with extended timeout
            result = self.instance.sandbox.commands.run(
                command,
                timeout=CLAUDE_TIMEOUT,
            )

            output = result.stdout or ""
            error = result.stderr or ""

            if on_output and output:
                on_output(output)

            if result.exit_code != 0:
                logger.error(f"Claude Code failed with exit code {result.exit_code}")
                logger.error(f"Stdout: {output}")
                logger.error(f"Stderr: {error}")
                return ExecutionResult(
                    success=False,
                    output=output,
                    error=error or output or f"Exit code: {result.exit_code}",
                    exit_code=result.exit_code,
                )

            logger.info("Claude Code execution completed successfully")
            return ExecutionResult(
                success=True,
                output=output,
                exit_code=0,
            )

        except Exception as e:
            # E2B raises CommandExitException for non-zero exit codes
            # Extract stdout/stderr from the exception if available
            error_msg = str(e)
            stdout = getattr(e, 'stdout', '') or ''
            stderr = getattr(e, 'stderr', '') or ''
            exit_code = getattr(e, 'exit_code', -1)

            logger.error(f"Claude Code execution error: {error_msg}")
            logger.error(f"Exit code: {exit_code}")
            logger.error(f"Stdout: {stdout}")
            logger.error(f"Stderr: {stderr}")

            # Combine all available error info
            full_error = stderr or stdout or error_msg
            return ExecutionResult(
                success=False,
                output=stdout,
                error=full_error,
                exit_code=exit_code,
            )

    async def run_claude_with_context(
        self,
        context_file: str,
        prompt_file: str,
        working_dir: str | None = None,
    ) -> ExecutionResult:
        """Run Claude Code with context and prompt from files.

        Reads the prompt from a file in the sandbox and passes it to Claude Code.
        The context_file parameter is provided for compatibility with the workflow
        but is not currently used directly - context is typically embedded in the
        prompt_file content itself.

        This method is useful when prompts are pre-written to the sandbox filesystem
        as part of the workflow setup, avoiding the need to pass large prompt strings
        through method parameters.

        Args:
            context_file: Path to context file in sandbox (reserved for future use)
            prompt_file: Path to prompt file in sandbox to read and execute
            working_dir: Working directory for Claude Code (defaults to repo path)

        Returns:
            ExecutionResult with success status and output
        """
        if working_dir is None:
            working_dir = self.instance.repo_path

        # Read prompt file
        prompt_content = self.instance.sandbox.files.read(prompt_file)

        return await self.run_claude(prompt_content, working_dir)

    async def commit_changes(self, message: str) -> ExecutionResult:
        """Stage and commit all changes in the repository.

        Performs a three-step commit process:
        1. Stage all changes (tracked and untracked) with 'git add -A'
        2. Check if there are actually changes to commit
        3. Create the commit if changes exist

        This method handles the common case where there might be no changes
        (returning success without creating an empty commit) and properly
        escapes the commit message to avoid shell injection issues.

        Args:
            message: Commit message (will be escaped for shell safety)

        Returns:
            ExecutionResult indicating success/failure of the commit operation.
            Returns success=True with "No changes to commit" message if the
            working tree is clean.

        Note:
            Uses 'git add -A' which stages all changes including deletions,
            unlike 'git add .' which doesn't stage deletions in some git versions.
        """
        logger.info(f"Committing changes: {message}")

        # Stage all changes
        stage_result = self.instance.sandbox.commands.run(
            f"cd {self.instance.repo_path} && git add -A",
            timeout=60,
        )

        if stage_result.exit_code != 0:
            return ExecutionResult(
                success=False,
                output=stage_result.stdout or "",
                error=f"Failed to stage changes: {stage_result.stderr}",
                exit_code=stage_result.exit_code,
            )

        # Check if there are changes to commit
        status_result = self.instance.sandbox.commands.run(
            f"cd {self.instance.repo_path} && git status --porcelain",
            timeout=30,
        )

        if not status_result.stdout.strip():
            logger.info("No changes to commit")
            return ExecutionResult(
                success=True,
                output="No changes to commit",
                exit_code=0,
            )

        # Commit
        escaped_message = message.replace('"', '\\"')
        commit_result = self.instance.sandbox.commands.run(
            f'cd {self.instance.repo_path} && git commit -m "{escaped_message}"',
            timeout=60,
        )

        if commit_result.exit_code != 0:
            return ExecutionResult(
                success=False,
                output=commit_result.stdout or "",
                error=f"Failed to commit: {commit_result.stderr}",
                exit_code=commit_result.exit_code,
            )

        return ExecutionResult(
            success=True,
            output=commit_result.stdout or "",
            exit_code=0,
        )

    async def get_changed_files(self) -> list[str]:
        """Get list of files changed in the repository.

        Attempts to get files changed in the last commit (HEAD~1..HEAD).
        Falls back to showing all uncommitted changes if HEAD~1 doesn't exist
        (e.g., in a new repository with only one commit).

        Returns:
            List of file paths relative to repository root. Returns empty list
            if git command fails or no changes exist.
        """
        result = self.instance.sandbox.commands.run(
            f"cd {self.instance.repo_path} && git diff --name-only HEAD~1 2>/dev/null || git diff --name-only",
            timeout=30,
        )

        if result.exit_code != 0:
            return []

        return [f.strip() for f in result.stdout.split("\n") if f.strip()]

    async def file_exists(self, path: str) -> bool:
        """Check if a file exists in the repository.

        Uses 'test -f' to check for regular files only (not directories).

        Args:
            path: Relative path from repository root

        Returns:
            True if the file exists, False otherwise (including on errors)
        """
        full_path = f"{self.instance.repo_path}/{path}"
        try:
            result = self.instance.sandbox.commands.run(f"test -f {full_path} && echo 'yes'")
            return result.stdout.strip() == "yes"
        except Exception:
            return False

    async def read_repo_file(self, path: str) -> str | None:
        """Read a file from the repository.

        Args:
            path: Relative path from repository root

        Returns:
            File contents as string, or None if file doesn't exist or can't be read
        """
        full_path = f"{self.instance.repo_path}/{path}"
        try:
            return self.instance.sandbox.files.read(full_path)
        except Exception:
            return None

    async def write_repo_file(self, path: str, content: str) -> None:
        """Write a file to the repository.

        Creates or overwrites the file at the specified path. Parent directories
        are created automatically if they don't exist.

        Args:
            path: Relative path from repository root
            content: File contents to write

        Raises:
            Exception: If the file cannot be written (e.g., permission denied)
        """
        full_path = f"{self.instance.repo_path}/{path}"
        self.instance.sandbox.files.write(full_path, content)
