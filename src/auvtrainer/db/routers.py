from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from .database import DatabaseManager
from .deps import get_dbm
from .models import HealthResponse, RecordIn, RecordOut

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(ok=True, service="API")


@router.post("/records", response_model=RecordOut, status_code=status.HTTP_201_CREATED)
async def create_record(payload: RecordIn, dbm: DatabaseManager = Depends(get_dbm)) -> RecordOut:
    new_id = await dbm.execute("INSERT INTO records (data) VALUES (?);", (payload.data,))
    row = await dbm.fetch_one("SELECT id, created_at, data FROM records WHERE id = ?;", (new_id,))
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create record.")
    return RecordOut(**row)


@router.get("/records/{record_id}", response_model=RecordOut)
async def get_record(record_id: int, dbm: DatabaseManager = Depends(get_dbm)) -> RecordOut:
    row = await dbm.fetch_one("SELECT id, created_at, data FROM records WHERE id = ?;", (record_id,))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")
    return RecordOut(**row)


@router.get("/records", response_model=list[RecordOut])
async def list_records(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    dbm: DatabaseManager = Depends(get_dbm),
) -> list[RecordOut]:
    rows = await dbm.fetch_many(
        "SELECT id, created_at, data FROM records ORDER BY id DESC LIMIT ? OFFSET ?;",
        (limit, offset),
    )
    return [RecordOut(**r) for r in rows]


@router.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_record(record_id: int, dbm: DatabaseManager = Depends(get_dbm)) -> None:
    existing = await dbm.fetch_one("SELECT id FROM records WHERE id = ?;", (record_id,))
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found.")

    await dbm.execute("DELETE FROM records WHERE id = ?;", (record_id,))
    return None
