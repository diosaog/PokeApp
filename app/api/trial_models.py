"""Manual Discord decisions; no votes, jury or client-owned effect provenance."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, field_serializer, model_validator
from app.api.season_admin_models import StrictBody, Revision, Reason, Name

Text = Annotated[str, Field(strict=True, min_length=1, max_length=2000)]


class StoreBan(StrictBody):
    type: Literal['store_ban']
    duration_matchdays: int = Field(strict=True, ge=1, le=1000)


class CoinsReduction(StrictBody):
    type: Literal['coins_reduction']
    amount: int = Field(strict=True, gt=0, le=2147483647)


class PointsReduction(StrictBody):
    type: Literal['points_reduction']
    amount: Decimal = Field(gt=0, le=Decimal('9999999999.99'), decimal_places=2)

    @field_validator('amount', mode='before')
    @classmethod
    def exact_number(cls, value):
        if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
            raise ValueError('Invalid points')
        try:
            result = Decimal(str(value))
        except InvalidOperation as exc:
            raise ValueError('Invalid points') from exc
        if not result.is_finite():
            raise ValueError('Invalid points')
        return result.normalize()

    @field_serializer('amount')
    def canonical_amount(self, value):
        return format(value, 'f')


class SanctionNote(StrictBody):
    type: Literal['pokemon_release', 'other']
    text: Text


Sanction = Annotated[StoreBan | CoinsReduction | PointsReduction | SanctionNote, Field(discriminator='type')]


class ProposalFields(StrictBody):
    title: Name
    description: Text
    is_public: bool = Field(strict=True, default=True)
    evidence: str = Field(strict=True, max_length=10000, default='')


class CreateTrialBody(ProposalFields):
    accused_trainer_id: UUID


class UpdateTrialBody(ProposalFields):
    expected_case_revision: Revision


class ResolveTrialBody(StrictBody):
    expected_case_revision: Revision
    verdict: Literal['guilty', 'not_guilty']
    decision_summary: Text
    sanctions: list[Sanction] = Field(max_length=5)

    @model_validator(mode='after')
    def coherent_sanctions(self):
        types = [s.type for s in self.sanctions]
        if len(types) != len(set(types)):
            raise ValueError('One sanction per type; combine amounts/notes')
        if self.verdict == 'not_guilty' and any(t in ('store_ban', 'coins_reduction', 'points_reduction') for t in types):
            raise ValueError('Not guilty cannot apply mechanical sanctions')
        self.sanctions.sort(key=lambda s: s.type)
        return self


class CorrectTrialBody(ResolveTrialBody):
    reason: Reason


class CancelTrialBody(StrictBody):
    expected_case_revision: Revision
    reason: Reason


class TrialReceipt(BaseModel):
    operation_id: UUID
    event_id: UUID
    season_id: UUID
    case_id: UUID
    case_number: int = Field(strict=True, gt=0)
    case_revision: int = Field(strict=True, gt=0)
    operation: Literal['create', 'proposal', 'resolve', 'cancel', 'correct']
    status: Literal['open', 'resolved', 'dismissed', 'cancelled']
    verdict: Literal['guilty', 'not_guilty'] | None
    decision_revision_id: UUID | None
    actor_trainer_id: UUID
    changed_at: datetime
    replayed: bool


class SafeSanction(BaseModel):
    id: UUID
    type: str
    amount: Decimal | None = None
    duration_matchdays: int | None = None
    start_matchday_number: int | None = None
    end_matchday_number: int | None = None


class TrialHistory(BaseModel):
    id: UUID
    revision: int
    operation: str
    actor_trainer_id: UUID
    created_at: datetime
    previous_decision_id: UUID | None
    details: ProposalFields
    verdict: Literal['guilty', 'not_guilty'] | None
    decision_summary: str
    reason: str
    sanctions: list[Sanction]


class TrialDetail(BaseModel):
    evidence: str
    history: list[TrialHistory]


class TrialView(BaseModel):
    id: UUID
    season_id: UUID
    case_number: int | None
    revision: int
    title: str
    description: str
    status: str
    verdict: Literal['guilty', 'not_guilty'] | None
    is_public: bool
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    sanctions: list[SafeSanction]
    detail: TrialDetail | None


class TrialList(BaseModel):
    season_id: UUID
    cases: list[TrialView]
