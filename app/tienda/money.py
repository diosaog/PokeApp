from __future__ import annotations

from app.liga.coins import coins_from_league
from app.entrenadores.badges import count_badges
from app.interfaz.badges import coins_from_badges
from storage import (
    get_current_save_for_user,
    list_inventory,
    list_saves_by_user,
    load_save_bytes,
    total_spent,
)
from utils import ensure_user_dir, list_user_saves
from conex_pkhex import open_sav_cached
try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore


def _cache_data(ttl: int = 10):
    if st is None:
        return lambda f: f
    return st.cache_data(ttl=ttl, show_spinner=False)


@_cache_data(ttl=10)
def _calc_money_for_user(user: str) -> int:
    liga = coins_from_league(user)
    badge_coins = 0
    badge_found = False
    try:
        spath = None
        cur = get_current_save_for_user(user)
        if cur:
            fname = cur[1]
            p = ensure_user_dir(user) / fname
            if not p.exists():
                data = load_save_bytes(fname)
                if data:
                    p.write_bytes(data)
            if p.exists():
                spath = p

        if spath is None:
            saves = list_user_saves(user)
            if not saves:
                remote = list_saves_by_user(user, limit=1)
                if remote:
                    _, fname, *_ = remote[0]
                    data = load_save_bytes(fname)
                    if data:
                        p = ensure_user_dir(user) / fname
                        p.write_bytes(data)
                        saves = [p]
            if saves:
                spath = saves[0]

        if spath:
            sav_json = open_sav_cached(str(spath))
            badge_found = True
            try:
                badge_coins = 4 * count_badges(sav_json)
            except Exception:
                badge_coins = coins_from_badges(sav_json)
    except Exception:
        badge_coins = 0
        badge_found = False
    if not badge_found:
        try:
            from storage import settings_get
            raw = settings_get(f"badges_count:{user}")
            if raw not in (None, ""):
                badge_coins = 4 * max(int(raw), 0)
        except Exception:
            pass
    total = int(liga + badge_coins)
    return total


@_cache_data(ttl=10)
def _money_available(user: str | None) -> int:
    if not user:
        return 0
    try:
        base = _calc_money_for_user(user)
    except Exception:
        base = 0
    try:
        spent = total_spent(user)
        if spent == 0:
            inv = list_inventory(user, limit=300)
            for r in inv or []:
                try:
                    spent += int(r[2] or 0)
                except Exception:
                    continue
    except Exception:
        spent = 0
    return max(int(base) - int(spent), 0)
