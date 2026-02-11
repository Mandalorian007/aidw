"""E2B sandbox management."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from e2b_code_interpreter import Sandbox

from aidw.env import get_settings

logger = logging.getLogger(__name__)

# Sandbox timeout in seconds (1 hour). E2B sandboxes auto-terminate after inactivity.
SANDBOX_TIMEOUT = 3600


@dataclass
class SandboxConfig:
    """Configuration for creating and initializing a sandbox.

    Attributes:
        repo_url: Git repository URL (e.g., https://github.com/owner/repo.git)
        branch: Optional branch to checkout after cloning
        gh_token: Optional GitHub token for authentication (falls back to env)
        claude_auth_path: Path to local .claude directory for auth sync
    """

    repo_url: str
    branch: str | None = None
    gh_token: str | None = None
    claude_auth_path: Path | None = None


@dataclass
class SandboxInstance:
    """A running sandbox instance with initialized repository.

    Attributes:
        sandbox: E2B sandbox object for command execution and file operations
        sandbox_id: Unique ID for reconnecting to this sandbox
        repo_path: Path to cloned repository in sandbox
        context_path: Path where context.md is written
        prompt_path: Path where prompt.md is written
    """

    sandbox: Sandbox
    sandbox_id: str
    repo_path: str = "/home/user/repo"
    context_path: str = "/home/user/context.md"
    prompt_path: str = "/home/user/prompt.md"


class SandboxManager:
    """Manages E2B sandboxes for workflow execution."""

    def __init__(self):
        """Initialize sandbox manager with E2B and GitHub credentials from settings."""
        settings = get_settings()
        self.api_key = settings.e2b_api_key
        self.gh_token = settings.gh_token

    async def create_sandbox(self, config: SandboxConfig) -> SandboxInstance:
        """Create and initialize a new sandbox with full repository setup.

        Orchestrates the complete sandbox initialization lifecycle:
        1. Creates E2B sandbox with configured timeout
        2. Installs development tools (aitk)
        3. Syncs Claude authentication for Code subscription
        4. Clones repository with GitHub token authentication
        5. Checks out specified branch if provided
        6. Pulls encrypted .env files from aitk env store

        If any step fails, the sandbox is killed and the exception is re-raised.

        Args:
            config: Sandbox configuration with repo URL, branch, and auth info

        Returns:
            Initialized sandbox instance ready for workflow execution

        Raises:
            RuntimeError: If repository clone or branch checkout fails
        """
        logger.info(f"Creating sandbox for {config.repo_url}")

        # Create sandbox
        sandbox = Sandbox.create(api_key=self.api_key, timeout=SANDBOX_TIMEOUT)
        sandbox_id = sandbox.sandbox_id

        logger.info(f"Sandbox created: {sandbox_id}")

        instance = SandboxInstance(
            sandbox=sandbox,
            sandbox_id=sandbox_id,
        )

        try:
            # Install tools (aitk, etc.)
            await self._install_tools(instance)

            # Sync Claude auth
            if config.claude_auth_path:
                await self._sync_claude_auth(instance, config.claude_auth_path)

            # Clone repository
            await self._clone_repo(instance, config)

            # Checkout branch if specified
            if config.branch:
                await self._checkout_branch(instance, config.branch)

            return instance

        except Exception as e:
            logger.error(f"Failed to initialize sandbox: {e}")
            await self.kill_sandbox(instance)
            raise

    async def _install_tools(self, instance: SandboxInstance) -> None:
        """Install development tools (aitk) in the sandbox.

        Prefers uv if available, falls back to pip. Also syncs aitk config
        for env store access.
        """
        logger.info("Installing tools in sandbox...")

        # Check if uv is available (preferred), otherwise fall back to pip
        try:
            instance.sandbox.commands.run("which uv", timeout=10)
            use_uv = True
        except Exception:
            use_uv = False

        pkg = "uv" if use_uv else "pip"
        cmd = (
            "uv tool install git+https://github.com/Mandalorian007/aitk"
            if use_uv
            else "pip install git+https://github.com/Mandalorian007/aitk"
        )
        try:
            instance.sandbox.commands.run(cmd, timeout=120)
            logger.info(f"aitk installed successfully via {pkg}")
        except Exception as e:
            logger.warning(f"Failed to install aitk via {pkg}: {e}")

        # Sync aitk config for env store support
        await self._sync_aitk_config(instance)

    async def _sync_aitk_config(self, instance: SandboxInstance) -> None:
        """Sync aitk configuration to sandbox for env store access.

        Copies ~/.config/aitk/config from host to sandbox with secure permissions.
        Enables automatic decryption of .env files from env store.
        """
        aitk_config = Path.home() / ".config/aitk/config"
        if not aitk_config.exists():
            logger.debug("No aitk config found, skipping env store setup")
            return

        try:
            content = aitk_config.read_text()
            # Create config directory in sandbox
            instance.sandbox.commands.run("mkdir -p /home/user/.config/aitk")
            instance.sandbox.files.write("/home/user/.config/aitk/config", content)
            # Secure permissions
            instance.sandbox.commands.run("chmod 600 /home/user/.config/aitk/config")
            logger.info("aitk config synced to sandbox")
        except Exception as e:
            logger.warning(f"Failed to sync aitk config: {e}")

    async def _sync_claude_auth(self, instance: SandboxInstance, auth_path: Path) -> None:
        """Sync Claude authentication files to sandbox.

        Copies credentials.json and settings.json from ~/.claude to sandbox,
        enabling Claude Code subscription auth to work in the sandbox environment.

        Args:
            instance: Sandbox instance to sync auth to
            auth_path: Path to directory containing .claude folder (usually home dir)
        """
        logger.info("Syncing Claude authentication to sandbox")

        # Read local auth files
        claude_dir = auth_path / ".claude"
        if not claude_dir.exists():
            logger.warning("No Claude auth directory found, skipping auth sync")
            return

        # Create .claude directory in sandbox
        instance.sandbox.commands.run("mkdir -p /home/user/.claude")

        # Copy auth files
        for file_name in ["credentials.json", "settings.json"]:
            local_file = claude_dir / file_name
            if local_file.exists():
                content = local_file.read_text()
                instance.sandbox.files.write(f"/home/user/.claude/{file_name}", content)
                logger.debug(f"Synced {file_name} to sandbox")

    async def _clone_repo(self, instance: SandboxInstance, config: SandboxConfig) -> None:
        """Clone repository into sandbox with authentication.

        Injects GitHub token into clone URL for private repos, configures git
        user, and pulls encrypted .env files from aitk env store if configured.

        Args:
            instance: Sandbox instance to clone into
            config: Config with repo URL and optional token

        Raises:
            RuntimeError: If git clone fails
        """
        logger.info(f"Cloning {config.repo_url}")

        # Build clone URL with token if available
        token = config.gh_token or self.gh_token
        if token and "github.com" in config.repo_url:
            # Insert token into URL
            clone_url = config.repo_url.replace(
                "https://github.com",
                f"https://{token}@github.com",
            )
        else:
            clone_url = config.repo_url

        result = instance.sandbox.commands.run(
            f"git clone {clone_url} {instance.repo_path}",
            timeout=300,
        )

        if result.exit_code != 0:
            raise RuntimeError(f"Failed to clone repository: {result.stderr}")

        # Configure git
        instance.sandbox.commands.run(
            f'cd {instance.repo_path} && git config user.email "aidw@users.noreply.github.com"'
        )
        instance.sandbox.commands.run(
            f'cd {instance.repo_path} && git config user.name "AIDW Bot"'
        )

        # Pull env files from env store if configured
        await self._pull_env_files(instance, config.repo_url)

    async def _pull_env_files(self, instance: SandboxInstance, repo_url: str) -> None:
        """Pull encrypted .env files from env store using aitk."""
        # Extract owner/repo from URL (e.g., https://github.com/owner/repo.git)
        import re

        match = re.search(r"github\.com[/:]([^/]+)/([^/.]+)", repo_url)
        if not match:
            logger.debug(f"Could not extract owner/repo from {repo_url}")
            return

        owner_repo = f"{match.group(1)}/{match.group(2)}"
        logger.info(f"Attempting to pull env files for {owner_repo}")

        try:
            result = instance.sandbox.commands.run(
                f"cd {instance.repo_path} && aitk env pull {owner_repo}",
                timeout=60,
            )
            logger.info(f"Pulled env files for {owner_repo}")
        except Exception as e:
            # Not an error - repo might not have env files in store
            logger.debug(f"No env files pulled for {owner_repo}: {e}")

    async def _checkout_branch(self, instance: SandboxInstance, branch: str) -> None:
        """Checkout existing branch or create new one.

        Attempts checkout first, creates new branch if it doesn't exist.

        Args:
            instance: Sandbox instance with cloned repo
            branch: Branch name to checkout/create

        Raises:
            RuntimeError: If checkout and branch creation both fail
        """
        logger.info(f"Checking out branch: {branch}")

        # Try to checkout existing branch
        result = instance.sandbox.commands.run(
            f"cd {instance.repo_path} && git checkout {branch}",
            timeout=60,
        )

        if result.exit_code != 0:
            # Create new branch
            result = instance.sandbox.commands.run(
                f"cd {instance.repo_path} && git checkout -b {branch}",
                timeout=60,
            )

            if result.exit_code != 0:
                raise RuntimeError(f"Failed to checkout/create branch: {result.stderr}")

    async def write_context(self, instance: SandboxInstance, context: str) -> None:
        """Write context file to sandbox at /home/user/context.md."""
        instance.sandbox.files.write(instance.context_path, context)

    async def write_prompt(self, instance: SandboxInstance, prompt: str) -> None:
        """Write prompt file to sandbox at /home/user/prompt.md."""
        instance.sandbox.files.write(instance.prompt_path, prompt)

    async def get_git_state(self, instance: SandboxInstance) -> dict:
        """Get git state from sandbox repository.

        Returns:
            Dict with 'log' (last 10 commits), 'diff_stat' (changes from HEAD~1),
            and 'branch' (current branch name)
        """
        log_result = instance.sandbox.commands.run(
            f"cd {instance.repo_path} && git log --oneline -10",
            timeout=30,
        )

        diff_result = instance.sandbox.commands.run(
            f"cd {instance.repo_path} && git diff --stat HEAD~1 2>/dev/null || echo 'No previous commit'",
            timeout=30,
        )

        branch_result = instance.sandbox.commands.run(
            f"cd {instance.repo_path} && git branch --show-current",
            timeout=30,
        )

        return {
            "log": log_result.stdout,
            "diff_stat": diff_result.stdout,
            "branch": branch_result.stdout.strip(),
        }

    async def push_changes(
        self,
        instance: SandboxInstance,
        branch: str,
        force: bool = False,
    ) -> None:
        """Push changes to remote repository.

        Args:
            instance: Sandbox with committed changes
            branch: Branch name to push
            force: Whether to force push (use with caution)

        Raises:
            RuntimeError: If git push fails
        """
        logger.info(f"Pushing changes to {branch}")

        force_flag = "--force" if force else ""
        result = instance.sandbox.commands.run(
            f"cd {instance.repo_path} && git push -u origin {branch} {force_flag}",
            timeout=120,
        )

        if result.exit_code != 0:
            raise RuntimeError(f"Failed to push changes: {result.stderr}")

    async def read_file(self, instance: SandboxInstance, path: str) -> str | None:
        """Read a file from the sandbox.

        Args:
            instance: Sandbox instance
            path: Absolute path to file in sandbox

        Returns:
            File contents as string, or None if file doesn't exist
        """
        try:
            return instance.sandbox.files.read(path)
        except Exception:
            return None

    async def kill_sandbox(self, instance: SandboxInstance) -> None:
        """Terminate sandbox and release resources.

        Errors during shutdown are logged but not raised.
        """
        logger.info(f"Killing sandbox: {instance.sandbox_id}")
        try:
            instance.sandbox.kill()
        except Exception as e:
            logger.warning(f"Error killing sandbox: {e}")

    async def reconnect(self, sandbox_id: str) -> SandboxInstance | None:
        """Reconnect to an existing sandbox by ID.

        Useful for resuming workflows or debugging. Returns None if reconnection fails.

        Args:
            sandbox_id: E2B sandbox ID to reconnect to

        Returns:
            Sandbox instance if successful, None otherwise
        """
        try:
            sandbox = Sandbox.connect(sandbox_id, api_key=self.api_key)
            return SandboxInstance(
                sandbox=sandbox,
                sandbox_id=sandbox_id,
            )
        except Exception as e:
            logger.warning(f"Failed to reconnect to sandbox {sandbox_id}: {e}")
            return None
