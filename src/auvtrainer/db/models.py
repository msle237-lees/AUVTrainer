from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool = True
    service: str = "API"


class RecordIn(BaseModel):
    """
    Generic record payload.

    `data` is a JSON-encoded string to keep the DB schema dead simple.
    If you prefer structured JSON, store TEXT and validate at the edges.
    """
    data: str = Field(..., description="JSON-encoded payload string")


class RecordOut(BaseModel):
    id: int
    created_at: str
    data: str
