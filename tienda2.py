# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import unicodedata
import time
from typing import List
from pathlib import Path

import streamlit as st

from utils import USERS, list_user_saves
from storage import (
    add_purchase, total_spent, list_purchases, set_purchase_status, add_redemption, upsert_pokemon_flags,
    get_flags_by_fingerprints, clear_all_pokemon_flags, clear_pokemon_flags_for_owner,
)
from conex_pkhex import PKHeXRuntime, get_bridge_path, extract_team, extract_box
from interfaz import coins_from_badges

# Smbolo de moneda (consistente en toda la app)
COIN = "\U0001FA99"
COINS_BY_POSITION = {1: 12, 2: 11, 3: 9, 4: 8, 5: 9, 6: 6, 7: 5, 8: 4, 9: 2}


def _coins_from_league(user: str) -> int:
    lr = st.session_state.get("league_results", {})
    user_map = lr.get(user, {})
    return sum(COINS_BY_POSITION.get(pos, 0) for pos in user_map.values())


@st.cache_data(ttl=60, show_spinner=False)
def _calc_money_for_user(user: str) -> int:
    liga = _coins_from_league(user)
    badge_coins = 0
    try:
        if get_bridge_path():
            saves = list_user_saves(user)
            if saves:
                sav_json = PKHeXRuntime.open_sav(str(saves[0]))
                badge_coins = coins_from_badges(sav_json)
    except Exception:
        badge_coins = 0
    return int(liga + badge_coins)


def _money_available(user: str | None) -> int:
    if not user:
        return 0
    try:
        base = _calc_money_for_user(user)
    except Exception:
        base = 0
    try:
        spent = total_spent(user)
    except Exception:
        spent = 0
    return max(int(base) - int(spent), 0)


def _pokeapi_item_png(slug: str) -> str:
    return f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/items/{slug}.png"

# Assets locales para iconos de la tienda
SHOP_DIR = Path("assets") / "shop"

def _shop_asset(slug: str) -> str | None:
    try:
        if not SHOP_DIR.exists():
            return None
        s = (slug or "").strip()
        if not s:
            return None
        candidates = [s, s.replace(" ", "-"), s.replace(" ", "_")]
        for base in candidates:
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                p = SHOP_DIR / f"{base}{ext}"
                if p.exists():
                    return str(p)
    except Exception:
        return None
    return None

# ---- Texto: reparacin de acentos/mojibake para mostrar en UI ----
def _fix_text(s: str) -> str:
    if not s:
        return ""
    t = str(s)
    try:
        alt = t.encode("latin1", errors="ignore").decode("utf-8", errors="ignore")
        if alt:
            t = alt
    except Exception:
        pass
    replacements = {
        "Pok\\u00e9mon": "Pok\u00e9mon",
        "Pok\\\\u00e9mon": "Pok\u00e9mon",
        "Pokémon": "Pok\u00e9mon",
        "Catologo": "Cat\u00e1logo",
        "Catalogo": "Cat\u00e1logo",
        # nf y tildes
        "diseno": "dise\u00f1o",
        "dise\\u00f1o": "dise\u00f1o",
        "descripcion": "descripci\u00f3n",
        "Restauracion": "Restauraci\u00f3n",
        "Curacion": "Curaci\u00f3n",
        "congelacion": "congelaci\u00f3n",
        "confusion": "confusi\u00f3n",
        # Otros frecuentes
        "Fosil": "F\u00f3sil",
        "Electrico": "El\u00e9ctrico",
        "critico": "cr\u00edtico"
    }

    
    for a,b in replacements.items():
        t = t.replace(a,b)
    # Correccion de UTF-8 mal decodificado (ñ, á, etc.)
    for bad, good in {
        "\u00C3\u00B1": "\u00F1",
        "\u00C3\u00A1": "\u00E1",
        "\u00C3\u00A9": "\u00E9",
        "\u00C3\u00AD": "\u00ED",
        "\u00C3\u00B3": "\u00F3",
        "\u00C3\u00BA": "\u00FA",
        "\u00C3\u0081": "\u00C1",
        "\u00C3\u0089": "\u00C9",
        "\u00C3\u008D": "\u00CD",
        "\u00C3\u0093": "\u00D3",
        "\u00C3\u009A": "\u00DA",
    }.items():
        t = t.replace(bad, good)
    return t

