from __future__ import annotations

import streamlit as st

from dexdata import moves_data, pokedex_data
from storage import migrate_user_alias


def run_startup_migrations() -> None:
    try:
        if st.session_state.get("_startup_migrations_done"):
            return
        migrate_user_alias("Barto", "Sergio")
        st.session_state["_startup_migrations_done"] = True
    except Exception:
        pass


def preload_datasets() -> None:
    try:
        if st.session_state.get("_preload_done"):
            return
        pokedex_data()
        moves_data()
        st.session_state["_preload_done"] = True
    except Exception:
        pass
