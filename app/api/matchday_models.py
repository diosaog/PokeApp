from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator
from app.api.season_admin_models import StrictBody, Revision, Reason


class OpenDayBody(StrictBody):
    expected_revision: Revision


class CancelDayBody(OpenDayBody):
    reason: Reason


class MatchResult(StrictBody):
    match_id: UUID
    winner_season_player_id: UUID | None


class ResultsBody(StrictBody):
    expected_results_revision: Revision
    results: Annotated[list[MatchResult], Field(min_length=1, max_length=1000)]

    @field_validator("results")
    @classmethod
    def unique(cls, results):
        if len({r.match_id for r in results}) != len(results):
            raise ValueError("Duplicate match")
        return sorted(results, key=lambda r: str(r.match_id))


class CloseDayBody(StrictBody):
    expected_results_revision: Revision
    tie_resolution: "TieResolution | None" = None


class ParticipantCloseDayBody(StrictBody):
    expected_results_revision: Revision
    tie_resolution: "TieResolution | None" = None


class CorrectDayBody(StrictBody):
    expected_snapshot_revision: Annotated[int, Field(strict=True, gt=0)]
    reason: Reason
    results: Annotated[list[MatchResult], Field(min_length=1, max_length=1000)]
    tie_resolution: "TieResolution | None" = None

    @field_validator("results")
    @classmethod
    def complete_winners(cls, results):
        if any(r.winner_season_player_id is None for r in results):
            raise ValueError("Correction requires winners")
        return ResultsBody.unique(results)


class DayReceipt(BaseModel):
    operation_id: UUID
    season_id: UUID
    matchday_id: UUID
    event_id: UUID
    state: Literal["scheduled", "open", "closed"]
    revision: Revision
    results_revision: Revision
    snapshot_revision: Revision
    current_matchday_id: UUID
    replayed: bool


class DayMatch(BaseModel):
    id: UUID
    player_a_id: UUID
    player_b_id: UUID
    winner_id: UUID | None


class DayState(BaseModel):
    season_id: UUID
    matchday_id: UUID
    current_matchday_id: UUID
    state: Literal["scheduled", "open", "closed", "cancelled"]
    revision: Revision
    results_revision: Revision
    snapshot_revision: Revision
    matches: list[DayMatch]


class TieBattle(StrictBody):
    """An extra ranking battle, never a normal League match or a point award."""

    player_a_id: UUID
    player_b_id: UUID
    winner_id: UUID
    played_at: AwareDatetime
    evidence: Reason

    @model_validator(mode="after")
    def valid_participants(self):
        if self.player_a_id == self.player_b_id or self.winner_id not in (
            self.player_a_id, self.player_b_id
        ):
            raise ValueError("Invalid tiebreak battle outcome")
        return self


class TieOrder(StrictBody):
    player_ids: Annotated[list[UUID], Field(min_length=2, max_length=500)]
    reason: Reason
    # None preserves historical receipt bodies. New scoring requires played,
    # auditable extra battles; an administrative order alone is insufficient.
    battles: Annotated[list[TieBattle], Field(min_length=1, max_length=1000)] | None = None

    @field_validator("player_ids")
    @classmethod
    def unique_players(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Duplicate participant in resolution")
        return value

    @field_validator("battles")
    @classmethod
    def canonical_battles(cls, value):
        if value is None:
            return value
        return sorted(value, key=lambda b: sorted((str(b.player_a_id), str(b.player_b_id))))


class TieResolution(StrictBody):
    input_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    orders: Annotated[list[TieOrder], Field(min_length=1, max_length=250)]

    @field_validator("orders")
    @classmethod
    def canonical_groups(cls, value):
        groups = [frozenset(order.player_ids) for order in value]
        if len(set(groups)) != len(groups):
            raise ValueError("Duplicate tie group")
        # Group transport order is canonical; the explicitly chosen member order is not changed.
        return sorted(
            value, key=lambda order: sorted(str(pid) for pid in order.player_ids)
        )


class TieGroup(BaseModel):
    division: Literal["A", "B"]
    player_ids: Annotated[list[UUID], Field(min_length=2, max_length=500)]
    position: Annotated[int, Field(gt=0)]
    position_end: Annotated[int, Field(gt=0)]
    wins: Annotated[int, Field(ge=0)]
    adjusted_deaths: Annotated[int, Field(ge=0)]
    segment_deaths: Annotated[int, Field(ge=0)] | None = None
    consequences: list[
        Literal["points", "coins", "podium", "movement", "last_b_reward", "single_league_prize", "matchday_prize"]
    ]


class RankingReview(BaseModel):
    input_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    groups: Annotated[list[TieGroup], Field(max_length=250)]
    ranking_rule: Literal["wins_adjusted_deaths_v1", "wins_segment_deaths_v2"] | None = None


class RankingErrorDetail(BaseModel):
    code: str
    message: str
    ranking: RankingReview | None = None


class RankingErrorResponse(BaseModel):
    detail: RankingErrorDetail


CloseDayBody.model_rebuild()
CorrectDayBody.model_rebuild()
ParticipantCloseDayBody.model_rebuild()
