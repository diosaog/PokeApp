from __future__ import annotations

import json
from pathlib import Path
from html import escape
import streamlit as st

from app.entrenadores.bridge import try_auto_load_bridge
from app.entrenadores.cache import cached_box_meta_quick, cached_has_pc_data, cached_team, preload_entrenadores_cache
from app.entrenadores.detail import pokemon_detail_panel
from app.entrenadores.inventory import _purchases_inventory_ui, _inventory_cached, _render_purchase_cards, _category_for_item
from app.entrenadores.pokepaste import ensure_pokepaste_state
from app.entrenadores.profile import find_trainer_image
from app.entrenadores.state import ensure_local_save_for
from app.entrenadores.summary import trainer_summary_with_portrait_ui
from app.entrenadores.trainer_flags import (
    format_trainer_with_flags,
    is_trainer_retired,
    set_trainer_retired,
    sync_trainer_robbed_flags_from_history,
)
from app.entrenadores.boxes import boxes_grid_ui
from app.discord_notify import discord_notifications_enabled, notify_team_locked_async
from app.interfaz.media import image_data_uri
from app.ui.team_grid import team_grid_ui
from app.interfaz.theme import apply_platinum_ui
from app.liga.context import current_jornada
from app.liga.ranking import clear_ranking_caches
from app.tienda.money import clear_money_caches
from conex_pkhex import PKHeXRuntime, extract_team, get_bridge_path, open_sav_cached
from storage import (
    get_current_save_for_user,
    get_team_lock,
    list_saves_by_user,
    settings_get,
    upsert_team_lock,
)
from utils import DEFAULT_DLL_HINT, USERS, active_users, list_user_saves, users_with_retired_last


INVENTORY_TABS_CSS = """
<style>
div[data-testid="stTabs"] div[data-baseweb="tab-list"],
div[data-testid="stTabs"] [role="tablist"] {
  gap: 8px !important;
  flex-wrap: wrap !important;
  align-items: stretch !important;
}
div[data-testid="stTabs"] div[data-baseweb="tab-list"] button:first-of-type,
div[data-testid="stTabs"] [role="tablist"] [role="tab"]:first-of-type {
  flex: 0 0 176px !important;
  width: 176px !important;
  min-width: 176px !important;
  justify-content: center !important;
  padding-left: 14px !important;
  padding-right: 14px !important;
  white-space: nowrap !important;
}
div[data-testid="stTabs"] div[data-baseweb="tab-list"] button:first-of-type *,
div[data-testid="stTabs"] [role="tablist"] [role="tab"]:first-of-type * {
  width: 100%;
  text-align: center;
  white-space: nowrap !important;
}
</style>
"""

