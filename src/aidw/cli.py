"""AIDW CLI - Command line interface."""

import asyncio
import sys
from typing import Any

import click

from aidw import __version__
from aidw.env import (
    get_settings,
    get_credential,
    load_credentials_file,
    validate_required_credentials,
    create_default_config,
    ensure_config_dir,
    CONFIG_DIR,
    CREDENTIALS_FILE,
    CONFIG_FILE,
)


@click.group()
@click.version_option(version=__version__, prog_name="aidw")
def cli() -> None:
    """AIDW - AI Dev Workflow

    Trigger AI workflows from GitHub issue/PR comments.
    """
    pass


@cli.command()
@click.option("--set", "set_credential", help="Set a single credential (KEY=VALUE)")
def config(set_credential: str | None) -> None:
    """Configure API credentials and settings.

    Prompts for each credential and saves to ~/.config/aidw/credentials.
    Press Enter to keep existing values. Credentials are stored with 600 permissions.

    \b
    Credentials:
      AIDW_WEBHOOK_SECRET  GitHub webhook signature secret
      E2B_API_KEY          E2B sandbox API key
      GH_TOKEN             GitHub PAT with repo scope
      CLAUDE_CODE_TOKEN    Long-lived Claude token (run: claude setup-token)

    \b
    Set a single credential:
      aidw config --set CLAUDE_CODE_TOKEN=<token>

    \b
    Also configures allowed GitHub usernames in ~/.config/aidw/config.yml
    """
    import yaml

    ensure_config_dir()

    # Handle --set option for single credential
    if set_credential:
        if "=" not in set_credential:
            click.secho("Error: Use format KEY=VALUE", fg="red")
            sys.exit(1)
        key, value = set_credential.split("=", 1)
        key = key.strip()

        # Load existing credentials and update
        creds = load_credentials_file()
        creds[key] = value.strip()

        with open(CREDENTIALS_FILE, "w") as f:
            for k, v in creds.items():
                f.write(f"{k}={v}\n")
        CREDENTIALS_FILE.chmod(0o600)
        click.echo(f"Set {key} in {CREDENTIALS_FILE}")
        return

    # Interactive mode - collect all credentials
    creds = {}
    for key, description in [
        ("AIDW_WEBHOOK_SECRET", "webhook secret"),
        ("E2B_API_KEY", "E2B API key"),
        ("GH_TOKEN", "GitHub token"),
        ("CLAUDE_CODE_TOKEN", "Claude token (from: claude setup-token)"),
    ]:
        existing = get_credential(key)
        prompt_text = f"{key} ({description})"
        if existing:
            prompt_text += " [configured]"
        val = click.prompt(prompt_text, default="", hide_input=True, show_default=False)
        if val:
            creds[key] = val
        elif existing:
            creds[key] = existing

    # Save credentials
    with open(CREDENTIALS_FILE, "w") as f:
        for k, v in creds.items():
            f.write(f"{k}={v}\n")
    CREDENTIALS_FILE.chmod(0o600)
    click.echo(f"Saved credentials: {CREDENTIALS_FILE}")

    # Configure domain
    click.echo()
    config_data: dict[str, Any] = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            config_data = yaml.safe_load(f) or {}

    current_domain = config_data.get("server", {}).get("domain") or ""
    domain_input = click.prompt(
        "Server domain (e.g. https://example.com)",
        default=current_domain,
        show_default=bool(current_domain),
    )
    if "server" not in config_data:
        config_data["server"] = {"port": 8787, "workers": 3}
    config_data["server"]["domain"] = domain_input if domain_input else None

    # Configure allowed users
    click.echo()

    current_users = config_data.get("auth", {}).get("allowed_users", [])
    if current_users:
        click.echo(f"Current allowed users: {', '.join(current_users)}")

    users_input = click.prompt(
        "Allowed GitHub usernames (comma-separated)",
        default=",".join(current_users),
        show_default=False,
    )

    if users_input:
        users = [u.strip() for u in users_input.split(",") if u.strip()]
        if "auth" not in config_data:
            config_data["auth"] = {}
        config_data["auth"]["allowed_users"] = users

    # Ensure other defaults
    if "server" not in config_data:
        config_data["server"] = {"port": 8787, "workers": 3}
    if "github" not in config_data:
        config_data["github"] = {"bot_name": "aidw"}

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False)
    click.echo(f"Saved config: {CONFIG_FILE}")


