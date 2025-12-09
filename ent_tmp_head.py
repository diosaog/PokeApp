# -*- coding: utf-8 -*-
"""
Plantilla limpia (head) para la vista de Entrenadores.

Este archivo sufrió problemas de codificación en el pasado (acentos rotos),
por lo que se reescribe en UTF‑8 con los textos corregidos. No es usado por
la app en tiempo de ejecución; se mantiene como referencia/documentación.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import streamlit as st

# Tamaños y ajustes
TEAM_IMG_W = 88
BOX_IMG_W = 56
DETAIL_IMG_W = 112
TOTAL_BOXES = 18  # Gen4


# ---------- Utilidades de retratos (placeholder) ----------
PORTRAITS_DIR = Path("assets") / "trainers"

def _slug_candidates(name: str) -> List[str]:
    s = (name or "").strip()
    if not s:
        return []
    base = [s, s.lower(), s.capitalize()]
    norm = s.replace(" ", "_")
    base += [norm, norm.lower()]
    norm2 = s.replace(" ", "-")
    base += [norm2, norm2.lower()]
    return list(dict.fromkeys(base))

def _find_trainer_image(trainer: str) -> str | None:
    try:
        if not PORTRAITS_DIR.exists():
            return None
        exts = (".png", ".jpg", ".jpeg", ".webp")
        for cand in _slug_candidates(trainer):
            for ext in exts:
                p = PORTRAITS_DIR / f"{cand}{ext}"
                if p.exists():
                    return str(p)
        # Búsqueda case-insensitive por si los nombres no coinciden exactamente
        low = {f.name.lower(): str(f) for f in PORTRAITS_DIR.glob("*") if f.suffix.lower() in exts}
        for cand in _slug_candidates(trainer):
            for ext in exts:
                key = f"{cand}{ext}".lower()
                if key in low:
                    return low[key]
        return None
    except Exception:
        return None

def _badge_row(level: int | str | None, is_shiny: bool, gender: str | None) -> str:
    lv = f"<span class='pill'>Lv.{level}</span>" if level not in (None, "-") else "<span></span>"
    sh = "★" if is_shiny else ""
    gd = {"M": "♂", "F": "♀"}.get((gender or "").upper(), "")
    right = f"<span style='opacity:.9'>{sh} {gd}</span>".strip()
    return f"<div class='badges'><div>{lv}</div><div>{right}</div></div>"

def _slot_empty_html(label: str) -> str:
    return f"""
    <div class='slot slot-empty'>
      <div class='hint'>Vacío – {label}</div>
    </div>
    """

# Marcadores mínimos para evitar errores si alguien importa esta plantilla
def _url_official_art_by_id(dex_id: int) -> str:
    return (
        "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/"
        f"pokemon/other/official-artwork/{dex_id}.png"
    )

def _sprite_url_from_p(p: dict, *, prefer_animated: bool = True) -> str:
    # En la plantilla devolvemos el art oficial si hay dex_id
    dex_id = p.get("dex_id")
    if isinstance(dex_id, int) and dex_id > 0:
        return _url_official_art_by_id(dex_id)
    return f"https://via.placeholder.com/{TEAM_IMG_W}?text=PKM"

