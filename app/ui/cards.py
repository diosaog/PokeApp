from __future__ import annotations

import streamlit as st

from app.ui.type_icons import type_icon_html


TEAM_IMG_W = 104


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
        chips = " ".join(
            type_icon_html(t, label=True, compact=True, class_name="slot-type-badge")
            for t in types[:2]
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
        "<div class='slot team-slot-card'>"
        f"{badges}"
        f"<img src='{img_url}' width='{img_w}' alt='{title}'>"
        f"<div class='title'>{title}</div>"
        f"<div class='sub'>{subtitle}</div>"
        f"{types_html}{chips_html}"
        "</div>"
    )


def ensure_type_css() -> None:
    try:
        css = st.session_state.get("_type_css_bw2_v1")
    except Exception:
        css = None
    if not css:
        css = (
            "<style>"
            ".badges { display:flex; align-items:center; justify-content:space-between; gap:6px; margin-bottom:6px; }"
            ".badge-right { display:flex; align-items:center; justify-content:flex-end; gap:6px; }"
            ".pill { display:inline-block; padding:2px 6px; border-radius:0; font-family:var(--font-pixel); font-weight:700; font-size:0.55rem; "
            "color:#ffffff; background:linear-gradient(180deg,var(--accent) 0%, var(--accent-dark) 100%); border:1px solid var(--bw2-edge-strong); }"
            ".pill-empty { opacity:0.0; }"
            ".pill-shiny { background: linear-gradient(180deg,#f6e39c 0%, #b68a28 100%); color:#1d1610; border-color:#fff1be; }"
            ".gender-m { background: linear-gradient(180deg,#79b9f5 0%, #376c96 100%); color:#ffffff; border-color:#d8dfe8; }"
            ".gender-f { background: linear-gradient(180deg,#f48bbb 0%, #9e3f68 100%); color:#ffffff; border-color:#f8d4e4; }"
            ".slot { background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%); border:1px solid var(--bw2-edge); border-radius:0; padding:8px 8px 6px; "
            "text-align:center; color:var(--bw2-text); font-family:var(--font-ui); font-weight:400; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28); }"
            ".slot-sep { height:2px; background:linear-gradient(90deg, transparent 0%, var(--accent) 18%, var(--accent) 82%, transparent 100%); margin: 4px 0 8px; }"
            ".slot img { display:block; margin: 0 auto 2px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.35)); image-rendering: pixelated; }"
            ".slot .title { letter-spacing: 0.04em; font-size:0.62rem; font-family:var(--font-pixel); font-weight:700; color:var(--bw2-text) !important; text-transform:uppercase; }"
            ".slot .sub { margin-top: 2px; font-size:1rem; color:var(--bw2-text-soft) !important; font-weight:400; }"
            ".type-chip { display:inline-block; padding:2px 6px; border-radius:0; color:#fff; font-family:var(--font-pixel); font-weight:700; font-size:0.55rem; border:1px solid rgba(255,255,255,0.16); }"
            ".types { margin-top:6px; display:flex; justify-content:center; gap:6px; flex-wrap:wrap; }"
            ".shield-chip { display:inline-block; padding:2px 6px; border-radius:0; color:#ffffff; font-family:var(--font-pixel); font-weight:700; font-size:0.55rem; border:1px solid #d8dfe8; background:linear-gradient(180deg,#79b9f5 0%, #376c96 100%); }"
            ".rob-chip { display:inline-block; padding:2px 6px; border-radius:0; color:#ffffff; font-family:var(--font-pixel); font-weight:700; font-size:0.55rem; border:1px solid #ecd8ff; background:linear-gradient(180deg,#cf74ff 0%, #74389f 100%); }"
            ".slot-empty { border:1px dashed var(--bw2-edge); background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%); height:120px; display:flex; align-items:center; "
            "justify-content:center; color:var(--bw2-text-dim); border-radius:0; font-family:var(--font-pixel); font-size:0.58rem; text-transform:uppercase; }"
            "</style>"
        )
        try:
            st.session_state["_type_css_bw2_v1"] = css
        except Exception:
            pass
    st.markdown(css, unsafe_allow_html=True)
    try:
        st.session_state["_type_css_done"] = True
    except Exception:
        pass
