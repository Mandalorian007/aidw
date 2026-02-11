"""Git operations in E2B sandbox."""

import logging
from dataclasses import dataclass

from aidw.sandbox.manager import SandboxInstance

logger = logging.getLogger(__name__)


@dataclass
class GitStatus:
    """Git repository status information.

    Parsed from git status --porcelain output to provide structured
    information about the working tree state.

    Attributes:
        branch: Current branch name
        clean: True if no changes (staged, modified, or untracked)
        staged_files: Files in staging area ready to commit
        modified_files: Modified files not yet staged
        untracked_files: New files not yet added to git
    """

    branch: str
    clean: bool
    staged_files: list[str]
    modified_files: list[str]
    untracked_files: list[str]


async def get_status(instance: SandboxInstance) -> GitStatus:
    """Get git status in the repo.

    Parses git status --porcelain output to determine branch, staged files,
    modified files, and untracked files.

    Args:
        instance: Sandbox instance with cloned repository

    Returns:
        Structured git status information
    """
    repo_path = instance.repo_path

    # Get current branch
    branch_result = instance.sandbox.commands.run(
        f"cd {repo_path} && git branch --show-current",
        timeout=30,
    )
    branch = branch_result.stdout.strip()

    # Get status
    status_result = instance.sandbox.commands.run(
        f"cd {repo_path} && git status --porcelain",
        timeout=30,
    )

    staged = []
    modified = []
    untracked = []

    for line in status_result.stdout.split("\n"):
        if not line.strip():
            continue

        status_code = line[:2]
        file_path = line[3:].strip()

        if status_code[0] in ("A", "M", "D", "R", "C"):
            staged.append(file_path)
        if status_code[1] == "M":
            modified.append(file_path)
        if status_code == "??":
            untracked.append(file_path)

    return GitStatus(
        branch=branch,
        clean=not (staged or modified or untracked),
        staged_files=staged,
        modified_files=modified,
        untracked_files=untracked,
    )


async def get_log(instance: SandboxInstance, count: int = 10) -> str:
    """Get recent git log.

    Args:
        instance: Sandbox instance with cloned repository
        count: Number of commits to show (default: 10)

    Returns:
        Git log output (one line per commit)
    """
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git log --oneline -{count}",
        timeout=30,
    )
    return result.stdout


async def get_diff(instance: SandboxInstance, base: str | None = None) -> str:
    """Get diff from base commit.

    Args:
        instance: Sandbox instance with cloned repository
        base: Base commit/ref for diff (default: HEAD~1)

    Returns:
        Full git diff output
    """
    base = base or "HEAD~1"
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git diff {base} 2>/dev/null || echo ''",
        timeout=60,
    )
    return result.stdout


async def get_diff_stat(instance: SandboxInstance, base: str | None = None) -> str:
    """Get diff statistics from base commit.

    Shows a summary of changed files and line counts.

    Args:
        instance: Sandbox instance with cloned repository
        base: Base commit/ref for diff (default: HEAD~1)

    Returns:
        Git diff --stat output
    """
    base = base or "HEAD~1"
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git diff --stat {base} 2>/dev/null || echo ''",
        timeout=60,
    )
    return result.stdout


async def create_branch(instance: SandboxInstance, branch: str) -> bool:
    """Create and checkout a new branch.

    Args:
        instance: Sandbox instance with cloned repository
        branch: Name of new branch to create

    Returns:
        True if successful, False otherwise
    """
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git checkout -b {branch}",
        timeout=30,
    )
    return result.exit_code == 0


async def checkout_branch(instance: SandboxInstance, branch: str) -> bool:
    """Checkout an existing branch.

    Args:
        instance: Sandbox instance with cloned repository
        branch: Name of branch to checkout

    Returns:
        True if successful, False otherwise
    """
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git checkout {branch}",
        timeout=30,
    )
    return result.exit_code == 0


async def push(
    instance: SandboxInstance,
    branch: str | None = None,
    force: bool = False,
) -> bool:
    """Push changes to remote repository.

    Args:
        instance: Sandbox instance with cloned repository
        branch: Branch name to push (uses current if None)
        force: Whether to force push

    Returns:
        True if successful, False otherwise
    """
    branch_arg = branch or ""
    force_arg = "--force" if force else ""

    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git push -u origin {branch_arg} {force_arg}".strip(),
        timeout=120,
    )
    return result.exit_code == 0


async def fetch(instance: SandboxInstance) -> bool:
    """Fetch from remote repository.

    Args:
        instance: Sandbox instance with cloned repository

    Returns:
        True if successful, False otherwise
    """
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git fetch",
        timeout=120,
    )
    return result.exit_code == 0


async def pull(instance: SandboxInstance) -> bool:
    """Pull from remote repository.

    Args:
        instance: Sandbox instance with cloned repository

    Returns:
        True if successful, False otherwise
    """
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git pull",
        timeout=120,
    )
    return result.exit_code == 0
