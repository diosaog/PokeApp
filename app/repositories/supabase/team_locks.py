from __future__ import annotations

from copy import deepcopy
from dataclasses import fields
from typing import Any
from uuid import UUID

from app.domain.team_locks import TeamLockMutation, TeamLockRecord, TeamLockSource
from app.repositories.errors import ConflictError, NotFoundError, PermissionDeniedError, PersistenceError


RPC_NAME = "api_upsert_team_lock"
RPC_ERRORS = {
    "PT403": PermissionDeniedError,
    "PT404": NotFoundError,
    "PT409": ConflictError,
}


class SupabaseTeamLockRepository:
    def __init__(self, client: Any) -> None:
        self._client = client

    @classmethod
    def from_url_key(cls, url: str, service_role_key: str) -> "SupabaseTeamLockRepository":
        from supabase import create_client

        return cls(create_client(url, service_role_key))

    def _one(self, table: str, columns: str, **filters) -> dict | None:
        try:
            query = self._client.table(table).select(columns)
            for key, value in filters.items():
                query = query.eq(key, value)
            rows = query.limit(1).execute().data
            return deepcopy(rows[0]) if rows else None
        except Exception as exc:
            raise PersistenceError("Team lock source is unavailable.") from exc

    def load_source(self, *, season_id: str, matchday_id: str, trainer_id: str, save_file_id: str) -> TeamLockSource:
        season_id, matchday_id, trainer_id, save_file_id = (
            str(UUID(value)) for value in (season_id, matchday_id, trainer_id, save_file_id)
        )
        season = self._one("seasons", "id,status", id=season_id)
        matchday = self._one("matchdays", "id,season_id,number,status,closed_at", id=matchday_id, season_id=season_id)
        participant = self._one("season_players", "id,season_id,trainer_id,status", season_id=season_id, trainer_id=trainer_id)
        save = self._one(
            "save_files", "id,season_id,trainer_id,sha256,parser_status,parser_version,deleted_at",
            id=save_file_id, season_id=season_id, trainer_id=trainer_id,
        )
        parsed = None
        if save and save.get("parser_version"):
            parsed = self._one(
                "parsed_saves", "id,save_file_id,parser_version,schema_version,status,payload",
                save_file_id=save_file_id, parser_version=save["parser_version"],
            )
        return TeamLockSource(season, matchday, participant, save, parsed)

    def upsert_with_activity(self, mutation: TeamLockMutation) -> TeamLockRecord:
        args = {"p_" + field.name: deepcopy(getattr(mutation, field.name)) for field in fields(mutation)}
        try:
            rows = self._client.rpc(RPC_NAME, args).execute().data
        except Exception as exc:
            error = RPC_ERRORS.get(str(getattr(exc, "code", "")), PersistenceError)
            raise error("Team lock mutation was rejected." if error is not PersistenceError else "Team lock backend is unavailable.") from exc
        if not isinstance(rows, list) or len(rows) != 1:
            raise PersistenceError("Team lock mutation returned no unique receipt.")
        try:
            record = TeamLockRecord(**{f.name: deepcopy(rows[0][f.name]) for f in fields(TeamLockRecord)})
            for key in ("season_id", "matchday_id", "trainer_id", "season_player_id", "save_file_id", "save_sha256"):
                if getattr(record, key) != getattr(mutation, key):
                    raise ValueError("Mismatched receipt")
            return record
        except (KeyError, TypeError, ValueError) as exc:
            raise PersistenceError("Team lock mutation returned an invalid receipt.") from exc