TRAINERS_PAGE_CSS = """
<style>
.trainers-hero {
  position: relative;
  min-height: 228px;
  overflow: hidden;
  padding: 18px;
  border: 1px solid rgba(216,223,232,0.24);
  background:
    linear-gradient(135deg, rgba(98,200,255,0.22), transparent 38%),
    linear-gradient(315deg, rgba(255,199,92,0.13), transparent 42%),
    linear-gradient(180deg, var(--bw2-panel-2), var(--bw2-panel));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.09), 0 14px 34px rgba(0,0,0,0.26);
  clip-path: polygon(16px 0, 100% 0, 100% calc(100% - 16px), calc(100% - 16px) 100%, 0 100%, 0 16px);
}
.trainers-hero:after {
  content: "";
  position: absolute;
  right: -58px;
  bottom: -72px;
  width: 220px;
  height: 220px;
  border-radius: 50%;
  border: 26px solid rgba(255,255,255,0.07);
  box-shadow: inset 0 0 0 20px rgba(0,0,0,0.16);
}
.trainers-hero-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 124px minmax(0, 1fr);
  gap: 16px;
  align-items: center;
}
.trainers-portrait-xl {
  width: 124px;
  height: 124px;
  display: grid;
  place-items: center;
  overflow: hidden;
  border: 1px solid rgba(216,223,232,0.34);
  background: linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 12px 28px rgba(0,0,0,0.24);
}
.trainers-portrait-xl img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.trainers-pokeball {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  position: relative;
  background: linear-gradient(180deg, #e95151 0 48%, #131820 48% 52%, #f1f5f8 52% 100%);
  border: 3px solid #131820;
  box-shadow: inset 0 0 0 2px rgba(255,255,255,0.12);
}
.trainers-pokeball:after {
  content: "";
  position: absolute;
  left: 50%;
  top: 50%;
  width: 14px;
  height: 14px;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: #f1f5f8;
  border: 3px solid #131820;
}
.trainers-title {
  color: #fff;
  font-family: var(--font-pixel);
  font-size: 22px;
  line-height: 1.2;
  text-transform: uppercase;
  letter-spacing: 0;
}
.trainers-subtitle {
  margin-top: 7px;
  color: var(--bw2-text-soft);
  font-size: 22px;
  line-height: 1.08;
}
.trainers-chip-row {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
  margin-top: 14px;
}
.trainers-chip {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 4px 9px;
  border: 1px solid rgba(216,223,232,0.28);
  background: rgba(255,255,255,0.06);
  color: #fff;
  font-family: var(--font-pixel);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0;
}
.trainers-chip--ok { border-color: rgba(88,209,142,0.8); color: #aaf0c8; }
.trainers-chip--warn { border-color: rgba(242,107,97,0.85); color: #ffb4ae; }
.trainers-picker {
  min-height: 228px;
  padding: 14px;
  border: 1px solid rgba(216,223,232,0.22);
  background:
    linear-gradient(180deg, rgba(255,255,255,0.05), transparent 44%),
    linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 14px 30px rgba(0,0,0,0.22);
}
.trainers-panel-label {
  color: #fff;
  font-family: var(--font-pixel);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0;
}
.trainers-panel-copy {
  margin: 7px 0 10px;
  color: var(--bw2-text-soft);
  font-size: 18px;
  line-height: 1.08;
}
.trainers-status-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin: 12px 0 16px;
}
.trainers-stat {
  min-height: 94px;
  padding: 11px;
  border: 1px solid rgba(216,223,232,0.2);
  background: linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
}
.trainers-stat-label {
  color: var(--bw2-text-dim);
  font-family: var(--font-pixel);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0;
}
.trainers-stat-value {
  margin-top: 9px;
  color: #fff;
  font-family: var(--font-pixel);
  font-size: 13px;
  line-height: 1.2;
  overflow-wrap: anywhere;
  letter-spacing: 0;
}
.trainers-stat-detail {
  margin-top: 6px;
  color: var(--bw2-text-soft);
  font-size: 18px;
  line-height: 1.08;
  overflow-wrap: anywhere;
}
.trainers-section-title {
  display: inline-block;
  margin: 8px 0 10px;
  padding: 8px 11px;
  border: 1px solid var(--bw2-edge-strong);
  background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
  color: #fff;
  font-family: var(--font-pixel);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0;
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
}
.trainers-lock-panel {
  margin-bottom: 12px;
  padding: 12px;
  border: 1px solid rgba(216,223,232,0.2);
  background: linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen));
}
.trainers-lock-main {
  color: #fff;
  font-family: var(--font-pixel);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0;
}
.trainers-lock-sub {
  margin-top: 6px;
  color: var(--bw2-text-soft);
  font-size: 18px;
  line-height: 1.08;
}
@media (max-width: 960px) {
  .trainers-status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 680px) {
  .trainers-hero-grid { grid-template-columns: 1fr; }
  .trainers-status-grid { grid-template-columns: 1fr; }
}
</style>
"""


