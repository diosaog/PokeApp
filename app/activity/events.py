from __future__ import annotations

import hashlib
import json
import time
from typing import Any

from app.repositories import mappers
from app.repositories.legacy.activity import LegacyActivityRepository
from app.repositories.legacy.settings_store import LegacySettingsStore
from storage import settings_get, settings_set


ACTIVITY_EVENTS_KEY = "activity_events_v1"
ACTIVITY_EVENT_SCHEMA_VERSION = 1
ACTIVITY_EVENT_STORAGE_LIMIT = 1000

EVENT_SAVE_UPLOADED = "SAVE_UPLOADED"
EVENT_PURCHASE_COMPLETED = "PURCHASE_COMPLETED"
EVENT_TEAM_LOCKED = "TEAM_LOCKED"

VISIBILITY_PUBLIC = "public"
VISIBILITY_TRAINER = "trainer-only"
VISIBILITY_ADMIN = "admin-only"

UI_EVENT_TYPES = {
    EVENT_SAVE_UPLOADED,
    EVENT_PURCHASE_COMPLETED,
    EVENT_TEAM_LOCKED,
}


def _now() -> int:
    return int(time.time())


def _json_loads(raw: str | None, fallback: Any) -> Any:
    if not raw:
        return fallback
    try:
        return json.loads(raw)
    except Exception:
        return fallback


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _stable_digest(value: Any, *, length: int = 16) -> str:
    raw = _json_dumps(value)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:length]


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _clean_payload(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, Any] = {}
    for key, raw in value.items():
        clean_key = _clean_text(key)
        if not clean_key:
            continue
        if isinstance(raw, (str, int, float, bool)) or raw is None:
            out[clean_key] = raw
        elif isinstance(raw, list):
            out[clean_key] = [
                item
                for item in raw
                if isinstance(item, (str, int, float, bool)) or item is None
            ]
        elif isinstance(raw, dict):
            out[clean_key] = {
                str(k): v
                for k, v in raw.items()
                if isinstance(k, str)
                and (isinstance(v, (str, int, float, bool)) or v is None)
            }
        else:
            out[clean_key] = str(raw)
    return out


def _clean_context(value: Any) -> dict[str, Any]:
    return _clean_payload(value)


def _clean_visibility(value: Any) -> str:
    visibility = _clean_text(value, VISIBILITY_PUBLIC).lower()
    if visibility in {VISIBILITY_PUBLIC, VISIBILITY_TRAINER, VISIBILITY_ADMIN}:
        return visibility
    return VISIBILITY_PUBLIC


def _event_id(event_type: str, dedupe_key: str) -> str:
    return f"evt:{_stable_digest({'type': event_type, 'dedupe_key': dedupe_key}, length=20)}"


