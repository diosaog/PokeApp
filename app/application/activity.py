from __future__ import annotations

from app.domain.activity import ActivityEvent, ActivityEventType
from app.domain.common import Visibility
from app.domain.services import activity as activity_domain
from app.repositories.protocols import ActivityRepository


def record_activity(
    repository: ActivityRepository,
    event_type: ActivityEventType,
    *,
    created_at: int,
    actor_id: str = "",
    trainer_id: str = "",
    context: dict | None = None,
    payload: dict | None = None,
    visibility: Visibility = Visibility.PUBLIC,
    dedupe_key: str,
) -> ActivityEvent:
    event = activity_domain.build_activity_event(
        event_type,
        created_at=created_at,
        actor_id=actor_id,
        trainer_id=trainer_id,
        context=context,
        payload=payload,
        visibility=visibility,
        dedupe_key=dedupe_key,
    )
    return repository.append(event)
