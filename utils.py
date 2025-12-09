# -*- coding: utf-8 -*-
# utils.py  constantes, estado de sesión y utilidades sin UI (esqueleto)
from pathlib import Path
from typing import Dict, List
from datetime import datetime
import hashlib
import streamlit as st

APP_TITLE = "Liga Pokmon"
APP_ICON = ""
BASE_SAVES_DIR = Path("./saves")
# Ruta sugerida al bridge (pista por defecto en la UI)
DEFAULT_DLL_HINT = "Bridge/PKHeXBridge/bin/Release/net9.0/linux-x64/publish/PKHeXBridge"

USERS: Dict[str, str] = {
    "Anto":"a07","Victor":"v42","Rober":"r03","Samu":"s88","Daviry":"d15",
    "Barto":"b60","Iker":"i09","Aaron":"a31","Miguel":"m77",
}

SECTIONS = ["Inicio", "Liga y Tabla", "Entrenadores", "Copa", "Tienda", "Saves"]

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


# ---------- Helpers de archivos (implementados) ----------
def ensure_user_dir(u: str) -> Path:
    """Crea (si no existe) y devuelve la carpeta del usuario."""
    p = BASE_SAVES_DIR / u
    p.mkdir(parents=True, exist_ok=True)
    return p

def list_user_saves(u: str) -> List[Path]:
    """Devuelve una lista ordenada de .sav del usuario (más recientes primero)."""
    folder = ensure_user_dir(u)
    return sorted(folder.glob("*.sav"), key=lambda p: p.stat().st_mtime, reverse=True)

def format_bytes(n: int) -> str:
    """Formatea bytes a B/KB/MB."""
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    return f"{n/1024/1024:.2f} MB"

def sha256_hex(data: bytes) -> str:
    """Hash SHA-256 en hex (para mostrar)."""
    return hashlib.sha256(data).hexdigest()

def ts_name(user: str) -> str:
    """Nombre con timestamp para guardados .sav."""
    return f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user}.sav"








