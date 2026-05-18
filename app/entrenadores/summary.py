from __future__ import annotations

import base64
import mimetypes
import os
import streamlit as st

from app.entrenadores.badges import UNOVA_BW2_BADGE_NAMES, count_badges
from app.entrenadores.boxes import muertos_box_index
from app.entrenadores.constants import DEAD_BOX_LABEL
from app.entrenadores.profile import find_trainer_image
from app.juicios.penalties import get_user_penalties
from app.tienda.money import (
    LEAGUE_FINISHED_COINS,
    clear_money_caches,
    league_finished_bonus,
    league_finished_claimed,
    mark_league_finished_claimed,
)
from storage import settings_get, settings_set


def _cache_data(ttl: int = 30):
    try:
        return st.cache_data(ttl=ttl, show_spinner=False)
    except Exception:
        return lambda f: f
from conex_pkhex import extract_box


_UNOVA_BW2_BADGE_COLORS = (
    "#d8d2bd",
    "#b56ad6",
    "#79c255",
    "#f4c542",
    "#c08b53",
    "#75bce8",
    "#8793d8",
    "#4fb7d4",
)


@_cache_data(ttl=120)
def _img_uri(path: str, mtime: float | None = None) -> str:
    try:
        if not path:
            return ""
        mt = mimetypes.guess_type(path)[0] or "image/png"
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        uri = f"data:{mt};base64,{b64}"
        return uri
    except Exception:
        return ""


@_cache_data(ttl=120)
def _medals_html(count: int) -> str:
    try:
        n = max(0, min(int(count or 0), 8))
    except Exception:
        n = 0
    chips = []
    for i, name in enumerate(UNOVA_BW2_BADGE_NAMES):
        active = i < n
        color = _UNOVA_BW2_BADGE_COLORS[i]
        bg = color if active else "rgba(216,223,232,0.08)"
        border = "#ffffff" if active else "rgba(216,223,232,0.18)"
        fg = "#10151b" if active else "rgba(216,223,232,0.45)"
        shadow = "0 0 12px rgba(255,255,255,0.16)" if active else "none"
        chips.append(
            "<span title='Medalla "
            f"{name}' style='display:inline-flex; align-items:center; justify-content:center; min-width:56px; padding:4px 6px; "
            f"background:{bg}; border:1px solid {border}; color:{fg}; box-shadow:{shadow}; "
            "font-family:var(--font-pixel); font-size:8px; text-transform:uppercase; letter-spacing:0.02em;'>"
            f"{name}</span>"
        )
    return "<div style='display:flex; gap:5px; align-items:center; flex-wrap:wrap;'>" + "".join(chips) + "</div>"


def _hp_bar(label: str, value: float, cap: float, color: str) -> str:
    try:
        pct = 0 if cap <= 0 else max(0, min(100, int(100 * float(value) / float(cap))))
    except Exception:
        pct = 0
    return pct


def _ensure_trainer_css() -> None:
    css = """
    <style>
    .trainer-panel { border:1px solid var(--bw2-edge); background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%); border-radius:0; padding:10px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28); }
    .trainer-head { background:linear-gradient(180deg,var(--accent) 0%, var(--accent-dark) 100%); border:1px solid var(--bw2-edge-strong); border-radius:0; padding:7px 9px; font-weight:700; color:#ffffff; font-family:var(--font-pixel); font-size:10px; text-transform:uppercase; letter-spacing:0.04em; clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px); }
    .trainer-grid { display:grid; grid-template-columns: 150px 1fr; gap:10px; margin-top:8px; }
    .trainer-portrait { background:linear-gradient(180deg,var(--bw2-screen-2) 0%, var(--bw2-screen) 100%); border:1px solid var(--bw2-edge); border-radius:0; padding:8px; display:flex; align-items:center; justify-content:center; box-shadow: inset 0 1px 0 rgba(255,255,255,0.06); }
    .trainer-portrait img { width:120px; height:auto; image-rendering:pixelated; }
    .trainer-bars { display:flex; flex-direction:column; gap:8px; }
    .tbar-row { display:grid; grid-template-columns: 110px 1fr 70px; align-items:center; gap:8px; }
    .tbar-label { font-size:10px; font-weight:700; color:var(--bw2-text); font-family:var(--font-pixel); text-transform:uppercase; }
    .tbar-track { height:10px; background:#0d1217; border:1px solid var(--bw2-edge); border-radius:0; overflow:hidden; }
    .tbar-fill { height:100%; border-radius:4px; }
    .tbar-value { background:linear-gradient(180deg,var(--bw2-panel-3) 0%, var(--bw2-panel) 100%); border:1px solid var(--bw2-edge); border-radius:0; padding:2px 6px; font-size:1rem; text-align:right; color:var(--bw2-text); }
    .trainer-medals { margin-top:6px; }
    .trainer-kia { margin-top:8px; background:linear-gradient(180deg,var(--bw2-panel-3) 0%, var(--bw2-panel) 100%); border:1px solid var(--bw2-edge); border-radius:0; padding:8px; font-size:1rem; color:var(--bw2-text); box-shadow: inset 0 1px 0 rgba(255,255,255,0.06); }
    .trainer-kia strong { font-family:var(--font-pixel); font-size:10px; color:#ffffff; }
    .trainer-note { margin-top:6px; font-size:1rem; color:var(--bw2-text-soft); }
    </style>
    """
    try:
        st.markdown(css, unsafe_allow_html=True)
    except Exception:
        pass


