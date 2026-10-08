from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator
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


class TieOrder(StrictBody):
    player_ids: Annotated[list[UUID], Field(min_length=2, max_length=500)]
    reason: Reason

    @field_validator("player_ids")
    @classmethod
    def unique_players(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("Duplicate participant in resolution")
        return value


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
    consequences: list[
        Literal["points", "coins", "podium", "movement", "last_b_reward"]
    ]


class RankingReview(BaseModel):
    input_hash: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    groups: Annotated[list[TieGroup], Field(max_length=250)]


class RankingErrorDetail(BaseModel):
    code: str
    message: str
    ranking: RankingReview | None = None


class RankingErrorResponse(BaseModel):
    detail: RankingErrorDetail


CloseDayBody.model_rebuild()
CorrectDayBody.model_rebuild()
