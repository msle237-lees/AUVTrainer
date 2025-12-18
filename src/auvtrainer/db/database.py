from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

import aiosqlite


@dataclass(slots=True)
class DatabaseConfig:
    """Configuration for the SQLite database connection."""
    path: str
    enforce_foreign_keys: bool = True
    row_factory_dict: bool = True


class DatabaseManager:
    """
    Thin async wrapper around aiosqlite.

    Keeps a single connection open for the app lifetime (managed by FastAPI lifespan).
    """

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Open the SQLite connection and apply basic pragmas."""
        if self.connection is not None:
            return

        self.connection = await aiosqlite.connect(self.config.path)

        if self.config.enforce_foreign_keys:
            await self.connection.execute("PRAGMA foreign_keys = ON;")

        if self.config.row_factory_dict:
            self.connection.row_factory = aiosqlite.Row

        await self.connection.commit()

    async def close(self) -> None:
        """Close the SQLite connection."""
        if self.connection is None:
            return
        await self.connection.close()
        self.connection = None

    def require_connection(self) -> aiosqlite.Connection:
        """Return an active connection or raise a clear error."""
        if self.connection is None:
            raise RuntimeError("Database connection is not initialized. Did lifespan run?")
        return self.connection

    async def execute(self, sql: str, params: Sequence[Any] | None = None) -> int:
        """
        Execute a statement and commit.

        Returns:
            int: lastrowid when available, otherwise -1.
        """
        db = self.require_connection()
        cur = await db.execute(sql, params or ())
        await db.commit()
        last_id = getattr(cur, "lastrowid", None)
        await cur.close()
        return int(last_id) if last_id is not None else -1

    async def fetch_one(self, sql: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
        """Fetch a single row as a dict (or None)."""
        db = self.require_connection()
        cur = await db.execute(sql, params or ())
        row = await cur.fetchone()
        await cur.close()
        return dict(row) if row else None

    async def fetch_many(
        self, sql: str, params: Sequence[Any] | None = None
    ) -> list[dict[str, Any]]:
        """Fetch multiple rows as a list of dicts."""
        db = self.require_connection()
        cur = await db.execute(sql, params or ())
        rows = await cur.fetchall()
        await cur.close()
        return [dict(r) for r in rows]
