from __future__ import annotations

from typing import Any

import streamlit as st


PHASE2_CSS = """
<style>
:root {
  --p2-bg: #070b14;
  --p2-bg-2: #0b1220;
  --p2-bg-3: #0e1728;
  --p2-surface: #101827;
  --p2-surface-2: #141f33;
  --p2-surface-3: #19263d;
  --p2-surface-glass: rgba(16, 24, 39, 0.88);
  --p2-border: rgba(228, 238, 255, 0.08);
  --p2-border-2: rgba(228, 238, 255, 0.14);
  --p2-text: #f4f7fc;
  --p2-text-2: #b3bdcd;
  --p2-muted: #737f93;
  --p2-primary: #5da2ff;
  --p2-primary-2: #2f78e6;
  --p2-primary-soft: rgba(93, 162, 255, 0.12);
  --p2-cyan: #58d6ff;
  --p2-gold: #f4c84a;
  --p2-green: #45d483;
  --p2-red: #ff6172;
  --p2-purple: #8e7dff;
  --p2-radius-sm: 10px;
  --p2-radius: 14px;
  --p2-radius-lg: 18px;
  --p2-cut: polygon(0 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%);
  --p2-shadow: 0 14px 34px rgba(0, 0, 0, 0.24);
  --p2-shadow-sm: 0 8px 20px rgba(0, 0, 0, 0.18);

  --text-primary: var(--p2-text);
  --text-secondary: var(--p2-text-2);
  --text-muted: var(--p2-muted);
  --surface-0: var(--p2-bg);
  --surface-1: var(--p2-surface);
  --surface-2: var(--p2-surface-2);
  --surface-3: var(--p2-surface-3);
  --border-soft: var(--p2-border);
  --border-normal: var(--p2-border-2);
  --primary: var(--p2-primary);
  --primary-soft: var(--p2-primary-soft);
  --pokemon-yellow: var(--p2-gold);
  --radius-input: var(--p2-radius-sm);
  --radius-card: var(--p2-radius);
  --radius-large: var(--p2-radius-lg);
  --shadow-card: var(--p2-shadow-sm);
  --shadow-hero: var(--p2-shadow);
}

html,
body,
.stApp,
.stApp * {
  letter-spacing: 0 !important;
}

html,
body,
[class*="css"] {
  color: var(--p2-text-2);
}

.stApp {
  background:
    radial-gradient(circle at 18% -8%, rgba(93, 162, 255, 0.12), transparent 28%),
    radial-gradient(circle at 95% 12%, rgba(244, 200, 74, 0.05), transparent 28%),
    linear-gradient(180deg, var(--p2-bg) 0%, var(--p2-bg-2) 58%, #070b13 100%) !important;
  color: var(--p2-text) !important;
}

.stApp::before {
  height: 1px !important;
  background: linear-gradient(90deg, transparent, rgba(93, 162, 255, 0.55), transparent) !important;
  border: 0 !important;
  box-shadow: none !important;
  opacity: 0.5 !important;
}

.stApp::after {
  display: none !important;
  content: "" !important;
}

.main {
  position: relative !important;
  isolation: isolate !important;
}

.main::before {
  content: "" !important;
  position: fixed !important;
  inset: 0 !important;
  z-index: -2 !important;
  pointer-events: none !important;
  opacity: 1 !important;
  background:
    linear-gradient(120deg, transparent 0 20%, rgba(255, 255, 255, 0.018) 20% 20.7%, transparent 20.7% 100%) 0 0 / 620px 340px,
    linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px) 0 0 / 36px 36px,
    linear-gradient(180deg, rgba(255,255,255,0.016) 1px, transparent 1px) 0 0 / 36px 36px,
    linear-gradient(180deg, rgba(14, 23, 40, 0.4), rgba(7, 11, 20, 0.9)) !important;
}

.main::after {
  content: var(--section-watermark, "POKEAPP") !important;
  position: fixed !important;
  right: 4vw !important;
  bottom: 5vh !important;
  z-index: -1 !important;
  pointer-events: none !important;
  color: rgba(255, 255, 255, 0.028) !important;
  font-family: var(--font-pixel), var(--font-ui), sans-serif !important;
  font-size: clamp(88px, 18vw, 250px) !important;
  font-weight: 950 !important;
  line-height: 1 !important;
  text-transform: uppercase !important;
  white-space: nowrap !important;
}

.main .block-container {
  width: min(100%, 1540px) !important;
  max-width: 1540px !important;
  padding-top: 4.25rem !important;
  padding-left: clamp(16px, 2vw, 32px) !important;
  padding-right: clamp(16px, 2vw, 32px) !important;
}

.main h1,
.main h2,
.main h3,
.main h4,
.main h5,
.main h6 {
  color: var(--p2-text) !important;
  text-transform: none !important;
  text-shadow: none !important;
}

.main h1 {
  font-size: clamp(25px, 2.3vw, 36px) !important;
  line-height: 1.08 !important;
  margin-bottom: 0.7rem !important;
}

.main h2 {
  font-size: clamp(20px, 1.7vw, 26px) !important;
}

.main h3 {
  font-size: 18px !important;
}

.main p,
.main li,
.main span,
.main label,
.main div {
  color: var(--p2-text-2);
}

.main strong,
.main b {
  color: var(--p2-text);
}

.main hr {
  height: 1px !important;
  margin: 24px 0 !important;
  background: linear-gradient(90deg, transparent, rgba(228, 238, 255, 0.16), transparent) !important;
}

/* Streamlit chrome and core controls */
header[data-testid="stHeader"],
div[data-testid="stDecoration"] {
  background: transparent !important;
}

.main .stButton > button,
section[data-testid="stSidebar"] .stButton > button {
  min-height: 38px !important;
  border: 1px solid var(--p2-border-2) !important;
  border-radius: var(--p2-radius-sm) !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015)),
    var(--p2-surface-2) !important;
  color: var(--p2-text) !important;
  box-shadow: none !important;
  transition: transform 150ms ease, border-color 150ms ease, background 150ms ease, color 150ms ease !important;
}

.main .stButton > button:hover,
section[data-testid="stSidebar"] .stButton > button:hover {
  transform: translateY(-1px) !important;
  border-color: rgba(93, 162, 255, 0.34) !important;
  background:
    linear-gradient(180deg, rgba(93,162,255,0.1), rgba(93,162,255,0.035)),
    var(--p2-surface-2) !important;
}

.main .stButton > button:active,
section[data-testid="stSidebar"] .stButton > button:active {
  transform: scale(0.99) !important;
}

.main .stButton > button[kind="primary"],
section[data-testid="stSidebar"] .stButton > button[kind="primary"] {
  border-color: rgba(93, 162, 255, 0.52) !important;
  background:
    linear-gradient(180deg, rgba(93,162,255,0.28), rgba(47,120,230,0.18)),
    var(--p2-surface-2) !important;
  box-shadow: inset 3px 0 0 var(--p2-primary) !important;
}

.main .stButton > button p,
section[data-testid="stSidebar"] .stButton > button p {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 13px !important;
  font-weight: 800 !important;
}

.main input,
.main textarea,
.main [data-baseweb="select"] > div,
.main div[data-baseweb="input"],
.main div[data-baseweb="textarea"] {
  border-color: var(--p2-border-2) !important;
  border-radius: var(--p2-radius-sm) !important;
  background: #0d1422 !important;
  color: var(--p2-text) !important;
  box-shadow: none !important;
}

.main input:focus,
.main textarea:focus,
.main [data-baseweb="select"] > div:focus-within,
.main div[data-baseweb="input"]:focus-within,
.main div[data-baseweb="textarea"]:focus-within {
  border-color: rgba(93, 162, 255, 0.7) !important;
  box-shadow: 0 0 0 3px rgba(93, 162, 255, 0.12) !important;
}

.main div[data-testid="stSelectbox"] label,
.main div[data-testid="stTextInput"] label,
.main div[data-testid="stTextArea"] label,
.main div[data-testid="stNumberInput"] label,
.main div[data-testid="stRadio"] label,
.main div[data-testid="stCheckbox"] label {
  color: var(--p2-text-2) !important;
  font-size: 11px !important;
  font-weight: 850 !important;
  text-transform: uppercase !important;
}

.main div[data-testid="stTabs"] div[data-baseweb="tab-list"],
.main div[data-testid="stTabs"] [role="tablist"] {
  gap: 8px !important;
  align-items: flex-end !important;
  padding: 0 0 8px !important;
  border: 0 !important;
  border-bottom: 1px solid var(--p2-border) !important;
  background: transparent !important;
  box-shadow: none !important;
}

.main div[data-testid="stTabs"] button[data-baseweb="tab"],
.main div[data-testid="stTabs"] button[role="tab"] {
  flex: 0 1 auto !important;
  min-width: max-content !important;
  min-height: 36px !important;
  padding: 0 12px !important;
  border: 0 !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  background: transparent !important;
  clip-path: none !important;
  box-shadow: none !important;
}

.main div[data-testid="stTabs"] button[data-baseweb="tab"] *,
.main div[data-testid="stTabs"] button[role="tab"] * {
  color: var(--p2-muted) !important;
  -webkit-text-fill-color: var(--p2-muted) !important;
  font-size: 13px !important;
  font-weight: 850 !important;
  text-align: center !important;
  white-space: nowrap !important;
}

.main div[data-testid="stTabs"] button[aria-selected="true"],
.main div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
  border-color: var(--p2-primary) !important;
  background: rgba(93, 162, 255, 0.055) !important;
}

.main div[data-testid="stTabs"] button[aria-selected="true"] *,
.main div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] * {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
}

.main div[data-testid="stExpander"] details,
section[data-testid="stSidebar"] div[data-testid="stExpander"] details {
  border: 1px solid var(--p2-border) !important;
  border-radius: var(--p2-radius) !important;
  background: rgba(16, 24, 39, 0.72) !important;
  box-shadow: none !important;
}

.main div[data-testid="stExpander"] summary,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary {
  min-height: 38px !important;
  padding: 9px 12px !important;
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] summary [data-testid="stIconMaterial"],
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary .material-symbols-rounded,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary .material-symbols-outlined {
  width: 14px !important;
  min-width: 14px !important;
  height: 14px !important;
  overflow: hidden !important;
  color: transparent !important;
  -webkit-text-fill-color: transparent !important;
  font-size: 0 !important;
}

section[data-testid="stSidebar"] div[data-testid="stExpander"] summary [data-testid="stIconMaterial"]::before,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary .material-symbols-rounded::before,
section[data-testid="stSidebar"] div[data-testid="stExpander"] summary .material-symbols-outlined::before {
  content: "" !important;
  display: block !important;
  width: 8px !important;
  height: 8px !important;
  margin: 1px auto 0 !important;
  border: solid var(--p2-text-2) !important;
  border-width: 0 2px 2px 0 !important;
  transform: rotate(45deg) !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
  width: 236px !important;
  min-width: 236px !important;
  max-width: 236px !important;
  border-right: 1px solid rgba(228, 238, 255, 0.1) !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.018) 1px, transparent 1px) 0 0 / 100% 34px,
    linear-gradient(145deg, rgba(93,162,255,0.08), transparent 36%),
    linear-gradient(180deg, #0a101d 0%, #090d17 100%) !important;
  box-shadow: 10px 0 28px rgba(0, 0, 0, 0.22) !important;
}

section[data-testid="stSidebar"]::before {
  display: none !important;
}

section[data-testid="stSidebar"] .block-container {
  padding-top: 20px !important;
  padding-left: 12px !important;
  padding-right: 12px !important;
}

section[data-testid="stSidebar"] .sidebar-brand {
  display: grid !important;
  grid-template-columns: 42px minmax(0, 1fr) !important;
  gap: 10px !important;
  align-items: center !important;
  margin: 0 0 12px !important;
  padding: 10px !important;
  border: 1px solid var(--p2-border) !important;
  border-radius: var(--p2-radius) !important;
  background:
    linear-gradient(135deg, rgba(93,162,255,0.11), transparent 46%),
    rgba(255,255,255,0.025) !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] .sidebar-brand-mark {
  width: 42px !important;
  height: 42px !important;
  display: grid !important;
  place-items: center !important;
  border: 1px solid rgba(93, 162, 255, 0.28) !important;
  border-radius: 50% !important;
  background:
    linear-gradient(180deg, var(--p2-red) 0 47%, #111827 47% 53%, #f4f7fc 53% 100%) !important;
  box-shadow: inset 0 0 0 3px rgba(7, 11, 20, 0.7), 0 0 18px rgba(93, 162, 255, 0.14) !important;
}

section[data-testid="stSidebar"] .sidebar-brand-mark::before {
  content: "" !important;
  width: 14px !important;
  height: 14px !important;
  border-radius: 50% !important;
  border: 3px solid #111827 !important;
  background: #f4f7fc !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] .sidebar-brand-mark span {
  display: none !important;
}

section[data-testid="stSidebar"] .sidebar-brand-name {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 15px !important;
  font-weight: 950 !important;
  text-transform: uppercase !important;
}

section[data-testid="stSidebar"] .sidebar-brand-sub {
  margin-top: 1px !important;
  color: var(--p2-primary) !important;
  -webkit-text-fill-color: var(--p2-primary) !important;
  font-size: 10px !important;
  font-weight: 850 !important;
  text-transform: uppercase !important;
}

section[data-testid="stSidebar"] .profile-card {
  margin: 0 0 10px !important;
  padding: 10px !important;
  border: 1px solid var(--p2-border) !important;
  border-radius: var(--p2-radius) !important;
  background:
    linear-gradient(135deg, rgba(93,162,255,0.08), transparent 52%),
    rgba(255,255,255,0.025) !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] .profile-head {
  grid-template-columns: 52px minmax(0, 1fr) !important;
  gap: 9px !important;
}

section[data-testid="stSidebar"] .profile-avatar {
  width: 52px !important;
  height: 52px !important;
  border-radius: 12px !important;
  border-color: rgba(228,238,255,0.12) !important;
  background: var(--p2-surface-2) !important;
}

section[data-testid="stSidebar"] .profile-name {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 13px !important;
  font-weight: 950 !important;
}

section[data-testid="stSidebar"] .profile-sub {
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 11px !important;
  font-weight: 750 !important;
}

section[data-testid="stSidebar"] .profile-sub::before {
  content: "" !important;
  display: inline-block !important;
  width: 7px !important;
  height: 7px !important;
  margin-right: 6px !important;
  border-radius: 50% !important;
  background: var(--p2-green) !important;
  box-shadow: 0 0 10px rgba(69, 212, 131, 0.4) !important;
}

section[data-testid="stSidebar"] .badges-row {
  margin: 8px 0 6px !important;
  gap: 4px !important;
}

section[data-testid="stSidebar"] .badge-dot {
  width: 12px !important;
  height: 6px !important;
  border-radius: 2px !important;
  background: rgba(228, 238, 255, 0.12) !important;
}

section[data-testid="stSidebar"] .badge-dot.badge-on {
  background: linear-gradient(90deg, var(--p2-primary), var(--p2-cyan)) !important;
}

section[data-testid="stSidebar"] .mini-team {
  gap: 4px !important;
}

section[data-testid="stSidebar"] .mini-mon {
  width: 25px !important;
  height: 25px !important;
  border: 1px solid rgba(228,238,255,0.1) !important;
  border-radius: 8px !important;
  background: rgba(255,255,255,0.035) !important;
}

section[data-testid="stSidebar"] .mini-mon img {
  max-width: 25px !important;
  max-height: 25px !important;
}

section[data-testid="stSidebar"] .sidebar-nav-title {
  margin: 14px 0 7px !important;
  padding: 0 2px !important;
  color: var(--p2-muted) !important;
  -webkit-text-fill-color: var(--p2-muted) !important;
  font-size: 10px !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
}

section[data-testid="stSidebar"] div.stButton > button {
  position: relative !important;
  min-height: 38px !important;
  margin-bottom: 4px !important;
  justify-content: flex-start !important;
  padding-left: 10px !important;
  border-color: transparent !important;
  border-radius: 11px !important;
  background: transparent !important;
  box-shadow: none !important;
  overflow: hidden !important;
}

section[data-testid="stSidebar"] div.stButton > button::after {
  content: "" !important;
  position: absolute !important;
  inset: 0 0 0 auto !important;
  width: 18px !important;
  opacity: 0 !important;
  background: linear-gradient(135deg, transparent 0 48%, rgba(93,162,255,0.18) 48% 100%) !important;
  transition: opacity 150ms ease !important;
}

section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
  border-color: rgba(93,162,255,0.22) !important;
  background:
    linear-gradient(90deg, rgba(93,162,255,0.15), rgba(93,162,255,0.035)),
    rgba(255,255,255,0.018) !important;
  box-shadow: inset 3px 0 0 var(--p2-primary) !important;
}

section[data-testid="stSidebar"] div.stButton > button[kind="primary"]::after {
  opacity: 1 !important;
}

section[data-testid="stSidebar"] div.stButton > button p {
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 12px !important;
  font-weight: 850 !important;
}

section[data-testid="stSidebar"] div.stButton > button[kind="primary"] p {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
}

section[data-testid="stSidebar"] .app-notice-menu {
  margin: 8px 0 10px !important;
}

section[data-testid="stSidebar"] .app-notice-menu summary {
  min-height: 36px !important;
  padding: 8px 10px !important;
  border: 1px solid var(--p2-border) !important;
  border-radius: 11px !important;
  background:
    linear-gradient(90deg, rgba(244,200,74,0.1), transparent 52%),
    rgba(255,255,255,0.025) !important;
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] .app-notice-menu summary span:first-child::before {
  content: "" !important;
  display: inline-block !important;
  width: 7px !important;
  height: 7px !important;
  margin-right: 7px !important;
  border-radius: 50% !important;
  background: var(--p2-gold) !important;
  box-shadow: 0 0 10px rgba(244,200,74,0.45) !important;
  vertical-align: 1px !important;
}

section[data-testid="stSidebar"] .app-notice-menu summary * {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 12px !important;
  font-weight: 850 !important;
}

section[data-testid="stSidebar"] .app-notice-menu-panel {
  margin-top: 7px !important;
  padding: 7px !important;
  border: 1px solid var(--p2-border) !important;
  border-radius: var(--p2-radius) !important;
  background: rgba(9, 13, 23, 0.86) !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] .app-notice {
  margin-bottom: 6px !important;
  padding: 8px 9px !important;
  border: 1px solid var(--p2-border) !important;
  border-left: 3px solid var(--p2-primary) !important;
  border-radius: 10px !important;
  background: rgba(255,255,255,0.028) !important;
  box-shadow: none !important;
}

section[data-testid="stSidebar"] .app-notice-title {
  font-size: 11px !important;
}

section[data-testid="stSidebar"] .app-notice-body,
section[data-testid="stSidebar"] .app-notice-time {
  font-size: 11px !important;
}

section[data-testid="stSidebar"] hr {
  margin: 12px 0 !important;
  border-color: var(--p2-border) !important;
}

/* Topbar */
.main .poke-topbar {
  position: sticky !important;
  top: 8px !important;
  z-index: 20 !important;
  min-height: 50px !important;
  margin: 0 0 18px !important;
  padding: 9px 12px !important;
  border: 1px solid var(--p2-border) !important;
  border-radius: var(--p2-radius) !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.015)),
    var(--p2-surface-glass) !important;
  backdrop-filter: blur(14px) !important;
  box-shadow: var(--p2-shadow-sm) !important;
}

.main .poke-topbar-left,
.main .poke-topbar-right {
  gap: 9px !important;
}

.main .poke-topbar-left span,
.main .poke-topbar-user,
.main .poke-topbar-pill {
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 12px !important;
  font-weight: 850 !important;
}

.main .poke-topbar-round {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
}

.main .poke-topbar-pill,
.main .poke-topbar-user {
  min-height: 30px !important;
  border: 1px solid var(--p2-border) !important;
  border-radius: 999px !important;
  background: rgba(255,255,255,0.035) !important;
  box-shadow: none !important;
}

.main .poke-topbar-user span {
  background: linear-gradient(180deg, var(--p2-primary), var(--p2-primary-2)) !important;
  color: #fff !important;
  -webkit-text-fill-color: #fff !important;
}

.main .poke-topbar-bell {
  width: 15px !important;
  height: 15px !important;
  background: none !important;
}

.main .poke-topbar-bell::before {
  width: 12px !important;
  height: 12px !important;
  border: 2px solid var(--p2-gold) !important;
  border-bottom: 0 !important;
  border-radius: 8px 8px 4px 4px !important;
  background: transparent !important;
}

.main .poke-topbar-bell::after {
  width: 5px !important;
  height: 5px !important;
  background: var(--p2-gold) !important;
}

/* Card hierarchy and page headers */
.main .home-hero,
.main .league-hero,
.main .matchup-hero,
.main .trainers-hero,
.main .mart-hero,
.main .hof-hero,
.main .auth-hero,
.main .season-hero,
.main .judgement-hero,
.main .normativa-hero {
  min-height: 0 !important;
  padding: 18px !important;
  border: 1px solid var(--p2-border) !important;
  border-radius: var(--p2-radius-lg) !important;
  clip-path: none !important;
  background:
    linear-gradient(125deg, rgba(93,162,255,0.11) 0 32%, transparent 32% 100%),
    linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015)),
    var(--p2-surface) !important;
  box-shadow: var(--p2-shadow-sm) !important;
}

.main .league-hero,
.main .matchup-hero,
.main .mart-hero {
  padding: 18px 20px !important;
}

.main .home-hero::before,
.main .home-hero::after,
.main .league-hero::before,
.main .league-hero::after,
.main .matchup-hero::before,
.main .matchup-hero::after,
.main .mart-hero::before,
.main .mart-hero::after,
.main .trainers-hero::before,
.main .trainers-hero::after,
.main .hof-hero::before,
.main .hof-hero::after,
.main .auth-hero::before,
.main .auth-hero::after {
  opacity: 0.12 !important;
}

.main .home-kicker,
.main .league-kicker,
.main .matchup-kicker,
.main .mart-kicker,
.main .auth-kicker,
.main .trainers-kicker,
.main .hof-kicker {
  display: inline-flex !important;
  min-height: 24px !important;
  align-items: center !important;
  padding: 0 9px !important;
  border: 1px solid var(--p2-border) !important;
  border-left: 3px solid var(--accent, var(--p2-primary)) !important;
  border-radius: 999px !important;
  background: rgba(255,255,255,0.035) !important;
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 10px !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
}

.main .home-title,
.main .league-title,
.main .matchup-title,
.main .mart-title,
.main .auth-title,
.main .trainers-title,
.main .hof-title {
  margin-top: 8px !important;
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: clamp(24px, 2.4vw, 38px) !important;
  line-height: 1.05 !important;
  text-transform: none !important;
  text-shadow: none !important;
}

.main .home-subtitle,
.main .league-subtitle,
.main .matchup-subtitle,
.main .mart-note,
.main .trainers-subtitle,
.main .hof-subtitle {
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 13px !important;
  line-height: 1.35 !important;
}

.main .home-card,
.main .home-context-card,
.main .league-card,
.main .league-status-card,
.main .league-division-card,
.main .league-history-card,
.main .league-section,
.main .league-table-shell,
.main .trainers-picker,
.main .trainers-stat,
.main .trainers-lock-panel,
.main .trainer-panel,
.main .matchup-summary,
.main .matchup-metric,
.main .matchup-mode-card,
.main .battle-board,
.main .battle-card,
.main .battle-mon-card,
.main .battle-empty-card,
.main .shop-card,
.main .mart-register-card,
.main .mart-alert,
.main .mart-aisle-head,
.main .mart-confirm-card,
.main .champ-detail-card,
.main .champ-box-grid-shell {
  border: 1px solid var(--p2-border) !important;
  border-radius: var(--p2-radius) !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.012)),
    var(--p2-surface) !important;
  box-shadow: none !important;
  clip-path: none !important;
}

.main .home-card,
.main .home-context-card,
.main .league-status-card,
.main .matchup-metric,
.main .trainers-stat,
.main .mart-register-card {
  min-height: 0 !important;
  padding: 12px 14px !important;
  border-radius: var(--p2-radius-sm) !important;
}

.main .home-card-label,
.main .league-status-card span,
.main .trainers-stat-label,
.main .mart-label,
.main .matchup-metric span,
.main .shop-sku {
  color: var(--p2-muted) !important;
  -webkit-text-fill-color: var(--p2-muted) !important;
  font-size: 10px !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
}

.main .home-card-value,
.main .league-status-card strong,
.main .trainers-stat-value,
.main .mart-value,
.main .matchup-metric strong {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 18px !important;
  font-weight: 900 !important;
  font-variant-numeric: tabular-nums !important;
}

.main .home-card-detail,
.main .trainers-stat-detail,
.main .mart-note,
.main .mart-aisle-note {
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 12px !important;
  line-height: 1.35 !important;
}

.main .home-section-title,
.main .league-section-title,
.main .trainers-section-title,
.main .mart-aisle-title,
.main .hof-section-title {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  margin: 26px 0 12px !important;
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 17px !important;
  font-weight: 950 !important;
  text-transform: none !important;
}

.main .home-section-title::after,
.main .league-section-title::after,
.main .trainers-section-title::after,
.main .mart-aisle-title::after,
.main .hof-section-title::after {
  content: "" !important;
  height: 1px !important;
  flex: 1 1 auto !important;
  background: linear-gradient(90deg, rgba(93,162,255,0.4), transparent) !important;
}

.main .home-card,
.main .league-card,
.main .league-division-card,
.main .league-history-card,
.main .trainer-panel,
.main .shop-card,
.main .matchup-mon,
.main .battle-mon-card,
.main .slot,
.main .champ-box-tile {
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease !important;
}

.main .home-card:hover,
.main .league-card:hover,
.main .league-division-card:hover,
.main .league-history-card:hover,
.main .shop-card:hover,
.main .matchup-mon:hover,
.main .battle-mon-card:hover,
.main .slot:hover,
.main .champ-box-tile-link:hover .champ-box-tile {
  transform: translateY(-2px) !important;
  border-color: rgba(93, 162, 255, 0.28) !important;
}

/* Pokemon cards and box grid */
.main .slot,
.main .slot-empty {
  position: relative !important;
  overflow: hidden !important;
  min-height: 214px !important;
  padding: 10px 10px 12px !important;
  border: 1px solid var(--p2-border-2) !important;
  border-radius: var(--p2-radius) !important;
  background:
    radial-gradient(circle at 50% 38%, rgba(93,162,255,0.13), transparent 52%),
    linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.012)),
    var(--p2-surface-2) !important;
  box-shadow: none !important;
  text-align: center !important;
}

.main .slot::after {
  content: "" !important;
  position: absolute !important;
  left: 50% !important;
  top: 88px !important;
  width: 76px !important;
  height: 16px !important;
  transform: translateX(-50%) !important;
  border-radius: 50% !important;
  background: rgba(0,0,0,0.24) !important;
  filter: blur(5px) !important;
  pointer-events: none !important;
  z-index: 0 !important;
}

.main .slot > * {
  position: relative !important;
  z-index: 1 !important;
}

.main .slot .badges {
  height: 26px !important;
  margin-bottom: 8px !important;
}

.main .slot-sep {
  display: none !important;
}

.main .slot .pill {
  min-height: 20px !important;
  padding: 3px 7px !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  border-radius: 6px !important;
  background: rgba(93,162,255,0.18) !important;
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 10px !important;
  font-weight: 900 !important;
}

.main .slot img {
  width: min(100%, 132px) !important;
  height: 110px !important;
  margin: 0 auto 8px !important;
  object-fit: contain !important;
  image-rendering: pixelated !important;
  filter: drop-shadow(0 9px 11px rgba(0,0,0,0.36)) !important;
}

.main .slot .title {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 11px !important;
  font-weight: 950 !important;
  text-transform: uppercase !important;
}

.main .slot .sub {
  margin-top: 2px !important;
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 15px !important;
}

.main .slot .types {
  margin-top: 8px !important;
  gap: 6px !important;
}

.main .poke-type-chip,
section[data-testid="stSidebar"] .poke-type-chip {
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  overflow: hidden !important;
  background: transparent !important;
  border: 0 !important;
  box-shadow: none !important;
}

.main .poke-type-chip.asset-icon,
section[data-testid="stSidebar"] .poke-type-chip.asset-icon {
  width: 24px !important;
  min-width: 24px !important;
  height: 24px !important;
  border-radius: 7px !important;
  background: rgba(255,255,255,0.06) !important;
}

.main .poke-type-icon-img,
section[data-testid="stSidebar"] .poke-type-icon-img {
  width: 24px !important;
  height: 24px !important;
  object-fit: contain !important;
}

.main .poke-type-chip.asset-full,
section[data-testid="stSidebar"] .poke-type-chip.asset-full {
  width: 92px !important;
  min-width: 92px !important;
  height: 24px !important;
  min-height: 24px !important;
  border-radius: 7px !important;
  background: transparent !important;
}

.main .poke-type-full-img,
section[data-testid="stSidebar"] .poke-type-full-img {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain !important;
}

.main .poke-type-chip.uses-fallback {
  min-height: 24px !important;
  padding: 0 8px !important;
  border: 1px solid color-mix(in srgb, var(--type-color) 46%, transparent) !important;
  border-radius: 7px !important;
  background: color-mix(in srgb, var(--type-color) 22%, transparent) !important;
}

.main .poke-type-fallback {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 9px !important;
  font-weight: 900 !important;
}

.main .champ-box-grid-shell {
  margin-top: 14px !important;
  padding: 14px !important;
  border-radius: var(--p2-radius-lg) !important;
}

.main .champ-box-grid-toolbar {
  margin-bottom: 12px !important;
}

.main .champ-box-grid-toolbar strong {
  min-height: 32px !important;
  border-color: var(--p2-border) !important;
  border-radius: 999px !important;
  background: rgba(255,255,255,0.035) !important;
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 12px !important;
  font-weight: 850 !important;
}

.main .champ-box-grid {
  grid-template-columns: repeat(6, minmax(74px, 1fr)) !important;
  gap: 9px !important;
}

.main .champ-box-tile {
  min-height: 76px !important;
  border-radius: 13px !important;
  border-color: var(--p2-border) !important;
  background:
    radial-gradient(circle at 50% 44%, rgba(93,162,255,0.12), transparent 58%),
    linear-gradient(135deg, rgba(255,255,255,0.055) 0 45%, rgba(255,255,255,0.02) 45% 100%),
    var(--p2-surface-2) !important;
}

.main .champ-box-tile::before {
  display: block !important;
  content: "" !important;
  position: absolute !important;
  inset: 5px !important;
  border: 1px solid rgba(255,255,255,0.035) !important;
  border-radius: 10px !important;
  background: linear-gradient(135deg, transparent 0 62%, rgba(255,255,255,0.045) 62% 100%) !important;
}

.main .champ-box-tile::after {
  display: none !important;
}

.main .champ-box-tile img {
  width: 84% !important;
  height: 84% !important;
  max-width: 76px !important;
  max-height: 76px !important;
  object-fit: contain !important;
  image-rendering: pixelated !important;
  filter: drop-shadow(0 7px 8px rgba(0,0,0,0.34)) !important;
}

.main .champ-box-tile-empty {
  opacity: 0.36 !important;
  border-style: dashed !important;
}

/* Pokemon detail */
.main .champ-detail-layout {
  grid-template-columns: minmax(240px, 0.92fr) minmax(280px, 1fr) minmax(280px, 1.02fr) !important;
  gap: 14px !important;
}

.main .champ-detail-card {
  padding: 10px !important;
  border-radius: var(--p2-radius-lg) !important;
}

.main .champ-detail-header,
.main .champ-detail-item-label {
  border: 1px solid rgba(93,162,255,0.26) !important;
  border-radius: 11px !important;
  background: linear-gradient(180deg, rgba(93,162,255,0.24), rgba(93,162,255,0.11)) !important;
  clip-path: none !important;
}

.main .champ-detail-level,
.main .champ-detail-item-value,
.main .champ-detail-stat-value,
.main .champ-detail-private-value,
.main .champ-detail-move-pp {
  border-radius: 8px !important;
  background: rgba(255,255,255,0.04) !important;
  border-color: var(--p2-border) !important;
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-variant-numeric: tabular-nums !important;
}

.main .champ-detail-sprite-stage {
  min-height: 184px !important;
  border-radius: var(--p2-radius) !important;
  border-color: var(--p2-border) !important;
  background:
    radial-gradient(ellipse at 50% 60%, rgba(0,0,0,0.26), transparent 28%),
    radial-gradient(circle at 50% 42%, rgba(93,162,255,0.15), transparent 60%),
    var(--p2-surface-2) !important;
}

.main .champ-detail-sprite-stage img {
  width: 156px !important;
}

.main .champ-detail-screen,
.main .champ-detail-move-screen {
  border-color: var(--p2-border) !important;
  border-radius: var(--p2-radius) !important;
  background: rgba(255,255,255,0.025) !important;
}

.main .champ-detail-ps-row,
.main .champ-detail-stat-row,
.main .champ-detail-private-row,
.main .champ-detail-ability-desc {
  border-bottom: 1px solid var(--p2-border) !important;
  background: rgba(255,255,255,0.025) !important;
}

.main .champ-detail-bar {
  height: 5px !important;
  border: 0 !important;
  border-radius: 999px !important;
  background: rgba(255,255,255,0.12) !important;
}

.main .champ-detail-bar > div {
  border-radius: 999px !important;
  background: linear-gradient(90deg, var(--p2-green), #9be56a) !important;
}

.main .champ-detail-move-row {
  min-height: 42px !important;
  border-bottom: 1px solid var(--p2-border) !important;
  border-radius: 0 !important;
  background: rgba(255,255,255,0.025) !important;
}

.main .champ-detail-move-name {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 14px !important;
  font-weight: 850 !important;
}

.main .champ-detail-type-chip.poke-type-chip.asset-full {
  width: 104px !important;
  min-width: 104px !important;
  height: 25px !important;
  min-height: 25px !important;
}

/* Team preview */
.main .matchup-shell {
  display: inline-flex !important;
  min-height: 28px !important;
  align-items: center !important;
  padding: 0 10px !important;
  border-radius: 999px !important;
  border: 1px solid rgba(93,162,255,0.28) !important;
  background: rgba(93,162,255,0.1) !important;
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  clip-path: none !important;
}

.main .matchup-mode-grid {
  gap: 10px !important;
  margin-bottom: 14px !important;
}

.main .matchup-mode-card {
  min-height: 74px !important;
  padding: 12px 14px !important;
  border-left: 3px solid transparent !important;
}

.main .matchup-mode-card.is-active {
  border-color: rgba(93,162,255,0.34) !important;
  border-left-color: var(--p2-primary) !important;
  background:
    linear-gradient(90deg, rgba(93,162,255,0.16), rgba(93,162,255,0.035)),
    var(--p2-surface) !important;
}

.main .battle-board {
  position: relative !important;
  overflow: hidden !important;
  padding: 14px !important;
  border-radius: var(--p2-radius-lg) !important;
  background:
    radial-gradient(circle at 0 12%, rgba(93,162,255,0.08), transparent 30%),
    radial-gradient(circle at 100% 18%, rgba(255,97,114,0.055), transparent 32%),
    var(--p2-surface) !important;
}

.main .battle-board::before {
  content: "VS" !important;
  position: absolute !important;
  left: 50% !important;
  top: 50% !important;
  transform: translate(-50%, -50%) !important;
  color: rgba(255,255,255,0.035) !important;
  font-family: var(--font-pixel) !important;
  font-size: clamp(72px, 9vw, 150px) !important;
  font-weight: 950 !important;
  pointer-events: none !important;
}

.main .battle-board-top {
  position: relative !important;
  z-index: 1 !important;
  gap: 10px !important;
  margin-bottom: 12px !important;
}

.main .battle-board-top > div {
  min-height: 48px !important;
  padding: 9px 12px !important;
  border: 1px solid var(--p2-border) !important;
  border-radius: var(--p2-radius-sm) !important;
  background: rgba(255,255,255,0.03) !important;
  box-shadow: none !important;
}

.main .battle-team-grid,
.main .matchup-team-grid {
  position: relative !important;
  z-index: 1 !important;
  gap: 10px !important;
}

.main .battle-mon-card {
  position: relative !important;
  overflow: hidden !important;
  min-height: 206px !important;
  padding: 12px !important;
  grid-template-columns: minmax(190px, 0.9fr) 132px minmax(250px, 1.1fr) !important;
  align-items: center !important;
  border-radius: var(--p2-radius) !important;
  background:
    radial-gradient(circle at 46% 50%, rgba(93,162,255,0.12), transparent 34%),
    linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.012)),
    var(--p2-surface-2) !important;
}

.main .battle-mon-card-public {
  grid-template-columns: minmax(180px, 0.82fr) 128px minmax(240px, 1.12fr) !important;
}

.main .battle-slot-mark,
.main .matchup-mon::after {
  color: rgba(255,255,255,0.055) !important;
  -webkit-text-fill-color: rgba(255,255,255,0.055) !important;
  font-size: 62px !important;
  font-weight: 950 !important;
  line-height: 1 !important;
}

.main .battle-card-left,
.main .battle-private-info,
.main .battle-private-line,
.main .battle-ivs,
.main .battle-stat-stack,
.main .battle-ability-row {
  border: 1px solid var(--p2-border) !important;
  border-radius: var(--p2-radius-sm) !important;
  background: rgba(255,255,255,0.03) !important;
  box-shadow: none !important;
}

.main .battle-card-left {
  padding: 10px !important;
}

.main .battle-mon-name,
.main .matchup-mon-title {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 14px !important;
  font-weight: 950 !important;
  text-transform: none !important;
}

.main .battle-species,
.main .battle-level,
.main .battle-item,
.main .battle-ability-desc,
.main .matchup-mon-sub,
.main .matchup-mon-extra {
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 12px !important;
}

.main .battle-sprite-wrap {
  position: relative !important;
  width: 126px !important;
  height: 132px !important;
  border: 1px solid var(--p2-border) !important;
  border-radius: var(--p2-radius) !important;
  background:
    radial-gradient(ellipse at 50% 72%, rgba(0,0,0,0.28), transparent 28%),
    radial-gradient(circle at 50% 46%, rgba(255,255,255,0.12), transparent 58%),
    rgba(255,255,255,0.045) !important;
  box-shadow: none !important;
}

.main .battle-sprite {
  width: 128px !important;
  height: 128px !important;
  object-fit: contain !important;
  image-rendering: pixelated !important;
}

.main .battle-moves,
.main .matchup-move-list {
  gap: 7px !important;
}

.main .battle-move-link,
.main .battle-no-move,
.main .matchup-move {
  min-height: 38px !important;
  padding: 7px 9px !important;
  border: 1px solid var(--p2-border) !important;
  border-radius: 11px !important;
  background: rgba(255,255,255,0.035) !important;
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  box-shadow: none !important;
  transition: background 150ms ease, border-color 150ms ease, transform 150ms ease !important;
}

.main .battle-move-link:hover,
.main .battle-move-row[open] > .battle-move-link {
  transform: translateX(2px) !important;
  border-color: rgba(93,162,255,0.32) !important;
  background: rgba(93,162,255,0.095) !important;
}

.main .battle-move-link span:last-child,
.main .matchup-move span:last-child {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 13px !important;
  font-weight: 850 !important;
}

.main .battle-type-dot.poke-type-chip.asset-icon,
.main .matchup-move .battle-type-dot.poke-type-chip.asset-icon {
  width: 24px !important;
  min-width: 24px !important;
  height: 24px !important;
  border-radius: 7px !important;
  background: rgba(255,255,255,0.06) !important;
}

.main .battle-type-dot:not(.poke-type-chip) {
  width: 24px !important;
  height: 24px !important;
  flex: 0 0 24px !important;
  border-radius: 7px !important;
  border: 1px solid rgba(255,255,255,0.18) !important;
  box-shadow: none !important;
  font-size: 8px !important;
}

.main .battle-stat-row {
  min-height: 28px !important;
  gap: 8px !important;
}

.main .battle-stat-bar {
  height: 4px !important;
  border: 0 !important;
  border-radius: 999px !important;
  background: rgba(255,255,255,0.12) !important;
}

.main .battle-stat-bar > span {
  border-radius: 999px !important;
  background: linear-gradient(90deg, var(--p2-primary), var(--p2-cyan)) !important;
}

.main .battle-stat-row strong,
.main .battle-iv strong {
  font-variant-numeric: tabular-nums !important;
}

.main .battle-move-detail,
.main .battle-move-detail-inline {
  margin-top: 8px !important;
  padding: 12px !important;
  border: 1px solid var(--p2-border) !important;
  border-radius: var(--p2-radius) !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.012)),
    #0d1422 !important;
  box-shadow: none !important;
}

.main .battle-detail-kicker {
  color: var(--p2-muted) !important;
  -webkit-text-fill-color: var(--p2-muted) !important;
  font-size: 10px !important;
  font-weight: 900 !important;
  text-transform: uppercase !important;
}

.main .battle-detail-head strong {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 15px !important;
}

.main .battle-detail-head span {
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 12px !important;
}

.main .battle-detail-stats {
  gap: 8px !important;
}

.main .battle-detail-stats div,
.main .battle-detail-stat {
  min-height: 62px !important;
  padding: 9px !important;
  border: 1px solid var(--p2-border) !important;
  border-radius: 11px !important;
  background: rgba(255,255,255,0.03) !important;
  box-shadow: none !important;
}

.main .battle-detail-stats div span {
  color: var(--p2-muted) !important;
  -webkit-text-fill-color: var(--p2-muted) !important;
  font-size: 10px !important;
  font-weight: 900 !important;
}

.main .battle-detail-stats div strong {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 16px !important;
  font-weight: 850 !important;
}

.main .battle-detail-stat-type {
  background: transparent !important;
  border-color: transparent !important;
  padding: 6px 0 !important;
}

.main .battle-detail-stat-type > span {
  padding-left: 2px !important;
}

.main .battle-detail-stat-type > strong {
  margin-top: 5px !important;
  display: block !important;
}

.main .battle-type-pill.poke-type-chip.asset-full {
  width: 132px !important;
  min-width: 132px !important;
  height: 31px !important;
  min-height: 31px !important;
  border: 0 !important;
  background: transparent !important;
}

.main .battle-category-value {
  display: inline-flex !important;
  align-items: center !important;
  gap: 8px !important;
}

.main .battle-category-icon {
  width: 34px !important;
  height: 24px !important;
  border-radius: 4px !important;
  border-color: rgba(255,255,255,0.22) !important;
}

.main .battle-detail-desc {
  margin-top: 10px !important;
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 14px !important;
  line-height: 1.45 !important;
}

.main .matchup-mon {
  position: relative !important;
  min-height: 188px !important;
  padding: 12px !important;
  border-radius: var(--p2-radius) !important;
  background:
    radial-gradient(circle at 18% 20%, rgba(93,162,255,0.12), transparent 40%),
    var(--p2-surface-2) !important;
}

.main .matchup-mon-head {
  grid-template-columns: 98px minmax(0, 1fr) !important;
}

.main .matchup-sprite {
  width: 96px !important;
  height: 96px !important;
  border: 0 !important;
  border-radius: 0 !important;
  background: transparent !important;
  filter: drop-shadow(0 8px 9px rgba(0,0,0,0.32)) !important;
}

.main .matchup-mon-empty,
.main .battle-empty-card {
  min-height: 138px !important;
  border-style: dashed !important;
  opacity: 0.7 !important;
  background: rgba(255,255,255,0.018) !important;
}

/* Shop */
.main .mart-hero {
  grid-template-columns: minmax(0, 1fr) auto !important;
  min-height: 112px !important;
}

.main .mart-register-grid {
  gap: 10px !important;
  margin: 12px 0 !important;
}

.main .mart-aisle-head {
  margin: 16px 0 10px !important;
  padding: 12px 14px !important;
  border-left: 3px solid var(--accent, var(--p2-primary)) !important;
}

.main .shop-card {
  position: relative !important;
  overflow: hidden !important;
  min-height: 206px !important;
  margin-bottom: 9px !important;
  border-radius: var(--p2-radius) !important;
  background:
    linear-gradient(180deg, rgba(255,255,255,0.035), rgba(255,255,255,0.012)),
    var(--p2-surface) !important;
}

.main .shop-card::before {
  display: none !important;
}

.main .shop-card.is-sale {
  border-color: rgba(244, 200, 74, 0.36) !important;
  box-shadow: inset 3px 0 0 var(--p2-gold) !important;
}

.main .shop-card.is-pending-sale {
  border-color: rgba(88, 214, 255, 0.34) !important;
  box-shadow: inset 3px 0 0 var(--p2-cyan) !important;
}

.main .shop-head {
  min-height: 40px !important;
  padding: 10px 12px !important;
  border-bottom: 1px solid var(--p2-border) !important;
  background: rgba(255,255,255,0.018) !important;
}

.main .shop-name {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 12px !important;
  font-weight: 950 !important;
}

.main .shop-body {
  grid-template-columns: 78px minmax(0, 1fr) !important;
  gap: 12px !important;
  padding: 12px !important;
}

.main .shop-icon-slot {
  width: 72px !important;
  height: 72px !important;
  border-radius: 12px !important;
  border-color: var(--p2-border) !important;
  background:
    radial-gradient(circle at 50% 44%, rgba(244,200,74,0.14), transparent 54%),
    rgba(255,255,255,0.035) !important;
}

.main .shop-icon {
  width: 56px !important;
  height: 56px !important;
  filter: drop-shadow(0 7px 8px rgba(0,0,0,0.36)) !important;
}

.main .shop-desc {
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 13px !important;
  line-height: 1.35 !important;
}

.main .shop-price {
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  flex-wrap: wrap !important;
  gap: 8px !important;
  padding: 8px 9px !important;
  border-radius: 10px !important;
  background: rgba(255,255,255,0.035) !important;
}

.main .shop-coin-value {
  min-height: 30px !important;
  min-width: 58px !important;
  padding: 4px 8px !important;
  border-radius: 9px !important;
  background: rgba(244,200,74,0.095) !important;
}

.main .shop-coin {
  font-size: 20px !important;
  line-height: 1 !important;
}

.main .shop-amount {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 18px !important;
  font-weight: 950 !important;
  font-variant-numeric: tabular-nums !important;
}

.main .shop-stock,
.main .shop-missing {
  font-size: 12px !important;
  line-height: 1.3 !important;
}

.main .shop-missing {
  border-radius: 9px !important;
  background: rgba(255, 97, 114, 0.09) !important;
  color: #ffb3bd !important;
  -webkit-text-fill-color: #ffb3bd !important;
}

.main .shop-discount-badge {
  min-height: 26px !important;
  border-radius: 999px !important;
  background: linear-gradient(180deg, rgba(244,200,74,0.3), rgba(244,200,74,0.12)) !important;
  border-color: rgba(244,200,74,0.42) !important;
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 11px !important;
}

/* League and tables */
.main .league-table-shell,
.main .league-status-table {
  border-radius: var(--p2-radius) !important;
  border-color: var(--p2-border) !important;
  background: var(--p2-surface) !important;
  box-shadow: none !important;
}

.main .league-status-table {
  font-size: 14px !important;
}

.main .league-status-table th {
  height: 38px !important;
  padding: 0 12px !important;
  border-color: var(--p2-border) !important;
  background: rgba(255,255,255,0.035) !important;
  color: var(--p2-muted) !important;
  -webkit-text-fill-color: var(--p2-muted) !important;
  font-size: 11px !important;
  font-weight: 900 !important;
}

.main .league-status-table td {
  height: 40px !important;
  border-color: rgba(228, 238, 255, 0.055) !important;
  background: rgba(255,255,255,0.012) !important;
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-variant-numeric: tabular-nums !important;
}

.main .league-status-table tr:hover td {
  background: rgba(93,162,255,0.055) !important;
}

.main .league-status-table tr:nth-child(even) td {
  background: rgba(255,255,255,0.02) !important;
}

.main .league-table-pos {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-weight: 950 !important;
}

.main .league-player-name {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 13px !important;
  font-weight: 900 !important;
}

.main .league-table-coins {
  color: var(--p2-gold) !important;
  -webkit-text-fill-color: var(--p2-gold) !important;
  font-size: 16px !important;
}

.main .league-trainer-badge {
  min-height: 20px !important;
  padding: 2px 8px !important;
  border-radius: 999px !important;
  box-shadow: none !important;
  font-size: 10px !important;
}

.main .league-trainer-badge--robado {
  border-color: rgba(255,97,114,0.38) !important;
  background: rgba(255,97,114,0.12) !important;
  color: #ffd2d8 !important;
  -webkit-text-fill-color: #ffd2d8 !important;
}

.main .league-trainer-badge--retirado {
  border-color: rgba(179,189,205,0.24) !important;
  background: rgba(179,189,205,0.1) !important;
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
}

.main table,
.main div[data-testid="stDataFrame"] {
  font-variant-numeric: tabular-nums !important;
}

/* Trainers and admin-ish pages */
.main .trainers-picker {
  padding: 12px 14px !important;
  margin-bottom: 14px !important;
}

.main .trainers-panel-label,
.main .trainers-panel-copy {
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 12px !important;
}

.main .trainers-hero-grid {
  gap: 14px !important;
}

.main .trainers-portrait-xl,
.main .trainer-portrait,
.main .auth-avatar {
  border-radius: var(--p2-radius) !important;
  border-color: var(--p2-border) !important;
  background:
    radial-gradient(ellipse at 50% 74%, rgba(0,0,0,0.26), transparent 30%),
    radial-gradient(circle at 50% 42%, rgba(93,162,255,0.13), transparent 58%),
    var(--p2-surface-2) !important;
  box-shadow: none !important;
}

.main .trainers-portrait-xl img,
.main .trainer-portrait img {
  filter: drop-shadow(0 8px 9px rgba(0,0,0,0.32)) !important;
}

.main .trainer-head {
  border: 0 !important;
  border-bottom: 1px solid var(--p2-border) !important;
  border-radius: 0 !important;
  background: transparent !important;
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  clip-path: none !important;
}

.main .trainer-grid {
  gap: 12px !important;
}

.main .trainer-kia,
.main .trainer-note {
  border-radius: var(--p2-radius-sm) !important;
  background: rgba(255,255,255,0.03) !important;
  border-color: var(--p2-border) !important;
}

/* Login */
.main .auth-hero {
  margin: 0 auto 14px !important;
  padding: 12px 0 !important;
  max-width: 520px !important;
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.main .auth-hero::before {
  opacity: 0.08 !important;
}

.main .auth-kicker {
  border: 0 !important;
  background: transparent !important;
  color: var(--p2-primary) !important;
  -webkit-text-fill-color: var(--p2-primary) !important;
}

.main .auth-title {
  max-width: 500px !important;
  font-size: clamp(26px, 4vw, 34px) !important;
}

.main .auth-trainer-card {
  max-width: 520px !important;
  margin-left: auto !important;
  margin-right: auto !important;
}

.main .auth-trainer-card {
  padding: 14px !important;
  grid-template-columns: 86px minmax(0, 1fr) !important;
  border-radius: var(--p2-radius-lg) !important;
  background:
    linear-gradient(135deg, rgba(93,162,255,0.12), transparent 52%),
    var(--p2-surface) !important;
}

.main .auth-avatar {
  width: 86px !important;
  height: 86px !important;
}

.main .auth-trainer-name {
  color: var(--p2-text) !important;
  -webkit-text-fill-color: var(--p2-text) !important;
  font-size: 18px !important;
}

.main .auth-trainer-role {
  color: var(--p2-text-2) !important;
  -webkit-text-fill-color: var(--p2-text-2) !important;
  font-size: 13px !important;
}

/* Normativa, Hall of Fame and judgement polish */
.main .hof-hero,
.main .hof-card {
  border-color: rgba(244, 200, 74, 0.18) !important;
  background:
    radial-gradient(circle at 50% -12%, rgba(244,200,74,0.12), transparent 38%),
    var(--p2-surface) !important;
}

.main .hof-title,
.main .hof-section-title {
  color: #ffe28a !important;
  -webkit-text-fill-color: #ffe28a !important;
}

.main .stAlert {
  border-radius: var(--p2-radius) !important;
}

.main div[data-testid="stMarkdownContainer"] code,
.main code,
.main pre {
  font-family: "JetBrains Mono", "Cascadia Mono", "Consolas", monospace !important;
  font-variant-numeric: tabular-nums !important;
}

/* Responsive */
@media (min-width: 1600px) {
  .main .block-container {
    max-width: 1540px !important;
  }
}

@media (max-width: 1180px) {
  .main .battle-team-grid,
  .main .matchup-team-grid {
    grid-template-columns: 1fr !important;
  }

  .main .battle-mon-card,
  .main .battle-mon-card-public {
    grid-template-columns: minmax(0, 1fr) 120px !important;
  }

  .main .battle-moves {
    grid-column: 1 / -1 !important;
  }

  .main .champ-detail-layout {
    grid-template-columns: 1fr !important;
  }
}

@media (max-width: 980px) {
  section[data-testid="stSidebar"] {
    width: 232px !important;
    min-width: 232px !important;
    max-width: 232px !important;
  }

  .main .block-container {
    padding-top: 3.25rem !important;
    padding-left: 16px !important;
    padding-right: 16px !important;
  }

  .main .poke-topbar {
    position: relative !important;
    top: auto !important;
    align-items: flex-start !important;
    flex-direction: column !important;
  }

  .main .poke-topbar-right {
    justify-content: flex-start !important;
    flex-wrap: wrap !important;
    width: 100% !important;
  }

  .main .home-hero,
  .main .league-hero,
  .main .matchup-hero,
  .main .mart-hero {
    grid-template-columns: 1fr !important;
  }

  .main .champ-box-grid {
    grid-template-columns: repeat(4, minmax(58px, 1fr)) !important;
  }
}

@media (max-width: 620px) {
  .main .home-grid,
  .main .home-context-grid,
  .main .league-division-grid,
  .main .league-history-grid,
  .main .mart-register-grid,
  .main .matchup-mode-grid {
    grid-template-columns: 1fr !important;
  }

  .main .battle-mon-card,
  .main .battle-mon-card-public {
    grid-template-columns: 1fr !important;
  }

  .main .battle-sprite-wrap {
    width: 100% !important;
  }

  .main .champ-box-grid {
    grid-template-columns: repeat(3, minmax(54px, 1fr)) !important;
  }

  .main .slot {
    min-height: 198px !important;
  }
}
</style>
"""


def apply_phase2_skin(container: Any = None) -> None:
    target = container or st
    target.markdown(PHASE2_CSS, unsafe_allow_html=True)
