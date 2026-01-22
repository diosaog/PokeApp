from __future__ import annotations

import html as _html
import streamlit as st

from app.common import COIN
from app.tienda.common import _fix_text, _norm, _pokeapi_item_png, _resolve_img_src, _shop_asset
from app.tienda.money import _money_available


def _render_item_card(item: dict, idx_key: str, *, available: int | None = None) -> None:
    name = item.get("name")
    price = int(item.get("price", 0))
    desc = item.get("desc") or ""
    icon = item.get("icon") or ""
    img = item.get("img")

    name = _fix_text(name)
    desc = _fix_text(desc)

    if not img and name:
        try:
            n = _norm(name)
            if "revivir" in n:
                img = _shop_asset("revivir") or _pokeapi_item_png("max-revive")
            elif "robar" in n:
                img = _shop_asset("robar") or _pokeapi_item_png("dread-plate")
            elif "captura extra" in n:
                img = _shop_asset("captura-extra") or _pokeapi_item_png("ultra-ball")
            elif "blindar" in n:
                img = _shop_asset("blindar") or _pokeapi_item_png("metal-coat")
            elif ("fosil" in n) or ("fsil" in n):
                img = _shop_asset("fosil") or _pokeapi_item_png("helix-fossil")
        except Exception:
            img = None
    img = _resolve_img_src(img or "")

    user = st.session_state.get("user") or "-"
    if available is None:
        available = _money_available(user)
    afford = available >= price
    img_html = ""
    if img:
        img_html = (
            "<img class='shop-icon' "
            "style='width:42px; height:42px; image-rendering:pixelated;' "
            f"src='{img}' alt='' onerror=\"this.style.display='none'\"/>"
        )
    else:
        img_html = f"<div style='font-size:20px; line-height:1;'>{icon}</div>" if icon else ""
    name_html = _html.escape(str(name)) if name else "-"
    desc_html = _html.escape(str(desc)) if desc else ""
    price_html = f"{COIN} {price}"
    missing_html = ""
    if (available is not None) and (not afford) and price > 0:
        missing_html = f"<div class='shop-missing'>Faltan {COIN} {price - available}</div>"

    card_style = (
        "background:#f7f6ef; border:2px solid #9a9680; border-radius:6px; padding:0; "
        "color:#2b2b2b; margin-bottom:8px; overflow:hidden; "
        "font-family:\"Press Start 2P\", monospace; font-weight:700;"
    )
    head_style = "background:#f1c258; border-bottom:2px solid #c28f27; padding:6px 8px;"
    body_style = "display:flex; align-items:center; gap:8px; padding:8px;"
    name_style = "font-size:11px; color:#2b2b2b;"
    desc_style = "font-size:10px; color:#3b3b3b; margin-top:4px;"
    price_style = (
        "display:inline-block; margin-top:6px; background:#f1c258; border:2px solid #c28f27; "
        "border-radius:4px; padding:4px 6px; font-size:10px; color:#2b2b2b;"
    )
    missing_style = "font-size:10px; color:#7a2e2e; margin-top:4px;"
    info_html = ""
    if desc_html:
        info_html += f"<div class='shop-desc' style='{desc_style}'>{desc_html}</div>"
    info_html += f"<div class='shop-price' style='{price_style}'>{price_html}</div>"
    if missing_html:
        info_html += missing_html.replace("shop-missing", "shop-missing' style='" + missing_style)
    st.markdown(
        "<div class='shop-card' style='" + card_style + "'>"
        f"<div class='shop-head' style='{head_style}'><span class='shop-name' style='{name_style}'>{name_html}</span></div>"
        f"<div class='shop-body' style='{body_style}'>"
        f"{img_html}"
        "<div class='shop-info' style='display:flex; flex-direction:column; gap:2px;'>"
        + info_html
        + "</div></div></div>",
        unsafe_allow_html=True,
    )
    if st.button("Comprar", key=f"buy_{idx_key}", disabled=(not afford) or price <= 0, use_container_width=True):
        st.session_state.pop("shop_error", None)
        st.session_state["shop_pending"] = {"name": name, "price": int(price)}
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


