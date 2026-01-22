from __future__ import annotations

import unicodedata
import streamlit as st

from app.common import COIN
from app.tienda.common import _pokeapi_item_png, _resolve_img_src, _shop_asset
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
    custom = {
        "revivir pokemon": ("Revivir", "max-revive"),
        "robar pokemon": ("robar", "dread-plate"),
        "captura extra": ("captura-extra", "ultra-ball"),
        "blindar pokemon": ("Blindar", "metal-coat"),
        "comodin de blindaje por robo": ("Blindar", "metal-coat"),
        "fosil": ("fosil", "helix-fossil"),
    }
    if n in custom:
        asset_slug, poke_slug = custom[n]
        asset = _shop_asset(asset_slug)
        return _resolve_img_src(asset or "") or _pokeapi_item_png(poke_slug)

    slug_map = {
        "gafas elegidas": "choice-specs",
        "cinta elegida": "choice-band",
        "panuelo elegido": "choice-scarf",
        "restos": "leftovers",
        "banda focus": "focus-sash",
        "vidasfera": "life-orb",
        "hierba blanca": "white-herb",
        "roca del rey": "kings-rock",
        "periscopio": "scope-lens",
        "lupa": "zoom-lens",
        "toxisfera": "toxic-orb",
        "llamasfera": "flame-orb",
        "capsula habilidad": "ability-capsule",
        "chapa dorada": "gold-bottle-cap",
        "chapa plateada": "bottle-cap",
        "menta de naturaleza": "adamant-mint",
        "objeto evolutivo": "dawn-stone",
        "objeto potenciador de tipo": "silk-scarf",
    }
    berry_map = {
        "baya aranja": "oran-berry",
        "baya zidra": "sitrus-berry",
        "baya zreza": "cheri-berry",
        "baya ziuela": "chesto-berry",
        "baya meloc": "pecha-berry",
        "baya safre": "rawst-berry",
        "baya perasi": "aspear-berry",
        "baya atania": "persim-berry",
        "baya aslac": "salac-berry",
        "baya lichi": "liechi-berry",
        "baya petaya": "petaya-berry",
        "baya ganlon": "ganlon-berry",
        "baya apicot": "apicot-berry",
        "baya lansat": "lansat-berry",
        "baya starf": "starf-berry",
        "baya occa": "occa-berry",
        "baya passho": "passho-berry",
        "baya wacan": "wacan-berry",
        "baya rindo": "rindo-berry",
        "baya yache": "yache-berry",
        "baya shuca": "shuca-berry",
        "baya chople": "chople-berry",
        "baya kebia": "kebia-berry",
        "baya coba": "coba-berry",
        "baya payapa": "payapa-berry",
        "baya tanga": "tanga-berry",
        "baya charti": "charti-berry",
        "baya kasib": "kasib-berry",
        "baya haban": "haban-berry",
        "baya colbur": "colbur-berry",
        "baya babiri": "babiri-berry",
        "baya chilan": "chilan-berry",
    }
    if n in berry_map:
        return _pokeapi_item_png(berry_map[n])
    if n in slug_map:
        return _pokeapi_item_png(slug_map[n])
    if "revivir" in n:
        return _pokeapi_item_png("max-revive")
    if "robar" in n:
        return _pokeapi_item_png("dread-plate")
    if "captura extra" in n:
        return _pokeapi_item_png("ultra-ball")
    if "blindar" in n or "blindaje" in n:
        return _pokeapi_item_png("metal-coat")
    if "fosil" in n or "fossil" in n or "fsil" in n:
        return _pokeapi_item_png("helix-fossil")
    slug = n.replace(" ", "-")
    return _pokeapi_item_png(slug)


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
                "<div class='pl-card'>"
                "<div class='pl-row'>"
                f"<img class='pl-icon' src='{icon}' alt='' onerror=\"this.style.display='none'\"/>"
                f"<div><div class='pl-title'>{item}</div><div class='pl-muted'>{COIN} {price}</div></div>"
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