TRAINERS_STORAGE_CSS = """
<style>
.slot.team-slot-card {
  min-height: 222px !important;
  margin: 6px 0 8px !important;
  padding: 10px 10px 12px !important;
  display: flex !important;
  flex-direction: column !important;
  align-items: center !important;
  justify-content: flex-start !important;
  overflow: hidden !important;
}
.slot.team-slot-card .badges {
  width: 100% !important;
  height: 22px !important;
  margin: 0 0 5px !important;
}
.slot.team-slot-card .pill {
  min-height: 18px !important;
  padding: 2px 6px !important;
  border-radius: 999px !important;
  font-family: var(--font-ui) !important;
  font-size: 10px !important;
  font-weight: 800 !important;
  line-height: 1 !important;
}
.slot.team-slot-card > img {
  width: min(100%, 142px) !important;
  height: 118px !important;
  margin: 4px auto 8px !important;
  display: block !important;
  object-fit: contain !important;
  image-rendering: pixelated !important;
}
.slot.team-slot-card .title,
.slot.team-slot-card .sub {
  width: 100% !important;
  overflow: hidden !important;
  text-align: center !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.slot.team-slot-card .title {
  margin-top: 0 !important;
  font-size: 11px !important;
  line-height: 1.12 !important;
}
.slot.team-slot-card .sub {
  min-height: 18px !important;
  margin-top: 2px !important;
  font-size: 15px !important;
  line-height: 1.16 !important;
}
.slot.team-slot-card .types {
  width: 100% !important;
  min-height: 22px !important;
  margin-top: 8px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 6px !important;
  flex-wrap: nowrap !important;
  overflow: hidden !important;
}
.slot.team-slot-card .slot-type-badge.poke-type-chip {
  width: 94px !important;
  min-width: 0 !important;
  max-width: 94px !important;
  height: 19px !important;
  min-height: 19px !important;
  flex: 0 1 94px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  overflow: hidden !important;
  border: 0 !important;
  border-radius: 999px !important;
  background: transparent !important;
  box-shadow: none !important;
}
.slot.team-slot-card .slot-type-badge.poke-type-chip img,
.slot.team-slot-card .slot-type-badge .poke-type-full-img,
.slot.team-slot-card .slot-type-badge .poke-type-icon-img {
  width: 94px !important;
  max-width: 94px !important;
  height: 19px !important;
  max-height: 19px !important;
  margin: 0 !important;
  display: block !important;
  object-fit: contain !important;
  image-rendering: auto !important;
  filter: none !important;
}
.slot.team-slot-card .slot-type-badge.poke-type-chip.uses-fallback {
  width: fit-content !important;
  padding: 0 9px !important;
  border: 1px solid color-mix(in srgb, var(--type-color) 48%, transparent) !important;
  background: color-mix(in srgb, var(--type-color) 22%, transparent) !important;
}
.slot.team-slot-card .slot-type-badge .poke-type-fallback {
  font-family: var(--font-ui) !important;
  font-size: 10px !important;
  font-weight: 750 !important;
  letter-spacing: 0.02em !important;
}
.slot.team-slot-card .shield-chip,
.slot.team-slot-card .rob-chip {
  min-height: 20px !important;
  padding: 0 8px !important;
  border-radius: 999px !important;
  font-family: var(--font-ui) !important;
  font-size: 10px !important;
  font-weight: 800 !important;
}
div[data-testid="column"]:has(.slot.team-slot-card) .stButton {
  display: flex !important;
  justify-content: center !important;
  margin-top: 7px !important;
}
div[data-testid="column"]:has(.slot.team-slot-card) .stButton > button {
  width: auto !important;
  min-width: 0 !important;
  min-height: 34px !important;
  padding: 0 13px !important;
  border-radius: 999px !important;
}
div[data-testid="column"]:has(.slot.team-slot-card) .stButton > button p {
  font-size: 11px !important;
  font-weight: 800 !important;
}
.champ-box-page-head {
  min-height: 40px !important;
  display: flex !important;
  align-items: center !important;
}
.champ-box-page-head h3 {
  margin: 0 !important;
  color: var(--bw2-text) !important;
  -webkit-text-fill-color: var(--bw2-text) !important;
  font-size: 22px !important;
  font-weight: 900 !important;
}
.champ-box-grid-shell {
  margin-top: 8px !important;
  position: relative !important;
  overflow: hidden !important;
  padding: 12px !important;
  border: 1px solid rgba(216,223,232,0.18) !important;
  border-radius: 16px !important;
  background:
    linear-gradient(135deg, rgba(69,209,255,0.08), transparent 42%),
    linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015)),
    rgba(10,16,29,0.94) !important;
}
.champ-box-grid-shell::before {
  content: "PC" !important;
  position: absolute !important;
  right: 16px !important;
  top: 2px !important;
  color: rgba(255,255,255,0.035) !important;
  -webkit-text-fill-color: rgba(255,255,255,0.035) !important;
  font-size: 58px !important;
  font-weight: 950 !important;
  line-height: 1 !important;
  pointer-events: none !important;
}
.champ-box-grid-toolbar {
  position: relative !important;
  z-index: 1 !important;
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) auto !important;
  gap: 10px !important;
  align-items: center !important;
  margin-bottom: 8px !important;
}
.champ-box-grid-toolbar strong {
  display: block !important;
  color: var(--bw2-text) !important;
  -webkit-text-fill-color: var(--bw2-text) !important;
  font-size: 16px !important;
  font-weight: 900 !important;
  line-height: 1.1 !important;
}
.champ-box-meta {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: flex-end !important;
  gap: 7px !important;
  flex-wrap: wrap !important;
}
.champ-box-meta span {
  min-height: 23px !important;
  display: inline-flex !important;
  align-items: center !important;
  padding: 0 8px !important;
  border: 1px solid rgba(216,223,232,0.12) !important;
  border-radius: 999px !important;
  background: rgba(255,255,255,0.035) !important;
  color: var(--bw2-text-soft) !important;
  -webkit-text-fill-color: var(--bw2-text-soft) !important;
  font-size: 10px !important;
  font-weight: 800 !important;
  font-variant-numeric: tabular-nums !important;
}
.champ-box-occupancy {
  position: relative !important;
  z-index: 1 !important;
  display: grid !important;
  grid-template-columns: 1fr !important;
  margin: 0 0 10px !important;
}
.champ-box-occupancy-bar {
  height: 4px !important;
  overflow: hidden !important;
  border-radius: 999px !important;
  background: rgba(255,255,255,0.08) !important;
}
.champ-box-occupancy-bar span {
  display: block !important;
  width: var(--box-fill, 0%) !important;
  height: 100% !important;
  border-radius: inherit !important;
  background: linear-gradient(90deg, var(--accent), var(--champion-cyan)) !important;
}
.champ-box-occupancy-dots,
.champ-box-types,
.champ-box-species {
  display: none !important;
}
.champ-box-grid {
  position: relative !important;
  z-index: 1 !important;
  display: grid !important;
  grid-template-columns: repeat(6, minmax(82px, 1fr)) !important;
  gap: 8px !important;
  align-items: stretch !important;
}
.champ-box-tile-link {
  display: block !important;
  min-width: 0 !important;
  color: inherit !important;
  text-decoration: none !important;
}
.champ-box-tile {
  position: relative !important;
  min-height: 98px !important;
  aspect-ratio: 1 / 0.85 !important;
  padding: 7px 6px 6px !important;
  display: grid !important;
  grid-template-rows: 16px minmax(48px, 1fr) auto 4px !important;
  gap: 2px !important;
  align-items: center !important;
  justify-items: center !important;
  overflow: hidden !important;
  border: 1px solid rgba(216,223,232,0.14) !important;
  border-radius: 11px !important;
  background:
    radial-gradient(circle at 50% 45%, color-mix(in srgb, var(--box-glow, var(--accent)) 18%, transparent), transparent 58%),
    linear-gradient(135deg, rgba(255,255,255,0.055) 0 45%, rgba(255,255,255,0.018) 45% 100%),
    rgba(17,27,44,0.96) !important;
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease !important;
}
.champ-box-tile-link:hover .champ-box-tile {
  transform: translateY(-2px) !important;
  border-color: rgba(69,209,255,0.42) !important;
}
.champ-box-tile::before {
  content: "" !important;
  position: absolute !important;
  inset: 4px !important;
  z-index: 0 !important;
  border: 1px solid rgba(255,255,255,0.035) !important;
  border-radius: 8px !important;
  background: linear-gradient(135deg, transparent 0 62%, rgba(255,255,255,0.045) 62% 100%) !important;
  pointer-events: none !important;
}
.champ-box-tile::after {
  content: "" !important;
  position: absolute !important;
  left: 50% !important;
  top: 57% !important;
  z-index: 0 !important;
  width: 42px !important;
  height: 8px !important;
  transform: translate(-50%, -50%) !important;
  border-radius: 50% !important;
  background: rgba(0,0,0,0.22) !important;
  filter: blur(4px) !important;
  pointer-events: none !important;
}
.champ-box-slot-no,
.champ-box-level,
.champ-box-name,
.champ-box-type-rails,
.champ-box-sprite-stage,
.champ-box-empty-mark {
  position: relative !important;
  z-index: 1 !important;
}
.champ-box-slot-no {
  position: absolute !important;
  top: 6px !important;
  right: 7px !important;
  color: rgba(255,255,255,0.28) !important;
  -webkit-text-fill-color: rgba(255,255,255,0.28) !important;
  font-size: 9px !important;
  font-weight: 900 !important;
  font-variant-numeric: tabular-nums !important;
}
.champ-box-level {
  justify-self: start !important;
  min-height: 15px !important;
  display: inline-flex !important;
  align-items: center !important;
  padding: 0 5px !important;
  border-radius: 999px !important;
  background: rgba(69,209,255,0.14) !important;
  color: var(--bw2-text) !important;
  -webkit-text-fill-color: var(--bw2-text) !important;
  font-size: 9px !important;
  font-weight: 850 !important;
  font-variant-numeric: tabular-nums !important;
}
.champ-box-sprite-stage {
  width: 100% !important;
  min-height: 50px !important;
  display: grid !important;
  place-items: center !important;
}
.champ-box-tile img {
  width: 64px !important;
  height: 58px !important;
  max-width: 64px !important;
  max-height: 58px !important;
  margin: 0 !important;
  display: block !important;
  object-fit: contain !important;
  image-rendering: pixelated !important;
  filter: drop-shadow(0 6px 7px rgba(0,0,0,0.34)) !important;
  transition: transform 150ms ease, filter 150ms ease !important;
}
.champ-box-tile-link:hover .champ-box-tile img,
.champ-box-tile.is-selected img {
  transform: translateY(-2px) scale(1.03) !important;
}
.champ-box-name {
  width: 100% !important;
  display: block !important;
  overflow: hidden !important;
  color: var(--bw2-text) !important;
  -webkit-text-fill-color: var(--bw2-text) !important;
  font-size: 11px !important;
  font-weight: 850 !important;
  line-height: 1.1 !important;
  text-align: center !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}
.champ-box-type-rails {
  width: min(54px, 80%) !important;
  height: 4px !important;
  margin-top: 1px !important;
  display: grid !important;
  grid-template-columns: repeat(auto-fit, minmax(0, 1fr)) !important;
  gap: 3px !important;
}
.champ-box-type-rails span {
  height: 3px !important;
  border-radius: 999px !important;
  background: var(--rail-color, rgba(255,255,255,0.12)) !important;
}
.champ-box-tile.is-selected {
  border-color: rgba(69,209,255,0.74) !important;
  box-shadow: inset 0 0 0 1px rgba(69,209,255,0.34), 0 0 0 3px rgba(69,209,255,0.1) !important;
}
.champ-box-tile-empty {
  opacity: 0.42 !important;
  border-style: dashed !important;
  border-color: rgba(255,255,255,0.07) !important;
  background:
    radial-gradient(circle at 50% 50%, rgba(255,255,255,0.025), transparent 42%),
    rgba(255,255,255,0.012) !important;
}
.champ-box-tile-empty::after {
  display: none !important;
}
.champ-box-empty-mark {
  width: 8px !important;
  height: 8px !important;
  border: 0 !important;
  border-radius: 50% !important;
  background: rgba(255,255,255,0.18) !important;
  box-shadow: none !important;
}
@media (max-width: 960px) {
  .champ-box-grid { grid-template-columns: repeat(4, minmax(72px, 1fr)) !important; }
  .slot.team-slot-card .types { flex-wrap: wrap !important; }
}
@media (max-width: 680px) {
  .champ-box-grid { grid-template-columns: repeat(3, minmax(64px, 1fr)) !important; }
}
</style>
"""


