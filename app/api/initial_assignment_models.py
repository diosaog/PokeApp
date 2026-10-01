"""Observed first-leg readiness; no caller-supplied progress or death totals."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, model_validator

from app.api.matchday_models import TieResolution
from app.api.season_admin_models import DivisionSizes, Revision, StrictBody

InitialRule = Literal["observed_deaths_v1"]
Digest = Annotated[str, Field(strict=True, pattern=r"^[0-9a-f]{64}$")]
BlockReason = Literal[
    "season_not_active",
    "invalid_roster",
    "config_not_effective",
    "progress_unobserved",
    "cap_not_reached",
    "death_inputs_unobserved",
    "initial_assignment_locked",
    "initial_assignment_legacy",
]


class InitialAssignmentPlayer(StrictBody):
    id: UUID
    trainer_id: UUID
    display_name: Annotated[str, Field(strict=True, max_length=512)]
    progress_state: Literal["observed", "unknown"]
    observed_badges: Annotated[int, Field(strict=True, ge=0, le=8)] | None
    cap_reached: Annotated[bool, Field(strict=True)]
    adjusted_deaths: Revision | None
    proposed_division: Literal["A", "B"] | None = None

    @model_validator(mode="after")
    def observation_consistency(self):
        if (self.progress_state == "unknown") != (self.observed_badges is None):
            raise ValueError("Invalid observation state")
        if self.cap_reached and (
            self.observed_badges is None or self.observed_badges < 2
        ):
            raise ValueError("Invalid cap evidence")
        return self


class InitialBoundaryTie(StrictBody):
    player_ids: Annotated[list[UUID], Field(min_length=2, max_length=500)]
    adjusted_deaths: Revision
    places_in_a: Annotated[int, Field(strict=True, gt=0)]

    @model_validator(mode="after")
    def valid_group(self):
        if len(set(self.player_ids)) != len(self.player_ids) or self.places_in_a >= len(
            self.player_ids
        ):
            raise ValueError("Invalid boundary")
        return self


class InitialAssignmentRead(StrictBody):
    season_id: UUID
    rule: InitialRule | None
    state: Literal["legacy", "pending", "assigned"]
    config_version_id: UUID | None
    division_sizes: DivisionSizes | None
    setup_revision: Revision
    roster_revision: Revision
    input_hash: Digest
    ready: Annotated[bool, Field(strict=True)]
    blocking_reasons: Annotated[list[BlockReason], Field(max_length=8)]
    players: Annotated[list[InitialAssignmentPlayer], Field(max_length=500)]
    boundary_tie: InitialBoundaryTie | None = None

    @model_validator(mode="after")
    def validate_scope_and_readiness(self):
        ids = [p.id for p in self.players]
        if len(set(ids)) != len(ids) or len(
            {p.trainer_id for p in self.players}
        ) != len(ids):
            raise ValueError("Duplicate roster")
        if (self.state == "legacy") != (self.rule is None):
            raise ValueError("Invalid rule state")
        if self.ready and (
            self.state != "pending"
            or self.blocking_reasons
            or self.config_version_id is None
            or self.division_sizes is None
            or self.division_sizes.A + self.division_sizes.B != len(ids)
            or any(not p.cap_reached or p.adjusted_deaths is None for p in self.players)
        ):
            raise ValueError("Invalid readiness")
        if self.boundary_tie and (
            not self.ready or not set(self.boundary_tie.player_ids).issubset(ids)
        ):
            raise ValueError("Invalid boundary scope")
        return self


class FinalizeInitialAssignmentBody(StrictBody):
    config_version_id: UUID
    expected_setup_revision: Revision
    expected_roster_revision: Revision
    input_hash: Digest
    tie_resolution: TieResolution | None = None
