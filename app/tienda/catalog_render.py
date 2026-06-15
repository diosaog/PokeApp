from __future__ import annotations

import html as _html

import streamlit as st

from app.common import COIN
from app.tienda.common import (
    _fix_text,
    _norm,
    _pokeapi_item_png,
    _resolve_img_src,
    _shop_asset,
)
from app.tienda.discounts import discount_label, promotion_opens_label
from app.tienda.money import _money_available


def _render_item_card(
    item: dict,
    idx_key: str,
    *,
    category_key: str,
    available: int | None = None,
    discount: dict | None = None,
) -> None:
    name = _fix_text(item.get("name"))
    price = int(item.get("price", 0))
    desc = _fix_text(item.get("desc") or "")
    icon = item.get("icon") or ""
    img = item.get("img")

    if not img and name:
        try:
            normalized = _norm(name)
            if "revivir" in normalized:
                img = _shop_asset("revivir") or _pokeapi_item_png("max-revive")
            elif "robar" in normalized:
                img = _shop_asset("robar") or _pokeapi_item_png("dread-plate")
            elif "captura extra" in normalized:
                img = _shop_asset("captura-extra") or _pokeapi_item_png("ultra-ball")
            elif "blindar" in normalized:
                img = _shop_asset("blindar") or _pokeapi_item_png("metal-coat")
            elif "fosil" in normalized or "fsil" in normalized:
                img = _shop_asset("fosil") or _pokeapi_item_png("helix-fossil")
        except Exception:
            img = None
    img = _resolve_img_src(img or "")

    user = st.session_state.get("user") or "-"
    if available is None:
        available = _money_available(user)

    discount = discount or None
    state = str(discount.get("promotion_state") or "active") if discount else ""
    already_claimed = bool(discount.get("user_claimed")) if discount else False
    pending_promotion = bool(discount) and state == "pending"
    active_promotion = bool(discount) and state == "active" and not already_claimed
    delivery_locked = pending_promotion and category_key != "comodines"
    base_price = int(discount.get("base_price") or price) if discount else price
    effective_price = (
        int(discount.get("discount_price") or price) if active_promotion else price
    )
    afford = available >= effective_price

    if img:
        img_html = (
            "<img class='shop-icon' "
            f"src='{img}' alt='' onerror='this.style.display=\"none\"'/>"
        )
    else:
        img_html = f"<div class='shop-icon'>{icon}</div>" if icon else ""

    name_html = _html.escape(str(name)) if name else "-"
    desc_html = _html.escape(str(desc)) if desc else ""
    if pending_promotion:
        label = discount_label(str(discount.get("discount_kind") or "normal"))
        future_price = int(discount.get("discount_price") or price)
        opens = _html.escape(promotion_opens_label(discount))
        availability = (
            "Comodín disponible ahora a precio normal"
            if category_key == "comodines"
            else "Stock en traslado"
        )
        price_html = (
            f"<span class='shop-discount-badge is-pending'>Próxima {label}</span>"
            f"<span class='shop-old-price'>{COIN} {base_price}</span>"
            f"<span class='shop-arrow'>-&gt;</span>"
            f"<span class='shop-future-price'>{COIN} {future_price}</span>"
            f"<span class='shop-stock'>{availability} · {opens}</span>"
        )
    elif active_promotion:
        label = discount_label(str(discount.get("discount_kind") or "normal"))
        left = max(
            int(discount.get("stock_total") or 0)
            - int(discount.get("stock_used") or 0),
            0,
        )
        price_html = (
            f"<span class='shop-discount-badge'>🔥 {label}</span>"
            f"<span class='shop-old-price'>{COIN} {base_price}</span>"
            f"<span class='shop-arrow'>-&gt;</span>"
            f"<span class='shop-main-price'>{COIN} {effective_price}</span>"
            f"<span class='shop-stock'>Quedan {left}</span>"
        )
    elif discount and already_claimed:
        price_html = (
            "<span class='shop-discount-badge is-used'>Promoción ya utilizada</span>"
            f"<span class='shop-main-price'>{COIN} {price}</span>"
            "<span class='shop-stock'>Ya aprovechaste una unidad de esta oferta</span>"
        )
    else:
        price_html = f"<span class='shop-main-price'>{COIN} {price}</span>"

    missing_html = ""
    if available is not None and not afford and effective_price > 0:
        missing_html = (
            f"<div class='shop-missing'>Faltan {COIN} "
            f"{effective_price - available}</div>"
        )

    info_html = f"<div class='shop-desc'>{desc_html}</div>" if desc_html else ""
    info_html += f"<div class='shop-price'>{price_html}</div>"
    info_html += missing_html

    card_classes = ["shop-card"]
    if active_promotion:
        card_classes.append("is-sale")
    if pending_promotion:
        card_classes.append("is-pending-sale")
    if delivery_locked:
        card_classes.append("is-delivery-locked")
    if not afford:
        card_classes.append("is-poor")

    st.markdown(
        f"<div class='{' '.join(card_classes)}'>"
        "<div class='shop-head'>"
        f"<span class='shop-name'>{name_html}</span>"
        f"<span class='shop-sku'>{idx_key.split('_')[0]}-{idx_key.split('_')[-1]}</span>"
        "</div>"
        "<div class='shop-body'>"
        f"<div class='shop-icon-slot'>{img_html}</div>"
        f"<div class='shop-info'>{info_html}</div>"
        "</div></div>",
        unsafe_allow_html=True,
    )

    button_label = "Stock en traslado" if delivery_locked else "Comprar"
    if st.button(
        button_label,
        key=f"buy_{idx_key}",
        disabled=delivery_locked or not afford or effective_price <= 0,
        use_container_width=True,
    ):
        st.session_state.pop("shop_error", None)
        pending = {
            "name": name,
            "price": int(effective_price),
            "base_price": int(base_price),
        }
        if active_promotion:
            pending.update(
                {
                    "discount_id": int(discount.get("id") or 0),
                    "discount_kind": str(
                        discount.get("discount_kind") or "normal"
                    ),
                }
            )
        st.session_state["shop_pending"] = pending
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