def _render_trainers_page_css() -> None:
    st.markdown(TRAINERS_PAGE_CSS, unsafe_allow_html=True)
    st.markdown(TRAINERS_STORAGE_CSS, unsafe_allow_html=True)


def _safe_mtime(path: str | Path | None) -> float | None:
    try:
        return Path(path).stat().st_mtime if path else None
    except Exception:
        return None


def _trainer_portrait_uri(trainer: str) -> str:
    image_path = find_trainer_image(trainer)
    return image_data_uri(image_path, _safe_mtime(image_path), min_bytes=256)


def _pokeball_placeholder() -> str:
    return "<div class='trainers-pokeball'></div>"


def _chip(label: str, *, ok: bool = True) -> str:
    cls = "trainers-chip--ok" if ok else "trainers-chip--warn"
    return f"<span class='trainers-chip {cls}'>{escape(label)}</span>"


def _stat(label: str, value: str, detail: str) -> str:
    detail_html = (
        f"<div class='trainers-stat-detail'>{escape(detail)}</div>" if detail else ""
    )
    return (
        "<div class='trainers-stat'>"
        f"<div class='trainers-stat-label'>{escape(label)}</div>"
        f"<div class='trainers-stat-value'>{escape(value)}</div>"
        f"{detail_html}"
        "</div>"
    )


