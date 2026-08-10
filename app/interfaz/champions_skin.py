from __future__ import annotations

from typing import Any

import streamlit as st


CHAMPIONS_SKIN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0,0&display=swap');

:root {
  --font-ui: "Nunito Sans", "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-pixel: "Oxanium", "Nunito Sans", "Trebuchet MS", system-ui, sans-serif;
  --champ-bg-0: #2f235d;
  --champ-bg-1: #473789;
  --champ-bg-2: #315b9d;
  --champ-panel: rgba(86, 70, 190, 0.9);
  --champ-panel-2: rgba(111, 91, 216, 0.9);
  --champ-panel-3: rgba(78, 64, 176, 0.95);
  --champ-panel-deep: rgba(48, 40, 132, 0.94);
  --champ-list: rgba(222, 216, 248, 0.94);
  --champ-list-2: rgba(199, 192, 230, 0.94);
  --champ-text: #263566;
  --champ-text-soft: #4d5789;
  --champ-muted: #6d75a0;
  --champ-lime: #b7ee32;
  --champ-lime-2: #8fd10b;
  --champ-yellow: #f6d83b;
  --champ-pink: #ff75dd;
  --champ-cyan: #45d1ff;
  --champ-orange: #ffb35c;
  --champ-red: #f24d67;
  --champ-white-edge: rgba(238, 233, 255, 0.58);
  --champ-panel-edge: rgba(238, 233, 255, 0.28);
  --accent: #8069ff;
  --accent-dark: #5c45d6;
  --accent-soft: #d8cbff;
  --accent-ghost: rgba(128, 105, 255, 0.22);
  --bw2-bg-0: #2f235d;
  --bw2-bg-1: #473789;
  --bw2-bg-2: #315b9d;
  --bw2-panel: rgba(86, 70, 190, 0.9);
  --bw2-panel-2: rgba(111, 91, 216, 0.9);
  --bw2-panel-3: rgba(132, 107, 238, 0.94);
  --bw2-screen: rgba(59, 49, 150, 0.82);
  --bw2-screen-2: rgba(92, 75, 202, 0.82);
  --bw2-edge: rgba(238, 233, 255, 0.28);
  --bw2-edge-strong: rgba(248, 245, 255, 0.72);
  --bw2-text: #ffffff;
  --bw2-text-soft: #f1edff;
  --bw2-text-dim: #d6d0ff;
  --bw2-shadow: rgba(24, 18, 70, 0.32);
  --poke-radius-sm: 10px;
  --poke-radius: 14px;
  --poke-radius-xl: 18px;
  --poke-shadow-soft: 0 18px 38px rgba(18, 14, 54, 0.28);
  --poke-shadow-card: 0 10px 22px rgba(18, 14, 54, 0.22);
  --poke-surface-glow: inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.stApp {
  min-height: 100vh !important;
  color: var(--bw2-text) !important;
  background:
    linear-gradient(128deg, rgba(255,255,255,0.12) 0 12%, transparent 12% 100%) 0 76px / 420px 260px,
    linear-gradient(38deg, rgba(255,255,255,0.08) 0 10%, transparent 10% 100%) 100% 120px / 360px 240px,
    linear-gradient(110deg, rgba(255,117,221,0.14), transparent 30%),
    linear-gradient(250deg, rgba(69,209,255,0.16), transparent 38%),
    linear-gradient(180deg, var(--champ-bg-0) 0%, var(--champ-bg-1) 44%, var(--champ-bg-2) 100%) !important;
}

.stApp::before {
  height: 46px !important;
  background:
    linear-gradient(90deg, rgba(96,80,215,0.96) 0%, rgba(81,151,245,0.96) 48%, rgba(255,117,221,0.9) 73%, rgba(255,230,54,0.9) 100%) !important;
  border-bottom: 1px solid rgba(238,233,255,0.46) !important;
  box-shadow: 0 12px 28px rgba(18,14,54,0.28) !important;
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
    linear-gradient(30deg, transparent 0 68%, rgba(255,255,255,0.08) 68% 69%, transparent 69% 100%) 0 0 / 180px 180px,
    linear-gradient(150deg, transparent 0 58%, rgba(255,255,255,0.06) 58% 59%, transparent 59% 100%) 0 0 / 220px 220px,
    radial-gradient(circle at 20% 30%, rgba(255,255,255,0.12), transparent 170px),
    radial-gradient(circle at 78% 18%, rgba(255,255,255,0.1), transparent 190px),
    linear-gradient(180deg, rgba(255,255,255,0.08), transparent 48%) !important;
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

.stApp .material-symbols-rounded,
.stApp .material-symbols-outlined,
.stApp .material-icons,
.stApp [class*="material-symbols"],
.stApp [class*="material-icons"],
.stApp span[data-testid="stIconMaterial"],
section[data-testid="stSidebar"] .material-symbols-rounded,
section[data-testid="stSidebar"] .material-symbols-outlined,
section[data-testid="stSidebar"] [class*="material-symbols"],
section[data-testid="stSidebar"] span[data-testid="stIconMaterial"] {
  font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
  font-weight: 400 !important;
  font-style: normal !important;
  font-size: 20px !important;
  line-height: 1 !important;
  letter-spacing: normal !important;
  text-transform: none !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-feature-settings: "liga" !important;
  -webkit-font-feature-settings: "liga" !important;
  -webkit-font-smoothing: antialiased !important;
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
    linear-gradient(150deg, rgba(255,255,255,0.09) 0 18%, transparent 18% 100%) 0 84px / 260px 190px,
    linear-gradient(180deg, rgba(80,66,186,0.96), rgba(57,48,154,0.94) 58%, rgba(47,92,176,0.94)) !important;
  border-right: 1px solid rgba(238,233,255,0.34) !important;
  box-shadow: 12px 0 34px rgba(18,14,54,0.28) !important;
}

section[data-testid="stSidebar"] .block-container {
  padding-top: 4.25rem !important;
}

section[data-testid="stSidebar"]::before {
  top: 10px !important;
  border: 1px solid rgba(238,233,255,0.42) !important;
  border-radius: 999px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.18), rgba(255,255,255,0.06)),
    rgba(64, 53, 170, 0.88) !important;
  color: #ffffff !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.22), 0 10px 22px rgba(18,14,54,0.22) !important;
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
.main .saves-hero {
  overflow: hidden !important;
  border: 1px solid rgba(238,233,255,0.42) !important;
  border-radius: var(--poke-radius-xl) !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.11) 0 21%, transparent 21% 100%),
    linear-gradient(302deg, rgba(255,117,221,0.16), transparent 44%),
    linear-gradient(180deg, rgba(111,91,216,0.92), rgba(57,48,154,0.9)) !important;
  box-shadow: var(--poke-surface-glow), 0 22px 44px rgba(18,14,54,0.26) !important;
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
.main .trainers-chip,
.main .hof-team-pill,
.main .saves-card-badge,
.main .mart-pill,
.main .cup-pill,
.main .matchup-hero-pill,
.main .season-pill {
  border: 1px solid rgba(238,233,255,0.34) !important;
  border-radius: 999px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.2), rgba(255,255,255,0.07)),
    rgba(72, 59, 182, 0.78) !important;
  color: #ffffff !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.22), 0 8px 18px rgba(18,14,54,0.2) !important;
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
.main .saves-current-card,
.main .saves-admin-panel,
.main .saves-stat,
.main .pl-card,
.main .pt-metric,
.main .pt-section,
.main .trainer-panel,
section[data-testid="stSidebar"] .profile-card,
section[data-testid="stSidebar"] .app-notice {
  border: 1px solid rgba(238,233,255,0.3) !important;
  border-radius: var(--poke-radius) !important;
  background:
    linear-gradient(130deg, rgba(255,255,255,0.1) 0 24%, transparent 24% 100%),
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
  border: 1px solid rgba(238,233,255,0.44) !important;
  border-radius: 999px !important;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.18), transparent 72%),
    linear-gradient(180deg, var(--accent), var(--accent-dark)) !important;
  color: #ffffff !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.24), 0 10px 22px rgba(18,14,54,0.22) !important;
}

.main .home-action-card,
.main .auth-trainer-card,
.main .matchup-mode-card,
.main .cup-mode-card,
.main .season-version-row,
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
  border: 1px solid rgba(238, 233, 255, 0.3) !important;
  border-radius: 14px !important;
  background:
    linear-gradient(136deg, transparent 0 70%, rgba(255,117,221,0.18) 70% 82%, rgba(69,209,255,0.18) 82% 100%),
    linear-gradient(180deg, var(--champ-list), var(--champ-list-2)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.46), 0 9px 20px rgba(18,14,54,0.2) !important;
  color: var(--champ-text) !important;
}

.main .home-action-card *,
.main .auth-trainer-card *,
.main .matchup-mode-card *,
.main .cup-mode-card *,
.main .season-version-row *,
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
  padding: 0.62rem 0.9rem 0.62rem 1.12rem !important;
  transform: translateX(0);
}

section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
  display: none !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label p {
  margin: 0 !important;
  width: 100% !important;
  font-family: var(--font-ui) !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  line-height: 1.1 !important;
  text-transform: uppercase !important;
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label::after,
section[data-testid="stSidebar"] div.stButton > button::after,
.main div[data-testid="stTabs"] button[data-baseweb="tab"]::after,
.main div[data-testid="stTabs"] button[role="tab"]::after {
  content: "" !important;
  position: absolute !important;
  inset: 0 0 0 auto !important;
  width: 44% !important;
  pointer-events: none !important;
  background:
    linear-gradient(135deg, transparent 0 38%, rgba(255,117,221,0.18) 38% 58%, rgba(69,209,255,0.18) 58% 78%, transparent 78% 100%) !important;
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
  border-color: rgba(248,245,255,0.78) !important;
  background:
    linear-gradient(136deg, transparent 0 68%, rgba(255,255,255,0.22) 68% 100%),
    linear-gradient(180deg, var(--champ-lime), var(--champ-lime-2)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.48), 0 9px 18px rgba(35, 58, 0, 0.24), 0 0 0 3px rgba(246,216,59,0.18) !important;
  color: var(--champ-text) !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
  color: #21416d !important;
  -webkit-text-fill-color: #21416d !important;
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
  border: 1px solid rgba(238,233,255,0.32) !important;
  border-radius: 16px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.14), rgba(255,255,255,0.05)),
    rgba(77, 63, 186, 0.78) !important;
  box-shadow: var(--poke-surface-glow), 0 12px 24px rgba(18,14,54,0.22) !important;
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
  border: 1px solid rgba(238,233,255,0.3) !important;
  border-radius: 13px !important;
  background:
    linear-gradient(180deg, rgba(222,216,248,0.96), rgba(199,192,230,0.96)) !important;
  color: var(--champ-text) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.36), 0 8px 18px rgba(18,14,54,0.18) !important;
}

.main .stSelectbox [data-baseweb="select"] > div,
.main .stMultiSelect [data-baseweb="select"] > div {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
  font-family: var(--font-pixel) !important;
  font-size: 12px !important;
  text-transform: uppercase !important;
}

.main .stSelectbox [data-baseweb="select"] svg,
.main .stMultiSelect [data-baseweb="select"] svg {
  color: var(--accent-dark) !important;
  fill: var(--accent-dark) !important;
}

div[data-baseweb="popover"] {
  border-radius: 16px !important;
  overflow: hidden !important;
  border: 1px solid rgba(238,233,255,0.34) !important;
  background:
    linear-gradient(180deg, rgba(88,72,198,0.98), rgba(48,40,132,0.98)) !important;
  box-shadow: 0 18px 34px rgba(18,14,54,0.34) !important;
}

div[data-baseweb="popover"] ul,
div[data-baseweb="menu"] {
  padding: 8px !important;
  background:
    linear-gradient(180deg, rgba(88,72,198,0.98), rgba(48,40,132,0.98)) !important;
}

div[data-baseweb="popover"] li,
div[data-baseweb="menu"] li,
div[role="option"] {
  min-height: 40px !important;
  margin: 3px 0 !important;
  border-radius: 12px !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  font-family: var(--font-ui) !important;
  font-weight: 800 !important;
}

div[data-baseweb="popover"] li:hover,
div[data-baseweb="menu"] li:hover,
div[role="option"]:hover,
div[aria-selected="true"][role="option"] {
  background:
    linear-gradient(136deg, transparent 0 68%, rgba(255,255,255,0.22) 68% 100%),
    linear-gradient(180deg, var(--champ-lime), var(--champ-lime-2)) !important;
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
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
  border: 1px solid rgba(238,233,255,0.32) !important;
  border-radius: var(--poke-radius) !important;
  overflow: hidden !important;
  background:
    linear-gradient(180deg, rgba(92,75,202,0.88), rgba(53,44,142,0.86)) !important;
  color: #ffffff !important;
  box-shadow: var(--poke-surface-glow), var(--poke-shadow-card) !important;
}

.main table th,
.main .league-status-table th,
.main .season-table th {
  background: rgba(255,255,255,0.09) !important;
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
  border: 1px solid rgba(238,233,255,0.26) !important;
  border-radius: 14px !important;
  background:
    radial-gradient(circle at 48% 42%, rgba(255,255,255,0.45), rgba(255,255,255,0.08) 58%, transparent 59%),
    linear-gradient(180deg, rgba(214,207,244,0.94), rgba(178,170,218,0.9)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.42), 0 8px 16px rgba(18,14,54,0.2) !important;
}

