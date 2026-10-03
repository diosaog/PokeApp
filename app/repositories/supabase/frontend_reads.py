"""Read-only, bounded PostgREST transport; filter names are server constants."""

from typing import Any, Protocol
import logging
import re
from httpx import ReadError
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
    # These SELECTs and the two explicitly read-only RPCs have no durable effects.
    # A dropped response can be retried once; mutation repositories must not use
    # this helper. Do not retry status errors, malformed data or arbitrary failures.
    try:
        return query.execute().data
    except ReadError:
        logger.warning("frontend_read_retry operation=%s cause=ReadError", operation)
        return query.execute().data


class FrontendReadRepository(Protocol):
    def league_general(self, season_id: str) -> dict | None: ...
    def initial_observations(self, season_id: str) -> list[dict]: ...

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
        from supabase import create_client

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
