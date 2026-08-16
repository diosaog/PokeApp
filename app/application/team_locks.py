from __future__ import annotations

from app.domain.pokemon import PublicPokemon
from app.domain.seasons import SeasonRules
from app.domain.services import team_locks as team_lock_domain
from app.domain.team_locks import TeamLock
from app.repositories.errors import ConflictError
from app.repositories.protocols import TeamLockRepository


def lock_team_for_matchday(
    repository: TeamLockRepository,
    *,
    lock_id: str,
    season_id: str,
    trainer_id: str,
    locked_at: str,
    matchday_number: int,
    team: tuple[PublicPokemon, ...],
    participant_ids: tuple[str, ...],
    rules: SeasonRules,
    save_record_id: str = "",
    save_sha256: str = "",
    is_late: bool = False,
) -> TeamLock:
    validation = team_lock_domain.validate_team_lock(
        trainer_id=trainer_id,
        participant_ids=participant_ids,
        matchday_number=matchday_number,
        team=team,
        rules=rules,
    )
    if not validation.allowed:
        raise ConflictError(validation.reason)
    lock = team_lock_domain.build_team_lock(
        lock_id=lock_id,
        season_id=season_id,
        trainer_id=trainer_id,
        locked_at=locked_at,
        team=team,
        matchday_number=matchday_number,
        save_record_id=save_record_id,
        save_sha256=save_sha256,
        is_late=is_late,
    )
    saved = repository.upsert_team_lock(lock)
    if saved is None:
        raise ConflictError("team_lock_not_saved")
    return saved
