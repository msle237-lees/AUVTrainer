from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from .database import get_db

router = APIRouter(prefix="/db", tags=["db"])


def _list_tables(db: sqlite3.Connection) -> list[str]:
    cur = db.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    return [r[0] for r in cur.fetchall()]


def _ensure_table_exists(db: sqlite3.Connection, table_name: str) -> None:
    if table_name not in _list_tables(db):
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


@router.get("/status")
async def get_status() -> dict[str, str]:
    return {"status": "Database service is running"}


@router.get("/tables")
async def list_tables(db: sqlite3.Connection = Depends(get_db)) -> dict[str, list[str]]:
    return {"tables": _list_tables(db)}


@router.get("/tables/{table_name}/count")
async def count_table_rows(table_name: str, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(f"SELECT COUNT(*) AS cnt FROM \"{table_name}\";")
    return {"table": table_name, "row_count": int(cur.fetchone()[0])}


@router.get("/tables/{table_name}/schema")
async def get_table_schema(table_name: str, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(f"PRAGMA table_info(\"{table_name}\");")
    # PRAGMA table_info returns tuples -> make them dicts for readability
    cols = []
    for cid, name, ctype, notnull, dflt_value, pk in cur.fetchall():
        cols.append(
            {
                "cid": cid,
                "name": name,
                "type": ctype,
                "notnull": bool(notnull),
                "default": dflt_value,
                "pk": bool(pk),
            }
        )
    return {"table": table_name, "schema": cols}


@router.get("/tables/{table_name}/get_all")
async def get_all_rows(table_name: str, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(f"SELECT * FROM \"{table_name}\";")
    rows = _rows_to_dicts(cur.fetchall())
    return {"table": table_name, "rows": rows}


@router.get("/tables/{table_name}/get/newest")
async def get_newest_row(table_name: str, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(f"SELECT * FROM \"{table_name}\" ORDER BY rowid DESC LIMIT 1;")
    row = cur.fetchone()
    return {"table": table_name, "newest_row": (dict(row) if row else None)}


@router.get("/tables/{table_name}/get/oldest")
async def get_oldest_row(table_name: str, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(f"SELECT * FROM \"{table_name}\" ORDER BY rowid ASC LIMIT 1;")
    row = cur.fetchone()
    return {"table": table_name, "oldest_row": (dict(row) if row else None)}


@router.post("/tables/{table_name}/delete/oldest")
async def delete_oldest_row(table_name: str, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(
        f"""
        DELETE FROM "{table_name}"
        WHERE rowid = (SELECT rowid FROM "{table_name}" ORDER BY rowid ASC LIMIT 1);
        """
    )
    db.commit()
    return {"table": table_name, "deleted": cur.rowcount}


@router.post("/tables/{table_name}/delete/newest")
async def delete_newest_row(table_name: str, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(
        f"""
        DELETE FROM "{table_name}"
        WHERE rowid = (SELECT rowid FROM "{table_name}" ORDER BY rowid DESC LIMIT 1);
        """
    )
    db.commit()
    return {"table": table_name, "deleted": cur.rowcount}


@router.post("/tables/{table_name}/delete/selection")
async def delete_selected_rows(
    table_name: str,
    row_ids: list[int] = Body(..., embed=True),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    if not row_ids:
        return {"table": table_name, "deleted": 0}

    placeholders = ", ".join("?" for _ in row_ids)
    cur = db.cursor()
    cur.execute(f'DELETE FROM "{table_name}" WHERE rowid IN ({placeholders});', tuple(row_ids))
    db.commit()
    return {"table": table_name, "deleted": cur.rowcount}


@router.post("/tables/{table_name}/clear")
async def clear_table(table_name: str, db: sqlite3.Connection = Depends(get_db)) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(f'DELETE FROM "{table_name}";')
    db.commit()
    return {"table": table_name, "deleted": cur.rowcount}


@router.post("/tables/{table_name}/append")
async def append_row(
    table_name: str,
    row_data: dict[str, Any] = Body(...),
    db: sqlite3.Connection = Depends(get_db),
) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    if not row_data:
        raise HTTPException(status_code=400, detail="row_data cannot be empty")

    # Validate columns exist in target table
    cur = db.cursor()
    cur.execute(f'PRAGMA table_info("{table_name}");')
    valid_cols = {r[1] for r in cur.fetchall()}
    bad_cols = [c for c in row_data.keys() if c not in valid_cols]
    if bad_cols:
        raise HTTPException(status_code=400, detail=f"Invalid columns for '{table_name}': {bad_cols}")

    cols = ", ".join(f'"{c}"' for c in row_data.keys())
    placeholders = ", ".join("?" for _ in row_data)
    values = tuple(row_data.values())

    cur.execute(f'INSERT INTO "{table_name}" ({cols}) VALUES ({placeholders});', values)
    db.commit()
    return {"table": table_name, "status": "row added", "rowid": cur.lastrowid}
