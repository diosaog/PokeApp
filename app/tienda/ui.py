from __future__ import annotations

import streamlit as st

from app.common import COIN
from app.interfaz.theme import apply_platinum_ui
from app.juicios.penalties import get_user_penalties
from app.tienda.catalog import _render_shop_items, get_catalog
from app.tienda.money import _calc_money_for_user
from app.tienda.redeem import render_redeem_flow
from storage import add_purchase, clear_all_pokemon_flags, clear_pokemon_flags_for_owner, list_purchases, total_spent


def page_tienda() -> None:
    apply_platinum_ui("Tienda")
    st.markdown(
        "<style>"
        ".stButton>button, .stButton>button *{font-family:var(--font-pixel) !important; font-size:11px !important; "
        "font-weight:700 !important; color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; opacity:1 !important;}"
        ".stButton>button:disabled, .stButton>button:disabled *{opacity:1 !important; color:#cbd1d9 !important; -webkit-text-fill-color:#cbd1d9 !important;}"
        "button[data-baseweb='tab'], button[role='tab'], button[data-baseweb='tab'] *, button[role='tab'] *{font-family:var(--font-pixel) !important; font-size:10px !important; font-weight:700 !important;}"
        "</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='display:inline-block; background:linear-gradient(180deg,var(--accent) 0%, var(--accent-dark) 100%);"
        " border:1px solid var(--bw2-edge-strong); border-radius:0; padding:9px 12px; color:#ffffff;"
        " font-family:var(--font-pixel); font-weight:700; font-size:12px; text-transform:uppercase;"
        " clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);'>Poke Mart</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:2px; background:linear-gradient(90deg, transparent 0%, var(--accent) 22%, var(--accent) 78%, transparent 100%); margin:10px 0 14px;'></div>", unsafe_allow_html=True)

    current_user = st.session_state.get("user") or "-"
    penalties = get_user_penalties(current_user if current_user != "-" else "")
    store_locked = bool(penalties.get("store_blocked"))
    avail = None
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
            extra_reduction = int(penalties.get("coins_reduction") or 0)
            avail = max(int(base) - int(spent) - extra_reduction, 0)
            if store_locked:
                avail = 0
            st.markdown(
                "<div style='background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%); border:1px solid var(--bw2-edge); border-radius:0; "
                "padding:10px 12px; color:var(--bw2-text); font-family:var(--font-ui); box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);'>"
                "<div style='font-size:10px; color:#fff; font-family:var(--font-pixel); font-weight:700; letter-spacing:0.05em; text-transform:uppercase;'>Disponible</div>"
                f"<div style='font-size:28px; margin-top:8px; color:#ffffff;'>{COIN} {avail}</div>"
                f"<div style='font-size:18px; color:var(--bw2-text-soft); margin-top:8px; line-height:1.35;'>Base: {COIN} {base} | Gastado: {COIN} {spent} | Castigo: {COIN} {extra_reduction}</div>"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%); border:1px solid var(--bw2-edge); border-radius:0; "
                "padding:10px 12px; color:var(--bw2-text); font-family:var(--font-ui);'>"
                "<div style='font-size:10px; color:#fff; font-family:var(--font-pixel); font-weight:700; text-transform:uppercase;'>Disponible</div>"
                f"<div style='font-size:28px; margin-top:8px; color:#ffffff;'>{COIN} 0</div>"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        "<div style='display:inline-block; background:linear-gradient(180deg,var(--bw2-panel-3) 0%, var(--bw2-panel) 100%); border:1px solid var(--bw2-edge); border-radius:0; "
        "padding:8px 10px; font-size:10px; color:#ffffff; font-family:var(--font-pixel); "
        "font-weight:700; text-transform:uppercase;'>Catalogo</div>",
        unsafe_allow_html=True,
    )
    if store_locked:
        st.error("Tienda bloqueada por castigo de Juicio. No puedes gastar monedas.")
        tramos = list(penalties.get("store_ban_tramos") or [])
        if tramos:
            st.caption("Tramo de bloqueo: " + ", ".join(tramos))
        src = penalties.get("sources") or []
        if src:
            st.caption("Origen: " + " | ".join(src))
    st.markdown("<div style='height:2px; background:linear-gradient(90deg, transparent 0%, var(--accent) 22%, var(--accent) 78%, transparent 100%); margin:10px 0 14px;'></div>", unsafe_allow_html=True)
    catalog = get_catalog()
    tab_com, tab_bay, tab_comp, tab_bred = st.tabs(["Comodines", "Bayas", "Competitivos", "Crianza"])
    with tab_com:
        _render_shop_items(catalog["comodines"], "comodines", available=avail if current_user != "-" else None)
    with tab_bay:
        _render_shop_items(catalog["bayas"], "bayas", available=avail if current_user != "-" else None)
    with tab_comp:
        _render_shop_items(catalog["competitivos"], "competitivos", available=avail if current_user != "-" else None)
    with tab_bred:
        _render_shop_items(catalog["crianza"], "crianza", available=avail if current_user != "-" else None)

    pending = st.session_state.get("shop_pending")
    if pending and store_locked:
        st.session_state.pop("shop_pending", None)
        st.warning("No se puede completar la compra: la tienda esta bloqueada por castigo.")
    elif pending:
        nombre = pending.get("name")
        precio = int(pending.get("price") or 0)
        try:
            st.markdown(
                f"<div class='panel-dashed'><strong>Confirmacion</strong><br/>Comprar '<em>{nombre}</em>' por {COIN} {precio}?</div>",
                unsafe_allow_html=True,
            )
        except Exception:
            pass
        st.info(f"Comprar '{nombre}' por {COIN} {precio}?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirmar compra", use_container_width=True):
                try:
                    pid = add_purchase(current_user, nombre, precio)
                    st.session_state.pop("_money_cache", None)
                    st.session_state.pop("_money_cache_entrenadores", None)
                    try:
                        import streamlit as _st
                        _st.cache_data.clear()
                    except Exception:
                        pass
                    st.session_state.pop("shop_pending", None)
                    st.session_state.pop("shop_error", None)
                    st.success(f"Compra registrada (#{pid}).")
                    st.rerun()
                except Exception as e:
                    st.session_state["shop_error"] = str(e)
                    st.error(f"No se pudo registrar la compra: {e}")
        with c2:
            if st.button("Cancelar", use_container_width=True):
                st.session_state.pop("shop_pending", None)
        if st.session_state.get("shop_error"):
            st.error(st.session_state["shop_error"])

    st.markdown("---")
    with st.expander("Historial de compras (global)"):
        compras = list_purchases(limit=50)
        if compras:
            rows = []
            from datetime import datetime as _dt
            for row in compras:
                if len(row) == 5:
                    pid, user, item, price, ts = row
                    status, red_at = None, None
                else:
                    pid, user, item, price, ts, status, red_at = row
                origen = "Premio" if int(price) == 0 else "Compra"
                rows.append({
                    "#": pid,
                    "Jugador": user,
                    "Objeto": item,
                    "Precio": f"{COIN} {price}",
                    "Origen": origen,
                    "Fecha": _dt.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                    "Estado": (status or "pendiente").capitalize(),
                })
            st.dataframe(rows, use_container_width=True)
        else:
            st.caption("Sin compras registradas.")

    ctx = st.session_state.get("redeem_ctx")
    if ctx:
        render_redeem_flow(ctx, current_user)

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
