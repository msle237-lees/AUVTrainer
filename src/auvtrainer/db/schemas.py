from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class InputCreate(BaseModel):
    """
    Payload used to create a new row in the `inputs` table.
    """

    x: int = Field(..., description="X axis input")
    y: int = Field(..., description="Y axis input")
    z: int = Field(..., description="Z axis input")
    yaw: int = Field(..., description="Yaw input")
    arm: bool = Field(..., description="Arm input (True/False)")


class InputRead(InputCreate):
    """
    API representation of an input row returned from the DB.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Auto-incrementing primary key")


class OutputCreate(BaseModel):
    """
    Payload used to create a new row in the `outputs` table.
    """

    inputs_id: int = Field(..., description="FK to inputs.id")

    m1: int
    m2: int
    m3: int
    m4: int
    m5: int
    m6: int
    m7: int
    m8: int


class OutputRead(OutputCreate):
    """
    API representation of an output row returned from the DB.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Auto-incrementing primary key")
