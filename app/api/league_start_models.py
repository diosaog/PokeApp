"""Ordinary League start (079): readiness, J1 preparation, own death history.

Every value is server-observed. The caller never supplies an authority, a
target trainer or a death count of their choosing.
"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from app.api.season_admin_models import Revision, StrictBody

Sha256 = Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
DayStatus = Literal["scheduled", "open", "closed", "cancelled"]
SeasonReason = Literal[
    "season_not_active",
    "matchday_unavailable",
    "matchday_already_prepared",
    "initial_assignment_required",
    "initial_setup_locked",
    "invalid_roster",
    "opponent_missing",
    "config_not_effective",
]
TrainerReason = Literal[
    "trainer_disabled",
    "save_missing",
    "progress_unobserved",
    "badges_missing",
    "death_history_baseline_required",
    "death_history_source_unavailable",
    "death_history_wipe_state_unavailable",
    "death_history_dead_box_changed",
    "death_history_observation_gap",
    "death_history_wipe_reconciliation_required",
    "death_history_unmapped_revival",
    "death_history_inconsistent",
]


class ReadinessMatchday(BaseModel):
    id: UUID
    number: Annotated[int, Field(ge=1)]
    status: DayStatus
    revision: Revision


class ReadinessParticipant(BaseModel):
    season_player_id: UUID
    trainer_id: UUID
    display_name: Annotated[str, Field(max_length=512)]
    reasons: Annotated[list[TrainerReason], Field(max_length=16)]
    # The trainer can resolve the death-history reason themselves (own profile).
    self_confirmable: bool


class LeagueReadinessRead(BaseModel):
    """What opening the next matchday needs, as the server would decide it."""

    season_id: UUID
    state: Literal["unprepared", "scheduled", "open", "completed", "finished", "unavailable"]
    structure: Literal["all_vs_all", "divisions", "legacy"]
    matchday: ReadinessMatchday | None
    next_number: Annotated[int, Field(ge=1)] | None
    can_prepare: bool
    can_open: bool
    # The viewer may operate the League (active participant or administrator).
    can_operate: bool
    reasons: Annotated[list[SeasonReason], Field(max_length=16)]
    participants: Annotated[list[ReadinessParticipant], Field(max_length=500)]

    @model_validator(mode="after")
    def consistent(self):
        if self.state in ("scheduled", "open") and (
            self.matchday is None or self.matchday.status != self.state
        ):
            raise ValueError("Inconsistent readiness state")
        if self.state == "unprepared" and self.matchday is not None:
            raise ValueError("An unprepared League has no matchday")
        if self.can_open and (
            self.state not in ("unprepared", "scheduled") or self.reasons
            or any(p.reasons for p in self.participants)
        ):
            raise ValueError("Readiness cannot be both open-able and blocked")
        if self.can_prepare and self.state != "unprepared":
            raise ValueError("Only an unprepared League can be prepared")
        return self


class FirstMatchdayRead(BaseModel):
    season_id: UUID
    matchday_id: UUID
    number: Annotated[int, Field(ge=1)]
    status: DayStatus
    revision: Revision
    # False when it already existed (prepared earlier, by anyone): idempotent.
    created: bool


class DeathCounts(StrictBody):
    actual_deaths: Revision
    wipe_deaths: Revision
    segment_deaths: Revision


class OwnDeathHistoryBody(DeathCounts):
    """Confirms exactly the observed values the trainer was shown."""

    expected_revision: Revision
    source_sha256: Sha256

    @model_validator(mode="after")
    def consistent_counts(self):
        if self.wipe_deaths > self.actual_deaths or self.segment_deaths > self.actual_deaths:
            raise ValueError("Historical death counts are inconsistent")
        return self


class OwnDeathHistoryRead(BaseModel):
    season_id: UUID
    season_player_id: UUID
    trainer_id: UUID
    revision: Revision
    known: bool
    blocking_reason: str | None
    actual_deaths: Revision | None
    wipe_deaths: Revision | None
    segment_deaths: Revision | None
    dead_box_number: Annotated[int, Field(ge=1, le=32)]
    source_sha256: Sha256 | None
    confirmed_at: datetime | None
    current_matchday_id: UUID | None
    can_confirm: bool
    confirm_blocker: Literal[
        "death_history_confirmed", "save_missing", "death_history_closed",
        "death_history_pending_sync", "death_history_admin_required",
    ] | None
    proposed: DeathCounts | None
    replayed: bool = False
    resolution_id: UUID | None = None

    @model_validator(mode="after")
    def consistent(self):
        if self.can_confirm != (self.confirm_blocker is None) or self.can_confirm != (self.proposed is not None):
            raise ValueError("Inconsistent confirmation state")
        if self.can_confirm and self.source_sha256 is None:
            raise ValueError("Confirmation has no authoritative save")
        if self.known and None in (self.actual_deaths, self.wipe_deaths):
            raise ValueError("Inconsistent known history")
        return self
