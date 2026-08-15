from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import (
    JsonObject,
    MatchdayId,
    SaveId,
    SeasonId,
    TeamLockId,
    TrainerId,
    UtcTimestamp,
    clean_text,
    optional_id,
    require_id,
    require_positive_int,
)
from app.domain.pokemon import PublicPokemon


@dataclass(frozen=True)
class TeamLock:
    """Frozen team registered for a matchday.

    It stores public Pokemon data and save references, not a dependency on the
    current live save.
    """

    id: TeamLockId
    season_id: SeasonId
    trainer_id: TrainerId
    locked_at: UtcTimestamp
    team: tuple[PublicPokemon, ...]
    matchday_id: MatchdayId = ""
    matchday_number: int | None = None
    save_record_id: SaveId = ""
    save_sha256: str = ""
    deadline_at: UtcTimestamp = ""
    is_late: bool = False
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "team_lock.id"))
        object.__setattr__(self, "season_id", require_id(self.season_id, "team_lock.season_id"))
        object.__setattr__(self, "trainer_id", require_id(self.trainer_id, "team_lock.trainer_id"))
        object.__setattr__(self, "locked_at", clean_text(self.locked_at))
        if not self.locked_at:
            raise ValueError("team_lock.locked_at must be set.")
        object.__setattr__(self, "team", tuple(self.team)[:6])
        object.__setattr__(self, "matchday_id", optional_id(self.matchday_id))
        if self.matchday_number is not None:
            object.__setattr__(self, "matchday_number", require_positive_int(self.matchday_number, "team_lock.matchday_number"))
        object.__setattr__(self, "save_record_id", optional_id(self.save_record_id))
        object.__setattr__(self, "save_sha256", clean_text(self.save_sha256))
        object.__setattr__(self, "deadline_at", clean_text(self.deadline_at))
