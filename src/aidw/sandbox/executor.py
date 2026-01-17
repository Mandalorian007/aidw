"""Execute Claude Code in E2B sandbox."""

import json
import logging
from dataclasses import dataclass
from typing import Callable

from aidw.sandbox.manager import SandboxInstance

logger = logging.getLogger(__name__)

# Claude Code command timeout (30 minutes)
CLAUDE_TIMEOUT = 1800


@dataclass
class ExecutionResult:
    """Result of a Claude Code execution."""

    success: bool
    output: str
    error: str | None = None
    exit_code: int = 0


class SandboxExecutor:
    """Executes Claude Code in a sandbox."""

    def __init__(self, instance: SandboxInstance, claude_token: str = ""):
        self.instance = instance
        self.claude_token = claude_token
        self._claude_installed = False

    async def _ensure_claude_installed(self) -> None:
        """Ensure Claude Code is installed in the sandbox."""
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
        env_prefix = ""
        if self.claude_token:
            env_prefix = f"ANTHROPIC_API_KEY={self.claude_token} "
        command = f'cd {working_dir} && {env_prefix}claude -p "$(cat {prompt_file})" --output-format json'

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
            # E2B raises exceptions for non-zero exit codes
            # Try to extract useful info from the exception
            error_msg = str(e)
            logger.error(f"Claude Code execution error: {error_msg}")
            return ExecutionResult(
                success=False,
                output="",
                error=error_msg,
                exit_code=-1,
            )

    async def run_claude_with_context(
        self,
        context_file: str,
        prompt_file: str,
        working_dir: str | None = None,
    ) -> ExecutionResult:
        """Run Claude Code with context and prompt from files.

        This method reads the prompt from files in the sandbox and passes it to Claude.
        """
        if working_dir is None:
            working_dir = self.instance.repo_path

        # Read prompt file
        prompt_content = self.instance.sandbox.files.read(prompt_file)

        return await self.run_claude(prompt_content, working_dir)

    async def commit_changes(self, message: str) -> ExecutionResult:
        """Stage and commit all changes."""
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
        """Get list of files changed in the repo."""
        result = self.instance.sandbox.commands.run(
            f"cd {self.instance.repo_path} && git diff --name-only HEAD~1 2>/dev/null || git diff --name-only",
            timeout=30,
        )

        if result.exit_code != 0:
            return []

        return [f.strip() for f in result.stdout.split("\n") if f.strip()]

    async def file_exists(self, path: str) -> bool:
        """Check if a file exists in the repo."""
        full_path = f"{self.instance.repo_path}/{path}"
        result = self.instance.sandbox.commands.run(f"test -f {full_path} && echo 'yes'")
        return result.stdout.strip() == "yes"

    async def read_repo_file(self, path: str) -> str | None:
        """Read a file from the repo."""
        full_path = f"{self.instance.repo_path}/{path}"
        try:
            return self.instance.sandbox.files.read(full_path)
        except Exception:
            return None

    async def write_repo_file(self, path: str, content: str) -> None:
        """Write a file to the repo."""
        full_path = f"{self.instance.repo_path}/{path}"
        self.instance.sandbox.files.write(full_path, content)
