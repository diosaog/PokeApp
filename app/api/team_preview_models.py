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
    timing_status: Literal["on_time", "late", "unknown"] = "unknown"
    team: list[PokemonRead] = Field(min_length=6, max_length=6)


class SelfPreviewLock(BaseModel):
    locked_at: datetime
    is_late: bool
    timing_status: Literal["on_time", "late", "unknown"] = "unknown"
    team: list[PrivatePokemonRead] = Field(min_length=6, max_length=6)


# 079: why a trainer shows neither an official lock nor a provisional team.
UnavailableReason = Literal[
    "no_team_lock",  # finished season: only official locks are history
    "no_linked_save",
    "no_synced_save",
    "processing",
    "unsupported_payload",
    "ineligible_personal_save",
    "empty_party",
]


class PublicProvisionalTeam(BaseModel):
    """Current synchronized party, NOT a Team Lock (public projection only)."""

    source: Literal["league", "personal"]
    team: list[PokemonRead] = Field(min_length=1, max_length=6)


class SelfProvisionalTeam(BaseModel):
    source: Literal["league", "personal"]
    team: list[PrivatePokemonRead] = Field(min_length=1, max_length=6)


def _one_source(entry):
    if entry.lock is not None and (entry.provisional is not None or entry.unavailable_reason):
        raise ValueError("An official lock is never mixed with a provisional team")
    if entry.lock is None and (entry.provisional is None) == (entry.unavailable_reason is None):
        raise ValueError("A missing lock has exactly one provisional team or reason")
    return entry


class PublicPreviewTeam(BaseModel):
    trainer_id: UUID
    visibility: Literal["public"] = "public"
    lock: PublicPreviewLock | None
    provisional: PublicProvisionalTeam | None = None
    unavailable_reason: UnavailableReason | None = None

    @model_validator(mode="after")
    def one_source(self):
        return _one_source(self)


class SelfPreviewTeam(BaseModel):
    trainer_id: UUID
    visibility: Literal["self"] = "self"
    lock: SelfPreviewLock | None
    provisional: SelfProvisionalTeam | None = None
    unavailable_reason: UnavailableReason | None = None

    @model_validator(mode="after")
    def one_source(self):
        return _one_source(self)


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
