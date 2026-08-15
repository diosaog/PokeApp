from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import (
    DivisionId,
    JsonObject,
    MatchId,
    MatchdayId,
    SeasonId,
    SeasonVersionId,
    TrainerId,
    UtcTimestamp,
    clean_text,
    optional_id,
    require_id,
    require_non_negative_float,
    require_non_negative_int,
    require_positive_int,
    StringEnum,
)
from app.domain.seasons import SeasonVersion
from app.domain.trainers import TrainerStatus


class MatchdayStatus(StringEnum):
    PLANNED = "planned"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class MatchStatus(StringEnum):
    SCHEDULED = "scheduled"
    REPORTED = "reported"
    CONFIRMED = "confirmed"
    VOID = "void"


@dataclass(frozen=True)
class Matchday:
    id: MatchdayId
    season_id: SeasonId
    number: int
    status: MatchdayStatus
    season_version_id: SeasonVersionId
    opened_at: UtcTimestamp = ""
    closed_at: UtcTimestamp = ""
    snapshot_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "matchday.id"))
        object.__setattr__(self, "season_id", require_id(self.season_id, "matchday.season_id"))
        object.__setattr__(self, "number", require_positive_int(self.number, "matchday.number"))
        object.__setattr__(self, "season_version_id", require_id(self.season_version_id, "matchday.season_version_id"))
        object.__setattr__(self, "snapshot_id", optional_id(self.snapshot_id))


@dataclass(frozen=True)
class Match:
    id: MatchId
    matchday_id: MatchdayId
    division_id: DivisionId
    trainer_a_id: TrainerId
    trainer_b_id: TrainerId
    status: MatchStatus = MatchStatus.SCHEDULED
    winner_trainer_id: TrainerId = ""
    score: str = ""
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "match.id"))
        object.__setattr__(self, "matchday_id", require_id(self.matchday_id, "match.matchday_id"))
        object.__setattr__(self, "division_id", require_id(self.division_id, "match.division_id"))
        object.__setattr__(self, "trainer_a_id", require_id(self.trainer_a_id, "match.trainer_a_id"))
        object.__setattr__(self, "trainer_b_id", require_id(self.trainer_b_id, "match.trainer_b_id"))
        object.__setattr__(self, "winner_trainer_id", optional_id(self.winner_trainer_id))
        object.__setattr__(self, "score", clean_text(self.score))


@dataclass(frozen=True)
class PenaltySummary:
    dead_count: int = 0
    dead_points_penalty: float = 0.0
    points_reduction: float = 0.0
    coins_reduction: int = 0
    store_blocked: bool = False
    trainer_status: TrainerStatus = TrainerStatus.ACTIVE
    trainer_status_labels: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(self, "dead_count", require_non_negative_int(self.dead_count, "penalty.dead_count"))
        object.__setattr__(
            self,
            "dead_points_penalty",
            require_non_negative_float(self.dead_points_penalty, "penalty.dead_points_penalty"),
        )
        object.__setattr__(
            self,
            "points_reduction",
            require_non_negative_float(self.points_reduction, "penalty.points_reduction"),
        )
        object.__setattr__(self, "coins_reduction", require_non_negative_int(self.coins_reduction, "penalty.coins_reduction"))
        object.__setattr__(self, "trainer_status_labels", tuple(clean_text(x) for x in self.trainer_status_labels if clean_text(x)))


@dataclass(frozen=True)
class LeagueStanding:
    matchday_id: MatchdayId
    trainer_id: TrainerId
    division_id: DivisionId
    position: int
    division_position: int
    points_awarded: int = 0
    coins_awarded: int = 0
    score: float = 0.0
    penalties: PenaltySummary = field(default_factory=PenaltySummary)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "matchday_id", require_id(self.matchday_id, "standing.matchday_id"))
        object.__setattr__(self, "trainer_id", require_id(self.trainer_id, "standing.trainer_id"))
        object.__setattr__(self, "division_id", require_id(self.division_id, "standing.division_id"))
        object.__setattr__(self, "position", require_positive_int(self.position, "standing.position"))
        object.__setattr__(self, "division_position", require_positive_int(self.division_position, "standing.division_position"))
        object.__setattr__(self, "points_awarded", require_non_negative_int(self.points_awarded, "standing.points_awarded"))
        object.__setattr__(self, "coins_awarded", require_non_negative_int(self.coins_awarded, "standing.coins_awarded"))


@dataclass(frozen=True)
class MatchdaySnapshot:
    """Official immutable representation of a closed matchday."""

    id: str
    schema_version: int
    matchday_id: MatchdayId
    season_id: SeasonId
    matchday_number: int
    closed_at: UtcTimestamp
    season_version: SeasonVersion
    division_composition: dict[DivisionId, tuple[TrainerId, ...]]
    standings: tuple[LeagueStanding, ...] = field(default_factory=tuple)
    points_awarded: dict[TrainerId, int] = field(default_factory=dict)
    coins_awarded: dict[TrainerId, int] = field(default_factory=dict)
    penalties: dict[TrainerId, PenaltySummary] = field(default_factory=dict)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "matchday_snapshot.id"))
        object.__setattr__(self, "schema_version", require_positive_int(self.schema_version, "matchday_snapshot.schema_version"))
        object.__setattr__(self, "matchday_id", require_id(self.matchday_id, "matchday_snapshot.matchday_id"))
        object.__setattr__(self, "season_id", require_id(self.season_id, "matchday_snapshot.season_id"))
        object.__setattr__(self, "matchday_number", require_positive_int(self.matchday_number, "matchday_snapshot.matchday_number"))
        object.__setattr__(self, "closed_at", clean_text(self.closed_at))
        if not self.closed_at:
            raise ValueError("matchday_snapshot.closed_at must be set.")
        composition = {
            require_id(division_id, "matchday_snapshot.division_id"): tuple(
                require_id(trainer_id, "matchday_snapshot.trainer_id")
                for trainer_id in trainer_ids
            )
            for division_id, trainer_ids in self.division_composition.items()
        }
        object.__setattr__(self, "division_composition", composition)
        object.__setattr__(self, "standings", tuple(self.standings))
        object.__setattr__(
            self,
            "points_awarded",
            {require_id(k, "points_awarded.trainer_id"): require_non_negative_int(v, "points_awarded.value") for k, v in self.points_awarded.items()},
        )
        object.__setattr__(
            self,
            "coins_awarded",
            {require_id(k, "coins_awarded.trainer_id"): require_non_negative_int(v, "coins_awarded.value") for k, v in self.coins_awarded.items()},
        )
