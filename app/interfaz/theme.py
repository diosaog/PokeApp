from __future__ import annotations

import streamlit as st

from app.interfaz.champions_skin import apply_champions_skin
from app.interfaz.final_polish import apply_final_polish


def apply_css() -> None:
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@400;600;700;800&family=Oxanium:wght@600;700;800&display=swap');

    :root {
      --font-ui: "Nunito Sans", "Inter", system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --font-pixel: "Oxanium", "Trebuchet MS", system-ui, sans-serif;
      --accent: #2f80ed;
      --accent-dark: #1452bf;
      --accent-soft: #8fd0ff;
      --accent-ghost: rgba(47, 128, 237, 0.18);
      --champion-red: #ef3f56;
      --champion-yellow: #ffd447;
      --champion-cyan: #45c7ff;
      --champion-blue: #2f80ed;
      --champion-navy: #071936;
      --bw2-bg-0: #06142e;
      --bw2-bg-1: #0c2b5a;
      --bw2-bg-2: #123f7a;
      --bw2-panel: #102b50;
      --bw2-panel-2: #173d6e;
      --bw2-panel-3: #245f9d;
      --bw2-screen: #081f3f;
      --bw2-screen-2: #0e315f;
      --bw2-screen-line: #8fd0ff;
      --bw2-edge: rgba(170, 211, 255, 0.42);
      --bw2-edge-strong: rgba(247, 251, 255, 0.9);
      --bw2-text: #f8fbff;
      --bw2-text-soft: #dcecff;
      --bw2-text-dim: #a9bedc;
      --bw2-ok: #2ed18a;
      --bw2-warn: #ef3f56;
      --bw2-gold: #ffd447;
      --bw2-shadow: rgba(3, 18, 43, 0.42);
      --divider: rgba(248, 251, 255, 0.18);
      --ball-color: #ef3f56;
      --poke-radius-sm: 6px;
      --poke-radius: 8px;
      --poke-radius-xl: 8px;
      --poke-shadow-soft: 0 14px 34px rgba(2, 18, 46, 0.24);
      --poke-shadow-card: 0 10px 24px rgba(2, 18, 46, 0.2);
      --poke-surface-glow: inset 0 1px 0 rgba(255,255,255,0.2);
      --section-label: "NORMATIVA";
    }

    html, body, [class*="css"] {
      font-family: var(--font-ui);
    }

    .stApp {
      background:
        linear-gradient(180deg, rgba(255,255,255,0.06) 0 1px, transparent 1px 100%) 0 44px / 100% 32px,
        linear-gradient(90deg, rgba(255,255,255,0.045) 0 1px, transparent 1px 100%) 0 44px / 32px 100%,
        linear-gradient(135deg, rgba(69,199,255,0.18) 0 18%, transparent 18% 54%, rgba(255,212,71,0.1) 54% 62%, transparent 62%),
        linear-gradient(180deg, #071936 0%, #0c2b5a 45%, #081936 100%);
      color: var(--bw2-text);
    }

    .stApp::before {
      content: "";
      position: fixed;
      inset: 0 0 auto 0;
      height: 52px;
      background:
        linear-gradient(90deg, var(--champion-red) 0 23%, #f8fbff 23% 27%, var(--champion-blue) 27% 100%),
        linear-gradient(180deg, rgba(255,255,255,0.2), transparent);
      border-bottom: 1px solid rgba(248,251,255,0.34);
      box-shadow: 0 1px 0 rgba(255,255,255,0.15), 0 12px 26px rgba(2,18,46,0.24);
      z-index: 1000;
      pointer-events: none;
    }

    .stApp::after {
      content: "POKEAPP LEAGUE CENTER";
      position: fixed;
      top: 14px;
      left: 50%;
      transform: translateX(-50%);
      color: #ffffff;
      font-family: var(--font-pixel);
      font-size: 12px;
      letter-spacing: 0;
      z-index: 1001;
      pointer-events: none;
      text-shadow: 0 2px 8px rgba(0,0,0,0.32);
    }

    .main { position: relative; }
    .main::before {
      content: "";
      position: fixed;
      inset: 0;
      z-index: -1;
      pointer-events: none;
      background:
        linear-gradient(120deg, transparent 0 12%, rgba(255,255,255,0.05) 12% 13%, transparent 13% 100%) 0 0 / 560px 300px,
        linear-gradient(240deg, transparent 0 18%, rgba(255,212,71,0.08) 18% 20%, transparent 20% 100%) 100% 100% / 620px 360px no-repeat,
        linear-gradient(180deg, rgba(255,255,255,0.04), transparent 42%),
        linear-gradient(180deg, var(--bw2-bg-0) 0%, var(--bw2-bg-1) 46%, #071936 100%);
    }

    .block-container {
      padding-top: 4.25rem;
      padding-bottom: 2.75rem;
      animation: fadeInUp .28s ease-out both;
    }

    @keyframes fadeInUp {
      from { opacity: 0; transform: translate3d(0, 10px, 0); }
      to { opacity: 1; transform: translate3d(0, 0, 0); }
    }

    h1, h2, h3, h4, h5, h6 {
      font-family: var(--font-pixel);
      color: var(--bw2-text);
      letter-spacing: 0;
      text-transform: uppercase;
      text-shadow: 0 2px 10px rgba(0,0,0,0.22);
    }

    p, span, div, label, li, caption {
      color: var(--bw2-text-soft);
    }

    strong, b {
      color: var(--bw2-text);
      font-weight: 700;
    }

    a {
      color: var(--accent-soft);
      text-decoration: none;
    }

    a:hover {
      color: #ffffff;
    }

    hr {
      border: none;
      height: 2px;
      margin: 1rem 0 1.2rem;
      background:
        linear-gradient(90deg, transparent 0%, rgba(216,223,232,0.15) 12%, rgba(216,223,232,0.15) 88%, transparent 100%),
        linear-gradient(90deg, transparent 0%, var(--accent) 18%, var(--accent) 82%, transparent 100%);
      background-size: 100% 2px, 100% 1px;
      background-repeat: no-repeat;
      background-position: center center;
    }

    section[data-testid="stSidebar"] {
      position: relative;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.08) 0 1px, transparent 1px 100%) 0 0 / 100% 28px,
        linear-gradient(135deg, rgba(69,199,255,0.12), transparent 42%),
        linear-gradient(180deg, #0b2a58 0%, #071936 100%);
      border-right: 1px solid rgba(248,251,255,0.18);
      box-shadow: inset -1px 0 0 rgba(255,255,255,0.08), 10px 0 26px rgba(2,18,46,0.24);
    }

    section[data-testid="stSidebar"] .block-container {
      padding-top: 4.25rem;
    }

    section[data-testid="stSidebar"]::before {
      content: var(--section-label);
      position: absolute;
      top: 10px;
      left: 18px;
      right: 18px;
      z-index: 2;
      padding: 9px 12px;
      color: #ffffff;
      background:
        linear-gradient(90deg, rgba(255,255,255,0.18), transparent 64%),
        linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
      border: 1px solid var(--bw2-edge-strong);
      border-radius: var(--poke-radius);
      box-shadow: var(--poke-surface-glow), var(--poke-shadow-card);
      font-family: var(--font-pixel);
      font-size: 11px;
      letter-spacing: 0;
      text-align: center;
    }

    .stButton > button,
    .stDownloadButton > button {
      min-height: 42px;
      padding: 0.65rem 1rem;
      border-radius: var(--poke-radius);
      border: 1px solid var(--bw2-edge-strong);
      background:
        linear-gradient(90deg, rgba(255,255,255,0.2), transparent 68%),
        linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
      color: #ffffff;
      font-family: var(--font-pixel);
      font-size: 11px;
      letter-spacing: 0;
      text-transform: uppercase;
      box-shadow: var(--poke-surface-glow), var(--poke-shadow-card);
      transition: transform .12s ease, filter .12s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
      transform: translateY(-1px);
      filter: brightness(1.06);
    }

    .stButton > button:focus-visible,
    .stDownloadButton > button:focus-visible {
      outline: 2px solid var(--accent-soft);
      outline-offset: 2px;
    }

    .stButton > button:disabled,
    .stDownloadButton > button:disabled {
      background: linear-gradient(180deg, #6d809c 0%, #42516b 100%);
      color: #cbd1d9;
      border-color: #aab2bd;
      box-shadow: none;
      filter: none;
    }

    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea,
    .stDateInput input,
    .stTimeInput input {
      background: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.06) 100%) !important;
      color: var(--bw2-text) !important;
      border: 1px solid var(--bw2-edge) !important;
      border-radius: var(--poke-radius) !important;
      box-shadow: var(--poke-surface-glow), 0 0 0 1px rgba(2,18,46,0.22) !important;
      font-family: var(--font-ui) !important;
      font-size: 1rem !important;
      letter-spacing: 0;
    }

    .stTextInput label,
    .stNumberInput label,
    .stTextArea label,
    .stSelectbox label,
    .stMultiSelect label,
    .stRadio label,
    .stCheckbox label,
    .stFileUploader label {
      color: var(--bw2-text) !important;
      font-family: var(--font-pixel) !important;
      font-size: 10px !important;
      letter-spacing: 0;
      text-transform: uppercase;
    }

    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {
      background: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.06) 100%) !important;
      border: 1px solid var(--bw2-edge) !important;
      border-radius: var(--poke-radius) !important;
      box-shadow: var(--poke-surface-glow), 0 0 0 1px rgba(2,18,46,0.22) !important;
      min-height: 44px;
      color: var(--bw2-text) !important;
      font-family: var(--font-ui) !important;
      font-size: 1rem !important;
    }

    div[data-baseweb="popover"] div[role="listbox"] {
      background: var(--bw2-panel-2) !important;
      border: 1px solid var(--bw2-edge) !important;
      color: var(--bw2-text) !important;
      font-family: var(--font-ui) !important;
      font-size: 1.1rem !important;
    }

    div[data-baseweb="tag"] {
      background: var(--accent-ghost) !important;
      color: var(--bw2-text) !important;
      border: 1px solid rgba(255,255,255,0.12) !important;
      border-radius: var(--poke-radius-sm) !important;
      font-family: var(--font-ui) !important;
      font-size: 0.95rem !important;
    }

    div[data-baseweb="tab-list"] {
      background: linear-gradient(180deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%) !important;
      border: 1px solid var(--bw2-edge) !important;
      border-radius: var(--poke-radius) !important;
      padding: 4px !important;
      gap: 4px !important;
      box-shadow: var(--poke-surface-glow), 0 0 0 1px rgba(2,18,46,0.2);
    }

    button[data-baseweb="tab"],
    button[role="tab"] {
      background: linear-gradient(180deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.04) 100%) !important;
      color: var(--bw2-text-soft) !important;
      border: 1px solid var(--bw2-edge) !important;
      border-radius: var(--poke-radius-sm) !important;
      font-family: var(--font-pixel) !important;
      font-size: 10px !important;
      letter-spacing: 0;
      text-transform: uppercase;
    }

    button[data-baseweb="tab"][aria-selected="true"],
    button[role="tab"][aria-selected="true"] {
      background:
        linear-gradient(90deg, rgba(255,255,255,0.2), transparent 68%),
        linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%) !important;
      color: #ffffff !important;
      border-color: var(--bw2-edge-strong) !important;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.22);
    }

    details[data-testid="stExpander"],
    div[data-testid="stVerticalBlockBorderWrapper"],
    div[data-testid="stMetric"],
    div[data-testid="stAlert"],
    div[data-baseweb="notification"],
    div[data-testid="stForm"] {
      background: linear-gradient(180deg, rgba(255,255,255,0.08) 0%, transparent 100%), linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%) !important;
      border: 1px solid var(--bw2-edge) !important;
      border-radius: var(--poke-radius) !important;
      box-shadow: var(--poke-surface-glow), var(--poke-shadow-card) !important;
      color: var(--bw2-text-soft) !important;
    }

    details[data-testid="stExpander"] > summary {
      background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(0,0,0,0.04) 100%);
      border-bottom: 1px solid rgba(255,255,255,0.08);
      color: var(--bw2-text) !important;
      font-family: var(--font-pixel) !important;
      font-size: 10px !important;
      letter-spacing: 0;
      text-transform: uppercase;
    }

    div[data-testid="stMetric"] label,
    div[data-testid="stMetric"] [data-testid="stMetricLabel"],
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
      color: var(--bw2-text) !important;
      font-family: var(--font-pixel) !important;
    }

    div[data-testid="stMetric"] [data-testid="stMetricLabel"] {
      font-size: 10px !important;
      text-transform: uppercase;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
      font-size: 1rem !important;
    }

    div[data-testid="stAlert"] * ,
    div[data-baseweb="notification"] * {
      color: var(--bw2-text) !important;
      font-family: var(--font-ui) !important;
    }

    div[data-testid="stFileUploaderDropzone"] {
      background: linear-gradient(180deg, rgba(255,255,255,0.1) 0%, rgba(255,255,255,0.05) 100%) !important;
      border: 1px dashed var(--bw2-edge) !important;
      border-radius: var(--poke-radius) !important;
    }

    div[data-testid="stFileUploaderDropzone"] * {
      color: var(--bw2-text-soft) !important;
      font-family: var(--font-ui) !important;
    }

    .stRadio [role="radiogroup"] {
      gap: 8px;
    }

    .stRadio [role="radiogroup"] label {
      background: linear-gradient(180deg, #1a1f27 0%, #11161c 100%);
      border: 1px solid var(--bw2-edge);
      border-radius: 0;
      padding: 8px 10px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.07);
    }

    .stCheckbox label {
      background: transparent !important;
      border: none !important;
      padding: 0 !important;
      box-shadow: none !important;
    }

    div[data-testid="stDataFrame"],
    div[data-testid="stTable"] {
      border: 1px solid var(--bw2-edge);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.06), 0 0 0 1px rgba(0,0,0,0.28);
      overflow: hidden;
    }

    .slot {
      background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
      border: 1px solid var(--bw2-edge);
      border-radius: 0;
      padding: 10px 10px 8px;
      text-align: center;
      margin: 6px 0 16px;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
    }

    .slot:hover {
      border-color: var(--bw2-edge-strong);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 0 18px rgba(245,125,49,0.08);
    }

    .slot .title {
      margin-top: 6px;
      font-family: var(--font-pixel);
      font-size: 10px;
      color: var(--bw2-text);
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .slot .sub {
      color: var(--bw2-text-soft);
      font-size: 1rem;
      line-height: 1.2;
    }

    .slot-empty {
      border: 1px dashed var(--bw2-edge);
      background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
      height: 120px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--bw2-text-dim);
      border-radius: 0;
    }

    .pokedex-card,
    .panel-dashed,
    .panel-ghost {
      background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
      border: 1px solid var(--bw2-edge);
      border-radius: 0;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
      color: var(--bw2-text-soft);
    }

    .panel-dashed {
      border-style: dashed;
      padding: 10px 12px;
    }

    .panel-ghost {
      padding: 10px 12px;
    }

    .panel-ghost .title,
    .pokedex-card .title {
      font-family: var(--font-pixel);
      font-size: 10px;
      color: var(--bw2-text);
      text-transform: uppercase;
    }

    .panel-ghost .value,
    .pokedex-card .meta {
      color: var(--bw2-text-soft);
    }

    .poke-sep {
      position: relative;
      height: 2px;
      background: linear-gradient(90deg, transparent 0%, rgba(216,223,232,0.14) 12%, rgba(216,223,232,0.14) 88%, transparent 100%);
      margin: 18px 0;
    }

    .poke-sep::after {
      content: "";
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%) rotate(45deg);
      width: 14px;
      height: 14px;
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dark) 100%);
      border: 1px solid var(--bw2-edge-strong);
      box-shadow: 0 0 0 2px rgba(0,0,0,0.38);
    }

    .status-badge {
      display: inline-block;
      padding: 3px 9px;
      border-radius: 0;
      font-family: var(--font-pixel);
      font-size: 9px;
      text-transform: uppercase;
      border: 1px solid var(--bw2-edge-strong);
      color: #ffffff;
    }

    .status-ok {
      background: linear-gradient(180deg, #4dcc89 0%, #2a8d5c 100%);
    }

    .status-warn {
      background: linear-gradient(180deg, #f06a61 0%, #9f3a34 100%);
    }

    .profile-card {
      border-radius: 0;
      padding: 12px;
      background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
      border: 1px solid var(--bw2-edge);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.3);
    }

    .profile-head {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .profile-avatar {
      width: 68px;
      height: 68px;
      border-radius: 0;
      overflow: hidden;
      flex: 0 0 auto;
      border: 1px solid var(--bw2-edge-strong);
      box-shadow: 0 4px 12px rgba(0,0,0,0.32), inset 0 1px 0 rgba(255,255,255,0.08);
      position: relative;
      background: linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
    }

    .profile-avatar img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }

    .glint {
      position: absolute;
      inset: 0;
      pointer-events: none;
      background: linear-gradient(120deg, transparent 0%, rgba(255,255,255,0.4) 10%, transparent 22%);
      transform: translateX(-130%);
      animation: glint 5s linear infinite;
    }

    @keyframes glint {
      0% { transform: translateX(-130%); }
      100% { transform: translateX(130%); }
    }

    .profile-name {
      font-family: var(--font-pixel);
      font-size: 10px;
      color: var(--bw2-text);
      text-transform: uppercase;
      line-height: 1.4;
    }

    .profile-sub {
      color: var(--bw2-text-dim);
      font-size: 1rem;
      line-height: 1.2;
    }

    .badges-row {
      display: flex;
      gap: 6px;
      align-items: center;
      margin-top: 10px;
      flex-wrap: wrap;
    }

    .badge-dot {
      width: 12px;
      height: 12px;
      display: inline-block;
      clip-path: polygon(20% 0, 100% 0, 100% 80%, 80% 100%, 0 100%, 0 20%);
      background: #2b313b;
      border: 1px solid #6a7382;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
    }

    .badge-on {
      background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
      border-color: var(--bw2-edge-strong);
    }

    .pokeball-mini {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      position: relative;
      display: inline-block;
      background: linear-gradient(180deg, var(--accent) 0 49%, #f4f6f8 51% 100%);
      border: 2px solid #11161a;
      box-shadow: inset 0 0 0 2px #11161a;
    }

    .pokeball-mini::after {
      content: "";
      position: absolute;
      left: 50%;
      top: 50%;
      transform: translate(-50%, -50%);
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: #ffffff;
      border: 2px solid #11161a;
    }

    .mini-team {
      display: flex;
      gap: 6px;
      align-items: center;
      margin-top: 10px;
      flex-wrap: wrap;
    }

    .mini-mon {
      width: 30px;
      height: 30px;
      border-radius: 0;
      background: linear-gradient(180deg, #1a1f27 0%, #10151b 100%);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      border: 1px solid rgba(255,255,255,0.08);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
    }

    .mini-mon img {
      width: 100%;
      height: 100%;
      object-fit: contain;
      image-rendering: -webkit-optimize-contrast;
      filter: drop-shadow(0 0 2px rgba(0,0,0,0.4));
    }

    .stApp * {
      letter-spacing: 0 !important;
    }

    .main .block-container {
      max-width: 1440px;
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
      border-radius: var(--poke-radius-xl) !important;
      clip-path: none !important;
      border: 1px solid rgba(248,251,255,0.28) !important;
      background:
        linear-gradient(110deg, rgba(69,199,255,0.26), transparent 36%),
        linear-gradient(300deg, rgba(255,212,71,0.16), transparent 42%),
        linear-gradient(180deg, rgba(36,95,157,0.98), rgba(16,43,80,0.98)) !important;
      box-shadow: var(--poke-surface-glow), var(--poke-shadow-soft) !important;
    }

    .main .home-hero::before,
    .main .trainers-hero::before,
    .main .league-hero::before,
    .main .matchup-hero::before,
    .main .mart-hero::before,
    .main .cup-hero::before,
    .main .ju-hero::before,
    .main .hof-hero::before,
    .main .norma-hero::before,
    .main .saves-hero::before {
      opacity: 0.5 !important;
    }

    .main .home-hero::after,
    .main .auth-hero::before,
    .main .trainers-hero::after,
    .main .norma-hero::after {
      opacity: 0.32 !important;
    }

    .main .home-card,
    .main .home-action-card,
    .main .auth-panel,
    .main .auth-trainer-card,
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
    .main .matchup-mode-card,
    .main .matchup-summary,
    .main .matchup-metric,
    .main .matchup-mon,
    .main .matchup-move,
    .main .battle-card,
    .main .battle-mon-card,
    .main .battle-empty-card,
    .main .battle-slot,
    .main .mart-register-card,
    .main .mart-confirm-card,
    .main .shop-card,
    .main .cup-mode-card,
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
    .main .season-version-row,
    .main .norma-summary,
    .main .norma-list-item,
    .main .norma-row-card,
    .main .saves-current-card,
    .main .saves-history-card,
    .main .saves-admin-panel,
    .main .saves-stat,
    .main .pl-card,
    .main .pt-metric,
    .main .pt-section,
    .main .pokedex-card,
    .main .trainer-panel,
    .slot,
    .slot-empty,
    .pokedex-card,
    .panel-dashed,
    .panel-ghost,
    section[data-testid="stSidebar"] .profile-card,
    section[data-testid="stSidebar"] .profile-avatar,
    section[data-testid="stSidebar"] .mini-mon {
      border-radius: var(--poke-radius) !important;
      clip-path: none !important;
      border-color: var(--bw2-edge) !important;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.09), rgba(255,255,255,0.03)),
        linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%) !important;
      box-shadow: var(--poke-surface-glow), var(--poke-shadow-card) !important;
    }

    .main .home-card,
    .main .trainers-stat,
    .main .league-status-card,
    .main .matchup-metric,
    .main .season-card,
    .main .saves-stat,
    .main .auth-status {
      background:
        linear-gradient(90deg, rgba(255,212,71,0.12), transparent 44%),
        linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen)) !important;
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
    .main .pt-section,
    .main .trainer-head {
      display: inline-flex !important;
      align-items: center !important;
      gap: 8px !important;
      padding: 8px 12px !important;
      border-radius: var(--poke-radius-sm) !important;
      clip-path: none !important;
      border: 1px solid var(--bw2-edge-strong) !important;
      background:
        linear-gradient(90deg, rgba(255,255,255,0.2), transparent 70%),
        linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%) !important;
      color: #ffffff !important;
      box-shadow: var(--poke-surface-glow), 0 8px 18px rgba(2,18,46,0.18) !important;
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
      font-size: clamp(24px, 3vw, 38px) !important;
      line-height: 1.05 !important;
      text-shadow: 0 3px 16px rgba(2,18,46,0.28) !important;
    }

    .main .home-kicker,
    .main .auth-kicker,
    .main .matchup-kicker,
    .main .cup-kicker,
    .main .ju-hero-chip,
    .main .mart-pill,
    .main .cup-pill,
    .main .matchup-hero-pill,
    .main .season-pill,
    .main .norma-chip,
    .main .trainers-chip,
    .main .hof-team-pill,
    .main .saves-card-badge {
      border-radius: 999px !important;
      clip-path: none !important;
      border: 1px solid rgba(248,251,255,0.3) !important;
      background:
        linear-gradient(90deg, rgba(255,255,255,0.18), transparent 72%),
        rgba(8,31,63,0.74) !important;
      color: var(--bw2-text) !important;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.16) !important;
    }

    .main .shop-head,
    .main .mart-register-card.is-main,
    .main .cup-round-title,
    .main .league-history-title,
    .main .app-notice-title {
      border-radius: var(--poke-radius-sm) !important;
      clip-path: none !important;
    }

    .main img,
    section[data-testid="stSidebar"] img {
      image-rendering: auto;
    }

    .pokeball-mini,
    .trainers-pokeball,
    .auth-pokeball {
      background: linear-gradient(180deg, var(--champion-red) 0 48%, #111c2f 48% 52%, #f8fbff 52% 100%) !important;
      border-color: #111c2f !important;
    }

    .main [style*="clip-path"] {
      clip-path: none !important;
    }

    .main [style*="border-radius:0"],
    .main [style*="border-radius: 0"] {
      border-radius: var(--poke-radius) !important;
    }

    .main .shop-price,
    .main .shop-price-row,
    .main .battle-type-pill,
    .main .type-chip,
    .main .shield-chip,
    .main .rob-chip,
    .status-badge {
      border-radius: 999px !important;
      clip-path: none !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
    apply_champions_skin()
    apply_final_polish()


def render_poke_separator() -> None:
    st.markdown("<div class='poke-sep'></div>", unsafe_allow_html=True)


def apply_section_theme(section: str) -> None:
    palette = {
        "Inicio": ("#4d8dff", "#2f6fff", "#a7d6ff"),
        "Normativa": ("#4d8dff", "#2f6fff", "#c9efff"),
        "Entrenadores": ("#45d1ff", "#218ed9", "#d7f6ff"),
        "Liga y Tabla": ("#ffcf4d", "#d58b15", "#fff0ad"),
        "Hall of Fame": ("#ffe25c", "#c89416", "#fff3b9"),
        "Temporada": ("#4fdf9a", "#24a86a", "#d8ffe8"),
        "Team Preview": ("#45d1ff", "#2f6fff", "#c9efff"),
        "Previa Combate": ("#45d1ff", "#2f6fff", "#c9efff"),
        "Copa": ("#ffd24d", "#d58b15", "#fff0ad"),
        "Juicios": ("#ff6f86", "#c6465b", "#ffe0e7"),
        "Tienda": ("#ffbd5c", "#d47a21", "#ffe8bd"),
        "Saves": ("#45d1ff", "#218ed9", "#d7f6ff"),
    }
    watermarks = {
        "Inicio": "POKEAPP",
        "Normativa": "RULES",
        "Entrenadores": "TRAINER",
        "Liga y Tabla": "LEAGUE",
        "Hall of Fame": "CHAMPION",
        "Temporada": "SEASON",
        "Team Preview": "VS",
        "Previa Combate": "VS",
        "Copa": "CUP",
        "Juicios": "CASE",
        "Tienda": "MART",
        "Saves": "SAVE",
    }
    accent, accent_dark, accent_soft = palette.get(section, ("#2f80ed", "#1452bf", "#9dd3ff"))
    label = section.upper().replace('"', "")
    watermark = watermarks.get(section, "POKEAPP").replace('"', "")
    st.markdown(
        (
            "<style>:root{"
            f"--accent:{accent};"
            f"--accent-dark:{accent_dark};"
            f"--accent-soft:{accent_soft};"
            f"--accent-ghost:{accent}2e;"
            f"--ball-color:{accent};"
            f'--section-label:"{label}";'
            f'--section-watermark:"{watermark}";'
            "}</style>"
        ),
        unsafe_allow_html=True,
    )


def apply_platinum_ui(section: str) -> None:
    if section not in ("Entrenadores", "Tienda", "Saves", "Copa"):
        return
    css = """
    <style>
    .main .block-container {
      font-family: var(--font-ui);
    }

    .main h1,
    .main h2,
    .main h3,
    .main h4,
    .main h5,
    .main h6 {
      font-family: var(--font-pixel);
    }

    .main .pl-card,
    .main .shop-card,
    .main .pt-metric,
    .main .pt-section,
    .main .pt-title,
    .main .pokedex-card {
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
    }

    .main .pl-card {
      background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
      border: 1px solid var(--bw2-edge);
      border-radius: 0;
      padding: 10px;
      color: var(--bw2-text-soft);
    }

    .main .pl-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .main .pl-title,
    .main .shop-name,
    .main .pt-label {
      font-family: var(--font-pixel);
      font-size: 10px;
      color: var(--bw2-text);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .main .pl-muted,
    .main .shop-desc,
    .main .pt-sub {
      color: var(--bw2-text-soft);
      font-size: 1rem;
      line-height: 1.2;
    }

    .main .pl-icon,
    .main .shop-icon {
      image-rendering: pixelated;
    }

    .main .shop-card {
      background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
      border: 1px solid var(--bw2-edge);
      border-radius: 0;
      padding: 0;
      overflow: hidden;
      color: var(--bw2-text-soft);
    }

    .main .shop-head {
      background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
      border-bottom: 1px solid var(--bw2-edge-strong);
      padding: 8px 10px;
    }

    .main .shop-body,
    .main .shop-row {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px;
    }

    .main .shop-info {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .main .shop-price {
      display: inline-block;
      margin-top: 6px;
      padding: 5px 8px;
      background: linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.03) 100%);
      border: 1px solid rgba(255,255,255,0.12);
      color: #ffffff;
      font-family: var(--font-pixel);
      font-size: 10px;
      clip-path: polygon(8px 0, 100% 0, 100% calc(100% - 8px), calc(100% - 8px) 100%, 0 100%, 0 8px);
    }

    .main .shop-missing {
      margin-top: 6px;
      color: #ffaba7;
      font-size: 1rem;
    }

    .main .pt-title {
      display: inline-block;
      padding: 9px 12px;
      background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
      border: 1px solid var(--bw2-edge-strong);
      border-radius: 0;
      color: #ffffff;
      font-family: var(--font-pixel);
      font-size: 12px;
      text-transform: uppercase;
      clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
    }

    .main .pt-section {
      display: inline-block;
      padding: 7px 10px;
      background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
      border: 1px solid var(--bw2-edge);
      border-radius: 0;
      color: var(--bw2-text);
      font-family: var(--font-pixel);
      font-size: 10px;
      text-transform: uppercase;
    }

    .main .pt-metric {
      background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
      border: 1px solid var(--bw2-edge);
      border-radius: 0;
      padding: 10px 12px;
      color: var(--bw2-text-soft);
    }

    .main .pt-metric .pt-value {
      margin-top: 6px;
      font-family: var(--font-pixel);
      font-size: 12px;
      color: var(--bw2-text);
    }

    .main .pt-divider {
      height: 2px;
      margin: 10px 0 14px;
      background:
        linear-gradient(90deg, transparent 0%, rgba(216,223,232,0.12) 15%, rgba(216,223,232,0.12) 85%, transparent 100%),
        linear-gradient(90deg, transparent 0%, var(--accent) 22%, var(--accent) 78%, transparent 100%);
      background-size: 100% 2px, 100% 1px;
      background-repeat: no-repeat;
      background-position: center center;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
