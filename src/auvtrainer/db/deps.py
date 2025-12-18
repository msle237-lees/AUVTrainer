from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request

from .database import DatabaseConfig, DatabaseManager


def _db_path_from_env() -> str:
    """
    Determine the database path.

    Env var:
        APP_DB_PATH: path to sqlite db file
    """
    return os.getenv("APP_DB_PATH", "app.db")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    App startup/shutdown:
      - open DB connection
      - optionally ensure minimal schema exists
      - close DB connection on shutdown
    """
    dbm = DatabaseManager(DatabaseConfig(path=_db_path_from_env()))
    await dbm.connect()

    # Minimal, non-domain-specific schema (safe to remove if not needed).
    await dbm.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
            data TEXT NOT NULL
        );
        """
    )

    app.state.dbm = dbm
    try:
        yield
    finally:
        await app.state.dbm.close()


async def get_dbm(request: Request) -> DatabaseManager:
    """
    Dependency to retrieve the DatabaseManager from app.state.
    """
    dbm = getattr(request.app.state, "dbm", None)
    if dbm is None:
        raise RuntimeError("DatabaseManager not available on app.state (lifespan not initialized).")
    return dbm
