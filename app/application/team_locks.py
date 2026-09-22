from __future__ import annotations

from copy import deepcopy
import re

from app.domain.pokemon import PublicPokemon
from app.domain.seasons import SeasonRules
from app.domain.services import team_locks as team_lock_domain
from app.domain.team_locks import TeamLock, TeamLockMutation, TeamLockRecord
from app.repositories.errors import ConflictError, NotFoundError, PermissionDeniedError
from app.repositories.protocols import TeamLockMutationRepository, TeamLockRepository


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


def lock_team_v2(
    repository: TeamLockMutationRepository, *, season_id: str, matchday_id: str,
    trainer_id: str, save_file_id: str,
) -> TeamLockRecord:
    source = repository.load_source(
        season_id=season_id, matchday_id=matchday_id,
        trainer_id=trainer_id, save_file_id=save_file_id,
    )
    season, matchday, player, save, parsed = (
        source.season, source.matchday, source.participant, source.save, source.parsed,
    )
    if not season or season.get("id") != season_id:
        raise NotFoundError("season_not_found")
    if not matchday or matchday.get("id") != matchday_id or matchday.get("season_id") != season_id:
        raise NotFoundError("matchday_not_found")
    if season.get("status") != "active":
        raise ConflictError("season_not_active")
    if matchday.get("status") not in ("scheduled", "open") or matchday.get("closed_at"):
        raise ConflictError("matchday_not_lockable")
    if not player or player.get("season_id") != season_id or player.get("trainer_id") != trainer_id:
        raise NotFoundError("participation_not_found")
    if player.get("status") != "active":
        raise PermissionDeniedError("participant_inactive")
    if not save or save.get("id") != save_file_id or save.get("season_id") != season_id or save.get("trainer_id") != trainer_id:
        raise NotFoundError("save_not_found")
    if save.get("deleted_at") or save.get("parser_status") != "parsed":
        raise ConflictError("save_not_ready")
    if not re.fullmatch(r"[a-f0-9]{64}", str(save.get("sha256") or "")):
        raise ConflictError("invalid_save_hash")
    if (not parsed or parsed.get("save_file_id") != save_file_id
            or not save.get("parser_version") or parsed.get("parser_version") != save["parser_version"]
            or parsed.get("status") != "parsed" or parsed.get("schema_version") != 1):
        raise ConflictError("parsed_save_not_ready")
    payload = parsed.get("payload")
    if not isinstance(payload, dict):
        raise ConflictError("invalid_parsed_team")
    for field, expected in (("save_record_id", save_file_id), ("trainer_id", trainer_id), ("source_hash", save["sha256"])):
        if field in payload and payload[field] != expected:
            raise ConflictError("parsed_save_identity_mismatch")
    try:
        public, private = team_lock_domain.snapshots_from_parsed_payload(payload)
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ConflictError("invalid_parsed_team") from exc
    return repository.upsert_with_activity(TeamLockMutation(
        season_id=season_id, matchday_id=matchday_id, trainer_id=trainer_id,
        season_player_id=str(player["id"]), save_file_id=save_file_id, save_sha256=save["sha256"],
        parsed_save_id=str(parsed["id"]), parsed_payload=deepcopy(payload),
        public_team_snapshot=public, private_team_snapshot=private,
    ))
