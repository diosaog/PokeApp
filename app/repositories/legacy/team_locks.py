from __future__ import annotations

from app.domain.team_locks import TeamLock
from app.repositories import mappers


class LegacyTeamLockRepository:
    def __init__(self, *, season_id: str = mappers.LEGACY_SEASON_ID) -> None:
        self.season_id = season_id

    def get_team_lock(self, *, matchday_number: int, trainer_id: str) -> TeamLock | None:
        from storage import get_team_lock

        raw = get_team_lock(int(matchday_number), str(trainer_id))
        return mappers.team_lock_from_any(raw, season_id=self.season_id)

    def list_team_locks(self, *, matchday_number: int) -> tuple[TeamLock, ...]:
        from storage import list_team_locks

        return tuple(
            lock
            for lock in (
                mappers.team_lock_from_any(raw, season_id=self.season_id)
                for raw in list_team_locks(int(matchday_number))
            )
            if lock
        )

    def upsert_team_lock(self, lock: TeamLock) -> TeamLock | None:
        from storage import upsert_team_lock

        raw = upsert_team_lock(
            jornada=int(lock.matchday_number or 0),
            user=lock.trainer_id,
            team=[mappers.to_jsonable(mon) for mon in lock.team],
            save_id=mappers.as_int(lock.save_record_id, 0) or None,
            save_sha256=lock.save_sha256 or None,
            is_late=bool(lock.is_late),
        )
        return mappers.team_lock_from_any(raw, season_id=self.season_id)
