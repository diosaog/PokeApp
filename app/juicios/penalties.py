from __future__ import annotations

import json
from typing import Any

from app.juicios.constants import (
    LEGACY_STATUS_MAP,
    PENALTY_COINS_REDUCTION,
    PENALTY_OTHER,
    PENALTY_POINTS_REDUCTION,
    PENALTY_POKEMON_RELEASE,
    PENALTY_STORE_BAN,
    STATUS_FINISHED,
)
from app.juicios.repo import list_cases
from storage import settings_get


def _as_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except Exception:
        return default


def _as_int(val: Any, default: int = 0) -> int:
    try:
        return int(float(val))
    except Exception:
        return default


def _normalized_status(raw: Any) -> str:
    status = str(raw or "").strip().lower()
    if status == STATUS_FINISHED:
        return status
    return LEGACY_STATUS_MAP.get(status, status)


def _current_league_tramo() -> int:
    try:
        raw = settings_get("league_state")
        if not raw:
            return 1
        obj = json.loads(raw)
        tramo = int(obj.get("tramo") or 1)
        return max(tramo, 1)
    except Exception:
        return 1


def _store_ban_active_now(penalty: dict[str, Any], current_tramo: int) -> bool:
    try:
        start = int(penalty.get("start_tramo") or 0)
        end = int(penalty.get("end_tramo") or 0)
    except Exception:
        start, end = 0, 0
    if start > 0 and end > 0:
        return start <= int(current_tramo) <= end
    # Compatibilidad con castigos antiguos sin ventana de tramo.
    return True


def get_user_penalties(user: str | None) -> dict[str, Any]:
    if not user:
        return {
            "store_blocked": False,
            "coins_reduction": 0,
            "points_reduction": 0.0,
            "pokemon_release_notes": [],
            "other_notes": [],
            "sources": [],
            "store_ban_tramos": [],
        }

    store_blocked = False
    coins_reduction = 0
    points_reduction = 0.0
    pokemon_release_notes: list[str] = []
    other_notes: list[str] = []
    sources: list[str] = []
    current_tramo = _current_league_tramo()
    store_ban_tramos: list[str] = []

    for case in list_cases():
        if _normalized_status(case.get("status")) != STATUS_FINISHED:
            continue
        if str(case.get("accused") or "").strip() != str(user).strip():
            continue

        case_ref = f"Caso #{case.get('case_no')}: {case.get('title') or '-'}"
        has_effect = False
        for p in list(case.get("penalties") or []):
            ptype = str(p.get("type") or "").strip()
            if not ptype:
                continue
            has_effect = True
            if ptype == PENALTY_STORE_BAN:
                if _store_ban_active_now(p, current_tramo):
                    store_blocked = True
                    start = int(p.get("start_tramo") or 0)
                    end = int(p.get("end_tramo") or 0)
                    if start > 0 and end > 0:
                        store_ban_tramos.append(f"{start}-{end}")
                continue
            if ptype == PENALTY_COINS_REDUCTION:
                coins_reduction += max(_as_int(p.get("amount")), 0)
                continue
            if ptype == PENALTY_POINTS_REDUCTION:
                points_reduction += max(_as_float(p.get("amount")), 0.0)
                continue
            if ptype == PENALTY_POKEMON_RELEASE:
                txt = str(p.get("text") or "").strip()
                if txt:
                    pokemon_release_notes.append(txt)
                continue
            if ptype == PENALTY_OTHER:
                txt = str(p.get("text") or "").strip()
                if txt:
                    other_notes.append(txt)
        if has_effect:
            sources.append(case_ref)

    return {
        "store_blocked": store_blocked,
        "coins_reduction": coins_reduction,
        "points_reduction": points_reduction,
        "pokemon_release_notes": pokemon_release_notes,
        "other_notes": other_notes,
        "sources": sources,
        "store_ban_tramos": store_ban_tramos,
    }
