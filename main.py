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
from app.interfaz.auth import login_gate  # noqa: E402
from app.interfaz.final_polish import apply_final_polish  # noqa: E402
from app.interfaz.sidebar import render_sidebar  # noqa: E402
from app.interfaz.theme import apply_css  # noqa: E402
from app.interfaz.topbar import render_topbar  # noqa: E402
from app.startup import preload_datasets  # noqa: E402


def router(section: str) -> None:
    if section == "Inicio":
        from app.interfaz.pages import page_inicio as page
    elif section == "Normativa":
        from app.interfaz.pages import page_normativa as page
    elif section == "Liga y Tabla":
        from app.interfaz.pages import page_tabla as page
    elif section == "Hall of Fame":
        from app.interfaz.pages import page_hall_of_fame as page
    elif section == "Temporada":
        from app.interfaz.pages import page_temporada as page
    elif section in ("Team Preview", "Previa Combate"):
        from app.interfaz.pages import page_previa_combate as page
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
    render_topbar(section)
    preload_datasets(section)
    router(section)
    apply_final_polish()


if __name__ == "__main__":
    main()
