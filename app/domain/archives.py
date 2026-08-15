from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import (
    JsonObject,
    SeasonArchiveId,
    SeasonId,
    UtcTimestamp,
    clean_text,
    require_id,
    require_positive_int,
)
from app.domain.cup import Cup
from app.domain.hall_of_fame import HallOfFameEntry
from app.domain.league import MatchdaySnapshot
from app.domain.pokemon import PublicPokemon
from app.domain.seasons import SeasonVersion
from app.domain.trainers import TrainerStatus


@dataclass(frozen=True)
class SeasonArchive:
    """Frozen season representation. It is not the live Season entity."""

    id: SeasonArchiveId
    schema_version: int
    season_id: SeasonId
    label: str
    archived_at: UtcTimestamp
    season_versions: tuple[SeasonVersion, ...] = field(default_factory=tuple)
    matchday_snapshots: tuple[MatchdaySnapshot, ...] = field(default_factory=tuple)
    trainer_statuses: dict[str, TrainerStatus] = field(default_factory=dict)
    champion_id: str = ""
    runner_up_id: str = ""
    champion_team: tuple[PublicPokemon, ...] = field(default_factory=tuple)
    cup_states: tuple[Cup, ...] = field(default_factory=tuple)
    hall_entries: tuple[HallOfFameEntry, ...] = field(default_factory=tuple)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "season_archive.id"))
        object.__setattr__(self, "schema_version", require_positive_int(self.schema_version, "season_archive.schema_version"))
        object.__setattr__(self, "season_id", require_id(self.season_id, "season_archive.season_id"))
        object.__setattr__(self, "label", require_id(self.label, "season_archive.label"))
        object.__setattr__(self, "archived_at", clean_text(self.archived_at))
        if not self.archived_at:
            raise ValueError("season_archive.archived_at must be set.")
        object.__setattr__(self, "season_versions", tuple(self.season_versions))
        object.__setattr__(self, "matchday_snapshots", tuple(self.matchday_snapshots))
        object.__setattr__(self, "champion_id", clean_text(self.champion_id))
        object.__setattr__(self, "runner_up_id", clean_text(self.runner_up_id))
        object.__setattr__(self, "champion_team", tuple(self.champion_team)[:6])
        object.__setattr__(self, "cup_states", tuple(self.cup_states))
        object.__setattr__(self, "hall_entries", tuple(self.hall_entries))
