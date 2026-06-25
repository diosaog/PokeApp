from __future__ import annotations

from datetime import datetime as _dt
import html as _html

import streamlit as st

from app.common import COIN
from app.discord_notify import (
    discord_webhook_configured,
    discord_webhook_status,
    notify_discount_purchase_async,
    send_test_notification,
)
from app.entrenadores.trainer_flags import is_trainer_retired
from app.juicios.penalties import get_user_penalties
from app.liga.context import current_jornada
from app.tienda.catalog import _render_shop_items, get_catalog
from app.tienda.discounts import shop_promotions_by_item
from app.tienda.money import clear_money_caches, money_breakdown
from app.tienda.styles import render_shop_styles
from storage import (
    add_purchase,
    claimed_shop_discount_ids,
    clear_all_pokemon_flags,
    clear_pokemon_flags_for_owner,
    list_purchases,
    purchase_shop_discount,
)
DIVIDER_HTML = "<div style='height:2px; background:linear-gradient(90deg, transparent 0%, var(--accent) 22%, var(--accent) 78%, transparent 100%); margin:10px 0 14px;'></div>"


def render_shop_header() -> None:
    render_shop_styles()
    user = _html.escape(str(st.session_state.get("user") or "-"))
    jornada = current_jornada()
    st.markdown(
        (
            "<div class='mart-hero'>"
            "<div class='mart-hero-left'>"
            "<div class='mart-kicker'>Unova Market System</div>"
            "<div class='mart-title'>Supermercado Pokemon</div>"
            "<div class='mart-subrow'>"
            f"<span class='mart-pill'>Jornada {int(jornada)}</span>"
            "<span class='mart-pill'>Poke Mart BW2</span>"
            "<span class='mart-pill'>Linea de caja</span>"
            "</div>"
            "</div>"
            "<div class='mart-hero-right'>"
            "<div class='mart-led'>Terminal online</div>"
            f"<div class='mart-pill'>Cliente: {user}</div>"
            "<div class='mart-pill'>Stock por categorias</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_money_panel(current_user: str) -> tuple[dict, bool, int | None]:
    penalties = get_user_penalties(current_user if current_user != "-" else "")
    retired = is_trainer_retired(current_user)
    store_locked = bool(penalties.get("store_blocked")) or retired
    available = None
    if current_user != "-":
        try:
            breakdown = money_breakdown(current_user)
        except Exception:
            breakdown = {"base": 0, "spent": 0, "coins_reduction": 0, "available": 0}
        base = int(breakdown.get("base") or 0)
        spent = int(breakdown.get("spent") or 0)
        extra_reduction = int(breakdown.get("coins_reduction") or 0)
        available = int(breakdown.get("available") or 0)
    else:
        base = spent = extra_reduction = 0
        available = 0

    status = "Bloqueada" if store_locked else "Abierta"
    status_value = "Retirado" if retired else ("Juicio" if store_locked else "OK")
    st.markdown(
        (
            "<div class='mart-register-grid'>"
            "<div class='mart-register-card is-main'>"
            "<div class='mart-label'>Disponible</div>"
            f"<div class='mart-value'>{COIN} {available}</div>"
            "</div>"
            "<div class='mart-register-card'>"
            "<div class='mart-label'>Base</div>"
            f"<div class='mart-value'>{COIN} {base}</div>"
            "</div>"
            "<div class='mart-register-card'>"
            "<div class='mart-label'>Gastado</div>"
            f"<div class='mart-value'>{COIN} {spent}</div>"
            "</div>"
            "<div class='mart-register-card'>"
            f"<div class='mart-label'>Caja {status}</div>"
            f"<div class='mart-value'>{status_value}"
            + (f" -{COIN} {extra_reduction}" if extra_reduction else "")
            + "</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if retired:
        st.warning("Este entrenador esta retirado. Puede mirar la tienda, pero no comprar.")
    return penalties, store_locked, available


def _render_locked_notice(penalties: dict) -> None:
    tramos = list(penalties.get("store_ban_tramos") or [])
    src = list(penalties.get("sources") or [])
    detail = []
    if tramos:
        detail.append("Tramo: " + ", ".join(str(t) for t in tramos))
    if src:
        detail.append("Origen: " + " | ".join(str(s) for s in src))
    st.markdown(
        (
            "<div class='mart-alert'>"
            "<strong>Tienda bloqueada</strong>"
            f"<span>{_html.escape(' | '.join(detail) if detail else 'No puedes gastar monedas.')}</span>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _discount_count(items: list[dict], discounts: dict[str, dict]) -> int:
    names = {str(item.get("name") or "") for item in items}
    return sum(1 for name in names if name in discounts)


def _render_aisle_header(code: str, title: str, items: list[dict], discounts: dict[str, dict]) -> None:
    discount_total = _discount_count(items, discounts)
    st.markdown(
        (
            "<div class='mart-aisle-head'>"
            "<div>"
            f"<div class='mart-aisle-code'>{_html.escape(code)}</div>"
            f"<div class='mart-aisle-title'>{_html.escape(title)}</div>"
            "</div>"
            "<div class='mart-aisle-meta'>"
            f"<span class='mart-pill'>{len(items)} productos</span>"
            f"<span class='mart-pill'>{discount_total} rebajas</span>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_shop_catalog(*, penalties: dict, store_locked: bool, current_user: str, available: int | None) -> None:
    catalog = get_catalog()
    jornada = current_jornada()
    discounts = shop_promotions_by_item(jornada)
    claimed_ids = claimed_shop_discount_ids(
        current_user,
        [int(discount.get("id") or 0) for discount in discounts.values()],
    )
    discounts = {
        item: {
            **discount,
            "user_claimed": int(discount.get("id") or 0) in claimed_ids,
        }
        for item, discount in discounts.items()
    }

    if store_locked:
        _render_locked_notice(penalties)

    st.markdown(DIVIDER_HTML, unsafe_allow_html=True)

    tab_com, tab_bay, tab_comp, tab_bred = st.tabs(["Comodines", "Bayas", "Competitivos", "Crianza"])
    with tab_com:
        _render_aisle_header("Categoria", "Comodines", catalog["comodines"], discounts)
        _render_shop_items(catalog["comodines"], "comodines", available=available if current_user != "-" else None, discounts=discounts)
    with tab_bay:
        _render_aisle_header("Categoria", "Bayas", catalog["bayas"], discounts)
        _render_shop_items(catalog["bayas"], "bayas", available=available if current_user != "-" else None, discounts=discounts)
    with tab_comp:
        _render_aisle_header("Categoria", "Competitivos", catalog["competitivos"], discounts)
        _render_shop_items(catalog["competitivos"], "competitivos", available=available if current_user != "-" else None, discounts=discounts)
    with tab_bred:
        _render_aisle_header("Categoria", "Crianza", catalog["crianza"], discounts)
        _render_shop_items(catalog["crianza"], "crianza", available=available if current_user != "-" else None, discounts=discounts)


def render_pending_purchase(current_user: str, *, store_locked: bool) -> None:
    pending = st.session_state.get("shop_pending")
    if pending and is_trainer_retired(current_user):
        st.session_state.pop("shop_pending", None)
        st.warning("No se puede completar la compra: este entrenador esta retirado.")
        return
    if pending and store_locked:
        st.session_state.pop("shop_pending", None)
        st.warning("No se puede completar la compra: la tienda esta bloqueada por castigo.")
        return
    if not pending:
        return

    nombre = pending.get("name")
    precio = int(pending.get("price") or 0)
    base_price = int(pending.get("base_price") or precio)
    discount_id = pending.get("discount_id")
    discount_kind = str(pending.get("discount_kind") or "normal")
    force_base = bool(pending.get("force_base_price"))
    jornada = current_jornada()
    display_price = base_price if force_base else precio
    nombre_html = _html.escape(str(nombre or ""))
    if discount_id and not force_base:
        desc = (
            f"Comprar '<em>{nombre_html}</em>' en rebaja por {COIN} {precio} "
            f"(precio original {COIN} {base_price})?"
        )
    elif force_base:
        desc = (
            f"La rebaja de '<em>{nombre_html}</em>' se acaba de agotar. "
            f"Comprar igualmente por {COIN} {base_price}?"
        )
    else:
        desc = f"Comprar '<em>{nombre_html}</em>' por {COIN} {precio}?"
    st.markdown(
        (
            "<div class='mart-confirm-card'>"
            "<div class='mart-confirm-title'>Ticket de caja</div>"
            f"<div class='mart-confirm-line'>{desc}</div>"
            f"<div class='mart-confirm-price'>{COIN} {display_price}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    try:
        available_now = int(money_breakdown(current_user).get("available") or 0)
    except Exception:
        available_now = None
    confirm_disabled = (
        available_now is not None
        and int(display_price) > int(available_now)
    )
    if confirm_disabled:
        st.error(f"No tienes monedas suficientes para comprarlo por {COIN} {display_price}.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Confirmar compra", disabled=confirm_disabled, use_container_width=True):
            try:
                if discount_id and not force_base:
                    claimed = purchase_shop_discount(
                        user=current_user,
                        discount_id=int(discount_id),
                        jornada=jornada,
                    )
                    if not claimed.get("purchased"):
                        reason = str(claimed.get("reason") or "")
                        if reason in {"exhausted", "already_claimed", "expired"}:
                            pending["force_base_price"] = True
                            pending["price"] = int(base_price)
                            st.session_state["shop_pending"] = pending
                            if reason == "already_claimed":
                                st.warning(
                                    "Ya aprovechaste una unidad de esta promoción. "
                                    "Puedes comprar otra al precio normal."
                                )
                            else:
                                st.warning(
                                    "La promoción ya no está disponible. "
                                    "Confirma si quieres comprar al precio normal."
                                )
                            st.rerun()
                        if reason == "pending":
                            st.error("La promoción todavía está en traslado.")
                        else:
                            st.error("La promoción ya no está disponible.")
                        st.session_state.pop("shop_pending", None)
                        st.rerun()

                    price_paid = int(claimed.get("discount_price") or precio)
                    original_price = int(claimed.get("base_price") or base_price)
                    kind = str(claimed.get("discount_kind") or discount_kind)
                    pid = int(claimed.get("purchase_id") or 0)
                    notify_discount_purchase_async(
                        user=current_user,
                        item=str(nombre),
                        base_price=original_price,
                        discount_price=price_paid,
                        discount_kind=kind,
                        purchase_id=pid,
                    )
                else:
                    pid = add_purchase(
                        current_user,
                        nombre,
                        display_price,
                        jornada=jornada,
                        base_price=base_price if force_base else None,
                    )
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
    if is_trainer_retired(current_user):
        st.caption("Entrenador retirado: no puede reiniciar flags de Pokemon.")
        return
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