def _save_snapshot(trainer: str) -> tuple[str, str, Path | None]:
    try:
        ensure_local_save_for(trainer)
    except Exception:
        pass
    try:
        saves = list_user_saves(trainer) if trainer else []
    except Exception:
        saves = []
    active_path = saves[0] if saves else None
    if active_path:
        return Path(active_path).name, "Save detectado", Path(active_path)
    return "Sin save", "Subida pendiente", None


def _team_lock_snapshot(trainer: str) -> tuple[str, str, bool]:
    jornada = current_jornada()
    try:
        lock = get_team_lock(jornada, trainer)
    except Exception:
        lock = None
    if not lock or not lock.get("team"):
        return "Sin fijar", f"Jornada {jornada}", False
    status = "Fijado tarde" if lock.get("is_late") else "Fijado"
    return status, _fmt_lock_time(int(lock.get("locked_at") or 0)), True


def _inventory_snapshot(trainer: str) -> tuple[str, str]:
    try:
        inv = _inventory_cached(trainer)
    except Exception:
        inv = []
    available = [row for row in inv if len(row) < 5 or row[4] != "used"]
    comodines = [
        row
        for row in available
        if len(row) > 1 and _category_for_item(str(row[1])) == "Comodines"
    ]
    return f"{len(available)} activos", f"{len(comodines)} comodines"


