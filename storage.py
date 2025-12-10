from __future__ import annotations
import os
import sqlite3
import hashlib
import time
from pathlib import Path
from typing import Optional, List, Tuple, Any
import httpx
from supabase import create_client, Client

# Rutas de datos en la raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SAVES_DIR = DATA_DIR / "saves"
DB_PATH = DATA_DIR / "app.db"
_SUPABASE: Client | None = None
_SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "saves")


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


def _conn():
    return sqlite3.connect(DB_PATH)


def init_storage():
    DATA_DIR.mkdir(exist_ok=True)
    SAVES_DIR.mkdir(exist_ok=True)
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


def _fetch_save_by_id(save_id: int) -> Optional[Tuple]:
    if _supabase_enabled():
        try:
            client = _sb()
            res = client.table("saves").select("*").eq("id", int(save_id)).limit(1).execute()
            data = (res.data or [])
            if not data:
                return None
            row = data[0]
            ts = _iso_to_ts(row.get("created_at"))
            return (
                row.get("id"),
                row.get("filename"),
                row.get("original_name"),
                row.get("sha256"),
                row.get("user"),
                ts,
            )
        except Exception:
            return None
    with _conn() as cx:
        row = cx.execute(
            "SELECT id, filename, original_name, sha256, uploader, created_at FROM saves WHERE id=?",
            (int(save_id),),
        ).fetchone()
        return row


def save_upload(content: bytes, original_name: str, uploader: str|None=None) -> dict:
    sha = _sha256(content)
    ts = int(time.time())
    safe_name = f"{ts}_{sha[:8]}.sav"

    if _supabase_enabled():
        client = _sb()
        bucket = _bucket_name()
        # Subir al bucket
        client.storage.from_(bucket).upload(
            safe_name,
            content,
            {"contentType": "application/octet-stream", "upsert": True},
        )
        public_url = client.storage.from_(bucket).get_public_url(safe_name)
        # Insertar metadatos en tabla remota
        res = client.table("saves").insert(
            {
                "filename": safe_name,
                "original_name": original_name,
                "user": uploader,
                "url": public_url,
                "sha256": sha,
            }
        ).execute()
        new_id = None
        try:
            data = res.data or []
            if data:
                new_id = data[0].get("id")
        except Exception:
            new_id = None
        return {
            "id": new_id,
            "filename": safe_name,
            "sha256": sha,
            "created_at": ts,
            "url": public_url,
        }

    # Fallback local
    (SAVES_DIR / safe_name).write_bytes(content)
    with _conn() as cx:
        cx.execute(
            "INSERT INTO saves(filename, original_name, sha256, uploader, created_at) VALUES(?,?,?,?,?)",
            (safe_name, original_name, sha, uploader, ts)
        )
        rowid = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
        cx.commit()
    return {"id": rowid, "filename": safe_name, "sha256": sha, "created_at": ts}


def list_saves(limit: int = 50) -> List[Tuple]:
    if _supabase_enabled():
        client = _sb()
        res = client.table("saves").select("*").order("id", desc=True).limit(limit).execute()
        out = []
        for row in res.data or []:
            ts = _iso_to_ts(row.get("created_at"))
            out.append(
                (
                    row.get("id"),
                    row.get("filename"),
                    row.get("original_name"),
                    row.get("sha256"),
                    row.get("user"),
                    ts,
                )
            )
        return out
    with _conn() as cx:
        return cx.execute(
            "SELECT id, filename, original_name, sha256, uploader, created_at FROM saves ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()


def set_current_save(save_id: int):
    with _conn() as cx:
        cx.execute(
            """INSERT INTO settings(key,value) VALUES('current_save', ?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (str(save_id),)
        )
        cx.commit()


def get_current_save() -> Optional[Tuple]:
    with _conn() as cx:
        v = cx.execute("SELECT value FROM settings WHERE key='current_save'").fetchone()
        if not v:
            return None
        save_id = int(v[0])
    return _fetch_save_by_id(save_id)


def load_save_bytes(filename: str) -> bytes:
    if _supabase_enabled():
        try:
            client = _sb()
            bucket = _bucket_name()
            # Prefer public URL (bucket es público)
            url = client.storage.from_(bucket).get_public_url(filename)
            resp = httpx.get(url, timeout=10)
            resp.raise_for_status()
            return resp.content
        except Exception:
            try:
                res = client.storage.from_(bucket).download(filename)
                return res
            except Exception:
                return b""
    try:
        return (SAVES_DIR / filename).read_bytes()
    except Exception:
        return b""

# Helper: ruta del save actual
def get_current_save_path() -> Path | None:
    cur = get_current_save()
    if not cur:
        return None
    return SAVES_DIR / cur[1]

def list_saves_by_user(user: str, limit: int = 50) -> List[Tuple]:
    if _supabase_enabled():
        client = _sb()
        res = (
            client.table("saves")
            .select("*")
            .eq("user", user)
            .order("id", desc=True)
            .limit(limit)
            .execute()
        )
        out = []
        for row in res.data or []:
            ts = _iso_to_ts(row.get("created_at"))
            out.append(
                (
                    row.get("id"),
                    row.get("filename"),
                    row.get("original_name"),
                    row.get("sha256"),
                    row.get("user"),
                    ts,
                )
            )
        return out
    with _conn() as cx:
        return cx.execute(
            """
            SELECT id, filename, original_name, sha256, uploader, created_at
            FROM saves
            WHERE uploader = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user, limit),
        ).fetchall()


