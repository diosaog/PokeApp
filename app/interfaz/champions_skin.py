from __future__ import annotations

from typing import Any

import streamlit as st


CHAMPIONS_SKIN_CSS = """
<style>
:root {
  --font-ui: "Nunito Sans", "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-pixel: "Oxanium", "Nunito Sans", "Trebuchet MS", system-ui, sans-serif;
  --champ-bg-0: #f7e9ff;
  --champ-bg-1: #dfccff;
  --champ-bg-2: #c6ddff;
  --champ-panel: rgba(102, 85, 211, 0.84);
  --champ-panel-2: rgba(134, 108, 238, 0.86);
  --champ-panel-3: rgba(88, 73, 190, 0.92);
  --champ-panel-deep: rgba(62, 52, 160, 0.88);
  --champ-list: rgba(250, 248, 255, 0.95);
  --champ-list-2: rgba(238, 233, 255, 0.95);
  --champ-text: #35447f;
  --champ-text-soft: #5f6b9d;
  --champ-muted: #7982ad;
  --champ-lime: #c8ff1f;
  --champ-lime-2: #9ee600;
  --champ-yellow: #ffe636;
  --champ-pink: #ff75dd;
  --champ-cyan: #45d1ff;
  --champ-orange: #ffb35c;
  --champ-red: #f24d67;
  --champ-white-edge: rgba(255, 255, 255, 0.72);
  --champ-panel-edge: rgba(255, 255, 255, 0.36);
  --accent: #8069ff;
  --accent-dark: #5c45d6;
  --accent-soft: #e7ddff;
  --accent-ghost: rgba(128, 105, 255, 0.22);
  --bw2-bg-0: #f7e9ff;
  --bw2-bg-1: #dfccff;
  --bw2-bg-2: #c6ddff;
  --bw2-panel: rgba(102, 85, 211, 0.84);
  --bw2-panel-2: rgba(134, 108, 238, 0.86);
  --bw2-panel-3: rgba(161, 132, 252, 0.92);
  --bw2-screen: rgba(74, 62, 174, 0.78);
  --bw2-screen-2: rgba(111, 91, 216, 0.78);
  --bw2-edge: rgba(255, 255, 255, 0.36);
  --bw2-edge-strong: rgba(255, 255, 255, 0.86);
  --bw2-text: #ffffff;
  --bw2-text-soft: #f1edff;
  --bw2-text-dim: #d6d0ff;
  --bw2-shadow: rgba(65, 56, 148, 0.24);
  --poke-radius-sm: 10px;
  --poke-radius: 14px;
  --poke-radius-xl: 18px;
  --poke-shadow-soft: 0 18px 38px rgba(82, 62, 160, 0.18);
  --poke-shadow-card: 0 10px 22px rgba(82, 62, 160, 0.16);
  --poke-surface-glow: inset 0 1px 0 rgba(255, 255, 255, 0.34);
}

.stApp {
  min-height: 100vh !important;
  color: var(--bw2-text) !important;
  background:
    linear-gradient(128deg, rgba(255,255,255,0.34) 0 12%, transparent 12% 100%) 0 76px / 420px 260px,
    linear-gradient(38deg, rgba(255,255,255,0.24) 0 10%, transparent 10% 100%) 100% 120px / 360px 240px,
    linear-gradient(110deg, rgba(255,117,221,0.22), transparent 28%),
    linear-gradient(250deg, rgba(69,209,255,0.28), transparent 36%),
    linear-gradient(180deg, var(--champ-bg-0) 0%, var(--champ-bg-1) 44%, var(--champ-bg-2) 100%) !important;
}

.stApp::before {
  height: 46px !important;
  background:
    linear-gradient(90deg, rgba(96,80,215,0.96) 0%, rgba(81,151,245,0.96) 48%, rgba(255,117,221,0.9) 73%, rgba(255,230,54,0.9) 100%) !important;
  border-bottom: 1px solid rgba(255,255,255,0.76) !important;
  box-shadow: 0 12px 28px rgba(85,70,180,0.22) !important;
}

.stApp::after {
  content: "POKEAPP CHAMPIONS HUB" !important;
  top: 13px !important;
  color: #ffffff !important;
  font-size: 12px !important;
  text-shadow: 0 2px 8px rgba(62,52,160,0.42) !important;
}

.main::before {
  background:
    linear-gradient(30deg, transparent 0 68%, rgba(255,255,255,0.18) 68% 69%, transparent 69% 100%) 0 0 / 180px 180px,
    linear-gradient(150deg, transparent 0 58%, rgba(255,255,255,0.12) 58% 59%, transparent 59% 100%) 0 0 / 220px 220px,
    radial-gradient(circle at 20% 30%, rgba(255,255,255,0.28), transparent 170px),
    radial-gradient(circle at 78% 18%, rgba(255,255,255,0.22), transparent 190px),
    linear-gradient(180deg, rgba(255,255,255,0.22), transparent 48%) !important;
}

.main .block-container {
  max-width: 1460px !important;
  padding-top: 4.9rem !important;
}

html, body, [class*="css"],
.stApp p,
.stApp span,
.stApp div,
.stApp label,
.stApp li,
.stApp caption {
  font-family: var(--font-ui) !important;
  letter-spacing: 0 !important;
}

.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4,
.stApp h5,
.stApp h6 {
  color: #ffffff !important;
  font-family: var(--font-pixel) !important;
  letter-spacing: 0 !important;
  text-shadow: 0 3px 14px rgba(77, 62, 164, 0.3) !important;
}

.stApp hr {
  height: 1px !important;
  background: linear-gradient(90deg, transparent, rgba(93, 79, 196, 0.32), transparent) !important;
}

section[data-testid="stSidebar"] {
  background:
    linear-gradient(150deg, rgba(255,255,255,0.17) 0 18%, transparent 18% 100%) 0 84px / 260px 190px,
    linear-gradient(180deg, rgba(111,91,216,0.96), rgba(82,70,195,0.92) 58%, rgba(71,113,218,0.92)) !important;
  border-right: 1px solid rgba(255,255,255,0.5) !important;
  box-shadow: 12px 0 34px rgba(82,62,160,0.2) !important;
}

section[data-testid="stSidebar"] .block-container {
  padding-top: 4.25rem !important;
}

section[data-testid="stSidebar"]::before {
  top: 10px !important;
  border: 1px solid rgba(255,255,255,0.58) !important;
  border-radius: 999px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.3), rgba(255,255,255,0.1)),
    rgba(84, 69, 198, 0.86) !important;
  color: #ffffff !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.38), 0 10px 22px rgba(59,47,142,0.2) !important;
}

.main .home-hero,
.main .auth-hero,
.main .trainers-hero,
.main .league-hero,
.main .matchup-hero,
.main .mart-hero,
.main .cup-hero,
.main .ju-hero,
.main .hof-hero,
.main .season-hero,
.main .norma-hero,
.main .saves-hero {
  overflow: hidden !important;
  border: 1px solid rgba(255,255,255,0.56) !important;
  border-radius: var(--poke-radius-xl) !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.2) 0 21%, transparent 21% 100%),
    linear-gradient(302deg, rgba(255,117,221,0.22), transparent 42%),
    linear-gradient(180deg, rgba(137,113,238,0.9), rgba(83,73,190,0.88)) !important;
  box-shadow: var(--poke-surface-glow), 0 22px 44px rgba(82,62,160,0.18) !important;
  backdrop-filter: blur(14px);
}

.main .home-hero::before,
.main .home-hero::after,
.main .auth-hero::before,
.main .trainers-hero::before,
.main .trainers-hero::after,
.main .league-hero::before,
.main .matchup-hero::before,
.main .mart-hero::before,
.main .cup-hero::before,
.main .ju-hero::before,
.main .hof-hero::before,
.main .norma-hero::after,
.main .saves-hero::before {
  opacity: 0.28 !important;
}

.main .home-title,
.main .auth-title,
.main .trainers-title,
.main .league-title,
.main .matchup-title,
.main .mart-title,
.main .cup-title,
.main .ju-hero-title,
.main .hof-title,
.main .season-title,
.main .norma-title,
.main .saves-title {
  color: #ffffff !important;
  font-size: clamp(25px, 3.2vw, 40px) !important;
  line-height: 1.05 !important;
  text-shadow: 0 4px 16px rgba(58,49,151,0.34) !important;
}

.main .home-subtitle,
.main .auth-subtitle,
.main .trainers-subtitle,
.main .league-subtitle,
.main .matchup-subtitle,
.main .mart-subtitle,
.main .cup-sub,
.main .ju-hero-sub,
.main .hof-subtitle,
.main .season-subtitle,
.main .norma-subtitle,
.main .saves-subtitle {
  color: rgba(255,255,255,0.88) !important;
  font-size: 20px !important;
  line-height: 1.18 !important;
}

.main .home-kicker,
.main .auth-kicker,
.main .matchup-kicker,
.main .cup-kicker,
.main .mart-kicker,
.main .ju-hero-chip,
.main .league-kicker,
.main .season-kicker,
.main .norma-chip,
.main .trainers-chip,
.main .hof-team-pill,
.main .saves-card-badge,
.main .mart-pill,
.main .cup-pill,
.main .matchup-hero-pill,
.main .season-pill {
  border: 1px solid rgba(255,255,255,0.5) !important;
  border-radius: 999px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.34), rgba(255,255,255,0.12)),
    rgba(91, 74, 205, 0.74) !important;
  color: #ffffff !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.34), 0 8px 18px rgba(75,60,165,0.15) !important;
}

.main .home-card,
.main .auth-panel,
.main .auth-status,
.main .profile-card,
.main .trainers-picker,
.main .trainers-stat,
.main .trainers-lock-panel,
.main .league-card,
.main .league-status-card,
.main .league-division-card,
.main .league-history-card,
.main .league-section,
.main .league-table-shell,
.main .matchup-shell,
.main .matchup-summary,
.main .matchup-metric,
.main .matchup-mon,
.main .battle-board,
.main .battle-card,
.main .battle-mon-card,
.main .battle-empty-card,
.main .mart-register-card,
.main .mart-confirm-card,
.main .cup-metric,
.main .cup-section,
.main .cup-vs-card,
.main .cup-paste-card,
.main .cup-match,
.main .doubles-card,
.main .doubles-metric,
.main .doubles-section,
.main .ju-action-card,
.main .ju-metric,
.main .ju-penalty-card,
.main .hof-card,
.main .season-card,
.main .season-alert,
.main .season-table,
.main .norma-summary,
.main .norma-row-card,
.main .saves-current-card,
.main .saves-admin-panel,
.main .saves-stat,
.main .pl-card,
.main .pt-metric,
.main .pt-section,
.main .trainer-panel,
section[data-testid="stSidebar"] .profile-card,
section[data-testid="stSidebar"] .app-notice {
  border: 1px solid rgba(255,255,255,0.42) !important;
  border-radius: var(--poke-radius) !important;
  background:
    linear-gradient(130deg, rgba(255,255,255,0.17) 0 24%, transparent 24% 100%),
    linear-gradient(180deg, var(--champ-panel-2), var(--champ-panel-deep)) !important;
  box-shadow: var(--poke-surface-glow), var(--poke-shadow-card) !important;
  color: #ffffff !important;
}

.main .home-card-label,
.main .auth-status-label,
.main .trainers-stat-label,
.main .league-status-card span,
.main .matchup-metric span,
.main .cup-card-label,
.main .season-label,
.main .saves-stat-label,
.main .pt-label,
.main .battle-detail-kicker {
  color: rgba(255,255,255,0.72) !important;
  font-family: var(--font-pixel) !important;
  font-size: 9px !important;
  text-transform: uppercase !important;
}

.main .home-card-value,
.main .auth-status-value,
.main .trainers-stat-value,
.main .league-status-card strong,
.main .matchup-metric strong,
.main .cup-card-value,
.main .season-value,
.main .saves-stat-value,
.main .pt-value {
  color: #ffffff !important;
  font-family: var(--font-pixel) !important;
  text-shadow: 0 2px 9px rgba(58,49,151,0.25) !important;
}

.main .home-section-title,
.main .trainers-section-title,
.main .league-section-title,
.main .cup-section-title,
.main .hof-section-title,
.main .season-section-title,
.main .saves-section-title,
.main .mart-aisle-title,
.main .pt-title,
.main .trainer-head {
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
  padding: 8px 13px !important;
  border: 1px solid rgba(255,255,255,0.6) !important;
  border-radius: 999px !important;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.28), transparent 72%),
    linear-gradient(180deg, var(--accent), var(--accent-dark)) !important;
  color: #ffffff !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.34), 0 10px 22px rgba(82,62,160,0.16) !important;
}

.main .home-action-card,
.main .auth-trainer-card,
.main .matchup-mode-card,
.main .cup-mode-card,
.main .season-version-row,
.main .norma-list-item,
.main .app-notice,
.main .saves-history-card,
.main .pokedex-card,
.main .slot,
.main .slot-empty,
.main .matchup-move,
.main .battle-move-link,
.main .battle-no-move,
.main .battle-ability-row,
.main .battle-private-line,
.main .battle-ivs,
.main .shop-card,
section[data-testid="stSidebar"] div[role="radiogroup"] label,
section[data-testid="stSidebar"] div.stButton > button,
section[data-testid="stSidebar"] .stPopover > div > button,
.main div[data-testid="stTabs"] button[data-baseweb="tab"],
.main div[data-testid="stTabs"] button[role="tab"],
.main .stButton > button,
.main .stDownloadButton > button,
.main form button {
  position: relative !important;
  overflow: hidden !important;
  clip-path: none !important;
  border: 1px solid rgba(105, 89, 202, 0.28) !important;
  border-radius: 14px !important;
  background:
    linear-gradient(136deg, transparent 0 70%, rgba(255,117,221,0.28) 70% 82%, rgba(69,209,255,0.28) 82% 100%),
    linear-gradient(180deg, var(--champ-list), var(--champ-list-2)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.86), 0 9px 20px rgba(82,62,160,0.14) !important;
  color: var(--champ-text) !important;
}

.main .home-action-card *,
.main .auth-trainer-card *,
.main .matchup-mode-card *,
.main .cup-mode-card *,
.main .season-version-row *,
.main .norma-list-item *,
.main .saves-history-card *,
.main .pokedex-card *,
.main .slot *,
.main .slot-empty *,
.main .matchup-move span:last-child,
.main .battle-move-link span:last-child,
.main .battle-no-move *,
.main .battle-private-line *,
.main .battle-ivs *,
.main .shop-card *,
section[data-testid="stSidebar"] div[role="radiogroup"] label *,
section[data-testid="stSidebar"] div.stButton > button *,
.main div[data-testid="stTabs"] button[data-baseweb="tab"] *,
.main div[data-testid="stTabs"] button[role="tab"] *,
.main .stButton > button *,
.main .stDownloadButton > button *,
.main form button * {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

.main .home-action-title,
.main .auth-trainer-name,
.main .matchup-mode-title,
.main .cup-card-label,
.main .season-version-name,
.main .shop-name,
.main .battle-mon-name,
.main .matchup-mon-title {
  font-family: var(--font-pixel) !important;
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
  text-shadow: none !important;
}

.main .home-action-body,
.main .auth-trainer-meta,
.main .matchup-mode-sub,
.main .cup-card-sub,
.main .season-version-meta,
.main .shop-desc,
.main .matchup-mon-sub,
.main .matchup-mon-extra,
.main .battle-species,
.main .battle-level,
.main .battle-item {
  color: var(--champ-text-soft) !important;
  -webkit-text-fill-color: var(--champ-text-soft) !important;
}

section[data-testid="stSidebar"] .sidebar-nav-title {
  border: 1px solid rgba(255,255,255,0.48) !important;
  border-radius: 999px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.26), rgba(255,255,255,0.08)),
    rgba(74, 61, 177, 0.62) !important;
  color: #ffffff !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] {
  gap: 8px !important;
  overflow: visible !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label {
  min-height: 52px !important;
  padding: 0.62rem 0.82rem 0.62rem 1.02rem !important;
  transform: translateX(0);
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:hover,
.main .home-action-card:hover,
.main .matchup-mode-card:hover,
.main .cup-mode-card:hover,
.main .pokedex-card:hover,
.main .slot:hover,
.main .stButton > button:hover,
.main .stDownloadButton > button:hover {
  transform: translateY(-1px) !important;
  filter: brightness(1.03) saturate(1.05) !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked),
.main .matchup-mode-card.is-active,
.main .cup-mode-card.is-active,
.main div[data-testid="stTabs"] button[aria-selected="true"],
.main button[data-baseweb="tab"][aria-selected="true"],
.main button[role="tab"][aria-selected="true"],
.main .battle-move-link:hover,
.main .battle-move-link.is-active,
.main .battle-move-row[open] > .battle-move-link,
.main .stButton > button[kind="primary"],
section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
  border-color: rgba(255,255,255,0.88) !important;
  background:
    linear-gradient(136deg, transparent 0 68%, rgba(255,255,255,0.34) 68% 100%),
    linear-gradient(180deg, var(--champ-lime), var(--champ-lime-2)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.84), 0 9px 18px rgba(110, 160, 0, 0.22), 0 0 0 3px rgba(255,230,54,0.2) !important;
  color: var(--champ-text) !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before,
.main .matchup-mode-card.is-active::before,
.main .cup-mode-card.is-active::before,
.main div[data-testid="stTabs"] button[aria-selected="true"]::before,
.main button[data-baseweb="tab"][aria-selected="true"]::before,
.main button[role="tab"][aria-selected="true"]::before {
  content: "" !important;
  position: absolute !important;
  left: -18px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 0 !important;
  height: 0 !important;
  border-top: 15px solid transparent !important;
  border-bottom: 15px solid transparent !important;
  border-left: 0 !important;
  border-right: 20px solid var(--champ-yellow) !important;
  filter: drop-shadow(0 2px 0 rgba(84,71,170,0.28)) !important;
  z-index: 4 !important;
}

.main div[data-testid="stTabs"] div[data-baseweb="tab-list"],
.main div[data-testid="stTabs"] [role="tablist"],
.main div[data-baseweb="tab-list"] {
  gap: 10px !important;
  padding: 10px !important;
  border: 1px solid rgba(255,255,255,0.42) !important;
  border-radius: 16px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.2), rgba(255,255,255,0.08)),
    rgba(99, 82, 207, 0.72) !important;
  box-shadow: var(--poke-surface-glow), 0 12px 24px rgba(82,62,160,0.14) !important;
}

.main div[data-testid="stTabs"] button[data-baseweb="tab"],
.main div[data-testid="stTabs"] button[role="tab"] {
  min-height: 48px !important;
  padding: 0 20px !important;
}

.main .stButton > button,
.main .stDownloadButton > button,
.main form button {
  min-height: 44px !important;
  justify-content: center !important;
  font-family: var(--font-pixel) !important;
  font-size: 11px !important;
  font-weight: 800 !important;
  text-transform: uppercase !important;
}

.main .stButton > button:disabled,
.main .stDownloadButton > button:disabled,
.main form button:disabled,
.main .stButton > button:disabled *,
.main .stDownloadButton > button:disabled *,
.main form button:disabled * {
  opacity: 0.64 !important;
  color: #7e84a9 !important;
  -webkit-text-fill-color: #7e84a9 !important;
  filter: grayscale(0.25) !important;
}

.main .stTextInput input,
.main .stNumberInput input,
.main .stTextArea textarea,
.main .stSelectbox [data-baseweb="select"],
.main .stMultiSelect [data-baseweb="select"],
.main .stDateInput input {
  min-height: 42px !important;
  border: 1px solid rgba(105,89,202,0.32) !important;
  border-radius: 13px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.95), rgba(239,235,255,0.96)) !important;
  color: var(--champ-text) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.82), 0 8px 18px rgba(82,62,160,0.08) !important;
}

.main .stTextInput input *,
.main .stNumberInput input *,
.main .stTextArea textarea *,
.main .stSelectbox [data-baseweb="select"] *,
.main .stMultiSelect [data-baseweb="select"] * {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

.main [data-testid="stDataFrame"],
.main .stDataFrame,
.main table,
.main .league-status-table,
.main .season-table {
  border: 1px solid rgba(255,255,255,0.44) !important;
  border-radius: var(--poke-radius) !important;
  overflow: hidden !important;
  background:
    linear-gradient(180deg, rgba(116,94,224,0.86), rgba(74,62,174,0.82)) !important;
  color: #ffffff !important;
  box-shadow: var(--poke-surface-glow), var(--poke-shadow-card) !important;
}

.main table th,
.main .league-status-table th,
.main .season-table th {
  background: rgba(255,255,255,0.14) !important;
  color: #ffffff !important;
  font-family: var(--font-pixel) !important;
}

.main table td,
.main .league-status-table td,
.main .season-table td {
  color: #ffffff !important;
  border-color: rgba(255,255,255,0.18) !important;
}

.main .shop-card {
  min-height: 238px !important;
}

.main .shop-head {
  min-height: 48px !important;
  border-bottom: 1px solid rgba(255,255,255,0.34) !important;
  border-radius: 13px 13px 0 0 !important;
  background:
    linear-gradient(90deg, var(--accent) 0 6px, transparent 6px),
    linear-gradient(180deg, var(--champ-panel-2), var(--champ-panel-3)) !important;
}

.main .shop-head *,
.main .shop-head .shop-name,
.main .shop-head .shop-sku {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

.main .shop-body {
  grid-template-columns: 76px minmax(0, 1fr) !important;
}

.main .shop-icon-slot,
.main .auth-avatar,
.main .trainers-portrait-xl,
.main .profile-avatar,
.main .matchup-avatar,
.main .battle-sprite-wrap,
section[data-testid="stSidebar"] .mini-mon {
  border: 1px solid rgba(105,89,202,0.26) !important;
  border-radius: 14px !important;
  background:
    radial-gradient(circle at 48% 42%, rgba(255,255,255,0.8), rgba(255,255,255,0.14) 58%, transparent 59%),
    linear-gradient(180deg, rgba(248,246,255,0.96), rgba(223,215,255,0.9)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.88), 0 8px 16px rgba(82,62,160,0.12) !important;
}

.main .shop-price,
.main .shop-coin-value {
  border: 1px solid rgba(105,89,202,0.26) !important;
  border-radius: 10px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.9), rgba(240,236,255,0.9)) !important;
  color: var(--champ-text) !important;
}

.main .shop-price *,
.main .shop-coin-value *,
.main .shop-stock,
.main .shop-missing {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

.main .shop-coin {
  font-size: 20px !important;
}

.main .shop-amount {
  font-size: 16px !important;
}

.main .shop-discount-badge {
  border-radius: 999px !important;
  background: linear-gradient(180deg, #ffbe5c, #ff7d4c) !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

.main .shop-discount-badge *,
.main .slot .type-chip,
.main .slot .shield-chip,
.main .slot .rob-chip,
.main .slot .pill,
.main .pokedex-card .type-chip,
.main .pokedex-card .shield-chip,
.main .pokedex-card .rob-chip,
.main .pokedex-card .pill {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  text-shadow: 0 1px 0 rgba(0,0,0,0.28) !important;
}

.main .slot .pill-shiny,
.main .pokedex-card .pill-shiny {
  color: #1d1610 !important;
  -webkit-text-fill-color: #1d1610 !important;
  text-shadow: none !important;
}

.main .shop-card.is-sale {
  border-color: rgba(255,230,54,0.9) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.86), 0 0 0 3px rgba(255,230,54,0.18), 0 12px 26px rgba(82,62,160,0.18) !important;
}

.main .battle-board {
  background:
    linear-gradient(110deg, rgba(255,255,255,0.16) 0 24%, transparent 24% 100%),
    linear-gradient(180deg, rgba(111,91,216,0.86), rgba(74,62,174,0.78)) !important;
}

.main .battle-mon-card,
.main .matchup-mon {
  background:
    linear-gradient(112deg, rgba(255,255,255,0.17) 0 36%, transparent 36% 100%),
    linear-gradient(180deg, rgba(126,103,230,0.88), rgba(76,65,176,0.86)) !important;
}

.main .battle-move-link,
.main .battle-no-move,
.main .matchup-move {
  min-height: 33px !important;
  padding: 6px 9px !important;
  border-radius: 12px !important;
  background:
    linear-gradient(136deg, transparent 0 74%, rgba(255,117,221,0.22) 74% 100%),
    linear-gradient(180deg, rgba(255,255,255,0.96), rgba(238,233,255,0.94)) !important;
}

.main .battle-move-row[open] > .battle-move-link span:last-child,
.main .battle-move-link:hover span:last-child {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

.main .battle-move-detail {
  border: 1px solid rgba(255,255,255,0.42) !important;
  border-radius: var(--poke-radius) !important;
  background:
    linear-gradient(130deg, rgba(255,255,255,0.16) 0 26%, transparent 26% 100%),
    linear-gradient(180deg, var(--champ-panel-2), var(--champ-panel-deep)) !important;
  box-shadow: var(--poke-surface-glow), var(--poke-shadow-card) !important;
}

.main .battle-detail-stats div,
.main .battle-ability-row,
.main .battle-private-line,
.main .battle-ivs,
.main .battle-iv {
  border: 1px solid rgba(255,255,255,0.22) !important;
  border-radius: 10px !important;
  background: rgba(255,255,255,0.12) !important;
}

.main .battle-type-pill {
  border-radius: 4px !important;
}

.main .battle-category-icon {
  border-radius: 4px !important;
}

.main .app-notice {
  background:
    linear-gradient(136deg, transparent 0 72%, rgba(255,117,221,0.24) 72% 100%),
    linear-gradient(180deg, rgba(255,255,255,0.94), rgba(238,233,255,0.94)) !important;
}

.main .app-notice-title,
.main .app-notice-body,
.main .app-notice-time {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

section[data-testid="stSidebar"] .app-notice {
  background:
    linear-gradient(136deg, transparent 0 72%, rgba(255,117,221,0.22) 72% 100%),
    linear-gradient(180deg, rgba(255,255,255,0.95), rgba(238,233,255,0.93)) !important;
}

section[data-testid="stSidebar"] .app-notice *,
section[data-testid="stSidebar"] .stPopover button *,
section[data-testid="stSidebar"] .profile-name,
section[data-testid="stSidebar"] .profile-sub {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

section[data-testid="stSidebar"] .profile-card {
  background:
    linear-gradient(130deg, rgba(255,255,255,0.2) 0 28%, transparent 28% 100%),
    linear-gradient(180deg, rgba(255,255,255,0.22), rgba(255,255,255,0.1)),
    rgba(104, 86, 211, 0.74) !important;
}

section[data-testid="stSidebar"] .profile-card *,
section[data-testid="stSidebar"] .sidebar-nav-title {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) *,
section[data-testid="stSidebar"] div.stButton > button[kind="primary"] *,
.main .matchup-mode-card.is-active *,
.main .cup-mode-card.is-active *,
.main div[data-testid="stTabs"] button[aria-selected="true"] *,
.main button[data-baseweb="tab"][aria-selected="true"] *,
.main button[role="tab"][aria-selected="true"] * {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

.main img,
section[data-testid="stSidebar"] img {
  image-rendering: auto !important;
}

.main .pokemon-sprite,
.main .battle-sprite,
.main .matchup-sprite,
.main .shop-icon,
.main .mini-mon img,
section[data-testid="stSidebar"] .mini-mon img {
  image-rendering: pixelated !important;
}

@media (max-width: 980px) {
  .main .home-grid,
  .main .matchup-team-grid,
  .main .battle-team-grid,
  .main .league-division-grid,
  .main .league-history-grid,
  .main .cup-mode-grid,
  .main .cup-metric-grid {
    grid-template-columns: 1fr !important;
  }
  .main .battle-mon-card {
    grid-template-columns: minmax(0, 1fr) !important;
  }
}
</style>
"""


def apply_champions_skin(container: Any = None) -> None:
    target = container or st
    target.markdown(CHAMPIONS_SKIN_CSS, unsafe_allow_html=True)
