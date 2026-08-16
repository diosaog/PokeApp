from __future__ import annotations

from typing import Any

from app.domain.league import MatchdaySnapshot
from app.repositories import mappers
from app.repositories.legacy.settings_store import LegacySettingsStore


LEAGUE_STATE_KEY = "league_state"


class LegacyLeagueRepository:
    def __init__(
        self,
        *,
        settings: LegacySettingsStore | None = None,
        season_id: str = mappers.LEGACY_SEASON_ID,
    ) -> None:
        self.settings = settings or LegacySettingsStore()
        self.season_id = season_id

    def load_state(self) -> dict[str, Any]:
        raw = mappers.json_loads(self.settings.get(LEAGUE_STATE_KEY), {})
        return dict(raw) if isinstance(raw, dict) else {}

    def save_state(self, state: dict[str, Any]) -> None:
        self.settings.set(LEAGUE_STATE_KEY, mappers.json_dumps(dict(state or {})))

    def list_matchday_snapshots(self) -> tuple[MatchdaySnapshot, ...]:
        from app.liga.snapshots import normalize_round_snapshots

        state = self.load_state()
        snapshots_raw = normalize_round_snapshots(
            state.get("round_snapshots")
            or state.get("league_round_snapshots")
            or {}
        )
        out: list[MatchdaySnapshot] = []
        for raw in snapshots_raw.values():
            try:
                out.append(mappers.matchday_snapshot_from_legacy(raw, season_id=self.season_id))
            except Exception:
                continue
        return tuple(sorted(out, key=lambda item: item.matchday_number))

    def save_matchday_snapshots(self, snapshots: tuple[MatchdaySnapshot, ...]) -> None:
        state = self.load_state()
        legacy: dict[str, Any] = {}
        for snapshot in snapshots:
            raw = mappers.to_jsonable(snapshot)
            legacy[str(snapshot.matchday_number)] = raw
        state["round_snapshots"] = legacy
        self.save_state(state)

    def closed_matchdays(self) -> tuple[int, ...]:
        return tuple(snapshot.matchday_number for snapshot in self.list_matchday_snapshots())

    def current_matchday_status(self) -> tuple[int, bool]:
        state = self.load_state()
        return max(1, mappers.as_int(state.get("tramo"), 1)), bool(state.get("active"))
