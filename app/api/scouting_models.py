"""Explicit competitive scouting allowlist; no private/save or timing evidence."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.read_models import DayRead, SeasonRead
from app.api.team_preview_models import PreviewTrainer


class ScoutingQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trainer_id: UUID | None = None


class ScoutingMove(BaseModel):
    name: str


class ScoutingPokemon(BaseModel):
    species: str
    nickname: str = ""
    level: int | None = Field(default=None, ge=1, le=100)
    types: list[str] = Field(default_factory=list)
    item: str = ""
    moves: list[ScoutingMove] = Field(default_factory=list)


class ScoutingRead(BaseModel):
    season: SeasonRead
    day: DayRead | None
    trainers: list[PreviewTrainer] = Field(max_length=500)
    trainer_id: UUID | None
    team: list[ScoutingPokemon] | None = Field(min_length=6, max_length=6)