def _render_shop_items(
    items: list[dict],
    category_key: str,
    *,
    available: int | None = None,
    discounts: dict[str, dict] | None = None,
) -> None:
    if category_key == "comodines":
        try:
            for item in items:
                normalized = _norm(item.get("name") or "")
                if (
                    "fosil" in normalized
                    or (normalized.startswith("f") and "sil" in normalized)
                    or "fossil" in normalized
                ) and "img" not in item:
                    item["img"] = _shop_asset("fosil") or _pokeapi_item_png(
                        "helix-fossil"
                    )
                elif "captura" in normalized and "extra" in normalized and "img" not in item:
                    item["img"] = _shop_asset("captura-extra") or _pokeapi_item_png(
                        "ultra-ball"
                    )
                elif "robar" in normalized and "img" not in item:
                    item["img"] = _shop_asset("robar") or _pokeapi_item_png(
                        "dread-plate"
                    )
                elif "revivir" in normalized and "img" not in item:
                    item["img"] = _shop_asset("revivir") or _pokeapi_item_png(
                        "max-revive"
                    )
                elif "blindar" in normalized and "img" not in item:
                    item["img"] = _shop_asset("blindar") or _pokeapi_item_png(
                        "metal-coat"
                    )
        except Exception:
            pass
    elif category_key == "crianza":
        try:
            for item in items:
                normalized = _norm(item.get("name") or "")
                if "menta" in normalized and not item.get("img"):
                    item["img"] = (
                        _shop_asset("menta")
                        or _shop_asset("adamant-mint")
                        or _pokeapi_item_png("leaf-stone")
                    )
        except Exception:
            pass
    else:
        try:
            for item in items:
                if not item.get("img"):
                    item["img"] = _shop_asset(item.get("name") or "")
        except Exception:
            pass

    cols = st.columns(3)
    for idx, item in enumerate(items):
        with cols[idx % 3]:
            item_name = str(item.get("name") or "")
            _render_item_card(
                item,
                f"{category_key}_{idx}",
                category_key=category_key,
                available=available,
                discount=(discounts or {}).get(item_name),
            )
    st.write("")
