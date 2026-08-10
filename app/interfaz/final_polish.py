from __future__ import annotations

import streamlit as st


FINAL_POLISH_CSS = """
<style>
:root {
  --bg-main: #070d18;
  --bg-secondary: #0a1424;
  --bg-tertiary: #102037;
  --surface-0: #07101d;
  --surface-1: rgba(13, 22, 36, 0.96);
  --surface-2: rgba(18, 30, 49, 0.96);
  --surface-3: rgba(27, 43, 68, 0.96);
  --border-soft: rgba(215, 230, 255, 0.08);
  --border-normal: rgba(215, 230, 255, 0.14);
  --border-hover: rgba(91, 178, 255, 0.34);
  --text-primary: #f6f9ff;
  --text-secondary: #b8c7dc;
  --text-muted: #77879e;
  --primary: #4d8dff;
  --primary-hover: #72b9ff;
  --primary-soft: rgba(77, 141, 255, 0.14);
  --info: #45d1ff;
  --pokemon-yellow: #ffd24d;
  --success: #43d17c;
  --warning: #ffb84a;
  --danger: #ff5263;
  --champ-list: var(--surface-2);
  --champ-list-2: var(--surface-3);
  --champ-text: var(--text-primary);
  --champ-text-soft: var(--text-secondary);
  --champ-muted: var(--text-muted);
  --champ-lime: var(--primary);
  --champ-lime-2: #2f6fff;
  --champ-pink: var(--info);
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
  --poke-radius-sm: 8px;
  --poke-radius: 12px;
  --poke-radius-xl: 16px;
  --poke-shadow-card: 0 14px 30px rgba(0, 0, 0, 0.24);
  --poke-shadow-soft: 0 18px 42px rgba(0, 0, 0, 0.28);
  --poke-surface-glow: inset 0 1px 0 rgba(255, 255, 255, 0.055);
}

.stApp {
  color: var(--text-primary) !important;
  background:
    linear-gradient(135deg, rgba(69, 209, 255, 0.06) 0 18%, transparent 18% 100%) 0 42px / 560px 360px,
    linear-gradient(225deg, rgba(255, 210, 77, 0.045) 0 16%, transparent 16% 100%) 100% 110px / 620px 420px,
    radial-gradient(circle at 18% 12%, rgba(77, 141, 255, 0.12), transparent 320px),
    linear-gradient(180deg, #070d18 0%, #0b1526 50%, #07101d 100%) !important;
}

.main::before {
  background:
    linear-gradient(32deg, transparent 0 67%, rgba(255,255,255,0.035) 67% 68%, transparent 68% 100%) 0 0 / 220px 220px,
    linear-gradient(150deg, transparent 0 60%, rgba(91,178,255,0.04) 60% 61%, transparent 61% 100%) 0 0 / 260px 260px !important;
}

.main .block-container {
  max-width: 1500px !important;
}

div[data-testid="collapsedControl"],
button[data-testid="stSidebarCollapseButton"],
button[aria-label="Close sidebar"],
button[aria-label="Open sidebar"] {
  display: none !important;
}

section[data-testid="stSidebar"] {
  width: 248px !important;
  min-width: 248px !important;
}

.stApp h1,
.stApp h2,
.stApp h3 {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.stApp p,
.stApp span,
.stApp div,
.stApp label,
.stApp li {
  letter-spacing: 0 !important;
}

.stApp code,
.saves-meta-value,
.saves-card-title,
.poke-topbar,
.league-status-table,
.trainer-panel {
  font-variant-numeric: tabular-nums !important;
}

/* Topbar */
.poke-topbar {
  position: sticky !important;
  top: 0 !important;
  z-index: 60 !important;
  min-height: 46px !important;
  margin: 0 0 18px !important;
  padding: 8px 12px !important;
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) !important;
  align-items: center !important;
  gap: 12px !important;
  overflow: hidden !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: 14px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.012)),
    rgba(9, 15, 26, 0.92) !important;
  box-shadow: 0 10px 24px rgba(0,0,0,0.2) !important;
  backdrop-filter: blur(14px) !important;
}

.poke-topbar-left,
.poke-topbar-center,
.poke-topbar-right {
  min-width: 0 !important;
  display: flex !important;
  align-items: center !important;
  gap: 9px !important;
  white-space: nowrap !important;
}

.poke-topbar-left {
  justify-self: start !important;
  overflow: hidden !important;
  color: var(--text-secondary) !important;
}

.poke-topbar-center {
  max-width: 360px !important;
  min-width: 0 !important;
  justify-self: center !important;
  justify-content: center !important;
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
  font-size: 11px !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
}

.poke-topbar-right {
  justify-self: end !important;
}

.poke-topbar-left > span,
.poke-topbar-center,
.poke-topbar-pill,
.poke-topbar-user {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 12px !important;
  font-weight: 850 !important;
}

.poke-topbar-round {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.poke-topbar-division::before {
  content: "\\00b7";
  margin: 0 8px 0 1px;
  color: rgba(184,199,220,0.58);
  -webkit-text-fill-color: rgba(184,199,220,0.58);
}

.poke-topbar-sep,
.poke-topbar-dot {
  width: auto !important;
  height: auto !important;
  color: rgba(184,199,220,0.58) !important;
  -webkit-text-fill-color: rgba(184,199,220,0.58) !important;
  background: transparent !important;
  font-weight: 900 !important;
}

.poke-topbar-pill,
.poke-topbar-user {
  min-height: 28px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 7px !important;
  padding: 0 10px !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: 999px !important;
  background: rgba(255,255,255,0.035) !important;
  box-shadow: none !important;
}

.poke-topbar-user > span {
  width: 22px !important;
  height: 22px !important;
  display: inline-grid !important;
  place-items: center !important;
  border-radius: 50% !important;
  background: var(--primary-soft) !important;
  color: var(--primary-hover) !important;
  -webkit-text-fill-color: var(--primary-hover) !important;
  font-size: 9px !important;
  font-weight: 950 !important;
}

.poke-topbar-icon,
.poke-topbar-bell,
.main .poke-topbar-icon,
.main .poke-topbar-bell {
  display: none !important;
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  flex-basis: 0 !important;
  overflow: hidden !important;
  background: transparent !important;
  box-shadow: none !important;
}

.poke-topbar-bell::before,
.main .poke-topbar-bell::before {
  content: "" !important;
  display: none !important;
}

.poke-topbar-bell::after,
.main .poke-topbar-bell::after {
  content: "" !important;
  display: none !important;
}

.poke-topbar-label {
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
  font-size: 10px !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
}

.poke-coin-mark {
  width: 16px !important;
  height: 16px !important;
  flex: 0 0 16px !important;
}

@media (max-width: 720px) {
  .poke-topbar {
    grid-template-columns: 1fr !important;
    align-items: flex-start !important;
    gap: 7px !important;
  }
  .poke-topbar-left,
  .poke-topbar-center,
  .poke-topbar-right {
    width: 100% !important;
    flex-wrap: wrap !important;
    justify-self: start !important;
    justify-content: flex-start !important;
  }
  .poke-topbar-right {
    justify-content: flex-start !important;
  }
}

/* Global controls */
.stApp .stButton > button {
  min-height: 36px !important;
  border-radius: 10px !important;
  border: 1px solid var(--border-normal) !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.055), rgba(255,255,255,0.018)),
    var(--surface-2) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  box-shadow: none !important;
}

.stApp .stButton > button:hover {
  transform: translateY(-1px) !important;
  border-color: var(--border-hover) !important;
  background:
    linear-gradient(180deg, rgba(77,141,255,0.18), rgba(77,141,255,0.08)),
    var(--surface-2) !important;
}

.stApp .stButton > button[kind="primary"],
.stApp .stFormSubmitButton > button[kind="primary"] {
  border-color: rgba(114,185,255,0.52) !important;
  background: linear-gradient(180deg, #5aa6ff, #2f6fff) !important;
}

.stApp .stButton > button:disabled,
.stApp .stFormSubmitButton > button:disabled {
  border-color: rgba(255,255,255,0.055) !important;
  background: rgba(255,255,255,0.035) !important;
  color: rgba(184,199,220,0.5) !important;
  -webkit-text-fill-color: rgba(184,199,220,0.5) !important;
  transform: none !important;
}

.stApp input,
.stApp textarea,
.stApp div[data-baseweb="select"] > div {
  min-height: 38px !important;
  border-color: var(--border-normal) !important;
  border-radius: 10px !important;
  background: rgba(9, 15, 26, 0.88) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  box-shadow: none !important;
}

.stApp input:focus,
.stApp textarea:focus,
.stApp div[data-baseweb="select"] > div:focus-within {
  border-color: rgba(114,185,255,0.68) !important;
  box-shadow: 0 0 0 3px rgba(77,141,255,0.13) !important;
}

.stApp label,
.stApp [data-testid="stWidgetLabel"] p {
  color: var(--text-secondary) !important;
  font-size: 12px !important;
  font-weight: 850 !important;
}

.stApp div[data-testid="stTabs"] [role="tablist"] {
  gap: 8px !important;
  padding: 0 0 10px !important;
  border: 0 !important;
  border-bottom: 1px solid var(--border-soft) !important;
  background: transparent !important;
  box-shadow: none !important;
}

.stApp div[data-testid="stTabs"] button[role="tab"],
.stApp div[data-testid="stTabs"] button[data-baseweb="tab"] {
  flex: 0 1 auto !important;
  min-width: 132px !important;
  min-height: 38px !important;
  padding: 0 14px !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: 10px !important;
  clip-path: none !important;
  background: rgba(255,255,255,0.035) !important;
}

.stApp div[data-testid="stTabs"] button[aria-selected="true"],
.stApp div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
  border-color: rgba(114,185,255,0.58) !important;
  background:
    linear-gradient(180deg, rgba(77,141,255,0.24), rgba(77,141,255,0.12)),
    rgba(15, 25, 42, 0.96) !important;
  box-shadow: inset 0 -2px 0 var(--primary) !important;
}

.stApp div[data-testid="stTabs"] button[role="tab"] *,
.stApp div[data-testid="stTabs"] button[data-baseweb="tab"] * {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 12px !important;
  font-weight: 850 !important;
  white-space: nowrap !important;
}

.stApp div[data-testid="stTabs"] button[aria-selected="true"] *,
.stApp div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] * {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.stApp div[data-testid="stExpander"] details {
  border: 1px solid var(--border-soft) !important;
  border-radius: 12px !important;
  background: rgba(12, 20, 34, 0.86) !important;
  box-shadow: none !important;
}

.stApp div[data-testid="stExpander"] summary {
  min-height: 38px !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] details,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary,
section[data-testid="stSidebar"] .app-notice-menu summary {
  border-color: var(--border-soft) !important;
  border-radius: 12px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.015)),
    rgba(12, 20, 34, 0.94) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] summary [data-testid="stIconMaterial"] {
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  overflow: hidden !important;
  font-size: 0 !important;
}

section[data-testid="stSidebar"] summary [data-testid="stIconMaterial"],
section[data-testid="stSidebar"] summary [data-testid="stIconMaterial"] *,
section[data-testid="stSidebar"] summary .material-symbols-rounded,
section[data-testid="stSidebar"] summary .material-symbols-outlined,
section[data-testid="stSidebar"] summary .material-icons,
section[data-testid="stSidebar"] summary [class*="material-symbols"],
section[data-testid="stSidebar"] summary [class*="material-icons"],
section[data-testid="stSidebar"] summary [aria-hidden="true"]:has(svg),
section[data-testid="stSidebar"] summary svg {
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  overflow: hidden !important;
  font-size: 0 !important;
  color: transparent !important;
  -webkit-text-fill-color: transparent !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] div[data-testid="stExpanderDetails"],
section[data-testid="stSidebar"] .app-notice-menu-panel {
  border: 1px solid var(--border-soft) !important;
  border-radius: 12px !important;
  background: rgba(7, 12, 22, 0.94) !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] input {
  min-height: 34px !important;
  border-color: var(--border-normal) !important;
  border-radius: 9px !important;
  background: rgba(5, 10, 19, 0.96) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

section[data-testid="stSidebar"] .pin-form-title {
  margin: 0 0 10px !important;
  padding: 8px 10px !important;
  border: 1px solid rgba(114,185,255,0.18) !important;
  border-left: 3px solid var(--primary) !important;
  border-radius: 10px !important;
  background: rgba(77,141,255,0.08) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-family: var(--font-pixel) !important;
  font-size: 11px !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] label p {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 12px !important;
  font-weight: 850 !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] div.stButton > button {
  justify-content: center !important;
  border-color: rgba(77,141,255,0.4) !important;
  background:
    linear-gradient(180deg, rgba(77,141,255,0.95), rgba(47,111,255,0.95)) !important;
  color: #ffffff !important;
  -webkit-text-fill-color: #ffffff !important;
}

/* Shared page surfaces */
.main .home-hero,
.main .trainers-hero,
.main .league-hero,
.main .matchup-hero,
.main .mart-hero,
.main .hof-hero,
.main .saves-hero {
  border-color: var(--border-normal) !important;
  border-radius: 16px !important;
  clip-path: none !important;
  background:
    linear-gradient(135deg, rgba(77,141,255,0.105), transparent 38%),
    linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.014)),
    rgba(11, 19, 32, 0.96) !important;
  box-shadow: var(--poke-shadow-card) !important;
}

.main .league-hero,
.main .mart-hero,
.main .saves-hero,
.main .hof-hero {
  min-height: 104px !important;
  padding: 14px !important;
}

.main .trainers-hero {
  min-height: 132px !important;
  padding: 14px !important;
}

.main .trainers-hero:after {
  opacity: 0.24 !important;
}

.main .league-title,
.main .mart-title,
.main .saves-title,
.main .hof-title,
.main .matchup-title,
.main .trainers-title {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  text-shadow: none !important;
}

.main .league-title,
.main .hof-title,
.main .matchup-title {
  font-size: clamp(24px, 2.2vw, 31px) !important;
}

.main .mart-title,
.main .saves-title {
  font-size: clamp(20px, 1.8vw, 26px) !important;
}

.main .league-subtitle,
.main .saves-subtitle,
.main .hof-subtitle,
.main .trainers-subtitle,
.main .mart-led,
.main .league-section-sub {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 14px !important;
  line-height: 1.25 !important;
}

.main .league-kicker,
.main .hof-kicker,
.main .saves-kicker,
.main .mart-kicker,
.main .trainers-panel-label,
.main .league-section-title,
.main .hof-section-title,
.main .saves-section-title,
.main .trainers-section-title {
  border-color: var(--border-normal) !important;
  border-left-color: var(--accent) !important;
  border-radius: 10px !important;
  clip-path: none !important;
  background: rgba(255,255,255,0.045) !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  box-shadow: none !important;
}

/* Type badges */
.poke-type-chip.uses-asset {
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
  overflow: hidden !important;
}

.poke-type-chip.asset-icon {
  width: 22px !important;
  min-width: 22px !important;
  max-width: 22px !important;
  height: 22px !important;
  min-height: 22px !important;
  max-height: 22px !important;
  border-radius: 6px !important;
}

.poke-type-chip.asset-icon img,
.poke-type-icon-img {
  width: 22px !important;
  height: 22px !important;
  max-width: 22px !important;
  max-height: 22px !important;
  object-fit: contain !important;
}

.poke-type-chip.asset-full {
  width: 88px !important;
  min-width: 88px !important;
  max-width: 88px !important;
  height: 18px !important;
  min-height: 18px !important;
  max-height: 18px !important;
  border-radius: 999px !important;
}

.poke-type-chip.asset-full img,
.poke-type-full-img {
  width: 88px !important;
  height: 18px !important;
  max-width: 88px !important;
  max-height: 18px !important;
  object-fit: contain !important;
}

.poke-type-chip.uses-fallback {
  min-height: 18px !important;
  padding: 0 8px !important;
  border: 1px solid color-mix(in srgb, var(--type-color) 48%, transparent) !important;
  border-radius: 999px !important;
  background: color-mix(in srgb, var(--type-color) 16%, transparent) !important;
}

.poke-type-chip.uses-fallback .poke-type-fallback {
  color: var(--type-fg) !important;
  -webkit-text-fill-color: var(--type-fg) !important;
  font-size: 9px !important;
  font-weight: 900 !important;
}

/* Team Preview */
.main .matchup-shell,
.main .matchup-summary,
.main .battle-board {
  border: 1px solid var(--border-normal) !important;
  border-radius: 16px !important;
  background:
    linear-gradient(135deg, rgba(77,141,255,0.08), transparent 36%),
    linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.012)),
    rgba(8, 14, 26, 0.96) !important;
  box-shadow: var(--poke-shadow-card) !important;
}

.main .matchup-hero {
  min-height: 98px !important;
  grid-template-columns: minmax(0, 1fr) auto !important;
}

.main .matchup-hero-side,
.main .matchup-hero-pill,
.main .matchup-metric,
.main .battle-board-top > div,
.main .battle-card-left,
.main .battle-ability-row,
.main .battle-private-line,
.main .battle-ivs,
.main .battle-detail-stats div {
  border-color: var(--border-soft) !important;
  border-radius: 12px !important;
  background: rgba(255,255,255,0.04) !important;
  box-shadow: none !important;
}

.main .matchup-mode-card,
.main .matchup-move,
.main .battle-move-link,
.main .battle-no-move {
  border: 1px solid rgba(215,230,255,0.12) !important;
  border-radius: 10px !important;
  background: rgba(11, 19, 32, 0.82) !important;
  box-shadow: none !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.main .matchup-mode-card *,
.main .matchup-move span:last-child,
.main .battle-move-link span:last-child,
.main .battle-no-move,
.main .battle-no-move * {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.main .matchup-mode-card.is-active,
.main .battle-move-link:hover,
.main .battle-move-row[open] > .battle-move-link {
  border-color: rgba(114,185,255,0.62) !important;
  background:
    linear-gradient(180deg, rgba(77,141,255,0.18), rgba(77,141,255,0.08)),
    rgba(14, 24, 42, 0.92) !important;
  box-shadow: inset 3px 0 0 var(--primary) !important;
}

.main .battle-mon-card,
.main .matchup-mon {
  border: 1px solid rgba(215,230,255,0.13) !important;
  border-radius: 15px !important;
  background:
    radial-gradient(circle at 50% 18%, color-mix(in srgb, var(--type-color, var(--primary)) 10%, transparent), transparent 38%),
    linear-gradient(135deg, rgba(255,255,255,0.045), transparent 42%),
    rgba(12, 20, 34, 0.95) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.055), 0 10px 20px rgba(0,0,0,0.18) !important;
}

.main .battle-mon-card {
  min-height: 166px !important;
  padding: 11px !important;
}

.main .battle-mon-card-public {
  min-height: 144px !important;
}

.main .battle-sprite-wrap,
.main .matchup-sprite {
  border-radius: 13px !important;
  background:
    radial-gradient(circle at 50% 48%, rgba(77,141,255,0.18), transparent 58%),
    rgba(255,255,255,0.035) !important;
}

.main .battle-sprite {
  width: 110px !important;
  height: 110px !important;
}

.main .matchup-sprite {
  width: 96px !important;
  height: 96px !important;
}

.main .battle-slot-mark {
  color: rgba(255,255,255,0.09) !important;
  -webkit-text-fill-color: rgba(255,255,255,0.09) !important;
  font-size: 42px !important;
}

.main .battle-move-detail,
.main .battle-move-detail-inline {
  border: 1px solid rgba(215,230,255,0.14) !important;
  border-radius: 14px !important;
  background:
    linear-gradient(135deg, rgba(77,141,255,0.08), transparent 34%),
    rgba(8, 14, 26, 0.96) !important;
  box-shadow: none !important;
}

.main .battle-detail-stats div {
  background: rgba(255,255,255,0.04) !important;
}

.main .battle-detail-stats div span {
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
}

.main .battle-detail-stats div strong {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.main .battle-detail-stat-type {
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.main .battle-detail-stat-type > span {
  display: none !important;
}

.main .battle-type-pill.poke-type-chip.asset-full,
.main .champ-detail-type-chip.poke-type-chip.asset-full {
  width: 104px !important;
  min-width: 104px !important;
  max-width: 104px !important;
  height: 22px !important;
  min-height: 22px !important;
  max-height: 22px !important;
}

.main .battle-type-pill.poke-type-chip.asset-full img,
.main .champ-detail-type-chip.poke-type-chip.asset-full img {
  width: 104px !important;
  height: 22px !important;
  max-width: 104px !important;
  max-height: 22px !important;
}

.main .battle-move-link .battle-type-dot.poke-type-chip.asset-icon,
.main .matchup-move .battle-type-dot.poke-type-chip.asset-icon,
.main .battle-type-dot.poke-type-chip.asset-icon {
  width: 20px !important;
  min-width: 20px !important;
  max-width: 20px !important;
  height: 20px !important;
  min-height: 20px !important;
  max-height: 20px !important;
  flex-basis: 20px !important;
}

.main .battle-move-link .battle-type-dot.poke-type-chip.asset-icon img,
.main .matchup-move .battle-type-dot.poke-type-chip.asset-icon img,
.main .battle-type-dot.poke-type-chip.asset-icon img {
  width: 20px !important;
  height: 20px !important;
  max-width: 20px !important;
  max-height: 20px !important;
}

.main .battle-stat-stack {
  gap: 5px !important;
  border-color: rgba(215,230,255,0.1) !important;
  border-radius: 12px !important;
  background: rgba(255,255,255,0.035) !important;
}

.main .battle-stat-row {
  min-height: 23px !important;
  background: rgba(255,255,255,0.035) !important;
}

.main .battle-stat-bar {
  height: 5px !important;
  background: rgba(0,0,0,0.34) !important;
}

/* Phase 1A final Team Preview overrides. Keep this short: base lives in matchup_styles. */
.main .matchup-competition-bar {
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr) !important;
  gap: 14px !important;
  align-items: center !important;
  margin: 8px 0 14px !important;
  padding: 12px 14px !important;
  border: 1px solid rgba(139,171,216,0.18) !important;
  border-radius: 14px !important;
  background:
    linear-gradient(135deg, rgba(77,141,255,0.075), transparent 36%),
    linear-gradient(180deg, rgba(18,30,49,0.96), rgba(8,14,26,0.98)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 14px 28px rgba(0,0,0,0.22) !important;
}

.main .matchup-competitor {
  min-width: 0 !important;
  display: grid !important;
  gap: 4px !important;
}

.main .matchup-competitor-right {
  text-align: right !important;
}

.main .matchup-competitor span,
.main .matchup-pair-record {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 12px !important;
  font-weight: 850 !important;
}

.main .matchup-competitor strong {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-family: var(--font-pixel) !important;
  font-size: clamp(15px, 1.35vw, 18px) !important;
  line-height: 1.08 !important;
  overflow-wrap: anywhere !important;
  text-transform: uppercase !important;
}

.main .matchup-vs-mark {
  width: 48px !important;
  height: 48px !important;
  display: grid !important;
  place-items: center !important;
  border: 1px solid rgba(69,209,255,0.32) !important;
  border-radius: 50% !important;
  background: rgba(69,209,255,0.08) !important;
  color: #8fdcff !important;
  -webkit-text-fill-color: #8fdcff !important;
  font-family: var(--font-pixel) !important;
  font-size: 15px !important;
}

.main .matchup-pair-record {
  grid-column: 1 / -1 !important;
  padding-top: 8px !important;
  border-top: 1px solid rgba(139,171,216,0.11) !important;
  text-align: center !important;
}

.main .battle-move-link,
.main .matchup-move,
.main .battle-no-move {
  display: grid !important;
  grid-template-columns: auto minmax(0, 1fr) auto !important;
  align-items: center !important;
  gap: 8px !important;
  border-color: rgba(139,171,216,0.14) !important;
  background: rgba(6,12,22,0.68) !important;
}

.main .battle-move-name {
  min-width: 0 !important;
  overflow: hidden !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 14px !important;
  font-weight: 850 !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}

.main .battle-move-pp {
  justify-self: end !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 11px !important;
  font-weight: 900 !important;
  font-variant-numeric: tabular-nums !important;
  white-space: nowrap !important;
}

.main .battle-detail-stat-type,
.main .battle-detail-stat-type.battle-detail-stat {
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.main .battle-detail-stat-type > span {
  display: none !important;
}

/* Trainers */
.main .trainers-portrait-xl {
  width: 104px !important;
  height: 104px !important;
  border-radius: 14px !important;
  background: rgba(255,255,255,0.04) !important;
}

.main .trainers-hero-grid {
  grid-template-columns: 104px minmax(0, 1fr) !important;
}

.main .trainers-status-grid,
.main .saves-status-grid,
.main .mart-register-grid {
  gap: 9px !important;
}

.main .trainers-stat,
.main .saves-stat,
.main .mart-register-card,
.main .league-status-card,
.main .hof-stat {
  min-height: 70px !important;
  border-color: var(--border-soft) !important;
  border-radius: 12px !important;
  background: rgba(255,255,255,0.035) !important;
  box-shadow: none !important;
}

.main .trainers-stat-detail,
.main .saves-stat-detail,
.main .mart-value,
.main .league-status-card strong,
.main .hof-stat strong {
  font-size: 16px !important;
}

.main .trainer-panel {
  border-color: var(--border-normal) !important;
  border-radius: 16px !important;
  background:
    linear-gradient(135deg, rgba(77,141,255,0.07), transparent 40%),
    rgba(10, 17, 29, 0.96) !important;
  box-shadow: var(--poke-shadow-card) !important;
}

.main .trainer-head {
  border: 0 !important;
  border-left: 3px solid var(--accent) !important;
  border-radius: 10px !important;
  clip-path: none !important;
  background: rgba(255,255,255,0.045) !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
}

.main .trainer-grid {
  grid-template-columns: 124px minmax(0, 1fr) !important;
}

.main .trainer-portrait {
  border-color: var(--border-soft) !important;
  border-radius: 14px !important;
  background: rgba(255,255,255,0.035) !important;
}

.main .trainer-portrait img {
  width: 106px !important;
}

.main .trainer-metrics {
  display: grid !important;
  grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
  gap: 8px !important;
}

.main .trainer-metric {
  min-height: 66px !important;
  padding: 9px 10px !important;
  border: 1px solid var(--border-soft) !important;
  border-radius: 12px !important;
  background: rgba(255,255,255,0.035) !important;
}

.main .trainer-metric span {
  display: block !important;
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
  font-size: 10px !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
}

.main .trainer-metric strong {
  display: block !important;
  margin-top: 6px !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 18px !important;
  font-weight: 950 !important;
}

.main .trainer-medals {
  margin-top: 9px !important;
}

.main .trainer-kia,
.main .trainer-note {
  border-color: var(--border-soft) !important;
  border-radius: 12px !important;
  background: rgba(255,255,255,0.035) !important;
}

/* Current team and PC */
.main .slot.team-slot-card {
  min-height: 190px !important;
  border-radius: 14px !important;
  background:
    radial-gradient(circle at 50% 24%, rgba(77,141,255,0.11), transparent 42%),
    rgba(13, 22, 36, 0.95) !important;
}

.main .slot.team-slot-card > img {
  width: min(100%, 126px) !important;
  height: 104px !important;
  margin: 2px auto 6px !important;
}

.main .slot.team-slot-card .title {
  font-size: 10px !important;
}

.main .slot.team-slot-card .sub {
  font-size: 14px !important;
}

.main .slot.team-slot-card .types {
  min-height: 17px !important;
  margin-top: 6px !important;
  gap: 4px !important;
}

.main .slot.team-slot-card .slot-type-badge.poke-type-chip.asset-full {
  width: 72px !important;
  min-width: 72px !important;
  max-width: 72px !important;
  height: 15px !important;
  min-height: 15px !important;
  max-height: 15px !important;
}

.main .slot.team-slot-card .slot-type-badge.poke-type-chip.asset-full img,
.main .slot.team-slot-card .slot-type-badge .poke-type-full-img {
  width: 72px !important;
  height: 15px !important;
  max-width: 72px !important;
  max-height: 15px !important;
}

div[data-testid="column"]:has(.slot.team-slot-card) .stButton > button {
  min-height: 32px !important;
  padding: 0 12px !important;
}

.main .champ-box-grid-shell {
  border-color: var(--border-normal) !important;
  background:
    linear-gradient(135deg, rgba(77,141,255,0.075), transparent 40%),
    rgba(8, 14, 26, 0.96) !important;
}

.main .champ-box-tile {
  min-height: 118px !important;
  border-color: rgba(215,230,255,0.12) !important;
  background:
    radial-gradient(circle at 50% 45%, color-mix(in srgb, var(--box-glow, var(--primary)) 15%, transparent), transparent 58%),
    rgba(15, 26, 43, 0.96) !important;
}

.main .champ-box-tile img {
  width: 90px !important;
  height: 80px !important;
  max-width: 90px !important;
  max-height: 80px !important;
}

/* Shop */
.main .mart-hero {
  grid-template-columns: minmax(0, 1fr) auto !important;
  min-height: 92px !important;
  margin-bottom: 10px !important;
  padding: 14px 16px !important;
}

.main .mart-hero-right {
  min-width: 164px !important;
  padding: 0 !important;
  border: 0 !important;
  background: transparent !important;
}

.main .mart-balance-card {
  min-width: 164px !important;
  padding: 10px 12px !important;
  border: 1px solid rgba(255,210,109,0.26) !important;
  border-radius: 12px !important;
  background:
    radial-gradient(circle at 100% 0%, rgba(255,210,109,0.13), transparent 54%),
    rgba(255,255,255,0.035) !important;
}

.main .mart-balance-card span {
  display: block !important;
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
  font-family: var(--font-pixel) !important;
  font-size: 9px !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
}

.main .mart-balance-card strong {
  display: block !important;
  margin-top: 4px !important;
  color: var(--pokemon-yellow) !important;
  -webkit-text-fill-color: var(--pokemon-yellow) !important;
  font-family: var(--font-pixel) !important;
  font-size: 22px !important;
  line-height: 1 !important;
  font-variant-numeric: tabular-nums !important;
}

.main .mart-pill {
  min-height: 26px !important;
  border-color: var(--border-soft) !important;
  border-radius: 999px !important;
  background: rgba(255,255,255,0.045) !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
}

.main .mart-register-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  gap: 8px !important;
  margin: 10px 0 12px !important;
}

.main .mart-register-card {
  min-height: 58px !important;
  padding: 9px 10px !important;
}

.main .mart-register-card.is-main {
  border-color: rgba(255,210,109,0.3) !important;
  background:
    radial-gradient(circle at 100% 0%, rgba(255,210,109,0.12), transparent 56%),
    rgba(255,255,255,0.04) !important;
  box-shadow: inset 3px 0 0 var(--pokemon-yellow) !important;
}

.main .mart-label {
  font-size: 9px !important;
}

.main .mart-value {
  margin-top: 5px !important;
  font-size: 16px !important;
}

.main .mart-register-card.is-main .mart-value {
  color: var(--pokemon-yellow) !important;
  -webkit-text-fill-color: var(--pokemon-yellow) !important;
  font-size: 20px !important;
}

.main .mart-aisle-head {
  margin: 12px 0 10px !important;
  padding: 10px 12px !important;
  border-color: rgba(139,171,216,0.14) !important;
  border-radius: 12px !important;
  background: rgba(255,255,255,0.03) !important;
  box-shadow: none !important;
}

.main .mart-aisle-title {
  margin: 0 !important;
  font-size: 15px !important;
  line-height: 1.1 !important;
}

.main .shop-card {
  min-height: 196px !important;
  margin-bottom: 6px !important;
  border-color: rgba(139,171,216,0.15) !important;
  border-radius: 14px !important;
  background:
    radial-gradient(circle at 18% 22%, rgba(255,189,92,0.09), transparent 44%),
    linear-gradient(180deg, rgba(18,30,49,0.96), rgba(10,17,29,0.98)) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.055), 0 10px 22px rgba(0,0,0,0.18) !important;
}

.main .shop-card::before {
  display: none !important;
}

.main .shop-card.is-sale {
  border-color: rgba(255,210,109,0.45) !important;
  box-shadow: inset 3px 0 0 var(--pokemon-yellow), 0 10px 22px rgba(0,0,0,0.2) !important;
}

.main .shop-card.is-pending-sale {
  border-color: rgba(69,209,255,0.36) !important;
  box-shadow: inset 3px 0 0 var(--info), 0 10px 22px rgba(0,0,0,0.18) !important;
}

.main .shop-card.is-delivery-locked {
  opacity: 0.82 !important;
}

.main .shop-head {
  min-height: 48px !important;
  display: flex !important;
  align-items: flex-start !important;
  justify-content: space-between !important;
  gap: 10px !important;
  padding: 10px 11px 8px !important;
  border-bottom-color: var(--border-soft) !important;
  background: rgba(6, 12, 22, 0.54) !important;
}

.main .shop-title-block {
  min-width: 0 !important;
  display: grid !important;
  gap: 5px !important;
}

.main .shop-name {
  font-size: 12px !important;
  font-weight: 950 !important;
  line-height: 1.14 !important;
}

.main .shop-category-badge,
.main .shop-state-badge,
.main .shop-discount-badge {
  display: inline-flex !important;
  width: fit-content !important;
  max-width: 100% !important;
  align-items: center !important;
  min-height: 22px !important;
  padding: 3px 7px !important;
  border: 1px solid rgba(139,171,216,0.16) !important;
  border-radius: 999px !important;
  background: rgba(255,255,255,0.04) !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-family: var(--font-pixel) !important;
  font-size: 9px !important;
  font-weight: 900 !important;
  line-height: 1 !important;
  text-transform: uppercase !important;
  white-space: nowrap !important;
}

.main .shop-state-row {
  flex: 0 0 auto !important;
  display: flex !important;
  justify-content: flex-end !important;
}

.main .shop-state-badge.is-sale,
.main .shop-discount-badge {
  border-color: rgba(255,210,109,0.35) !important;
  background: rgba(255,210,109,0.1) !important;
  color: var(--pokemon-yellow) !important;
  -webkit-text-fill-color: var(--pokemon-yellow) !important;
}

.main .shop-state-badge.is-locked,
.main .shop-discount-badge.is-pending {
  border-color: rgba(69,209,255,0.3) !important;
  background: rgba(69,209,255,0.085) !important;
  color: #8fdcff !important;
  -webkit-text-fill-color: #8fdcff !important;
}

.main .shop-state-badge.is-poor,
.main .shop-state-badge.is-used,
.main .shop-discount-badge.is-used {
  border-color: rgba(139,171,216,0.15) !important;
  background: rgba(255,255,255,0.035) !important;
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
}

.main .shop-body {
  grid-template-columns: 74px minmax(0, 1fr) !important;
  gap: 12px !important;
  padding: 12px 11px 13px !important;
}

.main .shop-icon-slot {
  width: 72px !important;
  height: 72px !important;
  border-color: var(--border-soft) !important;
  border-radius: 12px !important;
  background:
    radial-gradient(circle at 50% 42%, rgba(255,210,109,0.11), transparent 54%),
    rgba(255,255,255,0.035) !important;
}

.main .shop-icon {
  width: 58px !important;
  height: 58px !important;
  max-width: 58px !important;
  max-height: 58px !important;
}

.main .shop-desc {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 14px !important;
  line-height: 1.25 !important;
}

.main .shop-price {
  display: grid !important;
  gap: 6px !important;
  padding: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
}

.main .shop-coin-value {
  min-height: 30px !important;
  min-width: 60px !important;
  padding: 4px 8px !important;
  border-color: rgba(255,210,109,0.26) !important;
  border-radius: 9px !important;
  background: rgba(255,210,109,0.08) !important;
  color: var(--pokemon-yellow) !important;
  -webkit-text-fill-color: var(--pokemon-yellow) !important;
}

.main .shop-old-price {
  opacity: 0.7 !important;
  border-color: rgba(139,171,216,0.14) !important;
  background: rgba(255,255,255,0.025) !important;
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
}

.main .shop-coin {
  font-size: 18px !important;
}

.main .shop-amount {
  color: inherit !important;
  -webkit-text-fill-color: currentColor !important;
  font-size: 17px !important;
  font-weight: 950 !important;
}

.main .shop-missing {
  margin-top: 0 !important;
  padding: 5px 7px !important;
  border-radius: 10px !important;
}

div[data-testid="column"]:has(.shop-card) .stButton {
  display: flex !important;
  justify-content: flex-end !important;
  margin-top: -2px !important;
  margin-bottom: 12px !important;
}

div[data-testid="column"]:has(.shop-card) .stButton > button {
  width: auto !important;
  min-width: 108px !important;
  min-height: 32px !important;
  padding: 0 13px !important;
  border-radius: 10px !important;
  border-color: rgba(77,141,255,0.42) !important;
  background: linear-gradient(180deg, #5aa6ff, #2f6fff) !important;
}

div[data-testid="column"]:has(.shop-card) .stButton > button:disabled {
  border-color: rgba(139,171,216,0.09) !important;
  background: rgba(255,255,255,0.035) !important;
  color: rgba(184,199,220,0.55) !important;
  -webkit-text-fill-color: rgba(184,199,220,0.55) !important;
}

div[data-testid="column"]:has(.shop-card) .stButton > button p {
  font-size: 11px !important;
  font-weight: 900 !important;
}

/* Saves */
.main .saves-hero {
  min-height: 86px !important;
  display: grid !important;
  grid-template-columns: minmax(0, 1fr) auto !important;
  align-items: end !important;
  padding: 14px 16px !important;
}

.main .saves-hero-side {
  border: 1px solid var(--border-normal) !important;
  border-radius: 999px !important;
  background: rgba(255,255,255,0.055) !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 13px !important;
}

.main .saves-status-grid {
  gap: 8px !important;
  margin: 10px 0 14px !important;
}

.main .saves-stat {
  min-height: 72px !important;
  padding: 10px !important;
}

.main .saves-stat-value {
  font-size: 13px !important;
}

.main .saves-stat-detail {
  font-size: 13px !important;
}

.main .saves-current-card,
.main .saves-history-card,
.main .saves-admin-panel,
.main .saves-upload-panel,
.main .saves-empty-state,
.main .bill-save-meta {
  border-color: var(--border-normal) !important;
  border-radius: 14px !important;
  background:
    linear-gradient(135deg, rgba(77,141,255,0.045), transparent 42%),
    rgba(11, 19, 32, 0.94) !important;
  box-shadow: none !important;
}

.main .saves-current-card {
  border-left-color: var(--accent) !important;
}

.main .saves-card-meta {
  gap: 7px !important;
}

.main .saves-meta-cell {
  min-height: 44px !important;
  border-color: var(--border-soft) !important;
  border-radius: 10px !important;
  background: rgba(255,255,255,0.035) !important;
}

.main .saves-meta-value {
  font-size: 13px !important;
}

.main .saves-meta-cell.is-technical .saves-meta-value {
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace !important;
  font-size: 12px !important;
}

.main .saves-admin-panel {
  border-left-color: var(--danger) !important;
  background:
    linear-gradient(90deg, rgba(255,82,99,0.1), transparent 50%),
    rgba(11, 19, 32, 0.94) !important;
}

.main .saves-empty-state {
  border-style: dashed !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
}

.main .saves-empty-state strong {
  display: block !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 13px !important;
}

div[data-testid="stFileUploaderDropzone"] {
  min-height: 112px !important;
  border-color: rgba(114,185,255,0.28) !important;
  border-radius: 14px !important;
  background: rgba(9, 15, 26, 0.82) !important;
}

/* League and tables */
.main .league-hero {
  min-height: 92px !important;
  padding: 14px 16px !important;
  grid-template-columns: minmax(0, 1fr) minmax(320px, .72fr) !important;
}

.main .league-title {
  font-size: clamp(22px, 2.1vw, 30px) !important;
}

.main .league-subtitle {
  margin-top: 7px !important;
  font-size: 13px !important;
}

.main .league-hero-grid {
  gap: 8px !important;
}

.main .league-status-card {
  min-height: 50px !important;
  padding: 8px 10px !important;
}

.main .league-status-card strong {
  margin-top: 4px !important;
  font-size: 14px !important;
}

.main .league-section-heading {
  margin: 16px 0 8px !important;
}

.main .league-section-copy {
  margin: 5px 0 0 12px !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 13px !important;
  line-height: 1.25 !important;
}

.main .league-division-card,
.main .league-history-card,
.main .league-status-table,
.main .league-table-shell,
.main .hof-card {
  border-color: var(--border-normal) !important;
  border-radius: 14px !important;
  background:
    linear-gradient(135deg, rgba(77,141,255,0.055), transparent 38%),
    rgba(10, 17, 29, 0.96) !important;
  box-shadow: none !important;
}

.main .league-card-player {
  grid-template-columns: 38px minmax(0, 1fr) auto auto auto !important;
  min-height: 42px !important;
  border-color: var(--border-soft) !important;
  border-radius: 10px !important;
  background: rgba(255,255,255,0.035) !important;
}

.main .league-card-player.is-history-row {
  grid-template-columns: 38px minmax(0, 1fr) auto !important;
}

.main .league-card-main {
  min-width: 0 !important;
}

.main .league-card-score,
.main .league-card-coins {
  display: grid !important;
  justify-items: end !important;
  min-width: 54px !important;
  line-height: 1 !important;
}

.main .league-card-score strong,
.main .league-card-coins strong {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 16px !important;
  font-weight: 950 !important;
}

.main .league-card-coins strong {
  color: var(--pokemon-yellow) !important;
  -webkit-text-fill-color: var(--pokemon-yellow) !important;
}

.main .league-card-score span,
.main .league-card-coins span {
  color: var(--text-muted) !important;
  -webkit-text-fill-color: var(--text-muted) !important;
  font-size: 10px !important;
  font-weight: 850 !important;
  text-transform: uppercase !important;
}

.main .league-card-player.is-current-player,
.main .league-status-table tr.is-current-player td {
  border-color: rgba(69,209,255,0.34) !important;
  background:
    linear-gradient(90deg, rgba(69,209,255,0.11), transparent 58%),
    rgba(12, 25, 43, 0.9) !important;
}

.main .league-card-player.is-current-player,
.main .league-status-table tr.is-current-player td:first-child {
  box-shadow: inset 3px 0 0 var(--accent) !important;
}

.main .league-card-player.is-retired-player,
.main .league-status-table tr.is-retired-player td {
  opacity: .72 !important;
}

.main .league-card-player:hover {
  border-color: rgba(114,185,255,0.25) !important;
}

.main .league-status-table th {
  background: rgba(255,255,255,0.045) !important;
}

.main .league-status-table td {
  background: rgba(7, 12, 22, 0.86) !important;
}

.main .league-trainer-badge {
  border-radius: 999px !important;
}

/* Hall of Fame */
.main .hof-empty {
  display: grid !important;
  gap: 4px !important;
  padding: 18px !important;
  border-color: rgba(255,210,109,0.24) !important;
  border-radius: 14px !important;
  background:
    linear-gradient(90deg, rgba(255,210,109,0.08), transparent 50%),
    rgba(11, 19, 32, 0.94) !important;
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 14px !important;
}

.main .hof-empty strong {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 16px !important;
}

/* Secondary pages 1F: same visual intent, selector specificity fixed */
.main .norma-hero,
.main .cup-hero,
.main .ju-hero,
.main .season-hero {
  min-height: 104px !important;
  padding: 15px 16px !important;
  border-color: var(--border-normal) !important;
  border-left: 4px solid var(--primary) !important;
  border-radius: 16px !important;
  clip-path: none !important;
  background:
    linear-gradient(118deg, rgba(77,141,255,0.12) 0 32%, transparent 32% 100%),
    linear-gradient(180deg, rgba(18,30,49,0.96), rgba(8,14,26,0.98)) !important;
  box-shadow: var(--poke-shadow-card) !important;
}

.main .norma-hero::before {
  content: "" !important;
  position: absolute !important;
  inset: 0 !important;
  pointer-events: none !important;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.025) 0 1px, transparent 1px 100%) 0 0 / 28px 100%,
    linear-gradient(180deg, rgba(255,255,255,0.025) 0 1px, transparent 1px 100%) 0 0 / 100% 24px !important;
  opacity: .42 !important;
}

.main .norma-hero::after {
  content: "" !important;
  position: absolute !important;
  right: 22px !important;
  top: 14px !important;
  width: 120px !important;
  height: 72px !important;
  border: 1px solid rgba(216,223,232,0.12) !important;
  border-radius: 0 !important;
  background:
    linear-gradient(135deg, transparent 0 56%, rgba(110,168,255,0.11) 56% 100%),
    linear-gradient(180deg, rgba(255,255,255,0.05), transparent) !important;
  opacity: .45 !important;
  transform: skewX(-14deg) !important;
}

.main .hof-hero {
  border-left: 4px solid var(--pokemon-yellow) !important;
  background:
    linear-gradient(118deg, rgba(255,210,77,0.11) 0 32%, transparent 32% 100%),
    linear-gradient(180deg, rgba(18,30,49,0.96), rgba(8,14,26,0.98)) !important;
}

.main .norma-title,
.main .cup-title,
.main .ju-hero-title,
.main .season-title {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: clamp(22px, 2.2vw, 30px) !important;
  text-shadow: none !important;
}

.main .norma-subtitle,
.main .norma-summary,
.main .cup-sub,
.main .ju-hero-sub,
.main .season-subtitle {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 14px !important;
  line-height: 1.3 !important;
}

.main .norma-kicker,
.main .cup-kicker,
.main .season-kicker,
.main .norma-doc-chip,
.main .cup-pill,
.main .season-pill,
.main .ju-chip,
.main .ju-status-badge {
  border-radius: 999px !important;
  clip-path: none !important;
}

.main .norma-kicker,
.main .cup-kicker,
.main .season-kicker {
  display: inline-flex !important;
  align-items: center !important;
  min-height: 24px !important;
  padding: 4px 8px !important;
}

.main .norma-kicker,
.main .cup-kicker,
.main .season-kicker,
.main .norma-block-head,
.main .cup-section,
.main .doubles-section,
.main .ju-toolbar,
.main .season-section-title {
  border-color: var(--border-normal) !important;
  border-left: 4px solid var(--primary) !important;
  border-radius: 12px !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.015)),
    rgba(11,19,32,0.94) !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.main .hof-kicker,
.main .hof-section-title {
  border-left-color: var(--pokemon-yellow) !important;
  color: var(--pokemon-yellow) !important;
  -webkit-text-fill-color: var(--pokemon-yellow) !important;
}

.main .norma-block,
.main .norma-list-item,
.main .cup-mode-card,
.main .cup-metric,
.main .cup-vs-card,
.main .cup-paste-card,
.main .cup-match,
.main .doubles-card,
.main .doubles-metric,
.main .doubles-note,
.main .doubles-logo-wrap,
.main .ju-action-card,
.main .ju-penalty-card,
.main .ju-case-card,
.main .ju-docket,
.main .ju-docket-cell,
.main .ju-detail-block,
.main .ju-empty,
.main .season-card,
.main .season-alert,
.main .season-version-row {
  border-color: var(--border-normal) !important;
  border-radius: 14px !important;
  background:
    linear-gradient(135deg, rgba(77,141,255,0.055), transparent 42%),
    rgba(10,17,29,0.94) !important;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.055) !important;
}

.main .norma-list-bullet,
.main .ju-case-no {
  border-color: rgba(114,185,255,0.28) !important;
  border-radius: 12px !important;
  background: rgba(77,141,255,0.1) !important;
  color: var(--primary-hover) !important;
  -webkit-text-fill-color: var(--primary-hover) !important;
}

.main .cup-mode-card.is-active {
  border-color: rgba(114,185,255,0.42) !important;
  border-left-color: var(--primary) !important;
  background:
    linear-gradient(116deg, rgba(77,141,255,0.16) 0 35%, transparent 35% 100%),
    rgba(12,25,43,0.94) !important;
}

.main .doubles-banner,
.main .doubles-round-head,
.main .doubles-card-head {
  border-color: var(--border-normal) !important;
  border-left: 4px solid var(--primary) !important;
  border-radius: 12px !important;
  clip-path: none !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.015)),
    rgba(11,19,32,0.94) !important;
}

.main .doubles-champion {
  border-color: rgba(255,210,77,0.34) !important;
  border-radius: 14px !important;
  background:
    linear-gradient(90deg, rgba(255,210,77,0.14), transparent 56%),
    rgba(11,19,32,0.94) !important;
  color: var(--pokemon-yellow) !important;
  -webkit-text-fill-color: var(--pokemon-yellow) !important;
}

.main .ju-case-title,
.main .ju-docket-title,
.main .season-value,
.main .cup-card-value,
.main .doubles-team-name {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.main .ju-case-kv,
.main .ju-docket-cell,
.main .ju-detail-block,
.main .season-detail,
.main .season-alert-body,
.main .season-version-meta,
.main .doubles-team-meta,
.main .doubles-round-team-meta {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 13px !important;
  line-height: 1.3 !important;
}

.main .hof-empty {
  position: relative !important;
  min-height: 126px !important;
  padding: 18px 18px 18px 74px !important;
  border-style: dashed !important;
  border-color: rgba(255,210,77,0.24) !important;
}

.main .hof-empty:before {
  content: "HF" !important;
  position: absolute !important;
  left: 22px !important;
  top: 50% !important;
  width: 34px !important;
  height: 34px !important;
  display: grid !important;
  place-items: center !important;
  border: 1px solid rgba(255,210,77,0.3) !important;
  border-radius: 999px !important;
  background: rgba(255,210,77,0.1) !important;
  color: var(--pokemon-yellow) !important;
  -webkit-text-fill-color: var(--pokemon-yellow) !important;
  font-family: var(--font-pixel) !important;
  font-size: 9px !important;
  transform: translateY(-50%) !important;
}

/* Notifications */
.app-notice-menu summary {
  min-height: 38px !important;
  overflow: hidden !important;
  color: transparent !important;
  -webkit-text-fill-color: transparent !important;
  font-size: 0 !important;
}

.app-notice-menu summary > span:first-child {
  min-width: 0 !important;
  overflow: hidden !important;
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
  font-size: 12px !important;
  font-weight: 850 !important;
  text-overflow: ellipsis !important;
  white-space: nowrap !important;
}

.app-notice-chevron {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
  font-size: 0 !important;
}

.app-notice,
.app-notice-menu-panel {
  border-color: var(--border-soft) !important;
  border-radius: 12px !important;
  background: rgba(7, 12, 22, 0.94) !important;
}

.app-notice-title {
  color: var(--text-primary) !important;
  -webkit-text-fill-color: var(--text-primary) !important;
}

.app-notice-body {
  color: var(--text-secondary) !important;
  -webkit-text-fill-color: var(--text-secondary) !important;
}

@media (max-width: 980px) {
  .main .league-hero,
  .main .saves-hero {
    grid-template-columns: 1fr !important;
  }
  .main .mart-register-grid,
  .main .trainers-status-grid,
  .main .saves-status-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
  }
  .main .trainer-grid {
    grid-template-columns: 1fr !important;
  }
  .main .trainer-metrics {
    grid-template-columns: 1fr !important;
  }
}

@media (max-width: 640px) {
  .main .league-hero,
  .main .mart-hero,
  .main .saves-hero,
  .main .hof-hero,
  .main .matchup-hero {
    grid-template-columns: 1fr !important;
    padding: 12px !important;
  }
  .main .mart-register-grid,
  .main .trainers-status-grid,
  .main .saves-status-grid {
    grid-template-columns: 1fr !important;
  }
  .main .shop-body {
    grid-template-columns: 62px minmax(0, 1fr) !important;
  }
  .main .shop-icon-slot {
    width: 62px !important;
    height: 62px !important;
  }
  .main .shop-icon {
    width: 50px !important;
    height: 50px !important;
  }
  .main .champ-box-grid {
    grid-template-columns: repeat(3, minmax(76px, 1fr)) !important;
  }
  .main .league-card-player {
    grid-template-columns: 32px minmax(0, 1fr) auto auto !important;
  }
  .main .league-card-score,
  .main .league-card-coins {
    min-width: 42px !important;
  }
  .main .league-movement-badge {
    grid-column: 2 / -1 !important;
    justify-self: start !important;
  }
  .main .saves-hero-side {
    justify-self: start !important;
    white-space: normal !important;
  }
}
</style>
"""


def apply_final_polish() -> None:
    st.markdown(FINAL_POLISH_CSS, unsafe_allow_html=True)
