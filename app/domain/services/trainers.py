from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from app.domain.trainers import TrainerStatus


INACTIVE_STATUSES = {
    TrainerStatus.RETIRED.value,
    TrainerStatus.ABANDONED.value,
    TrainerStatus.DISQUALIFIED.value,
}
STATUS_LABELS = {
    TrainerStatus.ACTIVE.value: "Activo",
    TrainerStatus.RETIRED.value: "Retirado",
    TrainerStatus.ABANDONED.value: "Abandono",
    TrainerStatus.DISQUALIFIED.value: "Descalificado",
}
ROBBED_FLAG_KEYS = (
    "robbed",
    "robbed_at",
    "robbed_by",
    "robbed_source",
    "robbed_seed_id",
    "robbed_note",
)


@dataclass(frozen=True)
class RobbedFlagResult:
    flags_by_trainer: dict[str, dict[str, Any]]
    marked: bool
    already_robbed: bool
    cycle_reset: bool


def status_from_flags(flags: Mapping[str, Any] | None) -> TrainerStatus:
    data = flags if isinstance(flags, Mapping) else {}
    raw_status = str(data.get("status") or "").strip().lower()
    for status in TrainerStatus:
        if raw_status == status.value:
            return status
    raw_reason = str(data.get("inactive_reason") or "").strip().lower()
    for status in (TrainerStatus.RETIRED, TrainerStatus.ABANDONED, TrainerStatus.DISQUALIFIED):
        if raw_reason == status.value:
            return status
    if data.get("abandoned"):
        return TrainerStatus.ABANDONED
    if data.get("disqualified"):
        return TrainerStatus.DISQUALIFIED
    if data.get("retired"):
        return TrainerStatus.RETIRED
    return TrainerStatus.ACTIVE


def is_inactive_status(status: TrainerStatus | str) -> bool:
    return str(status.value if isinstance(status, TrainerStatus) else status) in INACTIVE_STATUSES


def clear_robbed_flag(flags: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(flags)
    for key in ROBBED_FLAG_KEYS:
        data.pop(key, None)
    return data


def status_labels_for_flags(flags: Mapping[str, Any] | None) -> tuple[str, ...]:
    status = status_from_flags(flags)
    labels: list[str] = []
    if status != TrainerStatus.ACTIVE:
        labels.append(STATUS_LABELS.get(status.value, "Inactivo"))
    elif isinstance(flags, Mapping) and flags.get("robbed"):
        labels.append("Robado")
    return tuple(labels)


def apply_status_transition(
    current_flags: Mapping[str, Any] | None,
    status: TrainerStatus | str,
    *,
    by_user: str = "",
    note: str = "",
    now: int,
) -> dict[str, Any]:
    normalized = str(status.value if isinstance(status, TrainerStatus) else status).strip().lower()
    if normalized == TrainerStatus.ACTIVE.value:
        raise ValueError("La reactivacion no esta permitida por las reglas actuales.")
    if normalized not in INACTIVE_STATUSES:
        raise ValueError("Estado de entrenador no valido.")

    data = clear_robbed_flag(current_flags or {})
    data["status"] = normalized
    data["inactive"] = True
    data["inactive_reason"] = normalized
    data["inactive_at"] = int(now)
    data["inactive_by"] = str(by_user or "")
    if note:
        data["inactive_note"] = str(note)
    data["retired"] = True
    data.setdefault("retired_at", int(now))
    if by_user:
        data.setdefault("retired_by", str(by_user))
    if normalized == TrainerStatus.ABANDONED.value:
        data["abandoned"] = True
        data["abandoned_at"] = int(now)
        if by_user:
            data["abandoned_by"] = str(by_user)
    elif normalized == TrainerStatus.DISQUALIFIED.value:
        data["disqualified"] = True
        data["disqualified_at"] = int(now)
        if by_user:
            data["disqualified_by"] = str(by_user)
    return data


def reset_robbed_cycle_if_complete(
    flags_by_trainer: Mapping[str, Mapping[str, Any]],
    active_trainers: list[str] | tuple[str, ...],
) -> tuple[dict[str, dict[str, Any]], bool]:
    active = [str(trainer or "").strip() for trainer in active_trainers if str(trainer or "").strip()]
    flags = {str(trainer): dict(values) for trainer, values in flags_by_trainer.items()}
    if not active:
        return flags, False
    if not all(bool(flags.get(trainer, {}).get("robbed")) for trainer in active):
        return flags, False
    for trainer in active:
        flags[trainer] = clear_robbed_flag(flags.get(trainer, {}))
    return flags, True


def mark_trainer_robbed(
    flags_by_trainer: Mapping[str, Mapping[str, Any]],
    trainer: str,
    *,
    by_user: str = "",
    active_trainers: list[str] | tuple[str, ...] = (),
    now: int,
) -> RobbedFlagResult:
    name = str(trainer or "").strip()
    flags = {str(key): dict(value) for key, value in flags_by_trainer.items()}
    if not name:
        return RobbedFlagResult(flags, False, False, False)

    current = dict(flags.get(name, {}))
    if status_from_flags(current) != TrainerStatus.ACTIVE:
        return RobbedFlagResult(flags, False, False, False)
    if current.get("robbed"):
        return RobbedFlagResult(flags, False, True, False)

    current["robbed"] = True
    current["robbed_at"] = int(now)
    current["robbed_source"] = "live"
    if by_user:
        current["robbed_by"] = str(by_user)
    flags[name] = current
    flags, cycle_reset = reset_robbed_cycle_if_complete(flags, active_trainers)
    return RobbedFlagResult(flags, True, False, cycle_reset)
