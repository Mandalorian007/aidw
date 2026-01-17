"""Git operations in E2B sandbox."""

import logging
from dataclasses import dataclass

from aidw.sandbox.manager import SandboxInstance

logger = logging.getLogger(__name__)


@dataclass
class GitStatus:
    """Git repository status."""

    branch: str
    clean: bool
    staged_files: list[str]
    modified_files: list[str]
    untracked_files: list[str]


async def get_status(instance: SandboxInstance) -> GitStatus:
    """Get git status in the repo."""
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
    """Get recent git log."""
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git log --oneline -{count}",
        timeout=30,
    )
    return result.stdout


async def get_diff(instance: SandboxInstance, base: str | None = None) -> str:
    """Get diff from base (defaults to HEAD~1)."""
    base = base or "HEAD~1"
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git diff {base} 2>/dev/null || echo ''",
        timeout=60,
    )
    return result.stdout


async def get_diff_stat(instance: SandboxInstance, base: str | None = None) -> str:
    """Get diff stat from base."""
    base = base or "HEAD~1"
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git diff --stat {base} 2>/dev/null || echo ''",
        timeout=60,
    )
    return result.stdout


async def create_branch(instance: SandboxInstance, branch: str) -> bool:
    """Create and checkout a new branch."""
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git checkout -b {branch}",
        timeout=30,
    )
    return result.exit_code == 0


async def checkout_branch(instance: SandboxInstance, branch: str) -> bool:
    """Checkout an existing branch."""
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
    """Push changes to remote."""
    branch_arg = branch or ""
    force_arg = "--force" if force else ""

    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git push -u origin {branch_arg} {force_arg}".strip(),
        timeout=120,
    )
    return result.exit_code == 0


async def fetch(instance: SandboxInstance) -> bool:
    """Fetch from remote."""
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git fetch",
        timeout=120,
    )
    return result.exit_code == 0


async def pull(instance: SandboxInstance) -> bool:
    """Pull from remote."""
    result = instance.sandbox.commands.run(
        f"cd {instance.repo_path} && git pull",
        timeout=120,
    )
    return result.exit_code == 0
