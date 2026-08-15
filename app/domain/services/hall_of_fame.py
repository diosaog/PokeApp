from __future__ import annotations

from app.domain.common import CompetitionType
from app.domain.hall_of_fame import HallOfFameEntry
from app.domain.pokemon import PublicPokemon


def build_league_hall_entry(
    *,
    entry_id: str,
    title: str,
    champion_id: str,
    created_at: str,
    season_id: str = "",
    archive_id: str = "",
    runner_up_id: str = "",
    frozen_team: list[PublicPokemon] | tuple[PublicPokemon, ...] = (),
    notes: str = "",
) -> HallOfFameEntry:
    return HallOfFameEntry(
        id=entry_id,
        competition=CompetitionType.LEAGUE,
        title=title,
        champion_id=champion_id,
        created_at=created_at,
        season_id=season_id,
        archive_id=archive_id,
        runner_up_id=runner_up_id,
        frozen_team=tuple(frozen_team)[:6],
        source="season_archive",
        notes=notes,
    )
