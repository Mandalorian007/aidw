"""SQLite database operations."""

import logging
import uuid
from datetime import datetime

import aiosqlite

from aidw.database.models import Session, SessionStatus
from aidw.env import DB_FILE, ensure_config_dir

logger = logging.getLogger(__name__)

# Schema
SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    status TEXT NOT NULL,
    repo TEXT NOT NULL,
    issue_number INTEGER NOT NULL,
    pr_number INTEGER,
    branch TEXT,
    sandbox_id TEXT,
    triggered_by TEXT,
    instruction TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    completed_at TEXT,
    error TEXT,
    metadata TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_repo ON sessions(repo);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at);
"""


class Database:
    """Async SQLite database for session tracking."""

    def __init__(self, db_path: str | None = None):
        ensure_config_dir()
        self.db_path = db_path or str(DB_FILE)
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Connect to the database and initialize schema."""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()
        logger.info(f"Connected to database: {self.db_path}")

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        """Get the database connection."""
        if not self._conn:
            raise RuntimeError("Database not connected")
        return self._conn

    async def create_session(
        self,
        command: str,
        repo: str,
        issue_number: int,
        pr_number: int | None = None,
        triggered_by: str | None = None,
        instruction: str | None = None,
    ) -> Session:
        """Create a new session."""
        session = Session(
            id=str(uuid.uuid4())[:8],
            command=command,
            status=SessionStatus.PENDING,
            repo=repo,
            issue_number=issue_number,
            pr_number=pr_number,
            triggered_by=triggered_by,
            instruction=instruction,
        )

        data = session.to_dict()
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))

        await self.conn.execute(
            f"INSERT INTO sessions ({columns}) VALUES ({placeholders})",
            list(data.values()),
        )
        await self.conn.commit()

        logger.info(f"Created session: {session.id}")
        return session

    async def get_session(self, session_id: str) -> Session | None:
        """Get a session by ID."""
        cursor = await self.conn.execute(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return Session.from_dict(dict(row))

    async def update_session(
        self,
        session_id: str,
        status: SessionStatus | None = None,
        sandbox_id: str | None = None,
        branch: str | None = None,
        pr_number: int | None = None,
        error: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Update a session."""
        updates = ["updated_at = ?"]
        values: list[str | int] = [datetime.utcnow().isoformat()]

        if status is not None:
            updates.append("status = ?")
            values.append(status.value)

            if status in (SessionStatus.COMPLETED, SessionStatus.FAILED):
                updates.append("completed_at = ?")
                values.append(datetime.utcnow().isoformat())

        if sandbox_id is not None:
            updates.append("sandbox_id = ?")
            values.append(sandbox_id)

        if branch is not None:
            updates.append("branch = ?")
            values.append(branch)

        if pr_number is not None:
            updates.append("pr_number = ?")
            values.append(pr_number)

        if error is not None:
            updates.append("error = ?")
            values.append(error)

        if metadata is not None:
            import json

            updates.append("metadata = ?")
            values.append(json.dumps(metadata))

        values.append(session_id)

        await self.conn.execute(
            f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        await self.conn.commit()

    async def list_sessions(
        self,
        repo: str | None = None,
        status: SessionStatus | None = None,
        limit: int = 50,
    ) -> list[Session]:
        """List sessions with optional filters."""
        query = "SELECT * FROM sessions"
        conditions: list[str] = []
        values: list[str | int] = []

        if repo:
            conditions.append("repo = ?")
            values.append(repo)

        if status:
            conditions.append("status = ?")
            values.append(status.value)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY created_at DESC LIMIT ?"
        values.append(limit)

        cursor = await self.conn.execute(query, values)
        rows = await cursor.fetchall()

        return [Session.from_dict(dict(row)) for row in rows]

    async def get_active_session_for_issue(
        self,
        repo: str,
        issue_number: int,
    ) -> Session | None:
        """Get an active (running) session for an issue."""
        cursor = await self.conn.execute(
            """
            SELECT * FROM sessions
            WHERE repo = ? AND issue_number = ? AND status = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (repo, issue_number, SessionStatus.RUNNING.value),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return Session.from_dict(dict(row))

    async def get_latest_session_for_pr(
        self,
        repo: str,
        pr_number: int,
    ) -> Session | None:
        """Get the latest session for a PR."""
        cursor = await self.conn.execute(
            """
            SELECT * FROM sessions
            WHERE repo = ? AND pr_number = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (repo, pr_number),
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return Session.from_dict(dict(row))

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """Delete sessions older than the specified days."""
        cutoff = datetime.utcnow()
        from datetime import timedelta

        cutoff = cutoff - timedelta(days=days)

        cursor = await self.conn.execute(
            "DELETE FROM sessions WHERE created_at < ?",
            (cutoff.isoformat(),),
        )
        await self.conn.commit()

        deleted = cursor.rowcount
        if deleted > 0:
            logger.info(f"Deleted {deleted} old sessions")

        return deleted