.main .shop-price,
.main .shop-coin-value {
  border: 1px solid rgba(238,233,255,0.26) !important;
  border-radius: 10px !important;
  background:
    linear-gradient(180deg, rgba(222,216,248,0.92), rgba(199,192,230,0.92)) !important;
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
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.42), 0 0 0 3px rgba(246,216,59,0.16), 0 12px 26px rgba(18,14,54,0.24) !important;
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
    linear-gradient(136deg, transparent 0 74%, rgba(255,117,221,0.16) 74% 100%),
    linear-gradient(180deg, rgba(222,216,248,0.94), rgba(199,192,230,0.94)) !important;
}

.main .battle-move-row[open] > .battle-move-link span:last-child,
.main .battle-move-link:hover span:last-child {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

.main .battle-move-detail {
  border: 1px solid rgba(238,233,255,0.3) !important;
  border-radius: var(--poke-radius) !important;
  background:
    linear-gradient(130deg, rgba(255,255,255,0.1) 0 26%, transparent 26% 100%),
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
  background: rgba(255,255,255,0.08) !important;
}

.main .battle-type-pill {
  border-radius: 4px !important;
}

.main .battle-category-icon {
  border-radius: 4px !important;
}

/* Champions-style Pokemon storage and roster tiles */
.main .slot,
.main .slot-empty {
  min-height: 184px !important;
  display: grid !important;
  grid-template-rows: auto minmax(76px, 1fr) auto auto auto !important;
  align-items: center !important;
  padding: 9px 9px 10px !important;
  border: 1px solid rgba(114, 96, 212, 0.34) !important;
  border-radius: 16px !important;
  background:
    linear-gradient(138deg, transparent 0 66%, rgba(255,117,221,0.16) 66% 82%, rgba(69,209,255,0.16) 82% 100%),
    linear-gradient(180deg, rgba(222,216,248,0.94), rgba(199,192,230,0.94)) !important;
  box-shadow:
    inset 0 1px 0 rgba(255,255,255,0.46),
    0 8px 18px rgba(18,14,54,0.22) !important;
}

.main .slot::before {
  content: "" !important;
  position: absolute !important;
  left: 10px !important;
  top: 9px !important;
  width: 16px !important;
  height: 16px !important;
  border-radius: 50% !important;
  background:
    linear-gradient(180deg, var(--champ-red) 0 48%, #3b3e58 48% 54%, #ffffff 54% 100%) !important;
  border: 1px solid rgba(57,68,127,0.42) !important;
  opacity: 0.88 !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.38) !important;
  pointer-events: none !important;
}

.main .slot .badges {
  min-height: 22px !important;
  margin-bottom: 7px !important;
  padding-left: 22px !important;
}

.main .slot .pill {
  min-height: 20px !important;
  padding: 2px 7px !important;
  border-radius: 999px !important;
  background:
    linear-gradient(180deg, rgba(142,122,245,0.96), rgba(90,74,206,0.96)) !important;
  border: 1px solid rgba(238,233,255,0.64) !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.28), 0 4px 8px rgba(18,14,54,0.18) !important;
}

.main .slot .gender-m {
  background: linear-gradient(180deg, #66c7ff, #3979d8) !important;
}

.main .slot .gender-f {
  background: linear-gradient(180deg, #ff8ed8, #c84c9c) !important;
}

.main .slot .slot-sep {
  height: 2px !important;
  margin: 2px 0 8px !important;
  background:
    linear-gradient(90deg, transparent 0%, rgba(128,105,255,0.22) 12%, rgba(128,105,255,0.72) 50%, rgba(128,105,255,0.22) 88%, transparent 100%) !important;
}

.main .slot img {
  width: min(100%, 104px) !important;
  height: 82px !important;
  object-fit: contain !important;
  margin: 0 auto 5px !important;
  filter: drop-shadow(0 6px 8px rgba(80,64,152,0.24)) !important;
}

.main .slot .title {
  margin-top: 4px !important;
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
  font-family: var(--font-pixel) !important;
  font-size: 10px !important;
  line-height: 1.15 !important;
  text-transform: uppercase !important;
}

.main .slot .sub {
  margin-top: 4px !important;
  color: var(--champ-text-soft) !important;
  -webkit-text-fill-color: var(--champ-text-soft) !important;
  font-size: 15px !important;
  line-height: 1.08 !important;
}

.main .slot .types {
  min-height: 21px !important;
  margin-top: 8px !important;
}

.main .slot-empty {
  place-items: center !important;
  color: rgba(53,68,127,0.58) !important;
  -webkit-text-fill-color: rgba(53,68,127,0.58) !important;
  border-style: dashed !important;
  background:
    linear-gradient(138deg, transparent 0 66%, rgba(255,255,255,0.12) 66% 100%),
    rgba(190,183,222,0.42) !important;
}

.main .slot-empty *,
.main .slot-empty .hint {
  color: rgba(53,68,127,0.58) !important;
  -webkit-text-fill-color: rgba(53,68,127,0.58) !important;
}

/* Champions-style trainer detail panels */
.main .trainer-panel {
  padding: 12px !important;
  border-radius: 18px !important;
  background:
    linear-gradient(130deg, rgba(255,255,255,0.1) 0 30%, transparent 30% 100%),
    linear-gradient(180deg, rgba(132,107,238,0.9), rgba(77,65,178,0.88)) !important;
}

.main .trainer-head {
  width: 100% !important;
  justify-content: space-between !important;
  border-radius: 999px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.05)),
    rgba(82,70,195,0.78) !important;
}

.main .trainer-grid {
  grid-template-columns: 170px minmax(0, 1fr) !important;
  gap: 14px !important;
}

.main .trainer-portrait {
  min-height: 186px !important;
  border-radius: 18px !important;
  background:
    radial-gradient(circle at 50% 48%, rgba(255,255,255,0.44), rgba(255,255,255,0.08) 58%, transparent 59%),
    linear-gradient(180deg, rgba(214,207,244,0.94), rgba(178,170,218,0.9)) !important;
}

.main .trainer-portrait img {
  width: min(100%, 138px) !important;
  filter: drop-shadow(0 8px 12px rgba(54,44,130,0.22)) !important;
}

.main .trainer-bars {
  gap: 10px !important;
}

.main .tbar-row {
  grid-template-columns: 116px minmax(0, 1fr) 76px !important;
  padding: 7px 8px !important;
  border: 1px solid rgba(255,255,255,0.22) !important;
  border-radius: 999px !important;
  background: rgba(255,255,255,0.08) !important;
}

.main .tbar-label {
  color: #ffffff !important;
}

.main .tbar-track {
  height: 12px !important;
  border: 1px solid rgba(255,255,255,0.26) !important;
  border-radius: 999px !important;
  background: rgba(52,44,133,0.44) !important;
}

.main .tbar-fill {
  border-radius: 999px !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.6) !important;
}

.main .tbar-value,
.main .trainer-kia {
  border: 1px solid rgba(238,233,255,0.26) !important;
  border-radius: 12px !important;
  background:
    linear-gradient(180deg, rgba(222,216,248,0.92), rgba(199,192,230,0.92)) !important;
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

.main .trainer-kia strong,
.main .trainer-note {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

.main .trainer-medals span {
  border-radius: 999px !important;
}

/* Champions-style Team Preview / battle board */
.main .battle-board {
  padding: 12px !important;
  border-radius: 20px !important;
  background:
    linear-gradient(128deg, rgba(255,255,255,0.09) 0 21%, transparent 21% 100%),
    linear-gradient(180deg, rgba(130,105,238,0.86), rgba(75,64,176,0.8)) !important;
}

.main .battle-board-top {
  gap: 10px !important;
}

.main .battle-board-top > div {
  min-height: 46px !important;
  padding: 8px 12px !important;
  border: 1px solid rgba(238,233,255,0.3) !important;
  border-radius: 999px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.05)),
    rgba(86,72,198,0.74) !important;
}

.main .battle-board-top span,
.main .battle-board-top strong {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

.main .battle-team-grid {
  gap: 12px !important;
}

.main .battle-mon-card {
  min-height: 174px !important;
  grid-template-columns: minmax(144px, .9fr) 112px minmax(206px, 1.18fr) !important;
  gap: 12px !important;
  padding: 12px !important;
  border-radius: 18px !important;
  border: 1px solid rgba(238,233,255,0.34) !important;
  background:
    linear-gradient(112deg, rgba(255,255,255,0.1) 0 35%, rgba(255,255,255,0.03) 35% 100%),
    linear-gradient(180deg, rgba(129,104,236,0.9), rgba(82,70,190,0.9)) !important;
}

.main .battle-card-left {
  min-width: 0 !important;
  padding: 8px 9px !important;
  border-radius: 14px !important;
  background: rgba(255,255,255,0.07) !important;
}

.main .battle-mon-name {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  font-size: 10px !important;
}

.main .battle-species,
.main .battle-level,
.main .battle-item {
  color: rgba(255,255,255,0.84) !important;
  -webkit-text-fill-color: rgba(255,255,255,0.84) !important;
}

.main .battle-sprite-wrap {
  min-height: 112px !important;
  border-radius: 18px !important;
}

.main .battle-sprite {
  width: 104px !important;
  height: 104px !important;
}

.main .battle-moves {
  gap: 8px !important;
}

.main .battle-type-dot {
  width: 25px !important;
  height: 25px !important;
  flex-basis: 25px !important;
  border-radius: 7px !important;
  border: 1px solid rgba(238,233,255,0.62) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.28), 0 3px 6px rgba(18,14,54,0.22) !important;
}

.main .battle-move-link,
.main .battle-no-move {
  min-height: 36px !important;
  gap: 9px !important;
  padding: 6px 9px !important;
  border-radius: 999px !important;
}

.main .battle-move-row[open] > .battle-move-link::before,
.main .battle-move-link:hover::before {
  content: "" !important;
  position: absolute !important;
  left: -16px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 0 !important;
  height: 0 !important;
  border-top: 13px solid transparent !important;
  border-bottom: 13px solid transparent !important;
  border-right: 18px solid var(--champ-yellow) !important;
}

.main .battle-move-detail-inline {
  margin: 7px 0 1px 14px !important;
  border-radius: 14px !important;
  background:
    linear-gradient(130deg, rgba(255,255,255,0.09) 0 28%, transparent 28% 100%),
    linear-gradient(180deg, rgba(92,75,202,0.96), rgba(62,52,160,0.96)) !important;
}

.main .battle-move-detail-inline .battle-detail-stats div {
  border-radius: 12px !important;
  background:
    linear-gradient(180deg, rgba(222,216,248,0.92), rgba(199,192,230,0.92)) !important;
}

.main .battle-move-detail-inline .battle-detail-stats div span,
.main .battle-move-detail-inline .battle-detail-stats div strong {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

.main .battle-move-detail-inline .battle-detail-desc {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

.main .matchup-summary-head {
  grid-template-columns: 116px minmax(0, 1fr) !important;
}

.main .matchup-avatar {
  border-radius: 18px !important;
}

.main .matchup-team-grid {
  gap: 12px !important;
}

.main .matchup-mon {
  min-height: 214px !important;
  border-radius: 18px !important;
  padding: 12px !important;
}

.main .matchup-mon-head {
  grid-template-columns: 92px minmax(0, 1fr) !important;
}

.main .matchup-sprite {
  width: 92px !important;
  height: 92px !important;
  padding: 4px !important;
  border-radius: 16px !important;
  background:
    radial-gradient(circle at 50% 46%, rgba(255,255,255,0.42), rgba(255,255,255,0.08) 60%, transparent 61%),
    rgba(214,207,244,0.88) !important;
}

.main .matchup-move-list {
  gap: 8px !important;
}

.main .matchup-move {
  border-radius: 999px !important;
}

/* Champions-style Pokemon detail sheet */
.main .champ-detail-layout {
  grid-template-columns: 0.92fr 1.05fr 1.05fr !important;
  gap: 14px !important;
  align-items: stretch !important;
}

.main .champ-detail-card {
  min-width: 0 !important;
  padding: 10px !important;
  border: 1px solid rgba(238,233,255,0.32) !important;
  border-radius: 18px !important;
  background:
    linear-gradient(130deg, rgba(255,255,255,0.1) 0 28%, transparent 28% 100%),
    linear-gradient(180deg, rgba(132,107,238,0.9), rgba(77,65,178,0.88)) !important;
  color: #ffffff !important;
  box-shadow: var(--poke-surface-glow), var(--poke-shadow-card) !important;
}

.main .champ-detail-header {
  border: 1px solid rgba(238,233,255,0.42) !important;
  border-radius: 999px !important;
  clip-path: none !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.05)),
    rgba(84,70,196,0.78) !important;
  color: #ffffff !important;
}

.main .champ-detail-header *,
.main .champ-detail-card > div:first-child *,
.main .champ-detail-tabs + .champ-detail-screen div:first-child {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

.main .champ-detail-level,
.main .champ-detail-item-value,
.main .champ-detail-stat-value,
.main .champ-detail-private-value,
.main .champ-detail-move-pp {
  border: 1px solid rgba(238,233,255,0.26) !important;
  border-radius: 999px !important;
  background:
    linear-gradient(180deg, rgba(222,216,248,0.92), rgba(199,192,230,0.92)) !important;
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.42) !important;
}

