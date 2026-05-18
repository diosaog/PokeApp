from __future__ import annotations

from typing import Dict
import hashlib
import json
import streamlit as st

from storage import settings_get_uncached, settings_set
from utils import USERS


_LEAGUE_STATE_HASH_KEY = "_league_state_hash"
_LEAGUE_STATE_ERROR_KEY = "_league_state_error"


def _sanitize_divisions(divs: dict) -> dict:
    players = list(USERS.keys())
    canon = {}
    for u in players:
        key = str(u).strip()
        if key and key not in canon:
            canon[key] = u

    def _norm_list(items: list) -> list[str]:
        out: list[str] = []
        for it in items or []:
            key = str(it).strip()
            if not key:
                continue
            val = canon.get(key)
            if val and val not in out:
                out.append(val)
        return out

    curA = _norm_list(divs.get("A", [])) if isinstance(divs, dict) else []
    curB = _norm_list(divs.get("B", [])) if isinstance(divs, dict) else []
    curB = [u for u in curB if u not in curA]
    for u in players:
        if u not in curA and u not in curB:
            curB.append(u)
    return {"A": curA, "B": curB}


def _serialize_state() -> dict:
    S = st.session_state
    matches: Dict[str, Dict[str, list[dict]]] = {}
    for tramo, divs in (S.get("league_matches") or {}).items():
        tkey = str(tramo)
        out = {"A": [], "B": []}
        for d in ("A", "B"):
            for (p1, p2), w in divs.get(d, {}).items():
                out[d].append({"p1": p1, "p2": p2, "winner": w})
        matches[tkey] = out
    results = {u: {str(k): int(v) for k, v in mp.items()} for u, mp in (S.get("league_results") or {}).items()}
    return {
        "tramo": int(S.get("league_tramo", 1)),
        "active": bool(S.get("league_active", False)),
        "divisions": S.get("league_divisions", {"A": [], "B": []}),
        "matches": matches,
        "results": results,
        "movements": S.get("league_movements", {}),
    }


def _state_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _apply_serialized_state(obj: dict) -> None:
    st.session_state.league_tramo = int(obj.get("tramo", 1))
    st.session_state.league_active = bool(obj.get("active", False))
    st.session_state.league_divisions = _sanitize_divisions(obj.get("divisions", {"A": [], "B": []}))

    res_in = obj.get("results", {})
    st.session_state.league_results = {
        u: {int(k): int(v) for k, v in mp.items()} for u, mp in res_in.items()
    }

    mat_in = obj.get("matches", {})
    mat_out: Dict[int, Dict[str, Dict[tuple, str | None]]] = {}
    for tkey, divs in mat_in.items():
        t = int(tkey)
        mat_out[t] = {"A": {}, "B": {}}
        for d in ("A", "B"):
            for m in divs.get(d, []) or []:
                mat_out[t][d][(m.get("p1"), m.get("p2"))] = m.get("winner")
    st.session_state.league_matches = mat_out

    mov = obj.get("movements", {})
    if isinstance(mov, dict):
        st.session_state.league_movements = {int(k): v for k, v in mov.items()}
    else:
        st.session_state.league_movements = {}


def restore_state() -> bool:
    required = (
        "league_tramo",
        "league_active",
        "league_divisions",
        "league_results",
        "league_matches",
        "league_movements",
    )
    has_local_state = all(key in st.session_state for key in required)
    try:
        raw = settings_get_uncached("league_state", strict_remote=True)
        if not raw:
            if has_local_state:
                # If this session still has the league in memory but Supabase lost the
                # shared row, push it back instead of silently falling back to defaults.
                persist_state()
                return False
            st.session_state[_LEAGUE_STATE_ERROR_KEY] = (
                "No existe la fila settings.key='league_state' en Supabase. "
                "La liga no esta guardada en la nube."
            )
            return False
        raw_hash = _state_hash(raw)
        if has_local_state and st.session_state.get(_LEAGUE_STATE_HASH_KEY) == raw_hash:
            st.session_state.pop(_LEAGUE_STATE_ERROR_KEY, None)
            return False

        obj = json.loads(raw)
        _apply_serialized_state(obj)
        st.session_state[_LEAGUE_STATE_HASH_KEY] = raw_hash
        st.session_state.pop(_LEAGUE_STATE_ERROR_KEY, None)
        return True
    except Exception as e:
        st.session_state[_LEAGUE_STATE_ERROR_KEY] = str(e)
        return False


def persist_state() -> None:
    try:
        raw = json.dumps(_serialize_state(), ensure_ascii=False)
        settings_set("league_state", raw, strict_remote=True)
        st.session_state[_LEAGUE_STATE_HASH_KEY] = _state_hash(raw)
        st.session_state.pop(_LEAGUE_STATE_ERROR_KEY, None)
    except Exception:
        try:
            st.error("No se pudo guardar el estado de la liga (settings).")
        except Exception:
            pass
        raise


def ensure_state() -> None:
    if "league_tramo" not in st.session_state:
        st.session_state.league_tramo = 1
    if "league_active" not in st.session_state:
        st.session_state.league_active = False
    if "league_results" not in st.session_state:
        st.session_state.league_results = {}
    if "league_divisions" not in st.session_state:
        players = list(USERS.keys())
        st.session_state.league_divisions = {"A": players[:5], "B": players[5:]}
    else:
        st.session_state.league_divisions = _sanitize_divisions(st.session_state.league_divisions)
    if "league_matches" not in st.session_state:
        st.session_state.league_matches = {}
    if "league_movements" not in st.session_state:
        st.session_state.league_movements = {}
