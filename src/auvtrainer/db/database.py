import sqlite3
from pathlib import Path
from typing import Generator, Optional

# Folder: src/auvtrainer/db/
BASE_DIR = Path(__file__).parent

# SQLite file location: src/auvtrainer/db/db/auvtrainer.db
DB_PATH = BASE_DIR / "db" / "auvtrainer.db"

# SQL init file location: src/auvtrainer/db/initialization_sql.sql
INIT_SQL_PATH = BASE_DIR / "initialization_sql.sql"


def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Establishes a connection to the SQLite database.

    Args:
        db_path (Optional[Path]): Path to the SQLite database file.
                                  If None, uses the default DB_PATH.

    Returns:
        sqlite3.Connection: SQLite database connection object.
    """
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Enforce FK constraints (SQLite defaults to OFF unless enabled per-connection)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def initialize_database(db_path: Optional[Path] = None) -> None:
    """
    Initializes the database by creating necessary tables if they do not exist.

    Args:
        db_path (Optional[Path]): Path to the SQLite database file.
                                  If None, uses the default DB_PATH.
    """
    conn = get_db_connection(db_path)
    try:
        sql_script = INIT_SQL_PATH.read_text(encoding="utf-8")
        conn.executescript(sql_script)
        conn.commit()
    finally:
        conn.close()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    FastAPI dependency that yields a database connection.

    Yields:
        sqlite3.Connection: SQLite database connection object.
    """
    db = get_db_connection()
    try:
        yield db
    finally:
        db.close()
