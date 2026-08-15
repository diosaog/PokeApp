from __future__ import annotations

from app.domain.archives import SeasonArchive
from app.domain.hall_of_fame import HallOfFameEntry
from app.domain.league import MatchdaySnapshot
from app.domain.pokemon import PublicPokemon
from app.domain.seasons import SeasonVersion
from app.domain.trainers import TrainerStatus


def build_season_archive(
    *,
    archive_id: str,
    season_id: str,
    label: str,
    archived_at: str,
    season_versions: list[SeasonVersion] | tuple[SeasonVersion, ...],
    matchday_snapshots: list[MatchdaySnapshot] | tuple[MatchdaySnapshot, ...],
    trainer_statuses: dict[str, TrainerStatus],
    champion_id: str = "",
    runner_up_id: str = "",
    champion_team: list[PublicPokemon] | tuple[PublicPokemon, ...] = (),
    hall_entries: list[HallOfFameEntry] | tuple[HallOfFameEntry, ...] = (),
) -> SeasonArchive:
    return SeasonArchive(
        id=archive_id,
        schema_version=1,
        season_id=season_id,
        label=label,
        archived_at=archived_at,
        season_versions=tuple(season_versions),
        matchday_snapshots=tuple(matchday_snapshots),
        trainer_statuses=dict(trainer_statuses),
        champion_id=champion_id,
        runner_up_id=runner_up_id,
        champion_team=tuple(champion_team)[:6],
        hall_entries=tuple(hall_entries),
    )