def _revives_key(user: str) -> str:
    return f"revived_after_wipe:{user}"


@_cache_data(ttl=30)
def _get_revives(user: str) -> int:
    if not user:
        return 0
    try:
        raw = settings_get(_revives_key(user))
        if raw is None or raw == "":
            return 0
        return max(int(raw), 0)
    except Exception:
        return 0


def _set_revives(user: str, count: int) -> None:
    if not user:
        return
    try:
        settings_set(_revives_key(user), str(max(0, int(count))))
    except Exception:
        pass


def _persist_badges_count(user: str, count: int) -> None:
    if not user:
        return
    try:
        cache = st.session_state.setdefault("_badges_cache", {})
        if cache.get(user) == int(count):
            return
        cache[user] = int(count)
    except Exception:
        pass
    try:
        settings_set(f"badges_count:{user}", str(max(0, int(count))))
    except Exception:
        pass


def _region_from_save(sav_json: dict, user: str) -> str:
    try:
        custom = st.session_state.get("trainer_region", {}).get(user or "")
        if custom:
            return str(custom)
    except Exception:
        pass
    try:
        game = str(sav_json.get("Game") or "").lower()
        if any(tag in game for tag in ("black", "white", "unova", "teselia")):
            return "Unova"
        if any(tag in game for tag in ("heartgold", "soulsilver", "johto")):
            return "Johto"
        if any(tag in game for tag in ("diamond", "pearl", "platinum", "sinnoh")):
            return "Sinnoh"
        if any(tag in game for tag in ("ruby", "sapphire", "emerald", "firered", "leafgreen", "hoenn", "kanto")):
            return "Hoenn"
    except Exception:
        pass
    try:
        gen = int(sav_json.get("Generation") or 0)
        if gen >= 5:
            return "Unova"
        if gen == 4:
            return "Sinnoh"
        if gen == 3:
            return "Hoenn"
    except Exception:
        pass
    return "Unova"


