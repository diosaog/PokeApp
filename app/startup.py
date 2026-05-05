from __future__ import annotations

import streamlit as st

_DEX_PRELOAD_SECTIONS = {"Entrenadores"}


def preload_datasets(section: str | None = None) -> None:
    if section not in _DEX_PRELOAD_SECTIONS:
        return
    try:
        if st.session_state.get("_dex_preload_done"):
            return
        from dexdata import moves_data, pokedex_data

        pokedex_data()
        moves_data()
        st.session_state["_dex_preload_done"] = True
    except Exception:
        pass