.main .champ-detail-sprite-stage {
  min-height: 206px !important;
  border: 1px solid rgba(238,233,255,0.26) !important;
  border-radius: 18px !important;
  background:
    radial-gradient(circle at 50% 46%, rgba(255,255,255,0.44), rgba(255,255,255,0.08) 60%, transparent 61%),
    linear-gradient(180deg, rgba(214,207,244,0.94), rgba(178,170,218,0.9)) !important;
}

.main .champ-detail-sprite-stage img {
  width: 158px !important;
  height: auto !important;
  filter: drop-shadow(0 8px 14px rgba(54,44,130,0.24)) !important;
}

.main .champ-detail-item-box {
  border: 1px solid rgba(238,233,255,0.28) !important;
  border-radius: 16px !important;
  overflow: hidden !important;
}

.main .champ-detail-item-label {
  border-bottom: 1px solid rgba(238,233,255,0.24) !important;
  background:
    linear-gradient(90deg, var(--accent) 0 6px, transparent 6px),
    linear-gradient(180deg, rgba(104,86,211,0.96), rgba(70,58,172,0.94)) !important;
  color: #ffffff !important;
}

.main .champ-detail-tabs {
  gap: 5px !important;
  margin-bottom: 8px !important;
}

.main .champ-detail-tab {
  width: 22px !important;
  height: 20px !important;
  border: 1px solid rgba(238,233,255,0.5) !important;
  border-radius: 6px !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.3), 0 4px 8px rgba(18,14,54,0.18) !important;
}

.main .champ-detail-screen {
  border: 1px solid rgba(238,233,255,0.28) !important;
  border-radius: 16px !important;
  padding: 7px !important;
  background:
    linear-gradient(180deg, rgba(98,82,209,0.74), rgba(69,58,170,0.74)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.18) !important;
}

.main .champ-detail-ps-row,
.main .champ-detail-stat-row,
.main .champ-detail-private-row {
  margin-bottom: 7px !important;
  padding: 7px 8px !important;
  border: 1px solid rgba(238,233,255,0.22) !important;
  border-radius: 14px !important;
  background: rgba(255,255,255,0.07) !important;
  color: #ffffff !important;
}

.main .champ-detail-stat-row > div:first-child,
.main .champ-detail-ps-row > div:first-child,
.main .champ-detail-private-row > div:first-child {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  font-family: var(--font-pixel) !important;
  text-transform: uppercase !important;
}

.main .champ-detail-bar {
  height: 12px !important;
  border-radius: 999px !important;
  border: 1px solid rgba(238,233,255,0.22) !important;
  background: rgba(52,44,133,0.42) !important;
}

.main .champ-detail-bar > div {
  border-radius: 999px !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.36) !important;
}

.main .champ-detail-ability-desc {
  margin-bottom: 7px !important;
  border: 1px solid rgba(238,233,255,0.18) !important;
  border-radius: 14px !important;
  background: rgba(255,255,255,0.06) !important;
  color: rgba(255,255,255,0.88) !important;
  -webkit-text-fill-color: rgba(255,255,255,0.88) !important;
}

.main .champ-detail-move-screen {
  display: grid !important;
  gap: 8px !important;
}

.main .champ-detail-move-row {
  grid-template-columns: minmax(78px, auto) minmax(0, 1fr) auto !important;
  gap: 9px !important;
  padding: 6px 8px !important;
  border: 1px solid rgba(238,233,255,0.28) !important;
  border-radius: 999px !important;
  background:
    linear-gradient(136deg, transparent 0 73%, rgba(255,117,221,0.14) 73% 100%),
    linear-gradient(180deg, rgba(222,216,248,0.94), rgba(199,192,230,0.94)) !important;
  color: var(--champ-text) !important;
}

.main .champ-detail-move-type {
  min-width: 72px !important;
  border-radius: 8px !important;
  border: 1px solid rgba(238,233,255,0.62) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.28), 0 3px 6px rgba(18,14,54,0.2) !important;
}

.main .champ-detail-move-name {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
  font-family: var(--font-ui) !important;
  font-weight: 800 !important;
}

.main .champ-detail-move-pp {
  gap: 5px !important;
  min-width: 64px !important;
  justify-content: center !important;
}

.main .champ-detail-move-pp span {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

@media (max-width: 1100px) {
  .main .champ-detail-layout {
    grid-template-columns: 1fr !important;
  }
}

.main .app-notice {
  background:
    linear-gradient(136deg, transparent 0 72%, rgba(255,117,221,0.14) 72% 100%),
    linear-gradient(180deg, rgba(222,216,248,0.92), rgba(199,192,230,0.92)) !important;
}

.main .app-notice-title,
.main .app-notice-body,
.main .app-notice-time {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

section[data-testid="stSidebar"] .app-notice {
  background:
    linear-gradient(136deg, transparent 0 72%, rgba(255,117,221,0.14) 72% 100%),
    linear-gradient(180deg, rgba(222,216,248,0.92), rgba(199,192,230,0.92)) !important;
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
    linear-gradient(130deg, rgba(255,255,255,0.11) 0 28%, transparent 28% 100%),
    linear-gradient(180deg, rgba(255,255,255,0.14), rgba(255,255,255,0.06)),
    rgba(72, 59, 182, 0.82) !important;
}

section[data-testid="stSidebar"] .profile-head {
  gap: 12px !important;
  align-items: center !important;
}

section[data-testid="stSidebar"] .profile-avatar {
  width: 76px !important;
  height: 76px !important;
  flex: 0 0 76px !important;
  border-radius: 18px !important;
  background:
    radial-gradient(circle at 50% 48%, rgba(255,255,255,0.46), rgba(255,255,255,0.08) 58%, transparent 59%),
    linear-gradient(180deg, rgba(229,222,252,0.94), rgba(179,171,222,0.9)) !important;
}

section[data-testid="stSidebar"] .profile-avatar img {
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
}

section[data-testid="stSidebar"] .profile-name {
  font-size: 14px !important;
  line-height: 1.08 !important;
}

section[data-testid="stSidebar"] .profile-sub {
  margin-top: 4px !important;
  font-size: 15px !important;
  line-height: 1.08 !important;
}

section[data-testid="stSidebar"] .mini-team {
  display: grid !important;
  grid-template-columns: repeat(6, minmax(0, 1fr)) !important;
  gap: 7px !important;
  margin-top: 12px !important;
}

section[data-testid="stSidebar"] .mini-mon {
  width: 100% !important;
  aspect-ratio: 1 / 1 !important;
  height: auto !important;
  min-height: 36px !important;
  padding: 2px !important;
  border-radius: 12px !important;
  background:
    linear-gradient(140deg, transparent 0 62%, rgba(255,117,221,0.16) 62% 78%, rgba(69,209,255,0.14) 78% 100%),
    linear-gradient(180deg, rgba(222,216,248,0.96), rgba(188,180,225,0.94)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.42), 0 5px 10px rgba(18,14,54,0.22) !important;
}

section[data-testid="stSidebar"] .mini-mon img {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain !important;
  transform: scale(1.28) !important;
  filter: drop-shadow(0 3px 4px rgba(18,14,54,0.28)) !important;
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

.main .poke-type-chip,
section[data-testid="stSidebar"] .poke-type-chip {
  --type-color: #999999;
  --type-fg: #ffffff;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 5px !important;
  min-width: 28px !important;
  min-height: 25px !important;
  padding: 3px 7px !important;
  border: 1px solid rgba(255,255,255,0.58) !important;
  border-radius: 5px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.24), rgba(0,0,0,0.18)),
    var(--type-color) !important;
  color: var(--type-fg) !important;
  -webkit-text-fill-color: var(--type-fg) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -2px 0 rgba(0,0,0,0.18), 0 3px 6px rgba(18,14,54,0.22) !important;
  vertical-align: middle !important;
}

.main .poke-type-chip.is-compact,
section[data-testid="stSidebar"] .poke-type-chip.is-compact {
  width: 26px !important;
  min-width: 26px !important;
  height: 26px !important;
  min-height: 26px !important;
  padding: 0 !important;
}

.main .poke-type-chip.has-label,
section[data-testid="stSidebar"] .poke-type-chip.has-label {
  width: auto !important;
  min-width: 74px !important;
  padding: 4px 8px !important;
}

.main .poke-type-icon,
section[data-testid="stSidebar"] .poke-type-icon {
  display: inline-grid !important;
  place-items: center !important;
  width: 18px !important;
  height: 18px !important;
  color: var(--type-fg) !important;
  -webkit-text-fill-color: var(--type-fg) !important;
  filter: drop-shadow(0 1px 0 rgba(0,0,0,0.28)) !important;
}

.main .poke-type-icon svg,
section[data-testid="stSidebar"] .poke-type-icon svg,
.main .poke-type-icon-img,
section[data-testid="stSidebar"] .poke-type-icon-img {
  display: block !important;
  width: 17px !important;
  height: 17px !important;
  object-fit: contain !important;
}

.main .poke-type-icon svg,
section[data-testid="stSidebar"] .poke-type-icon svg {
  fill: currentColor !important;
  stroke: currentColor !important;
}

.main .poke-type-label,
section[data-testid="stSidebar"] .poke-type-label {
  color: var(--type-fg) !important;
  -webkit-text-fill-color: var(--type-fg) !important;
  font-family: var(--font-pixel) !important;
  font-size: 8px !important;
  font-weight: 800 !important;
  line-height: 1 !important;
  text-transform: uppercase !important;
  text-shadow: 0 1px 0 rgba(0,0,0,0.28) !important;
}

/* Final Champions pass: sidebar controls, PC box, detail sheet and team preview */
section[data-testid="stSidebar"] .stPopover > div > button,
section[data-testid="stSidebar"] div[data-testid="stExpander"] details,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
  position: relative !important;
  overflow: hidden !important;
  border: 1px solid rgba(238,233,255,0.34) !important;
  border-radius: 14px !important;
  background:
    linear-gradient(136deg, transparent 0 70%, rgba(255,117,221,0.18) 70% 82%, rgba(69,209,255,0.18) 82% 100%),
    linear-gradient(180deg, rgba(222,216,248,0.96), rgba(199,192,230,0.95)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.46), 0 9px 20px rgba(18,14,54,0.18) !important;
}

section[data-testid="stSidebar"] .stPopover > div > button {
  min-height: 45px !important;
  justify-content: flex-start !important;
}

section[data-testid="stSidebar"] .stPopover > div > button *,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary *,
section[data-testid="stSidebar"] div[data-testid="stExpander"] details * {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

section[data-testid="stSidebar"] .stPopover > div > button [data-testid="stIconMaterial"],
section[data-testid="stSidebar"] .stPopover > div > button [class*="material-symbol"],
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary [data-testid="stIconMaterial"],
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary [class*="material-symbol"] {
  display: none !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] details {
  padding: 0 !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
  min-height: 42px !important;
  padding: 10px 14px !important;
  font-family: var(--font-ui) !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  text-transform: uppercase !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
  border: 0 !important;
  background: rgba(48,40,132,0.42) !important;
}

section[data-testid="stSidebar"] .profile-card {
  padding: 14px !important;
  border-radius: 18px !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.12) 0 34%, transparent 34% 100%),
    linear-gradient(180deg, rgba(125,101,232,0.9), rgba(75,64,174,0.88)) !important;
}

section[data-testid="stSidebar"] .profile-avatar {
  width: 84px !important;
  height: 84px !important;
  flex-basis: 84px !important;
  border-radius: 18px !important;
}

section[data-testid="stSidebar"] .mini-team {
  grid-template-columns: repeat(6, minmax(34px, 1fr)) !important;
  justify-content: stretch !important;
  gap: 7px !important;
}

section[data-testid="stSidebar"] .mini-mon {
  min-height: 40px !important;
  border-radius: 12px !important;
}

section[data-testid="stSidebar"] .mini-mon img {
  transform: scale(1.42) !important;
}

.main .champ-box-grid-shell {
  margin-top: 10px !important;
  padding: 12px !important;
  border: 1px solid rgba(238,233,255,0.34) !important;
  border-radius: 20px !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.1) 0 24%, transparent 24% 100%),
    linear-gradient(180deg, rgba(125,101,232,0.82), rgba(73,62,171,0.78)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.22), 0 12px 26px rgba(18,14,54,0.22) !important;
}

.main .champ-box-grid-toolbar {
  display: grid !important;
  grid-template-columns: auto minmax(130px, 1fr) auto minmax(130px, 1fr) !important;
  gap: 8px !important;
  align-items: center !important;
  margin-bottom: 11px !important;
}

.main .champ-box-grid-toolbar span,
.main .champ-box-grid-toolbar strong {
  min-height: 34px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  border-radius: 999px !important;
  border: 1px solid rgba(238,233,255,0.36) !important;
  background:
    linear-gradient(136deg, transparent 0 72%, rgba(255,117,221,0.14) 72% 100%),
    linear-gradient(180deg, rgba(238,233,255,0.95), rgba(211,204,237,0.94)) !important;
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
  font-family: var(--font-ui) !important;
  font-weight: 900 !important;
  font-size: 12px !important;
}

