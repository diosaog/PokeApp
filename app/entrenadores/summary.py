from __future__ import annotations

from pathlib import Path
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


def _render_medals_row(count: int) -> None:
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
        st.caption("Sin medallas")
        return
    cols = st.columns(len(files))
    for i, f in enumerate(files):
        with cols[i]:
            try:
                st.image(f, width=32)
            except Exception:
                pass


def _hp_bar(label: str, value: float, cap: float, color: str) -> str:
    try:
        pct = 0 if cap <= 0 else max(0, min(100, int(100 * float(value) / float(cap))))
    except Exception:
        pct = 0
    return (
        f"<div class='hp-row'><div class='hp-label'>{label}</div>"
        f"<div class='hp-bar'><div class='hp-fill' style='width:{pct}%; background:{color}'></div></div>"
        f"<div class='hp-val'>{value}</div></div>"
    )


def _ensure_trainer_css() -> None:
    css = """
    <style>
    .trainer-card {
        border:2px solid #9a9680; background:#f7f6ef; border-radius:6px; padding:12px;
        color:#2b2b2b; font-family: "Press Start 2P", monospace;
    }
    .hp-row { display:grid; grid-template-columns: 110px 1fr 70px; align-items:center; gap:10px; margin:8px 0; }
    .hp-label { font-weight:700; font-size:0.7rem; color:#2b2b2b; }
    .hp-val { font-size:0.7rem; color:#2b2b2b; text-align:right; }
    .hp-bar { height:10px; background:#2b2b2b; border-radius:6px; overflow:hidden; border:2px solid #2b2b2b; }
    .hp-fill { height:100%; border-radius:4px; }
    .medals-row { display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-top:6px; }
    .medals-row img { width: 32px; height:auto; filter:none; }
    .pokedex-card { border:2px solid #9a9680; background:#f7f6ef; border-radius:6px; padding:10px; color:#2b2b2b; font-family: "Press Start 2P", monospace; }
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

    colL, colR = st.columns([1, 3], gap="large")
    with colL:
        trainer = jugador or ""
        img = find_trainer_image(trainer)
        if img:
            st.image(img, caption=trainer, width=260)
        else:
            st.markdown("<div class='pokedex-card'>Sin retrato</div>", unsafe_allow_html=True)
    with colR:
        with st.container(border=False):
            st.markdown("<div class='trainer-card'>", unsafe_allow_html=True)
            region = st.session_state.get("trainer_region", {}).get(jugador or "", "Sinnoh")
            st.markdown(f"**Entrenador:** {jugador}    **Region:** {region}")
            html = "".join([
                _hp_bar("Monedas", monedas, 20, "#ffd54f"),
                _hp_bar("Puntos", puntos, 30, "#4fc3f7"),
            ])
            st.markdown(html, unsafe_allow_html=True)
            _render_medals_row(medallas)
            try:
                st.markdown(
                    "<div class='panel-ghost'><div class='title'>Muertos (Caja 18)"
                    f"</div><div class='value'>{muertos}</div></div>",
                    unsafe_allow_html=True,
                )
                st.caption(f"Revividos tras wipe: {revividos}")
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
            except Exception:
                pass
            st.markdown("</div>", unsafe_allow_html=True)
