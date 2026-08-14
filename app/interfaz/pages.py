from __future__ import annotations

import streamlit as st

from app.interfaz.normativa import (
    get_normativa_section_payloads,
    get_normativa_text,
    render_normativa_home,
)


def page_inicio() -> None:
    from app.interfaz.home import render_home

    render_home()


def page_normativa() -> None:
    try:
        from app.discord_notify import sync_normativa_notification

        sync_normativa_notification(get_normativa_text(), get_normativa_section_payloads())
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


def page_hall_of_fame() -> None:
    try:
        from app.interfaz.hall_of_fame import render_hall_of_fame

        render_hall_of_fame()
    except Exception as e:
        st.error(f"No se pudo cargar Hall of Fame: {e}")


def page_temporada() -> None:
    try:
        from app.interfaz.temporada import render_temporada

        render_temporada()
    except Exception as e:
        st.error(f"No se pudo cargar Temporada: {e}")


def page_previa_combate() -> None:
    try:
        from app.liga.matchup import render_matchup_preview
        from app.liga.context import current_jornada
        from utils import league_users_for_round, users_with_retired_last

        jornada = current_jornada()
        players = users_with_retired_last(league_users_for_round(jornada).keys())
        render_matchup_preview(players)
    except Exception as e:
        st.error(f"No se pudo cargar Team Preview: {e}")


def page_copa() -> None:
    try:
        from app.copa.styles import (
            MODE_INFO,
            render_copa_header,
            render_copa_mode_cards,
            render_copa_styles,
        )
        from app.interfaz.theme import apply_platinum_ui

        apply_platinum_ui("Copa")
        render_copa_styles()
        mode_keys = ["Copa", "Torneo", "Copa Dobles"]
        labels = [MODE_INFO[key]["label"] for key in mode_keys]
        current_label = st.session_state.get("copa_mode_selector", labels[0])
        if current_label not in labels:
            current_label = labels[0]
        fmt = mode_keys[labels.index(current_label)]
        selected_label = st.radio(
            "Formato",
            labels,
            horizontal=True,
            index=labels.index(current_label),
            key="copa_mode_selector",
            label_visibility="collapsed",
        )
        fmt = mode_keys[labels.index(selected_label)]
        render_copa_header(fmt)
        render_copa_mode_cards(fmt)
        if fmt == "Torneo":
            import copa2 as _selected
        elif fmt == "Copa Dobles":
            import copa_dobles as _selected
        else:
            import copa as _selected
        _selected.page_copa()
    except Exception as e:
        st.error(f"No se pudo cargar la copa: {e}")
