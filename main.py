# -*- coding: utf-8 -*-
# main.py - núcleo / router
import streamlit as st

from utils import APP_TITLE, APP_ICON, SECTIONS, init_session_state

st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Importar vistas después de configurar la página para evitar warnings
a = __import__('interfaz')
ui = a
# Tienda: usar implementación principal (tienda2)
tienda = __import__('tienda2')
saves = __import__('saves')


def router(section: str) -> None:
    """Despacha a la página seleccionada."""
    pages = {
        "Inicio": ui.page_inicio,
        "Liga y Tabla": ui.page_tabla,
        "Entrenadores": ui.page_entrenadores,
        "Copa": ui.page_copa,
        "Tienda": tienda.page_tienda,
        "Saves": saves.page_saves,
    }
    pages.get(section, ui.page_inicio)()


def main() -> None:
    """Punto de entrada. Orquesta UI; sin lógica de negocio."""
    ui.apply_css()
    init_session_state()
    ui.login_gate()  # corta ejecución si no hay sesión (usa st.stop)

    section = ui.render_sidebar(SECTIONS)
    router(section)


if __name__ == "__main__":
    main()

