from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Tuple, Any
import httpx
from storage_core import (
    _cache_data, _supabase_enabled, _sb, _bucket_name, _now_iso, _conn,
    _sha256, _iso_to_ts, SAVES_DIR
)
from storage_settings import settings_get, settings_set


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
            # Subir al bucket (sin upsert para evitar headers inválidos)
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