.main .champ-box-grid-toolbar span {
  min-width: 42px !important;
  font-family: var(--font-pixel) !important;
  background:
    linear-gradient(180deg, rgba(96,80,215,0.96), rgba(62,52,160,0.96)) !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

.main .champ-box-grid {
  display: grid !important;
  grid-template-columns: repeat(6, minmax(70px, 1fr)) !important;
  gap: 10px !important;
}

.main .champ-box-tile-link {
  display: block !important;
  width: 100% !important;
  text-decoration: none !important;
  outline: none !important;
}

.main .champ-box-tile {
  position: relative !important;
  display: grid !important;
  place-items: center !important;
  min-height: 84px !important;
  aspect-ratio: 1 / 1 !important;
  overflow: hidden !important;
  border: 1px solid rgba(238,233,255,0.4) !important;
  border-radius: 13px !important;
  background:
    linear-gradient(142deg, rgba(255,255,255,0.14) 0 34%, transparent 34% 100%),
    linear-gradient(180deg, rgba(224,219,249,0.96), rgba(190,183,225,0.96)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.5), 0 8px 17px rgba(18,14,54,0.18) !important;
  transition: transform .13s ease, border-color .13s ease, filter .13s ease, box-shadow .13s ease !important;
}

.main .champ-box-tile::before {
  content: "" !important;
  position: absolute !important;
  inset: 5px !important;
  border-radius: 10px !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  background:
    linear-gradient(136deg, transparent 0 68%, rgba(255,117,221,0.16) 68% 82%, rgba(69,209,255,0.16) 82% 100%) !important;
  pointer-events: none !important;
}

.main .champ-box-tile img {
  position: relative !important;
  z-index: 1 !important;
  width: 86% !important;
  height: 86% !important;
  object-fit: contain !important;
  image-rendering: pixelated !important;
  transform: scale(1.14) !important;
  filter: drop-shadow(0 5px 8px rgba(18,14,54,0.26)) !important;
}

.main .champ-box-tile-link:hover .champ-box-tile,
.main .champ-box-tile-link:focus-visible .champ-box-tile {
  transform: translateY(-2px) !important;
  border-color: rgba(246,216,59,0.95) !important;
  background:
    linear-gradient(136deg, transparent 0 70%, rgba(255,255,255,0.25) 70% 100%),
    linear-gradient(180deg, var(--champ-lime), var(--champ-lime-2)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.52), 0 0 0 3px rgba(246,216,59,0.18), 0 12px 23px rgba(18,14,54,0.24) !important;
}

.main .champ-box-tile-link:hover .champ-box-tile::after,
.main .champ-box-tile-link:focus-visible .champ-box-tile::after {
  content: "" !important;
  position: absolute !important;
  left: 5px !important;
  top: 50% !important;
  transform: translateY(-50%) !important;
  width: 0 !important;
  height: 0 !important;
  border-top: 9px solid transparent !important;
  border-bottom: 9px solid transparent !important;
  border-left: 0 !important;
  border-right: 14px solid var(--champ-yellow) !important;
  z-index: 2 !important;
}

.main .champ-box-tile-empty {
  opacity: .42 !important;
  border-style: dashed !important;
  background:
    linear-gradient(142deg, rgba(255,255,255,0.08) 0 34%, transparent 34% 100%),
    rgba(190,183,225,0.42) !important;
}

.main .champ-detail-layout {
  grid-template-columns: minmax(310px, .78fr) minmax(330px, 1fr) minmax(330px, 1fr) !important;
  gap: 18px !important;
}

.main .champ-detail-card {
  border-radius: 18px !important;
  border-color: rgba(238,233,255,0.34) !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.12) 0 33%, transparent 33% 100%),
    linear-gradient(180deg, rgba(125,101,232,0.9), rgba(73,62,171,0.9)) !important;
}

.main .champ-detail-main {
  max-width: 430px !important;
}

.main .champ-detail-header {
  min-height: 38px !important;
  border-radius: 12px !important;
  background:
    linear-gradient(180deg, var(--champ-cyan), #249bdb) !important;
}

.main .champ-detail-level,
.main .champ-detail-item-value,
.main .champ-detail-stat-value,
.main .champ-detail-private-value,
.main .champ-detail-move-pp {
  border-radius: 9px !important;
  background:
    linear-gradient(180deg, rgba(238,233,255,0.95), rgba(207,199,235,0.94)) !important;
}

.main .champ-detail-sprite-stage {
  min-height: 238px !important;
  border-radius: 14px !important;
  background:
    repeating-linear-gradient(0deg, rgba(255,255,255,0.08) 0 2px, transparent 2px 5px),
    radial-gradient(circle at 50% 54%, rgba(255,255,255,0.38), rgba(255,255,255,0.06) 48%, transparent 49%),
    linear-gradient(180deg, rgba(95,80,205,0.88), rgba(69,58,170,0.88)) !important;
}

.main .champ-detail-sprite-stage img {
  width: 190px !important;
  max-height: 210px !important;
  object-fit: contain !important;
  transform: scale(1.08) !important;
}

.main .champ-detail-screen {
  border-radius: 16px !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.09) 0 31%, transparent 31% 100%),
    linear-gradient(180deg, rgba(96,80,205,0.82), rgba(69,58,170,0.82)) !important;
}

.main .champ-detail-ps-row,
.main .champ-detail-stat-row,
.main .champ-detail-private-row {
  border-radius: 12px !important;
  background: rgba(255,255,255,0.09) !important;
}

.main .champ-detail-move-row {
  min-height: 48px !important;
  grid-template-columns: minmax(82px, auto) minmax(0, 1fr) auto !important;
  border-radius: 13px !important;
  background:
    linear-gradient(136deg, transparent 0 74%, rgba(255,117,221,0.13) 74% 100%),
    linear-gradient(180deg, rgba(238,233,255,0.96), rgba(211,204,237,0.96)) !important;
}

.main .champ-detail-move-type {
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.main .champ-detail-type-chip.poke-type-chip {
  min-width: 82px !important;
  height: 27px !important;
  border-radius: 5px !important;
}

.main .battle-board {
  border-radius: 20px !important;
  border-color: rgba(238,233,255,0.36) !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.1) 0 22%, transparent 22% 100%),
    linear-gradient(180deg, rgba(120,98,232,0.88), rgba(68,58,166,0.88)) !important;
}

.main .battle-board-top > div {
  border-radius: 14px !important;
  border-left: 0 !important;
  background:
    linear-gradient(136deg, transparent 0 74%, rgba(255,117,221,0.14) 74% 100%),
    linear-gradient(180deg, rgba(238,233,255,0.18), rgba(238,233,255,0.06)) !important;
}

.main .battle-mon-card {
  min-height: 180px !important;
  border-radius: 16px !important;
  background:
    linear-gradient(116deg, rgba(255,255,255,0.1) 0 35%, transparent 35% 100%),
    linear-gradient(180deg, rgba(119,98,229,0.9), rgba(72,62,172,0.9)) !important;
}

.main .battle-card-left {
  border-radius: 14px !important;
  background: rgba(255,255,255,0.08) !important;
}

.main .battle-sprite-wrap {
  min-height: 120px !important;
  border-radius: 16px !important;
}

.main .battle-sprite {
  width: 116px !important;
  height: 116px !important;
}

.main .battle-move-link,
.main .battle-no-move,
.main .matchup-move {
  border-radius: 14px !important;
  background:
    linear-gradient(136deg, transparent 0 74%, rgba(255,117,221,0.14) 74% 100%),
    linear-gradient(180deg, rgba(238,233,255,0.96), rgba(211,204,237,0.96)) !important;
}

.main .battle-move-row[open] > .battle-move-link,
.main .battle-move-link:hover {
  background:
    linear-gradient(136deg, transparent 0 70%, rgba(255,255,255,0.22) 70% 100%),
    linear-gradient(180deg, var(--champ-lime), var(--champ-lime-2)) !important;
}

.main .matchup-mon {
  border-radius: 16px !important;
  background:
    linear-gradient(116deg, rgba(255,255,255,0.1) 0 35%, transparent 35% 100%),
    linear-gradient(180deg, rgba(119,98,229,0.9), rgba(72,62,172,0.9)) !important;
}

.main .matchup-sprite {
  width: 108px !important;
  height: 108px !important;
  transform: scale(1.08) !important;
}

.main .battle-types .poke-type-chip.has-label.battle-type-dot,
.main .battle-type-pill.poke-type-chip {
  width: auto !important;
  min-width: 78px !important;
  padding: 4px 8px !important;
}

.main .poke-type-chip.uses-asset,
section[data-testid="stSidebar"] .poke-type-chip.uses-asset {
  width: auto !important;
  min-width: 0 !important;
  height: auto !important;
  min-height: 0 !important;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  line-height: 0 !important;
  overflow: visible !important;
}

.main .poke-type-chip.asset-icon,
section[data-testid="stSidebar"] .poke-type-chip.asset-icon,
.main .battle-type-dot.asset-icon {
  width: 26px !important;
  min-width: 26px !important;
  height: 26px !important;
  min-height: 26px !important;
  flex: 0 0 26px !important;
}

.main .poke-type-icon-img,
section[data-testid="stSidebar"] .poke-type-icon-img {
  display: block !important;
  width: 26px !important;
  height: 26px !important;
  object-fit: contain !important;
  border-radius: 5px !important;
  image-rendering: auto !important;
  filter: drop-shadow(0 2px 3px rgba(18,14,54,0.28)) !important;
}

.main .poke-type-chip.asset-full,
section[data-testid="stSidebar"] .poke-type-chip.asset-full,
.main .battle-type-pill.poke-type-chip.asset-full,
.main .champ-detail-type-chip.poke-type-chip.asset-full {
  width: 82px !important;
  min-width: 82px !important;
  height: 17px !important;
  min-height: 17px !important;
  flex: 0 0 auto !important;
}

.main .battle-type-pill.poke-type-chip.asset-full,
.main .champ-detail-type-chip.poke-type-chip.asset-full {
  width: 96px !important;
  min-width: 96px !important;
  height: 19px !important;
  min-height: 19px !important;
}

.main .poke-type-full-img,
section[data-testid="stSidebar"] .poke-type-full-img {
  display: block !important;
  width: 100% !important;
  height: 100% !important;
  object-fit: contain !important;
  image-rendering: auto !important;
  filter: drop-shadow(0 2px 3px rgba(18,14,54,0.22)) !important;
}

.main .slot .types {
  align-items: center !important;
  gap: 6px !important;
}

.main .battle-move-link .poke-type-chip.asset-icon,
.main .matchup-move .poke-type-chip.asset-icon {
  margin-left: -1px !important;
}

.main .battle-detail-stats .battle-detail-stat-type,
.main .battle-move-detail-inline .battle-detail-stats .battle-detail-stat-type {
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  align-self: center !important;
}

.main .battle-detail-stats .battle-detail-stat-type > span,
.main .battle-move-detail-inline .battle-detail-stats .battle-detail-stat-type > span {
  display: none !important;
}

.main .battle-detail-stats .battle-detail-stat-type > strong,
.main .battle-move-detail-inline .battle-detail-stats .battle-detail-stat-type > strong {
  margin: 0 !important;
  line-height: 0 !important;
}

.main .battle-detail-stats .battle-detail-stat-type .battle-type-pill.poke-type-chip.asset-full,
.main .battle-move-detail-inline .battle-detail-stats .battle-detail-stat-type .battle-type-pill.poke-type-chip.asset-full {
  width: 120px !important;
  min-width: 120px !important;
  height: 24px !important;
  min-height: 24px !important;
}

/* Final Champions polish: calmer premium shell, clearer menu surfaces and stronger Pokemon focus */
:root {
  --champ-bg-0: #151234;
  --champ-bg-1: #2d2577;
  --champ-bg-2: #17649d;
  --champ-panel: rgba(73, 62, 177, 0.86);
  --champ-panel-2: rgba(105, 86, 216, 0.88);
  --champ-panel-3: rgba(126, 104, 236, 0.9);
  --champ-panel-deep: rgba(40, 34, 122, 0.94);
  --champ-list: rgba(241, 238, 255, 0.96);
  --champ-list-2: rgba(213, 207, 239, 0.96);
  --champ-text: #273869;
  --champ-text-soft: #53608f;
  --champ-muted: #777fa8;
  --champ-lime: #b9ef32;
  --champ-lime-2: #91d909;
  --champ-yellow: #ffe14a;
  --champ-pink: #ff8ee3;
  --champ-cyan: #4fd6ff;
  --champ-coral: #ff7d70;
  --poke-radius-sm: 12px;
  --poke-radius: 16px;
  --poke-radius-xl: 22px;
  --poke-shadow-soft: 0 24px 54px rgba(14, 11, 48, 0.32);
  --poke-shadow-card: 0 14px 30px rgba(14, 11, 48, 0.24);
}

