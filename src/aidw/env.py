"""Configuration for AIDW.

Minimal config — gh and claude handle their own auth.
"""

from pathlib import Path

COMMANDS_DIR = Path.home() / ".claude" / "commands" / "aidw"
