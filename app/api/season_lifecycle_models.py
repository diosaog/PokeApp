"""Explicit lifecycle commands, not a generic season status patch."""

from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator
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


class ChampionshipBattle(StrictBody):
    """A recorded title battle, kept separate from normal League matches."""

    player_a_id: UUID
    player_b_id: UUID
    winner_id: UUID
    played_at: AwareDatetime
    evidence: Reason

    @field_validator("played_at", mode="before")
    @classmethod
    def explicit_recorded_time(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError("A recorded battle requires an explicit timestamp")
        return value

    @field_validator("played_at")
    @classmethod
    def recorded_time(cls, value):
        value = value.astimezone(timezone.utc)
        if value > datetime.now(timezone.utc):
            raise ValueError("A recorded championship battle cannot be in the future")
        return value

    @model_validator(mode="after")
    def valid_outcome(self):
        if self.player_a_id == self.player_b_id or self.winner_id not in (
            self.player_a_id, self.player_b_id
        ):
            raise ValueError("Invalid championship battle outcome")
        return self


class ChampionshipTiebreakBody(LifecycleRevisionBody):
    input_hash: Digest
    method: Literal["total_actual_deaths", "championship_1v1"]
    confirmation: Annotated[bool, Field(strict=True)]
    reason: Reason
    winner_season_player_id: UUID | None = None
    battles: Annotated[list[ChampionshipBattle], Field(min_length=1, max_length=1000)] | None = None

    @field_validator("battles")
    @classmethod
    def canonical_battles(cls, value):
        if value is None:
            return value
        pairs = [tuple(sorted((str(b.player_a_id), str(b.player_b_id)))) for b in value]
        if len(set(pairs)) != len(pairs):
            raise ValueError("Duplicate championship battle pair")
        return [battle for _, battle in sorted(zip(pairs, value), key=lambda pair: pair[0])]

    @model_validator(mode="after")
    def explicit_method(self):
        if self.confirmation is not True:
            raise ValueError("Explicit administrator confirmation is required")
        if self.method == "total_actual_deaths":
            if self.winner_season_player_id is not None or self.battles is not None:
                raise ValueError("Historical deaths are resolved by the authoritative server")
        elif self.winner_season_player_id is None or not self.battles:
            raise ValueError("Recorded championship battles and a winner are required")
        elif self.winner_season_player_id not in {b.winner_id for b in self.battles}:
            raise ValueError("The selected champion must have a recorded battle victory")
        return self


class ArchiveSeasonBody(LifecycleRevisionBody):
    label: Name | None = None


class DiscardSeasonBody(LifecycleRevisionBody):
    reason: Reason
    confirmation: Literal["DISCARD"]


class CancellationPreview(BaseModel):
    """What cancelling a season would leave behind, before confirming it."""

    season_id: UUID
    name: str
    status: str
    allowed: bool
    mode: Literal["clean", "preserving", "unavailable"]
    open_robberies: int
    open_item_uses: int
    participants: int
    matchdays: int
    closed_matchdays: int
    open_matchdays: int
    results: int
    team_locks: int
    purchases: int
    pending_purchases: int
    coin_transactions: int
    coins_awarded: str
    progress_rewards: int
    saves: int
    cups: int
    penalties: int
    trials: int


class SeasonLifecycleReceipt(BaseModel):
    operation_id: UUID
    event_id: UUID
    season_id: UUID
    operation: Literal["finish", "archive", "discard", "championship_bo3", "championship_residual", "championship_tiebreak"]
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
    # Only the frozen, actual historical count is authority for the new title
    # rule. Legacy adjusted penalty units remain a separate compatibility field.
    actual_deaths: Revision | None = None


class ChampionshipRead(StrictBody):
    season_id: UUID
    state: Literal[
        "incomplete",
        "ready",
        "bo3_required",
        "residual_required",
        "owner_decision_required",
        "tiebreak_required",
        "battle_required",
        "frozen",
        "legacy",
    ]
    setup_revision: Revision
    input_hash: Digest | None
    players: Annotated[list[ChampionshipPlayer], Field(max_length=500)]
    tied_player_ids: Annotated[list[UUID], Field(max_length=500)]
    champion_trainer_id: UUID | None
    resolution_type: (
        Literal["unique_points", "championship_bo3", "triple_adjusted_deaths", "multiple_adjusted_deaths", "championship_residual", "total_actual_deaths", "championship_1v1"] | None
    )
    tiebreak_method: Literal["total_actual_deaths", "championship_1v1"] | None = None
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
        if self.state == "residual_required" and (
            len(self.tied_player_ids) < 2 or self.input_hash is None
        ):
            raise ValueError("Invalid residual championship state")
        if self.state in ("tiebreak_required", "battle_required") and (
            len(self.tied_player_ids) < 2 or self.input_hash is None
        ):
            raise ValueError("Invalid championship tiebreak scope")
        if self.state == "battle_required" and self.tiebreak_method != "total_actual_deaths":
            raise ValueError("A required battle must follow the confirmed deaths comparison")
        if self.resolution_type in ("total_actual_deaths", "championship_1v1"):
            if self.tiebreak_method != self.resolution_type:
                raise ValueError("The championship method must match its resolution")
            winner = next(p for p in self.players if p.trainer_id == self.champion_trainer_id)
            if self.tied_player_ids and winner.season_player_id not in self.tied_player_ids:
                raise ValueError("The champion must belong to the reviewed tiebreak candidates")
        return self
