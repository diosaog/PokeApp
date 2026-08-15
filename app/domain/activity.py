from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import (
    ActivityEventId,
    JsonObject,
    TrainerId,
    UtcTimestamp,
    Visibility,
    clean_text,
    optional_id,
    require_id,
    require_positive_int,
    StringEnum,
)


class ActivityEventType(StringEnum):
    SAVE_UPLOADED = "save_uploaded"
    PURCHASE_COMPLETED = "purchase_completed"
    TEAM_LOCKED = "team_locked"


@dataclass(frozen=True)
class ActivityEvent:
    id: ActivityEventId
    type: ActivityEventType
    created_at: UtcTimestamp
    actor_id: TrainerId = ""
    trainer_id: TrainerId = ""
    context: JsonObject = field(default_factory=dict)
    payload: JsonObject = field(default_factory=dict)
    visibility: Visibility = Visibility.PUBLIC
    dedupe_key: str = ""
    schema_version: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "activity_event.id"))
        object.__setattr__(self, "schema_version", require_positive_int(self.schema_version, "activity_event.schema_version"))
        object.__setattr__(self, "created_at", clean_text(self.created_at))
        if not self.created_at:
            raise ValueError("activity_event.created_at must be set.")
        object.__setattr__(self, "actor_id", optional_id(self.actor_id))
        object.__setattr__(self, "trainer_id", optional_id(self.trainer_id))
        object.__setattr__(self, "dedupe_key", require_id(self.dedupe_key, "activity_event.dedupe_key"))
