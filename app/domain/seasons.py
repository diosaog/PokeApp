from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import (
    DivisionId,
    JsonObject,
    SeasonId,
    SeasonPlayerId,
    SeasonVersionId,
    TrainerId,
    UtcTimestamp,
    clean_text,
    optional_id,
    require_id,
    require_non_negative_int,
    require_positive_int,
    StringEnum,
)
from app.domain.trainers import TrainerStatus


class SeasonLifecycle(StringEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    FINISHED = "finished"
    ARCHIVED = "archived"
    DISCARDED = "discarded"


@dataclass(frozen=True)
class SeasonRules:
    team_lock_required: bool = True
    last_b_gets_steal: bool = True


@dataclass(frozen=True)
class SeasonMetadata:
    """Season configuration metadata that is not active business logic."""

    cup_is_separate: bool = True
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "notes", clean_text(self.notes))


@dataclass(frozen=True)
class Season:
    id: SeasonId
    name: str
    lifecycle: SeasonLifecycle = SeasonLifecycle.DRAFT
    active_version_id: SeasonVersionId = ""
    created_at: UtcTimestamp = ""
    started_at: UtcTimestamp = ""
    finished_at: UtcTimestamp = ""
    archived_at: UtcTimestamp = ""
    discarded_at: UtcTimestamp = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "season.id"))
        name = clean_text(self.name)
        if not name:
            raise ValueError("season.name must be non-empty.")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "active_version_id", optional_id(self.active_version_id))


@dataclass(frozen=True)
class SeasonVersion:
    id: SeasonVersionId
    season_id: SeasonId
    name: str
    effective_matchday: int
    max_matchdays: int
    participant_ids: tuple[TrainerId, ...] = field(default_factory=tuple)
    division_sizes: tuple[int, ...] = field(default_factory=tuple)
    promotion_relegation_count: int = 0
    points_by_position: dict[int, int] = field(default_factory=dict)
    coins_by_position: dict[int, int] = field(default_factory=dict)
    rules: SeasonRules = field(default_factory=SeasonRules)
    metadata: SeasonMetadata = field(default_factory=SeasonMetadata)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "season_version.id"))
        object.__setattr__(self, "season_id", require_id(self.season_id, "season_version.season_id"))
        name = clean_text(self.name)
        if not name:
            raise ValueError("season_version.name must be non-empty.")
        object.__setattr__(self, "name", name)
        object.__setattr__(
            self,
            "effective_matchday",
            require_positive_int(self.effective_matchday, "season_version.effective_matchday"),
        )
        object.__setattr__(
            self,
            "max_matchdays",
            require_positive_int(self.max_matchdays, "season_version.max_matchdays"),
        )
        participants = tuple(require_id(value, "season_version.participant_ids") for value in self.participant_ids)
        if len(set(participants)) != len(participants):
            raise ValueError("season_version.participant_ids cannot contain duplicates.")
        object.__setattr__(self, "participant_ids", participants)
        object.__setattr__(
            self,
            "division_sizes",
            tuple(require_non_negative_int(size, "season_version.division_sizes") for size in self.division_sizes),
        )
        object.__setattr__(
            self,
            "promotion_relegation_count",
            require_non_negative_int(
                self.promotion_relegation_count,
                "season_version.promotion_relegation_count",
            ),
        )
        object.__setattr__(
            self,
            "points_by_position",
            {require_positive_int(k, "points.position"): require_non_negative_int(v, "points.value") for k, v in self.points_by_position.items()},
        )
        object.__setattr__(
            self,
            "coins_by_position",
            {require_positive_int(k, "coins.position"): require_non_negative_int(v, "coins.value") for k, v in self.coins_by_position.items()},
        )


@dataclass(frozen=True)
class Division:
    id: DivisionId
    season_id: SeasonId
    name: str
    tier_order: int
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "division.id"))
        object.__setattr__(self, "season_id", require_id(self.season_id, "division.season_id"))
        name = clean_text(self.name)
        if not name:
            raise ValueError("division.name must be non-empty.")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "tier_order", require_positive_int(self.tier_order, "division.tier_order"))


@dataclass(frozen=True)
class SeasonPlayer:
    id: SeasonPlayerId
    season_id: SeasonId
    trainer_id: TrainerId
    status: TrainerStatus = TrainerStatus.ACTIVE
    division_id: DivisionId = ""
    joined_matchday: int = 1
    left_matchday: int | None = None
    seed_order: int | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "season_player.id"))
        object.__setattr__(self, "season_id", require_id(self.season_id, "season_player.season_id"))
        object.__setattr__(self, "trainer_id", require_id(self.trainer_id, "season_player.trainer_id"))
        object.__setattr__(self, "division_id", optional_id(self.division_id))
        object.__setattr__(self, "joined_matchday", require_positive_int(self.joined_matchday, "season_player.joined_matchday"))
        if self.left_matchday is not None:
            object.__setattr__(self, "left_matchday", require_positive_int(self.left_matchday, "season_player.left_matchday"))
        if self.seed_order is not None:
            object.__setattr__(self, "seed_order", require_positive_int(self.seed_order, "season_player.seed_order"))
