"""Authentication sync for E2B sandbox."""

import logging
from pathlib import Path

from aidw.sandbox.manager import SandboxInstance

logger = logging.getLogger(__name__)

# Default Claude config directory containing authentication files
DEFAULT_CLAUDE_DIR = Path.home() / ".claude"


async def sync_claude_auth(
    instance: SandboxInstance,
    source_dir: Path | None = None,
) -> bool:
    """Sync Claude Code authentication to sandbox.

    Copies the local ~/.claude directory to the sandbox so that
    Claude Code can use subscription authentication.

    Returns True if sync was successful.
    """
    source_dir = source_dir or DEFAULT_CLAUDE_DIR

    if not source_dir.exists():
        logger.warning(f"Claude config directory not found: {source_dir}")
        return False

    # Create .claude directory in sandbox
    instance.sandbox.commands.run("mkdir -p /home/user/.claude")

    # Files to sync
    auth_files = [
        "credentials.json",
        "settings.json",
        ".credentials.json",  # Alternative name
    ]

    synced = False
    for file_name in auth_files:
        source_file = source_dir / file_name
        if source_file.exists():
            try:
                content = source_file.read_text()
                instance.sandbox.files.write(f"/home/user/.claude/{file_name}", content)
                logger.info(f"Synced {file_name} to sandbox")
                synced = True
            except Exception as e:
                logger.error(f"Failed to sync {file_name}: {e}")

    return synced


async def verify_claude_auth(instance: SandboxInstance) -> bool:
    """Verify that Claude Code authentication works in the sandbox.

    Returns True if Claude Code can authenticate.
    """
    result = instance.sandbox.commands.run(
        "claude --version",
        timeout=30,
    )

    if result.exit_code != 0:
        logger.error("Claude Code not available in sandbox")
        return False

    logger.info(f"Claude Code version: {result.stdout.strip()}")
    return True
