from __future__ import annotations

import streamlit as st

from app.interfaz.theme import apply_platinum_ui
from app.tienda.sections import (
    render_money_panel,
    render_pending_purchase,
    render_purchase_history,
    render_shop_catalog,
    render_shop_header,
)


def page_tienda() -> None:
    apply_platinum_ui("Tienda")
    render_shop_header()
    current_user = st.session_state.get("user") or "-"
    penalties, store_locked, avail = render_money_panel(current_user)
    render_shop_catalog(penalties=penalties, store_locked=store_locked, current_user=current_user, available=avail)
    render_pending_purchase(current_user, store_locked=store_locked)

    st.markdown("---")
    render_purchase_history()

    ctx = st.session_state.get("redeem_ctx")
    if ctx:
        from app.tienda.redeem import render_redeem_flow

        render_redeem_flow(ctx, current_user)
