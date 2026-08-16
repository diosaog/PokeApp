from __future__ import annotations

from app.repositories.legacy.activity import LegacyActivityRepository
from app.repositories.legacy.competitions import LegacyCompetitionRepository
from app.repositories.legacy.hall_of_fame import LegacyHallOfFameRepository
from app.repositories.legacy.league import LegacyLeagueRepository
from app.repositories.legacy.saves import LegacySaveRepository
from app.repositories.legacy.season import LegacySeasonRepository
from app.repositories.legacy.shop import LegacyShopRepository
from app.repositories.legacy.team_locks import LegacyTeamLockRepository
from app.repositories.legacy.trainers import LegacyTrainerRepository

__all__ = [
    "LegacyActivityRepository",
    "LegacyCompetitionRepository",
    "LegacyHallOfFameRepository",
    "LegacyLeagueRepository",
    "LegacySaveRepository",
    "LegacySeasonRepository",
    "LegacyShopRepository",
    "LegacyTeamLockRepository",
    "LegacyTrainerRepository",
]
