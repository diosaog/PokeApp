from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping

from app.domain.activity import ActivityEvent, ActivityEventType
from app.domain.common import JsonObject, Visibility, epoch_to_utc_iso


@dataclass(frozen=True)
class ActivityVisibilityDecision:
    visible: bool
    reason: str = "ok"


def clean_payload(value: Mapping[str, Any] | None) -> JsonObject:
    if not isinstance(value, Mapping):
        return {}
    out: JsonObject = {}
    for key, raw in value.items():
        clean_key = str(key or "").strip()
        if not clean_key:
            continue
        if isinstance(raw, (str, int, float, bool)) or raw is None:
            out[clean_key] = raw
        elif isinstance(raw, list):
            out[clean_key] = [
                item for item in raw if isinstance(item, (str, int, float, bool)) or item is None
            ]
        elif isinstance(raw, Mapping):
            out[clean_key] = {
                str(k): v
                for k, v in raw.items()
                if isinstance(k, str) and (isinstance(v, (str, int, float, bool)) or v is None)
            }
        else:
            out[clean_key] = str(raw)
    return out


def stable_digest(value: Any, *, length: int = 16) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:length]


def event_id(event_type: ActivityEventType, dedupe_key: str) -> str:
    return f"evt:{stable_digest({'type': event_type.value, 'dedupe_key': dedupe_key}, length=20)}"


def _timestamp(value: str | int) -> str:
    return epoch_to_utc_iso(value) if isinstance(value, int) else str(value or "").strip()


def build_activity_event(
    event_type: ActivityEventType,
    *,
    created_at: str | int,
    actor_id: str = "",
    trainer_id: str = "",
    context: Mapping[str, Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    visibility: Visibility = Visibility.PUBLIC,
    dedupe_key: str,
) -> ActivityEvent:
    clean_context = clean_payload(context)
    clean_payload_value = clean_payload(payload)
    clean_dedupe = str(dedupe_key or "").strip()
    if not clean_dedupe:
        clean_dedupe = f"{event_type.value}:{stable_digest(clean_payload_value)}"
    return ActivityEvent(
        id=event_id(event_type, clean_dedupe),
        type=event_type,
        created_at=_timestamp(created_at),
        actor_id=str(actor_id or "").strip(),
        trainer_id=str(trainer_id or "").strip(),
        context=clean_context,
        payload=clean_payload_value,
        visibility=visibility,
        dedupe_key=clean_dedupe,
    )


def build_save_uploaded_event(
    *,
    trainer_id: str,
    save_id: int | str | None,
    filename: str,
    original_name: str = "",
    sha256: str = "",
    created_at: str | int,
) -> ActivityEvent:
    dedupe_ref = str(sha256 or save_id or filename).strip()
    return build_activity_event(
        ActivityEventType.SAVE_UPLOADED,
        created_at=created_at,
        actor_id=trainer_id,
        trainer_id=trainer_id,
        payload={
            "save_id": int(save_id) if isinstance(save_id, int) else save_id,
            "filename": filename,
            "original_name": original_name or filename,
            "sha256": sha256,
        },
        dedupe_key=f"{ActivityEventType.SAVE_UPLOADED.value}:{trainer_id}:{dedupe_ref}",
    )


def build_purchase_completed_event(
    *,
    trainer_id: str,
    item: str,
    price: int,
    purchase_id: int | str | None,
    created_at: str | int,
    matchday_number: int | None = None,
    promotion_id: int | str | None = None,
    base_price: int | None = None,
    promotion_kind: str = "",
) -> ActivityEvent:
    purchase_ref = str(purchase_id or "").strip()
    context = {"matchday_number": int(matchday_number)} if matchday_number is not None else {}
    fallback = stable_digest({"trainer": trainer_id, "item": item, "price": price, "context": context})
    return build_activity_event(
        ActivityEventType.PURCHASE_COMPLETED,
        created_at=created_at,
        actor_id=trainer_id,
        trainer_id=trainer_id,
        context=context,
        payload={
            "purchase_id": purchase_id,
            "item": item,
            "quantity": 1,
            "price": int(price),
            "base_price": int(base_price) if base_price is not None else None,
            "promotion_id": promotion_id,
            "promotion_kind": promotion_kind,
        },
        dedupe_key=f"{ActivityEventType.PURCHASE_COMPLETED.value}:{purchase_ref or fallback}",
    )


def build_team_locked_event(
    *,
    trainer_id: str,
    matchday_number: int,
    lock_id: int | str | None,
    created_at: str | int,
    is_late: bool = False,
    save_id: int | str | None = None,
    save_sha256: str = "",
) -> ActivityEvent:
    return build_activity_event(
        ActivityEventType.TEAM_LOCKED,
        created_at=created_at,
        actor_id=trainer_id,
        trainer_id=trainer_id,
        context={"matchday_number": int(matchday_number)},
        payload={
            "lock_id": lock_id,
            "matchday_number": int(matchday_number),
            "is_late": bool(is_late),
            "save_id": save_id,
            "save_sha256": save_sha256,
        },
        dedupe_key=f"{ActivityEventType.TEAM_LOCKED.value}:{int(matchday_number)}:{trainer_id}",
    )


def dedupe_events(events: Iterable[ActivityEvent], *, limit: int | None = None) -> tuple[ActivityEvent, ...]:
    by_key: dict[str, ActivityEvent] = {}
    for event in events:
        by_key.setdefault(event.dedupe_key, event)
    ordered = sorted(by_key.values(), key=lambda event: (event.created_at, event.id), reverse=True)
    if limit is None:
        return tuple(ordered)
    return tuple(ordered[: max(0, int(limit))])


def visible_to(event: ActivityEvent, viewer_id: str) -> ActivityVisibilityDecision:
    viewer = str(viewer_id or "").strip()
    if event.visibility == Visibility.PUBLIC:
        return ActivityVisibilityDecision(True)
    if event.visibility == Visibility.ADMIN:
        return ActivityVisibilityDecision(viewer.casefold() == "anto", "admin_only")
    if event.visibility == Visibility.OWNER:
        return ActivityVisibilityDecision(
            bool(viewer) and viewer in {event.actor_id, event.trainer_id},
            "owner_only",
        )
    return ActivityVisibilityDecision(False, "server_only")
