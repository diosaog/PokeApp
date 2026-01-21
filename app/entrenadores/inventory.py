from __future__ import annotations

import unicodedata
import streamlit as st

from app.common import COIN
from storage import list_inventory


def _norm_item(s: str) -> str:
    t = (s or "").strip().lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    return t


def _is_usable_item(name: str) -> bool:
    n = _norm_item(name)
    targets = (
        "revivir pokemon",
        "robar pokemon",
        "blindar pokemon",
        "comodin de blindaje por robo",
    )
    return any(t in n for t in targets)


def _item_icon_url(name: str) -> str:
    if not name:
        return ""
    n = _norm_item(name)
    if "revivir" in n:
        slug = "max-revive"
    elif "robar" in n:
        slug = "dread-plate"
    elif "captura extra" in n:
        slug = "ultra-ball"
    elif "blindar" in n or "blindaje" in n:
        slug = "metal-coat"
    elif "fosil" in n or "fossil" in n or "fsil" in n:
        slug = "helix-fossil"
    else:
        slug = n.replace(" ", "-")
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/{slug}.png"


def _category_for_item(name: str) -> str:
    n = _norm_item(name)
    if any(k in n for k in ("revivir", "robar", "captura extra", "blindar", "comodin")):
        return "Comodines"
    if n.startswith("baya ") or "berry" in n:
        return "Bayas"
    if any(
        k in n
        for k in (
            "gafas elegidas",
            "cinta elegida",
            "panuelo",
            "vidasfera",
            "focus",
            "banda focus",
            "scope",
            "restos",
        )
    ):
        return "Competitivos"
    if any(k in n for k in ("chapa", "menta", "habilidad", "capsula", "evolutivo", "piedra")):
        return "Crianza"
    return "Otros"


def _render_purchase_cards(
    items: list[tuple],
    title: str,
    *,
    show_used: bool = False,
    key_prefix: str = "",
    allow_use: bool = True,
) -> None:
    if not items:
        st.caption(f"Sin {title.lower()}.")
        return
    cols = st.columns(3)
    for idx, row in enumerate(items):
        pid, item, price = row[0], row[1], row[2]
        status = (row[4] if len(row) > 4 else None) or "pendiente"
        status_label = "Disponible" if status != "used" else "Usado"
        badge_cls = "status-ok" if status != "used" else "status-warn"
        icon = _item_icon_url(item)
        col = cols[idx % 3]
        with col:
            st.markdown(
                "<div style='border:1px solid rgba(255,255,255,0.12); border-radius:12px; padding:10px;"
                " background:rgba(255,255,255,0.02); box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03);'>"
                f"<div style='display:flex; gap:10px; align-items:center; margin-bottom:6px;'>"
                f"<img src='{icon}' alt='' width='40' onerror=\"this.style.display='none'\"/>"
                f"<div><strong>{item}</strong><br/><span style='opacity:.8'>{COIN} {price}</span></div>"
                "</div>"
                f"<span class='status-badge {badge_cls}'>{status_label}</span>"
                "</div>",
                unsafe_allow_html=True,
            )
            if (
                allow_use
                and (status != "used")
                and _is_usable_item(item)
                and st.button("Usar", key=f"use_{key_prefix}_{pid}_{idx}")
            ):
                st.session_state["redeem_ctx"] = {"item": item, "pid": pid, "step": 1}
                st.rerun()


def _purchases_inventory_ui(user: str, *, allow_use: bool = True) -> None:
    inv = _inventory_cached(user)
    if not inv:
        st.caption("Sin compras registradas.")
        return
    available = [r for r in inv if len(r) < 5 or not r[4] or r[4] != "used"]
    used = [r for r in inv if len(r) > 4 and r[4] == "used"]
    by_cat: dict[str, list[tuple]] = {}
    for r in available:
        cat = _category_for_item(r[1])
        by_cat.setdefault(cat, []).append(r)
    for cat in ("Comodines", "Bayas", "Competitivos", "Crianza", "Otros"):
        if cat in by_cat:
            st.markdown(f"**{cat}**")
            _render_purchase_cards(by_cat[cat], cat, key_prefix=cat, allow_use=allow_use)
    if used:
        with st.expander("Usados"):
            _render_purchase_cards(used, "Usados", show_used=True, key_prefix="usados", allow_use=allow_use)


@st.cache_data(ttl=5, show_spinner=False)
def _inventory_cached(user: str) -> list[tuple]:
    try:
        return list_inventory(user, status=None, limit=200)
    except Exception:
        return []
