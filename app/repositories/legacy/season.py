from __future__ import annotations

from typing import Any

from app.domain.archives import SeasonArchive
from app.domain.seasons import Season, SeasonVersion
from app.repositories import mappers
from app.repositories.legacy.settings_store import LegacySettingsStore


class LegacySeasonRepository:
    def __init__(
        self,
        *,
        settings: LegacySettingsStore | None = None,
        season_id: str = mappers.LEGACY_SEASON_ID,
    ) -> None:
        self.settings = settings or LegacySettingsStore()
        self.season_id = season_id

    def load_document(self, *, fallback_players: tuple[str, ...] = ()) -> dict[str, Any]:
        from app.season.config import SEASON_CONFIG_KEY, coerce_season_document

        raw = mappers.json_loads(self.settings.get(SEASON_CONFIG_KEY), None)
        return coerce_season_document(raw, fallback_players=list(fallback_players))

    def save_document(self, document: dict[str, Any]) -> None:
        from app.season.config import SEASON_CONFIG_KEY, clear_season_config_cache, coerce_season_document

        clean = coerce_season_document(document)
        self.settings.set(SEASON_CONFIG_KEY, mappers.json_dumps(clean))
        clear_season_config_cache()

    def get_active_season(self) -> Season:
        from app.season.archive import SEASON_LIFECYCLE_KEY

        document = self.load_document()
        versions = self.list_versions()
        active_version_id = str(document.get("active_version_id") or (versions[-1].id if versions else ""))
        name = versions[-1].name if versions else "Temporada actual"
        raw = mappers.json_loads(self.settings.get(SEASON_LIFECYCLE_KEY), {})
        return mappers.season_from_lifecycle(
            raw if isinstance(raw, dict) else {},
            season_id=self.season_id,
            name=name,
            active_version_id=active_version_id,
        )

    def save_active_season(self, season: Season) -> Season:
        from app.season.archive import SEASON_LIFECYCLE_KEY

        previous = mappers.json_loads(self.settings.get(SEASON_LIFECYCLE_KEY), {})
        payload = mappers.lifecycle_from_season(
            season,
            previous=previous if isinstance(previous, dict) else {},
        )
        self.settings.set(SEASON_LIFECYCLE_KEY, mappers.json_dumps(payload))
        return self.get_active_season()

    def list_versions(self) -> tuple[SeasonVersion, ...]:
        document = self.load_document()
        versions = [
            mappers.season_version_from_any(item, season_id=self.season_id)
            for item in (document.get("versions") if isinstance(document.get("versions"), list) else [])
        ]
        return tuple(versions)

    def save_versions(self, versions: tuple[SeasonVersion, ...], *, active_version_id: str) -> None:
        payload = {
            "schema_version": 1,
            "active_version_id": active_version_id,
            "versions": [mappers.season_version_to_legacy_dict(version) for version in versions],
        }
        self.save_document(payload)

    def list_archives(self) -> tuple[SeasonArchive, ...]:
        from app.season.archive import SEASON_ARCHIVES_KEY

        raw = mappers.json_loads(self.settings.get(SEASON_ARCHIVES_KEY), [])
        source = raw if isinstance(raw, list) else []
        archives = [
            archive
            for archive in (mappers.season_archive_from_legacy(item) for item in source)
            if archive
        ]
        return tuple(sorted(archives, key=lambda item: item.archived_at, reverse=True))

    def save_archives(self, archives: tuple[SeasonArchive, ...]) -> None:
        from app.season.archive import SEASON_ARCHIVES_KEY

        legacy_payload = []
        for archive in archives:
            legacy = archive.metadata.get("legacy") if isinstance(archive.metadata, dict) else None
            legacy_payload.append(dict(legacy) if isinstance(legacy, dict) else mappers.to_jsonable(archive))
        self.settings.set(SEASON_ARCHIVES_KEY, mappers.json_dumps(legacy_payload))