# ---- Render tarjeta de item ----
def _render_item_card(item: dict, idx_key: str) -> None:
    name = item.get("name")
    price = int(item.get("price", 0))
    desc = item.get("desc") or ""
    icon = item.get("icon") or ""
    img = item.get("img")

    name = _fix_text(name)
    desc = _fix_text(desc)

    # Fallback de imagen para comodines si no viene en datos (prefiere asset local)
    if not img and name:
        try:
            n = _norm(name)
            if "revivir" in n:
                img = _shop_asset("revivir") or _pokeapi_item_png("max-revive")
            elif "robar" in n:
                img = _shop_asset("robar") or _pokeapi_item_png("dread-plate")
            elif "recaptura" in n:
                img = _shop_asset("recaptura") or _pokeapi_item_png("repeat-ball")
            elif "captura extra" in n:
                img = _shop_asset("captura-extra") or _pokeapi_item_png("ultra-ball")
            elif "blindar" in n:
                img = _shop_asset("blindar") or _pokeapi_item_png("metal-coat")
            elif ("fosil" in n) or ("fsil" in n):
                img = _shop_asset("fosil") or _pokeapi_item_png("helix-fossil")
        except Exception:
            img = None

    user = st.session_state.get("user") or "-"
    available = _money_available(user)
    afford = available >= price
    with st.container(border=True):
        cols = st.columns([1, 2])
        with cols[0]:
            if img:
                st.image(img, width=48)
            else:
                st.markdown(icon)
        with cols[1]:
            st.markdown(f"**{name}**")
            if desc:
                st.caption(desc)
            if st.button("Comprar", key=f"buy_{idx_key}", disabled=(not afford) or price <= 0, use_container_width=True):
                st.session_state["shop_pending"] = {"name": name, "price": int(price)}
            st.caption(f"{COIN} {price}")
            if not afford and price > 0:
                st.caption(f"Faltan {COIN} {price - available}")

def _render_shop_items(items: list[dict], category_key: str) -> None:
    # Asegurar imágenes para categorías por nombre (soporta textos con acentos o mojibake)
    if category_key == "comodines":
        try:
            for it in items:
                n = _norm(it.get("name") or "")
                # Fsil: cubrir nombres mal codificados (p.ej. "Fsil")
                if (("fosil" in n) or (n.startswith("f") and "sil" in n) or ("fossil" in n)) and ("img" not in it):
                    it["img"] = _shop_asset("fosil") or _pokeapi_item_png("helix-fossil")
                elif ("captura" in n and "extra" in n) and ("img" not in it):
                    it["img"] = _shop_asset("captura-extra") or _pokeapi_item_png("ultra-ball")
                elif ("robar" in n) and ("img" not in it):
                    it["img"] = _shop_asset("robar") or _pokeapi_item_png("dread-plate")
                elif ("revivir" in n) and ("img" not in it):
                    it["img"] = _shop_asset("revivir") or _pokeapi_item_png("max-revive")
                elif ("blindar" in n) and ("img" not in it):
                    it["img"] = _shop_asset("blindar") or _pokeapi_item_png("metal-coat")
                elif ("recaptura" in n) and ("img" not in it):
                    it["img"] = _shop_asset("recaptura") or _pokeapi_item_png("repeat-ball")
        except Exception:
            pass
    elif category_key == "crianza":
        # Forzar imagen de Menta (usa Menta Firme por defecto)
        try:
            for it in items:
                n = _norm(it.get("name") or "")
                if ("menta" in n) and (not it.get("img")):
                    it["img"] = _shop_asset("adamant-mint") or _pokeapi_item_png("adamant-mint")
        except Exception:
            pass
    cols = st.columns(3)
    for idx, it in enumerate(items):
        col = cols[idx % 3]
        with col:
            _render_item_card(it, f"{category_key}_{idx}")
    st.write("")


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    return s


