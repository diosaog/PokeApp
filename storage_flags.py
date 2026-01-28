from __future__ import annotations
import time
from storage_core import _supabase_enabled, _sb, _now_iso, _conn


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
            return
        except Exception:
            pass
    with _conn() as cx:
        cx.execute("DELETE FROM purchases")
        cx.commit()

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

# Settings genéricos
