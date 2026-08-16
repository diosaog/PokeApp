from __future__ import annotations

from collections.abc import Callable

from app.repositories.errors import PersistenceError


class LegacySettingsStore:
    """Small adapter around the current settings storage.

    It keeps Supabase/SQLite fallback hidden behind the repository boundary.
    Tests can inject plain callables instead of patching global storage.
    """

    def __init__(
        self,
        *,
        getter: Callable[[str], str | None] | None = None,
        setter: Callable[[str, str], None] | None = None,
    ) -> None:
        self._getter = getter
        self._setter = setter

    def get(self, key: str) -> str | None:
        getter = self._getter
        if getter is None:
            from storage import settings_get

            getter = settings_get
        try:
            return getter(key)
        except Exception as exc:
            raise PersistenceError(f"settings_get failed for {key}: {exc}") from exc

    def set(self, key: str, value: str) -> None:
        setter = self._setter
        if setter is None:
            from storage import settings_set

            setter = settings_set
        try:
            setter(key, value)
        except Exception as exc:
            raise PersistenceError(f"settings_set failed for {key}: {exc}") from exc
