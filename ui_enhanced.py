from __future__ import annotations
import streamlit as st
from typing import List

from dexdata import species_types, type_color
from pkmmeta import pokemon_fingerprint
from storage import get_flags_by_fingerprints
import json
from i18n import translate_types_es

# Match sizes used in entrenadores.py
TEAM_IMG_W = 88


def _badge_row(level, is_shiny: bool, gender: str | None) -> str:
    lv = f"<span class='pill'>Lv.{level}</span>" if level not in (None, "-") else "<span></span>"
    sh = "\u2605" if is_shiny else ""
    gd = {"M": "\u2642", "F": "\u2640"}.get((gender or "").upper(), "")
    right = f"<span style='opacity:.9'>{sh} {gd}</span>".strip()
    return f"<div class='badges'><div>{lv}</div><div>{right}</div></div>"


def _slot_card_html(*, img_url: str, title: str, subtitle: str, img_w: int, level, is_shiny, gender, types: list[str] | None = None, blindado: bool = False, robado: bool = False) -> str:
    badges = _badge_row(level, is_shiny, gender)
    types_html = ""
    if types:
        labels = translate_types_es(types)
        chips = " ".join(
            f"<span class='type-chip' style='background:{type_color(t)}'>{labels[i]}</span>" for i, t in enumerate(types[:2])
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


def _ensure_type_css() -> None:
    # Inyectar siempre; el DOM de Streamlit se recompone en cada rerun.
    css = (
        "<style>"
        ".type-chip { display:inline-block; padding:2px 8px; border-radius:999px; color:#fff; font-weight:600; font-size:0.72rem; margin-right:6px; }"
        ".types { margin-top:4px; }"
        ".shield-chip { display:inline-block; padding:2px 8px; border-radius:999px; color:#e9f5ff; font-weight:700; font-size:0.72rem; margin-right:6px; border:1px solid rgba(255,255,255,0.35); background:#2563eb; }"
        ".rob-chip { display:inline-block; padding:2px 8px; border-radius:999px; color:#f6edff; font-weight:700; font-size:0.72rem; margin-right:6px; border:1px solid rgba(255,255,255,0.35); background:#a855f7; }"
        "</style>"
    )
    st.markdown(css, unsafe_allow_html=True)
    try:
        st.session_state["_type_css_done"] = True
    except Exception:
        pass


def team_grid_ui(team: List[dict]) -> None:
    """Enhanced team grid (6 slots) with type chips and stateful selection."""
    _ensure_type_css()
    # Precalcular blindajes para todo el equipo en una sola consulta
    fps = []
    for t in team:
        try:
            fps.append(pokemon_fingerprint(t))
        except Exception:
            fps.append(None)
    fp_valid = [fp for fp in fps if isinstance(fp, str)]
    flags_map = get_flags_by_fingerprints(fp_valid) if fp_valid else {}
    blindados: set[str] = set()
    robados: set[str] = set()
    for fp, meta in flags_map.items():
        try:
            fj = meta.get("flags_json")
            if isinstance(fj, str) and fj.strip():
                obj = json.loads(fj)
                if isinstance(obj, dict):
                    if obj.get("blindado"):
                        blindados.add(fp)
                    if obj.get("robado"):
                        robados.add(fp)
        except Exception:
            continue
    st.subheader("Equipo actual")
    cols = st.columns(6)
    for i in range(6):
        with cols[i]:
            if i < len(team):
                t = team[i]
                # reuse sprite helper from entrenadores to keep consistent visuals
                from entrenadores import _sprite_url_from_p  # local import to avoid cycles
                img_url = _sprite_url_from_p(t, prefer_animated=True)
                nickname = t.get("nickname") or ""
                species = t.get("species_name") or t.get("species")
                try:
                    types = species_types(
                        species_name=species,
                        form_index=t.get("form_index"),
                        form_name=t.get("form_name"),
                        gender=t.get("gender"),
                    )
                except Exception:
                    types = []
                flag_blindado = False
                try:
                    fp = fps[i]
                    flag_blindado = isinstance(fp, str) and fp in blindados
                    flag_robado = isinstance(fp, str) and fp in robados
                except Exception:
                    flag_blindado = False
                    flag_robado = False
                subtitle = species if nickname else ""
                title = nickname if nickname else species
                html = _slot_card_html(
                    img_url=img_url,
                    title=title,
                    subtitle=subtitle,
                    img_w=TEAM_IMG_W,
                    level=t.get("level", "-"),
                    is_shiny=bool(t.get("is_shiny", False)),
                    gender=t.get("gender"),
                    types=types,
                    blindado=flag_blindado,
                    robado=flag_robado,
                )
                st.markdown(html, unsafe_allow_html=True)
                if st.button("Ver detalles", key=f"team_view_{i}"):
                    st.session_state.selected_pokemon = {
                        "from": "team", "slot": i + 1,
                        "species": species,
                        "nickname": nickname,
                        "level": t.get("level", "-"),
                        "nature": t.get("nature", "-"),
                        "moves": t.get("moves", []),
                        "moves_detail": t.get("moves_detail"),
                        "form_name": t.get("form_name"),
                        "form_index": t.get("form_index"),
                        "is_shiny": t.get("is_shiny", False),
                        "gender": t.get("gender"),
                        "dex_id": t.get("dex_id"),
                        "ivs": t.get("ivs"),
                        "held_item": t.get("held_item") or t.get("Item"),
                        "evs": t.get("evs"),
                    }
            else:
                st.markdown(
                    "<div class='slot slot-empty'><div class='hint'>Vacio - Slot {}</div></div>".format(i + 1),
                    unsafe_allow_html=True,
                )