def _render_trainer_header(
    *,
    trainer: str,
    current_user: str,
    active_path: Path | None,
) -> None:
    portrait = _trainer_portrait_uri(trainer)
    avatar = (
        f"<img src='{portrait}' alt='Retrato de {escape(trainer)}'/>"
        if portrait
        else _pokeball_placeholder()
    )
    own_profile = trainer == current_user
    retired = is_trainer_retired(trainer)
    save_label = Path(active_path).name if active_path else "Sin save local"
    chips = [
        _chip("Tu perfil" if own_profile else "Consulta", ok=True),
        _chip("Retirado" if retired else "Activo", ok=not retired),
        _chip(save_label, ok=bool(active_path)),
    ]
    st.markdown(
        (
            "<div class='trainers-hero'>"
            "<div class='trainers-hero-grid'>"
            f"<div class='trainers-portrait-xl'>{avatar}</div>"
            "<div>"
            f"<div class='trainers-title'>{escape(trainer or '-')}</div>"
            f"<div class='trainers-chip-row'>{''.join(chips)}</div>"
            "</div>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_quick_status(
    *,
    trainer: str,
    current_user: str,
    active_path: Path | None,
) -> None:
    if active_path:
        save_value = Path(active_path).name
        save_detail = "Save detectado"
    else:
        save_value = "Sin save"
        save_detail = "Subida pendiente"
    lock_value, lock_detail, locked = _team_lock_snapshot(trainer)
    inv_value, inv_detail = _inventory_snapshot(trainer)
    own = trainer == current_user
    retired = is_trainer_retired(trainer)
    st.markdown(
        (
            "<div class='trainers-status-grid'>"
            + _stat("Save", save_value, save_detail)
            + _stat("Equipo jornada", lock_value, lock_detail)
            + _stat("Inventario", inv_value, inv_detail)
            + _stat(
                "Permisos",
                "Completo" if own and not retired else "Lectura",
                "",
            )
            + "</div>"
        ),
        unsafe_allow_html=True,
    )


def _notify_trainer_retired_async(trainer: str, by_user: str | None = None) -> None:
    try:
        from app import discord_notify

        enabled = getattr(discord_notify, "discord_notifications_enabled", None)
        if callable(enabled) and not enabled():
            return

        existing = getattr(discord_notify, "notify_trainer_retired_async", None)
        if callable(existing):
            existing(trainer=trainer, by_user=by_user)
            return

        import threading

        def _send() -> None:
            try:
                fields = []
                if by_user:
                    fields.append(
                        {
                            "name": "Registrado por",
                            "value": str(by_user),
                            "inline": True,
                        }
                    )
                discord_notify._post_webhook(
                    {
                        "embeds": [
                            discord_notify._embed(
                                title="Entrenador retirado",
                                description=(
                                    f"{trainer} se ha retirado de la liga. "
                                    "Sus resultados anteriores se conservan, pero deja de contar "
                                    "para jornadas, puntos, monedas y sistemas activos."
                                ),
                                color=0x95A5A6,
                                fields=fields,
                            )
                        ]
                    }
                )
            except Exception:
                pass

        threading.Thread(target=_send, daemon=True).start()
    except Exception:
        pass


def _save_meta_for_lock(user: str, save_path: Path | None) -> tuple[int | None, str | None]:
    if not user or not save_path:
        return None, None
    try:
        current = get_current_save_for_user(user)
        if current and str(current[1]) == save_path.name:
            return int(current[0]), str(current[3] or "")
    except Exception:
        pass
    try:
        for row in list_saves_by_user(user, limit=20):
            if str(row[1]) == save_path.name:
                return int(row[0]), str(row[3] or "")
    except Exception:
        pass
    return None, None


def _fmt_lock_time(ts: int) -> str:
    if not ts:
        return "-"
    try:
        from datetime import datetime

        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return "-"


def _render_team_lock_controls(
    *,
    team: list[dict],
    current_user: str,
    save_path: Path | None,
) -> None:
    jornada = current_jornada()
    lock = get_team_lock(jornada, current_user)
    if lock:
        status = "Fijado tarde" if lock.get("is_late") else "Fijado"
        lock_detail = (
            f"Jornada {jornada} - {status} - "
            f"{_fmt_lock_time(int(lock.get('locked_at') or 0))}"
        )
    else:
        status = "Sin fijar"
        lock_detail = f"Jornada {jornada} - pendiente"

    st.markdown(
        (
            "<div class='trainers-lock-panel'>"
            f"<div class='trainers-lock-main'>Equipo fijado: {escape(status)}</div>"
            f"<div class='trainers-lock-sub'>{escape(lock_detail)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    disabled = len(team) != 6
    if disabled:
        st.warning("Necesitas 6 Pokemon en el equipo para fijarlo para combates.")

    if st.button(
        f"Fijar Equipo Para la Jornada {jornada}",
        disabled=disabled,
        use_container_width=True,
        key=f"lock_team_{current_user}_{jornada}",
    ):
        save_id, save_sha = _save_meta_for_lock(current_user, save_path)
        is_late = bool(st.session_state.get("league_active"))
        saved = upsert_team_lock(
            jornada=jornada,
            user=current_user,
            team=list(team)[:6],
            save_id=save_id,
            save_sha256=save_sha,
            is_late=is_late,
        )
        if not saved:
            st.error("No se pudo fijar el equipo. Revisa Supabase o vuelve a intentarlo.")
            return
        if discord_notifications_enabled():
            notify_team_locked_async(user=current_user, jornada=jornada, is_late=is_late)
        st.success(
            f"Equipo fijado para Jornada {jornada}"
            + (" (tarde)." if is_late else ".")
        )
        st.rerun()


def page_entrenadores_setup() -> None:
    is_own_profile = st.session_state.get("trainer_selected") == st.session_state.get("user")
    if not is_own_profile:
        return
    with st.expander(
        "Configurar lector de saves DS (Bridge)",
        expanded=not st.session_state.get("pkhex_loaded", False),
    ):
        bridge_hint = st.session_state.get("pkhex_dll_path") or DEFAULT_DLL_HINT
        exe_in = st.text_input("Ruta a PKHeXBridge.exe (o carpeta)", value=bridge_hint)
        st.session_state.pkhex_mode = "auto"
        if st.button("Cargar lector", type="primary"):
            try:
                PKHeXRuntime.load(exe_in)
                st.session_state.pkhex_loaded = True
                st.session_state.pkhex_dll_path = exe_in
                st.success("Lector cargado correctamente.")
            except Exception as e:
                st.session_state.pkhex_loaded = False
                st.error(f"No se pudo cargar el lector: {e}")


def page_entrenadores_view() -> None:
    trainer = st.session_state.get("trainer_selected")
    current_user = st.session_state.get("user")
    is_own_profile = trainer == current_user
    current_user_retired = is_trainer_retired(current_user)
    ensure_pokepaste_state()

    ensure_local_save_for(trainer or "")

    if is_trainer_retired(trainer):
        st.warning("Entrenador retirado.")

    saves = list_user_saves(trainer) if trainer else []
    active_path = saves[0] if saves else None
    if not st.session_state.get("pkhex_loaded", False):
        if is_own_profile:
            st.warning("Configura el lector (bridge) para poder leer el save.")
        else:
            st.info("El guardado no esta disponible en este momento.")
        return

    if not active_path:
        if is_own_profile:
            st.warning("Sube un .sav o .dsv en la pestana Saves.")
        else:
            st.info("Este entrenador no tiene guardados.")
        return

    try:
        save_path = Path(active_path)
        if not save_path.exists():
            st.error("El archivo del entrenador no existe.")
            return
        st.session_state.active_sav_path = str(save_path)
        mtime = save_path.stat().st_mtime
        sav_json = open_sav_cached(save_path)
    except Exception as e:
        st.error(f"No se pudo abrir el guardado: {e}")
        try:
            st.caption(f"Ruta del bridge actual: {get_bridge_path() or ''}")
        except Exception:
            pass
        return

    try:
        box_count, box_names = cached_box_meta_quick(str(save_path), mtime)
    except Exception:
        box_count, box_names = 0, []
    try:
        pc_ok = cached_has_pc_data(str(save_path), mtime)
    except Exception:
        pc_ok = False
    preload_entrenadores_cache(str(save_path), mtime, box_count)

    st.markdown("---")
    col_stats, col_inv = st.columns([1.35, 1.1], gap="large")
    with col_stats:
        st.markdown("<div class='trainers-section-title'>Resumen</div>", unsafe_allow_html=True)
        trainer_summary_with_portrait_ui(
            sav_json,
            box_count,
            is_own_profile=is_own_profile,
            save_path=str(save_path),
        )
    with col_inv:
        st.markdown(
            "<div class='trainers-section-title'>Inventario</div>",
            unsafe_allow_html=True,
        )
        st.markdown(INVENTORY_TABS_CSS, unsafe_allow_html=True)
        tab_shop, tab_como = st.tabs(["Compras (tienda)", "Comodines"])
        with tab_shop:
            _purchases_inventory_ui(trainer or "", allow_use=False)
        with tab_como:
            inv = _inventory_cached(trainer or "")
            comos = [r for r in inv if _category_for_item(r[1]) == "Comodines"] if inv else []
            _render_purchase_cards(
                comos,
                "Comodines",
                key_prefix="comos",
                allow_use=is_own_profile and not current_user_retired,
            )

        ctx = st.session_state.get("redeem_ctx")
        if ctx and not current_user_retired:
            try:
                from tienda2 import _render_redeem_flow  # wrapper keeps API
                _render_redeem_flow(ctx, current_user)
            except Exception:
                st.error("No se pudo cargar el flujo de uso de comodines. Ve a la pestana Tienda.")
        elif ctx and current_user_retired:
            st.session_state.pop("redeem_ctx", None)
            st.warning("Los entrenadores retirados no pueden usar comodines.")

    st.markdown("---")
    try:
        active_spath = str(save_path) if save_path else None
        if active_spath:
            team = cached_team(active_spath, mtime)
        else:
            team = extract_team(sav_json) or []
    except Exception:
        team = []
    if is_own_profile and not current_user_retired:
        _render_team_lock_controls(
            team=list(team or [])[:6],
            current_user=str(current_user or ""),
            save_path=Path(save_path) if save_path else None,
        )
    team_grid_ui(team)
    detail_slot = st.empty()
    boxes_grid_ui(sav_json, box_count, box_names, save_path=str(save_path), pc_ok=pc_ok, mtime=mtime)
    with detail_slot:
        pokemon_detail_panel()


def _render_retirement_admin() -> None:
    current_user = str(st.session_state.get("user") or "")
    if current_user.strip().lower() != "anto":
        return

    st.markdown("---")
    with st.expander("Gestion de abandonos", expanded=False):
        league_active = False
        try:
            raw_state = settings_get("league_state")
            if raw_state:
                league_active = bool(json.loads(raw_state).get("active"))
        except Exception:
            league_active = bool(st.session_state.get("league_active"))
        if league_active:
            st.warning("Cierra la jornada antes de marcar un abandono.")
        candidates = [user for user in USERS.keys() if not is_trainer_retired(user)]
        if not candidates:
            st.caption("No quedan entrenadores disponibles para retirar.")
            return
        target = st.selectbox(
            "Entrenador que abandona",
            candidates,
            format_func=format_trainer_with_flags,
            key="retirement_target",
        )
        confirm = st.text_input(
            "Escribe RETIRAR para confirmar",
            key="retirement_confirm",
        )
        if st.button(
            "Marcar abandono",
            disabled=(confirm != "RETIRAR") or league_active,
            use_container_width=True,
            key="retirement_submit",
        ):
            try:
                set_trainer_retired(str(target), by_user=current_user)
                clear_money_caches()
                clear_ranking_caches()
                _notify_trainer_retired_async(str(target), by_user=current_user)
                st.success(f"{target} marcado como retirado.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo marcar el abandono: {e}")


def page_entrenadores() -> None:
    apply_platinum_ui("Entrenadores")
    _render_trainers_page_css()

    try:
        sync_trainer_robbed_flags_from_history(list(active_users().keys()))
    except Exception:
        pass

    users = users_with_retired_last(USERS)
    try:
        active = st.session_state.get("user")
        cur = st.session_state.get("trainer_selected")
        last_login_user = st.session_state.get("_trainer_login_user")
        if active in users and last_login_user != active:
            st.session_state.trainer_selected = active
            st.session_state["_trainer_login_user"] = active
        elif cur not in users:
            st.session_state.trainer_selected = active if active in users else (users[0] if users else None)
    except Exception:
        pass
    prev = st.session_state.get("_trainer_selected_last")
    picker_col, hero_col = st.columns([0.34, 0.66], gap="large")
    with picker_col:
        st.markdown(
            """
            <div class='trainers-picker'>
              <div class='trainers-panel-label'>Entrenadores</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        sel = st.selectbox(
            "Elige un entrenador",
            users,
            key="trainer_selected",
            format_func=format_trainer_with_flags,
        )
    if prev is None:
        st.session_state["_trainer_selected_last"] = sel
    elif sel != prev:
        st.session_state["_trainer_selected_last"] = sel
        st.session_state.pop("selected_pokemon", None)

    _save_label, _save_detail, active_path = _save_snapshot(str(sel or ""))
    with hero_col:
        _render_trainer_header(
            trainer=str(sel or ""),
            current_user=str(st.session_state.get("user") or ""),
            active_path=active_path,
        )
    _render_quick_status(
        trainer=str(sel or ""),
        current_user=str(st.session_state.get("user") or ""),
        active_path=active_path,
    )

    try_auto_load_bridge()
    page_entrenadores_setup()

    page_entrenadores_view()
    _render_retirement_admin()
