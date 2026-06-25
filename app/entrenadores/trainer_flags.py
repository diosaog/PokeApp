from __future__ import annotations

import json
import time
import unicodedata
from typing import Any

from storage import settings_get, settings_set

TRAINER_FLAGS_KEY = "trainer_flags"
TRAINER_ROBBED_HISTORY_WATERMARK_KEY = "trainer_robbed_history_watermark"
_HISTORY_SYNC_TTL_SECONDS = 15
_history_sync_at = 0.0
_history_sync_key = ""


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


def is_trainer_retired(trainer: str | None) -> bool:
    return bool(trainer_flags_for(trainer).get("retired"))


def is_trainer_robbed(trainer: str | None) -> bool:
    return bool(trainer_flags_for(trainer).get("robbed"))


def retired_trainers() -> set[str]:
    return {
        trainer
        for trainer, flags in _load_raw().items()
        if bool(flags.get("retired"))
    }


def robbed_trainers() -> set[str]:
    return {
        trainer
        for trainer, flags in _load_raw().items()
        if bool(flags.get("robbed")) and not bool(flags.get("retired"))
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
        if data.get("retired"):
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
        flags[trainer] = data

    if changed:
        _save_raw(flags)
    return robbed_trainers()


def status_labels_for(trainer: str | None) -> list[str]:
    flags = trainer_flags_for(trainer)
    labels: list[str] = []
    if flags.get("retired"):
        labels.append("Retirado")
    if flags.get("robbed") and not flags.get("retired"):
        labels.append("Robado")
    return labels


def format_trainer_with_flags(trainer: str | None) -> str:
    name = str(trainer or "").strip()
    labels = status_labels_for(name)
    return name if not labels else f"{name} [{' | '.join(labels)}]"


def set_trainer_retired(trainer: str, *, by_user: str | None = None) -> None:
    name = str(trainer or "").strip()
    if not name:
        return
    flags = _load_raw()
    data = dict(flags.get(name, {}))
    data["retired"] = True
    data["retired_at"] = _now()
    if by_user:
        data["retired_by"] = str(by_user)
    data.pop("robbed", None)
    data.pop("robbed_at", None)
    data.pop("robbed_by", None)
    data.pop("robbed_source", None)
    flags[name] = data
    _save_raw(flags)


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
            data.pop("robbed", None)
            data.pop("robbed_at", None)
            data.pop("robbed_by", None)
            data.pop("robbed_source", None)
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
    if not all(bool(flags.get(trainer, {}).get("robbed")) for trainer in active):
        return False
    for trainer in active:
        data = dict(flags.get(trainer, {}))
        data.pop("robbed", None)
        data.pop("robbed_at", None)
        data.pop("robbed_by", None)
        data.pop("robbed_source", None)
        flags[trainer] = data
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
    current = dict(flags.get(name, {}))
    if current.get("retired"):
        return {"marked": False, "already_robbed": False, "cycle_reset": False}
    if current.get("robbed"):
        return {"marked": False, "already_robbed": True, "cycle_reset": False}

    current["robbed"] = True
    current["robbed_at"] = _now()
    current["robbed_source"] = "live"
    if by_user:
        current["robbed_by"] = str(by_user)
    flags[name] = current
    _save_raw(flags)

    cycle_reset = reset_robbed_cycle_if_complete(active_trainers)
    return {"marked": True, "already_robbed": False, "cycle_reset": cycle_reset}
