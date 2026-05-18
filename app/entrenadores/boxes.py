from __future__ import annotations

from typing import List
import json
import streamlit as st

from app.entrenadores.cache import cached_box
from app.entrenadores.constants import BOX_IMG_W, DEAD_BOX_INDEX, TOTAL_BOXES
from app.entrenadores.sprites import sprite_url_from_p
from app.ui.cards import ensure_type_css, slot_card_html
from conex_pkhex import extract_box, has_pc_data
from dexdata import species_types
from pkmmeta import pokemon_fingerprint, pokemon_fingerprint_stable
from storage import get_flags_by_fingerprints


def resolve_total_boxes(box_count: int, box_names: List[str]) -> int:
    try:
        if box_count and int(box_count) > 0:
            return min(int(box_count), TOTAL_BOXES)
    except Exception:
        pass
    if box_names:
        return min(len(box_names), TOTAL_BOXES)
    return TOTAL_BOXES


def muertos_box_index(box_count: int) -> int:
    total_boxes = resolve_total_boxes(box_count, [])
    return max(0, min(DEAD_BOX_INDEX, total_boxes - 1))


def boxes_grid_ui(
    sav_json: dict,
    box_count: int,
    box_names: List[str],
    *,
    save_path: str | None = None,
    pc_ok: bool | None = None,
    mtime: float | None = None,
) -> None:
    ensure_type_css()
    st.subheader("PC (Cajas)")
    if pc_ok is None:
        try:
            pc_ok = has_pc_data(sav_json, save_path=save_path)
        except Exception:
            pc_ok = False
    if not pc_ok:
        st.warning("PC no disponible. Revisa el Bridge si persiste.")
        return

    total_boxes = resolve_total_boxes(box_count, box_names)
    virtual_names = list(box_names)[:total_boxes]
    if len(virtual_names) < total_boxes:
        start = len(virtual_names)
        virtual_names += [f"Caja {i+1}" for i in range(start, total_boxes)]

    box_index = st.selectbox(
        "Caja",
        options=list(range(total_boxes)),
        index=0,
        format_func=lambda i: virtual_names[i] if i < len(virtual_names) else f"Caja {i+1}",
    )

    try:
        if save_path and st is not None:
            if mtime is None:
                import os
                mtime = os.path.getmtime(str(save_path))
            box_list = cached_box(str(save_path), mtime, int(box_index))
        else:
            box_list = extract_box(sav_json, box_index, save_path=save_path)
    except Exception as e:
        st.error(f"Error al leer la caja: {e}")
        box_list = []

    fp_pairs = []
    fp_all = []
    for p in box_list:
        legacy = None
        stable = None
        try:
            legacy = pokemon_fingerprint(p)
        except Exception:
            legacy = None
        try:
            stable = pokemon_fingerprint_stable(p)
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

    rows, cols = 5, 6
    idx = 0
    for _ in range(rows):
        row_cols = st.columns(cols)
        for cell in row_cols:
            with cell:
                if idx < len(box_list):
                    p = box_list[idx]
                    img_url = sprite_url_from_p(p, prefer_animated=False)
                    title = p.get("species_name") or p.get("species")
                    try:
                        types = species_types(
                            species_name=title,
                            form_index=p.get("form_index"),
                            form_name=p.get("form_name"),
                            gender=p.get("gender"),
                            dex_id=p.get("dex_id"),
                        )
                    except Exception:
                        types = []
                    fp_legacy, fp_stable = fp_pairs[idx]
                    flags = {}
                    if fp_legacy in flags_by_fp:
                        flags.update(flags_by_fp[fp_legacy])
                    if fp_stable in flags_by_fp:
                        flags.update(flags_by_fp[fp_stable])
                    flag_blindado = bool(flags.get("blindado"))
                    flag_robado = bool(flags.get("robado"))
                    html = slot_card_html(
                        img_url=img_url,
                        title=title,
                        subtitle="",
                        img_w=BOX_IMG_W,
                        level=None,
                        is_shiny=bool(p.get("is_shiny", False)),
                        gender=p.get("gender"),
                        types=types,
                        blindado=flag_blindado,
                        robado=flag_robado,
                    )
                    st.markdown(html, unsafe_allow_html=True)
                    if st.button("Ver", key=f"box_{box_index}_{idx}"):
                        st.session_state.selected_pokemon = {
                            "from": "box",
                            "box": box_index,
                            "slot": idx + 1,
                            "species": title,
                            "nickname": p.get("nickname", ""),
                            "level": p.get("level", "-"),
                            "nature": p.get("nature", "-"),
                            "moves": p.get("moves", []),
                            "moves_detail": p.get("moves_detail"),
                            "form_name": p.get("form_name"),
                            "form_index": p.get("form_index"),
                            "is_shiny": p.get("is_shiny", False),
                            "gender": p.get("gender"),
                            "dex_id": p.get("dex_id"),
                            "ivs": p.get("ivs"),
                            "evs": p.get("evs"),
                            "ability": p.get("ability") or p.get("Ability"),
                            "held_item": p.get("held_item") or p.get("Item"),
                        }
                else:
                    st.markdown(
                        f"<div class='slot slot-empty'><div class='hint'>Vacio - Slot {idx + 1}</div></div>",
                        unsafe_allow_html=True,
                    )
                idx += 1
