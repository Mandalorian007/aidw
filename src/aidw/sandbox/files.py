"""File operations in E2B sandbox."""

import logging
from pathlib import Path

from aidw.sandbox.manager import SandboxInstance

logger = logging.getLogger(__name__)


async def upload_file(instance: SandboxInstance, local_path: Path, remote_path: str) -> None:
    """Upload a local file to the sandbox."""
    content = local_path.read_text()
    instance.sandbox.files.write(remote_path, content)
    logger.debug(f"Uploaded {local_path} to {remote_path}")


async def upload_directory(
    instance: SandboxInstance,
    local_dir: Path,
    remote_dir: str,
    pattern: str = "*",
) -> None:
    """Upload a directory to the sandbox."""
    # Create remote directory
    instance.sandbox.commands.run(f"mkdir -p {remote_dir}")

    # Upload matching files
    for local_file in local_dir.glob(pattern):
        if local_file.is_file():
            remote_path = f"{remote_dir}/{local_file.name}"
            await upload_file(instance, local_file, remote_path)


async def download_file(instance: SandboxInstance, remote_path: str) -> str | None:
    """Download a file from the sandbox."""
    try:
        return instance.sandbox.files.read(remote_path)
    except Exception as e:
        logger.warning(f"Failed to download {remote_path}: {e}")
        return None


async def list_files(instance: SandboxInstance, remote_dir: str, pattern: str = "*") -> list[str]:
    """List files in a sandbox directory."""
    result = instance.sandbox.commands.run(
        f"find {remote_dir} -name '{pattern}' -type f 2>/dev/null",
        timeout=30,
    )

    if result.exit_code != 0:
        return []

    return [f.strip() for f in result.stdout.split("\n") if f.strip()]