def _coerce_event(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    event_type = _clean_text(raw.get("type")).upper()
    dedupe_key = _clean_text(raw.get("dedupe_key"))
    if not event_type or not dedupe_key:
        return None
    created_at = _safe_int(raw.get("created_at"), 0)
    if created_at <= 0:
        created_at = _now()
    event_id = _clean_text(raw.get("id")) or _event_id(event_type, dedupe_key)
    return {
        "schema_version": ACTIVITY_EVENT_SCHEMA_VERSION,
        "id": event_id,
        "type": event_type,
        "created_at": created_at,
        "actor": _clean_text(raw.get("actor")),
        "trainer": _clean_text(raw.get("trainer")),
        "context": _clean_context(raw.get("context")),
        "payload": _clean_payload(raw.get("payload")),
        "visibility": _clean_visibility(raw.get("visibility")),
        "dedupe_key": dedupe_key,
    }


def _repository() -> LegacyActivityRepository:
    return LegacyActivityRepository(
        settings=LegacySettingsStore(
            getter=settings_get,
            setter=lambda key, value: settings_set(key, value),
        )
    )


def _load_events() -> list[dict[str, Any]]:
    try:
        events = [
            _coerce_event(mappers.activity_event_to_legacy(event))
            for event in _repository().list_all()
        ]
        return [event for event in events if event]
    except Exception:
        raw = _json_loads(settings_get(ACTIVITY_EVENTS_KEY), [])
        source = raw if isinstance(raw, list) else []
        events = [event for event in (_coerce_event(item) for item in source) if event]
        events.sort(key=lambda item: (_safe_int(item.get("created_at")), str(item.get("id") or "")), reverse=True)
        return events


def _save_events(events: list[dict[str, Any]]) -> None:
    domain_events = []
    for event in events:
        coerced = _coerce_event(event)
        if not coerced:
            continue
        mapped = mappers.activity_event_from_any(coerced)
        if mapped:
            domain_events.append(mapped)
    try:
        _repository().replace_all(tuple(domain_events))
        return
    except Exception:
        pass
    out = [
        mappers.activity_event_to_legacy(event)
        for event in domain_events[:ACTIVITY_EVENT_STORAGE_LIMIT]
    ]
    settings_set(ACTIVITY_EVENTS_KEY, json.dumps(out, ensure_ascii=False))


def record_activity_event(
    event_type: str,
    *,
    created_at: int | None = None,
    actor: str | None = None,
    trainer: str | None = None,
    context: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    visibility: str = VISIBILITY_PUBLIC,
    dedupe_key: str | None = None,
) -> dict[str, Any]:
    clean_type = _clean_text(event_type).upper()
    clean_payload = _clean_payload(payload)
    clean_context = _clean_context(context)
    clean_dedupe = _clean_text(dedupe_key) or f"{clean_type}:{_stable_digest(clean_payload)}"
    event = {
        "schema_version": ACTIVITY_EVENT_SCHEMA_VERSION,
        "id": _event_id(clean_type, clean_dedupe),
        "type": clean_type,
        "created_at": int(created_at if created_at is not None else _now()),
        "actor": _clean_text(actor),
        "trainer": _clean_text(trainer),
        "context": clean_context,
        "payload": clean_payload,
        "visibility": _clean_visibility(visibility),
        "dedupe_key": clean_dedupe,
    }
    coerced = _coerce_event(event)
    if not coerced:
        raise ValueError("ActivityEvent invalido.")

    events = _load_events()
    for existing in events:
        if existing.get("dedupe_key") == clean_dedupe:
            return existing

    _save_events([coerced, *events])
    return coerced


def _visible_to(event: dict[str, Any], viewer: str | None) -> bool:
    visibility = _clean_visibility(event.get("visibility"))
    if visibility == VISIBILITY_PUBLIC:
        return True
    viewer_name = _clean_text(viewer)
    if visibility == VISIBILITY_ADMIN:
        return viewer_name.lower() == "anto"
    if visibility == VISIBILITY_TRAINER:
        return viewer_name and viewer_name in {
            _clean_text(event.get("actor")),
            _clean_text(event.get("trainer")),
        }
    return False


def list_activity_events(
    *,
    limit: int | None = None,
    viewer: str | None = None,
    event_types: set[str] | list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    allowed = {str(value).upper() for value in event_types} if event_types else None
    out = [
        event
        for event in _load_events()
        if (allowed is None or str(event.get("type") or "").upper() in allowed)
        and _visible_to(event, viewer)
    ]
    if limit is None:
        return out
    return out[: max(0, int(limit))]


def recent_activity_events(
    *,
    limit: int = 5,
    viewer: str | None = None,
    event_types: set[str] | list[str] | tuple[str, ...] | None = None,
    ui_only: bool = False,
) -> list[dict[str, Any]]:
    types = set(event_types or ())
    if ui_only:
        types = types & UI_EVENT_TYPES if types else set(UI_EVENT_TYPES)
    return list_activity_events(
        limit=max(1, int(limit or 5)),
        viewer=viewer,
        event_types=types or None,
    )


def emit_save_uploaded(
    *,
    trainer: str,
    save_id: int | None,
    filename: str,
    original_name: str | None = None,
    sha256: str | None = None,
    created_at: int | None = None,
) -> dict[str, Any]:
    save_hash = _clean_text(sha256)
    dedupe_ref = save_hash or str(save_id or filename)
    return record_activity_event(
        EVENT_SAVE_UPLOADED,
        created_at=created_at,
        actor=trainer,
        trainer=trainer,
        payload={
            "save_id": int(save_id) if save_id is not None else None,
            "filename": filename,
            "original_name": original_name or filename,
            "sha256": save_hash,
        },
        visibility=VISIBILITY_PUBLIC,
        dedupe_key=f"{EVENT_SAVE_UPLOADED}:{_clean_text(trainer)}:{dedupe_ref}",
    )


def emit_purchase_completed(
    *,
    trainer: str,
    item: str,
    price: int,
    purchase_id: int | None,
    created_at: int | None = None,
    jornada: int | None = None,
    discount_id: int | None = None,
    base_price: int | None = None,
    discount_kind: str | None = None,
) -> dict[str, Any]:
    purchase_ref = int(purchase_id) if purchase_id is not None else 0
    payload = {
        "purchase_id": purchase_ref or None,
        "item": item,
        "quantity": 1,
        "price": int(price),
        "base_price": int(base_price) if base_price is not None else None,
        "discount_id": int(discount_id) if discount_id is not None else None,
        "discount_kind": discount_kind or "",
    }
    context = {"jornada": int(jornada)} if jornada is not None else {}
    fallback_ref = _stable_digest({"trainer": trainer, "item": item, "price": price, "context": context})
    return record_activity_event(
        EVENT_PURCHASE_COMPLETED,
        created_at=created_at,
        actor=trainer,
        trainer=trainer,
        context=context,
        payload=payload,
        visibility=VISIBILITY_PUBLIC,
        dedupe_key=f"{EVENT_PURCHASE_COMPLETED}:{purchase_ref or fallback_ref}",
    )


def emit_team_locked(
    *,
    trainer: str,
    jornada: int,
    lock_id: int | None,
    locked_at: int | None = None,
    is_late: bool = False,
    save_id: int | None = None,
    save_sha256: str | None = None,
) -> dict[str, Any]:
    return record_activity_event(
        EVENT_TEAM_LOCKED,
        created_at=locked_at,
        actor=trainer,
        trainer=trainer,
        context={"jornada": int(jornada)},
        payload={
            "lock_id": int(lock_id) if lock_id is not None else None,
            "jornada": int(jornada),
            "is_late": bool(is_late),
            "save_id": int(save_id) if save_id is not None else None,
            "save_sha256": _clean_text(save_sha256),
        },
        visibility=VISIBILITY_PUBLIC,
        dedupe_key=f"{EVENT_TEAM_LOCKED}:{int(jornada)}:{_clean_text(trainer)}",
    )
