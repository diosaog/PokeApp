from __future__ import annotations

from app.domain.trials import TrialCase
from app.repositories import mappers
from app.repositories.legacy.settings_store import LegacySettingsStore


CUP_STATE_KEYS = {
    "swiss": "copa_swiss_state",
    "elim": "copa_elim_state",
    "doubles": "copa_dobles_state",
}
TRIALS_STATE_KEY = "juicios_state_v1"


class LegacyCompetitionRepository:
    def __init__(
        self,
        *,
        settings: LegacySettingsStore | None = None,
        season_id: str = mappers.LEGACY_SEASON_ID,
    ) -> None:
        self.settings = settings or LegacySettingsStore()
        self.season_id = season_id

    def load_cup_state(self, key: str) -> dict:
        setting_key = CUP_STATE_KEYS.get(str(key), str(key))
        raw = mappers.json_loads(self.settings.get(setting_key), {})
        return dict(raw) if isinstance(raw, dict) else {}

    def save_cup_state(self, key: str, state: dict) -> None:
        setting_key = CUP_STATE_KEYS.get(str(key), str(key))
        self.settings.set(setting_key, mappers.json_dumps(dict(state or {})))

    def list_trials(self) -> tuple[TrialCase, ...]:
        raw = mappers.json_loads(self.settings.get(TRIALS_STATE_KEY), {})
        cases = raw.get("cases") if isinstance(raw, dict) and isinstance(raw.get("cases"), list) else []
        out = [
            case
            for case in (mappers.trial_case_from_legacy(item, season_id=self.season_id) for item in cases)
            if case
        ]
        return tuple(sorted(out, key=lambda item: (item.case_no, item.id), reverse=True))

    def save_trials(self, cases: tuple[TrialCase, ...]) -> None:
        legacy_cases = []
        for case in cases:
            legacy = case.metadata.get("legacy") if isinstance(case.metadata, dict) else None
            legacy_cases.append(dict(legacy) if isinstance(legacy, dict) else mappers.to_jsonable(case))
        payload = {
            "next_id": max((mappers.as_int(case.id, 0) for case in cases), default=0) + 1,
            "next_case_no": max((case.case_no for case in cases), default=0) + 1,
            "cases": legacy_cases,
        }
        self.settings.set(TRIALS_STATE_KEY, mappers.json_dumps(payload))
