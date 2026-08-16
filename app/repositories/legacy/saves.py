from __future__ import annotations

from app.domain.saves import SaveRecord
from app.repositories import mappers


class LegacySaveRepository:
    def list_saves(self, *, limit: int = 50) -> tuple[SaveRecord, ...]:
        from storage import list_saves

        return tuple(mappers.save_record_from_legacy(row) for row in list_saves(limit=int(limit)))

    def list_saves_by_trainer(self, trainer_id: str, *, limit: int = 50) -> tuple[SaveRecord, ...]:
        from storage import get_current_save_for_user, list_saves_by_user

        current = get_current_save_for_user(str(trainer_id))
        current_id = str(current[0]) if current else ""
        return tuple(
            mappers.save_record_from_legacy(row, current_save_id=current_id)
            for row in list_saves_by_user(str(trainer_id), limit=int(limit))
        )

    def get_current_save(self, trainer_id: str) -> SaveRecord | None:
        from storage import get_current_save_for_user

        row = get_current_save_for_user(str(trainer_id))
        return mappers.save_record_from_legacy(row, current_save_id=str(row[0])) if row else None

    def set_current_save(self, trainer_id: str, save_id: str) -> None:
        from storage import set_current_save_for_user

        set_current_save_for_user(str(trainer_id), mappers.as_int(save_id, 0))

    def load_save_bytes(self, save: SaveRecord) -> bytes:
        from storage import load_save_bytes

        return load_save_bytes(save.filename)