def _render_shop_items(items: list[dict], category_key: str, *, available: int | None = None) -> None:
    if category_key == "comodines":
        try:
            for it in items:
                n = _norm(it.get("name") or "")
                if ("fosil" in n or (n.startswith("f") and "sil" in n) or "fossil" in n) and ("img" not in it):
                    it["img"] = _shop_asset("fosil") or _pokeapi_item_png("helix-fossil")
                elif ("captura" in n and "extra" in n) and ("img" not in it):
                    it["img"] = _shop_asset("captura-extra") or _pokeapi_item_png("ultra-ball")
                elif ("robar" in n) and ("img" not in it):
                    it["img"] = _shop_asset("robar") or _pokeapi_item_png("dread-plate")
                elif ("revivir" in n) and ("img" not in it):
                    it["img"] = _shop_asset("revivir") or _pokeapi_item_png("max-revive")
                elif ("blindar" in n) and ("img" not in it):
                    it["img"] = _shop_asset("blindar") or _pokeapi_item_png("metal-coat")
        except Exception:
            pass
    elif category_key == "crianza":
        try:
            for it in items:
                n = _norm(it.get("name") or "")
                if ("menta" in n) and (not it.get("img")):
                    it["img"] = _shop_asset("adamant-mint") or _pokeapi_item_png("adamant-mint")
        except Exception:
            pass
    else:
        try:
            for it in items:
                if not it.get("img"):
                    n = it.get("name") or ""
                    it["img"] = _shop_asset(n) or it.get("img")
        except Exception:
            pass

    cols = st.columns(3)
    for idx, it in enumerate(items):
        col = cols[idx % 3]
        with col:
            _render_item_card(it, f"{category_key}_{idx}", available=available)
    st.write("")


