from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import (
    CompetitionType,
    HallOfFameEntryId,
    SeasonArchiveId,
    SeasonId,
    TrainerId,
    UtcTimestamp,
    clean_text,
    optional_id,
    require_id,
)
from app.domain.pokemon import PublicPokemon


@dataclass(frozen=True)
class HallOfFameEntry:
    id: HallOfFameEntryId
    competition: CompetitionType
    title: str
    champion_id: TrainerId
    created_at: UtcTimestamp
    season_id: SeasonId = ""
    archive_id: SeasonArchiveId = ""
    runner_up_id: TrainerId = ""
    frozen_team: tuple[PublicPokemon, ...] = field(default_factory=tuple)
    source: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "hall_of_fame_entry.id"))
        object.__setattr__(self, "title", require_id(self.title, "hall_of_fame_entry.title"))
        object.__setattr__(self, "champion_id", require_id(self.champion_id, "hall_of_fame_entry.champion_id"))
        object.__setattr__(self, "created_at", clean_text(self.created_at))
        if not self.created_at:
            raise ValueError("hall_of_fame_entry.created_at must be set.")
        object.__setattr__(self, "season_id", optional_id(self.season_id))
        object.__setattr__(self, "archive_id", optional_id(self.archive_id))
        object.__setattr__(self, "runner_up_id", optional_id(self.runner_up_id))
        object.__setattr__(self, "frozen_team", tuple(self.frozen_team)[:6])
        object.__setattr__(self, "source", clean_text(self.source))
        object.__setattr__(self, "notes", clean_text(self.notes))
