# -*- coding: utf-8 -*-
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import hashlib
import json

try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore

APP_TITLE = "Liga Pokemon"
APP_ICON = ""
BASE_SAVES_DIR = Path("./saves")
DEFAULT_DLL_HINT = "Bridge/PKHeXBridge/bin/Release/net9.0/linux-x64/publish/PKHeXBridge"

USERS: Dict[str, str] = {
    "Anto": "a07",
    "Victor": "v42",
    "Rober": "r03",
    "Samu": "s88",
    "Daviry": "d15",
    "Sergio": "s33",
    "Iker": "i09",
    "Aaron": "a31",
    "Miguel": "m77",
    "Mario": "m10",
    "Barto": "b66",
}

ROSTER_JOIN_ROUND = {
    "Barto": 2,
}

ROSTER_DEPARTURE_AFTER_ROUND = {
    "Mario": 2,
}

SECTIONS = [
    "Normativa",
    "Liga y Tabla",
    "Previa Combate",
    "Entrenadores",
    "Copa",
    "Juicios",
    "Tienda",
    "Saves",
]


def init_session_state() -> None:
    defaults = {
        "auth_ok": False,
        "user": None,
        "pkhex_loaded": False,
        "pkhex_dll_path": "",
        "active_sav_path": None,
        "selected_pokemon": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


def sections_for_user(user: str | None) -> list[str]:
    _ = user
    return list(SECTIONS)


def league_users_for_round(
    round_no: int, *, roster_transition_complete: bool = False
) -> Dict[str, str]:
    current_round = max(int(round_no), 1)
    _ = roster_transition_complete
    out: Dict[str, str] = {}
    for user, code in USERS.items():
        join_round = int(ROSTER_JOIN_ROUND.get(user, 1))
        departure_round = ROSTER_DEPARTURE_AFTER_ROUND.get(user)
        if current_round < join_round:
            continue
        if departure_round is not None and current_round > int(departure_round):
            continue
        out[user] = code
    return out


def active_users() -> Dict[str, str]:
    current_round = 1
    roster_transition_complete = False
    try:
        if st is not None and st.session_state.get("league_tramo"):
            return league_users_for_round(
                int(st.session_state.league_tramo),
                roster_transition_complete=bool(
                    st.session_state.get("league_roster_transition_complete", False)
                ),
            )
    except Exception:
        pass
    try:
        from storage import settings_get

        raw = settings_get("league_state")
        if raw:
            state = json.loads(raw)
            current_round = max(int(state.get("tramo") or 1), 1)
            roster_transition_complete = bool(
                state.get("roster_transition_complete", False)
            )
    except Exception:
        current_round = 1
    return league_users_for_round(
        current_round,
        roster_transition_complete=roster_transition_complete,
    )


def ensure_user_dir(u: str) -> Path:
    p = BASE_SAVES_DIR / u
    p.mkdir(parents=True, exist_ok=True)
    return p


def _list_user_saves_uncached(u: str) -> List[Path]:
    folder = ensure_user_dir(u)
    files = list(folder.glob("*.sav")) + list(folder.glob("*.dsv"))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


if st is not None:

    @st.cache_data(ttl=10, show_spinner=False)
    def _list_user_saves_cached(u: str) -> List[Path]:
        return _list_user_saves_uncached(u)

    def list_user_saves(u: str) -> List[Path]:
        return _list_user_saves_cached(u)
else:

    def list_user_saves(u: str) -> List[Path]:
        return _list_user_saves_uncached(u)


def format_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 / 1024:.2f} MB"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def ts_name(user: str, *, ext: str = ".sav") -> str:
    ext_clean = ext if ext.startswith(".") else f".{ext}"
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user}{ext_clean}"
