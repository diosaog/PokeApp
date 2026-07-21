from __future__ import annotations

from html import escape
import json
import time
from typing import Any

import streamlit as st

from app.entrenadores.snapshot import get_trainer_snapshot
from app.season.config import current_season_version
from showdown_sprites import showdown_sprite_url
from storage import settings_get, settings_set
from utils import USERS


HALL_OF_FAME_KEY = "hall_of_fame_v1"
COMPETITION_TYPES = ("Liga", "Copa", "Torneo", "Copa Dobles", "Otro")


def _is_anto() -> bool:
    return str(st.session_state.get("user") or "").strip().lower() == "anto"


def _clean_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text or fallback


def _clean_team(values: Any) -> list[str]:
    if isinstance(values, list):
        source = values
    else:
        source = str(values or "").replace(";", "\n").replace(",", "\n").splitlines()
    out: list[str] = []
    for value in source:
        name = _clean_text(value)
        if name and name not in out:
            out.append(name)
    return out[:6]


def _safe_timestamp(value: Any) -> int:
    try:
        return max(0, int(value))
    except Exception:
        return int(time.time())


def _current_team_for(user: str) -> list[str]:
    try:
        snapshot = get_trainer_snapshot(user, allow_rebuild=False)
    except Exception:
        snapshot = {}
    team: list[str] = []
    for mon in list((snapshot or {}).get("team") or [])[:6]:
        species = _clean_text(mon.get("species_name") or mon.get("species"))
        if species:
            team.append(species)
    return team


