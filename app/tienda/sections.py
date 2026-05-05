from __future__ import annotations

from datetime import datetime as _dt

import streamlit as st

from app.common import COIN
from app.discord_notify import discord_webhook_configured, discord_webhook_status, send_test_notification
from app.juicios.penalties import get_user_penalties
from app.tienda.catalog import _render_shop_items, get_catalog
from app.tienda.money import clear_money_caches, money_breakdown
from storage import add_purchase, clear_all_pokemon_flags, clear_pokemon_flags_for_owner, list_purchases

SHOP_PAGE_CSS = (
    "<style>"
    ".stButton>button, .stButton>button *{font-family:var(--font-pixel) !important; font-size:11px !important; "
    "font-weight:700 !important; color:#ffffff !important; -webkit-text-fill-color:#ffffff !important; opacity:1 !important;}"
    ".stButton>button:disabled, .stButton>button:disabled *{opacity:1 !important; color:#cbd1d9 !important; -webkit-text-fill-color:#cbd1d9 !important;}"
    "button[data-baseweb='tab'], button[role='tab'], button[data-baseweb='tab'] *, button[role='tab'] *{font-family:var(--font-pixel) !important; font-size:10px !important; font-weight:700 !important;}"
    "</style>"
)
DIVIDER_HTML = "<div style='height:2px; background:linear-gradient(90deg, transparent 0%, var(--accent) 22%, var(--accent) 78%, transparent 100%); margin:10px 0 14px;'></div>"


def render_shop_header() -> None:
    st.markdown(SHOP_PAGE_CSS, unsafe_allow_html=True)
    st.markdown(
        "<div style='display:inline-block; background:linear-gradient(180deg,var(--accent) 0%, var(--accent-dark) 100%);"
        " border:1px solid var(--bw2-edge-strong); border-radius:0; padding:9px 12px; color:#ffffff;"
        " font-family:var(--font-pixel); font-weight:700; font-size:12px; text-transform:uppercase;"
        " clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);'>Poke Mart</div>",
        unsafe_allow_html=True,
    )
    st.markdown(DIVIDER_HTML, unsafe_allow_html=True)


def render_money_panel(current_user: str) -> tuple[dict, bool, int | None]:
    penalties = get_user_penalties(current_user if current_user != "-" else "")
    store_locked = bool(penalties.get("store_blocked"))
    available = None
    _, colR = st.columns([5, 2])
    with colR:
        if current_user != "-":
            try:
                breakdown = money_breakdown(current_user)
            except Exception:
                breakdown = {"base": 0, "spent": 0, "coins_reduction": 0, "available": 0}
            base = int(breakdown.get("base") or 0)
            spent = int(breakdown.get("spent") or 0)
            extra_reduction = int(breakdown.get("coins_reduction") or 0)
            available = int(breakdown.get("available") or 0)
            st.markdown(
                "<div style='background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%); border:1px solid var(--bw2-edge); border-radius:0; "
                "padding:10px 12px; color:var(--bw2-text); font-family:var(--font-ui); box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);'>"
                "<div style='font-size:10px; color:#fff; font-family:var(--font-pixel); font-weight:700; letter-spacing:0.05em; text-transform:uppercase;'>Disponible</div>"
                f"<div style='font-size:28px; margin-top:8px; color:#ffffff;'>{COIN} {available}</div>"
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
    return penalties, store_locked, available


def render_shop_catalog(*, penalties: dict, store_locked: bool, current_user: str, available: int | None) -> None:
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
    st.markdown(DIVIDER_HTML, unsafe_allow_html=True)

    catalog = get_catalog()
    tab_com, tab_bay, tab_comp, tab_bred = st.tabs(["Comodines", "Bayas", "Competitivos", "Crianza"])
    with tab_com:
        _render_shop_items(catalog["comodines"], "comodines", available=available if current_user != "-" else None)
    with tab_bay:
        _render_shop_items(catalog["bayas"], "bayas", available=available if current_user != "-" else None)
    with tab_comp:
        _render_shop_items(catalog["competitivos"], "competitivos", available=available if current_user != "-" else None)
    with tab_bred:
        _render_shop_items(catalog["crianza"], "crianza", available=available if current_user != "-" else None)


def render_pending_purchase(current_user: str, *, store_locked: bool) -> None:
    pending = st.session_state.get("shop_pending")
    if pending and store_locked:
        st.session_state.pop("shop_pending", None)
        st.warning("No se puede completar la compra: la tienda esta bloqueada por castigo.")
        return
    if not pending:
        return

    nombre = pending.get("name")
    precio = int(pending.get("price") or 0)
    st.markdown(
        f"<div class='panel-dashed'><strong>Confirmacion</strong><br/>Comprar '<em>{nombre}</em>' por {COIN} {precio}?</div>",
        unsafe_allow_html=True,
    )
    st.info(f"Comprar '{nombre}' por {COIN} {precio}?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Confirmar compra", use_container_width=True):
            try:
                pid = add_purchase(current_user, nombre, precio)
                clear_money_caches()
                try:
                    from app.entrenadores.inventory import _inventory_cached

                    _inventory_cached.clear()
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


def render_purchase_history() -> None:
    with st.expander("Historial de compras (global)"):
        compras = list_purchases(limit=50)
        if not compras:
            st.caption("Sin compras registradas.")
            return
        rows = []
        for row in compras:
            if len(row) == 5:
                pid, user, item, price, ts = row
                status = None
            else:
                pid, user, item, price, ts, status, _red_at = row
            origen = "Premio" if int(price) == 0 else "Compra"
            rows.append(
                {
                    "#": pid,
                    "Jugador": user,
                    "Objeto": item,
                    "Precio": f"{COIN} {price}",
                    "Origen": origen,
                    "Fecha": _dt.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S"),
                    "Estado": (status or "pendiente").capitalize(),
                }
            )
        st.dataframe(rows, use_container_width=True)


def render_discord_panel() -> None:
    with st.expander("Discord"):
        if discord_webhook_configured():
            st.caption(discord_webhook_status())
        else:
            st.warning(discord_webhook_status())
        if st.button("Probar Aaron Avisa", key="test_discord_webhook"):
            sent, message = send_test_notification()
            if sent:
                st.success("Mensaje de prueba enviado a Discord.")
            else:
                st.error(message)


def render_flags_reset(current_user: str) -> None:
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
