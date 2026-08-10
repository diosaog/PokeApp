from __future__ import annotations

from html import escape
import re

import streamlit as st


def _current_division(user: str, league: dict) -> str:
    if user in (league.get("division_a") or []):
        return "Division A"
    if user in (league.get("division_b") or []):
        return "Division B"
    return "Liga"


def _coin_count(title: str) -> str:
    match = re.search(r"\d+", str(title or ""))
    return match.group(0) if match else "0"


def _initials(user: str) -> str:
    cleaned = str(user or "?").strip()
    return (cleaned[:2] or "?").upper()


def render_topbar(section: str | None = None) -> None:
    user = str(st.session_state.get("user") or "").strip()
    if not user or user == "-":
        return

    try:
        from app.interfaz.notifications import (
            collect_notifications,
            league_state_snapshot,
            money_snapshot,
            notification_count,
        )
        from app.liga.context import current_jornada
        from app.season.config import max_rounds

        jornada = int(current_jornada())
        league = league_state_snapshot()
        coins = _coin_count(money_snapshot(user).get("title") or "")
        notices = notification_count(collect_notifications(user=user, jornada=jornada))
        total_rounds = int(max_rounds(jornada))
        division = _current_division(user, league)
    except Exception:
        jornada = 1
        total_rounds = 1
        coins = "0"
        notices = 0
        division = "Liga"

    section_label = "Liga" if section == "Liga y Tabla" else str(section or "Inicio")
    st.markdown(
        (
            "<div class='poke-topbar'>"
            "<div class='poke-topbar-left'>"
            f"<span class='poke-topbar-round'>Jornada {jornada}/{total_rounds}</span>"
            "<span class='poke-topbar-sep' aria-hidden='true'>&middot;</span>"
            f"<span>{escape(division)}</span>"
            "<span class='poke-topbar-sep' aria-hidden='true'>&middot;</span>"
            f"<span>{escape(section_label)}</span>"
            "</div>"
            "<div class='poke-topbar-right'>"
            "<span class='poke-topbar-pill poke-topbar-money'>"
            "<span class='poke-coin-mark' aria-hidden='true'></span>"
            f"<strong>{escape(coins)}</strong>"
            "</span>"
            "<span class='poke-topbar-pill'>"
            "<span class='poke-topbar-icon poke-topbar-bell' aria-hidden='true'></span>"
            f"<strong>{int(notices)}</strong>"
            "</span>"
            f"<span class='poke-topbar-user'><span>{escape(_initials(user))}</span>{escape(user)}</span>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