def _eq_item(a: str, b: str) -> bool:
    return _norm(a) == _norm(b)


def _is_usable_item(name: str) -> bool:
    targets = ("Revivir Pokemon", "Robar Pokemon", "Blindar Pokemon", "Comodin de Blindaje por Robo")
    return any(_eq_item(name, t) for t in targets)


def page_tienda() -> None:
    st.header("Poke Mart")

    st.markdown("<div style=\"height:8px; background: repeating-linear-gradient(45deg, #2a75bb 0 12px, #3b88cc 12px 24px); border-radius: 6px; margin:-6px 0 10px\"></div>", unsafe_allow_html=True)
    current_user = st.session_state.get("user") or "-"
    _, colR = st.columns([5, 2])
    with colR:
        if current_user != "-":
            try:
                base = _calc_money_for_user(current_user)
            except Exception:
                base = 0
            try:
                spent = total_spent(current_user)
            except Exception:
                spent = 0
            avail = max(int(base) - int(spent), 0)
            st.metric("Disponible", f"{COIN} {avail}")
            st.caption(f"Base: {COIN} {base} | Gastado: {COIN} {spent}")
        else:
            st.metric("Disponible", f"{COIN} 0")

    st.subheader("Catalogo")
    # Comodines (por diseño, sin porcentajes en la descripción)
    comodines = [
        {"name": "Revivir Pokemon", "price": 10, "icon": ""},
        {"name": "Robar Pokemon",   "price": 10, "icon": ""},
        {"name": "Recaptura",       "price": 8,  "icon": ""},
        {"name": "Captura Extra",   "price": 5,  "icon": ""},
        {"name": "Blindar Pokemon", "price": 10, "icon": ""},
        {"name": "Fosil",           "price": 5,  "icon": ""},
    ]
    # Bayas (Gen 14)
    bayas = [
        # Restauración de PS
        {"name": "Baya Aranja", "price": 1, "img": _pokeapi_item_png("oran-berry"),   "desc": "Restaura 10 PS al 50% PS."},
        {"name": "Baya Zidra",  "price": 2, "img": _pokeapi_item_png("sitrus-berry"), "desc": "Restaura 25% de PS máximos."},
        # Curación de estados
        {"name": "Baya Zreza",  "price": 1, "img": _pokeapi_item_png("cheri-berry"),  "desc": "Cura parálisis."},
        {"name": "Baya Ziuela", "price": 1, "img": _pokeapi_item_png("chesto-berry"), "desc": "Cura sueño."},
        {"name": "Baya Meloc",  "price": 1, "img": _pokeapi_item_png("pecha-berry"),  "desc": "Cura envenenamiento."},
        {"name": "Baya Safre",  "price": 1, "img": _pokeapi_item_png("rawst-berry"),  "desc": "Cura quemaduras."},
        {"name": "Baya Perasi", "price": 1, "img": _pokeapi_item_png("aspear-berry"), "desc": "Cura congelación."},
        {"name": "Baya Atania", "price": 1, "img": _pokeapi_item_png("persim-berry"), "desc": "Cura confusión."},
        # Pinch berries (boost al 25% PS)
        {"name": "Baya Aslac",  "price": 2, "img": _pokeapi_item_png("salac-berry"),  "desc": "Velocidad +1 etapa (+50%) al 25% PS."},
        {"name": "Baya Lichi",  "price": 2, "img": _pokeapi_item_png("liechi-berry"), "desc": "Ataque +1 etapa (+50%) al 25% PS."},
        {"name": "Baya Petaya", "price": 2, "img": _pokeapi_item_png("petaya-berry"), "desc": "At. Esp. +1 etapa (+50%) al 25% PS."},
        {"name": "Baya Ganlon", "price": 1, "img": _pokeapi_item_png("ganlon-berry"), "desc": "Defensa +1 etapa al 25% PS."},
        {"name": "Baya Apicot", "price": 1, "img": _pokeapi_item_png("apicot-berry"), "desc": "Def. Esp. +1 etapa al 25% PS."},
        {"name": "Baya Lansat", "price": 1, "img": _pokeapi_item_png("lansat-berry"), "desc": "Ratio crítico +2 etapas al 25% PS."},
        {"name": "Baya Starf",  "price": 1, "img": _pokeapi_item_png("starf-berry"),  "desc": "Sube mucho una stat al azar (1 uso)."},
        # Resist berries (50% 1 golpe supereficaz)
        {"name": "Baya Occa (Fuego)",      "price": 2, "img": _pokeapi_item_png("occa-berry"),   "desc": "Reduce dano de Fuego supereficaz un 50% (1 vez)."},
        {"name": "Baya Passho (Agua)",     "price": 2, "img": _pokeapi_item_png("passho-berry"), "desc": "Reduce dano de Agua supereficaz un 50% (1 vez)."},
        {"name": "Baya Wacan (Electrico)", "price": 2, "img": _pokeapi_item_png("wacan-berry"),  "desc": "Reduce dano de Electrico supereficaz un 50% (1 vez)."},
        {"name": "Baya Rindo (Planta)",    "price": 2, "img": _pokeapi_item_png("rindo-berry"),  "desc": "Reduce dano de Planta supereficaz un 50% (1 vez)."},
        {"name": "Baya Yache (Hielo)",     "price": 2, "img": _pokeapi_item_png("yache-berry"),  "desc": "Reduce dano de Hielo supereficaz un 50% (1 vez)."},
        {"name": "Baya Chople (Lucha)",    "price": 2, "img": _pokeapi_item_png("chople-berry"), "desc": "Reduce dano de Lucha supereficaz un 50% (1 vez)."},
        {"name": "Baya Kebia (Veneno)",    "price": 1, "img": _pokeapi_item_png("kebia-berry"),  "desc": "Reduce dano de Veneno supereficaz un 50% (1 vez)."},
        {"name": "Baya Shuca (Tierra)",    "price": 2, "img": _pokeapi_item_png("shuca-berry"),  "desc": "Reduce dano de Tierra supereficaz un 50% (1 vez)."},
        {"name": "Baya Coba (Volador)",    "price": 1, "img": _pokeapi_item_png("coba-berry"),   "desc": "Reduce dano de Volador supereficaz un 50% (1 vez)."},
        {"name": "Baya Payapa (Psiquico)", "price": 1, "img": _pokeapi_item_png("payapa-berry"), "desc": "Reduce dano de Psiquico supereficaz un 50% (1 vez)."},
        {"name": "Baya Tanga (Bicho)",     "price": 1, "img": _pokeapi_item_png("tanga-berry"),  "desc": "Reduce dano de Bicho supereficaz un 50% (1 vez)."},
        {"name": "Baya Charti (Roca)",     "price": 2, "img": _pokeapi_item_png("charti-berry"), "desc": "Reduce dano de Roca supereficaz un 50% (1 vez)."},
        {"name": "Baya Kasib (Fantasma)",  "price": 1, "img": _pokeapi_item_png("kasib-berry"),  "desc": "Reduce dano de Fantasma supereficaz un 50% (1 vez)."},
        {"name": "Baya Haban (Dragon)",    "price": 2, "img": _pokeapi_item_png("haban-berry"),  "desc": "Reduce dano de Dragon supereficaz un 50% (1 vez)."},
        {"name": "Baya Colbur (Siniestro)","price": 1, "img": _pokeapi_item_png("colbur-berry"), "desc": "Reduce dano de Siniestro supereficaz un 50% (1 vez)."},
        {"name": "Baya Babiri (Acero)",    "price": 2, "img": _pokeapi_item_png("babiri-berry"), "desc": "Reduce dano de Acero supereficaz un 50% (1 vez)."},
        {"name": "Baya Chilan (Normal)",   "price": 1, "img": _pokeapi_item_png("chilan-berry"), "desc": "Reduce dano de Normal (primer golpe) un 50% (1 vez)."},
    ]
    # Objetos competitivos con porcentajes exactos
    competitivos = [
        {"name": "Gafas Elegidas",  "price": 5, "img": _pokeapi_item_png("choice-specs"), "desc": "At. Esp. +50% (x1.5); bloquea cambio de movimiento."},
        {"name": "Cinta Elegida",   "price": 5, "img": _pokeapi_item_png("choice-band"),  "desc": "Ataque +50% (x1.5); bloquea cambio de movimiento."},
        {"name": "Panuelo Elegido", "price": 5, "img": _pokeapi_item_png("choice-scarf"), "desc": "Velocidad +50% (x1.5); bloquea cambio de movimiento."},
        {"name": "Periscopio",      "price": 3, "img": _pokeapi_item_png("scope-lens"),   "desc": "Ratio critico +1 etapa (6.25%/12.5%)."},
        {"name": "Restos",          "price": 5, "img": _pokeapi_item_png("leftovers"),    "desc": "Restaura 1/16 de PS por turno (6.25%)."},
        {"name": "Roca del Rey",    "price": 3, "img": _pokeapi_item_png("kings-rock"),   "desc": "10% de hacer retroceder al golpear."},
        {"name": "Hierba Blanca",   "price": 4, "img": _pokeapi_item_png("white-herb"),   "desc": "Restaura reducciones de estadisticas (1 uso)."},
        {"name": "Vidasfera",       "price": 5, "img": _pokeapi_item_png("life-orb"),     "desc": "Dano +30% (x1.3); pierde 10% PS max tras atacar."},
        {"name": "Banda Focus",     "price": 5, "img": _pokeapi_item_png("focus-sash"),   "desc": "Con PS completos, sobrevive a 1 golpe con 1 PS (1 uso)."},
    ]
    crianza = [
        {"name": "Cápsula Habilidad", "price": 5,  "img": _pokeapi_item_png("ability-capsule"),  "desc": "Cambia habilidad normal."},
        {"name": "Chapa Dorada",     "price": 12, "img": _pokeapi_item_png("gold-bottle-cap"),  "desc": "Maximiza IVs en todos los stats."},
        {"name": "Chapa Plateada",   "price": 4,  "img": _pokeapi_item_png("bottle-cap"),       "desc": "Maximiza un IV concreto."},
        {"name": "Menta de Naturaleza", "price": 4, "img": _pokeapi_item_png("adamant-mint"),  "desc": "Cambia naturaleza."},
        {"name": "Objeto Evolutivo", "price": 3,  "img": _pokeapi_item_png("dawn-stone"),      "desc": "Piedras y otros objetos de evolución."},
    ]

    tab_com, tab_bay, tab_comp, tab_bred = st.tabs(["Comodines", "Bayas", "Competitivos", "Crianza"])
    with tab_com:
        _render_shop_items(comodines, "comodines")
    with tab_bay:
        _render_shop_items(bayas, "bayas")
    with tab_comp:
        _render_shop_items(competitivos, "competitivos")
    with tab_bred:
        _render_shop_items(crianza, "crianza")

    # Confirmacion de compra
    pending = st.session_state.get("shop_pending")
    if pending:
        nombre = pending.get("name")
        precio = int(pending.get("price") or 0)
        try:
            st.markdown(f"<div class='panel-dashed'><strong>Confirmacion</strong><br/>Comprar '<em>{nombre}</em>' por {COIN} {precio}?</div>", unsafe_allow_html=True)
        except Exception:
            pass
        st.info(f"Comprar '{nombre}' por {COIN} {precio}?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirmar compra", use_container_width=True):
                pid = add_purchase(current_user, nombre, precio)
                st.session_state.pop("shop_pending", None)
                try:
                    st.markdown("<audio autoplay style='display:none'><source src='data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAESsAACJWAAACABAAZGF0YQAAAAAA//8AAP//AAAA//8A' type='audio/wav'></audio>", unsafe_allow_html=True)
                except Exception:
                    pass
                st.success(f"Compra registrada (#{pid}).")
                try:
                    st.markdown("<div class='confetti-lite'>  </div>", unsafe_allow_html=True)
                except Exception:
                    pass
        with c2:
            if st.button("Cancelar", use_container_width=True):
                st.session_state.pop("shop_pending", None)

    st.markdown("---")
    with st.expander("Historial de compras (global)"):
        compras = list_purchases(limit=50)
        if compras:
            rows = []
            from datetime import datetime as _dt
            for row in compras:
                # soporte para antiguas filas sin status
                if len(row) == 5:
                    pid, user, item, price, ts = row
                    status, red_at = None, None
                else:
                    pid, user, item, price, ts, status, red_at = row
                origen = " Premio" if int(price) == 0 else "Compra"
                rows.append({
                    "#": pid,
                    "Jugador": user,
                    "Objeto": item,
                    "Precio": f"{COIN} {price}",
                    "Origen": origen,
                    "Fecha": _dt.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                    "Estado": (status or 'pendiente').capitalize(),
                })
            st.dataframe(rows, use_container_width=True)
        else:
            st.caption("Sin compras registradas todavia.")

    # Flujo de uso de comodines (mostrado desde Entrenadores o tras compra)
    ctx = st.session_state.get('redeem_ctx')
    if ctx:
        _render_redeem_flow(ctx, current_user)

    st.markdown("---")
    with st.expander("Reiniciar flags de Pokemon (Blindado/Robado)"):
        st.caption("Esto borra estados guardados en la base de datos; no modifica archivos .sav.")
        colA, colB = st.columns(2)
        with colA:
            if current_user != "-" and st.button("Resetear MIS flags", key="reset_my_flags"):
                try:
                    clear_pokemon_flags_for_owner(current_user)
                    st.success("Flags de tus Pokemon reiniciados.")
                except Exception as e:
                    st.error(f"No se pudieron reiniciar tus flags: {e}")
        with colB:
            confirm = st.text_input("Escribe RESET para borrar TODOS", key="reset_all_confirm")
            if st.button("Resetear TODOS los flags", disabled=(confirm != "RESET"), key="reset_all_flags"):
                try:
                    clear_all_pokemon_flags()
                    st.success("Todos los flags reiniciados.")
                except Exception as e:
                    st.error(f"No se pudieron reiniciar los flags: {e}")


