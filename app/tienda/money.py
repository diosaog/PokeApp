from __future__ import annotations

from pathlib import Path

from app.liga.coins import coins_from_league
from app.entrenadores.cache import cached_badge_count
from app.entrenadores.snapshot import clear_trainer_snapshot_runtime_caches, get_trainer_snapshot
from app.interfaz.badges import coins_from_badges
from app.juicios.penalties import get_user_penalties
from storage import (
    get_current_save_for_user,
    list_saves_by_user,
    load_save_bytes,
    settings_get,
    settings_set,
    total_spent,
)
from utils import ensure_user_dir, list_user_saves
try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore


def _cache_data(ttl: int = 10):
    if st is None:
        return lambda f: f
    return st.cache_data(ttl=ttl, show_spinner=False)


LEAGUE_FINISHED_COINS = 12


def _league_finished_reward_key(user: str) -> str:
    return f"league_finished_reward:{user}"


@_cache_data(ttl=10)
def league_finished_claimed(user: str | None) -> bool:
    if not user:
        return False
    try:
        raw = settings_get(_league_finished_reward_key(user))
        if raw in (None, "", "0", "false", "False"):
            return False
        return True
    except Exception:
        return False


def mark_league_finished_claimed(user: str | None) -> bool:
    if not user:
        return False
    try:
        settings_set(_league_finished_reward_key(user), "1")
        return True
    except Exception:
        return False


def league_finished_bonus(user: str | None) -> int:
    return LEAGUE_FINISHED_COINS if league_finished_claimed(user) else 0


@_cache_data(ttl=15)
def _resolve_user_save_path(user: str) -> str | None:
    try:
        cur = get_current_save_for_user(user)
        if cur:
            fname = cur[1]
            p = ensure_user_dir(user) / fname
            if not p.exists():
                data = load_save_bytes(fname)
                if data:
                    p.write_bytes(data)
            if p.exists():
                return str(p)

        saves = list_user_saves(user)
        if saves:
            return str(saves[0])

        remote = list_saves_by_user(user, limit=1)
        if remote:
            _, fname, *_ = remote[0]
            data = load_save_bytes(fname)
            if data:
                p = ensure_user_dir(user) / fname
                p.write_bytes(data)
                return str(p)
    except Exception:
        pass
    return None


@_cache_data(ttl=15)
def _badge_coins_from_save(save_path: str, mtime: float) -> int:
    try:
        return int(4 * cached_badge_count(str(save_path), float(mtime)))
    except Exception:
        try:
            from conex_pkhex import open_sav_cached

            sav_json = open_sav_cached(str(save_path))
            return int(coins_from_badges(sav_json))
        except Exception:
            return 0


def _snapshot_matches_save(snapshot: dict, save_path: str | None) -> bool:
    if not snapshot or not save_path:
        return False
    try:
        path = Path(save_path)
        stat = path.stat()
        if str(snapshot.get("save_name") or "") != path.name:
            return False
        if int(snapshot.get("save_size") or -1) != int(stat.st_size):
            return False
        return abs(float(snapshot.get("save_mtime") or 0.0) - float(stat.st_mtime)) < 0.001
    except Exception:
        return False


@_cache_data(ttl=10)
def money_breakdown(user: str | None) -> dict[str, int | bool]:
    return money_breakdown_from_parts(user)


def money_breakdown_from_parts(
    user: str | None,
    *,
    badge_coins: int | None = None,
    penalties: dict | None = None,
) -> dict[str, int | bool]:
    if not user:
        return {"base": 0, "spent": 0, "coins_reduction": 0, "store_blocked": False, "available": 0}

    penalties = penalties if penalties is not None else get_user_penalties(user)
    if badge_coins is None:
        try:
            base = _calc_money_for_user(user)
        except Exception:
            base = 0
    else:
        try:
            base = int(coins_from_league(user)) + int(badge_coins) + int(league_finished_bonus(user))
        except Exception:
            base = 0
    try:
        spent = total_spent(user)
    except Exception:
        spent = 0
    extra_reduction = int(penalties.get("coins_reduction") or 0)
    store_blocked = bool(penalties.get("store_blocked"))
    available = 0 if store_blocked else max(int(base) - int(spent) - extra_reduction, 0)
    return {
        "base": int(base),
        "spent": int(spent),
        "coins_reduction": extra_reduction,
        "store_blocked": store_blocked,
        "available": int(available),
    }


@_cache_data(ttl=10)
def _calc_money_for_user(user: str) -> int:
    liga = coins_from_league(user)
    badge_coins = 0
    badge_found = False
    spath = None
    try:
        spath = _resolve_user_save_path(user)
        snapshot = get_trainer_snapshot(user)
        if _snapshot_matches_save(snapshot, spath):
            badge_coins = 4 * max(int(snapshot.get("badge_count") or 0), 0)
            badge_found = True
    except Exception:
        badge_coins = 0
        badge_found = False
    try:
        if not badge_found and not spath:
            spath = _resolve_user_save_path(user)
        if spath and not badge_found:
            mtime = Path(spath).stat().st_mtime
            badge_coins = _badge_coins_from_save(str(spath), float(mtime))
            badge_found = True
    except Exception:
        badge_coins = 0
        badge_found = False
    if not badge_found:
        try:
            raw = settings_get(f"badges_count:{user}")
            if raw not in (None, ""):
                badge_coins = 4 * max(int(raw), 0)
        except Exception:
            pass
    total = int(liga + badge_coins + league_finished_bonus(user))
    return total


@_cache_data(ttl=10)
def _money_available(user: str | None) -> int:
    if not user:
        return 0
    return int(money_breakdown(user).get("available") or 0)


def clear_money_caches() -> None:
    for func in (
        league_finished_claimed,
        _resolve_user_save_path,
        _badge_coins_from_save,
        cached_badge_count,
        money_breakdown,
        _calc_money_for_user,
        _money_available,
    ):
        try:
            func.clear()
        except Exception:
            continue
    clear_trainer_snapshot_runtime_caches()
