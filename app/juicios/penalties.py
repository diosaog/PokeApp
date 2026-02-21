from __future__ import annotations

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


def get_user_penalties(user: str | None) -> dict[str, Any]:
    if not user:
        return {
            "store_blocked": False,
            "coins_reduction": 0,
            "points_reduction": 0.0,
            "pokemon_release_notes": [],
            "other_notes": [],
            "sources": [],
        }

    store_blocked = False
    coins_reduction = 0
    points_reduction = 0.0
    pokemon_release_notes: list[str] = []
    other_notes: list[str] = []
    sources: list[str] = []

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
                store_blocked = True
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
    }
