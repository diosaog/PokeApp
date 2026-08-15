from __future__ import annotations

from dataclasses import dataclass

from app.domain.pokemon import PublicPokemon
from app.domain.seasons import SeasonRules
from app.domain.team_locks import TeamLock


@dataclass(frozen=True)
class TeamLockValidation:
    allowed: bool
    reason: str = "ok"


def validate_team_lock(
    *,
    trainer_id: str,
    participant_ids: list[str] | tuple[str, ...],
    matchday_number: int,
    team: list[PublicPokemon] | tuple[PublicPokemon, ...],
    rules: SeasonRules,
) -> TeamLockValidation:
    trainer = str(trainer_id or "").strip()
    if not trainer:
        return TeamLockValidation(False, "missing_trainer")
    if trainer not in {str(value) for value in participant_ids}:
        return TeamLockValidation(False, "trainer_not_participant")
    if int(matchday_number or 0) <= 0:
        return TeamLockValidation(False, "invalid_matchday")
    if rules.team_lock_required and not team:
        return TeamLockValidation(False, "empty_team")
    if len(tuple(team)) > 6:
        return TeamLockValidation(False, "too_many_pokemon")
    return TeamLockValidation(True)


def build_team_lock(
    *,
    lock_id: str,
    season_id: str,
    trainer_id: str,
    locked_at: str,
    team: list[PublicPokemon] | tuple[PublicPokemon, ...],
    matchday_id: str = "",
    matchday_number: int | None = None,
    save_record_id: str = "",
    save_sha256: str = "",
    deadline_at: str = "",
    is_late: bool = False,
) -> TeamLock:
    return TeamLock(
        id=lock_id,
        season_id=season_id,
        trainer_id=trainer_id,
        locked_at=locked_at,
        team=tuple(team)[:6],
        matchday_id=matchday_id,
        matchday_number=matchday_number,
        save_record_id=save_record_id,
        save_sha256=save_sha256,
        deadline_at=deadline_at,
        is_late=bool(is_late),
    )
