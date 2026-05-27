from __future__ import annotations

from typing import Dict
import hashlib
import json
import streamlit as st

from storage import settings_get_uncached, settings_set
from utils import league_users_for_round


_LEAGUE_STATE_HASH_KEY = "_league_state_hash"
_LEAGUE_STATE_ERROR_KEY = "_league_state_error"
_DIVISION_A_SIZE = 5


def _player_canon(round_no: int, roster_transition_complete: bool = False) -> dict[str, str]:
    return {
        str(user).strip().lower(): user
        for user in league_users_for_round(
            round_no,
            roster_transition_complete=roster_transition_complete,
        ).keys()
    }


def _normalize_player(value, round_no: int, roster_transition_complete: bool = False) -> str | None:
    return _player_canon(round_no, roster_transition_complete).get(str(value).strip().lower())


def _sanitize_divisions(divs: dict, round_no: int, roster_transition_complete: bool = False) -> dict:
    players = list(
        league_users_for_round(
            round_no,
            roster_transition_complete=roster_transition_complete,
        ).keys()
    )

    def _norm_list(items: list) -> list[str]:
        out: list[str] = []
        for it in items or []:
            val = _normalize_player(it, round_no, roster_transition_complete)
            if val and val not in out:
                out.append(val)
        return out

    curA = _norm_list(divs.get("A", [])) if isinstance(divs, dict) else []
    curB = _norm_list(divs.get("B", [])) if isinstance(divs, dict) else []
    curB = [u for u in curB if u not in curA]
    ordered = curA + curB
    for u in players:
        if u not in ordered:
            ordered.append(u)
    return {"A": ordered[:_DIVISION_A_SIZE], "B": ordered[_DIVISION_A_SIZE:]}


def _sanitize_results(
    results: dict,
    round_no: int,
    roster_transition_complete: bool = False,
) -> dict[str, dict[int, int]]:
    active_round = int(round_no)
    entries_by_round: Dict[int, list[tuple[int, str | None]]] = {}
    for raw_user, round_map in (results or {}).items():
        if not isinstance(round_map, dict):
            continue
        user = _normalize_player(raw_user, active_round, roster_transition_complete)
        for raw_round, raw_position in round_map.items():
            try:
                result_round = int(raw_round)
                position = int(raw_position)
            except Exception:
                continue
            entries_by_round.setdefault(result_round, []).append((position, user))

    clean: dict[str, dict[int, int]] = {}
    for result_round, entries in entries_by_round.items():
        removed_positions = sorted(position for position, user in entries if user is None)
        kept = sorted(
            ((position, user) for position, user in entries if user),
            key=lambda item: (item[0], item[1]),
        )
        for position, user in kept:
            shift = sum(1 for removed_position in removed_positions if removed_position < position)
            clean.setdefault(user, {})[result_round] = position - shift
    return clean


def _sanitize_match(
    p1,
    p2,
    winner,
    round_no: int,
    roster_transition_complete: bool = False,
) -> tuple[str, str, str | None] | None:
    player1 = _normalize_player(p1, round_no, roster_transition_complete)
    player2 = _normalize_player(p2, round_no, roster_transition_complete)
    if not player1 or not player2 or player1 == player2:
        return None
    normalized_winner = (
        _normalize_player(winner, round_no, roster_transition_complete) if winner else None
    )
    if normalized_winner not in (player1, player2):
        normalized_winner = None
    return player1, player2, normalized_winner


def _sanitize_movements(
    movements: dict,
    round_no: int,
    roster_transition_complete: bool = False,
) -> dict[int, dict[str, list[str]]]:
    active_round = int(round_no)
    clean: dict[int, dict[str, list[str]]] = {}
    for raw_round, movement in (movements or {}).items():
        try:
            movement_round = int(raw_round)
        except Exception:
            continue
        movement = movement if isinstance(movement, dict) else {}
        clean[movement_round] = {
            key: [
                player
                for raw_player in movement.get(key, []) or []
                if (
                    player := _normalize_player(
                        raw_player,
                        active_round,
                        roster_transition_complete,
                    )
                )
            ]
            for key in ("up", "down")
        }
    return clean