def _user_key(user: str) -> str:
    return f"current_save:{user}"


def set_current_save_for_user(user: str, save_id: int) -> None:
    if save_id is None:
        return
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO settings(key,value) VALUES(?,?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (_user_key(user), str(int(save_id))),
        )
        cx.commit()


def get_current_save_for_user(user: str) -> Optional[Tuple]:
    with _conn() as cx:
        v = cx.execute("SELECT value FROM settings WHERE key=?", (_user_key(user),)).fetchone()
    if not v:
        return None
    save_id = int(v[0])
    return _fetch_save_by_id(save_id)


def get_current_save_path_for_user(user: str):
    cur = get_current_save_for_user(user)
    if not cur:
        return None
    return SAVES_DIR / cur[1]

# Tienda

def add_purchase(user: str, item: str, price: int) -> int:
    ts = int(time.time())
    with _conn() as cx:
        cx.execute(
            "INSERT INTO purchases(user, item, price, created_at, status) VALUES(?,?,?,?,?)",
            (user, item, int(price), ts, 'pending')
        )
        rowid = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
        cx.commit()
        return int(rowid)


def total_spent(user: str) -> int:
    with _conn() as cx:
        row = cx.execute("SELECT COALESCE(SUM(price),0) FROM purchases WHERE user=?", (user,)).fetchone()
        return int(row[0] or 0)


def list_purchases(user: str | None = None, limit: int = 100):
    with _conn() as cx:
        if user:
            return cx.execute(
                "SELECT id, user, item, price, created_at, status, redeemed_at FROM purchases WHERE user=? ORDER BY id DESC LIMIT ?",
                (user, limit)
            ).fetchall()
        return cx.execute(
            "SELECT id, user, item, price, created_at, status, redeemed_at FROM purchases ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()


def list_inventory(user: str, *, status: str | None = None, limit: int = 200):
    with _conn() as cx:
        if status:
            return cx.execute(
                "SELECT id, item, price, created_at, status, redeemed_at FROM purchases WHERE user=? AND status=? ORDER BY id DESC LIMIT ?",
                (user, status, limit)
            ).fetchall()
        return cx.execute(
            "SELECT id, item, price, created_at, status, redeemed_at FROM purchases WHERE user=? ORDER BY id DESC LIMIT ?",
            (user, limit)
        ).fetchall()

# Redemptions / vouchers

def add_redemption(purchase_id: int, user: str, item: str, payload_json: str) -> int:
    ts = int(time.time())
    with _conn() as cx:
        cx.execute(
            "INSERT INTO redemptions(purchase_id, user, item, payload_json, created_at) VALUES(?,?,?,?,?)",
            (int(purchase_id), user, item, payload_json, ts)
        )
        rid = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
        cx.commit()
        return int(rid)


def set_purchase_status(purchase_id: int, status: str) -> None:
    ts = int(time.time())
    with _conn() as cx:
        if status == 'used':
            cx.execute("UPDATE purchases SET status=?, redeemed_at=? WHERE id=?", (status, ts, int(purchase_id)))
        else:
            cx.execute("UPDATE purchases SET status=? WHERE id=?", (status, int(purchase_id)))
        cx.commit()

# Pokemon flags

def upsert_pokemon_flags(owner: str, fingerprint: str, flags_json: str) -> None:
    ts = int(time.time())
    with _conn() as cx:
        row = cx.execute("SELECT id FROM pokemon_flags WHERE fingerprint=?", (fingerprint,)).fetchone()
        if row:
            cx.execute(
                "UPDATE pokemon_flags SET owner=?, flags_json=?, updated_at=? WHERE id=?",
                (owner, flags_json, ts, int(row[0]))
            )
        else:
            cx.execute(
                "INSERT INTO pokemon_flags(owner, fingerprint, flags_json, created_at, updated_at) VALUES(?,?,?,?,?)",
                (owner, fingerprint, flags_json, ts, ts)
            )
        cx.commit()


def get_flags_by_fingerprints(fps: list[str]) -> dict:
    if not fps:
        return {}
    qmarks = ",".join(["?"] * len(fps))
    with _conn() as cx:
        rows = cx.execute(
            f"SELECT fingerprint, owner, flags_json FROM pokemon_flags WHERE fingerprint IN ({qmarks})",
            tuple(fps)
        ).fetchall()
    out = {}
    for fp, owner, fj in rows:
        out[fp] = {"owner": owner, "flags_json": fj}
    return out


def clear_purchases() -> None:
    with _conn() as cx:
        cx.execute("DELETE FROM purchases")
        cx.commit()

# Pokemon flags reset helpers

def clear_all_pokemon_flags() -> None:
    with _conn() as cx:
        cx.execute("DELETE FROM pokemon_flags")
        cx.commit()


def clear_pokemon_flags_for_owner(owner: str) -> None:
    with _conn() as cx:
        cx.execute("DELETE FROM pokemon_flags WHERE owner=?", (owner,))
        cx.commit()

# Settings genéricos

def settings_set(key: str, value: str) -> None:
    with _conn() as cx:
        cx.execute(
            """INSERT INTO settings(key,value) VALUES(?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, value)
        )
        cx.commit()


def settings_get(key: str) -> str | None:
    with _conn() as cx:
        row = cx.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

