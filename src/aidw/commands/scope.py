"""aidw scope command - Autonomous scoping workflow."""

import logging
from pathlib import Path

import click
from e2b_code_interpreter import Sandbox

from aidw.env import get_settings

logger = logging.getLogger(__name__)

# Sandbox timeout in seconds (1 hour)
SANDBOX_TIMEOUT = 3600

# Claude Code command timeout (30 minutes)
CLAUDE_TIMEOUT = 1800


class ScopeCommand:
    """Autonomous scoping workflow."""

    command_name = "scope"
    prompt_template = "scope.md"

    def _load_prompt(self, context: str = "") -> str:
        """Load and render the scope prompt template.

        Args:
            context: Optional additional context to append to the prompt

        Returns:
            The rendered prompt string with context appended if provided
        """
        prompt_path = Path(__file__).parent.parent / "prompts" / self.prompt_template
        prompt = prompt_path.read_text()

        if context:
            prompt = f"{prompt}\n\n## Additional Context\n\n{context}"

        return prompt

    async def execute(self, context: str = "") -> dict:
        """Run autonomous scoping.

        Args:
            context: Optional context to guide the scoping focus

        Returns:
            dict with summary of what was scoped
        """
        settings = get_settings()

        click.echo("Creating sandbox...")
        sandbox = Sandbox.create(api_key=settings.e2b_api_key, timeout=SANDBOX_TIMEOUT)

        try:
            # Install aitk for Notion access
            click.echo("Installing tools...")
            await self._install_tools(sandbox)

            # Sync aitk config for env store support
            await self._sync_aitk_config(sandbox)

            # Sync Claude auth
            await self._sync_claude_auth(sandbox)

            # Configure GitHub CLI
            await self._setup_github_auth(sandbox, settings.gh_token)

            # Install Claude Code
            click.echo("Installing Claude Code...")
            result = sandbox.commands.run(
                "sudo npm install -g @anthropic-ai/claude-code",
                timeout=300,
            )
            if result.exit_code != 0:
                raise RuntimeError(f"Failed to install Claude Code: {result.stderr}")

            # Load and render prompt
            prompt = self._load_prompt(context)

            # Write prompt to file to avoid shell escaping issues
            prompt_file = "/tmp/claude_prompt.txt"
            sandbox.files.write(prompt_file, prompt)

            # Build command with auth
            env_vars = []
            if settings.claude_token:
                env_vars.append(f"CLAUDE_CODE_OAUTH_TOKEN={settings.claude_token}")
            if settings.gh_token:
                env_vars.append(f"GH_TOKEN={settings.gh_token}")

            env_prefix = " ".join(env_vars) + " " if env_vars else ""
            command = f'{env_prefix}claude -p "$(cat {prompt_file})" --output-format json --dangerously-skip-permissions'

            click.echo("Running autonomous scoping workflow...")
            click.echo("(This may take several minutes)")

            # Run Claude Code
            result = sandbox.commands.run(command, timeout=CLAUDE_TIMEOUT)

            if result.exit_code != 0:
                click.secho(f"Scoping failed: {result.stderr or result.stdout}", fg="red")
                return {"success": False, "error": result.stderr or result.stdout}

            click.secho("Scoping completed successfully!", fg="green")
            click.echo(result.stdout)

            return {"success": True, "output": result.stdout}

        finally:
            click.echo("Cleaning up sandbox...")
            sandbox.kill()

    async def _install_tools(self, sandbox: Sandbox) -> None:
        """Install aitk (AI Toolkit) for Notion access in the sandbox.

        Prefers uv if available for faster installation, falls back to pip.

        Args:
            sandbox: E2B sandbox instance to install tools in
        """
        # Check if uv is available (preferred), otherwise fall back to pip
        try:
            uv_check = sandbox.commands.run("which uv", timeout=10)
            use_uv = uv_check.exit_code == 0
        except Exception:
            use_uv = False

        if use_uv:
            result = sandbox.commands.run(
                "uv tool install git+https://github.com/Mandalorian007/aitk",
                timeout=120,
            )
        else:
            result = sandbox.commands.run(
                "pip install git+https://github.com/Mandalorian007/aitk",
                timeout=120,
            )

        if result.exit_code != 0:
            logger.warning(f"Failed to install aitk: {result.stderr}")
        else:
            logger.info(f"aitk installed successfully via {'uv' if use_uv else 'pip'}")

    async def _sync_aitk_config(self, sandbox: Sandbox) -> None:
        """Sync aitk configuration to sandbox for env store access.

        Copies ~/.config/aitk/config from the local machine to the sandbox,
        enabling Claude Code to access Notion credentials via the env store.

        Args:
            sandbox: E2B sandbox instance to sync config to
        """
        aitk_config = Path.home() / ".config/aitk/config"
        if not aitk_config.exists():
            logger.debug("No aitk config found, skipping env store setup")
            return

        try:
            content = aitk_config.read_text()
            sandbox.commands.run("mkdir -p /home/user/.config/aitk")
            sandbox.files.write("/home/user/.config/aitk/config", content)
            sandbox.commands.run("chmod 600 /home/user/.config/aitk/config")
            logger.info("aitk config synced to sandbox")
        except Exception as e:
            logger.warning(f"Failed to sync aitk config: {e}")

    async def _sync_claude_auth(self, sandbox: Sandbox) -> None:
        """Sync Claude authentication files to sandbox.

        Copies ~/.claude/credentials.json and ~/.claude/settings.json from
        the local machine to the sandbox for Claude Code authentication.

        Args:
            sandbox: E2B sandbox instance to sync auth to
        """
        claude_dir = Path.home() / ".claude"
        if not claude_dir.exists():
            logger.warning("No Claude auth directory found, skipping auth sync")
            return

        sandbox.commands.run("mkdir -p /home/user/.claude")

        for file_name in ["credentials.json", "settings.json"]:
            local_file = claude_dir / file_name
            if local_file.exists():
                content = local_file.read_text()
                sandbox.files.write(f"/home/user/.claude/{file_name}", content)
                logger.debug(f"Synced {file_name} to sandbox")

    async def _setup_github_auth(self, sandbox: Sandbox, gh_token: str) -> None:
        """Install and configure GitHub CLI in sandbox.

        Installs gh CLI from official apt repository and verifies authentication
        works with the provided token.

        Args:
            sandbox: E2B sandbox instance to setup GitHub CLI in
            gh_token: GitHub personal access token for authentication
        """
        if not gh_token:
            logger.warning("No GH_TOKEN configured, skipping GitHub auth")
            return

        # Install gh CLI
        logger.info("Installing GitHub CLI...")
        install_result = sandbox.commands.run(
            "(type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)) && "
            "sudo mkdir -p -m 755 /etc/apt/keyrings && "
            "wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null && "
            "sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg && "
            'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null && '
            "sudo apt update && sudo apt install gh -y",
            timeout=120,
        )
        if install_result.exit_code != 0:
            logger.warning(f"Failed to install gh CLI: {install_result.stderr}")
            return

        # Verify gh is available and auth works
        result = sandbox.commands.run(
            f"GH_TOKEN={gh_token} gh auth status",
            timeout=30,
        )
        if result.exit_code == 0:
            logger.info("GitHub CLI authenticated successfully")
        else:
            logger.warning(f"GitHub CLI auth check failed: {result.stderr}")


# Singleton instance
scope_command = ScopeCommand()
