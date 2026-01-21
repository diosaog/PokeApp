from __future__ import annotations

from typing import List
import streamlit as st

from app.entrenadores.cache import cached_box
from app.entrenadores.constants import BOX_IMG_W, TOTAL_BOXES
from app.entrenadores.sprites import sprite_url_from_p
from app.ui.cards import ensure_type_css, slot_card_html
from conex_pkhex import extract_box, has_pc_data
from dexdata import species_types


def resolve_total_boxes(box_count: int, box_names: List[str]) -> int:
    if box_count and box_count > 0:
        return box_count
    if box_names:
        return len(box_names)
    return TOTAL_BOXES


def muertos_box_index(box_count: int) -> int:
    if box_count and box_count > 0:
        return max(0, min(box_count - 1, 17))
    return 17


def boxes_grid_ui(sav_json: dict, box_count: int, box_names: List[str], *, save_path: str | None = None) -> None:
    ensure_type_css()
    st.subheader("PC (Cajas)")
    if not has_pc_data(sav_json, save_path=save_path):
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
            import os
            mtime = os.path.getmtime(str(save_path))
            box_list = cached_box(str(save_path), mtime, int(box_index))
        else:
            box_list = extract_box(sav_json, box_index, save_path=save_path)
    except Exception as e:
        st.error(f"Error al leer la caja: {e}")
        box_list = []

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
                        )
                    except Exception:
                        types = []
                    html = slot_card_html(
                        img_url=img_url,
                        title=title,
                        subtitle="",
                        img_w=BOX_IMG_W,
                        level=None,
                        is_shiny=bool(p.get("is_shiny", False)),
                        gender=p.get("gender"),
                        types=types,
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