@cli.command()
@click.option("--dev", is_flag=True, help="Enable development mode with auto-reload")
@click.option("--port", type=int, help="Override server port")
@click.option("--host", type=str, help="Override server host")
def server(dev: bool, port: int | None, host: str | None) -> None:
    """Start the webhook server."""
    import uvicorn

    # Ensure config exists
    create_default_config()

    # Check credentials
    missing = validate_required_credentials()
    if missing:
        click.secho("Missing required credentials:", fg="red")
        for cred in missing:
            click.echo(f"  - {cred}")
        click.echo("\nRun 'aidw config' to configure credentials.")
        sys.exit(1)

    settings = get_settings()

    # Use overrides or config values
    server_port = port or settings.server.port
    server_host = host or settings.server.host

    click.secho(f"Starting AIDW server on {server_host}:{server_port}", fg="green")

    if dev:
        click.echo("Development mode enabled (auto-reload)")

    uvicorn.run(
        "aidw.server.app:app",
        host=server_host,
        port=server_port,
        reload=dev,
        workers=1 if dev else settings.server.workers,
    )


@cli.group()
def run() -> None:
    """Manually trigger workflows (for testing or CI)."""
    pass


@run.command("plan")
@click.option("--repo", required=True, help="Repository (owner/repo)")
@click.option("--issue", required=True, type=int, help="Issue number")
def run_plan(repo: str, issue: int) -> None:
    """Create a plan for an issue."""
    from aidw.commands import plan_command

    click.echo(f"Running plan for {repo}#{issue}")
    asyncio.run(plan_command.execute_manual(repo, issue))


@run.command("refine")
@click.option("--repo", required=True, help="Repository (owner/repo)")
@click.option("--pr", required=True, type=int, help="PR number")
@click.option("--instruction", default="", help="Refinement instruction")
def run_refine(repo: str, pr: int, instruction: str) -> None:
    """Refine a plan on a PR."""
    from aidw.commands import refine_command

    click.echo(f"Running refine for {repo}#{pr}")
    asyncio.run(refine_command.execute_manual(repo, pr, instruction))


@run.command("build")
@click.option("--repo", required=True, help="Repository (owner/repo)")
@click.option("--pr", required=True, type=int, help="PR number")
def run_build(repo: str, pr: int) -> None:
    """Build from a plan on a PR."""
    from aidw.commands import build_command

    click.echo(f"Running build for {repo}#{pr}")
    asyncio.run(build_command.execute_manual(repo, pr))


@run.command("oneshot")
@click.option("--repo", required=True, help="Repository (owner/repo)")
@click.option("--issue", required=True, type=int, help="Issue number")
def run_oneshot(repo: str, issue: int) -> None:
    """Full automation for an issue."""
    from aidw.commands import oneshot_command

    click.echo(f"Running oneshot for {repo}#{issue}")
    asyncio.run(oneshot_command.execute_manual(repo, issue))


@run.command("iterate")
@click.option("--repo", required=True, help="Repository (owner/repo)")
@click.option("--pr", required=True, type=int, help="PR number")
@click.option("--instruction", default="", help="Iteration instruction")
def run_iterate(repo: str, pr: int, instruction: str) -> None:
    """Iterate on an implementation."""
    from aidw.commands import iterate_command

    click.echo(f"Running iterate for {repo}#{pr}")
    asyncio.run(iterate_command.execute_manual(repo, pr, instruction))


@run.command("codereview")
@click.option("--repo", required=True, help="Repository (owner/repo)")
@click.option("--pr", required=True, type=int, help="PR number")
@click.option("--instruction", default="", help="Review focus or instruction")
def run_codereview(repo: str, pr: int, instruction: str) -> None:
    """Review a PR and post a comment with findings."""
    from aidw.commands import codereview_command

    click.echo(f"Running codereview for {repo}#{pr}")
    asyncio.run(codereview_command.execute_manual(repo, pr, instruction))


@cli.command()
@click.argument("session_id")
def status(session_id: str) -> None:
    """Check session status."""
    from aidw.database import Database

    async def _status() -> None:
        """Fetch and display session details from database."""
        ensure_config_dir()
        db = Database()
        await db.connect()
        session = await db.get_session(session_id)
        await db.close()

        if not session:
            click.secho(f"Session {session_id} not found", fg="red")
            sys.exit(1)

        click.echo(f"Session: {session.id}")
        click.echo(f"  Command: {session.command}")
        click.echo(f"  Status: {session.status.value}")
        click.echo(f"  Repository: {session.repo}")
        click.echo(f"  Issue: #{session.issue_number}")
        if session.pr_number:
            click.echo(f"  PR: #{session.pr_number}")
        if session.sandbox_id:
            click.echo(f"  Sandbox: {session.sandbox_id}")
        click.echo(f"  Created: {session.created_at}")
        if session.completed_at:
            click.echo(f"  Completed: {session.completed_at}")
        if session.error:
            click.secho(f"  Error: {session.error}", fg="red")

    asyncio.run(_status())


