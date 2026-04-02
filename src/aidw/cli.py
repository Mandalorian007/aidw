"""AIDW CLI - Command line interface."""

import shutil
import subprocess
import sys
from importlib import resources

import click

from aidw import __version__
from aidw.env import COMMANDS_DIR


@click.group()
@click.version_option(version=__version__, prog_name="aidw")
def cli() -> None:
    """AIDW - AI Dev Workflow

    CLI that turns descriptions into draft PRs via Claude Code.
    """
    pass


@cli.command()
def setup() -> None:
    """Install slash commands and verify dependencies."""
    errors = []

    # Check git
    if shutil.which("git"):
        click.echo("  git: ok")
    else:
        errors.append("git not found. Install git: https://git-scm.com/")

    # Check gh
    if shutil.which("gh"):
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            click.echo("  gh: ok")
        else:
            errors.append("gh not authenticated. Run: gh auth login")
    else:
        errors.append("gh not found. Install GitHub CLI: https://cli.github.com/")

    # Check claude
    if shutil.which("claude"):
        click.echo("  claude: ok")
    else:
        errors.append(
            "claude not found. Install Claude Code: npm install -g @anthropic-ai/claude-code"
        )

    if errors:
        click.echo()
        for err in errors:
            click.secho(f"  Error: {err}", fg="red")
        sys.exit(1)

    # Install slash commands
    click.echo()
    COMMANDS_DIR.mkdir(parents=True, exist_ok=True)

    commands_md = resources.files("aidw") / "prompts"
    installed = []
    for md_file in commands_md.iterdir():
        if md_file.name.endswith(".md"):
            dest = COMMANDS_DIR / md_file.name
            dest.write_text(md_file.read_text())
            name = md_file.name.removesuffix(".md")
            installed.append(f"/aidw:{name}")

    click.secho("Installed slash commands:", fg="green")
    for cmd in sorted(installed):
        click.echo(f"  {cmd}")

    click.echo()
    click.secho("Setup complete!", fg="green")


@cli.command("one-shot")
@click.argument("description")
def one_shot(description: str) -> None:
    """Plan, implement, and open a draft PR from a description."""
    from aidw.dispatch import extract_pr_url, run_claude
    from aidw.worktree import generate_slug, remove_worktree

    _require_git_repo()

    slug = generate_slug(description)
    worktree_name = f"aidw/{slug}"

    click.echo(f"Generating PR for: {description}")
    click.echo(f"Worktree: {worktree_name}")
    click.echo()

    try:
        result_text = run_claude("/aidw:one-shot-pr", description, worktree_name)
    except RuntimeError as e:
        click.secho(f"Error: {e}", fg="red")
        remove_worktree(slug)
        sys.exit(1)

    # Cleanup worktree
    remove_worktree(slug)

    # Extract and print PR URL
    pr_url = extract_pr_url(result_text)
    if pr_url:
        click.echo()
        click.secho(pr_url, fg="green", bold=True)
    else:
        click.echo()
        click.secho("Could not extract PR URL from output.", fg="yellow")
        click.echo("Claude output (last 20 lines):")
        for line in result_text.splitlines()[-20:]:
            click.echo(f"  {line}")


@cli.command()
@click.argument("pr", type=str)
@click.argument("feedback", required=False, default="")
def iterate(pr: str, feedback: str) -> None:
    """Iterate on a PR with optional feedback.

    PR can be a number or a GitHub PR URL.
    """
    from aidw.dispatch import extract_pr_url, run_claude
    from aidw.worktree import remove_worktree

    _require_git_repo()

    # Normalize PR to a number
    pr_number = _parse_pr_number(pr)

    # Get PR branch
    result = subprocess.run(
        ["gh", "pr", "view", str(pr_number), "--json", "headRefName", "-q", ".headRefName"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        click.secho(f"Error: Could not get branch for PR #{pr_number}", fg="red")
        click.secho(result.stderr.strip(), fg="red")
        sys.exit(1)

    branch = result.stdout.strip()
    slug = f"iterate-pr-{pr_number}"
    worktree_name = f"aidw/{slug}"

    click.echo(f"Iterating on PR #{pr_number} (branch: {branch})")
    if feedback:
        click.echo(f"Feedback: {feedback}")
    click.echo(f"Worktree: {worktree_name}")
    click.echo()

    arguments = f"--pr {pr_number} --branch {branch}"
    if feedback:
        arguments += f" {feedback}"

    try:
        result_text = run_claude("/aidw:iterate", arguments, worktree_name)
    except RuntimeError as e:
        click.secho(f"Error: {e}", fg="red")
        remove_worktree(slug)
        sys.exit(1)

    # Cleanup worktree
    remove_worktree(slug)

    # Extract and print PR URL
    pr_url = extract_pr_url(result_text)
    if pr_url:
        click.echo()
        click.secho(pr_url, fg="green", bold=True)
    else:
        click.echo()
        click.secho("Iteration complete.", fg="green")


@cli.command()
def cleanup() -> None:
    """Remove orphaned aidw/* worktrees and leftover plan files."""
    from aidw.worktree import cleanup_plan_files, cleanup_worktrees

    _require_git_repo()

    removed = cleanup_worktrees()
    if removed:
        click.secho(f"Removed {len(removed)} worktree(s):", fg="green")
        for path in removed:
            click.echo(f"  {path}")

    plans = cleanup_plan_files()
    if plans:
        click.secho(f"Removed {len(plans)} plan file(s):", fg="green")
        for path in plans:
            click.echo(f"  {path}")

    if not removed and not plans:
        click.echo("Nothing to clean up.")


@cli.command()
def uninstall() -> None:
    """Remove slash commands from ~/.claude and clean up worktrees."""
    # Remove slash commands
    if COMMANDS_DIR.exists():
        files = list(COMMANDS_DIR.iterdir())
        shutil.rmtree(COMMANDS_DIR)
        click.secho("Removed slash commands:", fg="green")
        for f in files:
            click.echo(f"  {f.name}")
    else:
        click.echo("No slash commands found.")

    # Also run cleanup if in a git repo
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        from aidw.worktree import cleanup_worktrees

        removed = cleanup_worktrees()
        if removed:
            click.echo()
            click.secho(f"Cleaned up {len(removed)} worktree(s).", fg="green")


def _require_git_repo() -> None:
    """Exit with error if not inside a git repository."""
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        click.secho("Error: Not inside a git repository.", fg="red")
        sys.exit(1)


def _parse_pr_number(pr: str) -> int:
    """Parse a PR number from a number or GitHub URL."""
    # Try as plain number
    try:
        return int(pr)
    except ValueError:
        pass

    # Try as URL: https://github.com/owner/repo/pull/123
    import re

    match = re.search(r"/pull/(\d+)", pr)
    if match:
        return int(match.group(1))

    click.secho(f"Error: Could not parse PR number from: {pr}", fg="red")
    sys.exit(1)


if __name__ == "__main__":
    cli()
