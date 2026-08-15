from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import (
    JsonObject,
    TrainerId,
    UtcTimestamp,
    clean_text,
    optional_id,
    require_id,
    StringEnum,
)


class TrainerStatus(StringEnum):
    ACTIVE = "active"
    RETIRED = "retired"
    ABANDONED = "abandoned"
    DISQUALIFIED = "disqualified"


@dataclass(frozen=True)
class Trainer:
    """Global trainer identity.

    Season participation belongs to SeasonPlayer, not here.
    """

    id: TrainerId
    display_name: str
    avatar_url: str = ""
    created_at: UtcTimestamp = ""
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "trainer.id"))
        name = clean_text(self.display_name)
        object.__setattr__(self, "display_name", name or self.id)
        object.__setattr__(self, "avatar_url", clean_text(self.avatar_url))


@dataclass(frozen=True)
class TrainerFlags:
    """Functional trainer flags that are not administrative status."""

    trainer_id: TrainerId
    robbed: bool = False
    robbed_at: UtcTimestamp = ""
    robbed_by: TrainerId = ""
    robbed_source: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "trainer_id", require_id(self.trainer_id, "trainer_flags.trainer_id"))
        object.__setattr__(self, "robbed_by", optional_id(self.robbed_by))
        object.__setattr__(self, "robbed_source", clean_text(self.robbed_source))
        object.__setattr__(self, "note", clean_text(self.note))
