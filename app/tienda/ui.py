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
        ".stButton>button{background:#f1c258 !important; color:#2b2b2b !important; border:2px solid #c28f27 !important; "
        "border-radius:6px !important; font-family:\"Press Start 2P\", monospace !important; font-size:13px !important; "
        "font-weight:900 !important; text-shadow:0 0 1px rgba(0,0,0,0.35); letter-spacing:0.2px;}"
        ".stButton>button:disabled{opacity:0.92 !important; color:#5c4314 !important; border-color:#c28f27 !important; font-weight:900 !important;}"
        "div[data-baseweb='tab-list']{background:#d7d4c0; border:2px solid #9a9680; border-radius:6px; padding:4px; gap:4px;}"
        "button[data-baseweb='tab']{background:#f7f6ef; color:#2b2b2b; border:2px solid #9a9680; border-radius:4px; "
        "font-family:\"Press Start 2P\", monospace; font-size:12px; font-weight:900; padding:7px 10px; text-shadow:0 0 1px rgba(0,0,0,0.28);}"
        "button[data-baseweb='tab'][aria-selected='true']{background:#f1c258; border-color:#c28f27; font-weight:900; color:#2b2b2b;}"
        "</style>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='background:#f1c258; border:2px solid #c28f27; border-radius:6px; "
        "padding:8px 10px; display:inline-block; font-family:\"Press Start 2P\", monospace; "
        "font-weight:900; color:#2b2b2b; font-size:14px;'>Poke Mart</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:2px; background:#b9b59f; margin:10px 0 14px;'></div>", unsafe_allow_html=True)

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
                "<div style='background:#f7f6ef; border:2px solid #9a9680; border-radius:6px; "
                "padding:10px 12px; color:#1f1f1f; font-family:\"Press Start 2P\", monospace; box-shadow: inset 0 0 0 1px rgba(255,255,255,0.45);'>"
                "<div style='font-size:13px; color:#2b2b2b; font-weight:900; text-shadow:0 0 1px rgba(0,0,0,0.35); letter-spacing:0.3px;'>Disponible</div>"
                f"<div style='font-size:26px; margin-top:8px; font-weight:900; color:#1b1b1b; text-shadow:0 0 1px rgba(0,0,0,0.45);'>{COIN} {avail}</div>"
                f"<div style='font-size:13px; color:#333; margin-top:8px; font-weight:900; line-height:1.45;'>Base: {COIN} {base} | Gastado: {COIN} {spent} | Castigo: {COIN} {extra_reduction}</div>"
                "</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='background:#f7f6ef; border:2px solid #9a9680; border-radius:6px; "
                "padding:10px 12px; color:#1f1f1f; font-family:\"Press Start 2P\", monospace;'>"
                "<div style='font-size:13px; color:#2b2b2b; font-weight:900; text-shadow:0 0 1px rgba(0,0,0,0.35);'>Disponible</div>"
                f"<div style='font-size:26px; margin-top:8px; font-weight:900; color:#1b1b1b; text-shadow:0 0 1px rgba(0,0,0,0.45);'>{COIN} 0</div>"
                "</div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        "<div style='background:#f7f6ef; border:2px solid #9a9680; border-radius:6px; "
        "padding:8px 10px; font-size:12px; color:#2b2b2b; font-family:\"Press Start 2P\", monospace; "
        "font-weight:900; text-shadow:0 0 1px rgba(0,0,0,0.25); display:inline-block;'>Catalogo</div>",
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
    st.markdown("<div style='height:2px; background:#b9b59f; margin:10px 0 14px;'></div>", unsafe_allow_html=True)
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
