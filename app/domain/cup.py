from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import (
    CupId,
    JsonObject,
    SeasonId,
    TrainerId,
    UtcTimestamp,
    clean_text,
    optional_id,
    require_id,
    require_non_negative_int,
    require_positive_int,
    StringEnum,
)


class CupFormat(StringEnum):
    SWISS = "swiss"
    SINGLE_ELIMINATION = "single_elimination"
    DOUBLES = "doubles"


@dataclass(frozen=True)
class Cup:
    id: CupId
    season_id: SeasonId
    format: CupFormat
    name: str
    player_ids: tuple[TrainerId, ...] = field(default_factory=tuple)
    current_round: int = 0
    max_rounds: int = 0
    configured: bool = False
    champion_id: TrainerId = ""
    hall_run_id: str = ""
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "cup.id"))
        object.__setattr__(self, "season_id", require_id(self.season_id, "cup.season_id"))
        object.__setattr__(self, "name", require_id(self.name, "cup.name"))
        object.__setattr__(self, "player_ids", tuple(require_id(player, "cup.player_ids") for player in self.player_ids))
        object.__setattr__(self, "current_round", require_non_negative_int(self.current_round, "cup.current_round"))
        object.__setattr__(self, "max_rounds", require_non_negative_int(self.max_rounds, "cup.max_rounds"))
        object.__setattr__(self, "champion_id", optional_id(self.champion_id))
        object.__setattr__(self, "hall_run_id", clean_text(self.hall_run_id))


@dataclass(frozen=True)
class CupMatch:
    id: str
    cup_id: CupId
    round_number: int
    participant_a_id: str = ""
    participant_b_id: str = ""
    winner_id: str = ""
    score: str = ""
    is_bye: bool = False
    played_at: UtcTimestamp = ""
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "cup_match.id"))
        object.__setattr__(self, "cup_id", require_id(self.cup_id, "cup_match.cup_id"))
        object.__setattr__(self, "round_number", require_positive_int(self.round_number, "cup_match.round_number"))
        object.__setattr__(self, "participant_a_id", optional_id(self.participant_a_id))
        object.__setattr__(self, "participant_b_id", optional_id(self.participant_b_id))
        object.__setattr__(self, "winner_id", optional_id(self.winner_id))
        object.__setattr__(self, "score", clean_text(self.score))
        object.__setattr__(self, "played_at", clean_text(self.played_at))
