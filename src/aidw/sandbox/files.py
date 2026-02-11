"""File operations in E2B sandbox."""

import logging
from pathlib import Path

from aidw.sandbox.manager import SandboxInstance

logger = logging.getLogger(__name__)


async def upload_file(instance: SandboxInstance, local_path: Path, remote_path: str) -> None:
    """Upload a local file to the sandbox.

    Args:
        instance: Sandbox instance to upload to
        local_path: Path to local file
        remote_path: Destination path in sandbox (absolute path)
    """
    content = local_path.read_text()
    instance.sandbox.files.write(remote_path, content)
    logger.debug(f"Uploaded {local_path} to {remote_path}")


async def upload_directory(
    instance: SandboxInstance,
    local_dir: Path,
    remote_dir: str,
    pattern: str = "*",
) -> None:
    """Upload a directory to the sandbox.

    Recursively uploads all files matching the pattern. Creates the
    remote directory if it doesn't exist.

    Args:
        instance: Sandbox instance to upload to
        local_dir: Path to local directory
        remote_dir: Destination directory in sandbox
        pattern: Glob pattern for files to upload (default: "*")
    """
    # Create remote directory
    instance.sandbox.commands.run(f"mkdir -p {remote_dir}")

    # Upload matching files
    for local_file in local_dir.glob(pattern):
        if local_file.is_file():
            remote_path = f"{remote_dir}/{local_file.name}"
            await upload_file(instance, local_file, remote_path)


async def download_file(instance: SandboxInstance, remote_path: str) -> str | None:
    """Download a file from the sandbox.

    Args:
        instance: Sandbox instance to download from
        remote_path: Path to file in sandbox (absolute path)

    Returns:
        File contents as string, or None if file doesn't exist or read fails
    """
    try:
        return instance.sandbox.files.read(remote_path)
    except Exception as e:
        logger.warning(f"Failed to download {remote_path}: {e}")
        return None


async def list_files(instance: SandboxInstance, remote_dir: str, pattern: str = "*") -> list[str]:
    """List files in a sandbox directory.

    Uses find command to locate matching files.

    Args:
        instance: Sandbox instance to query
        remote_dir: Directory path in sandbox
        pattern: File name pattern (default: "*")

    Returns:
        List of absolute file paths in the sandbox
    """
    result = instance.sandbox.commands.run(
        f"find {remote_dir} -name '{pattern}' -type f 2>/dev/null",
        timeout=30,
    )

    if result.exit_code != 0:
        return []

    return [f.strip() for f in result.stdout.split("\n") if f.strip()]
