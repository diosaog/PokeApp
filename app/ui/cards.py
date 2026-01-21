from __future__ import annotations

import streamlit as st

from dexdata import type_color
from i18n import translate_types_es


TEAM_IMG_W = 88


def badge_row(level, is_shiny: bool, gender: str | None) -> str:
    lv = f"<span class='pill'>Lv.{level}</span>" if level not in (None, "-") else "<span></span>"
    shiny = "Shiny" if is_shiny else ""
    gen = {"M": "M", "F": "F"}.get((gender or "").upper(), "")
    right = f"<span style='opacity:.9'>{shiny} {gen}</span>".strip()
    return f"<div class='badges'><div>{lv}</div><div>{right}</div></div>"


def slot_card_html(
    *,
    img_url: str,
    title: str,
    subtitle: str,
    img_w: int,
    level,
    is_shiny,
    gender,
    types: list[str] | None = None,
    blindado: bool = False,
    robado: bool = False,
) -> str:
    badges = badge_row(level, bool(is_shiny), gender)
    types_html = ""
    if types:
        labels = translate_types_es(types)
        chips = " ".join(
            f"<span class='type-chip' style='background:{type_color(t)}'>{labels[i]}</span>"
            for i, t in enumerate(types[:2])
        )
        types_html = f"<div class='types'>{chips}</div>"
    chips_html = ""
    if blindado:
        chips_html += "<span class='shield-chip'>Blindado</span>"
    if robado:
        chips_html += "<span class='rob-chip'>Robado</span>"
    if chips_html:
        chips_html = f"<div class='types'>{chips_html}</div>"
    return (
        "<div class='slot'>"
        f"{badges}"
        f"<img src='{img_url}' width='{img_w}' alt='{title}'>"
        f"<div class='title'>{title}</div>"
        f"<div class='sub'>{subtitle}</div>"
        f"{types_html}{chips_html}"
        "</div>"
    )


def ensure_type_css() -> None:
    try:
        css = st.session_state.get("_type_css")
    except Exception:
        css = None
    if not css:
        css = (
            "<style>"
            ".type-chip { display:inline-block; padding:2px 8px; border-radius:999px; color:#fff; font-weight:600; font-size:0.72rem; margin-right:6px; }"
            ".types { margin-top:4px; }"
            ".shield-chip { display:inline-block; padding:2px 8px; border-radius:999px; color:#e9f5ff; font-weight:700; font-size:0.72rem; margin-right:6px; border:1px solid rgba(255,255,255,0.35); background:#2563eb; }"
            ".rob-chip { display:inline-block; padding:2px 8px; border-radius:999px; color:#f6edff; font-weight:700; font-size:0.72rem; margin-right:6px; border:1px solid rgba(255,255,255,0.35); background:#a855f7; }"
            "</style>"
        )
        try:
            st.session_state["_type_css"] = css
        except Exception:
            pass
    st.markdown(css, unsafe_allow_html=True)
    try:
        st.session_state["_type_css_done"] = True
    except Exception:
        pass
