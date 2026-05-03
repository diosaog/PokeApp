from __future__ import annotations

import json
from typing import Any

try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore

from app.juicios.constants import (
    JUICIOS_STATE_KEY,
    LEGACY_STATUS_MAP,
    PENALTY_COINS_REDUCTION,
    PENALTY_OTHER,
    PENALTY_POINTS_REDUCTION,
    PENALTY_POKEMON_RELEASE,
    PENALTY_STORE_BAN,
    STATUS_FINISHED,
)
from storage import settings_get


def _cache_data(ttl: int = 10):
    if st is None:
        return lambda f: f
    return st.cache_data(ttl=ttl, show_spinner=False)


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


@_cache_data(ttl=10)
def _current_league_tramo_from_raw(raw: str) -> int:
    try:
        if not raw:
            return 1
        obj = json.loads(raw)
        tramo = int(obj.get("tramo") or 1)
        return max(tramo, 1)
    except Exception:
        return 1


def _current_league_tramo() -> int:
    return _current_league_tramo_from_raw(settings_get("league_state") or "")


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


def _empty_penalties() -> dict[str, Any]:
    return {
        "store_blocked": False,
        "coins_reduction": 0,
        "points_reduction": 0.0,
        "pokemon_release_notes": [],
        "other_notes": [],
        "sources": [],
        "store_ban_tramos": [],
    }


@_cache_data(ttl=10)
def _get_user_penalties_cached(user: str, current_tramo: int, juicios_raw: str) -> dict[str, Any]:
    if not user:
        return _empty_penalties()

    try:
        obj = json.loads(juicios_raw) if juicios_raw else {}
    except Exception:
        obj = {}
    cases = obj.get("cases") if isinstance(obj, dict) and isinstance(obj.get("cases"), list) else []

    store_blocked = False
    coins_reduction = 0
    points_reduction = 0.0
    pokemon_release_notes: list[str] = []
    other_notes: list[str] = []
    sources: list[str] = []
    store_ban_tramos: list[str] = []

    for case in cases:
        if not isinstance(case, dict):
            continue
        if _normalized_status(case.get("status")) != STATUS_FINISHED:
            continue
        if str(case.get("accused") or "").strip() != str(user).strip():
            continue

        case_ref = f"Caso #{case.get('case_no')}: {case.get('title') or '-'}"
        has_effect = False
        for p in list(case.get("penalties") or []):
            if not isinstance(p, dict):
                continue
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


def get_user_penalties(user: str | None) -> dict[str, Any]:
    if not user:
        return _empty_penalties()
    league_raw = settings_get("league_state") or ""
    juicios_raw = settings_get(JUICIOS_STATE_KEY) or ""
    current_tramo = _current_league_tramo_from_raw(league_raw)
    return _get_user_penalties_cached(str(user), int(current_tramo), juicios_raw)


def clear_penalty_caches() -> None:
    for func in (_current_league_tramo_from_raw, _get_user_penalties_cached):
        try:
            func.clear()
        except Exception:
            continue
