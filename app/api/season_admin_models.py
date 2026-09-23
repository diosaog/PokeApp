"""Strict public contract for initial season administration, not generic CRUD."""
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Revision = Annotated[int, Field(strict=True, ge=0)]
Positive = Annotated[int, Field(strict=True, gt=0)]
Name = Annotated[str, Field(strict=True, min_length=1, max_length=120)]
Reason = Annotated[str, Field(strict=True, min_length=1, max_length=500)]


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CreateSeasonBody(StrictBody):
    name: Name


class RenameSeasonBody(CreateSeasonBody):
    expected_revision: Revision


class AddParticipantBody(StrictBody):
    trainer_id: UUID
    seed_order: Positive | None = None
    expected_roster_revision: Revision


class RemoveParticipantBody(StrictBody):
    reason: Reason
    expected_roster_revision: Revision


class DivisionSizes(StrictBody):
    A: Positive
    B: Positive


class FunctionalRules(StrictBody):
    team_lock_required: Annotated[bool, Field(strict=True)]
    last_b_gets_steal: Annotated[bool, Field(strict=True)]


class ConfigVersionBody(StrictBody):
    name: Name
    effective_from_matchday: Positive
    total_matchdays: Positive
    division_sizes: DivisionSizes
    movement_count: Revision
    scoring: dict[Annotated[str, Field(pattern=r"^[1-9][0-9]*$")], Revision]
    coin_rewards: dict[Annotated[str, Field(pattern=r"^[1-9][0-9]*$")], Revision]
    rules: FunctionalRules
    expected_config_revision: Revision
    expected_roster_revision: Revision


class ReplaceConfigBody(ConfigVersionBody):
    reason: Reason


class Assignments(StrictBody):
    A: list[UUID]
    B: list[UUID]

    @field_validator("A", "B")
    @classmethod
    def canonical_order(cls, value):
        return sorted(value)


class InitialDivisionsBody(StrictBody):
    config_version_id: UUID
    assignments: Assignments
    expected_roster_revision: Revision
    expected_setup_revision: Revision


class SetupRevisionBody(StrictBody):
    expected_setup_revision: Revision


class AdminReceipt(StrictBody):
    operation_id: UUID
    resource_id: UUID
    season_id: UUID
    event_id: UUID
    replayed: Annotated[bool, Field(strict=True)]
    state: Literal["draft", "active"]
    setup_revision: Revision
    roster_revision: Revision
    config_revision: Revision


class SeasonSummary(StrictBody):
    id: UUID
    name: str
    status: Literal["draft", "active", "finished", "archived", "discarded"]
    started_at: str | None


class ParticipantSummary(StrictBody):
    id: UUID
    trainer_id: UUID
    display_name: str
    status: Literal["active", "retired", "abandoned", "disqualified"]
    seed_order: int | None
    stats_ready: bool
    status_effective_matchday_number: int | None = None


class ConfigSummary(StrictBody):
    id: UUID
    name: str
    version_number: int
    effective_from_matchday: int
    total_matchdays: int
    division_sizes: DivisionSizes | None
    movement_count: int
    scoring: dict[str, int]
    coin_rewards: dict[str, int]
    rules: dict[str, bool]
    roster_revision: int | None
    used: bool
    is_current: bool


class DivisionSummary(StrictBody):
    id: UUID
    code: str
    tier_order: int


class MembershipSummary(StrictBody):
    season_player_id: UUID
    division_id: UUID
    effective_from_matchday: int
    effective_to_matchday: int | None
    reason: str
    eligibility_ends_before_matchday_number: int | None = None


class FirstMatchdaySummary(StrictBody):
    id: UUID
    number: int
    status: str
    config_version_id: UUID
    match_count: int


class ReadinessChecks(StrictBody):
    has_roster: bool
    has_valid_config: bool
    has_initial_divisions: bool
    memberships_complete: bool
    first_matchday_prepared: bool
    match_pairs_complete: bool
    pointer_valid: bool
    no_other_active_season: bool
    is_draft: bool


class Readiness(StrictBody):
    checks: ReadinessChecks
    blocking_reasons: list[str]
    can_activate: bool


class SeasonSetup(StrictBody):
    season: SeasonSummary
    setup_revision: Revision
    roster_revision: Revision
    config_revision: Revision
    current_matchday_id: UUID | None
    participants: list[ParticipantSummary]
    config_versions: list[ConfigSummary]
    divisions: list[DivisionSummary]
    memberships: list[MembershipSummary]
    first_matchday: FirstMatchdaySummary | None
    readiness: Readiness
