from __future__ import annotations

from app.domain.activity import ActivityEvent
from app.domain.services import activity as activity_domain
from app.repositories import mappers
from app.repositories.legacy.settings_store import LegacySettingsStore


ACTIVITY_EVENTS_KEY = "activity_events_v1"
ACTIVITY_EVENT_STORAGE_LIMIT = 1000


class LegacyActivityRepository:
    def __init__(self, *, settings: LegacySettingsStore | None = None) -> None:
        self.settings = settings or LegacySettingsStore()

    def _load_all(self) -> tuple[ActivityEvent, ...]:
        raw = mappers.json_loads(self.settings.get(ACTIVITY_EVENTS_KEY), [])
        source = raw if isinstance(raw, list) else []
        events = [
            event
            for event in (mappers.activity_event_from_any(item) for item in source)
            if event
        ]
        return tuple(sorted(events, key=lambda item: (item.created_at, item.id), reverse=True))

    def _save_all(self, events: tuple[ActivityEvent, ...]) -> None:
        clean = activity_domain.dedupe_events(events)
        ordered = sorted(clean, key=lambda item: (item.created_at, item.id), reverse=True)
        payload = [mappers.activity_event_to_legacy(event) for event in ordered[:ACTIVITY_EVENT_STORAGE_LIMIT]]
        self.settings.set(ACTIVITY_EVENTS_KEY, mappers.json_dumps(payload))

    def list_all(self) -> tuple[ActivityEvent, ...]:
        return self._load_all()

    def replace_all(self, events: tuple[ActivityEvent, ...]) -> None:
        self._save_all(events)

    def append(self, event: ActivityEvent) -> ActivityEvent:
        existing = self.find_by_dedupe_key(event.dedupe_key)
        if existing:
            return existing
        self._save_all((event, *self._load_all()))
        return event

    def list_recent(
        self,
        *,
        limit: int = 5,
        viewer: str | None = None,
        event_types: tuple[str, ...] | None = None,
    ) -> tuple[ActivityEvent, ...]:
        allowed = {str(value).lower() for value in event_types or ()}
        out = []
        for event in self._load_all():
            if allowed and event.type.value not in allowed and event.type.name.lower() not in allowed:
                continue
            if activity_domain.visible_to(event, viewer).visible:
                out.append(event)
        return tuple(out[: max(0, int(limit))])

    def find_by_dedupe_key(self, dedupe_key: str) -> ActivityEvent | None:
        key = str(dedupe_key or "").strip()
        for event in self._load_all():
            if event.dedupe_key == key:
                return event
        return None
