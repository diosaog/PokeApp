from __future__ import annotations

import streamlit as st

COINS_BY_POSITION = {
    1: 15, 2: 14, 3: 12, 4: 11, 5: 10,
    6: 11, 7: 9, 8: 8, 9: 6, 10: 4,
}


def coins_from_league(user: str) -> int:
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
                    u: {int(k): int(v) for k, v in mp.items()} for u, mp in res_in.items()
                }
        except Exception:
            pass
    lr = st.session_state.get("league_results", {})
    user_map = lr.get(user, {})
    return sum(COINS_BY_POSITION.get(pos, 0) for pos in user_map.values())
