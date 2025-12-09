# -*- coding: utf-8 -*-
"""
Plantilla limpia (tail) para la vista de Entrenadores.
Texto y símbolos normalizados a UTF‑8. No es usada en tiempo de ejecución.
"""
from __future__ import annotations

from typing import List
import streamlit as st

TOTAL_BOXES = 18

def _slot_empty_html(label: str) -> str:
    return f"""
    <div class='slot slot-empty'>
      <div class='hint'>Vacío – {label}</div>
    </div>
    """

# Marcador: grilla de cajas mínima para referencia
def _boxes_grid_ui(sav_json: dict, box_count: int, box_names: List[str], *, save_path: str | None = None) -> None:
    st.subheader("PC (Cajas)")
    st.info("Esta es una plantilla estática de referencia.")

