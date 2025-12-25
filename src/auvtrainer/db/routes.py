from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from .database import get_db
from .schemas import InputCreate, InputRead, OutputCreate, OutputRead

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
async def count_table_rows(
    table_name: str, db: sqlite3.Connection = Depends(get_db)
) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(f'SELECT COUNT(*) AS cnt FROM "{table_name}";')
    return {"table": table_name, "row_count": int(cur.fetchone()[0])}


@router.get("/tables/{table_name}/schema")
async def get_table_schema(
    table_name: str, db: sqlite3.Connection = Depends(get_db)
) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(f'PRAGMA table_info("{table_name}");')
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
    cur.execute(f'SELECT * FROM "{table_name}";')
    rows = _rows_to_dicts(cur.fetchall())
    return {"table": table_name, "rows": rows}


@router.get("/tables/{table_name}/get/newest")
async def get_newest_row(
    table_name: str, db: sqlite3.Connection = Depends(get_db)
) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(f'SELECT * FROM "{table_name}" ORDER BY id DESC LIMIT 1;')
    row = cur.fetchone()
    return {"table": table_name, "newest_row": (dict(row) if row else None)}


@router.get("/tables/{table_name}/get/oldest")
async def get_oldest_row(
    table_name: str, db: sqlite3.Connection = Depends(get_db)
) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(f'SELECT * FROM "{table_name}" ORDER BY id ASC LIMIT 1;')
    row = cur.fetchone()
    return {"table": table_name, "oldest_row": (dict(row) if row else None)}


@router.post("/tables/{table_name}/delete/oldest")
async def delete_oldest_row(
    table_name: str, db: sqlite3.Connection = Depends(get_db)
) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(
        f"""
        DELETE FROM "{table_name}"
        WHERE id = (SELECT id FROM "{table_name}" ORDER BY id ASC LIMIT 1);
        """
    )
    db.commit()
    return {"table": table_name, "deleted": cur.rowcount}


