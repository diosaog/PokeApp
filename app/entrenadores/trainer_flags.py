from __future__ import annotations

import json
import time
import unicodedata
from typing import Any

from app.domain.services import trainers as trainer_domain
from app.liga.permissions import require_league_admin
from storage import settings_get, settings_set

TRAINER_FLAGS_KEY = "trainer_flags"
TRAINER_ROBBED_HISTORY_WATERMARK_KEY = "trainer_robbed_history_watermark"
_HISTORY_SYNC_TTL_SECONDS = 15
_history_sync_at = 0.0
_history_sync_key = ""

TRAINER_STATUS_ACTIVE = "active"
TRAINER_STATUS_RETIRED = "retired"
TRAINER_STATUS_ABANDONED = "abandoned"
TRAINER_STATUS_DISQUALIFIED = "disqualified"
TRAINER_STATUSES = {
    TRAINER_STATUS_ACTIVE,
    TRAINER_STATUS_RETIRED,
    TRAINER_STATUS_ABANDONED,
    TRAINER_STATUS_DISQUALIFIED,
}
INACTIVE_TRAINER_STATUSES = {
    TRAINER_STATUS_RETIRED,
    TRAINER_STATUS_ABANDONED,
    TRAINER_STATUS_DISQUALIFIED,
}
TRAINER_STATUS_LABELS = {
    TRAINER_STATUS_ACTIVE: "Activo",
    TRAINER_STATUS_RETIRED: "Retirado",
    TRAINER_STATUS_ABANDONED: "Abandono",
    TRAINER_STATUS_DISQUALIFIED: "Descalificado",
}

TRAINER_FLAG_ROBBED = "robbed"
ROBBED_FLAG_KEYS = (
    "robbed",
    "robbed_at",
    "robbed_by",
    "robbed_source",
    "robbed_seed_id",
    "robbed_note",
)


def _now() -> int:
    return int(time.time())


def _load_raw() -> dict[str, dict[str, Any]]:
    try:
        raw = settings_get(TRAINER_FLAGS_KEY)
        data = json.loads(raw or "{}")
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}

    out: dict[str, dict[str, Any]] = {}
    for trainer, flags in data.items():
        name = str(trainer or "").strip()
        if not name or not isinstance(flags, dict):
            continue
        out[name] = dict(flags)
    return out


def _save_raw(flags: dict[str, dict[str, Any]]) -> None:
    clean = {
        str(trainer): dict(values)
        for trainer, values in flags.items()
        if str(trainer).strip() and isinstance(values, dict) and values
    }
    settings_set(TRAINER_FLAGS_KEY, json.dumps(clean, ensure_ascii=False))


def _row_value(row: Any, index: int, key: str) -> Any:
    if isinstance(row, dict):
        return row.get(key)
    try:
        return row[index]
    except Exception:
        return None


def _normalised_item_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _history_watermark() -> int:
    try:
        return max(0, int(settings_get(TRAINER_ROBBED_HISTORY_WATERMARK_KEY) or 0))
    except Exception:
        return 0


def _set_history_watermark(value: int) -> None:
    try:
        settings_set(TRAINER_ROBBED_HISTORY_WATERMARK_KEY, str(max(0, int(value))))
    except Exception:
        pass


def _active_filter(
    active_trainers: list[str] | tuple[str, ...] | set[str] | None,
) -> tuple[set[str], bool]:
    if active_trainers is None:
        return set(), False
    return {
        str(trainer or "").strip()
        for trainer in active_trainers
        if str(trainer or "").strip()
    }, True


def _robbery_meta_from_redemption(row: Any) -> tuple[str, dict[str, Any]] | None:
    item = _row_value(row, 3, "item")
    payload_raw = _row_value(row, 4, "payload_json")
    payload: dict[str, Any] = {}
    if isinstance(payload_raw, str) and payload_raw.strip():
        try:
            parsed = json.loads(payload_raw)
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = {}

    payload_type = str(payload.get("type") or "").strip().lower()
    if payload_type != "steal" and _normalised_item_name(item) != "robar pokemon":
        return None

    target = str(
        payload.get("from")
        or payload.get("target")
        or payload.get("victim")
        or ""
    ).strip()
    if not target:
        return None

    return target, {
        "redemption_id": _as_int(_row_value(row, 0, "id")),
        "robbed_by": str(_row_value(row, 2, "user") or "").strip(),
        "robbed_at": _row_value(row, 5, "created_at"),
        "robbed_source": "history",
    }


