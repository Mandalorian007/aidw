"""AIDW CLI - Command line interface."""

import asyncio
import sys

import click

from aidw import __version__
from aidw.env import (
    get_settings,
    validate_required_credentials,
    create_default_config,
    ensure_config_dir,
)


@click.group()
@click.version_option(version=__version__, prog_name="aidw")
def cli() -> None:
    """AIDW - AI Dev Workflow

    Trigger AI workflows from GitHub issue/PR comments.
    """
    pass


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
        click.echo("\nSet these environment variables or add to .env file.")
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


@cli.command()
@click.argument("session_id")
def status(session_id: str) -> None:
    """Check session status."""
    from aidw.database import Database

    async def _status() -> None:
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


@cli.command()
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option("--lines", "-n", default=50, help="Number of lines to show")
def logs(follow: bool, lines: int) -> None:
    """View server logs."""
    import subprocess

    log_file = ensure_config_dir() or ""
    log_path = str(get_settings().server.port)  # Placeholder for actual log path

    # For now, just echo that logs would be shown
    click.echo("Log viewing not yet implemented")
    click.echo("Use: tail -f ~/.aidw/aidw.log")


if __name__ == "__main__":
    cli()
