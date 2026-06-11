from __future__ import annotations

import streamlit as st


def render_shop_styles() -> None:
    st.markdown(
        """
        <style>
        .main .stButton > button,
        .main .stButton > button * {
          font-family: var(--font-pixel) !important;
          font-size: 10px !important;
          font-weight: 700 !important;
          color: #ffffff !important;
          -webkit-text-fill-color: #ffffff !important;
          opacity: 1 !important;
        }
        .main .stButton > button:disabled,
        .main .stButton > button:disabled * {
          color: #cbd1d9 !important;
          -webkit-text-fill-color: #cbd1d9 !important;
          opacity: 1 !important;
        }
        .main button[data-baseweb="tab"],
        .main button[role="tab"],
        .main button[data-baseweb="tab"] *,
        .main button[role="tab"] * {
          font-family: var(--font-pixel) !important;
          font-size: 10px !important;
          font-weight: 700 !important;
        }
        .main div[data-testid="stTabs"] div[data-baseweb="tab-list"],
        .main div[data-testid="stTabs"] [role="tablist"] {
          gap: 8px !important;
          flex-wrap: wrap !important;
          align-items: stretch !important;
          padding: 6px;
          border: 1px solid rgba(216,223,232,0.16);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.05), transparent 58%),
            linear-gradient(180deg, rgba(29,37,48,0.96) 0%, rgba(13,18,25,0.96) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 6px 18px rgba(0,0,0,0.2);
        }
        .main div[data-testid="stTabs"] button[data-baseweb="tab"],
        .main div[data-testid="stTabs"] button[role="tab"] {
          flex: 0 0 178px !important;
          width: 178px !important;
          min-width: 178px !important;
          justify-content: center !important;
          min-height: 44px !important;
          padding-left: 12px !important;
          padding-right: 12px !important;
          border: 1px solid rgba(216,223,232,0.22) !important;
          background: linear-gradient(180deg, #252d38 0%, #151b24 100%) !important;
          clip-path: polygon(9px 0, 100% 0, 100% calc(100% - 9px), calc(100% - 9px) 100%, 0 100%, 0 9px);
          white-space: nowrap !important;
        }
        .main div[data-testid="stTabs"] button[aria-selected="true"],
        .main div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
          border-color: var(--bw2-edge-strong) !important;
          background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%) !important;
        }

        .mart-hero {
          position: relative;
          overflow: hidden;
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 18px;
          align-items: stretch;
          min-height: 150px;
          margin-bottom: 12px;
          padding: 16px;
          border: 1px solid var(--bw2-edge);
          background:
            linear-gradient(115deg, rgba(103,169,229,0.12) 0 32%, transparent 32% 100%),
            linear-gradient(180deg, rgba(43,52,64,0.96) 0%, rgba(17,24,33,0.96) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.09), 0 10px 26px rgba(0,0,0,0.24);
        }
        .mart-hero::before {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background:
            linear-gradient(180deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 100%) 0 0 / 100% 22px,
            linear-gradient(90deg, rgba(255,255,255,0.04) 0 1px, transparent 1px 100%) 0 0 / 26px 100%;
          opacity: .55;
        }
        .mart-hero-left,
        .mart-hero-right {
          position: relative;
          z-index: 1;
        }
        .mart-kicker,
        .mart-label,
        .mart-pill,
        .mart-aisle-code,
        .shop-sku {
          font-family: var(--font-pixel);
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }
        .mart-kicker {
          display: inline-block;
          padding: 5px 8px;
          border-left: 3px solid var(--accent);
          background: rgba(0,0,0,0.28);
          color: var(--bw2-text-soft);
          font-size: 9px;
        }
        .mart-title {
          margin-top: 12px;
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: clamp(20px, 3.2vw, 34px);
          line-height: 1.05;
          text-transform: uppercase;
          text-shadow: 0 2px 0 rgba(0,0,0,0.5);
        }
        .mart-subrow {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 13px;
        }
        .mart-pill {
          display: inline-flex;
          align-items: center;
          min-height: 29px;
          padding: 6px 9px;
          border: 1px solid rgba(216,223,232,0.16);
          background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02));
          color: #ffffff;
          font-size: 9px;
        }
        .mart-hero-right {
          min-width: 210px;
          display: grid;
          align-content: center;
          gap: 8px;
          padding: 12px;
          border: 1px solid rgba(216,223,232,0.18);
          background:
            linear-gradient(180deg, rgba(10,15,22,0.68) 0%, rgba(9,12,17,0.9) 100%);
        }
        .mart-led {
          display: flex;
          align-items: center;
          gap: 8px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
        }
        .mart-led::before {
          content: "";
          width: 10px;
          height: 10px;
          background: #58d18e;
          box-shadow: 0 0 12px rgba(88,209,142,0.7);
        }
        .mart-register-grid {
          display: grid;
          grid-template-columns: minmax(180px, 1.1fr) repeat(3, minmax(140px, .8fr));
          gap: 10px;
          margin: 12px 0 14px;
        }
        .mart-register-card,
        .mart-alert,
        .mart-aisle-head,
        .mart-confirm-card {
          border: 1px solid var(--bw2-edge);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.05), transparent 60%),
            linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
        }
        .mart-register-card {
          min-width: 0;
          padding: 11px 12px;
        }
        .mart-register-card.is-main {
          border-color: var(--bw2-edge-strong);
          background:
            linear-gradient(115deg, rgba(239,194,87,0.2) 0 42%, transparent 42% 100%),
            linear-gradient(180deg, #2d3440 0%, #161d27 100%);
        }
        .mart-label {
          color: var(--bw2-text-soft);
          font-size: 8px;
        }
        .mart-value {
          margin-top: 7px;
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 15px;
          line-height: 1.15;
          overflow-wrap: anywhere;
        }
        .mart-register-card.is-main .mart-value {
          color: #ffe08b;
          font-size: 20px;
        }
        .mart-alert {
          margin: 10px 0;
          padding: 10px 12px;
          border-left: 4px solid #f26b61;
          color: #ffffff;
        }
        .mart-alert strong {
          display: block;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
        }
        .mart-alert span {
          display: block;
          margin-top: 6px;
          font-family: var(--font-ui);
          font-size: 18px;
        }
        .mart-aisle-head {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 12px;
          align-items: center;
          margin: 12px 0 10px;
          padding: 11px 12px;
        }
        .mart-aisle-code {
          color: var(--accent-soft);
          font-size: 8px;
        }
        .mart-aisle-title {
          margin-top: 4px;
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 14px;
          text-transform: uppercase;
        }
        .mart-aisle-meta {
          display: flex;
          flex-wrap: wrap;
          justify-content: flex-end;
          gap: 7px;
        }

        .shop-card {
          position: relative;
          overflow: hidden;
          min-height: 218px;
          margin-bottom: 8px;
          border: 1px solid rgba(216,223,232,0.22);
          background:
            linear-gradient(180deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 100%) 0 0 / 100% 20px,
            linear-gradient(180deg, #252d38 0%, #151b24 100%);
          color: var(--bw2-text-soft);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.09), 0 6px 16px rgba(0,0,0,0.22);
        }
        .shop-card::before {
          content: "";
          position: absolute;
          left: 0;
          right: 0;
          bottom: 0;
          height: 13px;
          background: linear-gradient(180deg, #39424f 0%, #151b24 100%);
          border-top: 1px solid rgba(216,223,232,0.18);
        }
        .shop-card.is-sale {
          border-color: rgba(255,210,109,0.72);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.11), 0 0 0 1px rgba(239,194,87,0.2), 0 8px 20px rgba(0,0,0,0.26);
        }
        .shop-card.is-poor {
          filter: saturate(.72);
        }
        .shop-head {
          position: relative;
          z-index: 1;
          display: flex;
          justify-content: space-between;
          gap: 8px;
          min-height: 44px;
          padding: 9px 10px 8px;
          border-bottom: 1px solid rgba(216,223,232,0.18);
          background:
            linear-gradient(90deg, var(--accent) 0 4px, transparent 4px 100%),
            linear-gradient(180deg, rgba(18,25,34,0.96) 0%, rgba(10,15,22,0.96) 100%);
        }
        .shop-name {
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          line-height: 1.25;
          text-transform: uppercase;
          overflow-wrap: anywhere;
        }
        .shop-sku {
          flex: 0 0 auto;
          color: var(--bw2-text-dim);
          font-size: 7px;
        }
        .shop-body {
          position: relative;
          z-index: 1;
          display: grid;
          grid-template-columns: 76px minmax(0, 1fr);
          gap: 10px;
          padding: 11px 10px 12px;
        }
        .shop-icon-slot {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 76px;
          height: 76px;
          border: 1px solid rgba(216,223,232,0.2);
          background:
            radial-gradient(circle at 50% 42%, rgba(255,255,255,0.12), transparent 38px),
            linear-gradient(180deg, #1c2735 0%, #101720 100%);
        }
        .shop-icon {
          width: 58px;
          height: 58px;
          object-fit: contain;
          image-rendering: pixelated;
          filter: drop-shadow(0 4px 6px rgba(0,0,0,0.42));
        }
        .shop-info {
          min-width: 0;
          display: grid;
          align-content: start;
          gap: 8px;
        }
        .shop-desc {
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1.12;
          overflow-wrap: anywhere;
        }
        .shop-price {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 6px;
          width: fit-content;
          max-width: 100%;
          box-sizing: border-box;
          padding: 6px 8px;
          border: 1px solid rgba(255,255,255,0.14);
          background: linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.03) 100%);
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          line-height: 1.2;
        }
        .shop-main-price {
          color: #ffffff;
        }
        .shop-discount-badge {
          display: inline-flex;
          align-items: center;
          min-height: 22px;
          padding: 3px 6px;
          border: 1px solid rgba(255,255,255,0.24);
          background: linear-gradient(180deg, #f26f3d 0%, #8d2f20 100%);
          color: #ffffff;
        }
        .shop-old-price {
          color: #c6ccd4;
          text-decoration: line-through;
          text-decoration-thickness: 2px;
        }
        .shop-arrow {
          color: #f6c15b;
        }
        .shop-stock,
        .shop-missing {
          display: block;
          width: 100%;
          font-family: var(--font-pixel);
          font-size: 8px;
          line-height: 1.2;
        }
        .shop-stock {
          color: var(--bw2-text-soft);
        }
        .shop-missing {
          color: #ffaba7;
        }
        .main .shop-price {
          gap: 8px;
          padding: 8px 10px;
          font-size: 13px;
          line-height: 1.2;
        }
        .main .shop-discount-badge {
          min-height: 26px;
          padding: 4px 7px;
        }
        .main .shop-stock,
        .main .shop-missing {
          font-size: 10px;
          line-height: 1.25;
        }
        .mart-confirm-card {
          margin: 12px 0;
          padding: 12px;
          border-left: 4px solid var(--accent);
        }
        .mart-confirm-title {
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
        }
        .mart-confirm-line {
          margin-top: 8px;
          color: var(--bw2-text);
          font-family: var(--font-ui);
          font-size: 20px;
          line-height: 1.15;
        }
        .mart-confirm-price {
          color: #ffe08b;
          font-family: var(--font-pixel);
          font-size: 13px;
        }

        @media (max-width: 980px) {
          .mart-hero,
          .mart-register-grid,
          .mart-aisle-head {
            grid-template-columns: 1fr;
          }
          .mart-hero-right {
            min-width: 0;
          }
          .mart-aisle-meta {
            justify-content: flex-start;
          }
        }
        @media (max-width: 560px) {
          .shop-body {
            grid-template-columns: 64px minmax(0, 1fr);
          }
          .shop-icon-slot {
            width: 64px;
            height: 64px;
          }
          .shop-icon {
            width: 50px;
            height: 50px;
          }
          .mart-title {
            font-size: 20px;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
