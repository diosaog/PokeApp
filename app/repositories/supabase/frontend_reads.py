"""Read-only, bounded PostgREST transport; filter names are server constants."""

from typing import Any, Protocol
import logging
import re
from httpx import ReadError, RemoteProtocolError
from app.repositories.errors import PersistenceError

logger = logging.getLogger(__name__)


def _report_failure(operation: str, error: Exception) -> None:
    # Hosting diagnostics must never include SQL, rows, credentials, exception
    # messages or response bodies. Only a bounded Python exception class is logged.
    category = type(error).__name__
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", category) is None:
        category = "UnknownError"
    logger.warning("frontend_read_failed operation=%s cause=%s", operation, category)


def _execute_read(query, operation: str):
    # These SELECTs and explicitly read-only RPCs have no durable effects.
    # A dropped response can be retried once; mutation repositories must not use
    # this helper. Do not retry status errors, malformed data or arbitrary failures.
    # A dropped or stale pooled connection fails before any answer; the retry
    # runs on a fresh one.
    try:
        return query.execute().data
    except (ReadError, RemoteProtocolError) as error:
        logger.warning(
            "frontend_read_retry operation=%s cause=%s", operation, type(error).__name__
        )
        return query.execute().data


class FrontendReadRepository(Protocol):
    def shield_targets(self, season_id: str, trainer_id: str) -> list[str]: ...
    def league_general(self, season_id: str) -> dict | None: ...
    def initial_observations(self, season_id: str) -> list[dict]: ...
    def observed_progress(self, season_id: str, trainer_id: str | None = None) -> list[dict] | None: ...
    def observed_entities_for_locks(
        self, season_id: str, locks: list[dict]
    ) -> dict[tuple[str, str, int, int], str]: ...
    def public_pokemon_flags(
        self, season_id: str, pokemon_entity_ids: list[str]
    ) -> dict[str, list[str]]: ...

    def rows(
        self,
        table: str,
        columns: str,
        *,
        filters: dict | None = None,
        order: str | None = None,
        offset: int = 0,
        limit: int = 500,
    ) -> list[dict]: ...