async def _find_aidw_webhook(github, repo: str, webhook_url: str):
    """Find an existing AIDW webhook by matching payload URL.

    Searches through all webhooks on the repository and returns the one
    that matches the configured webhook URL.

    Args:
        github: GitHubClient instance
        repo: Repository in "owner/name" format
        webhook_url: URL to match against webhook configurations

    Returns:
        Webhook object if found, None otherwise
    """
    from aidw.github.client import Webhook

    hooks = await github.list_webhooks(repo)
    for hook in hooks:
        if hook.url == webhook_url:
            return hook
    return None


@cli.group()
def webhook() -> None:
    """Manage GitHub webhooks for AIDW."""
    pass


@webhook.command("add")
@click.option("--repo", required=True, help="Repository (owner/repo)")
def webhook_add(repo: str) -> None:
    """Create an AIDW webhook on a GitHub repository."""
    settings = get_settings()
    webhook_url = settings.webhook_url

    if not settings.webhook_secret:
        click.secho("Error: AIDW_WEBHOOK_SECRET not configured. Run 'aidw config' first.", fg="red")
        sys.exit(1)
    if not settings.gh_token:
        click.secho("Error: GH_TOKEN not configured. Run 'aidw config' first.", fg="red")
        sys.exit(1)

    async def _add() -> None:
        """Create a webhook on the repository."""
        from aidw.github.client import GitHubClient

        async with GitHubClient() as github:
            # Check for existing webhook
            existing = await _find_aidw_webhook(github, repo, webhook_url)
            if existing:
                click.secho(f"Webhook already exists on {repo} (id={existing.id})", fg="yellow")
                return

            hook = await github.create_webhook(
                repo=repo,
                url=webhook_url,
                secret=settings.webhook_secret,
                events=["issue_comment", "pull_request_review_comment"],
            )
            click.secho(f"Created webhook on {repo} (id={hook.id})", fg="green")
            click.echo(f"  URL: {hook.url}")
            click.echo(f"  Events: {', '.join(hook.events)}")

    asyncio.run(_add())


@webhook.command("remove")
@click.option("--repo", required=True, help="Repository (owner/repo)")
def webhook_remove(repo: str) -> None:
    """Remove the AIDW webhook from a GitHub repository."""
    settings = get_settings()
    webhook_url = settings.webhook_url

    async def _remove() -> None:
        """Delete the webhook from the repository."""
        from aidw.github.client import GitHubClient

        async with GitHubClient() as github:
            hook = await _find_aidw_webhook(github, repo, webhook_url)
            if not hook:
                click.secho(f"No AIDW webhook found on {repo}", fg="yellow")
                return

            await github.delete_webhook(repo, hook.id)
            click.secho(f"Removed webhook from {repo} (id={hook.id})", fg="green")

    asyncio.run(_remove())


@webhook.command("status")
@click.option("--repo", required=True, help="Repository (owner/repo)")
def webhook_status(repo: str) -> None:
    """Show AIDW webhook config and recent deliveries."""
    settings = get_settings()
    webhook_url = settings.webhook_url

    async def _status() -> None:
        """Display webhook configuration and recent deliveries."""
        from aidw.github.client import GitHubClient

        async with GitHubClient() as github:
            hook = await _find_aidw_webhook(github, repo, webhook_url)
            if not hook:
                click.secho(f"No AIDW webhook found on {repo}", fg="yellow")
                return

            click.secho(f"Webhook on {repo}", fg="green", bold=True)
            click.echo(f"  ID:      {hook.id}")
            click.echo(f"  URL:     {hook.url}")
            click.echo(f"  Active:  {hook.active}")
            click.echo(f"  Events:  {', '.join(hook.events)}")
            click.echo(f"  Created: {hook.created_at}")

            # Get recent deliveries
            deliveries = await github.get_webhook_deliveries(repo, hook.id)
            if not deliveries:
                click.echo("\n  No deliveries yet.")
                return

            click.echo(f"\n  Last {len(deliveries)} deliveries:")
            for d in deliveries:
                if 200 <= d.status_code < 300:
                    color = "green"
                elif d.status_code == 0:
                    color = "yellow"
                else:
                    color = "red"
                action_str = f" ({d.action})" if d.action else ""
                redeliver_str = " [redelivery]" if d.redelivery else ""
                click.echo(
                    f"    {d.delivered_at}  "
                    f"{click.style(str(d.status_code), fg=color)}  "
                    f"{d.event}{action_str}{redeliver_str}"
                )

    asyncio.run(_status())


@cli.command()
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--lines", "-n", default=50, help="Number of lines to show")
def logs(follow: bool, lines: int) -> None:
    """View server logs."""
    # For now, just echo that logs would be shown
    click.echo("Log viewing not yet implemented")
    click.echo("Use: tail -f ~/.config/aidw/aidw.log")


if __name__ == "__main__":
    cli()
