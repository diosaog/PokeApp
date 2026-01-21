from __future__ import annotations

import streamlit as st

from dexdata import type_color
from i18n import translate_types_es


TEAM_IMG_W = 88


def badge_row(level, is_shiny: bool, gender: str | None) -> str:
    lv = f"<span class='pill'>Lv.{level}</span>" if level not in (None, "-") else "<span class='pill pill-empty'>&nbsp;</span>"
    gkey = (gender or "").upper()
    gen_map = {
        "M": ("&#9794;", "gender-m"),
        "F": ("&#9792;", "gender-f"),
    }
    gen_symbol, gen_cls = gen_map.get(gkey, ("", ""))
    gen_html = f"<span class='pill {gen_cls}'>{gen_symbol}</span>" if gen_symbol else ""
    shiny_html = "<span class='pill pill-shiny'>Shiny</span>" if is_shiny else ""
    right_bits = " ".join([b for b in (shiny_html, gen_html) if b]).strip()
    right = right_bits if right_bits else "<span class='pill pill-empty'>&nbsp;</span>"
    return f"<div class='badges'><div>{lv}</div><div class='badge-right'>{right}</div></div><div class='slot-sep'></div>"


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
            ".badges { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:6px; }"
            ".badge-right { display:flex; align-items:center; justify-content:flex-end; gap:6px; }"
            ".pill { display:inline-block; padding:2px 8px; border-radius:0; font-weight:700; font-size:0.72rem; color:#e6edf3; background: rgba(255,255,255,0.08); border:1px solid rgba(255,255,255,0.16); }"
            ".pill-empty { opacity:0.0; }"
            ".pill-shiny { background: linear-gradient(135deg, #f59e0b, #f97316); color:#0b0f14; border-color: rgba(255,255,255,0.35); }"
            ".gender-m { background: rgba(56,189,248,0.2); color:#e0f2fe; border-color: rgba(56,189,248,0.4); }"
            ".gender-f { background: rgba(244,114,182,0.2); color:#ffe4f1; border-color: rgba(244,114,182,0.4); }"
            ".slot-sep { height:1px; background: linear-gradient(90deg, transparent 0 10%, rgba(255,255,255,0.18) 10% 90%, transparent 90% 100%); margin: 4px 0 8px; }"
            ".slot img { display:block; margin: 0 auto 2px; filter: drop-shadow(0 2px 8px rgba(0,0,0,0.35)); image-rendering: pixelated; }"
            ".slot .title { letter-spacing: .3px; }"
            ".slot .sub { margin-top: 2px; }"
            ".type-chip { display:inline-block; padding:2px 8px; border-radius:0; color:#fff; font-weight:600; font-size:0.72rem; }"
            ".types { margin-top:6px; display:flex; justify-content:center; gap:6px; flex-wrap:wrap; }"
            ".shield-chip { display:inline-block; padding:2px 8px; border-radius:0; color:#e9f5ff; font-weight:700; font-size:0.72rem; border:1px solid rgba(255,255,255,0.35); background:#2563eb; }"
            ".rob-chip { display:inline-block; padding:2px 8px; border-radius:0; color:#f6edff; font-weight:700; font-size:0.72rem; border:1px solid rgba(255,255,255,0.35); background:#a855f7; }"
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