def trainer_summary_with_portrait_ui(
    sav_json: dict,
    box_count: int,
    *,
    is_own_profile: bool,
    save_path: str | None = None,
) -> None:
    _ensure_trainer_css()
    try:
        medallas = count_badges(sav_json)
    except Exception:
        medallas = 0

    jugador = st.session_state.get("trainer_selected") or st.session_state.get("user")
    _persist_badges_count(jugador or "", medallas)

    try:
        from app.liga.coins import coins_from_league
        monedas_liga = coins_from_league(jugador or "")
    except Exception:
        monedas_liga = 0

    monedas_badges = 4 * medallas
    bonus_liga_finalizada = league_finished_bonus(jugador or "")
    bruto = monedas_badges + monedas_liga + bonus_liga_finalizada
    try:
        from storage import total_spent
        spent = total_spent(jugador or "")
    except Exception:
        spent = 0
    penalties = get_user_penalties(jugador or "")
    coins_reduction = int(penalties.get("coins_reduction") or 0)
    if penalties.get("store_blocked"):
        monedas = 0
    else:
        monedas = max(bruto - spent - coins_reduction, 0)

    try:
        from app.liga.ranking import current_points_total
        puntos = current_points_total(jugador or "")
    except Exception:
        puntos = 0.0

    box_index_muertos = muertos_box_index(box_count)
    try:
        muertos_list = (
            extract_box(sav_json, box_index_muertos, save_path=save_path)
            if box_count > box_index_muertos
            else []
        )
    except Exception:
        muertos_list = []
    muertos = len(muertos_list)
    revividos = _get_revives(jugador or "")

    trainer = jugador or ""
    img = find_trainer_image(trainer)
    img_mtime = None
    try:
        if img:
            img_mtime = os.path.getmtime(img)
    except Exception:
        img_mtime = None
    img_uri = _img_uri(img, img_mtime) if img else ""
    region = _region_from_save(sav_json, jugador or "")

    coins_pct = _hp_bar("Monedas", monedas, 20, "#ffd54f")
    points_pct = _hp_bar("Puntos", puntos, 30, "#4fc3f7")
    medals_html = _medals_html(medallas)

    portrait_html = (
        f"<img src='{img_uri}' alt='trainer'/>" if img_uri
        else "<div style='font-size:11px; color:#1f1f1f;'>Sin retrato</div>"
    )

    panel_html = (
        "<div class='trainer-panel'>"
        f"<div class='trainer-head'>Entrenador: {trainer}  Region: {region}</div>"
        "<div class='trainer-grid'>"
        f"<div class='trainer-portrait'>{portrait_html}</div>"
        "<div class='trainer-bars'>"
        "<div class='tbar-row'>"
        "<div class='tbar-label'>Monedas</div>"
        "<div class='tbar-track'><div class='tbar-fill' style='width:"
        f"{coins_pct}%; background:#ffd54f;'></div></div>"
        f"<div class='tbar-value'>{monedas}</div>"
        "</div>"
        "<div class='tbar-row'>"
        "<div class='tbar-label'>Puntos</div>"
        "<div class='tbar-track'><div class='tbar-fill' style='width:"
        f"{points_pct}%; background:#4fc3f7;'></div></div>"
        f"<div class='tbar-value'>{puntos}</div>"
        "</div>"
        f"<div class='trainer-medals'>{medals_html}</div>"
        f"<div class='trainer-kia'>Muertos ({DEAD_BOX_LABEL})<br/><strong>{muertos}</strong></div>"
        f"<div class='trainer-note'>Revividos tras wipe: {revividos}</div>"
        "</div></div></div>"
    )

    st.markdown(panel_html, unsafe_allow_html=True)
    if is_own_profile:
        rev_col1, rev_col2 = st.columns([2, 1.2])
        with rev_col1:
            rev_count = st.number_input(
                "Revividos tras wipe (penaliza -0.4 c/u)",
                min_value=0,
                max_value=30,
                step=1,
                value=revividos,
                key=f"revives_wipe_{jugador}",
                help="Usa esta casilla para anotar los revividos tras un wipe.",
            )
        with rev_col2:
            if st.button("Guardar revividos", key=f"save_revives_{jugador}"):
                _set_revives(jugador or "", rev_count)
                st.success("Revividos guardados.")
        already_claimed = league_finished_claimed(jugador or "")
        can_claim_league_bonus = medallas >= 8 and not already_claimed
        if st.button(
            "Liga Finalizada",
            key=f"league_finished_{jugador}",
            disabled=not can_claim_league_bonus,
            help=(
                "Reclama 12 monedas por completar la liga."
                if can_claim_league_bonus
                else "Necesitas las 8 medallas para reclamarlo."
                if medallas < 8
                else "Ya has reclamado esta recompensa."
            ),
        ):
            if mark_league_finished_claimed(jugador or ""):
                clear_money_caches()
                st.success(f"Has recibido {LEAGUE_FINISHED_COINS} monedas por finalizar la liga.")
                st.rerun()
            else:
                st.error("No se pudo guardar la recompensa de liga.")
        if already_claimed:
            st.caption(f"Recompensa de liga reclamada: +{LEAGUE_FINISHED_COINS} monedas.")
        elif medallas < 8:
            st.caption("La recompensa Liga Finalizada se desbloquea con las 8 medallas.")
        else:
            st.caption(f"Pulsa el boton para reclamar +{LEAGUE_FINISHED_COINS} monedas.")