class SupabaseFrontendReadRepository:
    def __init__(self, client: Any):
        self._client = client

    @classmethod
    def from_url_key(cls, url: str, key: str):
        from app.repositories.supabase.http import create_client

        return cls(create_client(url, key))

    def rows(self, table, columns, *, filters=None, order=None, offset=0, limit=500):
        try:
            query = self._client.table(table).select(columns)
            for key, value in (filters or {}).items():
                query = (
                    query.is_(key, "null") if value is None else query.eq(key, value)
                )
            query = query.order(order or columns.split(",")[0]).range(
                offset, offset + limit - 1
            )
            rows = _execute_read(query, "rows")
            if not isinstance(rows, list):
                raise ValueError("Invalid read")
            return rows
        except Exception as exc:
            _report_failure("rows", exc)
            raise PersistenceError("Read backend unavailable") from exc

    def league_general(self, season_id):
        try:
            data = _execute_read(
                self._client.rpc("league_general_read", {"p_season_id": season_id}),
                "league_general",
            )
            if data is not None and not isinstance(data, dict):
                raise ValueError("Invalid league read")
            return data
        except Exception as exc:
            _report_failure("league_general", exc)
            raise PersistenceError("League read backend unavailable") from exc

    def initial_observations(self, season_id):
        try:
            data = _execute_read(
                self._client.rpc("initial_assignment_observations", {"sid": season_id}),
                "initial_observations",
            )
            if not isinstance(data, list):
                raise ValueError("Invalid observed progress")
            return data
        except Exception as exc:
            _report_failure("initial_observations", exc)
            raise PersistenceError("Observed progress unavailable") from exc

    def shield_targets(self, season_id, trainer_id):
        try:
            data = _execute_read(
                self._client.rpc("inventory_shield_targets", {"sid": season_id, "tid": trainer_id}),
                "shield_targets",
            )
            if not isinstance(data, list) or any(not isinstance(v, str) for v in data):
                raise ValueError("Invalid target eligibility")
            return data
        except Exception as exc:
            _report_failure("shield_targets", exc)
            raise PersistenceError("Target eligibility unavailable") from exc

    def observed_progress(self, season_id, trainer_id=None):
        try:
            data = _execute_read(
                self._client.rpc("observed_progress_read", {
                    "p_season_id": season_id, "p_trainer_id": trainer_id,
                }), "observed_progress",
            )
            if data is not None and (not isinstance(data, list) or len(data) > 500):
                raise ValueError("Invalid progress read")
            return data
        except Exception as exc:
            _report_failure("observed_progress", exc)
            raise PersistenceError("Observed progress unavailable") from exc

    def public_pokemon_flags(self, season_id, pokemon_entity_ids):
        """Read only the three already-public state labels for known entities."""
        try:
            ids = sorted({value for value in pokemon_entity_ids if isinstance(value, str)})
            if len(ids) > 500:
                raise ValueError("Too many Pokemon entities")
            if not ids:
                return {}
            rows = _execute_read(
                self._client.table("pokemon_entity_flags")
                .select("pokemon_entity_id,flag_type,flag_value,flag_timestamp")
                .eq("season_id", season_id)
                .in_("pokemon_entity_id", ids)
                .in_("flag_type", ["robbed", "robado_at", "blindado", "revivido_at"])
                .range(0, 1999),
                "public_pokemon_flags",
            )
            if not isinstance(rows, list) or len(rows) > 2000:
                raise ValueError("Invalid Pokemon flags")
            result = {entity_id: [] for entity_id in ids}
            labels = {"robbed": "robado", "robado_at": "robado",
                      "blindado": "blindado", "revivido_at": "revivido"}
            for row in rows:
                entity_id, kind = row.get("pokemon_entity_id"), row.get("flag_type")
                if entity_id not in result or kind not in labels:
                    continue
                active = (
                    kind == "blindado" and row.get("flag_value") is True
                ) or (
                    kind == "robbed" and row.get("flag_value") is True
                ) or (
                    kind in ("robado_at", "revivido_at")
                    and row.get("flag_timestamp") is not None
                )
                if active and labels[kind] not in result[entity_id]:
                    result[entity_id].append(labels[kind])
            return result
        except Exception as exc:
            _report_failure("public_pokemon_flags", exc)
            raise PersistenceError("Pokemon flags unavailable") from exc

    def observed_entities_for_locks(self, season_id, locks):
        """Resolve only public lock slots through one bounded batch read pair.

        The inventory projection needs entity IDs to attach public team-lock
        Pokémon to existing competitive records.  It must never inspect a rival
        parsed save.  The lock-provided trainer/save pairs therefore scope both
        reads, and malformed or ambiguous rows fail closed.
        """
        try:
            pairs = set()
            for lock in locks:
                trainer_id, save_file_id = lock.get("trainer_id"), lock.get("save_file_id")
                if not isinstance(trainer_id, str) or not isinstance(save_file_id, str):
                    raise ValueError("Invalid lock identity")
                pairs.add((trainer_id, save_file_id))
            if len({trainer for trainer, _ in pairs}) != len(pairs):
                raise ValueError("Conflicting lock saves")
            if not pairs:
                return {}
            if len(pairs) > 500:
                raise ValueError("Too many locks")
            trainer_ids = sorted({trainer_id for trainer_id, _ in pairs})
            save_ids = sorted({save_file_id for _, save_file_id in pairs})
            observations = _execute_read(
                self._client.table("pokemon_observations")
                .select(
                    "trainer_id,save_file_id,pokemon_entity_id,source,box_number,slot_number,outcome"
                )
                .eq("season_id", season_id)
                .eq("source", "party")
                .eq("box_number", 0)
                .in_("slot_number", [1, 2, 3, 4, 5, 6])
                .in_("trainer_id", trainer_ids)
                .in_("save_file_id", save_ids)
                .range(0, 500),
                "observed_entities_for_locks_observations",
            )
            if not isinstance(observations, list) or len(observations) > 500:
                raise ValueError("Invalid observation collection")
            candidates = {}
            entity_ids = set()
            for observation in observations:
                if not isinstance(observation, dict):
                    raise ValueError("Invalid observation")
                pair = (observation.get("trainer_id"), observation.get("save_file_id"))
                if pair not in pairs or observation.get("outcome") not in ("NEW", "MATCHED"):
                    continue
                entity_id = observation.get("pokemon_entity_id")
                key = (
                    observation.get("trainer_id"),
                    observation.get("source"),
                    observation.get("box_number"),
                    observation.get("slot_number"),
                )
                if (not isinstance(entity_id, str)
                    or key[1] != "party" or type(key[2]) is not int or key[2] != 0
                    or type(key[3]) is not int or not 1 <= key[3] <= 6):
                    raise ValueError("Invalid observation identity")
                previous = candidates.get(key)
                if previous is not None:
                    raise ValueError("Ambiguous observation identity")
                candidates[key] = entity_id
                entity_ids.add(entity_id)
            if not entity_ids:
                return {}
            if len(entity_ids) > 500:
                raise ValueError("Too many entities")
            entities = _execute_read(
                self._client.table("pokemon_entities")
                .select("id,owner_trainer_id,identity_status")
                .eq("season_id", season_id)
                .eq("identity_status", "unambiguous")
                .in_("id", sorted(entity_ids))
                .range(0, 500),
                "observed_entities_for_locks_entities",
            )
            if not isinstance(entities, list) or len(entities) > 500:
                raise ValueError("Invalid entity collection")
            owners = {}
            for row in entities:
                if not isinstance(row, dict):
                    raise ValueError("Invalid entity")
                if row.get("identity_status") != "unambiguous":
                    continue
                entity_id, owner = row.get("id"), row.get("owner_trainer_id")
                if not isinstance(entity_id, str) or owner not in trainer_ids:
                    continue
                previous = owners.get(entity_id)
                if previous is not None:
                    raise ValueError("Ambiguous entity owner")
                owners[entity_id] = owner
            return {
                key: entity_id
                for key, entity_id in candidates.items()
                if owners.get(entity_id) == key[0]
            }
        except Exception as exc:
            _report_failure("observed_entities_for_locks", exc)
            raise PersistenceError("Public team identity unavailable") from exc
