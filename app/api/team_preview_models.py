"""Dedicated Team Lock projections; never carry live save or identity evidence."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.read_models import DayRead, PokemonRead, PrivatePokemonRead, SeasonRead


class TeamPreviewQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["spectator", "battle"] = "spectator"
    trainer_id: UUID | None = None
    second_trainer_id: UUID | None = None

    @model_validator(mode="after")
    def valid_selection(self):
        if self.second_trainer_id is not None and (
            self.mode != "spectator"
            or self.trainer_id is None
            or self.trainer_id == self.second_trainer_id
        ):
            raise ValueError("Select distinct trainers in spectator mode")
        return self


class PreviewTrainer(BaseModel):
    trainer_id: UUID
    display_name: str
    status: str


class PublicPreviewLock(BaseModel):
    locked_at: datetime
    is_late: bool
    team: list[PokemonRead] = Field(min_length=6, max_length=6)


class SelfPreviewLock(BaseModel):
    locked_at: datetime
    is_late: bool
    team: list[PrivatePokemonRead] = Field(min_length=6, max_length=6)


class PublicPreviewTeam(BaseModel):
    trainer_id: UUID
    visibility: Literal["public"] = "public"
    lock: PublicPreviewLock | None


class SelfPreviewTeam(BaseModel):
    trainer_id: UUID
    visibility: Literal["self"] = "self"
    lock: SelfPreviewLock | None


class TeamPreviewRead(BaseModel):
    season: SeasonRead
    day: DayRead | None
    trainers: list[PreviewTrainer] = Field(max_length=500)
    mode: Literal["spectator", "battle"]
    teams: list[
        Annotated[
            PublicPreviewTeam | SelfPreviewTeam, Field(discriminator="visibility")
        ]
    ] = Field(max_length=2)
