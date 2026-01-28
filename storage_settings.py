from __future__ import annotations
from storage_core import _cache_data, _supabase_enabled, _sb, _conn


def _ensure_settings_table(cx) -> None:
    try:
        cx.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    except Exception:
        pass


def settings_set(key: str, value: str) -> None:
    if _supabase_enabled():
        try:
            client = _sb()
            client.table("settings").upsert(
                {"key": key, "value": value},
                on_conflict="key",
            ).execute()
            return
        except Exception:
            pass
    with _conn() as cx:
        _ensure_settings_table(cx)
        cx.execute(
            """INSERT INTO settings(key,value) VALUES(?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
            (key, value)
        )
        cx.commit()


@_cache_data(ttl=30)
@_cache_data(ttl=15)
def settings_get(key: str) -> str | None:
    if _supabase_enabled():
        try:
            client = _sb()
            res = client.table("settings").select("value").eq("key", key).limit(1).execute()
            data = res.data or []
            if data:
                return data[0].get("value")
        except Exception:
            pass
    with _conn() as cx:
        try:
            _ensure_settings_table(cx)
            row = cx.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row[0] if row else None
        except Exception:
            return None