def _redemption_rows(limit: int = 2000) -> list[Any]:
    try:
        from storage import list_redemptions

        return list(list_redemptions(None, limit=limit) or [])
    except Exception:
        return []


def _historical_robbed_sources(limit: int = 2000) -> dict[str, dict[str, Any]]:
    rows = _redemption_rows(limit=limit)
    if not rows:
        return {}

    sources: dict[str, dict[str, Any]] = {}
    watermark = _history_watermark()
    for row in rows or []:
        parsed = _robbery_meta_from_redemption(row)
        if not parsed:
            continue
        target, meta = parsed
        if int(meta.get("redemption_id") or 0) <= watermark:
            continue
        if target in sources:
            continue
        sources[target] = meta
    return sources


def _latest_robbery_redemption_id(limit: int = 2000) -> int:
    latest = 0
    for row in _redemption_rows(limit=limit):
        parsed = _robbery_meta_from_redemption(row)
        if not parsed:
            continue
        _target, meta = parsed
        latest = max(latest, int(meta.get("redemption_id") or 0))
    return latest


def all_trainer_flags() -> dict[str, dict[str, Any]]:
    return _load_raw()


def trainer_flags_for(trainer: str | None) -> dict[str, Any]:
    name = str(trainer or "").strip()
    if not name:
        return {}
    return dict(_load_raw().get(name, {}))


def _status_from_flags(flags: dict[str, Any] | None) -> str:
    return trainer_domain.status_from_flags(flags).value


def trainer_status(trainer: str | None) -> str:
    return _status_from_flags(trainer_flags_for(trainer))


def trainer_status_label(trainer: str | None) -> str:
    return TRAINER_STATUS_LABELS.get(trainer_status(trainer), "Activo")


def is_trainer_inactive(trainer: str | None) -> bool:
    return trainer_status(trainer) in INACTIVE_TRAINER_STATUSES


def is_trainer_retired(trainer: str | None) -> bool:
    """Backward-compatible inactive check used by existing pages.

    Product wording historically used "retired" for every non-competing trainer.
    New code should prefer trainer_status()/is_trainer_inactive().
    """
    return is_trainer_inactive(trainer)


def is_trainer_robbed(trainer: str | None) -> bool:
    return bool(trainer_flags_for(trainer).get("robbed"))


def retired_trainers() -> set[str]:
    return {
        trainer
        for trainer, flags in _load_raw().items()
        if _status_from_flags(flags) in INACTIVE_TRAINER_STATUSES
    }


def robbed_trainers() -> set[str]:
    return {
        trainer
        for trainer, flags in _load_raw().items()
        if bool(flags.get("robbed"))
        and _status_from_flags(flags) == TRAINER_STATUS_ACTIVE
    }


def sync_trainer_robbed_flags_from_history(
    active_trainers: list[str] | tuple[str, ...] | set[str] | None = None,
    *,
    force: bool = False,
) -> set[str]:
    global _history_sync_at, _history_sync_key

    active, has_filter = _active_filter(active_trainers)
    if has_filter and not active:
        return robbed_trainers()

    sync_key = "|".join(sorted(active)) if has_filter else "*"
    now = time.time()
    if (
        not force
        and sync_key == _history_sync_key
        and now - _history_sync_at < _HISTORY_SYNC_TTL_SECONDS
    ):
        return robbed_trainers()
    _history_sync_at = now
    _history_sync_key = sync_key

    sources = _historical_robbed_sources()
    if not sources:
        return robbed_trainers()

    flags = _load_raw()
    changed = False
    for trainer, meta in sources.items():
        if has_filter and trainer not in active:
            continue
        data = dict(flags.get(trainer, {}))
        if _status_from_flags(data) != TRAINER_STATUS_ACTIVE:
            continue
        if not data.get("robbed"):
            data["robbed"] = True
            data["robbed_source"] = str(meta.get("robbed_source") or "history")
            changed = True
        if meta.get("robbed_by") and not data.get("robbed_by"):
            data["robbed_by"] = str(meta["robbed_by"])
            changed = True
        if meta.get("robbed_at") and not data.get("robbed_at"):
            try:
                data["robbed_at"] = int(meta["robbed_at"])
            except Exception:
                data["robbed_at"] = meta["robbed_at"]
            changed = True
        if meta.get("robbed_seed_id") and not data.get("robbed_seed_id"):
            data["robbed_seed_id"] = str(meta["robbed_seed_id"])
            changed = True
        if meta.get("robbed_note") and not data.get("robbed_note"):
            data["robbed_note"] = str(meta["robbed_note"])
            changed = True
        flags[trainer] = data

    if changed:
        _save_raw(flags)
    return robbed_trainers()


