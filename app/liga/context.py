from __future__ import annotations

import json

try:
    import streamlit as st
except Exception:  # pragma: no cover
    st = None  # type: ignore

from storage import settings_get


def current_jornada(default: int = 1) -> int:
    try:
        if st is not None and st.session_state.get("league_tramo"):
            return max(int(st.session_state.get("league_tramo") or default), 1)
    except Exception:
        pass
    try:
        raw = settings_get("league_state")
        data = json.loads(raw or "{}")
        return max(int(data.get("tramo") or default), 1)
    except Exception:
        return int(default)
