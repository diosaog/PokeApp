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
    "Barto": "b66",
}

SECTIONS = [
    "Inicio",
    "Normativa",
    "Liga y Tabla",
    "Temporada",
    "Team Preview",
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
    sections = list(SECTIONS)
    if str(user or "").strip().lower() != "anto":
        sections = [section for section in sections if section != "Temporada"]
    return sections


def league_users_for_round(
    round_no: int,
    *,
    include_retired: bool = True,
) -> Dict[str, str]:
    _ = max(int(round_no), 1)
    out: Dict[str, str] = {}
    retired: set[str] = set()
    if not include_retired:
        try:
            from app.entrenadores.trainer_flags import retired_trainers

            retired = retired_trainers()
        except Exception:
            retired = set()
    for user, code in USERS.items():
        if user in retired:
            continue
        out[user] = code
    return out


def active_users() -> Dict[str, str]:
    current_round = 1
    try:
        if st is not None and st.session_state.get("league_tramo"):
            return league_users_for_round(
                int(st.session_state.league_tramo),
                include_retired=False,
            )
    except Exception:
        pass
    try:
        from storage import settings_get

        raw = settings_get("league_state")
        if raw:
            state = json.loads(raw)
            current_round = max(int(state.get("tramo") or 1), 1)
    except Exception:
        current_round = 1
    return league_users_for_round(
        current_round,
        include_retired=False,
    )


def users_with_retired_last(users: List[str] | tuple[str, ...] | dict) -> List[str]:
    values = list(users.keys()) if isinstance(users, dict) else list(users)
    order = {str(user): idx for idx, user in enumerate(values)}
    try:
        from app.entrenadores.trainer_flags import retired_trainers

        retired = retired_trainers()
    except Exception:
        retired = set()
    return sorted(
        [str(user) for user in values],
        key=lambda user: (user in retired, order.get(user, 0)),
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
