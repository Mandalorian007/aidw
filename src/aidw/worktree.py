"""Worktree slug generation and cleanup utilities."""

import glob
import json
import os
import re
import subprocess


def generate_slug(description: str) -> str:
    """Generate a kebab-case slug from a description.

    Shells out to claude CLI with haiku for speed. Falls back to
    simple slugification if the LLM call fails.
    """
    try:
        result = subprocess.run(
            [
                "claude",
                "--model", "haiku",
                "-p",
                f"Generate a short kebab-case slug (3-5 words max) for: {description}. "
                f"Output ONLY the slug, nothing else.",
                "--output-format", "json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            slug = data.get("result", "").strip()
            slug = _sanitize_slug(slug)
            if slug:
                return slug
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, KeyError):
        pass

    return _fallback_slug(description)


def _sanitize_slug(slug: str) -> str:
    """Sanitize a slug to only contain [a-z0-9-], truncated to 50 chars."""
    slug = slug.strip().lower()
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug[:50]


def _fallback_slug(description: str) -> str:
    """Simple slugification of first 5 words."""
    words = description.lower().split()[:5]
    raw = "-".join(words)
    return _sanitize_slug(raw)


def cleanup_worktrees() -> list[str]:
    """Remove all orphaned aidw/* worktrees.

    Returns list of removed worktree paths.
    """
    removed = []

    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return removed

        for line in result.stdout.splitlines():
            if line.startswith("worktree ") and ".claude/worktrees/aidw/" in line:
                path = line.split("worktree ", 1)[1]
                rm_result = subprocess.run(
                    ["git", "worktree", "remove", path, "--force"],
                    capture_output=True,
                    text=True,
                )
                if rm_result.returncode == 0:
                    removed.append(path)

        # Clean up stale metadata
        subprocess.run(
            ["git", "worktree", "prune"],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        pass

    return removed


def remove_worktree(slug: str) -> bool:
    """Remove a specific aidw worktree by slug.

    Returns True if successfully removed.
    """
    # Find the worktree path by matching the slug in worktree list
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return False

        for line in result.stdout.splitlines():
            if line.startswith("worktree ") and f"aidw/{slug}" in line:
                path = line.split("worktree ", 1)[1]
                rm_result = subprocess.run(
                    ["git", "worktree", "remove", path, "--force"],
                    capture_output=True,
                    text=True,
                )
                return rm_result.returncode == 0

    except FileNotFoundError:
        pass

    return False


def cleanup_plan_files() -> list[str]:
    """Remove leftover /tmp/*-plan.md files from aidw runs.

    Returns list of removed file paths.
    """
    removed = []
    for path in glob.glob("/tmp/*-plan.md"):
        try:
            os.remove(path)
            removed.append(path)
        except OSError:
            pass
    return removed
