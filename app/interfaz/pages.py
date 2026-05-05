from __future__ import annotations

import streamlit as st

from app.interfaz.normativa import NORMATIVA_MD
from app.interfaz.theme import render_poke_separator


def page_inicio() -> None:
    user = st.session_state.get("user") or "-"
    st.header(f"Bienvenido, {user}")
    render_poke_separator()
    st.subheader("Guia rapida")
    st.markdown(
        "1. Ve a 'Saves' y sube tu archivo .sav o .dsv.\n"
        "2. Configura el lector en 'Entrenadores' si es necesario.\n"
        "3. En 'Entrenadores' puedes ver equipo, cajas y detalles.\n"
        "4. En 'Juicios' crea casos, revisa pruebas y aplica castigos.\n"
        "5. En 'Tienda' compra comodines/objetos.\n"
        "6. 'Liga y Tabla' y 'Copa' muestran clasificaciones y emparejamientos."
    )

    try:
        from app.discord_notify import sync_normativa_notification

        sync_normativa_notification(NORMATIVA_MD)
    except Exception:
        pass
    with st.expander("Normativa ChampionsLocke", expanded=False):
        st.markdown(NORMATIVA_MD)


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
