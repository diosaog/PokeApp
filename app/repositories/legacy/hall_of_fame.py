from __future__ import annotations

from app.domain.hall_of_fame import HallOfFameEntry
from app.repositories import mappers
from app.repositories.legacy.settings_store import LegacySettingsStore


HALL_OF_FAME_KEY = "hall_of_fame_v1"


class LegacyHallOfFameRepository:
    def __init__(self, *, settings: LegacySettingsStore | None = None) -> None:
        self.settings = settings or LegacySettingsStore()

    def list_entries(self) -> tuple[HallOfFameEntry, ...]:
        raw = mappers.json_loads(self.settings.get(HALL_OF_FAME_KEY), [])
        source = raw if isinstance(raw, list) else []
        entries = [
            entry
            for entry in (mappers.hall_entry_from_legacy(item) for item in source)
            if entry
        ]
        return tuple(sorted(entries, key=lambda item: item.created_at, reverse=True))

    def save_entries(self, entries: tuple[HallOfFameEntry, ...]) -> None:
        payload = [mappers.hall_entry_to_legacy(entry) for entry in entries]
        self.settings.set(HALL_OF_FAME_KEY, mappers.json_dumps(payload))

    def find_entry(self, entry_id: str) -> HallOfFameEntry | None:
        target = str(entry_id)
        for entry in self.list_entries():
            if entry.id == target:
                return entry
        return None
