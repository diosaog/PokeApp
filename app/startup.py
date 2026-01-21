from __future__ import annotations

import streamlit as st

from dexdata import moves_data, pokedex_data


def preload_datasets() -> None:
    try:
        if st.session_state.get("_preload_done"):
            return
        pokedex_data()
        moves_data()
        st.session_state["_preload_done"] = True
    except Exception:
        pass
