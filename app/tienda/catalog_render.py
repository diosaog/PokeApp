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
            "style='width:56px; height:56px; image-rendering:pixelated;' "
            f"src='{img}' alt='' onerror='this.style.display=\"none\"'/>"
        )
    else:
        img_html = f"<div style='font-size:24px; line-height:1;'>{icon}</div>" if icon else ""
    name_html = _html.escape(str(name)) if name else "-"
    desc_html = _html.escape(str(desc)) if desc else ""
    price_html = f"{COIN} {price}"
    missing_html = ""
    if (available is not None) and (not afford) and price > 0:
        missing_html = f"<div class='shop-missing'>Faltan {COIN} {price - available}</div>"

    card_style = (
        "background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%); border:1px solid var(--bw2-edge); border-radius:0; padding:0; "
        "color:var(--bw2-text); margin-bottom:8px; overflow:hidden; "
        "font-family:var(--font-ui); font-weight:400; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);"
    )
    head_style = "background:linear-gradient(180deg,var(--accent) 0%, var(--accent-dark) 100%); border-bottom:1px solid var(--bw2-edge-strong); padding:9px 10px;"
    body_style = "display:flex; align-items:center; gap:10px; padding:10px;"
    name_style = "font-size:10px; color:#ffffff; font-family:var(--font-pixel); font-weight:700; line-height:1.35; text-transform:uppercase; letter-spacing:0.04em;"
    desc_style = "font-size:18px; color:var(--bw2-text-soft); margin-top:5px; font-weight:400; line-height:1.25;"
    price_style = (
        "display:inline-block; margin-top:6px; background:linear-gradient(180deg,var(--bw2-panel-3) 0%, var(--bw2-panel) 100%); border:1px solid rgba(255,255,255,0.12); "
        "border-radius:0; padding:6px 9px; font-size:10px; color:#ffffff; font-family:var(--font-pixel); font-weight:700; line-height:1.25;"
    )
    missing_style = "font-size:18px; color:#ffaba7; margin-top:6px; font-weight:400; line-height:1.25;"
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
            _render_item_card(it, f"{category_key}_{idx}", available=available)
    st.write("")
