from __future__ import annotations

import json
import time
from typing import Any

from storage import settings_get, settings_set

TRAINER_FLAGS_KEY = "trainer_flags"


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
    flags[name] = data
    _save_raw(flags)


def clear_active_robbed_flags(active_trainers: list[str] | tuple[str, ...]) -> None:
    active = {str(trainer or "").strip() for trainer in active_trainers if str(trainer or "").strip()}
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
        flags[trainer] = data
    _save_raw(flags)
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
    if by_user:
        current["robbed_by"] = str(by_user)
    flags[name] = current
    _save_raw(flags)

    cycle_reset = reset_robbed_cycle_if_complete(active_trainers)
    return {"marked": True, "already_robbed": False, "cycle_reset": cycle_reset}