def status_labels_for(trainer: str | None) -> list[str]:
    flags = trainer_flags_for(trainer)
    return list(trainer_domain.status_labels_for_flags(flags))


def format_trainer_with_flags(trainer: str | None) -> str:
    name = str(trainer or "").strip()
    status = trainer_status(name)
    if status != TRAINER_STATUS_ACTIVE:
        return f"{name} - {TRAINER_STATUS_LABELS.get(status, 'Inactivo')}"
    return name


def _clear_robbed_flag(data: dict[str, Any]) -> None:
    cleaned = trainer_domain.clear_robbed_flag(data)
    data.clear()
    data.update(cleaned)


def set_trainer_status(
    trainer: str,
    status: str,
    *,
    by_user: str | None = None,
    note: str | None = None,
) -> None:
    require_league_admin(by_user)
    name = str(trainer or "").strip()
    if not name:
        return
    normalized = str(status or "").strip().lower()
    if normalized == TRAINER_STATUS_ACTIVE:
        raise ValueError("La reactivacion no esta permitida por las reglas actuales.")
    if normalized not in INACTIVE_TRAINER_STATUSES:
        raise ValueError("Estado de entrenador no valido.")
    flags = _load_raw()
    now = _now()
    data = trainer_domain.apply_status_transition(
        flags.get(name, {}),
        normalized,
        by_user=str(by_user or ""),
        note=str(note or ""),
        now=now,
    )
    flags[name] = data
    _save_raw(flags)


def set_trainer_retired(trainer: str, *, by_user: str | None = None) -> None:
    set_trainer_status(
        trainer,
        TRAINER_STATUS_RETIRED,
        by_user=by_user,
    )


def set_trainer_abandoned(trainer: str, *, by_user: str | None = None) -> None:
    set_trainer_status(
        trainer,
        TRAINER_STATUS_ABANDONED,
        by_user=by_user,
    )


def set_trainer_disqualified(trainer: str, *, by_user: str | None = None) -> None:
    set_trainer_status(
        trainer,
        TRAINER_STATUS_DISQUALIFIED,
        by_user=by_user,
    )


def clear_active_robbed_flags(active_trainers: list[str] | tuple[str, ...]) -> None:
    active = {
        str(trainer or "").strip()
        for trainer in active_trainers
        if str(trainer or "").strip()
    }
    if not active:
        return
    flags = _load_raw()
    changed = False
    for trainer in active:
        data = dict(flags.get(trainer, {}))
        if data.get("robbed"):
            data = trainer_domain.clear_robbed_flag(data)
            flags[trainer] = data
            changed = True
    if changed:
        _save_raw(flags)


def reset_robbed_cycle_if_complete(active_trainers: list[str] | tuple[str, ...]) -> bool:
    active = [
        str(trainer or "").strip()
        for trainer in active_trainers
        if str(trainer or "").strip()
    ]
    if not active:
        return False
    flags = _load_raw()
    flags, cycle_reset = trainer_domain.reset_robbed_cycle_if_complete(flags, active)
    if not cycle_reset:
        return False
    _save_raw(flags)
    _set_history_watermark(_latest_robbery_redemption_id())
    return True


def mark_trainer_robbed(
    trainer: str,
    *,
    by_user: str | None = None,
    active_trainers: list[str] | tuple[str, ...] = (),
) -> dict[str, bool]:
    name = str(trainer or "").strip()
    if not name:
        return {"marked": False, "already_robbed": False, "cycle_reset": False}

    flags = _load_raw()
    result = trainer_domain.mark_trainer_robbed(
        flags,
        name,
        by_user=str(by_user or ""),
        active_trainers=active_trainers,
        now=_now(),
    )
    if result.marked or result.cycle_reset:
        _save_raw(result.flags_by_trainer)
    if result.cycle_reset:
        _set_history_watermark(_latest_robbery_redemption_id())
    return {
        "marked": result.marked,
        "already_robbed": result.already_robbed,
        "cycle_reset": result.cycle_reset,
    }