.stApp {
  background:
    linear-gradient(126deg, rgba(255,255,255,0.075) 0 11%, transparent 11% 100%) 0 86px / 430px 270px,
    linear-gradient(38deg, rgba(255,255,255,0.055) 0 9%, transparent 9% 100%) 100% 180px / 390px 260px,
    radial-gradient(circle at 12% 6%, rgba(255,142,227,0.18), transparent 330px),
    radial-gradient(circle at 88% 10%, rgba(79,214,255,0.18), transparent 360px),
    linear-gradient(180deg, var(--champ-bg-0) 0%, var(--champ-bg-1) 48%, var(--champ-bg-2) 100%) !important;
}

.stApp::before {
  height: 42px !important;
  background:
    linear-gradient(90deg, rgba(255,225,74,0.96) 0 7%, rgba(116,97,232,0.98) 7% 54%, rgba(79,214,255,0.96) 54% 78%, rgba(255,142,227,0.96) 78% 100%) !important;
  border-bottom: 1px solid rgba(246, 242, 255, 0.42) !important;
  box-shadow: 0 12px 28px rgba(14, 11, 48, 0.32) !important;
}

.stApp::after {
  display: none !important;
  content: "" !important;
}

.main .block-container {
  max-width: 1500px !important;
  padding-top: 4.25rem !important;
}

section[data-testid="stSidebar"] {
  background:
    linear-gradient(128deg, rgba(255,255,255,0.08) 0 17%, transparent 17% 100%) 0 90px / 280px 210px,
    radial-gradient(circle at 50% 0%, rgba(79,214,255,0.16), transparent 250px),
    linear-gradient(180deg, rgba(54, 45, 154, 0.98), rgba(38, 32, 124, 0.97) 58%, rgba(24, 80, 145, 0.96)) !important;
  border-right: 1px solid rgba(246,242,255,0.34) !important;
}

section[data-testid="stSidebar"]::before {
  display: none !important;
}

section[data-testid="stSidebar"] .block-container {
  padding-top: 1.55rem !important;
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
.main .saves-hero {
  border-radius: 24px !important;
  border: 1px solid rgba(246,242,255,0.38) !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.12) 0 24%, transparent 24% 100%),
    linear-gradient(300deg, rgba(255,142,227,0.16), transparent 48%),
    linear-gradient(180deg, rgba(113, 92, 223, 0.88), rgba(52, 44, 148, 0.9)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.25), 0 24px 50px rgba(14,11,48,0.3) !important;
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
.main .saves-title {
  font-size: clamp(27px, 3vw, 42px) !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
  text-shadow: 0 5px 18px rgba(27, 22, 92, 0.36) !important;
}

.main .home-kicker,
.main .auth-kicker,
.main .matchup-kicker,
.main .cup-kicker,
.main .mart-kicker,
.main .league-kicker,
.main .season-kicker,
.main .saves-kicker,
.main .mart-pill,
.main .cup-pill,
.main .season-pill,
.main .trainers-chip,
.main .hof-team-pill,
.main .saves-card-badge {
  border: 1px solid rgba(246,242,255,0.42) !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.2), rgba(255,255,255,0.06)),
    rgba(59, 50, 165, 0.72) !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
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
  border-radius: 999px !important;
  padding: 9px 15px !important;
  background:
    linear-gradient(100deg, rgba(255,255,255,0.24), transparent 72%),
    linear-gradient(180deg, rgba(101,86,218,0.98), rgba(69,58,178,0.96)) !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

.main .home-card,
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
.main .battle-board,
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
.main .saves-current-card,
.main .saves-stat,
.main .pl-card,
.main .pt-metric,
.main .pt-section,
.main .trainer-panel {
  border: 1px solid rgba(246,242,255,0.3) !important;
  border-radius: 20px !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.1) 0 26%, transparent 26% 100%),
    linear-gradient(180deg, rgba(103, 85, 216, 0.78), rgba(48, 41, 139, 0.76)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 16px 34px rgba(14,11,48,0.22) !important;
}

.main .home-action-card,
.main .auth-trainer-card,
.main .matchup-mode-card,
.main .cup-mode-card,
.main .season-version-row,
.main .app-notice,
.main .saves-history-card,
.main .pokedex-card,
.main .slot,
.main .slot-empty,
.main .shop-card,
.main .matchup-move,
.main .battle-move-link,
.main .battle-no-move,
.main div[data-testid="stTabs"] button[data-baseweb="tab"],
.main div[data-testid="stTabs"] button[role="tab"],
section[data-testid="stSidebar"] div[role="radiogroup"] label,
section[data-testid="stSidebar"] .stPopover > div > button,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
  border: 1px solid rgba(246,242,255,0.48) !important;
  border-radius: 16px !important;
  background:
    linear-gradient(136deg, transparent 0 70%, rgba(255,142,227,0.16) 70% 84%, rgba(79,214,255,0.16) 84% 100%),
    linear-gradient(180deg, var(--champ-list), var(--champ-list-2)) !important;
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.54), 0 10px 22px rgba(14,11,48,0.18) !important;
}

.main .home-action-card *,
.main .auth-trainer-card *,
.main .matchup-mode-card *,
.main .cup-mode-card *,
.main .season-version-row *,
.main .saves-history-card *,
.main .pokedex-card *,
.main .slot *,
.main .slot-empty *,
.main .shop-card *,
.main .matchup-move span:last-child,
.main .battle-move-link span:last-child,
section[data-testid="stSidebar"] div[role="radiogroup"] label *,
section[data-testid="stSidebar"] .stPopover > div > button *,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary * {
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

section[data-testid="stSidebar"] .profile-card {
  margin-bottom: 14px !important;
  border: 1px solid rgba(246,242,255,0.34) !important;
  border-radius: 22px !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.12) 0 31%, transparent 31% 100%),
    linear-gradient(180deg, rgba(113,92,223,0.86), rgba(48,41,139,0.84)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 15px 31px rgba(14,11,48,0.24) !important;
}

section[data-testid="stSidebar"] .profile-card *,
section[data-testid="stSidebar"] .sidebar-nav-title {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

section[data-testid="stSidebar"] .profile-avatar {
  width: 92px !important;
  height: 92px !important;
  flex-basis: 92px !important;
  border-radius: 20px !important;
}

section[data-testid="stSidebar"] .mini-team {
  grid-template-columns: repeat(6, minmax(36px, 1fr)) !important;
}

section[data-testid="stSidebar"] .mini-mon {
  min-height: 42px !important;
  border-radius: 13px !important;
}

section[data-testid="stSidebar"] .mini-mon img {
  transform: scale(1.48) !important;
}

section[data-testid="stSidebar"] .sidebar-nav-title {
  margin: 8px 0 10px !important;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.18), transparent 72%),
    rgba(48, 41, 139, 0.62) !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] {
  gap: 9px !important;
  overflow: visible !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label {
  min-height: 50px !important;
  padding: 0.7rem 0.95rem 0.7rem 1.05rem !important;
  overflow: visible !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label::before {
  opacity: 0 !important;
  left: -18px !important;
  width: 0 !important;
  height: 0 !important;
  border-top: 14px solid transparent !important;
  border-bottom: 14px solid transparent !important;
  border-left: 0 !important;
  border-right: 19px solid var(--champ-yellow) !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before {
  opacity: 1 !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked),
.main div[data-testid="stTabs"] button[aria-selected="true"],
.main button[data-baseweb="tab"][aria-selected="true"],
.main button[role="tab"][aria-selected="true"],
.main .matchup-mode-card.is-active,
.main .cup-mode-card.is-active,
.main .battle-move-row[open] > .battle-move-link,
.main .battle-move-link:hover,
.main .stButton > button[kind="primary"],
section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
  border-color: rgba(255,225,74,0.95) !important;
  background:
    linear-gradient(136deg, transparent 0 70%, rgba(255,255,255,0.24) 70% 100%),
    linear-gradient(180deg, var(--champ-lime), var(--champ-lime-2)) !important;
  color: #243c68 !important;
  -webkit-text-fill-color: #243c68 !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.58), 0 0 0 3px rgba(255,225,74,0.18), 0 13px 25px rgba(14,11,48,0.24) !important;
}

.main .stButton > button,
.main .stDownloadButton > button,
.main form button {
  border-radius: 16px !important;
  min-height: 46px !important;
}

.main .stTextInput input,
.main .stNumberInput input,
.main .stTextArea textarea,
.main .stSelectbox [data-baseweb="select"],
.main .stMultiSelect [data-baseweb="select"],
.main .stDateInput input {
  border-radius: 16px !important;
  background:
    linear-gradient(136deg, transparent 0 72%, rgba(255,142,227,0.12) 72% 100%),
    linear-gradient(180deg, rgba(248,246,255,0.97), rgba(218,212,242,0.96)) !important;
}

div[data-baseweb="popover"],
div[data-baseweb="popover"] ul,
div[data-baseweb="menu"] {
  border-radius: 18px !important;
  background:
    linear-gradient(180deg, rgba(86,72,198,0.98), rgba(36,31,116,0.98)) !important;
}

div[data-baseweb="popover"] li,
div[data-baseweb="menu"] li,
div[role="option"] {
  border-radius: 14px !important;
}

.main div[data-testid="stTabs"] div[data-baseweb="tab-list"],
.main div[data-testid="stTabs"] [role="tablist"],
.main div[data-baseweb="tab-list"] {
  border-radius: 20px !important;
  padding: 10px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.13), rgba(255,255,255,0.05)),
    rgba(50, 43, 150, 0.72) !important;
}

.main div[data-testid="stTabs"] button[data-baseweb="tab"],
.main div[data-testid="stTabs"] button[role="tab"] {
  min-height: 50px !important;
  padding: 0 22px !important;
}

.main .slot,
.main .slot-empty {
  min-height: 210px !important;
  padding: 10px !important;
  border-radius: 18px !important;
}

.main .slot img {
  width: min(100%, 122px) !important;
  height: 96px !important;
  transform: scale(1.08) !important;
  filter: drop-shadow(0 8px 10px rgba(54,44,130,0.28)) !important;
}

.main .slot .title {
  font-size: 10.5px !important;
}

.main .slot .sub {
  font-size: 16px !important;
}

.main .champ-box-grid-shell {
  border-radius: 22px !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.1) 0 24%, transparent 24% 100%),
    linear-gradient(180deg, rgba(113,92,223,0.8), rgba(48,41,139,0.78)) !important;
}

.main .champ-box-grid {
  grid-template-columns: repeat(6, minmax(78px, 1fr)) !important;
  gap: 11px !important;
}

.main .champ-box-tile {
  min-height: 92px !important;
  border-radius: 16px !important;
}

.main .champ-box-tile img {
  width: 90% !important;
  height: 90% !important;
  transform: scale(1.18) !important;
}

.main .champ-detail-card,
.main .battle-mon-card,
.main .matchup-mon {
  border-radius: 20px !important;
  border-color: rgba(246,242,255,0.36) !important;
  background:
    linear-gradient(124deg, rgba(255,255,255,0.12) 0 32%, transparent 32% 100%),
    linear-gradient(180deg, rgba(112,92,223,0.88), rgba(50,43,150,0.86)) !important;
}

.main .champ-detail-sprite-stage,
.main .battle-sprite-wrap,
.main .matchup-sprite,
.main .auth-avatar,
.main .trainers-portrait-xl,
.main .profile-avatar {
  background:
    radial-gradient(circle at 50% 48%, rgba(255,255,255,0.52), rgba(255,255,255,0.12) 58%, transparent 59%),
    linear-gradient(180deg, rgba(232,227,252,0.96), rgba(184,176,223,0.93)) !important;
}

.main .battle-mon-card {
  grid-template-columns: minmax(170px, .9fr) 132px minmax(250px, 1.18fr) !important;
}

.main .battle-sprite {
  width: 126px !important;
  height: 126px !important;
}

.main .matchup-sprite {
  width: 116px !important;
  height: 116px !important;
}

.main .battle-move-link,
.main .battle-no-move,
.main .matchup-move,
.main .champ-detail-move-row {
  min-height: 42px !important;
}

.main .battle-type-dot.asset-icon,
.main .matchup-move .poke-type-chip.asset-icon,
.main .battle-move-link .poke-type-chip.asset-icon {
  width: 28px !important;
  min-width: 28px !important;
  height: 28px !important;
  min-height: 28px !important;
}

.main .poke-type-icon-img,
section[data-testid="stSidebar"] .poke-type-icon-img {
  width: 28px !important;
  height: 28px !important;
}

.main .poke-type-chip.asset-full,
section[data-testid="stSidebar"] .poke-type-chip.asset-full {
  width: 92px !important;
  min-width: 92px !important;
  height: 19px !important;
  min-height: 19px !important;
}

.main .battle-type-pill.poke-type-chip.asset-full,
.main .champ-detail-type-chip.poke-type-chip.asset-full {
  width: 124px !important;
  min-width: 124px !important;
  height: 25px !important;
  min-height: 25px !important;
}

.main .shop-card {
  min-height: 250px !important;
  border-radius: 18px !important;
}

.main .shop-icon-slot {
  width: 84px !important;
  height: 84px !important;
}

.main .shop-body {
  grid-template-columns: 86px minmax(0, 1fr) !important;
  gap: 12px !important;
}

.main .shop-price {
  border-radius: 14px !important;
}

.main .shop-coin {
  font-size: 22px !important;
}

.main .shop-amount {
  font-size: 17px !important;
}

