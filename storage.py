from __future__ import annotations
import os
import shutil
import sqlite3
import hashlib
import time
from pathlib import Path
from typing import Optional, List, Tuple, Any
import datetime
from app.storage_cache import ExpiringCache
try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore

# Rutas de datos en la raÃ­z del proyecto
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
SAVES_DIR = DATA_DIR / "saves"
DB_PATH = DATA_DIR / "app.db"
_SUPABASE: Any | None = None
_SETTINGS_CACHE = ExpiringCache(float(os.environ.get("SETTINGS_MEM_TTL", "10")))
_TOTAL_SPENT_CACHE = ExpiringCache(float(os.environ.get("TOTAL_SPENT_MEM_TTL", "10")))
_LIST_PURCHASES_CACHE = ExpiringCache(float(os.environ.get("LIST_PURCHASES_MEM_TTL", "10")))
_LIST_INVENTORY_CACHE = ExpiringCache(float(os.environ.get("LIST_INVENTORY_MEM_TTL", "10")))


def _config_value(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value not in (None, ""):
            return str(value).strip()

    if st is not None:
        try:
            for name in names:
                value = st.secrets.get(name, "")
                if value not in (None, ""):
                    return str(value).strip()
        except Exception:
            pass

        try:
            section = st.secrets.get("supabase", {})
            section_names = []
            for name in names:
                low = name.lower()
                section_names.append(low)
                if low.startswith("supabase_"):
                    section_names.append(low.removeprefix("supabase_"))
            for name in section_names:
                value = section.get(name, "") if hasattr(section, "get") else ""
                if value not in (None, ""):
                    return str(value).strip()
        except Exception:
            pass

    return str(default or "").strip()


def _supabase_url() -> str:
    return _config_value("SUPABASE_URL", "supabase_url")


def _supabase_key() -> str:
    return _config_value(
        "SUPABASE_KEY",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_ROLE_KEY",
        "supabase_key",
        "supabase_anon_key",
        "supabase_service_role_key",
    )


def _supabase_bucket() -> str:
    return _config_value("SUPABASE_BUCKET", "supabase_bucket", default="saves") or "saves"


def _cache_data(ttl: int = 15):
    if st is None:
        return lambda f: f
    return st.cache_data(ttl=ttl, show_spinner=False)


def _invalidate_purchase_caches(user: str | None = None) -> None:
    _TOTAL_SPENT_CACHE.clear(user)
    if user is None:
        _LIST_INVENTORY_CACHE.clear()
    else:
        _LIST_INVENTORY_CACHE.clear_where(lambda key: isinstance(key, tuple) and key[0] == user)
    _LIST_PURCHASES_CACHE.clear()


def _supabase_enabled() -> bool:
    url = _supabase_url()
    key = _supabase_key()
    return bool(url and key)


def _sb() -> Any:
    global _SUPABASE
    if _SUPABASE is None:
        from supabase import create_client

        url = _supabase_url()
        key = _supabase_key()
        if not url or not key:
            raise RuntimeError("Supabase no configurado")
        _SUPABASE = create_client(url, key)
    return _SUPABASE


def _bucket_name() -> str:
    return _supabase_bucket()


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


def _clear_storage_caches() -> None:
    _SETTINGS_CACHE.clear()
    _TOTAL_SPENT_CACHE.clear()
    _LIST_PURCHASES_CACHE.clear()
    _LIST_INVENTORY_CACHE.clear()
    for func in (_fetch_save_by_id, list_saves, list_saves_by_user):
        try:
            func.clear()
        except Exception:
            pass


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def _delete_dir_contents(path: Path, allowed_root: Path) -> int:
    root = path.resolve()
    allowed = allowed_root.resolve()
    if root != allowed and not _is_within(root, allowed):
        raise RuntimeError(f"Ruta fuera del directorio permitido: {root}")
    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
        return 0
    removed = 0
    for child in root.iterdir():
        try:
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink(missing_ok=True)
            removed += 1
        except Exception:
            continue
    return removed


def _wipe_local_sqlite() -> None:
    if not _db_path().exists():
        return
    with _conn() as cx:
        for table in ("redemptions", "pokemon_flags", "purchases", "saves", "settings"):
            try:
                cx.execute(f"DELETE FROM {table}")
            except Exception:
                pass
        try:
            cx.execute(
                "DELETE FROM sqlite_sequence WHERE name IN "
                "('redemptions','pokemon_flags','purchases','saves')"
            )
        except Exception:
            pass
        cx.commit()


def wipe_all_app_data() -> dict[str, Any]:
    """Reset completo de temporada: DB remota/local, saves y caches.

    No modifica archivos de codigo ni assets; solo datos generados por la app.
    """
    errors: list[str] = []
    remote_done = False

    if _supabase_enabled():
        try:
            client = _sb()
            for table, column, sentinel in (
                ("redemptions", "id", -1),
                ("pokemon_flags", "fingerprint", "__pokeapp_keep__"),
                ("purchases", "id", -1),
                ("saves", "id", -1),
                ("settings", "key", "__pokeapp_keep__"),
            ):
                try:
                    client.table(table).delete().neq(column, sentinel).execute()
                except Exception as e:
                    errors.append(f"Supabase {table}: {e}")

            try:
                bucket_ref = client.storage.from_(_bucket_name())
                objects = []
                try:
                    objects = bucket_ref.list("", {"limit": 1000})
                except TypeError:
                    objects = bucket_ref.list()
                names = [
                    str(obj.get("name"))
                    for obj in (objects or [])
                    if isinstance(obj, dict) and obj.get("name")
                ]
                for idx in range(0, len(names), 100):
                    chunk = names[idx: idx + 100]
                    if chunk:
                        bucket_ref.remove(chunk)
            except Exception as e:
                errors.append(f"Supabase storage: {e}")

            remote_done = True
        except Exception as e:
            errors.append(f"Supabase wipe: {e}")

    try:
        if not _supabase_enabled():
            init_storage()
        _wipe_local_sqlite()
    except Exception as e:
        errors.append(f"SQLite local: {e}")

    removed_data_saves = 0
    removed_user_saves = 0
    try:
        removed_data_saves = _delete_dir_contents(SAVES_DIR, DATA_DIR)
    except Exception as e:
        errors.append(f"Saves internos: {e}")
    try:
        from utils import BASE_SAVES_DIR

        removed_user_saves = _delete_dir_contents(BASE_SAVES_DIR, BASE_SAVES_DIR)
    except Exception as e:
        errors.append(f"Saves por usuario: {e}")

    _clear_storage_caches()
    try:
        if st is not None:
            st.cache_data.clear()
    except Exception:
        pass

    return {
        "ok": not errors,
        "errors": errors,
        "remote": remote_done,
        "removed_data_saves": removed_data_saves,
        "removed_user_saves": removed_user_saves,
    }


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


@_cache_data(ttl=20)
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
        try:
            client = _sb()
            bucket = _bucket_name()
            # Subir al bucket (sin upsert para evitar headers invÃ¡lidos)
            client.storage.from_(bucket).upload(
                safe_name,
                content,
                {"content-type": "application/octet-stream"},
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
                    "created_at": _now_iso(),
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
        except Exception:
            return {"id": None, "filename": safe_name, "sha256": sha, "created_at": ts, "url": None}

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


@_cache_data(ttl=15)
def list_saves(limit: int = 50) -> List[Tuple]:
    if _supabase_enabled():
        try:
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
        except Exception:
            return []
    with _conn() as cx:
        return cx.execute(
            "SELECT id, filename, original_name, sha256, uploader, created_at FROM saves ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()


def set_current_save(save_id: int):
    settings_set("current_save", str(save_id))


def get_current_save() -> Optional[Tuple]:
    v = settings_get("current_save")
    if not v:
        return None
    try:
        save_id = int(v)
    except Exception:
        return None
    return _fetch_save_by_id(save_id)


def load_save_bytes(filename: str) -> bytes:
    if _supabase_enabled():
        try:
            client = _sb()
            bucket = _bucket_name()
            # Prefer public URL (bucket es pÃºblico)
            url = client.storage.from_(bucket).get_public_url(filename)
            import httpx

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

@_cache_data(ttl=15)
def list_saves_by_user(user: str, limit: int = 50) -> List[Tuple]:
    if _supabase_enabled():
        try:
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
        except Exception:
            return []
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
    settings_set(_user_key(user), str(int(save_id)))


def get_current_save_for_user(user: str) -> Optional[Tuple]:
    v = settings_get(_user_key(user))
    if not v:
        return None
    try:
        save_id = int(v)
    except Exception:
        return None
    return _fetch_save_by_id(save_id)


def get_current_save_path_for_user(user: str):
    cur = get_current_save_for_user(user)
    if not cur:
        return None
    return SAVES_DIR / cur[1]

# Tienda


def _notify_purchase_inserted(user: str, item: str, price: int, purchase_id: int) -> None:
    try:
        from app.discord_notify import notify_purchase_async

        notify_purchase_async(user=user, item=item, price=int(price), purchase_id=int(purchase_id))
    except Exception:
        pass


def add_purchase(user: str, item: str, price: int) -> int:
    ts = int(time.time())
    if _supabase_enabled():
        try:
            client = _sb()
            res = client.table("purchases").insert(
                {
                    "user": user,
                    "item": item,
                    "price": int(price),
                    "created_at": _now_iso(),
                    "status": "pending",
                    "redeemed_at": None,
                }
            ).execute()
            data = res.data or []
            if data:
                pid = int(data[0].get("id") or 0)
                _invalidate_purchase_caches(user)
                _notify_purchase_inserted(user, item, int(price), pid)
                return pid
        except Exception as e:
            # Supabase estÃ¡ configurado pero fallÃ³: no hacemos fallback silencioso
            raise RuntimeError(f"Supabase add_purchase failed: {e}")
    with _conn() as cx:
        cx.execute(
            "INSERT INTO purchases(user, item, price, created_at, status) VALUES(?,?,?,?,?)",
            (user, item, int(price), ts, 'pending')
        )
        rowid = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
        cx.commit()
        _invalidate_purchase_caches(user)
        pid = int(rowid)
        _notify_purchase_inserted(user, item, int(price), pid)
        return pid


def total_spent(user: str) -> int:
    if not user:
        return 0
    hit, cached = _TOTAL_SPENT_CACHE.get(user)
    if hit:
        return int(cached)

    if _supabase_enabled():
        try:
            client = _sb()
            # 1) RPC opcional; si falla seguimos sin lanzar excepci?n
            try:
                res = client.rpc("rpc_total_spent", {"p_user": user}).execute()
                if res.data:
                    val = res.data[0] if isinstance(res.data, list) else res.data
                    out = int(val)
                    _TOTAL_SPENT_CACHE.set(user, out)
                    return out
            except Exception:
                pass

            # 2) Suma manual en la tabla purchases
            s = 0
            try:
                res = client.table("purchases").select("price").eq("user", user).execute()
                data = res.data or []
                for row in data:
                    try:
                        s += int(row.get("price") or 0)
                    except Exception:
                        continue
            except Exception:
                s = 0

            # 3) Fallback adicional: inventario si sigue en 0
            if s == 0:
                try:
                    inv = list_inventory(user, limit=300)
                    for r in inv or []:
                        try:
                            s += int(r[2] or 0)
                        except Exception:
                            continue
                except Exception:
                    pass
            out = int(s)
            _TOTAL_SPENT_CACHE.set(user, out)
            return out
        except Exception:
            pass
    with _conn() as cx:
        row = cx.execute("SELECT COALESCE(SUM(price),0) FROM purchases WHERE user=?", (user,)).fetchone()
        out = int(row[0] or 0)
        _TOTAL_SPENT_CACHE.set(user, out)
        return out


def list_purchases(user: str | None = None, limit: int = 100):
    cache_key = (user, int(limit))
    hit, cached = _LIST_PURCHASES_CACHE.get(cache_key)
    if hit:
        return list(cached)
    if _supabase_enabled():
        try:
            client = _sb()
            query = client.table("purchases").select("*").order("id", desc=True).limit(limit)
            if user:
                query = query.eq("user", user)
            res = query.execute()
            out = []
            for row in res.data or []:
                out.append(
                    (
                        row.get("id"),
                        row.get("user"),
                        row.get("item"),
                        row.get("price"),
                        _iso_to_ts(row.get("created_at")),
                        row.get("status"),
                        _iso_to_ts(row.get("redeemed_at")),
                    )
                )
            _LIST_PURCHASES_CACHE.set(cache_key, list(out))
            return out
        except Exception:
            pass
    with _conn() as cx:
        if user:
            rows = cx.execute(
                "SELECT id, user, item, price, created_at, status, redeemed_at FROM purchases WHERE user=? ORDER BY id DESC LIMIT ?",
                (user, limit)
            ).fetchall()
            _LIST_PURCHASES_CACHE.set(cache_key, list(rows))
            return rows
        rows = cx.execute(
            "SELECT id, user, item, price, created_at, status, redeemed_at FROM purchases ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        _LIST_PURCHASES_CACHE.set(cache_key, list(rows))
        return rows


def list_inventory(user: str, *, status: str | None = None, limit: int = 200):
    cache_key = (user, status, int(limit))
    hit, cached = _LIST_INVENTORY_CACHE.get(cache_key)
    if hit:
        return list(cached)
    if _supabase_enabled():
        try:
            client = _sb()
            query = (
                client.table("purchases")
                .select("id,item,price,created_at,status,redeemed_at")
                .eq("user", user)
                .order("id", desc=True)
                .limit(limit)
            )
            if status:
                query = query.eq("status", status)
            res = query.execute()
            out = []
            for row in res.data or []:
                out.append(
                    (
                        row.get("id"),
                        row.get("item"),
                        row.get("price"),
                        _iso_to_ts(row.get("created_at")),
                        row.get("status"),
                        _iso_to_ts(row.get("redeemed_at")),
                    )
                )
            _LIST_INVENTORY_CACHE.set(cache_key, list(out))
            return out
        except Exception:
            pass
    with _conn() as cx:
        if status:
            rows = cx.execute(
                "SELECT id, item, price, created_at, status, redeemed_at FROM purchases WHERE user=? AND status=? ORDER BY id DESC LIMIT ?",
                (user, status, limit)
            ).fetchall()
            _LIST_INVENTORY_CACHE.set(cache_key, list(rows))
            return rows
        rows = cx.execute(
            "SELECT id, item, price, created_at, status, redeemed_at FROM purchases WHERE user=? ORDER BY id DESC LIMIT ?",
            (user, limit)
        ).fetchall()
        _LIST_INVENTORY_CACHE.set(cache_key, list(rows))
        return rows

# Redemptions / vouchers

def add_redemption(purchase_id: int, user: str, item: str, payload_json: str) -> int:
    ts = int(time.time())
    if _supabase_enabled():
        try:
            client = _sb()
            res = client.table("redemptions").insert(
                {
                    "purchase_id": int(purchase_id),
                    "user": user,
                    "item": item,
                    "payload_json": payload_json,
                    "created_at": _now_iso(),
                }
            ).execute()
            data = res.data or []
            if data:
                return int(data[0].get("id") or 0)
        except Exception as e:
            raise RuntimeError(f"Supabase add_redemption failed: {e}")
    with _conn() as cx:
        cx.execute(
            "INSERT INTO redemptions(purchase_id, user, item, payload_json, created_at) VALUES(?,?,?,?,?)",
            (int(purchase_id), user, item, payload_json, ts)
        )
        rid = cx.execute("SELECT last_insert_rowid()").fetchone()[0]
        cx.commit()
        return int(rid)


def list_redemptions(user: str | None = None, limit: int = 500):
    if _supabase_enabled():
        try:
            client = _sb()
            query = (
                client.table("redemptions")
                .select("id,purchase_id,user,item,payload_json,created_at")
                .order("id", desc=True)
                .limit(limit)
            )
            if user:
                query = query.eq("user", user)
            res = query.execute()
            out = []
            for row in res.data or []:
                out.append(
                    (
                        row.get("id"),
                        row.get("purchase_id"),
                        row.get("user"),
                        row.get("item"),
                        row.get("payload_json"),
                        _iso_to_ts(row.get("created_at")),
                    )
                )
            return out
        except Exception:
            pass
    with _conn() as cx:
        if user:
            return cx.execute(
                "SELECT id, purchase_id, user, item, payload_json, created_at "
                "FROM redemptions WHERE user=? ORDER BY id DESC LIMIT ?",
                (user, limit),
            ).fetchall()
        return cx.execute(
            "SELECT id, purchase_id, user, item, payload_json, created_at "
            "FROM redemptions ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()


def set_purchase_status(purchase_id: int, status: str) -> None:
    ts = int(time.time())
    if _supabase_enabled():
        try:
            client = _sb()
            data = {"status": status}
            if status == "used":
                data["redeemed_at"] = _now_iso()
            client.table("purchases").update(data).eq("id", int(purchase_id)).execute()
            _invalidate_purchase_caches()
            return
        except Exception as e:
            raise RuntimeError(f"Supabase set_purchase_status failed: {e}")
    with _conn() as cx:
        if status == 'used':
            cx.execute("UPDATE purchases SET status=?, redeemed_at=? WHERE id=?", (status, ts, int(purchase_id)))
        else:
            cx.execute("UPDATE purchases SET status=? WHERE id=?", (status, int(purchase_id)))
        cx.commit()
    _invalidate_purchase_caches()

# Pokemon flags

def _flags_key(owner: str | None, fingerprint: str) -> str:
    if not owner:
        return fingerprint
    prefix = f"{owner}::"
    if fingerprint.startswith(prefix):
        return fingerprint
    return f"{prefix}{fingerprint}"


def _strip_flags_key(owner: str | None, fingerprint: str) -> str:
    if not owner:
        return fingerprint
    prefix = f"{owner}::"
    if fingerprint.startswith(prefix):
        return fingerprint[len(prefix):]
    return fingerprint

def upsert_pokemon_flags(owner: str, fingerprint: str, flags_json: str) -> None:
    ts = int(time.time())
    fp_key = _flags_key(owner, fingerprint)
    if _supabase_enabled():
        try:
            client = _sb()
            client.table("pokemon_flags").upsert(
                {
                    "owner": owner,
                    "fingerprint": fp_key,
                    "flags_json": flags_json,
                    "created_at": _now_iso(),
                    "updated_at": _now_iso(),
                },
                on_conflict="fingerprint",
            ).execute()
            return
        except Exception as e:
            raise RuntimeError(f"Supabase upsert_pokemon_flags failed: {e}")
    with _conn() as cx:
        row = cx.execute("SELECT id FROM pokemon_flags WHERE fingerprint=?", (fp_key,)).fetchone()
        if row:
            cx.execute(
                "UPDATE pokemon_flags SET owner=?, flags_json=?, updated_at=? WHERE id=?",
                (owner, flags_json, ts, int(row[0]))
            )
        else:
            cx.execute(
                "INSERT INTO pokemon_flags(owner, fingerprint, flags_json, created_at, updated_at) VALUES(?,?,?,?,?)",
                (owner, fp_key, flags_json, ts, ts)
            )
        cx.commit()


def get_flags_by_fingerprints(fps: list[str], owner: str | None = None) -> dict:
    if not fps:
        return {}
    owner_filter = owner
    fps_clean = [fp for fp in fps if fp]
    if not fps_clean:
        return {}
    if owner_filter:
        prefixed = [_flags_key(owner_filter, fp) for fp in fps_clean]
        query_fps = list(dict.fromkeys(prefixed + fps_clean))
    else:
        query_fps = fps_clean
    if _supabase_enabled():
        try:
            client = _sb()
            q = client.table("pokemon_flags").select("fingerprint,owner,flags_json").in_("fingerprint", query_fps)
            if owner_filter:
                q = q.eq("owner", owner_filter)
            res = q.execute()
            out = {}
            prefer_ns: set[str] = set()
            prefix = f"{owner_filter}::" if owner_filter else ""
            for row in res.data or []:
                fp_db = row.get("fingerprint")
                if not fp_db:
                    continue
                fp_raw = _strip_flags_key(owner_filter, fp_db)
                is_ns = bool(owner_filter) and str(fp_db).startswith(prefix)
                if fp_raw in out and (fp_raw in prefer_ns and not is_ns):
                    continue
                out[fp_raw] = {
                    "owner": row.get("owner"),
                    "flags_json": row.get("flags_json"),
                }
                if is_ns:
                    prefer_ns.add(fp_raw)
            return out
        except Exception:
            return {}
    qmarks = ",".join(["?"] * len(query_fps))
    with _conn() as cx:
        rows = cx.execute(
            (
                f"SELECT fingerprint, owner, flags_json FROM pokemon_flags "
                f"WHERE fingerprint IN ({qmarks})" + (" AND owner=?" if owner_filter else "")
            ),
            tuple(query_fps + ([owner_filter] if owner_filter else []))
        ).fetchall()
    out = {}
    prefer_ns: set[str] = set()
    prefix = f"{owner_filter}::" if owner_filter else ""
    for fp, row_owner, fj in rows:
        fp_raw = _strip_flags_key(owner_filter, fp)
        is_ns = bool(owner_filter) and str(fp).startswith(prefix)
        if fp_raw in out and (fp_raw in prefer_ns and not is_ns):
            continue
        out[fp_raw] = {"owner": row_owner, "flags_json": fj}
        if is_ns:
            prefer_ns.add(fp_raw)
    return out


def clear_purchases() -> None:
    if _supabase_enabled():
        try:
            client = _sb()
            client.table("purchases").delete().neq("id", -1).execute()
            _invalidate_purchase_caches()
            return
        except Exception:
            pass
    with _conn() as cx:
        cx.execute("DELETE FROM purchases")
        cx.commit()
    _invalidate_purchase_caches()

# Pokemon flags reset helpers

def clear_all_pokemon_flags() -> None:
    if _supabase_enabled():
        try:
            client = _sb()
            client.table("pokemon_flags").delete().neq("fingerprint", "").execute()
            return
        except Exception as e:
            raise RuntimeError(f"Supabase clear_all_pokemon_flags failed: {e}")
    with _conn() as cx:
        cx.execute("DELETE FROM pokemon_flags")
        cx.commit()


def clear_pokemon_flags_for_owner(owner: str) -> None:
    if _supabase_enabled():
        try:
            client = _sb()
            client.table("pokemon_flags").delete().eq("owner", owner).execute()
            return
        except Exception as e:
            raise RuntimeError(f"Supabase clear_pokemon_flags_for_owner failed: {e}")
    with _conn() as cx:
        cx.execute("DELETE FROM pokemon_flags WHERE owner=?", (owner,))
        cx.commit()

# Settings genÃ©ricos

def _ensure_settings_table(cx) -> None:
    try:
        cx.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    except Exception:
        pass


def settings_set(key: str, value: str, *, strict_remote: bool = False) -> None:
    if _supabase_enabled():
        try:
            client = _sb()
            client.table("settings").upsert(
                {"key": key, "value": value},
                on_conflict="key",
            ).execute()
            _SETTINGS_CACHE.set(key, value)
            return
        except Exception as e:
            if strict_remote:
                raise RuntimeError(f"Supabase settings_set failed for {key}: {e}") from e
    elif strict_remote:
        raise RuntimeError(f"Supabase no configurado para guardar settings:{key}")
    with _conn() as cx:
        _ensure_settings_table(cx)
        cx.execute(
            """INSERT INTO settings(key,value) VALUES(?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, value)
        )
        cx.commit()
    _SETTINGS_CACHE.set(key, value)


def settings_get(key: str, *, bypass_cache: bool = False, strict_remote: bool = False) -> str | None:
    if not bypass_cache:
        hit, cached = _SETTINGS_CACHE.get(key)
        if hit:
            return cached

    if _supabase_enabled():
        try:
            client = _sb()
            res = client.table("settings").select("value").eq("key", key).limit(1).execute()
            data = res.data or []
            if data:
                value = data[0].get("value")
                _SETTINGS_CACHE.set(key, value)
                return value
            _SETTINGS_CACHE.clear(key)
            return None
        except Exception as e:
            _SETTINGS_CACHE.clear(key)
            if strict_remote:
                raise RuntimeError(f"Supabase settings_get failed for {key}: {e}") from e
    elif strict_remote:
        raise RuntimeError(f"Supabase no configurado para leer settings:{key}")
    with _conn() as cx:
        try:
            _ensure_settings_table(cx)
            row = cx.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            value = row[0] if row else None
            _SETTINGS_CACHE.set(key, value)
            return value
        except Exception:
            _SETTINGS_CACHE.clear(key)
            return None


def settings_get_uncached(key: str, *, strict_remote: bool = False) -> str | None:
    _SETTINGS_CACHE.clear(key)
    return settings_get(key, bypass_cache=True, strict_remote=strict_remote)


def settings_clear_cache(key: str | None = None) -> None:
    _SETTINGS_CACHE.clear(key)

