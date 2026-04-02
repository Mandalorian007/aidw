"""Claude subprocess dispatch — build command, run, parse JSON output."""

import json
import subprocess
import sys


def run_claude(
    slash_command: str,
    arguments: str,
    worktree_name: str,
) -> str:
    """Run a claude subprocess with the given slash command and arguments.

    Args:
        slash_command: The slash command to invoke (e.g., "/aidw:one-shot-pr")
        arguments: Arguments to pass to the slash command
        worktree_name: Worktree name for --worktree flag (e.g., "aidw/add-rate-limiting")

    Returns:
        The text result from Claude's JSON output.

    Raises:
        RuntimeError: If the claude subprocess fails or output can't be parsed.
    """
    prompt = f"{slash_command} {arguments}"

    cmd = [
        "claude",
        "--dangerously-skip-permissions",
        "--worktree", worktree_name,
        "--output-format", "json",
        "-p", prompt,
    ]

    print(f"Running: claude --worktree {worktree_name} ...", file=sys.stderr)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("Claude subprocess timed out after 30 minutes")

    if result.returncode != 0:
        stderr = result.stderr.strip() if result.stderr else "unknown error"
        raise RuntimeError(f"Claude subprocess failed (exit {result.returncode}): {stderr}")

    # Parse JSON output
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse Claude JSON output: {result.stdout[:200]}")

    # Extract the text result from the JSON wrapper
    text = data.get("result", "")
    if not text:
        raise RuntimeError(f"No result field in Claude output: {list(data.keys())}")

    return text


def extract_pr_url(text: str) -> str | None:
    """Extract a GitHub PR URL from Claude's text output.

    Looks for a URL matching the pattern https://github.com/.../pull/...
    Checks lines in reverse order since the PR URL is typically at the end.
    """
    import re

    pattern = r"https://github\.com/[^/]+/[^/]+/pull/\d+"

    for line in reversed(text.splitlines()):
        match = re.search(pattern, line)
        if match:
            return match.group(0)

    return None
