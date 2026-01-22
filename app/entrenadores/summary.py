from __future__ import annotations

from pathlib import Path
import base64
import mimetypes
import os
import streamlit as st

from app.entrenadores.badges import count_badges
from app.entrenadores.boxes import muertos_box_index
from app.entrenadores.profile import find_trainer_image
from storage import settings_get, settings_set
from conex_pkhex import extract_box


BADGES_DIR = Path("assets") / "medallas"

_SINNOH_BADGE_FILES = [
    "Medalla_Lignito.png",
    "Medalla_Bosque.png",
    "Medalla_Reliquia.png",
    "Medalla_Adoquin.png",
    "Medalla_Cienaga.png",
    "Medalla_Mina.png",
    "Medalla_Carambano.png",
    "Medalla_Faro.png",
]


def _img_uri(path: str) -> str:
    try:
        if not path:
            return ""
        try:
            mtime = os.path.getmtime(path)
        except Exception:
            mtime = None
        try:
            cache = st.session_state.setdefault("_img_uri_cache", {})
            key = (path, mtime)
            if key in cache:
                return cache[key]
        except Exception:
            cache = None
        mt = mimetypes.guess_type(path)[0] or "image/png"
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        uri = f"data:{mt};base64,{b64}"
        if cache is not None:
            cache[(path, mtime)] = uri
        return uri
    except Exception:
        return ""


def _medals_html(count: int) -> str:
    try:
        n = max(0, min(int(count or 0), 8))
    except Exception:
        n = 0
    files: list[str] = []
    for i in range(n):
        p = BADGES_DIR / _SINNOH_BADGE_FILES[i]
        if p.exists():
            files.append(str(p))
    if not files:
        return "<div style='font-size:11px; color:#5a5a5a;'>Sin medallas</div>"
    imgs = []
    for f in files:
        uri = _img_uri(f)
        if uri:
            imgs.append(f"<img src='{uri}' alt='medalla' style='width:28px; height:auto; image-rendering:pixelated;'/>")
    return "<div style='display:flex; gap:6px; align-items:center; flex-wrap:wrap;'>" + "".join(imgs) + "</div>"


def _hp_bar(label: str, value: float, cap: float, color: str) -> str:
    try:
        pct = 0 if cap <= 0 else max(0, min(100, int(100 * float(value) / float(cap))))
    except Exception:
        pct = 0
    return pct


def _ensure_trainer_css() -> None:
    css = """
    <style>
    .trainer-panel { border:2px solid #9a9680; background:#f7f6ef; border-radius:6px; padding:10px; }
    .trainer-head { background:#f1c258; border:2px solid #c28f27; border-radius:6px; padding:6px 8px; font-weight:900; color:#1f1f1f; }
    .trainer-grid { display:grid; grid-template-columns: 150px 1fr; gap:10px; margin-top:8px; }
    .trainer-portrait { background:#e79a46; border:2px solid #c28f27; border-radius:6px; padding:6px; display:flex; align-items:center; justify-content:center; }
    .trainer-portrait img { width:120px; height:auto; image-rendering:pixelated; }
    .trainer-bars { display:flex; flex-direction:column; gap:8px; }
    .tbar-row { display:grid; grid-template-columns: 110px 1fr 70px; align-items:center; gap:8px; }
    .tbar-label { font-size:11px; font-weight:900; color:#1f1f1f; }
    .tbar-track { height:10px; background:#2b2b2b; border:2px solid #2b2b2b; border-radius:6px; overflow:hidden; }
    .tbar-fill { height:100%; border-radius:4px; }
    .tbar-value { background:#f7f6ef; border:2px solid #9a9680; border-radius:6px; padding:2px 6px; font-size:11px; text-align:right; color:#1f1f1f; }
    .trainer-medals { margin-top:6px; }
    .trainer-kia { margin-top:8px; background:#f7f6ef; border:2px solid #9a9680; border-radius:6px; padding:8px; font-size:11px; color:#1f1f1f; }
    .trainer-note { margin-top:6px; font-size:10px; color:#2b2b2b; }
    </style>
    """
    try:
        st.markdown(css, unsafe_allow_html=True)
    except Exception:
        pass


def _revives_key(user: str) -> str:
    return f"revived_after_wipe:{user}"


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


def trainer_summary_with_portrait_ui(sav_json: dict, box_count: int, *, is_own_profile: bool) -> None:
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
    bruto = monedas_badges + monedas_liga
    try:
        from storage import total_spent
        spent = total_spent(jugador or "")
    except Exception:
        spent = 0
    monedas = max(bruto - spent, 0)

    try:
        from app.liga.ranking import current_points_total
        puntos = current_points_total(jugador or "")
    except Exception:
        puntos = 0.0

    box_index_muertos = muertos_box_index(box_count)
    try:
        muertos_list = extract_box(sav_json, box_index_muertos) if box_count > box_index_muertos else []
    except Exception:
        muertos_list = []
    muertos = len(muertos_list)
    revividos = _get_revives(jugador or "")

    trainer = jugador or ""
    img = find_trainer_image(trainer)
    img_uri = _img_uri(img) if img else ""
    region = st.session_state.get("trainer_region", {}).get(jugador or "", "Sinnoh")

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
        f"<div class='trainer-kia'>Muertos (Caja 18)<br/><strong>{muertos}</strong></div>"
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