def _serialize_state() -> dict:
    S = st.session_state
    current_round = int(S.get("league_tramo", 1))
    roster_transition_complete = bool(
        S.get("league_roster_transition_complete", False)
    ) or current_round > 2
    matches: Dict[str, Dict[str, list[dict]]] = {}
    for tramo, divs in (S.get("league_matches") or {}).items():
        tkey = str(tramo)
        out = {"A": [], "B": []}
        for d in ("A", "B"):
            for (p1, p2), w in divs.get(d, {}).items():
                match = _sanitize_match(p1, p2, w, current_round, roster_transition_complete)
                if match:
                    player1, player2, winner = match
                    out[d].append({"p1": player1, "p2": player2, "winner": winner})
        matches[tkey] = out
    clean_results = _sanitize_results(
        S.get("league_results") or {},
        current_round,
        roster_transition_complete,
    )
    results = {u: {str(k): int(v) for k, v in mp.items()} for u, mp in clean_results.items()}
    return {
        "tramo": int(S.get("league_tramo", 1)),
        "active": bool(S.get("league_active", False)),
        "roster_transition_complete": roster_transition_complete,
        "divisions": _sanitize_divisions(
            S.get("league_divisions", {"A": [], "B": []}),
            current_round,
            roster_transition_complete,
        ),
        "matches": matches,
        "results": results,
        "movements": _sanitize_movements(
            S.get("league_movements", {}),
            current_round,
            roster_transition_complete,
        ),
    }


def _state_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _apply_serialized_state(obj: dict) -> None:
    current_round = int(obj.get("tramo", 1))
    roster_transition_complete = bool(
        obj.get("roster_transition_complete", False)
    ) or current_round > 2
    st.session_state.league_tramo = current_round
    st.session_state.league_active = bool(obj.get("active", False))
    st.session_state.league_roster_transition_complete = roster_transition_complete
    st.session_state.league_divisions = _sanitize_divisions(
        obj.get("divisions", {"A": [], "B": []}),
        current_round,
        roster_transition_complete,
    )

    st.session_state.league_results = _sanitize_results(
        obj.get("results", {}),
        current_round,
        roster_transition_complete,
    )

    mat_in = obj.get("matches", {})
    mat_out: Dict[int, Dict[str, Dict[tuple, str | None]]] = {}
    for tkey, divs in mat_in.items():
        t = int(tkey)
        mat_out[t] = {"A": {}, "B": {}}
        for d in ("A", "B"):
            for m in divs.get(d, []) or []:
                match = _sanitize_match(
                    m.get("p1"),
                    m.get("p2"),
                    m.get("winner"),
                    current_round,
                    roster_transition_complete,
                )
                if match:
                    player1, player2, winner = match
                    mat_out[t][d][(player1, player2)] = winner
    st.session_state.league_matches = mat_out

    st.session_state.league_movements = _sanitize_movements(
        obj.get("movements", {}),
        current_round,
        roster_transition_complete,
    )


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
        normalized_raw = json.dumps(_serialize_state(), ensure_ascii=False)
        if json.loads(normalized_raw) != obj:
            settings_set("league_state", normalized_raw, strict_remote=True)
            raw_hash = _state_hash(normalized_raw)
        st.session_state[_LEAGUE_STATE_HASH_KEY] = raw_hash
        st.session_state.pop(_LEAGUE_STATE_ERROR_KEY, None)
        return True
    except Exception as e:
        st.session_state[_LEAGUE_STATE_ERROR_KEY] = str(e)
        return False


def persist_state() -> None:
    try:
        serialized = _serialize_state()
        _apply_serialized_state(serialized)
        raw = json.dumps(serialized, ensure_ascii=False)
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
    current_round = int(st.session_state.league_tramo)
    roster_transition_complete = bool(
        st.session_state.get("league_roster_transition_complete", False)
    ) or current_round > 2
    st.session_state.league_roster_transition_complete = roster_transition_complete
    if "league_divisions" not in st.session_state:
        players = list(
            league_users_for_round(
                current_round,
                roster_transition_complete=roster_transition_complete,
            ).keys()
        )
        st.session_state.league_divisions = {"A": players[:5], "B": players[5:]}
    else:
        st.session_state.league_divisions = _sanitize_divisions(
            st.session_state.league_divisions,
            current_round,
            roster_transition_complete,
        )
    if "league_matches" not in st.session_state:
        st.session_state.league_matches = {}
    if "league_movements" not in st.session_state:
        st.session_state.league_movements = {}
