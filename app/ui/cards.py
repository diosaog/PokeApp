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
        css = st.session_state.get("_type_css_platinum_v1")
    except Exception:
        css = None
    if not css:
        css = (
            "<style>"
            ".badges { display:flex; align-items:center; justify-content:space-between; gap:6px; margin-bottom:6px; }"
            ".badge-right { display:flex; align-items:center; justify-content:flex-end; gap:6px; }"
            ".pill { display:inline-block; padding:2px 6px; border-radius:4px; font-weight:900; font-size:0.7rem; "
            "color:#2b2b2b; background:#f1c258; border:2px solid #c28f27; }"
            ".pill-empty { opacity:0.0; }"
            ".pill-shiny { background: #f6e7b2; color:#2b2b2b; border-color: #cbb777; }"
            ".gender-m { background: #b9d9ff; color:#1e3a8a; border-color: #7aa2d8; }"
            ".gender-f { background: #f8c4da; color:#7a1f3a; border-color: #d58aa7; }"
            ".slot { background:#f7f6ef; border:2px solid #9a9680; border-radius:6px; padding:8px 8px 6px; "
            "text-align:center; color:#2b2b2b; font-family: \"Press Start 2P\", monospace; font-weight:900; }"
            ".slot-sep { height:2px; background:#b9b59f; margin: 4px 0 8px; }"
            ".slot img { display:block; margin: 0 auto 2px; filter: none; image-rendering: pixelated; }"
            ".slot .title { letter-spacing: 0.2px; font-size:0.72rem; font-weight:900; color:#111111 !important; "
            "text-shadow: 0 0 1px currentColor; }"
            ".slot .sub { margin-top: 2px; font-size:0.68rem; color:#1f1f1f !important; font-weight:900; "
            "text-shadow: 0 0 1px currentColor; }"
            ".type-chip { display:inline-block; padding:2px 6px; border-radius:4px; color:#fff; font-weight:900; font-size:0.68rem; border:2px solid rgba(0,0,0,0.15); }"
            ".types { margin-top:6px; display:flex; justify-content:center; gap:6px; flex-wrap:wrap; }"
            ".shield-chip { display:inline-block; padding:2px 6px; border-radius:4px; color:#102a43; font-weight:900; font-size:0.68rem; border:2px solid #1e40af; background:#bfdbfe; }"
            ".rob-chip { display:inline-block; padding:2px 6px; border-radius:4px; color:#3b0764; font-weight:900; font-size:0.68rem; border:2px solid #6d28d9; background:#e9d5ff; }"
            ".slot-empty { border:2px dashed #9a9680; background:#f7f6ef; height:120px; display:flex; align-items:center; "
            "justify-content:center; color:#6a6a6a; border-radius:6px; font-family: \"Press Start 2P\", monospace; font-size:0.7rem; }"
            "</style>"
        )
        try:
            st.session_state["_type_css_platinum_v1"] = css
        except Exception:
            pass
    st.markdown(css, unsafe_allow_html=True)
    try:
        st.session_state["_type_css_done"] = True
    except Exception:
        pass
