from __future__ import annotations

import html as _html
import streamlit as st

from app.common import COIN
from app.tienda.common import _fix_text, _norm, _pokeapi_item_png, _resolve_img_src, _shop_asset
from app.tienda.discounts import discount_label
from app.tienda.money import _money_available


def _render_item_card(
    item: dict,
    idx_key: str,
    *,
    available: int | None = None,
    discount: dict | None = None,
) -> None:
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
    discount = discount or None
    effective_price = int(discount.get("discount_price") or price) if discount else price
    base_price = int(discount.get("base_price") or price) if discount else price
    afford = available >= effective_price
    img_html = ""
    if img:
        img_html = (
            "<img class='shop-icon' "
            f"src='{img}' alt='' onerror='this.style.display=\"none\"'/>"
        )
    else:
        img_html = f"<div class='shop-icon'>{icon}</div>" if icon else ""
    name_html = _html.escape(str(name)) if name else "-"
    desc_html = _html.escape(str(desc)) if desc else ""
    if discount:
        label = discount_label(str(discount.get("discount_kind") or "normal"))
        left = max(
            int(discount.get("stock_total") or 0) - int(discount.get("stock_used") or 0),
            0,
        )
        price_html = (
            f"<span class='shop-discount-badge'>🔥 {label}</span>"
            f"<span class='shop-old-price'>{COIN} {base_price}</span>"
            f"<span class='shop-arrow'>-&gt;</span>"
            f"<span class='shop-main-price'>{COIN} {effective_price}</span>"
            f"<span class='shop-stock'>Quedan {left}</span>"
        )
    else:
        price_html = f"<span class='shop-main-price'>{COIN} {price}</span>"
    missing_html = ""
    if (available is not None) and (not afford) and effective_price > 0:
        missing_html = f"<div class='shop-missing'>Faltan {COIN} {effective_price - available}</div>"

    info_html = ""
    if desc_html:
        info_html += f"<div class='shop-desc'>{desc_html}</div>"
    info_html += f"<div class='shop-price'>{price_html}</div>"
    if missing_html:
        info_html += missing_html
    card_class = "shop-card"
    if discount:
        card_class += " is-sale"
    if not afford:
        card_class += " is-poor"
    st.markdown(
        f"<div class='{card_class}'>"
        "<div class='shop-head'>"
        f"<span class='shop-name'>{name_html}</span>"
        f"<span class='shop-sku'>{idx_key.split('_')[0]}-{idx_key.split('_')[-1]}</span>"
        "</div>"
        "<div class='shop-body'>"
        f"<div class='shop-icon-slot'>{img_html}</div>"
        "<div class='shop-info'>"
        + info_html
        + "</div></div></div>",
        unsafe_allow_html=True,
    )
    if st.button("Comprar", key=f"buy_{idx_key}", disabled=(not afford) or effective_price <= 0, use_container_width=True):
        st.session_state.pop("shop_error", None)
        pending = {"name": name, "price": int(effective_price), "base_price": int(base_price)}
        if discount:
            pending.update(
                {
                    "discount_id": int(discount.get("id") or 0),
                    "discount_kind": str(discount.get("discount_kind") or "normal"),
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
                    it["img"] = _shop_asset("menta") or _shop_asset("adamant-mint") or _pokeapi_item_png("leaf-stone")
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
            item_name = str(it.get("name") or "")
            _render_item_card(
                it,
                f"{category_key}_{idx}",
                available=available,
                discount=(discounts or {}).get(item_name),
            )
    st.write("")
