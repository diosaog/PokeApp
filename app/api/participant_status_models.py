from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from app.api.season_admin_models import StrictBody, Revision, Reason


class ParticipantStatusBody(StrictBody):
    reason: Reason
    expected_roster_revision: Revision


class ParticipantStatusReceipt(BaseModel):
    operation_id: UUID
    event_id: UUID
    season_id: UUID
    participant_id: UUID
    old_status: Literal['active']
    new_status: Literal['retired', 'abandoned', 'disqualified']
    reason: Reason
    effective_matchday_id: UUID
    effective_matchday_number: int = Field(strict=True, gt=0)
    actor_trainer_id: UUID
    changed_at: datetime
    roster_revision: Revision
    setup_revision: Revision
    replayed: bool
