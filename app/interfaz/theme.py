from __future__ import annotations

import streamlit as st


def apply_css() -> None:
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Silkscreen:wght@400;700&family=VT323&display=swap');

    :root {
      --font-ui: "VT323", monospace;
      --font-pixel: "Silkscreen", "Press Start 2P", monospace;
      --accent: #f57d31;
      --accent-dark: #a94818;
      --accent-soft: #ffc08f;
      --accent-ghost: rgba(245, 125, 49, 0.18);
      --bw2-bg-0: #07090d;
      --bw2-bg-1: #0f1217;
      --bw2-bg-2: #161a20;
      --bw2-panel: #1c2129;
      --bw2-panel-2: #252a33;
      --bw2-panel-3: #2c333d;
      --bw2-screen: #121820;
      --bw2-screen-2: #18222d;
      --bw2-screen-line: #79b9f5;
      --bw2-edge: #636d7b;
      --bw2-edge-strong: #d8dfe8;
      --bw2-text: #f3f7fb;
      --bw2-text-soft: #b8c1cd;
      --bw2-text-dim: #8892a0;
      --bw2-ok: #58d18e;
      --bw2-warn: #f26b61;
      --bw2-gold: #e5bc56;
      --bw2-shadow: rgba(0, 0, 0, 0.42);
      --divider: rgba(216, 223, 232, 0.18);
      --ball-color: #f57d31;
      --section-label: "NORMATIVA";
    }

    html, body, [class*="css"] {
      font-family: var(--font-ui);
    }

    .stApp {
      background: linear-gradient(180deg, #08090c 0%, #0f1217 48%, #090b0f 100%);
      color: var(--bw2-text);
    }

    .stApp::before {
      content: "";
      position: fixed;
      inset: 0 0 auto 0;
      height: 44px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.07) 0, rgba(255,255,255,0.03) 1px, transparent 1px),
        linear-gradient(180deg, #252a31 0%, #171b22 100%);
      border-bottom: 1px solid rgba(216,223,232,0.18);
      box-shadow: 0 1px 0 rgba(255,255,255,0.05), 0 8px 20px rgba(0,0,0,0.28);
      z-index: 1000;
      pointer-events: none;
    }

    .stApp::after {
      content: "IR   ONLINE   WIRELESS";
      position: fixed;
      top: 10px;
      left: 50%;
      transform: translateX(-50%);
      color: #8c929c;
      font-family: var(--font-pixel);
      font-size: 10px;
      letter-spacing: 0.18em;
      z-index: 1001;
      pointer-events: none;
      text-shadow: 0 1px 0 rgba(0,0,0,0.65);
    }

    .main { position: relative; }
    .main::before {
      content: "";
      position: fixed;
      inset: 0;
      z-index: -1;
      pointer-events: none;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.035) 0 1px, transparent 1px 100%) 0 44px / 100% 28px,
        linear-gradient(90deg, rgba(255,255,255,0.03) 0 1px, transparent 1px 100%) 0 44px / 28px 100%,
        linear-gradient(135deg, rgba(245,125,49,0.22) 0 14%, transparent 14%) calc(100% - 36px) calc(100% - 36px) / 420px 220px no-repeat,
        linear-gradient(315deg, rgba(100,185,255,0.13) 0 12%, transparent 12%) 0 0 / 380px 240px no-repeat,
        radial-gradient(circle at 18% 10%, rgba(121,185,245,0.12) 0 110px, transparent 170px),
        radial-gradient(circle at 80% 84%, rgba(245,125,49,0.08) 0 100px, transparent 170px),
        linear-gradient(180deg, var(--bw2-bg-0) 0%, var(--bw2-bg-1) 36%, #0b0d11 100%);
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
      letter-spacing: 0.04em;
      text-transform: uppercase;
      text-shadow: 0 1px 0 rgba(0,0,0,0.55);
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
        linear-gradient(180deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 100%) 0 0 / 100% 24px,
        linear-gradient(90deg, rgba(255,255,255,0.04) 0 1px, transparent 1px 100%) 0 0 / 24px 100%,
        linear-gradient(180deg, #12151b 0%, #0b0d11 100%);
      border-right: 1px solid rgba(216,223,232,0.15);
      box-shadow: inset -1px 0 0 rgba(255,255,255,0.04);
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
      padding: 7px 12px;
      color: #ffffff;
      background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
      border: 1px solid var(--bw2-edge-strong);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.2), 0 4px 12px rgba(0,0,0,0.26);
      font-family: var(--font-pixel);
      font-size: 10px;
      letter-spacing: 0.08em;
      text-align: center;
      clip-path: polygon(12px 0, 100% 0, 100% calc(100% - 12px), calc(100% - 12px) 100%, 0 100%, 0 12px);
    }

    .stButton > button,
    .stDownloadButton > button {
      min-height: 42px;
      padding: 0.65rem 1rem;
      border-radius: 0;
      border: 1px solid var(--bw2-edge-strong);
      background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
      color: #ffffff;
      font-family: var(--font-pixel);
      font-size: 11px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.24), 0 6px 16px rgba(0,0,0,0.28);
      clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
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
      background: linear-gradient(180deg, #555d68 0%, #353b45 100%);
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
      background: linear-gradient(180deg, #0f151d 0%, #151c25 100%) !important;
      color: var(--bw2-text) !important;
      border: 1px solid var(--bw2-edge) !important;
      border-radius: 0 !important;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.36) !important;
      font-family: var(--font-ui) !important;
      font-size: 1.15rem !important;
      letter-spacing: 0.03em;
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
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .stSelectbox div[data-baseweb="select"] > div,
    .stMultiSelect div[data-baseweb="select"] > div {
      background: linear-gradient(180deg, #0f151d 0%, #151c25 100%) !important;
      border: 1px solid var(--bw2-edge) !important;
      border-radius: 0 !important;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.36) !important;
      min-height: 44px;
      color: var(--bw2-text) !important;
      font-family: var(--font-ui) !important;
      font-size: 1.15rem !important;
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
      border-radius: 0 !important;
      font-family: var(--font-ui) !important;
      font-size: 1.05rem !important;
    }

    div[data-baseweb="tab-list"] {
      background: linear-gradient(180deg, #252a32 0%, #191d24 100%) !important;
      border: 1px solid var(--bw2-edge) !important;
      border-radius: 0 !important;
      padding: 4px !important;
      gap: 4px !important;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.32);
    }

    button[data-baseweb="tab"],
    button[role="tab"] {
      background: linear-gradient(180deg, #1a1f27 0%, #11161c 100%) !important;
      color: var(--bw2-text-soft) !important;
      border: 1px solid var(--bw2-edge) !important;
      border-radius: 0 !important;
      font-family: var(--font-pixel) !important;
      font-size: 10px !important;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
    }

    button[data-baseweb="tab"][aria-selected="true"],
    button[role="tab"][aria-selected="true"] {
      background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%) !important;
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
      background: linear-gradient(180deg, rgba(255,255,255,0.03) 0%, transparent 100%), linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%) !important;
      border: 1px solid var(--bw2-edge) !important;
      border-radius: 0 !important;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.32) !important;
      color: var(--bw2-text-soft) !important;
    }

    details[data-testid="stExpander"] > summary {
      background: linear-gradient(180deg, rgba(255,255,255,0.05) 0%, rgba(0,0,0,0.04) 100%);
      border-bottom: 1px solid rgba(255,255,255,0.08);
      color: var(--bw2-text) !important;
      font-family: var(--font-pixel) !important;
      font-size: 10px !important;
      letter-spacing: 0.04em;
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
      background: linear-gradient(180deg, #10161d 0%, #151d26 100%) !important;
      border: 1px dashed var(--bw2-edge) !important;
      border-radius: 0 !important;
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
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def render_poke_separator() -> None:
    st.markdown("<div class='poke-sep'></div>", unsafe_allow_html=True)


def apply_section_theme(section: str) -> None:
    palette = {
        "Inicio": ("#6ea8ff", "#29548f"),
        "Normativa": ("#6ea8ff", "#29548f"),
        "Entrenadores": ("#62c8ff", "#1d679c"),
        "Liga y Tabla": ("#f58b3c", "#9f431f"),
        "Temporada": ("#8fd66b", "#357c36"),
        "Team Preview": ("#ff6f61", "#8e2d2f"),
        "Previa Combate": ("#ff6f61", "#8e2d2f"),
        "Copa": ("#cf74ff", "#74389f"),
        "Juicios": ("#ef5e68", "#962d37"),
        "Tienda": ("#efc257", "#a86f1f"),
        "Saves": ("#4fd399", "#1f7e5e"),
    }
    accent, accent_dark = palette.get(section, ("#f57d31", "#a94818"))
    label = section.upper().replace('"', "")
    st.markdown(
        (
            "<style>:root{"
            f"--accent:{accent};"
            f"--accent-dark:{accent_dark};"
            f"--ball-color:{accent};"
            f'--section-label:"{label}";'
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
