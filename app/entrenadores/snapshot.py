from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from app.entrenadores.cache import cached_badge_count, cached_box, cached_dead_count, cached_team
from app.entrenadores.constants import DEAD_BOX_INDEX
from storage import get_current_save_for_user, list_saves_by_user, load_save_bytes, settings_get, settings_set
from utils import ensure_user_dir, list_user_saves

SNAPSHOT_VERSION = 1
SNAPSHOT_KEY_PREFIX = "trainer_snapshot"


def _snapshot_key(user: str) -> str:
    return f"{SNAPSHOT_KEY_PREFIX}:{user}"


def _empty_snapshot(user: str, *, save_name: str = "Sin save") -> dict[str, Any]:
    return {
        "version": SNAPSHOT_VERSION,
        "user": user,
        "save_name": save_name,
        "save_path": "",
        "save_mtime": 0.0,
        "save_size": 0,
        "badge_count": 0,
        "dead_count": 0,
        "team": [],
        "updated_at": 0,
        "fresh": False,
    }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return max(int(value), 0)
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _load_stored_snapshot(user: str) -> dict[str, Any] | None:
    try:
        raw = settings_get(_snapshot_key(user))
        if not raw:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        if data.get("version") != SNAPSHOT_VERSION:
            return None
        if str(data.get("user") or "") != str(user):
            return None
        return data
    except Exception:
        return None


def _store_snapshot(user: str, snapshot: dict[str, Any]) -> None:
    try:
        settings_set(_snapshot_key(user), json.dumps(snapshot, ensure_ascii=False, default=str))
    except Exception:
        pass


def _copy_remote_save(user: str, filename: str) -> Path | None:
    try:
        dest = ensure_user_dir(user) / filename
        if not dest.exists():
            data = load_save_bytes(filename)
            if data:
                dest.write_bytes(data)
        return dest if dest.exists() else None
    except Exception:
        return None


def _ensure_any_local_save(user: str) -> None:
    try:
        if list_user_saves(user):
            return
    except Exception:
        pass

    try:
        cur = get_current_save_for_user(user)
        if cur:
            _copy_remote_save(user, str(cur[1]))
            return
    except Exception:
        pass

    try:
        latest = list_saves_by_user(user, limit=1)
        if latest:
            _, filename, *_ = latest[0]
            _copy_remote_save(user, str(filename))
    except Exception:
        pass


def _latest_local_save(user: str) -> Path | None:
    try:
        _ensure_any_local_save(user)
        saves = list_user_saves(user)
        return saves[0] if saves else None
    except Exception:
        return None


def _save_signature(path: Path | None) -> dict[str, Any]:
    if not path:
        return {"save_path": "", "save_name": "Sin save", "save_mtime": 0.0, "save_size": 0}
    try:
        stat = path.stat()
        return {
            "save_path": str(path),
            "save_name": path.name,
            "save_mtime": float(stat.st_mtime),
            "save_size": int(stat.st_size),
        }
    except Exception:
        return {"save_path": str(path), "save_name": path.name, "save_mtime": 0.0, "save_size": 0}


def _is_fresh(snapshot: dict[str, Any] | None, signature: dict[str, Any]) -> bool:
    if not snapshot:
        return False
    try:
        if snapshot.get("version") != SNAPSHOT_VERSION:
            return False
        if str(snapshot.get("save_name") or "") != str(signature.get("save_name") or ""):
            return False
        if _safe_int(snapshot.get("save_size"), -1) != _safe_int(signature.get("save_size"), -2):
            return False
        old_mtime = _safe_float(snapshot.get("save_mtime"))
        new_mtime = _safe_float(signature.get("save_mtime"))
        return abs(old_mtime - new_mtime) < 0.001
    except Exception:
        return False


def _bridge_ready() -> bool:
    try:
        from app.entrenadores.bridge import try_auto_load_bridge

        return bool(try_auto_load_bridge())
    except Exception:
        return False


def _build_snapshot(user: str, path: Path, signature: dict[str, Any]) -> dict[str, Any] | None:
    if not _bridge_ready():
        return None

    save_path = str(path)
    mtime = _safe_float(signature.get("save_mtime"))
    try:
        team = list(cached_team(save_path, mtime) or [])[:6]
    except Exception:
        team = []
    try:
        badge_count = _safe_int(cached_badge_count(save_path, mtime))
    except Exception:
        badge_count = 0
    try:
        dead_count = _safe_int(cached_dead_count(save_path, mtime, DEAD_BOX_INDEX))
    except Exception:
        dead_count = 0

    snapshot = {
        "version": SNAPSHOT_VERSION,
        "user": user,
        **signature,
        "badge_count": badge_count,
        "dead_count": dead_count,
        "team": team,
        "updated_at": int(time.time()),
        "fresh": True,
    }
    _store_snapshot(user, snapshot)
    return snapshot


def get_trainer_snapshot(user: str | None, *, allow_rebuild: bool = True, force: bool = False) -> dict[str, Any]:
    if not user:
        return _empty_snapshot("")

    user = str(user)
    path = _latest_local_save(user)
    signature = _save_signature(path)
    stored = _load_stored_snapshot(user)

    if not path:
        return stored or _empty_snapshot(user)

    if stored and not force and _is_fresh(stored, signature):
        stored["fresh"] = True
        return stored

    if allow_rebuild:
        built = _build_snapshot(user, path, signature)
        if built:
            return built

    if stored:
        stored["fresh"] = False
        return stored

    return _empty_snapshot(user, save_name=str(signature.get("save_name") or "Sin save"))


def refresh_trainer_snapshot(user: str | None) -> dict[str, Any]:
    return get_trainer_snapshot(user, allow_rebuild=True, force=True)


def clear_trainer_snapshot_runtime_caches() -> None:
    for func in (cached_team, cached_box, cached_badge_count, cached_dead_count):
        try:
            func.clear()
        except Exception:
            continue
