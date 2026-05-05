# -*- coding: utf-8 -*-
import streamlit as st

from utils import APP_TITLE, APP_ICON, init_session_state, sections_for_user

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import after config to avoid warnings
from app.interfaz.auth import login_gate
from app.interfaz.sidebar import render_sidebar
from app.interfaz.theme import apply_css
from app.startup import preload_datasets


def router(section: str) -> None:
    if section == "Liga y Tabla":
        from app.interfaz.pages import page_tabla as page
    elif section == "Entrenadores":
        from app.interfaz.pages import page_entrenadores as page
    elif section == "Copa":
        from app.interfaz.pages import page_copa as page
    elif section == "Juicios":
        from juicios import page_juicios as page
    elif section == "Tienda":
        from tienda2 import page_tienda as page
    elif section == "Saves":
        from saves import page_saves as page
    else:
        from app.interfaz.pages import page_inicio as page
    page()


def main() -> None:
    apply_css()
    init_session_state()
    login_gate()

    user = st.session_state.get("user")
    section = render_sidebar(sections_for_user(user))
    preload_datasets(section)
    router(section)


if __name__ == "__main__":
    main()
