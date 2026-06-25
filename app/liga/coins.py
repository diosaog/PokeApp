from __future__ import annotations

import streamlit as st

from app.liga.eligibility import counts_for_league_reward
from app.liga.rewards import (
    CURRENT_COINS_BY_POSITION,
    coins_for_league_position,
    field_size_for_round_results,
)
from utils import active_users

COINS_BY_POSITION = CURRENT_COINS_BY_POSITION


def _visible_league_users() -> dict[str, str]:
    return active_users()


def coins_from_league(user: str) -> int:
    if user not in _visible_league_users():
        return 0
    try:
        from app.liga.state import restore_state

        restore_state()
    except Exception:
        pass
    if "league_results" not in st.session_state or not st.session_state.get("league_results"):
        try:
            import json
            from storage import settings_get
            raw = settings_get("league_state")
            if raw:
                obj = json.loads(raw)
                res_in = obj.get("results", {})
                st.session_state.league_results = {
                    u: {int(k): int(v) for k, v in mp.items()}
                    for u, mp in res_in.items()
                }
        except Exception:
            pass
    lr = st.session_state.get("league_results", {})
    user_map = lr.get(user, {})
    return sum(
        coins_for_league_position(
            int(tramo),
            int(pos),
            field_size=field_size_for_round_results(lr, int(tramo)),
        )
        for tramo, pos in user_map.items()
        if counts_for_league_reward(user, int(tramo))
    )