def _coerce_entry(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    champion = _clean_text(raw.get("champion"))
    if not champion:
        return None
    created_at = _safe_timestamp(raw.get("created_at") or raw.get("id"))
    return {
        "id": _clean_text(raw.get("id"), str(created_at)),
        "competition": _clean_text(raw.get("competition"), "Liga"),
        "title": _clean_text(raw.get("title"), "Temporada archivada"),
        "season": _clean_text(raw.get("season"), "Temporada"),
        "champion": champion,
        "runner_up": _clean_text(raw.get("runner_up")),
        "team": _clean_team(raw.get("team")),
        "notes": _clean_text(raw.get("notes")),
        "created_at": created_at,
    }


def _load_entries() -> list[dict[str, Any]]:
    try:
        raw = settings_get(HALL_OF_FAME_KEY)
        parsed = json.loads(raw) if raw else []
    except Exception:
        parsed = []
    source = parsed if isinstance(parsed, list) else []
    entries = [_coerce_entry(item) for item in source]
    clean = [entry for entry in entries if entry]
    return sorted(clean, key=lambda item: int(item.get("created_at") or 0), reverse=True)


def _save_entries(entries: list[dict[str, Any]]) -> None:
    cleaned = [_coerce_entry(entry) for entry in entries]
    payload = [entry for entry in cleaned if entry]
    settings_set(HALL_OF_FAME_KEY, json.dumps(payload, ensure_ascii=False))


def _render_css() -> None:
    st.markdown(
        """
        <style>
        .hof-hero {
          position: relative;
          overflow: hidden;
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(260px, 0.55fr);
          gap: 14px;
          align-items: stretch;
          min-height: 140px;
          margin-bottom: 14px;
          padding: 16px;
          border: 1px solid var(--bw2-edge);
          background:
            linear-gradient(118deg, rgba(233,191,86,0.18) 0 32%, transparent 32% 100%),
            linear-gradient(180deg, rgba(43,52,64,0.97) 0%, rgba(16,22,30,0.97) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.09), 0 10px 26px rgba(0,0,0,0.24);
        }
        .hof-hero::before,
        .hof-card::before {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background:
            linear-gradient(180deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 100%) 0 0 / 100% 22px,
            linear-gradient(90deg, rgba(255,255,255,0.035) 0 1px, transparent 1px 100%) 0 0 / 26px 100%;
          opacity: .48;
        }
        .hof-hero-main,
        .hof-stat-grid,
        .hof-card > * {
          position: relative;
          z-index: 1;
        }
        .hof-kicker,
        .hof-title,
        .hof-stat span,
        .hof-stat strong,
        .hof-section-title,
        .hof-card-type,
        .hof-card-title,
        .hof-card-champion,
        .hof-team-pill {
          font-family: var(--font-pixel);
          text-transform: uppercase;
        }
        .hof-kicker {
          display: inline-block;
          padding: 5px 8px;
          border-left: 3px solid var(--accent);
          background: rgba(0,0,0,0.28);
          color: var(--bw2-text-soft);
          font-size: 9px;
        }
        .hof-title {
          margin-top: 12px;
          color: #ffffff;
          font-size: 31px;
          line-height: 1.05;
          text-shadow: 0 2px 0 rgba(0,0,0,0.5);
        }
        .hof-subtitle {
          margin-top: 10px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 20px;
          line-height: 1.16;
        }
        .hof-stat-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
        }
        .hof-stat {
          min-width: 0;
          min-height: 62px;
          padding: 9px 10px;
          border: 1px solid rgba(216,223,232,0.16);
          background: linear-gradient(180deg, rgba(9,15,22,0.64), rgba(8,12,18,0.88));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }
        .hof-stat span {
          display: block;
          color: var(--bw2-text-soft);
          font-size: 8px;
          line-height: 1.15;
        }
        .hof-stat strong {
          display: block;
          margin-top: 6px;
          color: #ffffff;
          font-size: 12px;
          line-height: 1.15;
          overflow-wrap: anywhere;
        }
        .hof-section-title {
          margin: 16px 0 8px;
          padding: 8px 10px;
          border-left: 4px solid var(--accent);
          background: linear-gradient(90deg, rgba(255,255,255,0.07), transparent 64%);
          color: #ffffff;
          font-size: 11px;
          line-height: 1.2;
        }
        .hof-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
        }
        .hof-card {
          position: relative;
          overflow: hidden;
          min-width: 0;
          min-height: 210px;
          padding: 12px;
          border: 1px solid var(--bw2-edge);
          background:
            linear-gradient(112deg, rgba(233,191,86,0.13) 0 35%, transparent 35% 100%),
            linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
        }
        .hof-card-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 10px;
          padding-bottom: 9px;
          border-bottom: 1px solid rgba(216,223,232,0.14);
        }
        .hof-card-type {
          color: #ffe7a6;
          font-size: 9px;
          line-height: 1.15;
        }
        .hof-card-title {
          margin-top: 6px;
          color: #ffffff;
          font-size: 12px;
          line-height: 1.2;
          overflow-wrap: anywhere;
        }
        .hof-card-season {
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1.1;
          text-align: right;
        }
        .hof-card-champion {
          margin-top: 12px;
          color: #ffffff;
          font-size: 16px;
          line-height: 1.15;
          overflow-wrap: anywhere;
        }
        .hof-card-runner,
        .hof-card-notes {
          margin-top: 6px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1.14;
        }
        .hof-team {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 12px;
        }
        .hof-team-pill {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          min-height: 32px;
          max-width: 100%;
          padding: 4px 7px;
          border: 1px solid rgba(216,223,232,0.16);
          background: rgba(8,12,18,0.48);
          color: #ffffff;
          font-size: 8px;
          line-height: 1;
        }
        .hof-team-pill img {
          width: 24px;
          height: 24px;
          object-fit: contain;
          image-rendering: pixelated;
        }
        .hof-empty {
          padding: 18px;
          border: 1px dashed rgba(216,223,232,0.32);
          background: linear-gradient(180deg, var(--bw2-panel-2), var(--bw2-panel));
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 20px;
          line-height: 1.15;
        }
        @media (max-width: 980px) {
          .hof-hero,
          .hof-grid {
            grid-template-columns: 1fr;
          }
        }
        @media (max-width: 620px) {
          .hof-hero {
            padding: 12px;
          }
          .hof-title {
            font-size: 24px;
          }
          .hof-stat-grid {
            grid-template-columns: 1fr;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _team_html(team: list[str]) -> str:
    if not team:
        return "<div class='hof-card-notes'>Equipo sin registrar.</div>"
    parts: list[str] = []
    for species in team[:6]:
        name = _clean_text(species)
        if not name:
            continue
        try:
            sprite = showdown_sprite_url(name, prefer_animated=False)
        except Exception:
            sprite = ""
        image = f"<img src='{escape(sprite)}' alt='{escape(name)}'/>" if sprite else ""
        parts.append(
            f"<span class='hof-team-pill'>{image}<span>{escape(name)}</span></span>"
        )
    return "<div class='hof-team'>" + "".join(parts) + "</div>"


def _entry_html(entry: dict[str, Any]) -> str:
    runner = _clean_text(entry.get("runner_up"))
    runner_html = (
        f"<div class='hof-card-runner'>Finalista: {escape(runner)}</div>"
        if runner
        else ""
    )
    notes = _clean_text(entry.get("notes"))
    notes_html = f"<div class='hof-card-notes'>{escape(notes)}</div>" if notes else ""
    return f"""
<div class="hof-card">
  <div class="hof-card-head">
    <div>
      <div class="hof-card-type">{escape(_clean_text(entry.get("competition"), "Liga"))}</div>
      <div class="hof-card-title">{escape(_clean_text(entry.get("title"), "Temporada archivada"))}</div>
    </div>
    <div class="hof-card-season">{escape(_clean_text(entry.get("season"), "Temporada"))}</div>
  </div>
  <div class="hof-card-champion">{escape(_clean_text(entry.get("champion")))}</div>
  {runner_html}
  {_team_html(_clean_team(entry.get("team")))}
  {notes_html}
</div>
"""


def _hero_html(entries: list[dict[str, Any]]) -> str:
    champions = {str(entry.get("champion") or "") for entry in entries if entry.get("champion")}
    latest = entries[0]["champion"] if entries else "-"
    current_version = current_season_version()
    return f"""
<div class="hof-hero">
  <div class="hof-hero-main">
    <div class="hof-kicker">Archivo historico</div>
    <div class="hof-title">Hall of Fame</div>
    <div class="hof-subtitle">Campeones de ligas y copas con el equipo que quedo registrado.</div>
  </div>
  <div class="hof-stat-grid">
    <div class="hof-stat">
      <span>Entradas</span>
      <strong>{len(entries)}</strong>
    </div>
    <div class="hof-stat">
      <span>Campeones unicos</span>
      <strong>{len(champions)}</strong>
    </div>
    <div class="hof-stat">
      <span>Ultimo campeon</span>
      <strong>{escape(str(latest))}</strong>
    </div>
    <div class="hof-stat">
      <span>Temporada activa</span>
      <strong>{escape(current_version.name)}</strong>
    </div>
  </div>
</div>
"""


def _render_entries(entries: list[dict[str, Any]]) -> None:
    st.markdown("<div class='hof-section-title'>Vitrina</div>", unsafe_allow_html=True)
    if not entries:
        st.markdown(
            (
                "<div class='hof-empty'>"
                "Todavia no hay campeones archivados. Cuando termine una liga o copa, "
                "Anto puede guardar aqui el campeon y su equipo."
                "</div>"
            ),
            unsafe_allow_html=True,
        )
        return
    html = (
        "<div class='hof-grid'>"
        + "".join(_entry_html(entry) for entry in entries)
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def _render_admin(entries: list[dict[str, Any]]) -> None:
    if not _is_anto():
        return
    st.markdown("<div class='hof-section-title'>Archivo Anto</div>", unsafe_allow_html=True)
    current_version = current_season_version()
    with st.form("hall_of_fame_add_entry"):
        c1, c2 = st.columns(2)
        with c1:
            competition = st.selectbox("Tipo", COMPETITION_TYPES)
            title = st.text_input("Titulo", value=current_version.name)
            season = st.text_input("Temporada", value=current_version.name)
            champion = st.selectbox("Campeon", list(USERS.keys()))
        with c2:
            runner_up = st.text_input("Finalista / segundo", value="")
            team_raw = st.text_area(
                "Equipo campeon",
                value="",
                placeholder="Uno por linea. Si lo dejas vacio, intenta usar el equipo actual guardado.",
                height=148,
            )
            notes = st.text_area("Notas", value="", height=80)

        submitted = st.form_submit_button("Guardar entrada", use_container_width=True)
        if submitted:
            team = _clean_team(team_raw)
            if not team:
                team = _current_team_for(champion)
            if not _clean_text(champion):
                st.error("El campeon es obligatorio.")
                return
            entry_id = str(int(time.time() * 1000))
            entries.insert(
                0,
                {
                    "id": entry_id,
                    "competition": competition,
                    "title": title,
                    "season": season,
                    "champion": champion,
                    "runner_up": runner_up,
                    "team": team,
                    "notes": notes,
                    "created_at": int(time.time()),
                },
            )
            _save_entries(entries)
            st.success("Entrada guardada en el Hall of Fame.")
            st.rerun()

    if entries:
        with st.expander("Eliminar entrada", expanded=False):
            labels = [
                f"{entry.get('competition')} - {entry.get('champion')} - {entry.get('title')}"
                for entry in entries
            ]
            selected = st.selectbox(
                "Entrada",
                list(range(len(entries))),
                format_func=lambda i: labels[i],
            )
            if st.button("Eliminar entrada seleccionada", use_container_width=True):
                entries.pop(int(selected))
                _save_entries(entries)
                st.success("Entrada eliminada.")
                st.rerun()


def render_hall_of_fame() -> None:
    _render_css()
    entries = _load_entries()
    st.markdown(_hero_html(entries), unsafe_allow_html=True)
    _render_entries(entries)
    _render_admin(entries)
