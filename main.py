# -*- coding: utf-8 -*-
import streamlit as st

from utils import APP_TITLE, APP_ICON, SECTIONS, init_session_state
from app.startup import preload_datasets

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Import after config to avoid warnings
ui = __import__("interfaz")
tiend = __import__("tienda2")
saves = __import__("saves")


def router(section: str) -> None:
    pages = {
        "Inicio": ui.page_inicio,
        "Liga y Tabla": ui.page_tabla,
        "Entrenadores": ui.page_entrenadores,
        "Copa": ui.page_copa,
        "Tienda": tiend.page_tienda,
        "Saves": saves.page_saves,
    }
    pages.get(section, ui.page_inicio)()


def main() -> None:
    ui.apply_css()
    init_session_state()
    ui.login_gate()
    preload_datasets()

    section = ui.render_sidebar(SECTIONS)
    router(section)


if __name__ == "__main__":
    main()
