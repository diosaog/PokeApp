"""Administración › Avisos contracts (migration 084). Informative, admin-only."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

NoticeStatus = Literal["pending", "reviewed", "justified", "confirmed"]
NoticeSeverity = Literal["alta", "media", "baja"]
NoticeCategory = Literal["pokemon", "objetos", "origen"]


class NoticeStatusBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: NoticeStatus
    note: str = Field(default="", max_length=1000)

    @field_validator("note")
    @classmethod
    def trimmed(cls, value):
        return value.strip()


class SaveAuditChange(BaseModel):
    field: str
    label: str
    kind: str
    before: int | str | bool | list[str] | None = None
    after: int | str | bool | list[str] | None = None
    severity: NoticeSeverity
    reason: str
    item: str | None = None
    category: str | None = None
    delta: int | None = None
    justified: int | None = None
    unjustified: int | None = None
    holders: list[str] = []


class SaveAuditOperation(BaseModel):
    kind: str
    label: str
    at: datetime | None = None
    detail: str = ""


class SaveAuditLocation(BaseModel):
    source: Literal["party", "box"]
    box: int
    slot: int


class SaveAuditPokemon(BaseModel):
    key: str
    species: str
    form: int | None = None
    nickname: str = ""
    level: int | None = None
    gender: str | None = None
    shiny: bool = False
    is_egg: bool = False
    location: SaveAuditLocation
    previous_location: SaveAuditLocation | None = None
    previous_species: str | None = None
    item: str | None = None


class SaveAuditSide(BaseModel):
    save_file_id: UUID
    sha256: str
    uploaded_at: datetime
    revision: int


class SaveAuditComparison(BaseModel):
    previous: SaveAuditSide
    current: SaveAuditSide
    inventory_status: str


class SaveAuditEvent(BaseModel):
    at: datetime
    actor: str | None = None
    from_status: NoticeStatus
    to_status: NoticeStatus
    note: str = ""


class SaveAuditNotice(BaseModel):
    id: UUID
    trainer_id: UUID
    display_name: str
    game: str
    detected_at: datetime
    updated_at: datetime
    category: NoticeCategory
    severity: NoticeSeverity
    status: NoticeStatus
    title: str
    summary: str
    origin: str
    pokemon: SaveAuditPokemon | None = None
    changes: list[SaveAuditChange]
    operations: list[SaveAuditOperation]
    compared: SaveAuditComparison | None = None
    detector_version: int
    events: list[SaveAuditEvent]
    replayed: bool | None = None


class SaveAuditTrainer(BaseModel):
    trainer_id: UUID
    display_name: str


class SaveAuditOverview(BaseModel):
    season_id: UUID
    season_status: str
    activated_at: datetime
    pending_saves: int
    analyzed_saves: int
    last_analyzed_at: datetime | None = None
    trainers: list[SaveAuditTrainer]
    notices: list[SaveAuditNotice]


class SaveAuditSummary(BaseModel):
    season_id: UUID
    pending: int
    pending_high: int


class SaveAuditRunResult(BaseModel):
    processed: int
    failed: int
    busy: bool
    pending_saves: int
