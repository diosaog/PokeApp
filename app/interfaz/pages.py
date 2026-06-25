from __future__ import annotations

import streamlit as st

from app.interfaz.normativa import NORMATIVA_MD, get_normativa_section_payloads, render_normativa_home


def page_inicio() -> None:
    st.header("Normativa")

    try:
        from app.discord_notify import sync_normativa_notification

        sync_normativa_notification(NORMATIVA_MD, get_normativa_section_payloads())
    except Exception:
        pass
    render_normativa_home()


def page_entrenadores() -> None:
    try:
        import entrenadores as _ent
        if hasattr(_ent, "page_entrenadores"):
            _ent.page_entrenadores()
    except Exception as e:
        st.error(f"No se pudo cargar la vista de entrenadores: {e}")


def page_tabla() -> None:
    try:
        import liga_tabla as _lt
        _lt.page_tabla()
    except Exception as e:
        st.error(f"No se pudo cargar la tabla: {e}")


def page_previa_combate() -> None:
    try:
        from app.liga.matchup import render_matchup_preview
        from utils import USERS

        render_matchup_preview(list(USERS.keys()))
    except Exception as e:
        st.error(f"No se pudo cargar Team Preview: {e}")


def page_copa() -> None:
    try:
        st.subheader("Copa")
        fmt = st.radio("Formato", ["Copa", "Torneo", "Copa Dobles"], horizontal=True)
        st.markdown("---")
        if fmt == "Torneo":
            import copa2 as _selected
        elif fmt == "Copa Dobles":
            import copa_dobles as _selected
        else:
            import copa as _selected
        _selected.page_copa()
    except Exception as e:
        st.error(f"No se pudo cargar la copa: {e}")
