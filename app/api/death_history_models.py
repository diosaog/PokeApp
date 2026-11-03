"""Audited historical death reconciliation, bound to a current parsed save."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.api.season_admin_models import Reason, Revision, StrictBody


class DeathHistoryBody(StrictBody):
    actual_deaths: Revision
    wipe_deaths: Revision
    segment_deaths: Revision
    source_sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    expected_revision: Revision
    reason: Reason
    evidence: Annotated[str, Field(strict=True, min_length=1, max_length=2000)]
    revived_entity_ids: Annotated[list[UUID], Field(max_length=500)] = Field(default_factory=list)
    invalidated_event_ids: Annotated[list[UUID], Field(max_length=500)] = Field(default_factory=list)

    @field_validator("revived_entity_ids", "invalidated_event_ids")
    @classmethod
    def unique_entities(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("Duplicate revived Pokemon")
        return sorted(values, key=str)

    @model_validator(mode="after")
    def consistent_counts(self):
        if self.wipe_deaths > self.actual_deaths or self.segment_deaths > self.actual_deaths:
            raise ValueError("Historical death counts are inconsistent")
        return self


class DeathHistoryEntity(BaseModel):
    pokemon_entity_id: UUID
    currently_dead: bool
    has_recorded_death: bool
    display_name: str | None = None
    species: str | None = None
    nickname: str | None = None


class DeathHistoryRead(BaseModel):
    season_id: UUID
    season_player_id: UUID
    trainer_id: UUID
    revision: int = Field(ge=0)
    known: bool
    blocking_reason: str | None
    actual_deaths: int | None = Field(ge=0)
    wipe_deaths: int | None = Field(ge=0)
    death_penalty_tenths: int | None = Field(ge=0)
    source_save_id: UUID | None
    source_sha256: str | None = Field(pattern=r"^[a-f0-9]{64}$")
    identity_revision_id: UUID | None
    wipe_revision: int | None = Field(ge=0)
    wipe_counter: int | None = Field(ge=0)
    current_matchday_id: UUID | None
    segment_deaths: int | None = Field(ge=0)
    can_reconcile: bool
    recorded_deaths: int = Field(ge=0)
    raw_recorded_deaths: int | None = Field(default=None, ge=0)
    invalidated_event_ids: list[UUID] = Field(default_factory=list)
    observed_dead_entities: list[DeathHistoryEntity]
    replayed: bool = False

    @model_validator(mode="after")
    def valid_evidence(self):
        if (len(set(self.invalidated_event_ids)) != len(self.invalidated_event_ids)
            or (self.raw_recorded_deaths is not None
                and self.raw_recorded_deaths - len(self.invalidated_event_ids) != self.recorded_deaths)):
            raise ValueError("Inconsistent corrected death evidence")
        if self.known and (
            self.actual_deaths is None or self.wipe_deaths is None
            or self.death_penalty_tenths != self.actual_deaths + self.wipe_deaths
            or self.wipe_deaths > self.actual_deaths
        ):
            raise ValueError("Inconsistent known historical evidence")
        if self.can_reconcile and any(value is None for value in (
            self.source_save_id, self.source_sha256, self.identity_revision_id
        )):
            raise ValueError("Reconciliation has no authoritative save identity")
        return self
