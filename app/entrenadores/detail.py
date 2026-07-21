from __future__ import annotations

import streamlit as st

from app.entrenadores.detail_calc import _calc_stats_from_base, _extract_stats_from_p, _nature_mods
from app.entrenadores.detail_render import render_detail_html
from i18n import nature_display_es


def pokemon_detail_panel() -> None:
    st.subheader("Detalle del Pokemon")
    p = st.session_state.get("selected_pokemon")
    if not p:
        st.markdown(
            "<div class='panel-dashed'>Selecciona un Pokemon.</div>",
            unsafe_allow_html=True,
        )
        return

    is_own = st.session_state.get("trainer_selected") == st.session_state.get("user")

    def _stat_dict_from(src: dict | None, default_val: int) -> dict:
        out = {}
        for k in ("hp", "atk", "def", "spa", "spd", "spe"):
            v = None if src is None else src.get(k)
            try:
                out[k] = int(v)
            except Exception:
                out[k] = default_val
        return out

    if is_own:
        up_key, down_key = _nature_mods(p.get("nature"))
        stx = _extract_stats_from_p(p) or {}
        ability = p.get("ability") or p.get("Ability")
        nature_txt = nature_display_es(p.get("nature") or "") or "-"
        ivs_display = _stat_dict_from(p.get("ivs") or {}, 0)
        evs_display = _stat_dict_from(p.get("evs") or {}, 0)
    else:
        p = dict(p)
        p["nature"] = None
        up_key, down_key = None, None
        ivs_display = _stat_dict_from(None, 1)
        evs_display = _stat_dict_from(None, 1)
        stx = _calc_stats_from_base(p, ivs=ivs_display, evs=evs_display, nature=None) or {}
        ability = None
        nature_txt = "-"

    html = render_detail_html(
        p=p,
        is_own=is_own,
        stx=stx,
        up_key=up_key,
        down_key=down_key,
        ability=ability,
        nature_txt=nature_txt,
        ivs_display=ivs_display,
        evs_display=evs_display,
    )
    st.markdown(html, unsafe_allow_html=True)
