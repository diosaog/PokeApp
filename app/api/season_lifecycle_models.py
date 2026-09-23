"""Explicit lifecycle commands, not a generic season status patch."""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from app.api.season_admin_models import StrictBody, Revision, Reason, Name


class FinishSeasonBody(StrictBody):
    expected_revision: Revision


class ArchiveSeasonBody(FinishSeasonBody):
    label: Name | None = None


class DiscardSeasonBody(FinishSeasonBody):
    reason: Reason
    confirmation: Literal['DISCARD']


class SeasonLifecycleReceipt(BaseModel):
    operation_id: UUID
    event_id: UUID
    season_id: UUID
    operation: Literal['finish', 'archive', 'discard']
    state: Literal['finished', 'archived', 'discarded']
    actor_trainer_id: UUID
    changed_at: datetime
    setup_revision: Revision
    current_matchday_id: UUID | None
    archive_id: UUID | None
    hall_id: UUID | None
    replayed: bool
