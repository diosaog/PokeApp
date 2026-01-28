from __future__ import annotations
import os
import sqlite3
import hashlib
import time
from pathlib import Path
from typing import Optional, List, Tuple, Any
import datetime
from supabase import create_client, Client
try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore

# Rutas de datos en la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SAVES_DIR = DATA_DIR / "saves"
DB_PATH = DATA_DIR / "app.db"
_SUPABASE: Client | None = None
_SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "saves")


def _cache_data(ttl: int = 15):
    if st is None:
        return lambda f: f
    return st.cache_data(ttl=ttl, show_spinner=False)


def _supabase_enabled() -> bool:
    url = os.environ.get("SUPABASE_URL", "").strip()
    key = os.environ.get("SUPABASE_KEY", "").strip()
    return bool(url and key)


def _sb() -> Client:
    global _SUPABASE
    if _SUPABASE is None:
        url = os.environ.get("SUPABASE_URL", "").strip()
        key = os.environ.get("SUPABASE_KEY", "").strip()
        if not url or not key:
            raise RuntimeError("Supabase no configurado")
        _SUPABASE = create_client(url, key)
    return _SUPABASE


def _bucket_name() -> str:
    return _SUPABASE_BUCKET or "saves"


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _db_path() -> Path:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        return DB_PATH
    except Exception:
        tmp = Path("/tmp/pokeapp_data")
        tmp.mkdir(parents=True, exist_ok=True)
        return tmp / "app.db"


def _conn():
    return sqlite3.connect(_db_path())


def init_storage():
    global DATA_DIR, SAVES_DIR, DB_PATH
    # En entorno Supabase (Streamlit Cloud) evitamos crear SQLite local salvo que no haya Supabase.
    if _supabase_enabled():
        return

    try:
        DATA_DIR.mkdir(exist_ok=True)
        SAVES_DIR.mkdir(exist_ok=True)
    except Exception:
        # Fallback a /tmp si la carpeta del repo es solo lectura
        DATA_DIR = Path("/tmp/pokeapp_data")
        SAVES_DIR = DATA_DIR / "saves"
        DB_PATH = DATA_DIR / "app.db"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        SAVES_DIR.mkdir(parents=True, exist_ok=True)
    with _conn() as cx:
        cx.execute("""CREATE TABLE IF NOT EXISTS saves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT,
            sha256 TEXT NOT NULL,
            uploader TEXT,
            created_at INTEGER NOT NULL
        )""")
        cx.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")
        cx.execute("""CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL,
            item TEXT NOT NULL,
            price INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            status TEXT,
            redeemed_at INTEGER
        )""")
        # Migraciones ligeras: columnas nuevas si faltan
        try:
            cols = {r[1] for r in cx.execute("PRAGMA table_info(purchases)").fetchall()}
            if 'status' not in cols:
                cx.execute("ALTER TABLE purchases ADD COLUMN status TEXT")
            if 'redeemed_at' not in cols:
                cx.execute("ALTER TABLE purchases ADD COLUMN redeemed_at INTEGER")
        except Exception:
            pass
        cx.execute("""CREATE TABLE IF NOT EXISTS redemptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id INTEGER NOT NULL,
            user TEXT NOT NULL,
            item TEXT NOT NULL,
            payload_json TEXT,
            created_at INTEGER NOT NULL
        )""")
        cx.execute("""CREATE TABLE IF NOT EXISTS pokemon_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            flags_json TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )""")
        try:
            cx.execute("CREATE INDEX IF NOT EXISTS idx_flags_fp ON pokemon_flags(fingerprint)")
            cx.execute("CREATE INDEX IF NOT EXISTS idx_flags_owner ON pokemon_flags(owner)")
        except Exception:
            pass
        try:
            cx.execute("CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user)")
            cx.execute("CREATE INDEX IF NOT EXISTS idx_purchases_created ON purchases(created_at)")
        except Exception:
            pass
        cx.commit()


def _sha256(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _iso_to_ts(val: Any) -> int:
    try:
        if val is None:
            return 0
        import datetime
        if isinstance(val, (int, float)):
            return int(val)
        s = str(val).replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(s)
        return int(dt.timestamp())
    except Exception:
        return 0

