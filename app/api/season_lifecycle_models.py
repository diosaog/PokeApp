"""Explicit lifecycle commands, not a generic season status patch."""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator
from app.api.season_admin_models import StrictBody, Revision, Reason, Name


Digest = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
ExactPoints = Annotated[str, Field(strict=True, pattern=r"^-?[0-9]+(?:\.[0-9]+)?$")]


class LifecycleRevisionBody(StrictBody):
    expected_revision: Revision


class FinishSeasonBody(LifecycleRevisionBody):
    # Hashless bodies may replay a successful pre-F receipt, but SQL rejects
    # every new finish without a current championship fingerprint.
    input_hash: Digest | None = None


class ChampionshipBo3Body(FinishSeasonBody):
    input_hash: Digest
    winner_season_player_id: UUID
    reason: Reason


class ArchiveSeasonBody(LifecycleRevisionBody):
    label: Name | None = None


class DiscardSeasonBody(LifecycleRevisionBody):
    reason: Reason
    confirmation: Literal["DISCARD"]


class SeasonLifecycleReceipt(BaseModel):
    operation_id: UUID
    event_id: UUID
    season_id: UUID
    operation: Literal["finish", "archive", "discard", "championship_bo3"]
    state: Literal["finished", "archived", "discarded", "active"]
    actor_trainer_id: UUID
    changed_at: datetime
    setup_revision: Revision
    current_matchday_id: UUID | None
    archive_id: UUID | None
    hall_id: UUID | None
    replayed: bool


class ChampionshipPlayer(StrictBody):
    season_player_id: UUID
    trainer_id: UUID
    display_name: Annotated[str, Field(strict=True, max_length=512)]
    total_points: ExactPoints
    adjusted_deaths: Revision | None


class ChampionshipRead(StrictBody):
    season_id: UUID
    state: Literal[
        "incomplete",
        "ready",
        "bo3_required",
        "owner_decision_required",
        "frozen",
        "legacy",
    ]
    setup_revision: Revision
    input_hash: Digest | None
    players: Annotated[list[ChampionshipPlayer], Field(max_length=500)]
    tied_player_ids: Annotated[list[UUID], Field(max_length=500)]
    champion_trainer_id: UUID | None
    resolution_type: (
        Literal["unique_points", "championship_bo3", "triple_adjusted_deaths"] | None
    )
    finalist_status: Literal["OWNER_DECISION_REQUIRED"]
    blocking_reason: Annotated[str, Field(strict=True, max_length=200)] | None

    @model_validator(mode="after")
    def validate_scope(self):
        ids = [p.season_player_id for p in self.players]
        trainers = [p.trainer_id for p in self.players]
        if len(set(ids)) != len(ids) or len(set(trainers)) != len(trainers):
            raise ValueError("Duplicate championship participants")
        if len(set(self.tied_player_ids)) != len(self.tied_player_ids) or not set(
            self.tied_player_ids
        ).issubset(ids):
            raise ValueError("Invalid championship tie scope")
        if (
            self.champion_trainer_id is not None
            and self.champion_trainer_id not in trainers
        ):
            raise ValueError("Invalid championship winner scope")
        if self.state in ("ready", "frozen") and (
            self.champion_trainer_id is None
            or self.resolution_type is None
            or self.input_hash is None
        ):
            raise ValueError("Missing championship certification")
        if self.state not in ("ready", "frozen") and (
            self.champion_trainer_id is not None or self.resolution_type is not None
        ):
            raise ValueError("Unresolved championship cannot name a winner")
        if self.state == "bo3_required" and (
            len(self.tied_player_ids) != 2 or self.input_hash is None
        ):
            raise ValueError("Invalid championship BO3 state")
        return self
