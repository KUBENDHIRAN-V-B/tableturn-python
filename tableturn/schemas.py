from datetime import datetime, timezone
from typing import Annotated, Literal
from pydantic import BaseModel, Field, PlainSerializer

Section = Literal["Window", "Garden", "Indoor"]
TableState = Literal["free", "seated", "uncleared"]
PartyState = Literal["waiting", "seated", "left", "cleared"]

def _iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

UtcZ = Annotated[datetime, PlainSerializer(_iso_z, return_type=str)]

class TableOut(BaseModel):
    no: str
    seats: int
    section: Section
    state: TableState
    party_id: str | None = None
    seating_id: str | None = None  # seated and uncleared tables: what the floor's Leave / Clear act on
    seated_minutes: int | None = None

class FloorOut(BaseModel):
    branch: str
    free: int
    tables: list[TableOut]

class JoinIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=60)
    covers: int = Field(..., ge=1, le=20)
    phone: str | None = Field(default=None, pattern=r"^\+[1-9]\d{7,14}$")

class JoinOut(BaseModel):
    party_id: str
    name: str
    covers: int
    position: int
    joined_at: UtcZ
    quoted_minutes: int
    quoted_at: UtcZ

class PartyOut(BaseModel):
    party_id: str
    name: str
    covers: int
    state: PartyState
    position: int
    joined_at: UtcZ
    quoted_minutes: int
    quoted_at: UtcZ
    waited_minutes: int | None = None
    table: str | None = None


class SeatIn(BaseModel):
    party_id: str = Field(..., min_length=2, max_length=12)
    table: str = Field(..., min_length=2, max_length=8)


class SeatOut(BaseModel):
    seating_id: str
    party_id: str
    table: str
    seated_at: UtcZ
    waited_minutes: int


class LeaveOut(BaseModel):
    seating_id: str
    left_at: UtcZ


class ClearOut(BaseModel):
    seating_id: str
    table: str
    turn_minutes: int
    cleared_at: UtcZ
