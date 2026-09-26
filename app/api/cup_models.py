"""Typed Cup commands and public projections. No client-supplied tournament graph."""
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
from pydantic import BaseModel, Field, model_validator
from app.api.season_admin_models import StrictBody, Revision, Name, Reason

Format = Literal['swiss', 'elimination', 'doubles']
Score = Annotated[int, Field(strict=True, ge=0, le=2)]


class CupSideBody(StrictBody):
    name: Name
    trainer_ids: Annotated[list[UUID], Field(min_length=1, max_length=2)]

    @model_validator(mode='after')
    def canonical_members(self):
        if len(set(self.trainer_ids)) != len(self.trainer_ids):
            raise ValueError('Duplicate member')
        self.trainer_ids.sort()
        return self


class CupCreateBody(StrictBody):
    name: Name
    format: Format
    sides: Annotated[list[CupSideBody], Field(min_length=2, max_length=64)]
    swiss_rounds: Annotated[int, Field(strict=True, ge=1, le=10)] = 3

    @model_validator(mode='after')
    def roster(self):
        ids = [t for s in self.sides for t in s.trainer_ids]
        size = 2 if self.format=='doubles' else 1
        if len(set(ids)) != len(ids) or any(len(s.trainer_ids)!=size for s in self.sides):
            raise ValueError('Invalid members')
        if self.format=='swiss' and len(self.sides)<4:
            raise ValueError('Swiss needs four entrants')
        if self.format=='doubles' and len(self.sides)>16:
            raise ValueError('At most sixteen teams')
        if self.format!='swiss':
            self.swiss_rounds = 1
        return self


class CupRevisionBody(StrictBody):
    expected_revision: Revision


class CupSetupBody(CupCreateBody):
    expected_revision: Revision


class CupResultBody(StrictBody):
    match_id: UUID
    winner_side_id: UUID | None = None
    score_a: Score | None = None
    score_b: Score | None = None

    @model_validator(mode='after')
    def result(self):
        if self.winner_side_id:
            if self.score_a is not None or self.score_b is not None:
                raise ValueError('Winner-only or Bo3')
        elif (self.score_a, self.score_b) not in ((2,0),(2,1),(1,2),(0,2)):
            raise ValueError('Completed Bo3 required')
        return self


class CupResultsBody(CupRevisionBody):
    results: Annotated[list[CupResultBody], Field(min_length=1, max_length=32)]

    @model_validator(mode='after')
    def canonical_results(self):
        if len({x.match_id for x in self.results}) != len(self.results):
            raise ValueError('Duplicate result')
        self.results.sort(key=lambda x: x.match_id)
        return self


class CupCorrectBody(CupResultsBody):
    reason: Reason


class CupDisqualifyBody(CupRevisionBody):
    reason: Reason


class CupDiscardBody(CupDisqualifyBody):
    confirmation: Literal['DISCARD']


class CupMember(BaseModel):
    trainer_id: UUID
    season_player_id: UUID
    display_name: str


class CupSide(BaseModel):
    id: UUID
    name: str
    seed: int
    status: Literal['active','disqualified']
    members: list[CupMember]


class CupMatch(BaseModel):
    id: UUID
    position: int
    a: UUID | None
    b: UUID | None
    winner: UUID | None
    status: Literal['scheduled','completed','bye','forfeit','void']
    score_a: Score | None
    score_b: Score | None


class CupRound(BaseModel):
    number: int
    phase: Literal['swiss','elimination','semifinal','round_robin','final']
    status: Literal['open','closed']
    eligible_side_ids: list[UUID]
    matches: list[CupMatch]


class CupStanding(BaseModel):
    side_id: UUID
    seed: int
    status: Literal['active','disqualified']
    wins: int
    losses: int
    byes: int
    buchholz: int
    games_won: int
    games_lost: int
    position: int


class CupSummary(BaseModel):
    id: UUID
    season_id: UUID
    name: str
    format: Format
    status: Literal['draft','active','finished','discarded']
    revision: Revision
    rules_version: Literal[1]
    swiss_rounds: int


class CupDetail(CupSummary):
    sides: list[CupSide]
    rounds: list[CupRound]
    standings: list[CupStanding]
    certificate_id: UUID | None = None
    champion_side_id: UUID | None = None
    finalist_side_id: UUID | None = None
    checksum: str | None = None


class CupReceipt(BaseModel):
    operation_id: UUID
    event_id: UUID
    cup_id: UUID
    season_id: UUID
    operation: Literal['create','setup','start','results','close','correct','disqualify','discard','finalize']
    revision: Revision
    state: Literal['draft','active','finished','discarded']
    certificate_id: UUID | None
    hall_id: UUID | None
    actor_trainer_id: UUID
    changed_at: datetime
    replayed: bool