.main .app-notice-menu summary {
  border-radius: 16px !important;
  background:
    linear-gradient(136deg, transparent 0 70%, rgba(255,142,227,0.16) 70% 84%, rgba(79,214,255,0.16) 84% 100%),
    linear-gradient(180deg, var(--champ-list), var(--champ-list-2)) !important;
  color: var(--champ-text) !important;
  -webkit-text-fill-color: var(--champ-text) !important;
}

.main .app-notice-menu-panel {
  border-radius: 18px !important;
  background: rgba(36, 31, 116, 0.72) !important;
}

.main .shop-discount-badge,
.main .shop-discount-badge *,
.main .slot .shield-chip,
.main .slot .rob-chip,
.main .slot .pill,
.main .pokedex-card .shield-chip,
.main .pokedex-card .rob-chip,
.main .pokedex-card .pill,
.main .poke-type-chip.uses-fallback,
.main .poke-type-chip.uses-fallback *,
section[data-testid="stSidebar"] .poke-type-chip.uses-fallback,
section[data-testid="stSidebar"] .poke-type-chip.uses-fallback * {
  color: var(--type-fg, #ffffff) !important;
  -webkit-text-fill-color: var(--type-fg, #ffffff) !important;
}

.main .shop-discount-badge,
.main .shop-discount-badge * {
  --type-fg: #ffffff;
  text-shadow: 0 1px 0 rgba(0,0,0,0.24) !important;
}

.main .slot .pill-shiny,
.main .pokedex-card .pill-shiny {
  color: #1d1610 !important;
  -webkit-text-fill-color: #1d1610 !important;
}

@media (max-width: 980px) {
  .main .battle-mon-card {
    grid-template-columns: minmax(0, 1fr) !important;
  }
  .main .champ-box-grid {
    grid-template-columns: repeat(5, minmax(58px, 1fr)) !important;
  }
  .main .champ-box-tile {
    min-height: 64px !important;
  }
  .main .slot {
    min-height: 190px !important;
  }
}

.stApp .material-symbols-rounded,
.stApp .material-symbols-outlined,
.stApp .material-icons,
.stApp [class*="material-symbols"],
.stApp [class*="material-icons"],
.stApp span[data-testid="stIconMaterial"] {
  font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
  font-feature-settings: "liga" !important;
  -webkit-font-feature-settings: "liga" !important;
  letter-spacing: normal !important;
  text-transform: none !important;
  white-space: nowrap !important;
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
  .main .champ-box-grid {
    grid-template-columns: repeat(5, minmax(54px, 1fr)) !important;
    gap: 8px !important;
  }
  .main .champ-box-tile {
    min-height: 58px !important;
  }
  .main .champ-box-grid-toolbar {
    grid-template-columns: auto minmax(0, 1fr) !important;
  }
}

/* PokeApp 2.0 Phase 1: dark competitive client foundation */
:root {
  --font-ui: "Inter", "Manrope", "Nunito Sans", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --font-pixel: "Inter", "Manrope", "Nunito Sans", system-ui, sans-serif;

  --bg-main: #080b14;
  --bg-secondary: #0d1220;
  --bg-tertiary: #111827;
  --bg-elevated: #151d2e;

  --surface-1: #111827;
  --surface-2: #172033;
  --surface-3: #1c2740;
  --surface-hover: #202c46;
  --surface-glass: rgba(17, 24, 39, 0.84);

  --border-soft: rgba(255,255,255,0.06);
  --border-normal: rgba(255,255,255,0.1);
  --border-hover: rgba(255,255,255,0.18);

  --text-primary: #f5f7fa;
  --text-secondary: #b5c0d3;
  --text-muted: #7b879a;
  --text-inverse: #101827;

  --primary: #4d8dff;
  --primary-hover: #6aa0ff;
  --primary-soft: rgba(77,141,255,0.13);
  --pokemon-yellow: #ffcb3b;
  --pokemon-yellow-soft: rgba(255,203,59,0.14);
  --accent-purple: #785df6;
  --success: #43d17c;
  --warning: #ffb84a;
  --danger: #ff5263;
  --info: #4db8ff;

  --radius-input: 10px;
  --radius-card: 14px;
  --radius-large: 18px;
  --radius-modal: 20px;
  --shadow-card: 0 4px 16px rgba(0,0,0,0.18);
  --shadow-hero: 0 12px 32px rgba(0,0,0,0.24);
  --transition-fast: 160ms ease;

  --champ-bg-0: var(--bg-main);
  --champ-bg-1: var(--bg-secondary);
  --champ-bg-2: var(--bg-tertiary);
  --champ-panel: var(--surface-1);
  --champ-panel-2: var(--surface-2);
  --champ-panel-3: var(--surface-3);
  --champ-panel-deep: var(--bg-secondary);
  --champ-list: var(--surface-2);
  --champ-list-2: var(--surface-3);
  --champ-text: var(--text-primary);
  --champ-text-soft: var(--text-secondary);
  --champ-muted: var(--text-muted);
  --champ-lime: var(--primary);
  --champ-lime-2: #2f6fff;
  --champ-yellow: var(--pokemon-yellow);
  --champ-pink: var(--accent-purple);
  --champ-cyan: var(--info);

  --accent: var(--primary);
  --accent-dark: #2f6fff;
  --accent-soft: var(--primary-hover);
  --accent-ghost: var(--primary-soft);
  --bw2-bg-0: var(--bg-main);
  --bw2-bg-1: var(--bg-secondary);
  --bw2-bg-2: var(--bg-tertiary);
  --bw2-panel: var(--surface-1);
  --bw2-panel-2: var(--surface-2);
  --bw2-panel-3: var(--surface-3);
  --bw2-screen: var(--surface-1);
  --bw2-screen-2: var(--surface-2);
  --bw2-edge: var(--border-normal);
  --bw2-edge-strong: var(--border-hover);
  --bw2-text: var(--text-primary);
  --bw2-text-soft: var(--text-secondary);
  --bw2-text-dim: var(--text-muted);
  --poke-radius-sm: var(--radius-input);
  --poke-radius: var(--radius-card);
  --poke-radius-xl: var(--radius-large);
  --poke-shadow-soft: var(--shadow-hero);
  --poke-shadow-card: var(--shadow-card);
  --poke-surface-glow: inset 0 1px 0 rgba(255,255,255,0.04);
}

#MainMenu,
footer,
header[data-testid="stHeader"] {
  visibility: hidden !important;
}

html,
body,
.stApp {
  background: var(--bg-main) !important;
}

.stApp {
  color: var(--text-primary) !important;
  background:
    radial-gradient(circle at 78% -8%, rgba(77,141,255,0.08), transparent 340px),
    radial-gradient(circle at 12% 12%, rgba(255,203,59,0.032), transparent 280px),
    linear-gradient(120deg, transparent 0 88%, rgba(255,255,255,0.008) 88% 89%, transparent 89% 100%) 0 0 / 360px 250px,
    linear-gradient(180deg, var(--bg-main) 0%, #0c1220 45%, #10192b 100%) !important;
}

.stApp::before,
.stApp::after,
.main::before {
  display: none !important;
  content: "" !important;
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

.main .block-container {
  max-width: 1500px !important;
  padding: 24px 32px 56px !important;
  margin: 0 auto !important;
}

.main .poke-topbar {
  position: sticky !important;
  top: 0 !important;
  z-index: 50 !important;
  min-height: 52px !important;
  margin: 0 0 22px !important;
  padding: 9px 12px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  gap: 14px !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-card) !important;
  background: rgba(13,18,32,0.88) !important;
  box-shadow: 0 10px 28px rgba(0,0,0,0.2) !important;
  backdrop-filter: blur(16px) !important;
}

.main .poke-topbar-left,
.main .poke-topbar-right {
  min-width: 0 !important;
  display: flex !important;
  align-items: center !important;
  gap: 10px !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 13px !important;
  font-weight: 800 !important;
}

.main .poke-topbar-right {
  justify-content: flex-end !important;
}

.main .poke-topbar-round {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.main .poke-topbar-dot {
  width: 4px !important;
  height: 4px !important;
  border-radius: 50% !important;
  background: var(--border-hover) !important;
}

.main .poke-topbar-pill,
.main .poke-topbar-user {
  min-height: 34px !important;
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
  padding: 0 10px !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: 999px !important;
  background: var(--surface-1) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.main .poke-topbar-user span {
  width: 24px !important;
  height: 24px !important;
  display: inline-grid !important;
  place-items: center !important;
  border-radius: 50% !important;
  background: var(--primary-soft) !important;
  color: var(--primary-hover) !important;
  -webkit-text-fill-color: var(--primary-hover) !important;
  font-size: 10px !important;
  font-weight: 900 !important;
}

.main .poke-topbar-icon {
  width: 17px !important;
  height: 17px !important;
  position: relative !important;
  flex: 0 0 17px !important;
  display: inline-block !important;
  overflow: visible !important;
  color: var(--pokemon-yellow) !important;
  -webkit-text-fill-color: var(--pokemon-yellow) !important;
  fill: currentColor !important;
}

.main .poke-topbar-bell {
  width: 17px !important;
  height: 17px !important;
  border-radius: 9px 9px 6px 6px !important;
  background: linear-gradient(180deg, #ffe47a, #f2b733) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.45), 0 2px 5px rgba(18,14,54,0.22) !important;
}

.main .poke-topbar-bell::before {
  content: "" !important;
  position: absolute !important;
  left: 50% !important;
  top: -3px !important;
  width: 7px !important;
  height: 5px !important;
  transform: translateX(-50%) !important;
  border-radius: 999px 999px 0 0 !important;
  background: #ffe47a !important;
}

.main .poke-topbar-bell::after {
  content: "" !important;
  position: absolute !important;
  left: 50% !important;
  bottom: -4px !important;
  width: 7px !important;
  height: 7px !important;
  transform: translateX(-50%) !important;
  border-radius: 50% !important;
  background: #f7f2ff !important;
  box-shadow: 0 0 0 2px rgba(18,14,54,0.28) !important;
}

.main .poke-coin-mark {
  width: 18px !important;
  height: 18px !important;
  border-radius: 50% !important;
  background:
    radial-gradient(circle at 35% 30%, rgba(255,255,255,0.9), transparent 18%),
    linear-gradient(180deg, #ffe078, #d99b1f) !important;
  box-shadow: inset 0 0 0 2px rgba(100,64,0,0.28) !important;
}

.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4,
.stApp h5,
.stApp h6 {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-family: var(--font-ui) !important;
  font-weight: 800 !important;
  letter-spacing: 0 !important;
  text-transform: none !important;
  text-shadow: none !important;
}

.stApp p,
.stApp li,
.stApp label,
.stApp caption {
  color: var(--text-secondary) !important;
}

.stApp strong,
.stApp b {
  color: var(--text-primary) !important;
}

.stApp hr {
  height: 1px !important;
  margin: 24px 0 !important;
  background: var(--border-soft) !important;
}

section[data-testid="stSidebar"] {
  width: 248px !important;
  min-width: 248px !important;
  max-width: 248px !important;
  background:
    linear-gradient(180deg, rgba(77,141,255,0.06), transparent 36%),
    var(--bg-secondary) !important;
  border-right: 1px solid var(--border-soft) !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] .block-container {
  padding: 24px 14px !important;
}

section[data-testid="stSidebar"]::before {
  display: none !important;
  content: "POKEAPP\\A LEAGUE" !important;
  white-space: pre !important;
  position: static !important;
  margin: 0 0 18px !important;
  padding: 0 4px 18px !important;
  border: 0 !important;
  border-bottom: 1px solid var(--border-soft) !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-family: var(--font-ui) !important;
  font-size: 18px !important;
  font-weight: 900 !important;
  line-height: 1.05 !important;
  letter-spacing: 0.02em !important;
  text-align: left !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] .sidebar-brand {
  margin: 0 0 18px !important;
  padding: 18px 4px 20px !important;
  display: grid !important;
  grid-template-columns: 44px minmax(0, 1fr) !important;
  gap: 10px !important;
  align-items: center !important;
  border-bottom: 1px solid var(--border-soft) !important;
}

section[data-testid="stSidebar"] .sidebar-brand-mark {
  width: 42px !important;
  height: 42px !important;
  position: relative !important;
  display: grid !important;
  place-items: center !important;
  border: 1px solid var(--border-normal) !important;
  border-radius: 50% !important;
  background:
    linear-gradient(#ff5263 0 46%, #0b1020 46% 54%, #f5f7fa 54% 100%) !important;
  box-shadow: 0 8px 18px rgba(0,0,0,0.28) !important;
}

section[data-testid="stSidebar"] .sidebar-brand-mark::before {
  content: "" !important;
  position: absolute !important;
  left: 0 !important;
  right: 0 !important;
  top: calc(50% - 2px) !important;
  height: 4px !important;
  background: #0b1020 !important;
}

section[data-testid="stSidebar"] .sidebar-brand-mark span {
  position: relative !important;
  z-index: 1 !important;
  width: 14px !important;
  height: 14px !important;
  border: 3px solid #0b1020 !important;
  border-radius: 50% !important;
  background: #f5f7fa !important;
}

section[data-testid="stSidebar"] .sidebar-brand-name {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 20px !important;
  font-weight: 950 !important;
  line-height: 1 !important;
}

section[data-testid="stSidebar"] .sidebar-brand-sub {
  margin-top: 2px !important;
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
  font-size: 11px !important;
  font-weight: 850 !important;
  text-transform: uppercase !important;
}

section[data-testid="stSidebar"] .profile-card {
  margin: 0 0 18px !important;
  padding: 12px !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-large) !important;
  background: rgba(255,255,255,0.025) !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] .profile-head {
  display: grid !important;
  grid-template-columns: 54px minmax(0, 1fr) !important;
  gap: 10px !important;
  align-items: center !important;
}

section[data-testid="stSidebar"] .profile-avatar {
  width: 54px !important;
  height: 54px !important;
  flex-basis: 54px !important;
  border-radius: 14px !important;
  border: 1px solid var(--border-normal) !important;
  background: var(--surface-2) !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] .profile-avatar img {
  width: 100% !important;
  height: 100% !important;
  object-fit: cover !important;
}

section[data-testid="stSidebar"] .profile-name {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 15px !important;
  font-weight: 800 !important;
  line-height: 1.15 !important;
  text-transform: none !important;
}

section[data-testid="stSidebar"] .profile-sub {
  margin-top: 3px !important;
  color: var(--success) !important;
  -webkit-text-fill-color: var(--success) !important;
  font-size: 12px !important;
  line-height: 1.2 !important;
}

section[data-testid="stSidebar"] .badges-row {
  display: none !important;
}

section[data-testid="stSidebar"] .mini-team {
  display: grid !important;
  grid-template-columns: repeat(6, minmax(0, 1fr)) !important;
  gap: 6px !important;
  margin-top: 12px !important;
}

section[data-testid="stSidebar"] .mini-mon {
  width: 100% !important;
  min-height: 30px !important;
  aspect-ratio: 1 / 1 !important;
  border: 0 !important;
  border-radius: 8px !important;
  background: rgba(255,255,255,0.045) !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] .mini-mon img {
  width: 120% !important;
  height: 120% !important;
  object-fit: contain !important;
  transform: scale(1) !important;
  filter: drop-shadow(0 3px 4px rgba(0,0,0,0.32)) !important;
}

section[data-testid="stSidebar"] .sidebar-nav-title {
  margin: 16px 0 7px !important;
  padding: 0 4px !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
  font-size: 11px !important;
  font-weight: 800 !important;
  text-transform: uppercase !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] {
  display: grid !important;
  gap: 4px !important;
  overflow: visible !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label,
section[data-testid="stSidebar"] div.stButton > button,
section[data-testid="stSidebar"] .stPopover > div > button,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
  position: relative !important;
  min-height: 42px !important;
  padding: 9px 10px 9px 12px !important;
  justify-content: flex-start !important;
  text-align: left !important;
  gap: 10px !important;
  border: 1px solid transparent !important;
  border-radius: var(--radius-input) !important;
  background: transparent !important;
  box-shadow: none !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  transition: background-color var(--transition-fast), border-color var(--transition-fast), transform var(--transition-fast), color var(--transition-fast) !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label::before,
section[data-testid="stSidebar"] div[role="radiogroup"] label::after {
  display: none !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label p,
section[data-testid="stSidebar"] div.stButton > button p,
section[data-testid="stSidebar"] .stPopover > div > button *,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary * {
  margin: 0 !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 13px !important;
  font-weight: 700 !important;
  line-height: 1.15 !important;
  text-transform: none !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:hover,
section[data-testid="stSidebar"] div.stButton > button:hover {
  background: rgba(255,255,255,0.045) !important;
  border-color: var(--border-soft) !important;
  transform: translateY(-1px) !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked),
section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
  background: var(--primary-soft) !important;
  border-color: rgba(77,141,255,0.3) !important;
  border-left: 3px solid var(--primary) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p,
section[data-testid="stSidebar"] div.stButton > button[kind="primary"] p {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

section[data-testid="stSidebar"] .app-notice-menu {
  margin: 8px 0 12px !important;
}

section[data-testid="stSidebar"] .app-notice-menu summary {
  min-height: 38px !important;
  padding: 8px 10px !important;
  border-color: transparent !important;
  background: rgba(255,255,255,0.025) !important;
}

section[data-testid="stSidebar"] .app-notice-menu-panel {
  max-height: 260px !important;
  overflow: auto !important;
}

section[data-testid="stSidebar"] .app-notice {
  padding: 8px 9px !important;
  margin-bottom: 6px !important;
  box-shadow: none !important;
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
.main .saves-hero {
  padding: 20px !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-large) !important;
  background: linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.015)), var(--surface-1) !important;
  box-shadow: var(--shadow-card) !important;
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
.main .saves-title {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: clamp(28px, 2.8vw, 36px) !important;
  font-weight: 850 !important;
  line-height: 1.08 !important;
  text-transform: none !important;
  text-shadow: none !important;
}

.main .home-kicker,
.main .auth-kicker,
.main .matchup-kicker,
.main .cup-kicker,
.main .mart-kicker,
.main .league-kicker,
.main .season-kicker,
.main .saves-kicker,
.main .mart-pill,
.main .cup-pill,
.main .season-pill,
.main .trainers-chip,
.main .hof-team-pill,
.main .saves-card-badge {
  border: 1px solid var(--border-soft) !important;
  border-radius: 999px !important;
  background: rgba(77,141,255,0.08) !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  box-shadow: none !important;
}

.main .home-hero {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) !important;
  gap: 22px !important;
  align-items: center !important;
  min-height: 188px !important;
  padding: 24px !important;
  background:
    radial-gradient(circle at 50% 0, rgba(77,141,255,0.12), transparent 42%),
    linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015)),
    var(--surface-1) !important;
  box-shadow: var(--shadow-hero) !important;
}

.main .home-hero .home-title {
  font-size: clamp(28px, 4vw, 44px) !important;
  font-weight: 950 !important;
  line-height: 1.02 !important;
}

.main .home-hero .home-kicker {
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 12px !important;
}

.main .home-versus {
  width: 86px !important;
  height: 86px !important;
  display: grid !important;
  place-items: center !important;
  border: 1px solid var(--border-normal) !important;
  border-radius: 50% !important;
  background: var(--surface-2) !important;
  color: var(--pokemon-yellow) !important;
  -webkit-text-fill-color: var(--pokemon-yellow) !important;
  font-weight: 950 !important;
}

.main .home-side.home-right {
  text-align: right !important;
}

.main .home-card,
.main .home-context-card {
  min-height: 112px !important;
  padding: 15px !important;
}

.main .home-card-value {
  font-size: 20px !important;
  font-weight: 900 !important;
}

.main .home-card-detail {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 13px !important;
}

.main .home-context-grid,
.main .home-activity {
  display: grid !important;
  gap: 12px !important;
}

.main .home-context-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
}

.main .home-activity-row {
  border-color: var(--border-soft) !important;
  background: rgba(255,255,255,0.025) !important;
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
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 18px !important;
  font-weight: 850 !important;
  text-transform: none !important;
}

.main .home-card,
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
.main .battle-board,
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
.main .saves-current-card,
.main .saves-stat,
.main .pl-card,
.main .pt-metric,
.main .pt-section,
.main .trainer-panel,
.main .shop-card,
.main .champ-detail-card,
.main .battle-mon-card,
.main .matchup-mon {
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-card) !important;
  background: linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.015)), var(--surface-1) !important;
  box-shadow: var(--shadow-card) !important;
  color: var(--text-primary) !important;
}

.main .home-action-card,
.main .auth-trainer-card,
.main .matchup-mode-card,
.main .cup-mode-card,
.main .season-version-row,
.main .app-notice,
.main .saves-history-card,
.main .pokedex-card,
.main .slot,
.main .slot-empty,
.main .matchup-move,
.main .battle-move-link,
.main .battle-no-move,
.main .champ-detail-move-row {
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-card) !important;
  background: var(--surface-2) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  box-shadow: var(--shadow-card) !important;
  transition: border-color var(--transition-fast), background-color var(--transition-fast), transform var(--transition-fast), box-shadow var(--transition-fast) !important;
}

.main .home-action-card *,
.main .auth-trainer-card *,
.main .matchup-mode-card *,
.main .cup-mode-card *,
.main .season-version-row *,
.main .saves-history-card *,
.main .pokedex-card *,
.main .slot *,
.main .slot-empty *,
.main .shop-card *,
.main .matchup-move span:last-child,
.main .battle-move-link span:last-child {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.main .home-action-card:hover,
.main .matchup-mode-card:hover,
.main .cup-mode-card:hover,
.main .pokedex-card:hover,
.main .slot:hover,
.main .shop-card:hover,
.main .champ-box-tile-link:hover .champ-box-tile {
  transform: translateY(-3px) !important;
  border-color: rgba(77,141,255,0.45) !important;
  background: var(--surface-hover) !important;
}

.main .stButton > button,
.main .stDownloadButton > button,
.main form button {
  min-height: 44px !important;
  padding: 0 16px !important;
  border: 1px solid var(--border-normal) !important;
  border-radius: var(--radius-input) !important;
  background: var(--surface-3) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-family: var(--font-ui) !important;
  font-size: 13px !important;
  font-weight: 800 !important;
  text-transform: none !important;
  box-shadow: none !important;
  transition: background-color var(--transition-fast), border-color var(--transition-fast), transform var(--transition-fast) !important;
}

.main .stButton > button:hover,
.main .stDownloadButton > button:hover,
.main form button:hover {
  background: var(--surface-hover) !important;
  border-color: var(--border-hover) !important;
  transform: translateY(-1px) !important;
}

.main .stButton > button:active,
.main .stDownloadButton > button:active,
.main form button:active {
  transform: scale(0.98) !important;
}

.main .stButton > button:disabled,
.main .stDownloadButton > button:disabled,
.main form button:disabled {
  opacity: 0.45 !important;
  cursor: not-allowed !important;
  transform: none !important;
  filter: grayscale(0.22) !important;
}

.main .stButton > button[kind="primary"],
.main form button[kind="primary"] {
  border-color: transparent !important;
  background: var(--primary) !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

.main .stButton > button[kind="primary"]:hover,
.main form button[kind="primary"]:hover {
  background: var(--primary-hover) !important;
}

.main .stTextInput input,
.main .stNumberInput input,
.main .stTextArea textarea,
.main .stSelectbox [data-baseweb="select"],
.main .stMultiSelect [data-baseweb="select"],
.main .stDateInput input {
  min-height: 44px !important;
  border: 1px solid var(--border-normal) !important;
  border-radius: var(--radius-input) !important;
  background: #0e1524 !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  box-shadow: none !important;
}

.main .stTextInput input:focus,
.main .stNumberInput input:focus,
.main .stTextArea textarea:focus {
  border-color: var(--primary) !important;
  outline: 2px solid rgba(77,141,255,0.35) !important;
  outline-offset: 2px !important;
}

.main .stSelectbox [data-baseweb="select"] *,
.main .stMultiSelect [data-baseweb="select"] * {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 14px !important;
  text-transform: none !important;
}

div[data-baseweb="popover"],
div[data-baseweb="popover"] ul,
div[data-baseweb="menu"] {
  border: 1px solid var(--border-normal) !important;
  border-radius: var(--radius-card) !important;
  background: var(--surface-1) !important;
  box-shadow: var(--shadow-hero) !important;
}

div[data-baseweb="popover"] li,
div[data-baseweb="menu"] li,
div[role="option"] {
  min-height: 40px !important;
  border-radius: var(--radius-input) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

div[data-baseweb="popover"] li:hover,
div[data-baseweb="menu"] li:hover,
div[role="option"]:hover,
div[aria-selected="true"][role="option"] {
  background: var(--primary-soft) !important;
}

.main div[data-testid="stTabs"] div[data-baseweb="tab-list"],
.main div[data-testid="stTabs"] [role="tablist"],
.main div[data-baseweb="tab-list"] {
  gap: 6px !important;
  padding: 0 !important;
  border: 0 !important;
  border-bottom: 1px solid var(--border-soft) !important;
  border-radius: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.main div[data-testid="stTabs"] button[data-baseweb="tab"],
.main div[data-testid="stTabs"] button[role="tab"] {
  min-height: 42px !important;
  padding: 0 12px !important;
  border: 0 !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  box-shadow: none !important;
}

.main div[data-testid="stTabs"] button[aria-selected="true"],
.main button[data-baseweb="tab"][aria-selected="true"],
.main button[role="tab"][aria-selected="true"] {
  border-bottom-color: var(--primary) !important;
  background: transparent !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  box-shadow: none !important;
}

.main .slot {
  min-height: 184px !important;
  padding: 12px !important;
  background:
    radial-gradient(circle at 50% 34%, rgba(77,141,255,0.1), transparent 48%),
    var(--surface-2) !important;
}

.main .slot::before {
  display: none !important;
}

.main .slot img {
  width: min(100%, 124px) !important;
  height: 94px !important;
  object-fit: contain !important;
  transform: none !important;
  filter: drop-shadow(0 8px 12px rgba(0,0,0,0.35)) !important;
}

.main .slot .badges {
  padding-left: 0 !important;
}

.main .slot .title {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 11px !important;
  font-weight: 850 !important;
}

.main .slot .sub {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 14px !important;
}

.main .champ-box-grid-shell {
  width: 100% !important;
  margin-top: 12px !important;
  padding: 14px !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-large) !important;
  background: var(--surface-1) !important;
  box-shadow: var(--shadow-card) !important;
}

.main .champ-box-grid-toolbar {
  display: flex !important;
  justify-content: flex-start !important;
  gap: 10px !important;
  align-items: center !important;
  margin-bottom: 14px !important;
}

.main .champ-box-control {
  min-width: 0 !important;
  display: inline-flex !important;
  width: min(360px, 100%) !important;
  gap: 8px !important;
  align-items: center !important;
}

.main .champ-box-grid-toolbar strong {
  min-height: 34px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: flex-start !important;
  width: 100% !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-input) !important;
  background: var(--surface-2) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 13px !important;
  font-weight: 800 !important;
  line-height: 1 !important;
  min-width: 0 !important;
  padding: 0 12px !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}

.main .champ-box-grid {
  display: grid !important;
  grid-template-columns: repeat(6, minmax(76px, 1fr)) !important;
  gap: 10px !important;
  width: 100% !important;
}

.main .champ-box-tile-link {
  display: block !important;
  width: 100% !important;
  text-decoration: none !important;
}

.main .champ-box-tile {
  position: relative !important;
  display: grid !important;
  place-items: center !important;
  aspect-ratio: 1 / 1 !important;
  min-height: 76px !important;
  overflow: hidden !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: 12px !important;
  background:
    radial-gradient(circle at 50% 38%, rgba(77,141,255,0.11), transparent 54%),
    var(--surface-2) !important;
  box-shadow: none !important;
}

.main .champ-box-tile::before,
.main .champ-box-tile::after {
  display: none !important;
}

.main .champ-box-tile img {
  position: relative !important;
  width: 86% !important;
  height: 86% !important;
  object-fit: contain !important;
  transform: none !important;
  filter: drop-shadow(0 6px 8px rgba(0,0,0,0.35)) !important;
}

.main .champ-box-tile-empty {
  opacity: 0.35 !important;
  border-style: dashed !important;
}

.main .battle-board,
.main .battle-mon-card,
.main .matchup-mon {
  background:
    radial-gradient(circle at 50% 24%, rgba(77,141,255,0.08), transparent 46%),
    var(--surface-1) !important;
}

.main .matchup-mon-empty,
.main .battle-empty-card {
  min-height: 138px !important;
  display: grid !important;
  place-items: center !important;
  border-style: dashed !important;
  border-color: rgba(181,192,211,0.2) !important;
  background: rgba(255,255,255,0.018) !important;
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
  box-shadow: none !important;
  opacity: 0.72 !important;
}

.main .matchup-mon-empty .matchup-mon-title,
.main .battle-empty-card .battle-empty-title {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 13px !important;
  font-weight: 800 !important;
}

.main .matchup-mon-empty .matchup-mon-sub,
.main .battle-empty-card .battle-empty-sub {
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
  font-size: 12px !important;
}

.main .battle-mon-card {
  grid-template-columns: minmax(180px, .9fr) 136px minmax(260px, 1.18fr) !important;
}

.main .battle-sprite-wrap,
.main .matchup-sprite,
.main .champ-detail-sprite-stage,
.main .auth-avatar,
.main .trainers-portrait-xl {
  border: 1px solid var(--border-soft) !important;
  background:
    radial-gradient(circle at 50% 48%, rgba(77,141,255,0.18), transparent 58%),
    var(--surface-2) !important;
  box-shadow: none !important;
}

.main .battle-sprite {
  width: 128px !important;
  height: 128px !important;
}

.main .matchup-sprite {
  width: 112px !important;
  height: 112px !important;
}

.main .shop-card {
  min-height: 228px !important;
}

.main .shop-head {
  background: var(--surface-2) !important;
  border-bottom: 1px solid var(--border-soft) !important;
}

.main .shop-icon-slot {
  width: 76px !important;
  height: 76px !important;
  background: var(--surface-2) !important;
}

.main .shop-body {
  grid-template-columns: 78px minmax(0, 1fr) !important;
}

.main .shop-price,
.main .shop-coin-value,
.main .champ-detail-level,
.main .champ-detail-item-value,
.main .champ-detail-stat-value,
.main .champ-detail-private-value,
.main .champ-detail-move-pp {
  background: var(--surface-3) !important;
  border-color: var(--border-soft) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.main .shop-coin,
.main .shop-amount,
.main .mart-confirm-price {
  color: var(--pokemon-yellow) !important;
  -webkit-text-fill-color: var(--pokemon-yellow) !important;
}

.main .app-notice-menu summary {
  min-height: 42px !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: var(--radius-input) !important;
  background: var(--surface-2) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.main .app-notice-menu-panel {
  border: 1px solid var(--border-soft) !important;
  background: var(--surface-1) !important;
}

.main .poke-type-chip.uses-asset,
section[data-testid="stSidebar"] .poke-type-chip.uses-asset {
  background: transparent !important;
}

.main .poke-type-icon-img,
section[data-testid="stSidebar"] .poke-type-icon-img {
  width: 26px !important;
  height: 26px !important;
}

.main .poke-type-chip.asset-full,
section[data-testid="stSidebar"] .poke-type-chip.asset-full {
  width: 86px !important;
  min-width: 86px !important;
  height: 18px !important;
  min-height: 18px !important;
}

.main .battle-type-pill.poke-type-chip.asset-full,
.main .champ-detail-type-chip.poke-type-chip.asset-full {
  width: 112px !important;
  min-width: 112px !important;
  height: 23px !important;
  min-height: 23px !important;
}

/* New Champions final pass: remove old dark BW2 surfaces from active controls. */
:root {
  --champ-final-list: rgba(222,216,248,0.96);
  --champ-final-list-2: rgba(199,192,230,0.95);
  --champ-final-text: #263566;
  --champ-final-lime: #b7ee32;
  --champ-final-lime-2: #8fd10b;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] details,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary,
section[data-testid="stSidebar"] .app-notice-menu summary {
  border: 1px solid rgba(246,242,255,0.48) !important;
  border-radius: 16px !important;
  background:
    linear-gradient(136deg, transparent 0 70%, rgba(255,142,227,0.16) 70% 84%, rgba(79,214,255,0.16) 84% 100%),
    linear-gradient(180deg, var(--champ-final-list), var(--champ-final-list-2)) !important;
  color: var(--champ-final-text) !important;
  -webkit-text-fill-color: var(--champ-final-text) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.54), 0 10px 22px rgba(14,11,48,0.18) !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] summary *,
section[data-testid="stSidebar"] div[data-testid="stExpander"] details *,
section[data-testid="stSidebar"] .app-notice-menu summary * {
  color: var(--champ-final-text) !important;
  -webkit-text-fill-color: var(--champ-final-text) !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] div[data-testid="stExpanderDetails"],
section[data-testid="stSidebar"] .app-notice-menu-panel {
  border: 1px solid rgba(246,242,255,0.24) !important;
  border-radius: 18px !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.08) 0 30%, transparent 30% 100%),
    rgba(48,40,132,0.68) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.12) !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] input {
  min-height: 38px !important;
  border: 1px solid rgba(246,242,255,0.34) !important;
  border-radius: 12px !important;
  background: rgba(247,244,255,0.92) !important;
  color: var(--champ-final-text) !important;
  -webkit-text-fill-color: var(--champ-final-text) !important;
}

.main .matchup-hero,
.main .matchup-shell,
.main .matchup-summary,
.main .battle-board {
  border: 1px solid rgba(246,242,255,0.36) !important;
  border-radius: 22px !important;
  background:
    linear-gradient(126deg, rgba(255,255,255,0.11) 0 24%, transparent 24% 100%),
    linear-gradient(302deg, rgba(255,142,227,0.12), transparent 44%),
    linear-gradient(180deg, rgba(100,82,212,0.92), rgba(48,40,132,0.9)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 18px 38px rgba(14,11,48,0.26) !important;
}

.main .matchup-mode-card,
.main .matchup-move,
.main .battle-move-link,
.main .battle-no-move,
.main .battle-board-top > div {
  border: 1px solid rgba(246,242,255,0.46) !important;
  border-radius: 16px !important;
  background:
    linear-gradient(136deg, transparent 0 70%, rgba(255,142,227,0.16) 70% 84%, rgba(79,214,255,0.16) 84% 100%),
    linear-gradient(180deg, var(--champ-final-list), var(--champ-final-list-2)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.54), 0 8px 18px rgba(14,11,48,0.18) !important;
  color: var(--champ-final-text) !important;
  -webkit-text-fill-color: var(--champ-final-text) !important;
}

.main .matchup-mode-card *,
.main .matchup-move span:last-child,
.main .battle-move-link span:last-child,
.main .battle-no-move *,
.main .battle-board-top > div * {
  color: var(--champ-final-text) !important;
  -webkit-text-fill-color: var(--champ-final-text) !important;
}

.main .matchup-mode-card.is-active,
.main .battle-move-link:hover,
.main .battle-move-link.is-active,
.main .battle-move-row[open] > .battle-move-link {
  border-color: rgba(246,216,59,0.95) !important;
  background:
    linear-gradient(136deg, transparent 0 70%, rgba(255,255,255,0.22) 70% 100%),
    linear-gradient(180deg, var(--champ-final-lime), var(--champ-final-lime-2)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.52), 0 0 0 3px rgba(246,216,59,0.18), 0 12px 23px rgba(18,14,54,0.24) !important;
}

.main .battle-mon-card,
.main .matchup-mon {
  border: 1px solid rgba(246,242,255,0.34) !important;
  border-radius: 20px !important;
  background:
    linear-gradient(116deg, rgba(255,255,255,0.1) 0 35%, transparent 35% 100%),
    linear-gradient(180deg, rgba(119,98,229,0.9), rgba(72,62,172,0.9)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 12px 26px rgba(18,14,54,0.2) !important;
}

.main .battle-card-left,
.main .battle-ability-row,
.main .battle-private-line,
.main .battle-ivs,
.main .battle-stat-stack,
.main .battle-detail-stats div,
.main .battle-move-detail,
.main .battle-move-detail-inline,
.main .matchup-metric {
  border: 1px solid rgba(246,242,255,0.24) !important;
  border-radius: 16px !important;
  background:
    linear-gradient(136deg, transparent 0 74%, rgba(255,142,227,0.12) 74% 100%),
    rgba(255,255,255,0.08) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.12) !important;
}

.main .battle-sprite-wrap,
.main .matchup-sprite {
  border: 1px solid rgba(246,242,255,0.4) !important;
  border-radius: 18px !important;
  background:
    radial-gradient(circle at 50% 46%, rgba(255,255,255,0.42), rgba(255,255,255,0.08) 60%, transparent 61%),
    linear-gradient(180deg, rgba(224,219,249,0.92), rgba(190,183,225,0.9)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.28), 0 8px 18px rgba(18,14,54,0.18) !important;
}

.main .battle-mon-name,
.main .matchup-mon-title,
.main .matchup-player,
.main .matchup-title,
.main .battle-stat-row strong,
.main .battle-ability-row strong,
.main .battle-private-line strong,
.main .battle-iv strong {
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

.main .battle-species,
.main .battle-level,
.main .battle-item,
.main .matchup-mon-sub,
.main .matchup-mon-extra,
.main .matchup-subtitle,
.main .matchup-division,
.main .matchup-save,
.main .battle-ability-desc,
.main .battle-detail-desc,
.main .battle-stat-label {
  color: rgba(255,255,255,0.88) !important;
  -webkit-text-fill-color: rgba(255,255,255,0.88) !important;
}

@media (max-width: 980px) {
  .main .block-container {
    padding: 24px 16px 48px !important;
  }
  .main .poke-topbar {
    align-items: flex-start !important;
    flex-direction: column !important;
  }
  .main .poke-topbar-right {
    width: 100% !important;
    justify-content: flex-start !important;
    flex-wrap: wrap !important;
  }
  .main .home-hero {
    grid-template-columns: 1fr !important;
    min-height: 0 !important;
  }
  .main .home-side.home-right {
    text-align: left !important;
  }
  .main .home-versus {
    width: 64px !important;
    height: 64px !important;
  }
  .main .home-context-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
  section[data-testid="stSidebar"] {
    width: 230px !important;
    min-width: 230px !important;
    max-width: 230px !important;
  }
  .main .battle-mon-card {
    grid-template-columns: minmax(0, 1fr) !important;
  }
  .main .champ-box-grid {
    grid-template-columns: repeat(4, minmax(58px, 1fr)) !important;
  }
  .main .champ-box-grid-toolbar {
    display: block !important;
  }
  .main .champ-box-control {
    width: 100% !important;
  }
}

@media (max-width: 560px) {
  .main .slot {
    min-height: 168px !important;
  }
  .main .champ-box-grid {
    grid-template-columns: repeat(3, minmax(54px, 1fr)) !important;
  }
  .main .home-context-grid {
    grid-template-columns: 1fr !important;
  }
}
</style>
"""


def apply_champions_skin(container: Any = None) -> None:
    target = container or st
    target.markdown(CHAMPIONS_SKIN_CSS, unsafe_allow_html=True)
    from app.interfaz.premium_phase2 import apply_phase2_skin

    apply_phase2_skin(target)
