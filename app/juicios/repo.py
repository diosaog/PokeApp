from __future__ import annotations

import json
import time
from typing import Any

from app.juicios.constants import JUICIOS_STATE_KEY
from storage import settings_get, settings_set


def _now() -> int:
    return int(time.time())


def _empty_state() -> dict[str, Any]:
    return {"next_id": 1, "next_case_no": 1, "cases": []}


def _normalize_case(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(raw.get("id", 0) or 0),
        "case_no": int(raw.get("case_no", 0) or 0),
        "title": str(raw.get("title") or "").strip(),
        "creator": str(raw.get("creator") or "").strip(),
        "accused": str(raw.get("accused") or "").strip(),
        "summary": str(raw.get("summary") or "").strip(),
        "hearing_date": str(raw.get("hearing_date") or "").strip(),
        "is_public": bool(raw.get("is_public", True)),
        "evidence": str(raw.get("evidence") or "").strip(),
        "witnesses": str(raw.get("witnesses") or "").strip(),
        "priority": str(raw.get("priority") or "Media").strip() or "Media",
        "category": str(raw.get("category") or "").strip(),
        "public_vote": bool(raw.get("public_vote", False)),
        "status": str(raw.get("status") or "abierto").strip() or "abierto",
        "resolution_notes": str(raw.get("resolution_notes") or "").strip(),
        "penalties": list(raw.get("penalties") or []),
        "created_at": int(raw.get("created_at") or 0),
        "updated_at": int(raw.get("updated_at") or 0),
        "resolved_at": int(raw.get("resolved_at") or 0),
    }


def _load_state() -> dict[str, Any]:
    raw = settings_get(JUICIOS_STATE_KEY)
    if not raw:
        return _empty_state()
    try:
        obj = json.loads(raw)
    except Exception:
        return _empty_state()
    if not isinstance(obj, dict):
        return _empty_state()
    cases_in = obj.get("cases") if isinstance(obj.get("cases"), list) else []
    cases = [_normalize_case(c) for c in cases_in if isinstance(c, dict)]
    max_id = max([c["id"] for c in cases], default=0)
    max_case_no = max([c["case_no"] for c in cases], default=0)
    return {
        "next_id": int(obj.get("next_id") or (max_id + 1)),
        "next_case_no": int(obj.get("next_case_no") or (max_case_no + 1)),
        "cases": cases,
    }


def _save_state(state: dict[str, Any]) -> None:
    settings_set(JUICIOS_STATE_KEY, json.dumps(state, ensure_ascii=False))


def next_case_number() -> int:
    state = _load_state()
    return int(state.get("next_case_no") or 1)


def list_cases() -> list[dict[str, Any]]:
    state = _load_state()
    cases = list(state.get("cases") or [])
    return sorted(cases, key=lambda c: (int(c.get("case_no") or 0), int(c.get("id") or 0)), reverse=True)


def can_view_case(case: dict[str, Any], user: str | None) -> bool:
    if bool(case.get("is_public")):
        return True
    return bool(user and str(case.get("creator")) == str(user))


def can_edit_case(case: dict[str, Any], user: str | None) -> bool:
    return bool(user and str(case.get("creator")) == str(user))


def list_cases_for_user(user: str | None) -> list[dict[str, Any]]:
    return [c for c in list_cases() if can_view_case(c, user)]


def create_case(creator: str, payload: dict[str, Any]) -> dict[str, Any]:
    state = _load_state()
    cid = int(state.get("next_id") or 1)
    case_no = int(state.get("next_case_no") or 1)
    now = _now()
    case = _normalize_case(
        {
            "id": cid,
            "case_no": case_no,
            "creator": creator,
            "title": payload.get("title"),
            "accused": payload.get("accused"),
            "summary": payload.get("summary"),
            "hearing_date": payload.get("hearing_date"),
            "is_public": payload.get("is_public", True),
            "evidence": payload.get("evidence", ""),
            "witnesses": payload.get("witnesses", ""),
            "priority": payload.get("priority", "Media"),
            "category": payload.get("category", ""),
            "public_vote": payload.get("public_vote", False),
            "status": payload.get("status", "abierto"),
            "resolution_notes": payload.get("resolution_notes", ""),
            "penalties": payload.get("penalties", []),
            "created_at": now,
            "updated_at": now,
            "resolved_at": now if str(payload.get("status")) == "resuelto" else 0,
        }
    )
    state["cases"].append(case)
    state["next_id"] = cid + 1
    state["next_case_no"] = case_no + 1
    _save_state(state)
    return case


def update_case(case_id: int, editor: str, payload: dict[str, Any]) -> dict[str, Any]:
    state = _load_state()
    idx = -1
    for i, c in enumerate(state.get("cases") or []):
        if int(c.get("id") or 0) == int(case_id):
            idx = i
            break
    if idx < 0:
        raise ValueError("No se encontro el juicio.")

    current = _normalize_case(state["cases"][idx])
    if not can_edit_case(current, editor):
        raise PermissionError("Solo el creador puede editar este juicio.")

    previous_status = str(current.get("status") or "abierto")
    now = _now()
    for key in (
        "title",
        "accused",
        "summary",
        "hearing_date",
        "is_public",
        "evidence",
        "witnesses",
        "priority",
        "category",
        "public_vote",
        "status",
        "resolution_notes",
        "penalties",
    ):
        if key in payload:
            current[key] = payload.get(key)

    if str(current.get("status")) == "resuelto":
        if not list(current.get("penalties") or []):
            raise ValueError("Un juicio resuelto debe tener al menos un castigo.")
        if previous_status != "resuelto":
            current["resolved_at"] = now
    else:
        current["resolved_at"] = 0

    current["updated_at"] = now
    state["cases"][idx] = _normalize_case(current)
    _save_state(state)
    return state["cases"][idx]

