from __future__ import annotations

from typing import Any

from app.domain.trainers import Trainer, TrainerFlags, TrainerStatus
from app.domain.services import trainers as trainer_domain
from app.repositories import mappers
from app.repositories.legacy.settings_store import LegacySettingsStore


TRAINER_FLAGS_KEY = "trainer_flags"


class LegacyTrainerRepository:
    def __init__(self, *, settings: LegacySettingsStore | None = None) -> None:
        self.settings = settings or LegacySettingsStore()

    def list_trainers(self) -> tuple[Trainer, ...]:
        try:
            from utils import USERS

            source = USERS
        except Exception:
            source = {}
        return tuple(mappers.trainer_from_legacy(name, raw) for name, raw in source.items())

    def load_flag_map(self) -> dict[str, dict[str, Any]]:
        raw = mappers.json_loads(self.settings.get(TRAINER_FLAGS_KEY), {})
        source = raw if isinstance(raw, dict) else {}
        return {
            str(trainer): dict(flags)
            for trainer, flags in source.items()
            if str(trainer).strip() and isinstance(flags, dict)
        }

    def save_flag_map(self, flags: dict[str, dict[str, Any]]) -> None:
        clean = {
            str(trainer): dict(values)
            for trainer, values in (flags or {}).items()
            if str(trainer).strip() and isinstance(values, dict)
        }
        self.settings.set(TRAINER_FLAGS_KEY, mappers.json_dumps(clean))

    def get_status(self, trainer_id: str) -> TrainerStatus:
        flags = self.load_flag_map().get(str(trainer_id), {})
        return trainer_domain.status_from_flags(flags)

    def set_status(self, trainer_id: str, status: TrainerStatus, *, by_user: str, now: int) -> TrainerStatus:
        all_flags = self.load_flag_map()
        current = dict(all_flags.get(str(trainer_id), {}))
        next_flags = trainer_domain.apply_status_transition(
            current,
            status,
            by_user=by_user,
            now=now,
        )
        all_flags[str(trainer_id)] = next_flags
        self.save_flag_map(all_flags)
        return trainer_domain.status_from_flags(next_flags)

    def get_flags(self, trainer_id: str) -> TrainerFlags:
        return mappers.trainer_flags_from_legacy(
            str(trainer_id),
            self.load_flag_map().get(str(trainer_id), {}),
        )

    def set_flags(self, flags: TrainerFlags) -> TrainerFlags:
        all_flags = self.load_flag_map()
        previous = dict(all_flags.get(flags.trainer_id, {}))
        all_flags[flags.trainer_id] = mappers.trainer_flags_to_legacy(flags, previous=previous)
        self.save_flag_map(all_flags)
        return self.get_flags(flags.trainer_id)

    def mark_robbed(self, trainer_id: str, *, by_user: str, active_trainers: tuple[str, ...], now: int) -> dict[str, dict[str, Any]]:
        result = trainer_domain.mark_trainer_robbed(
            self.load_flag_map(),
            trainer_id,
            by_user=by_user,
            active_trainers=active_trainers,
            now=now,
        )
        self.save_flag_map(result.flags_by_trainer)
        return result.flags_by_trainer
