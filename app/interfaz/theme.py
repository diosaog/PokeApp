from __future__ import annotations

import streamlit as st


def apply_css() -> None:
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');
    :root {
      --accent: #e65050;
      --accent-hover: #c73a3a;
      --text-1: #e6edf3;
      --text-2: #c9d1d9;
      --divider: rgba(255,255,255,0.14);
    }
    .main { position: relative; }
    .main:before {
      content: "";
      position: fixed; inset: 0; z-index: -1; pointer-events: none;
      background:
        radial-gradient(circle at 18% 22%, rgba(255,255,255,0.06) 0 64px, transparent 65px),
        radial-gradient(circle at 18% 22%, rgba(239,83,80,0.10) 0 36px, transparent 37px),
        linear-gradient(0deg, rgba(239,83,80,0.08) 0 12px, transparent 13px) 18% 22%/128px 128px no-repeat,
        radial-gradient(circle at 80% 78%, rgba(255,255,255,0.06) 0 74px, transparent 75px),
        radial-gradient(circle at 80% 78%, rgba(239,83,80,0.10) 0 42px, transparent 43px),
        linear-gradient(0deg, rgba(239,83,80,0.08) 0 12px, transparent 13px) 80% 78%/148px 148px no-repeat,
        radial-gradient(circle at 20% 15%, rgba(255,255,255,0.045) 0 25px, transparent 26px) 0 0/120px 120px,
        radial-gradient(circle at 80% 85%, rgba(255,255,255,0.045) 0 25px, transparent 26px) 0 0/140px 140px,
        radial-gradient(circle at calc(100% - 180px) calc(100% - 180px), color-mix(in srgb, var(--ball-color, #ffffff) 80%, transparent) 0 10px, transparent 11px) 100% 100%/360px 360px no-repeat,
        linear-gradient(0deg, color-mix(in srgb, var(--ball-color, #ffffff) 35%, transparent) 0 50%, rgba(10,13,18,0.8) 50% 100%) calc(100% - 180px) calc(100% - 180px)/360px 360px no-repeat,
        radial-gradient(circle at calc(100% - 180px) calc(100% - 220px), color-mix(in srgb, var(--ball-color, #ffffff) 45%, transparent) 0 140px, transparent 141px) 100% 100%/360px 360px no-repeat,
        linear-gradient(180deg, #0a0d12 0%, #0a0d12 60%, #090c10 100%);
    }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; border-radius: 0; animation: fadeInUp .35s ease-out both; }
    @keyframes fadeInUp { from { opacity:0; transform: translate3d(0,8px,0);} to { opacity:1; transform: translate3d(0,0,0);} }
    h1,h2,h3,h4,h5,h6 { color: var(--text-1); }
    p,span,div,label { color: var(--text-2); }
    section[data-testid="stSidebar"] { background: rgba(16,19,26,0.9); backdrop-filter: blur(6px); border-right: 1px solid rgba(255,255,255,0.06); }
    hr { border: none; height: 2px; background: linear-gradient(90deg, transparent 0 10%, var(--divider) 10% 90%, transparent 90% 100%); position: relative; }
    hr::after { content:""; position:absolute; top:-7px; left:50%; transform:translateX(-50%); width:20px; height:20px; border-radius:50%;
      background: radial-gradient(circle at 50% 50%, rgba(255,255,255,0.9) 0 3px, transparent 4px),
                  linear-gradient(180deg, #ff1d1d 0 50%, #f9f9f9 50% 100%);
      box-shadow: 0 0 0 2px rgba(0,0,0,0.35), 0 2px 6px rgba(0,0,0,0.25);
      border: 2px solid #111;
    }
    .stButton>button, .stDownloadButton>button { border-radius: 0; padding: 0.6rem 1rem; min-height: 40px; background: linear-gradient(180deg, var(--accent), color-mix(in srgb, var(--accent) 80%, #7f1d1d)); border: 1px solid rgba(255,255,255,0.18); color: #fff; box-shadow: inset 0 1px 0 rgba(255,255,255,0.15), 0 4px 12px rgba(0,0,0,0.35); }
    .stButton>button:focus-visible { outline: 2px solid #90caf9; outline-offset: 2px; }

    .slot { background: #0f1319; border: 1px solid #2a2f38; border-radius: 0; padding: 10px 10px 8px; text-align:center; margin: 6px 0 16px; box-shadow: inset 0 1px 0 rgba(255,255,255,0.04); }
    .slot:hover { box-shadow: inset 0 1px 0 rgba(255,255,255,0.08); border-color: #3a4250; }
    .slot .title { font-weight: 600; color: #e6edf3; margin-top: 6px; }
    .slot .sub { color: #9aa3ab; font-size: 0.82rem; }
    .slot { cursor: default; }
    .slot-empty { border: 1px dashed #3a4250; background: #0f1319; height: 120px; display:flex; align-items:center; justify-content:center; color:#8a919a; border-radius:0; }

    .pokedex-card { border-radius: 0; background: #0f1319; padding: 12px 14px; border: 1px solid #2a2f38; box-shadow: inset 0 1px 0 rgba(255,255,255,0.04); }
    .pokedex-card .title { font-family: "Press Start 2P", monospace; font-size: 0.9rem; color: #e6edf3; }
    .pokedex-card .meta  { color: #9aa3ab; font-size: 0.85rem; }

    .poke-sep { position: relative; height: 1px; background: rgba(255,255,255,0.12); margin: 18px 0; }
    .poke-sep::after { content:""; position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); width:28px; height:28px; border-radius:50%;
      background:
        radial-gradient(circle at 50% 50%, rgba(255,255,255,0.9) 0 3px, transparent 4px),
        linear-gradient(180deg, #ff1d1d 0 50%, #f7f7f7 50% 100%);
      box-shadow: 0 0 0 2px rgba(0,0,0,0.4), 0 2px 8px rgba(0,0,0,0.35);
      border: 2px solid #0b0d12;
    }
    .status-badge { display:inline-block; padding:2px 10px; border-radius:0; font-weight:700; font-size:0.8rem; margin-left:8px; }
    .panel-dashed { border: 1px dashed #3a4250; background: #0f1319; padding: 10px 12px; border-radius:0; }
    .panel-ghost { border: 1px solid #2a2f38; background: #0f1319; padding: 10px 12px; border-radius:0; }
    .panel-ghost .title { font-weight:700; margin-bottom:4px; }
    .panel-ghost .value { font-weight:800; font-size:1.1rem; }
    .status-ok { background:#1b5e20; color:#e8f5e9; border:1px solid rgba(255,255,255,0.15); }
    .status-warn { background:#7f1d1d; color:#ffebee; border:1px solid rgba(255,255,255,0.15); }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

    st.markdown(
        """
        <style>
        .profile-card { border-radius: 0; padding: 12px; background: #0f1319; border: 1px solid #2a2f38; box-shadow: inset 0 1px 0 rgba(255,255,255,0.04); }
        .profile-head { display:flex; align-items:center; gap:12px; }
        .profile-avatar { width:64px; height:64px; border-radius:50%; overflow:hidden; flex:0 0 auto; box-shadow: 0 4px 10px rgba(0,0,0,0.35), 0 0 0 3px rgba(255,255,255,0.06); position:relative; }
        .profile-avatar img { width:100%; height:100%; object-fit:cover; display:block; filter: saturate(1.08); }
        .glint { position:absolute; inset:0; pointer-events:none; background: linear-gradient(120deg, transparent 0%, rgba(255,255,255,0.55) 12%, transparent 24%); transform: translateX(-120%); animation: glint 5s linear infinite; }
        @keyframes glint { 0% { transform: translateX(-120%);} 100% { transform: translateX(120%);} }
        .profile-meta { line-height:1.2; }
        .profile-name { font-weight:700; color:#e6edf3; }
        .profile-sub { color:#9aa3ab; font-size: 0.85rem; }
        .badges-row { display:flex; gap:6px; align-items:center; margin-top:10px; flex-wrap:wrap; }
        .badge-dot { width:12px; height:12px; border-radius:50%; display:inline-block; box-shadow: inset 0 0 0 1px rgba(0,0,0,0.35); background: rgba(255,255,255,0.12); }
        .badge-on { background: color-mix(in srgb, var(--accent, #ef5350) 75%, #ffffff); }
        .pokeball-mini { width:16px; height:16px; border-radius:50%; position:relative; display:inline-block; background: linear-gradient(180deg, #ff1d1d 0 49%, #f7f7f7 51% 100%); border:2px solid #111; box-shadow: inset 0 0 0 2px #111; animation: spin 4s linear infinite; }
        .pokeball-mini::after { content:""; position:absolute; left:50%; top:50%; transform:translate(-50%,-50%); width:6px; height:6px; border-radius:50%; background:#fff; border:2px solid #111; box-shadow: 0 0 0 1px rgba(0,0,0,0.35); }
        @keyframes spin { 0% { transform: rotate(0deg);} 100% { transform: rotate(360deg);} }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <style>
        .mini-team { display:flex; gap:6px; align-items:center; margin-top:10px; flex-wrap:wrap; }
        .mini-mon { width:28px; height:28px; border-radius:6px; background:rgba(255,255,255,0.06); display:inline-flex; align-items:center; justify-content:center; overflow:hidden; box-shadow: 0 1px 0 rgba(0,0,0,0.25); }
        .mini-mon img { width:100%; height:100%; object-fit:contain; image-rendering: -webkit-optimize-contrast; filter: drop-shadow(0 0 2px rgba(0,0,0,0.35)); }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_poke_separator() -> None:
    st.markdown("<div class='poke-sep'></div>", unsafe_allow_html=True)


def apply_section_theme(section: str) -> None:
    palette = {
        "Inicio": "#ef5350",
        "Entrenadores": "#ef5350",
        "Liga y Tabla": "#f59e0b",
        "Copa": "#8b5cf6",
        "Tienda": "#2a75bb",
        "Saves": "#10b981",
    }
    color = palette.get(section, "#ef5350")
    st.markdown(f"<style>:root{{ --ball-color: {color}; }}</style>", unsafe_allow_html=True)


def apply_platinum_ui(section: str) -> None:
    if section not in ("Entrenadores", "Tienda"):
        return
    css = """
    <style>
    :root {
      --pt-beige: #d7d4c0;
      --pt-beige-dark: #9a9680;
      --pt-yellow: #f1c258;
      --pt-yellow-dark: #c28f27;
      --pt-paper: #f7f6ef;
      --pt-blue: #7f88dd;
      --pt-red: #f1a39a;
      --pt-text: #2b2b2b;
    }

    .main .block-container { font-family: "Press Start 2P", monospace; font-weight: 700; }
    .main .block-container * { font-weight: 700; }
    .main h1, .main h2, .main h3, .main h4, .main h5, .main h6 { font-family: "Press Start 2P", monospace; letter-spacing: 0.3px; }

    .main .stButton > button {
      font-family: "Press Start 2P", monospace;
      font-size: 11px;
      background: var(--pt-yellow);
      color: var(--pt-text);
      border: 2px solid var(--pt-yellow-dark);
      border-radius: 6px;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.35);
    }
    .main .stButton > button:disabled { opacity: 0.6; }

    .main div[data-baseweb="tab-list"] {
      background: var(--pt-beige);
      border: 2px solid var(--pt-beige-dark);
      border-radius: 6px;
      padding: 4px;
      gap: 4px;
    }
    .main button[data-baseweb="tab"] {
      font-family: "Press Start 2P", monospace;
      font-size: 10px;
      background: var(--pt-paper);
      color: var(--pt-text);
      border: 2px solid var(--pt-beige-dark);
      border-radius: 4px;
      padding: 6px 8px;
    }
    .main button[data-baseweb="tab"][aria-selected="true"] {
      background: var(--pt-yellow);
      border-color: var(--pt-yellow-dark);
    }

    .main .stSelectbox div[data-baseweb="select"],
    .main .stTextInput input,
    .main .stNumberInput input,
    .main .stTextArea textarea {
      background: var(--pt-paper);
      color: var(--pt-text);
      border: 2px solid var(--pt-beige-dark);
      border-radius: 6px;
      font-family: "Press Start 2P", monospace;
      font-size: 11px;
    }

    .main div[data-testid="stMetric"] {
      background: var(--pt-paper);
      border: 2px solid var(--pt-beige-dark);
      border-radius: 6px;
      padding: 8px 10px;
    }
    .main div[data-testid="stMetric"] [data-testid="stMetricLabel"],
    .main div[data-testid="stMetric"] [data-testid="stMetricValue"] {
      color: var(--pt-text);
      font-family: "Press Start 2P", monospace;
    }

    .main div[data-baseweb="notification"] {
      background: var(--pt-paper);
      border: 2px solid var(--pt-beige-dark);
      border-radius: 6px;
      color: var(--pt-text);
    }

    .main details[data-testid="stExpander"] {
      background: var(--pt-paper);
      border: 2px solid var(--pt-beige-dark);
      border-radius: 6px;
    }
    .main details[data-testid="stExpander"] > summary {
      background: var(--pt-yellow);
      border-bottom: 2px solid var(--pt-yellow-dark);
      color: var(--pt-text);
      font-family: "Press Start 2P", monospace;
      border-radius: 4px 4px 0 0;
    }

    .main .panel-dashed {
      border: 2px dashed var(--pt-beige-dark);
      background: var(--pt-paper);
      border-radius: 6px;
      color: var(--pt-text);
    }
    .main .panel-ghost {
      border: 2px solid var(--pt-beige-dark);
      background: var(--pt-paper);
      border-radius: 6px;
      color: var(--pt-text);
    }

    .main .status-badge {
      font-family: "Press Start 2P", monospace;
      font-size: 10px;
      border-radius: 4px;
      padding: 4px 8px;
      border: 2px solid #6a6a6a;
      background: var(--pt-paper);
      color: var(--pt-text);
    }
    .main .status-ok { background: #9de1a5; border-color: #5b9b65; color: #1f3b22; }
    .main .status-warn { background: var(--pt-red); border-color: #c9756b; color: #4b1f1a; }

    .main .pokedex-card {
      background: var(--pt-paper);
      border: 2px solid var(--pt-beige-dark);
      border-radius: 6px;
      color: var(--pt-text);
    }

    .main .pl-card {
      background: var(--pt-paper);
      border: 2px solid var(--pt-beige-dark);
      border-radius: 6px;
      padding: 8px;
      color: var(--pt-text);
    }
    .main .pl-row { display:flex; align-items:center; gap:8px; }
    .main .pl-title { font-size: 11px; color: var(--pt-text); }
    .main .pl-muted { font-size: 10px; color: #5a5a5a; }
    .main .pl-icon { width: 40px; height: 40px; image-rendering: pixelated; }

    .main .shop-card {
      background: var(--pt-paper);
      border: 2px solid var(--pt-beige-dark);
      border-radius: 6px;
      padding: 0;
      color: var(--pt-text);
      overflow: hidden;
    }
    .main .shop-head {
      background: var(--pt-yellow);
      border-bottom: 2px solid var(--pt-yellow-dark);
      padding: 6px 8px;
    }
    .main .shop-body { display:flex; align-items:center; gap:8px; padding: 8px; }
    .main .shop-row { display:flex; align-items:center; gap:8px; }
    .main .shop-icon { width: 42px; height: 42px; image-rendering: pixelated; }
    .main .shop-name { font-size: 11px; color: var(--pt-text); }
    .main .shop-desc { font-size: 10px; color: #3b3b3b; margin-top: 4px; }
    .main .shop-price {
      display: inline-block;
      margin-top: 6px;
      background: var(--pt-yellow);
      border: 2px solid var(--pt-yellow-dark);
      border-radius: 4px;
      padding: 4px 6px;
      font-size: 10px;
      color: var(--pt-text);
    }
    .main .shop-missing { font-size: 10px; color: #7a2e2e; margin-top: 4px; }

    .main .pt-title {
      display:inline-block;
      background: var(--pt-yellow);
      border: 2px solid var(--pt-yellow-dark);
      border-radius: 6px;
      padding: 8px 10px;
      font-size: 14px;
      color: var(--pt-text);
    }
    .main .pt-section {
      background: var(--pt-paper);
      border: 2px solid var(--pt-beige-dark);
      border-radius: 6px;
      padding: 6px 8px;
      font-size: 11px;
      color: var(--pt-text);
      display:inline-block;
    }
    .main .pt-divider {
      height: 2px;
      background: #b9b59f;
      margin: 10px 0 14px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
