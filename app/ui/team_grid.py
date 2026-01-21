from __future__ import annotations

from typing import List
import json
import streamlit as st

from dexdata import species_types
from pkmmeta import pokemon_fingerprint, pokemon_fingerprint_stable
from storage import get_flags_by_fingerprints
from app.ui.cards import TEAM_IMG_W, ensure_type_css, slot_card_html
from app.entrenadores.sprites import sprite_url_from_p


def team_grid_ui(team: List[dict]) -> None:
    """Enhanced team grid (6 slots) with type chips and flags."""
    ensure_type_css()

    fp_pairs = []
    fp_all = []
    for t in team:
        legacy = None
        stable = None
        try:
            legacy = pokemon_fingerprint(t)
        except Exception:
            legacy = None
        try:
            stable = pokemon_fingerprint_stable(t)
        except Exception:
            stable = None
        fp_pairs.append((legacy, stable))
        if isinstance(legacy, str):
            fp_all.append(legacy)
        if isinstance(stable, str):
            fp_all.append(stable)
    fp_valid = list(dict.fromkeys(fp_all))
    owner = st.session_state.get("trainer_selected") or st.session_state.get("user")
    if owner:
        flags_map = get_flags_by_fingerprints(fp_valid, owner=owner) if fp_valid else {}
    else:
        flags_map = get_flags_by_fingerprints(fp_valid) if fp_valid else {}
    flags_by_fp: dict[str, dict] = {}
    for fp, meta in flags_map.items():
        try:
            fj = meta.get("flags_json")
            if isinstance(fj, str) and fj.strip():
                obj = json.loads(fj)
                if isinstance(obj, dict):
                    flags_by_fp[fp] = obj
        except Exception:
            continue

    st.subheader("Equipo actual")
    cols = st.columns(6)
    for i in range(6):
        with cols[i]:
            if i < len(team):
                t = team[i]
                img_url = sprite_url_from_p(t, prefer_animated=True)
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

                fp_legacy, fp_stable = fp_pairs[i]
                flags = {}
                if fp_legacy in flags_by_fp:
                    flags.update(flags_by_fp[fp_legacy])
                if fp_stable in flags_by_fp:
                    flags.update(flags_by_fp[fp_stable])
                flag_blindado = bool(flags.get("blindado"))
                flag_robado = bool(flags.get("robado"))

                subtitle = species if nickname else ""
                title = nickname if nickname else species
                html = slot_card_html(
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
                        "from": "team",
                        "slot": i + 1,
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
                        "ability": t.get("ability"),
                        "held_item": t.get("held_item") or t.get("Item"),
                        "evs": t.get("evs"),
                    }
                    st.rerun()
            else:
                st.markdown(
                    f"<div class='slot slot-empty'><div class='hint'>Vacio - Slot {i + 1}</div></div>",
                    unsafe_allow_html=True,
                )