@router.post("/tables/{table_name}/delete/newest")
async def delete_newest_row(
    table_name: str, db: sqlite3.Connection = Depends(get_db)
) -> dict[str, Any]:
    _ensure_table_exists(db, table_name)
    cur = db.cursor()
    cur.execute(
        f"""
        DELETE FROM "{table_name}"
        WHERE id = (SELECT id FROM "{table_name}" ORDER BY id DESC LIMIT 1);
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
    cur.execute(f'DELETE FROM "{table_name}" WHERE id IN ({placeholders});', tuple(row_ids))
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

    cur = db.cursor()
    cur.execute(f'PRAGMA table_info("{table_name}");')
    valid_cols = {r[1] for r in cur.fetchall()}
    bad_cols = [c for c in row_data.keys() if c not in valid_cols]
    if bad_cols:
        raise HTTPException(
            status_code=400, detail=f"Invalid columns for '{table_name}': {bad_cols}"
        )

    cols = ", ".join(f'"{c}"' for c in row_data.keys())
    placeholders = ", ".join("?" for _ in row_data)
    values = tuple(row_data.values())

    cur.execute(f'INSERT INTO "{table_name}" ({cols}) VALUES ({placeholders});', values)
    db.commit()
    return {"table": table_name, "status": "row added", "id": cur.lastrowid}


# =========================
# Typed endpoints (inputs)
# =========================


@router.post("/inputs", response_model=InputRead)
async def create_input(payload: InputCreate, db: sqlite3.Connection = Depends(get_db)) -> InputRead:
    cur = db.cursor()
    cur.execute(
        """
        INSERT INTO inputs (x, y, z, yaw, arm)
        VALUES (?, ?, ?, ?, ?);
        """,
        (payload.x, payload.y, payload.z, payload.yaw, int(payload.arm)),
    )
    db.commit()

    new_id = int(cur.lastrowid)
    cur.execute("SELECT id, x, y, z, yaw, arm FROM inputs WHERE id = ?;", (new_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to read created input row")

    d = dict(row)
    d["arm"] = bool(d["arm"])
    return InputRead(**d)


@router.get("/inputs/{input_id}", response_model=InputRead)
async def get_input(input_id: int, db: sqlite3.Connection = Depends(get_db)) -> InputRead:
    cur = db.cursor()
    cur.execute("SELECT id, x, y, z, yaw, arm FROM inputs WHERE id = ?;", (input_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"inputs row {input_id} not found")

    d = dict(row)
    d["arm"] = bool(d["arm"])
    return InputRead(**d)


@router.get("/inputs", response_model=list[InputRead])
async def list_inputs(
    limit: int = 100, db: sqlite3.Connection = Depends(get_db)
) -> list[InputRead]:
    limit = max(1, min(limit, 1000))
    cur = db.cursor()
    cur.execute(
        """
        SELECT id, x, y, z, yaw, arm
        FROM inputs
        ORDER BY id DESC
        LIMIT ?;
        """,
        (limit,),
    )
    rows = cur.fetchall()
    out: list[InputRead] = []
    for r in rows:
        d = dict(r)
        d["arm"] = bool(d["arm"])
        out.append(InputRead(**d))
    return out


# ==========================
# Typed endpoints (outputs)
# ==========================


@router.post("/outputs", response_model=OutputRead)
async def create_output(
    payload: OutputCreate, db: sqlite3.Connection = Depends(get_db)
) -> OutputRead:
    # Ensure inputs_id exists
    cur = db.cursor()
    cur.execute("SELECT 1 FROM inputs WHERE id = ?;", (payload.inputs_id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=400, detail=f"inputs_id {payload.inputs_id} does not exist")

    cur.execute(
        """
        INSERT INTO outputs (inputs_id, m1, m2, m3, m4, m5, m6, m7, m8)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            payload.inputs_id,
            payload.m1,
            payload.m2,
            payload.m3,
            payload.m4,
            payload.m5,
            payload.m6,
            payload.m7,
            payload.m8,
        ),
    )
    db.commit()

    new_id = int(cur.lastrowid)
    cur.execute(
        """
        SELECT id, inputs_id, m1, m2, m3, m4, m5, m6, m7, m8
        FROM outputs
        WHERE id = ?;
        """,
        (new_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=500, detail="Failed to read created output row")

    return OutputRead(**dict(row))


@router.get("/outputs/{output_id}", response_model=OutputRead)
async def get_output(output_id: int, db: sqlite3.Connection = Depends(get_db)) -> OutputRead:
    cur = db.cursor()
    cur.execute(
        """
        SELECT id, inputs_id, m1, m2, m3, m4, m5, m6, m7, m8
        FROM outputs
        WHERE id = ?;
        """,
        (output_id,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"outputs row {output_id} not found")

    return OutputRead(**dict(row))


@router.get("/outputs", response_model=list[OutputRead])
async def list_outputs(
    limit: int = 100, db: sqlite3.Connection = Depends(get_db)
) -> list[OutputRead]:
    limit = max(1, min(limit, 1000))
    cur = db.cursor()
    cur.execute(
        """
        SELECT id, inputs_id, m1, m2, m3, m4, m5, m6, m7, m8
        FROM outputs
        ORDER BY id DESC
        LIMIT ?;
        """,
        (limit,),
    )
    return [OutputRead(**dict(r)) for r in cur.fetchall()]


@router.get("/pairs/{input_id}", response_model=dict[str, Any])
async def get_input_output_pair(
    input_id: int, db: sqlite3.Connection = Depends(get_db)
) -> dict[str, Any]:
    """
    Convenience endpoint: fetch InputRead plus the newest OutputRead that references it.
    """
    cur = db.cursor()

    cur.execute("SELECT id, x, y, z, yaw, arm FROM inputs WHERE id = ?;", (input_id,))
    input_row = cur.fetchone()
    if input_row is None:
        raise HTTPException(status_code=404, detail=f"inputs row {input_id} not found")
    input_d = dict(input_row)
    input_d["arm"] = bool(input_d["arm"])

    cur.execute(
        """
        SELECT id, inputs_id, m1, m2, m3, m4, m5, m6, m7, m8
        FROM outputs
        WHERE inputs_id = ?
        ORDER BY id DESC
        LIMIT 1;
        """,
        (input_id,),
    )
    out_row = cur.fetchone()

    return {
        "input": InputRead(**input_d),
        "output": (OutputRead(**dict(out_row)) if out_row else None),
    }