def _render_redeem_flow(ctx: dict, current_user: str) -> None:
    item = ctx.get('item')
    pid = ctx.get('pid')
    _ = int(ctx.get('step') or 1)
    st.markdown("---")
    st.subheader(f"Usar: {item} (#{pid})")

    # === ROBAR ===
    if _eq_item(item, "Robar Pokemon"):
        players = [u for u in USERS.keys() if u != current_user]
        target = st.selectbox("Jugador objetivo", players, key="rob_target")
        origin_kind = st.selectbox("Origen", ["Equipo"] + [f"Caja {i+1}" for i in range(18) if i != 17], key="rob_origin")
        mons: List[dict] = []
        try:
            saves = list_user_saves(target)
            if saves:
                spath = str(saves[0])
                sav_json = PKHeXRuntime.open_sav(spath)
                if origin_kind == "Equipo":
                    mons = extract_team(sav_json, save_path=spath)
                else:
                    idx = int(origin_kind.split()[-1]) - 1
                    mons = extract_box(sav_json, idx, save_path=spath)
            else:
                st.warning("El jugador no tiene save disponible.")
        except Exception as e:
            st.error(f"No se pudo leer el save del objetivo: {e}")

        options = []
        for i, m in enumerate(mons):
            from pkmmeta import pokemon_fingerprint
            fp = pokemon_fingerprint(m)
            slot = m.get('slot_index', i)
            label = f"{i+1}. {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}"
            options.append((label, int(slot), fp))

        label_to_idx = {lbl: (idx, fp) for (lbl, idx, fp) in options}
        choice_lbl = st.selectbox("Pokemon", [lbl for (lbl, _, _) in options]) if options else None

        if choice_lbl:
            idx, fp = label_to_idx[choice_lbl]
            # Validaciones: blindado
            flags = get_flags_by_fingerprints([fp]).get(fp)
            if flags:
                try:
                    fj = json.loads(flags.get('flags_json') or '{}')
                except Exception:
                    fj = {}
                if fj.get('blindado'):
                    st.error("Este Pokemon esta blindado. No se puede robar.")
                    return
            if st.button("Confirmar robo"):
                try:
                    # Registrar el robo sin modificar archivos .sav
                    add_redemption(int(pid), current_user, item, json.dumps({"type": "steal", "from": target, "origin": origin_kind, "choice_index": idx, "fingerprint": fp}, ensure_ascii=False))
                    set_purchase_status(int(pid), 'used')
                    add_purchase(current_user, "Comodin de Blindaje por Robo", 0)
                    # Flags: marcar como robado
                    try:
                        cur = get_flags_by_fingerprints([fp]).get(fp)
                        base = {}
                        if cur and isinstance(cur.get('flags_json'), str) and cur['flags_json'].strip():
                            base = json.loads(cur['flags_json'])
                            if not isinstance(base, dict):
                                base = {}
                        base['robado'] = True
                        base['robado_from'] = target
                        base['robado_at'] = int(time.time())
                        upsert_pokemon_flags(current_user, fp, json.dumps(base, ensure_ascii=False))
                    except Exception:
                        pass
                    st.success("Robo registrado (sin modificar el save).")
                    st.session_state.pop('redeem_ctx', None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error registrando el robo: {e}")
        return

    # === BLINDAR ===
    if _eq_item(item, "Blindar Pokemon"):
        origin_kind = st.selectbox("Origen", ["Equipo"] + [f"Caja {i+1}" for i in range(18)], key="shield_origin")
        mons: List[dict] = []
        try:
            saves = list_user_saves(current_user)
            if saves:
                spath = str(saves[0])
                sav_json = PKHeXRuntime.open_sav(spath)
                if origin_kind == "Equipo":
                    mons = extract_team(sav_json, save_path=spath)
                else:
                    idx = int(origin_kind.split()[-1]) - 1
                    mons = extract_box(sav_json, idx, save_path=spath)
            else:
                st.warning("No tienes save disponible.")
        except Exception as e:
            st.error(f"No se pudo leer tu save: {e}")
        options = []
        from pkmmeta import pokemon_fingerprint
        for i, m in enumerate(mons):
            fp = pokemon_fingerprint(m)
            slot = m.get('slot_index', i)
            options.append((f"{i+1}. {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}", int(slot), fp))
        label_to_idx = {lbl: (idx, fp) for (lbl, idx, fp) in options}
        choice_lbl = st.selectbox("Pokemon", [lbl for (lbl, _, _) in options]) if options else None
        if choice_lbl:
            _, fp = label_to_idx[choice_lbl]
            # Evitar doble blindaje
            _cur = get_flags_by_fingerprints([fp]).get(fp)
            _already = False
            if _cur:
                try:
                    _fj = json.loads(_cur.get("flags_json") or "{}")
                except Exception:
                    _fj = {}
                _already = bool(_fj.get("blindado"))
            if _already:
                st.error("Este Pokemon ya esta blindado.")
                return
            if st.button("Confirmar blindaje"):
                try:
                    add_redemption(int(pid), current_user, item, json.dumps({"type": "shield", "fingerprint": fp}, ensure_ascii=False))
                    set_purchase_status(int(pid), 'used')
                    try:
                        base = {}
                        if _cur and isinstance(_cur.get("flags_json"), str) and _cur["flags_json"].strip():
                            base = json.loads(_cur["flags_json"]) if isinstance(json.loads(_cur["flags_json"]), dict) else {}
                        base["blindado"] = True
                        upsert_pokemon_flags(current_user, fp, json.dumps(base, ensure_ascii=False))
                    except Exception:
                        pass
                    st.success("Blindaje aplicado."); st.toast("Pokemon blindado", icon="")
                    st.session_state.pop('redeem_ctx', None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error aplicando blindaje: {e}")
        return

    # === COMODIN DE BLINDAJE POR ROBO ===
    if _eq_item(item, "Comodin de Blindaje por Robo"):
        origin_kind = st.selectbox("Origen", ["Equipo"] + [f"Caja {i+1}" for i in range(18)], key="shieldrob_origin")
        mons: List[dict] = []
        try:
            saves = list_user_saves(current_user)
            if saves:
                spath = str(saves[0])
                sav_json = PKHeXRuntime.open_sav(spath)
                if origin_kind == "Equipo":
                    mons = extract_team(sav_json, save_path=spath)
                else:
                    idx = int(origin_kind.split()[-1]) - 1
                    mons = extract_box(sav_json, idx, save_path=spath)
            else:
                st.warning("No tienes save disponible.")
        except Exception as e:
            st.error(f"No se pudo leer tu save: {e}")
        options = []
        from pkmmeta import pokemon_fingerprint
        for i, m in enumerate(mons):
            fp = pokemon_fingerprint(m)
            slot = m.get('slot_index', i)
            options.append((f"{i+1}. {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}", int(slot), fp))
        label_to_idx = {lbl: (idx, fp) for (lbl, idx, fp) in options}
        choice_lbl = st.selectbox("Pokemon", [lbl for (lbl, _, _) in options]) if options else None
        if choice_lbl:
            _, fp = label_to_idx[choice_lbl]
            # Evitar doble blindaje
            _cur = get_flags_by_fingerprints([fp]).get(fp)
            _already = False
            if _cur:
                try:
                    _fj = json.loads(_cur.get('flags_json') or '{}')
                except Exception:
                    _fj = {}
                _already = bool(_fj.get('blindado'))
            if _already:
                st.error("Este Pokemon ya esta blindado.")
                return
            if st.button("Confirmar blindaje"):
                try:
                    add_redemption(int(pid), current_user, item, json.dumps({"type": "shield", "fingerprint": fp}, ensure_ascii=False))
                    set_purchase_status(int(pid), 'used')
                    base = {}
                    if _cur and isinstance(_cur.get('flags_json'), str) and _cur['flags_json'].strip():
                        try:
                            base = json.loads(_cur['flags_json'])
                            if not isinstance(base, dict):
                                base = {}
                        except Exception:
                            base = {}
                    base['blindado'] = True
                    base['blindaje_por_robo'] = True
                    upsert_pokemon_flags(current_user, fp, json.dumps(base, ensure_ascii=False))
                    st.success("Blindaje por robo aplicado.")
                    st.session_state.pop('redeem_ctx', None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error aplicando blindaje: {e}")
        return

    # === REVIVIR ===
    if _eq_item(item, "Revivir Pokemon"):
        mons: List[dict] = []
        try:
            saves = list_user_saves(current_user)
            if saves:
                spath = str(saves[0])
                sav_json = PKHeXRuntime.open_sav(spath)
                mons = extract_box(sav_json, 17, save_path=spath)  # Caja 18
            else:
                st.warning("No tienes save disponible.")
        except Exception as e:
            st.error(f"No se pudo leer tu save: {e}")
        options = []
        from pkmmeta import pokemon_fingerprint
        for i, m in enumerate(mons):
            fp = pokemon_fingerprint(m)
            options.append((f"{i+1}. {m.get('species_name') or m.get('species')} Lv.{m.get('level','-')}", i, fp))
        label_to_idx = {lbl: (idx, fp) for (lbl, idx, fp) in options}
        choice_lbl = st.selectbox("Pokemon a revivir (Caja 18)", [lbl for (lbl, _, _) in options]) if options else None
        if choice_lbl:
            slot, fp = label_to_idx[choice_lbl]
            if st.button("Confirmar revivir"):
                try:
                    # Registrar revivir sin modificar archivos .sav
                    add_redemption(int(pid), current_user, item, json.dumps({"type": "revive", "fingerprint": fp}, ensure_ascii=False))
                    set_purchase_status(int(pid), 'used')
                    st.success("Revivir registrado (sin modificar el save).")
                    st.session_state.pop('redeem_ctx', None)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error registrando revivir: {e}")
        return







