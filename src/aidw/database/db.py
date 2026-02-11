"""SQLite database operations."""

import logging
import uuid
from datetime import datetime

import aiosqlite

from aidw.database.models import Session, SessionStatus
from aidw.env import DB_FILE, ensure_config_dir

logger = logging.getLogger(__name__)

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
"""SQLite schema for session persistence.

Defines the sessions table which tracks workflow execution state across
the lifecycle of AIDW commands (plan, refine, build, etc). Includes
indexes for common query patterns (filtering by repo, status, creation time).

The sessions table stores:
- Session identity and command type
- Execution status and timestamps
- GitHub context (repo, issue, PR, branch)
- E2B sandbox information
- Error details and custom metadata
"""


class Database:
    """Async SQLite database for session tracking."""

    def __init__(self, db_path: str | None = None):
        """Initialize database with optional custom path.

        Args:
            db_path: Optional path to SQLite database file. If not provided,
                uses the default path from configuration (~/.config/aidw/sessions.db)
        """
        ensure_config_dir()
        self.db_path = db_path or str(DB_FILE)
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Connect to the database and initialize schema.

        Opens a connection to the SQLite database file, configures row factory
        for dict-like access, and ensures the sessions table and indexes exist
        by executing the SCHEMA script. Safe to call multiple times as the schema
        uses CREATE TABLE IF NOT EXISTS.
        """
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()
        logger.info(f"Connected to database: {self.db_path}")

    async def close(self) -> None:
        """Close the database connection.

        Safely closes the active database connection if one exists and resets
        the internal connection reference. Safe to call multiple times.
        """
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        """Get the database connection.

        Returns:
            The active aiosqlite connection

        Raises:
            RuntimeError: If connect() has not been called yet
        """
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
        """Create a new session and persist it to the database.

        Generates a new session with a unique 8-character ID (truncated UUID),
        sets initial status to PENDING, and stores it in the sessions table.

        Args:
            command: The AIDW command being executed (e.g., "plan", "build")
            repo: Full repository name in "owner/repo" format
            issue_number: GitHub issue number this session is addressing
            pr_number: Optional PR number if session is PR-related
            triggered_by: Optional GitHub username who triggered the workflow
            instruction: Optional custom instruction from trigger comment

        Returns:
            The newly created Session object with generated ID and timestamps
        """
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
        """Retrieve a session by its unique ID.

        Args:
            session_id: The session ID to look up

        Returns:
            The Session object if found, None otherwise
        """
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
        """Update session fields with automatic timestamp management.

        Builds a dynamic UPDATE query based on which fields are provided.
        Always updates the updated_at timestamp. When status transitions to
        COMPLETED or FAILED, automatically sets completed_at timestamp.
        Metadata is serialized to JSON before storage.

        Args:
            session_id: The session ID to update
            status: New session status (triggers completion timestamp if terminal)
            sandbox_id: E2B sandbox identifier
            branch: Git branch name
            pr_number: GitHub PR number
            error: Error message if session failed
            metadata: Custom metadata dict (will be JSON-serialized)
        """
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
        """Query sessions with optional filtering by repo and status.

        Returns sessions ordered by creation time (newest first), with
        configurable result limit.

        Args:
            repo: Optional repository filter in "owner/repo" format
            status: Optional status filter (PENDING, RUNNING, COMPLETED, FAILED)
            limit: Maximum number of sessions to return (default 50)

        Returns:
            List of Session objects matching the filters
        """
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
        """Find the currently running session for a specific issue.

        Used to prevent duplicate concurrent workflows on the same issue.
        Only returns sessions with RUNNING status.

        Args:
            repo: Repository name in "owner/repo" format
            issue_number: GitHub issue number

        Returns:
            The most recent running Session for this issue, or None if no
            active session exists
        """
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
        """Retrieve the most recent session associated with a PR.

        Useful for finding the last workflow execution that worked on a specific
        pull request, regardless of status (running, completed, or failed).

        Args:
            repo: Repository name in "owner/repo" format
            pr_number: GitHub pull request number

        Returns:
            The most recent Session for this PR, or None if no sessions exist
        """
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
        """Remove sessions older than the specified retention period.

        Useful for database maintenance to prevent unbounded growth. Deletes
        sessions based on their created_at timestamp.

        Args:
            days: Retention period in days (default 30). Sessions created
                before this many days ago will be deleted.

        Returns:
            Number of sessions deleted
        """
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
