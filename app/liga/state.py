from __future__ import annotations

from typing import Dict
import json
import streamlit as st

from storage import settings_get, settings_set
from utils import USERS


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


def restore_state() -> None:
    try:
        raw = settings_get("league_state")
        if not raw:
            return
        obj = json.loads(raw)
        if "league_tramo" not in st.session_state:
            st.session_state.league_tramo = int(obj.get("tramo", 1))
        if "league_active" not in st.session_state:
            st.session_state.league_active = bool(obj.get("active", False))
        if "league_divisions" not in st.session_state:
            st.session_state.league_divisions = obj.get("divisions", {"A": [], "B": []})
        if "league_divisions" in st.session_state:
            st.session_state.league_divisions = _sanitize_divisions(st.session_state.league_divisions)
        if "league_results" not in st.session_state:
            res_in = obj.get("results", {})
            st.session_state.league_results = {
                u: {int(k): int(v) for k, v in mp.items()} for u, mp in res_in.items()
            }
        if "league_matches" not in st.session_state:
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
    except Exception:
        pass


def persist_state() -> None:
    try:
        settings_set("league_state", json.dumps(_serialize_state(), ensure_ascii=False))
    except Exception:
        try:
            st.error("No se pudo guardar el estado de la liga (settings).")
        except Exception:
            pass


def ensure_state() -> None:
    if "league_tramo" not in st.session_state:
        st.session_state.league_tramo = 1
    if "league_active" not in st.session_state:
        st.session_state.league_active = False
    if "league_results" not in st.session_state:
        st.session_state.league_results = {}
    if "league_divisions" not in st.session_state:
        players = list(USERS.keys())
        st.session_state.league_divisions = {"A": players[:5], "B": players[5:10]}
    else:
        st.session_state.league_divisions = _sanitize_divisions(st.session_state.league_divisions)
    if "league_matches" not in st.session_state:
        st.session_state.league_matches = {}
    if "league_movements" not in st.session_state:
        st.session_state.league_movements = {}