def get_catalog() -> dict[str, list[dict]]:
    comodines = [
        {"name": "Revivir Pokemon", "price": 12, "icon": "", "img": _shop_asset("Revivir") or _shop_asset("revivir") or _pokeapi_item_png("max-revive")},
        {"name": "Robar Pokemon", "price": 12, "icon": "", "img": _shop_asset("robar") or _pokeapi_item_png("dread-plate")},
        {"name": "Captura Extra", "price": 5, "icon": "", "img": _shop_asset("captura-extra") or _pokeapi_item_png("ultra-ball")},
        {"name": "Blindar Pokemon", "price": 12, "icon": "", "img": _shop_asset("Blindar") or _shop_asset("blindar") or _pokeapi_item_png("metal-coat")},
        {"name": "Fosil", "price": 5, "icon": "", "img": _shop_asset("fosil") or _pokeapi_item_png("helix-fossil")},
    ]
    bayas = [
        {"name": "Baya Aranja", "price": 2, "img": _pokeapi_item_png("oran-berry"), "desc": "Restaura 10 PS al 50% PS."},
        {"name": "Baya Zidra", "price": 3, "img": _pokeapi_item_png("sitrus-berry"), "desc": "Restaura 25% de PS maximos."},
        {"name": "Baya Zreza", "price": 2, "img": _pokeapi_item_png("cheri-berry"), "desc": "Cura paralisis."},
        {"name": "Baya Ziuela", "price": 3, "img": _pokeapi_item_png("chesto-berry"), "desc": "Cura sueno."},
        {"name": "Baya Meloc", "price": 2, "img": _pokeapi_item_png("pecha-berry"), "desc": "Cura envenenamiento."},
        {"name": "Baya Safre", "price": 2, "img": _pokeapi_item_png("rawst-berry"), "desc": "Cura quemaduras."},
        {"name": "Baya Perasi", "price": 2, "img": _pokeapi_item_png("aspear-berry"), "desc": "Cura congelacion."},
        {"name": "Baya Atania", "price": 2, "img": _pokeapi_item_png("persim-berry"), "desc": "Cura confusion."},
        {"name": "Baya Aslac", "price": 2, "img": _pokeapi_item_png("salac-berry"), "desc": "Velocidad +1 etapa (x1.5) al 25% PS."},
        {"name": "Baya Lichi", "price": 2, "img": _pokeapi_item_png("liechi-berry"), "desc": "Ataque +1 etapa (x1.5) al 25% PS."},
        {"name": "Baya Petaya", "price": 2, "img": _pokeapi_item_png("petaya-berry"), "desc": "At. Esp. +1 etapa (x1.5) al 25% PS."},
        {"name": "Baya Ganlon", "price": 2, "img": _pokeapi_item_png("ganlon-berry"), "desc": "Defensa +1 etapa al 25% PS."},
        {"name": "Baya Apicot", "price": 2, "img": _pokeapi_item_png("apicot-berry"), "desc": "Def. Esp. +1 etapa al 25% PS."},
        {"name": "Baya Lansat", "price": 2, "img": _pokeapi_item_png("lansat-berry"), "desc": "Ratio critico +2 etapas al 25% PS."},
        {"name": "Baya Starf", "price": 2, "img": _pokeapi_item_png("starf-berry"), "desc": "Sube mucho una stat al azar (1 uso)."},
        {"name": "Baya Occa (Fuego)", "price": 3, "img": _pokeapi_item_png("occa-berry"), "desc": "Reduce dano de Fuego supereficaz un 50% (1 vez)."},
        {"name": "Baya Passho (Agua)", "price": 3, "img": _pokeapi_item_png("passho-berry"), "desc": "Reduce dano de Agua supereficaz un 50% (1 vez)."},
        {"name": "Baya Wacan (Electrico)", "price": 3, "img": _pokeapi_item_png("wacan-berry"), "desc": "Reduce dano de Electrico supereficaz un 50% (1 vez)."},
        {"name": "Baya Rindo (Planta)", "price": 3, "img": _pokeapi_item_png("rindo-berry"), "desc": "Reduce dano de Planta supereficaz un 50% (1 vez)."},
        {"name": "Baya Yache (Hielo)", "price": 3, "img": _pokeapi_item_png("yache-berry"), "desc": "Reduce dano de Hielo supereficaz un 50% (1 vez)."},
        {"name": "Baya Shuca (Tierra)", "price": 3, "img": _pokeapi_item_png("shuca-berry"), "desc": "Reduce dano de Tierra supereficaz un 50% (1 vez)."},
        {"name": "Baya Chople (Lucha)", "price": 3, "img": _pokeapi_item_png("chople-berry"), "desc": "Reduce dano de Lucha supereficaz un 50% (1 vez)."},
        {"name": "Baya Kebia (Veneno)", "price": 3, "img": _pokeapi_item_png("kebia-berry"), "desc": "Reduce dano de Veneno supereficaz un 50% (1 vez)."},
        {"name": "Baya Coba (Volador)", "price": 3, "img": _pokeapi_item_png("coba-berry"), "desc": "Reduce dano de Volador supereficaz un 50% (1 vez)."},
        {"name": "Baya Payapa (Psiquico)", "price": 3, "img": _pokeapi_item_png("payapa-berry"), "desc": "Reduce dano de Psiquico supereficaz un 50% (1 vez)."},
        {"name": "Baya Tanga (Bicho)", "price": 3, "img": _pokeapi_item_png("tanga-berry"), "desc": "Reduce dano de Bicho supereficaz un 50% (1 vez)."},
        {"name": "Baya Charti (Roca)", "price": 3, "img": _pokeapi_item_png("charti-berry"), "desc": "Reduce dano de Roca supereficaz un 50% (1 vez)."},
        {"name": "Baya Kasib (Fantasma)", "price": 3, "img": _pokeapi_item_png("kasib-berry"), "desc": "Reduce dano de Fantasma supereficaz un 50% (1 vez)."},
        {"name": "Baya Haban (Dragon)", "price": 3, "img": _pokeapi_item_png("haban-berry"), "desc": "Reduce dano de Dragon supereficaz un 50% (1 vez)."},
        {"name": "Baya Colbur (Siniestro)", "price": 3, "img": _pokeapi_item_png("colbur-berry"), "desc": "Reduce dano de Siniestro supereficaz un 50% (1 vez)."},
        {"name": "Baya Babiri (Acero)", "price": 3, "img": _pokeapi_item_png("babiri-berry"), "desc": "Reduce dano de Acero supereficaz un 50% (1 vez)."},
        {"name": "Baya Chilan (Normal)", "price": 3, "img": _pokeapi_item_png("chilan-berry"), "desc": "Reduce dano de Normal (primer golpe) un 50% (1 vez)."},
    ]
    competitivos = [
        {"name": "Gafas Elegidas", "price": 8, "img": _pokeapi_item_png("choice-specs"), "desc": "At. Esp. +50% (x1.5); bloquea cambio de movimiento."},
        {"name": "Cinta Elegida", "price": 8, "img": _pokeapi_item_png("choice-band"), "desc": "Ataque +50% (x1.5); bloquea cambio de movimiento."},
        {"name": "Panuelo Elegido", "price": 8, "img": _pokeapi_item_png("choice-scarf"), "desc": "Velocidad +50% (x1.5); bloquea cambio de movimiento."},
        {"name": "Restos", "price": 8, "img": _pokeapi_item_png("leftovers"), "desc": "Restaura 1/16 de PS por turno (6.25%)."},
        {"name": "Banda Focus", "price": 7, "img": _pokeapi_item_png("focus-sash"), "desc": "Con PS completos, sobrevive a 1 golpe con 1 PS (1 uso)."},
        {"name": "Vidasfera", "price": 7, "img": _pokeapi_item_png("life-orb"), "desc": "Dano +30% (x1.3); pierde 10% PS max tras atacar."},
        {"name": "Hierba Blanca", "price": 5, "img": _pokeapi_item_png("white-herb"), "desc": "Restaura reducciones de estadisticas (1 uso)."},
        {"name": "Roca del Rey", "price": 5, "img": _pokeapi_item_png("kings-rock"), "desc": "10% de hacer retroceder al golpear."},
        {"name": "Periscopio", "price": 5, "img": _pokeapi_item_png("scope-lens"), "desc": "Ratio critico +1 etapa (6.25%/12.5%)."},
        {"name": "Lupa", "price": 5, "img": _pokeapi_item_png("zoom-lens"), "desc": "Precision +20% si el usuario actua despues que el rival."},
        {"name": "Toxisfera", "price": 5, "img": _pokeapi_item_png("toxic-orb"), "desc": "Envenena gravemente al portador al final del turno."},
        {"name": "Llamasfera", "price": 5, "img": _pokeapi_item_png("flame-orb"), "desc": "Quema al portador al final del turno."},
        {"name": "Objeto Potenciador de Tipo", "price": 4, "img": _pokeapi_item_png("silk-scarf"), "desc": "Potencia movimientos de un tipo (x1.2)."},
    ]
    crianza = [
        {"name": "Capsula Habilidad", "price": 8, "img": _pokeapi_item_png("ability-capsule"), "desc": "Cambia habilidad normal."},
        {"name": "Chapa Dorada", "price": 15, "img": _pokeapi_item_png("gold-bottle-cap"), "desc": "Maximiza IVs en todos los stats."},
        {"name": "Chapa Plateada", "price": 6, "img": _pokeapi_item_png("bottle-cap"), "desc": "Maximiza un IV concreto."},
        {"name": "Menta de Naturaleza", "price": 6, "img": _pokeapi_item_png("adamant-mint"), "desc": "Cambia naturaleza."},
        {"name": "Objeto Evolutivo", "price": 4, "img": _pokeapi_item_png("dawn-stone"), "desc": "Piedras y otros objetos de evolucion."},
    ]
    return {
        "comodines": comodines,
        "bayas": bayas,
        "competitivos": competitivos,
        "crianza": crianza,
    }
