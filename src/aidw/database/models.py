"""Database models for session tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import json


class SessionStatus(Enum):
    """Status of a workflow session."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Session:
    """A workflow session."""

    id: str
    command: str  # plan, refine, build, oneshot, iterate
    status: SessionStatus
    repo: str
    issue_number: int
    pr_number: int | None = None
    branch: str | None = None
    sandbox_id: str | None = None
    triggered_by: str | None = None
    instruction: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "command": self.command,
            "status": self.status.value,
            "repo": self.repo,
            "issue_number": self.issue_number,
            "pr_number": self.pr_number,
            "branch": self.branch,
            "sandbox_id": self.sandbox_id,
            "triggered_by": self.triggered_by,
            "instruction": self.instruction,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
            "metadata": json.dumps(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Create from database row dictionary."""
        return cls(
            id=data["id"],
            command=data["command"],
            status=SessionStatus(data["status"]),
            repo=data["repo"],
            issue_number=data["issue_number"],
            pr_number=data["pr_number"],
            branch=data["branch"],
            sandbox_id=data["sandbox_id"],
            triggered_by=data["triggered_by"],
            instruction=data["instruction"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            completed_at=(
                datetime.fromisoformat(data["completed_at"]) if data["completed_at"] else None
            ),
            error=data["error"],
            metadata=json.loads(data["metadata"]) if data["metadata"] else {},
        )
