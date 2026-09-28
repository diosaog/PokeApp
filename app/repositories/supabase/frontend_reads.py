"""Read-only, bounded PostgREST transport; filter names are server constants."""

from typing import Any, Protocol
from app.repositories.errors import PersistenceError


class FrontendReadRepository(Protocol):
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
            rows = (
                query.order(order or columns.split(",")[0])
                .range(offset, offset + limit - 1)
                .execute()
                .data
            )
            if not isinstance(rows, list):
                raise ValueError("Invalid read")
            return rows
        except Exception as exc:
            raise PersistenceError("Read backend unavailable") from exc
