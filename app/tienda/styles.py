from __future__ import annotations

import streamlit as st


def render_shop_styles() -> None:
    st.markdown(
        """
        <style>
        .main .stButton > button,
        .main .stButton > button * {
          font-family: var(--font-pixel) !important;
          font-size: 11px !important;
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
          font-size: 11px !important;
          font-weight: 700 !important;
        }
        .main div[data-testid="stTabs"] div[data-baseweb="tab-list"],
        .main div[data-testid="stTabs"] [role="tablist"] {
          gap: 10px !important;
          flex-wrap: wrap !important;
          align-items: stretch !important;
          padding: 8px;
          border: 1px solid rgba(216,223,232,0.16);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.05), transparent 58%),
            linear-gradient(180deg, rgba(29,37,48,0.96) 0%, rgba(13,18,25,0.96) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 6px 18px rgba(0,0,0,0.2);
        }
        .main div[data-testid="stTabs"] button[data-baseweb="tab"],
        .main div[data-testid="stTabs"] button[role="tab"] {
          flex: 1 1 170px !important;
          width: auto !important;
          min-width: 158px !important;
          justify-content: center !important;
          min-height: 50px !important;
          padding-left: 18px !important;
          padding-right: 18px !important;
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
        .mart-aisle-note {
          margin-top: 6px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 17px;
          line-height: 1.15;
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
          min-height: 244px;
          margin-bottom: 10px;
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
          gap: 10px;
          min-height: 48px;
          padding: 10px 12px 9px;
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
          gap: 12px;
          padding: 12px 12px 14px;
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
          gap: 10px;
        }
        .shop-desc {
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1.12;
          overflow-wrap: anywhere;
        }
        .shop-price {
          display: grid;
          gap: 7px;
          width: 100%;
          max-width: 100%;
          box-sizing: border-box;
          padding: 8px 10px;
          border: 1px solid rgba(255,255,255,0.14);
          background: linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.03) 100%);
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 12px;
          line-height: 1.2;
        }
        .shop-price-row,
        .shop-price-flow {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
          min-width: 0;
        }
        .shop-price-flow {
          gap: 6px;
        }
        .shop-coin-value {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          min-height: 32px;
          min-width: 58px;
          padding: 5px 8px;
          border: 1px solid rgba(255,255,255,0.2);
          background:
            linear-gradient(180deg, rgba(255,255,255,0.12), rgba(255,255,255,0.03)),
            rgba(7, 11, 17, 0.46);
          color: #ffffff;
          box-sizing: border-box;
        }
        .shop-coin {
          font-family: "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif;
          font-size: 18px;
          line-height: 1;
        }
        .shop-amount {
          font-family: var(--font-pixel);
          font-size: 15px;
          line-height: 1;
        }
        .shop-main-price {
          border-color: rgba(255, 220, 120, 0.52);
          background:
            linear-gradient(180deg, rgba(255,217,126,0.16), rgba(255,217,126,0.04)),
            rgba(12, 15, 20, 0.58);
          color: #ffffff;
        }
        .shop-future-price {
          border-color: rgba(143, 215, 255, 0.5);
          color: #8fd7ff;
        }
        .shop-discount-badge {
          display: inline-flex;
          align-items: center;
          min-height: 30px;
          padding: 5px 8px;
          border: 1px solid rgba(255,255,255,0.24);
          background: linear-gradient(180deg, #f26f3d 0%, #8d2f20 100%);
          color: #ffffff;
          line-height: 1.1;
        }
        .shop-discount-badge.is-pending {
          border-color: rgba(117, 203, 255, 0.65);
          background: linear-gradient(180deg, #347fa8 0%, #1c4e70 100%);
        }
        .shop-discount-badge.is-used {
          border-color: rgba(255,255,255,0.16);
          background: linear-gradient(180deg, #5a626d 0%, #343a42 100%);
        }
        .shop-card.is-pending-sale {
          border-color: rgba(94, 188, 242, 0.62);
          box-shadow: inset 3px 0 0 #4db9f2;
        }
        .shop-card.is-delivery-locked {
          background:
            repeating-linear-gradient(
              -45deg,
              rgba(71, 151, 196, 0.05) 0,
              rgba(71, 151, 196, 0.05) 8px,
              transparent 8px,
              transparent 16px
            ),
            linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
        }
        .shop-old-price {
          color: #c6ccd4;
          text-decoration: line-through;
          text-decoration-thickness: 2px;
        }
        .shop-arrow {
          color: #f6c15b;
          font-size: 14px;
        }
        .shop-stock,
        .shop-missing {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
          width: 100%;
          font-family: var(--font-pixel);
          font-size: 11px;
          line-height: 1.2;
        }
        .shop-stock {
          color: var(--bw2-text-soft);
        }
        .shop-missing {
          width: fit-content;
          max-width: 100%;
          margin-top: -2px;
          padding: 7px 9px;
          border: 1px solid rgba(242, 107, 97, 0.32);
          background: rgba(95, 28, 28, 0.22);
          color: #ffaba7;
        }
        .shop-missing-label {
          text-transform: uppercase;
        }
        .shop-missing-price {
          min-height: 28px;
          min-width: 48px;
          padding: 4px 7px;
          border-color: rgba(255, 171, 167, 0.42);
        }
        .main .shop-price {
          gap: 8px;
          padding: 9px 11px;
          font-size: 13px;
          line-height: 1.2;
        }
        .main .shop-discount-badge {
          min-height: 31px;
          padding: 5px 9px;
        }
        .main .shop-stock,
        .main .shop-missing {
          font-size: 11px;
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

        div[data-testid="stTabs"] div[data-baseweb="tab-list"],
        div[data-testid="stTabs"] [role="tablist"] {
          display: flex !important;
          gap: 10px !important;
          flex-wrap: wrap !important;
          align-items: stretch !important;
          width: 100% !important;
          padding: 8px !important;
        }
        div[data-testid="stTabs"] button[data-baseweb="tab"],
        div[data-testid="stTabs"] button[role="tab"] {
          flex: 1 1 170px !important;
          width: auto !important;
          min-width: 158px !important;
          max-width: none !important;
          min-height: 50px !important;
          padding: 0 18px !important;
        }
        div[data-testid="stTabs"] button[data-baseweb="tab"] *,
        div[data-testid="stTabs"] button[role="tab"] * {
          width: 100% !important;
          font-size: 11px !important;
          line-height: 1.2 !important;
          text-align: center !important;
          white-space: nowrap !important;
        }
        .main .shop-price,
        .shop-price {
          display: grid !important;
          gap: 8px !important;
          padding: 9px 11px !important;
          font-size: 13px !important;
          line-height: 1.2 !important;
          width: 100% !important;
          max-width: 100% !important;
        }
        .main .shop-price-row,
        .shop-price-row,
        .main .shop-price-flow,
        .shop-price-flow {
          display: flex !important;
          align-items: center !important;
          flex-wrap: wrap !important;
          gap: 8px !important;
        }
        .main .shop-coin,
        .shop-coin {
          font-size: 18px !important;
          line-height: 1 !important;
        }
        .main .shop-amount,
        .shop-amount {
          font-size: 15px !important;
          line-height: 1 !important;
        }
        .main .shop-discount-badge,
        .shop-discount-badge {
          min-height: 31px !important;
          padding: 5px 9px !important;
          font-size: 12px !important;
        }
        .main .shop-stock,
        .main .shop-missing,
        .shop-stock,
        .shop-missing {
          margin-top: 4px !important;
          font-size: 12px !important;
          line-height: 1.25 !important;
        }

        /* Phase 1B: final Poke Mart visual reference. */
        .main .mart-hero,
        .mart-hero {
          min-height: 92px !important;
          grid-template-columns: minmax(0, 1fr) auto !important;
          gap: 14px !important;
          align-items: center !important;
          margin-bottom: 10px !important;
          padding: 14px 16px !important;
          border: 1px solid rgba(139,171,216,0.18) !important;
          border-radius: 14px !important;
          clip-path: none !important;
          background:
            linear-gradient(135deg, rgba(255,189,92,0.11), transparent 36%),
            linear-gradient(180deg, rgba(18,30,49,0.96), rgba(8,14,26,0.98)) !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 14px 28px rgba(0,0,0,0.22) !important;
        }

        .main .mart-hero::before,
        .mart-hero::before {
          opacity: 0.18 !important;
        }

        .main .mart-title,
        .mart-title {
          margin-top: 7px !important;
          color: var(--text-primary, #f6f9ff) !important;
          -webkit-text-fill-color: var(--text-primary, #f6f9ff) !important;
          font-size: clamp(24px, 2.2vw, 30px) !important;
          line-height: 1.04 !important;
          text-shadow: none !important;
        }

        .main .mart-kicker,
        .mart-kicker {
          padding: 4px 8px !important;
          border: 1px solid rgba(255,189,92,0.22) !important;
          border-left: 3px solid var(--accent, #ffbd5c) !important;
          border-radius: 8px !important;
          background: rgba(255,189,92,0.08) !important;
          color: var(--text-secondary, #b8c7dc) !important;
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc) !important;
          letter-spacing: 0 !important;
        }

        .main .mart-hero-right,
        .mart-hero-right {
          min-width: 164px !important;
          padding: 0 !important;
          border: 0 !important;
          background: transparent !important;
        }

        .mart-balance-card {
          min-width: 164px;
          padding: 10px 12px;
          border: 1px solid rgba(255,210,109,0.26);
          border-radius: 12px;
          background:
            radial-gradient(circle at 100% 0%, rgba(255,210,109,0.13), transparent 54%),
            rgba(255,255,255,0.035);
        }

        .mart-balance-card span {
          display: block;
          color: var(--text-muted, #77879e);
          -webkit-text-fill-color: var(--text-muted, #77879e);
          font-family: var(--font-pixel);
          font-size: 9px;
          font-weight: 900;
          text-transform: uppercase;
        }

        .mart-balance-card strong {
          display: block;
          margin-top: 4px;
          color: var(--pokemon-yellow, #ffd24d);
          -webkit-text-fill-color: var(--pokemon-yellow, #ffd24d);
          font-family: var(--font-pixel);
          font-size: 22px;
          line-height: 1;
          font-variant-numeric: tabular-nums;
        }

        .main .mart-register-grid,
        .mart-register-grid {
          grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
          gap: 8px !important;
          margin: 10px 0 12px !important;
        }

        .main .mart-register-card,
        .mart-register-card {
          min-height: 58px !important;
          padding: 9px 10px !important;
          border: 1px solid rgba(139,171,216,0.13) !important;
          border-radius: 12px !important;
          background: rgba(255,255,255,0.032) !important;
          box-shadow: none !important;
        }

        .main .mart-register-card.is-main,
        .mart-register-card.is-main {
          border-color: rgba(255,210,109,0.3) !important;
          background:
            radial-gradient(circle at 100% 0%, rgba(255,210,109,0.12), transparent 56%),
            rgba(255,255,255,0.04) !important;
          box-shadow: inset 3px 0 0 var(--pokemon-yellow, #ffd24d) !important;
        }

        .main .mart-label,
        .mart-label {
          color: var(--text-muted, #77879e) !important;
          -webkit-text-fill-color: var(--text-muted, #77879e) !important;
          font-size: 9px !important;
          letter-spacing: 0 !important;
        }

        .main .mart-value,
        .mart-value {
          margin-top: 5px !important;
          color: var(--text-primary, #f6f9ff) !important;
          -webkit-text-fill-color: var(--text-primary, #f6f9ff) !important;
          font-size: 16px !important;
          font-variant-numeric: tabular-nums !important;
        }

        .main .mart-register-card.is-main .mart-value,
        .mart-register-card.is-main .mart-value {
          color: var(--pokemon-yellow, #ffd24d) !important;
          -webkit-text-fill-color: var(--pokemon-yellow, #ffd24d) !important;
          font-size: 20px !important;
        }

        .main div[data-testid="stTabs"] [role="tablist"],
        div[data-testid="stTabs"] [role="tablist"] {
          gap: 8px !important;
          padding: 0 0 10px !important;
          border: 0 !important;
          border-bottom: 1px solid rgba(215,230,255,0.08) !important;
          background: transparent !important;
          box-shadow: none !important;
        }

        .main div[data-testid="stTabs"] button[role="tab"],
        div[data-testid="stTabs"] button[role="tab"] {
          flex: 0 1 auto !important;
          min-width: 132px !important;
          min-height: 38px !important;
          padding: 0 14px !important;
          border: 1px solid rgba(215,230,255,0.08) !important;
          border-radius: 10px !important;
          clip-path: none !important;
          background: rgba(255,255,255,0.035) !important;
        }

        .main div[data-testid="stTabs"] button[aria-selected="true"],
        div[data-testid="stTabs"] button[aria-selected="true"] {
          border-color: rgba(255,189,92,0.48) !important;
          background:
            linear-gradient(180deg, rgba(255,189,92,0.18), rgba(255,189,92,0.08)),
            rgba(15,25,42,0.96) !important;
          box-shadow: inset 0 -2px 0 var(--accent, #ffbd5c) !important;
        }

        .main .mart-aisle-head,
        .mart-aisle-head {
          margin: 12px 0 10px !important;
          padding: 10px 12px !important;
          border: 1px solid rgba(139,171,216,0.14) !important;
          border-radius: 12px !important;
          background: rgba(255,255,255,0.03) !important;
          box-shadow: none !important;
        }

        .main .mart-aisle-title,
        .mart-aisle-title {
          margin: 0 !important;
          color: var(--text-primary, #f6f9ff) !important;
          -webkit-text-fill-color: var(--text-primary, #f6f9ff) !important;
          font-size: 15px !important;
          line-height: 1.1 !important;
          text-shadow: none !important;
        }

        .main .shop-card,
        .shop-card {
          min-height: 196px !important;
          margin-bottom: 6px !important;
          border: 1px solid rgba(139,171,216,0.15) !important;
          border-radius: 14px !important;
          background:
            radial-gradient(circle at 18% 22%, rgba(255,189,92,0.09), transparent 44%),
            linear-gradient(180deg, rgba(18,30,49,0.96), rgba(10,17,29,0.98)) !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 10px 22px rgba(0,0,0,0.18) !important;
        }

        .main .shop-card:hover,
        .shop-card:hover {
          border-color: rgba(255,189,92,0.28) !important;
          transform: translateY(-1px);
        }

        .main .shop-card::before,
        .shop-card::before {
          display: none !important;
        }

        .main .shop-card.is-sale,
        .shop-card.is-sale {
          border-color: rgba(255,210,109,0.45) !important;
          box-shadow: inset 3px 0 0 var(--pokemon-yellow, #ffd24d), 0 10px 22px rgba(0,0,0,0.2) !important;
        }

        .main .shop-card.is-pending-sale,
        .shop-card.is-pending-sale {
          border-color: rgba(69,209,255,0.36) !important;
          box-shadow: inset 3px 0 0 var(--info, #45d1ff), 0 10px 22px rgba(0,0,0,0.18) !important;
        }

        .main .shop-card.is-delivery-locked,
        .shop-card.is-delivery-locked {
          opacity: 0.82 !important;
        }

        .main .shop-head,
        .shop-head {
          min-height: 48px !important;
          display: flex !important;
          align-items: flex-start !important;
          justify-content: space-between !important;
          gap: 10px !important;
          padding: 10px 11px 8px !important;
          border-bottom: 1px solid rgba(215,230,255,0.08) !important;
          background: rgba(6,12,22,0.54) !important;
        }

        .shop-title-block {
          min-width: 0;
          display: grid;
          gap: 5px;
        }

        .main .shop-name,
        .shop-name {
          color: var(--text-primary, #f6f9ff) !important;
          -webkit-text-fill-color: var(--text-primary, #f6f9ff) !important;
          font-size: 12px !important;
          font-weight: 950 !important;
          line-height: 1.14 !important;
        }

        .shop-category-badge,
        .shop-state-badge,
        .shop-discount-badge {
          display: inline-flex;
          width: fit-content;
          max-width: 100%;
          align-items: center;
          min-height: 22px;
          padding: 3px 7px;
          border: 1px solid rgba(139,171,216,0.16);
          border-radius: 999px;
          background: rgba(255,255,255,0.04);
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-family: var(--font-pixel);
          font-size: 9px;
          font-weight: 900;
          line-height: 1;
          text-transform: uppercase;
          white-space: nowrap;
        }

        .shop-state-row {
          flex: 0 0 auto;
          display: flex;
          justify-content: flex-end;
        }

        .shop-state-badge.is-sale,
        .shop-discount-badge {
          border-color: rgba(255,210,109,0.35) !important;
          background: rgba(255,210,109,0.1) !important;
          color: var(--pokemon-yellow, #ffd24d) !important;
          -webkit-text-fill-color: var(--pokemon-yellow, #ffd24d) !important;
        }

        .shop-state-badge.is-locked,
        .shop-discount-badge.is-pending {
          border-color: rgba(69,209,255,0.3) !important;
          background: rgba(69,209,255,0.085) !important;
          color: #8fdcff !important;
          -webkit-text-fill-color: #8fdcff !important;
        }

        .shop-state-badge.is-poor,
        .shop-state-badge.is-used,
        .shop-discount-badge.is-used {
          border-color: rgba(139,171,216,0.15) !important;
          background: rgba(255,255,255,0.035) !important;
          color: var(--text-muted, #77879e) !important;
          -webkit-text-fill-color: var(--text-muted, #77879e) !important;
        }

        .main .shop-body,
        .shop-body {
          display: grid !important;
          grid-template-columns: 74px minmax(0, 1fr) !important;
          gap: 12px !important;
          padding: 12px 11px 13px !important;
        }

        .main .shop-icon-slot,
        .shop-icon-slot {
          width: 72px !important;
          height: 72px !important;
          border: 1px solid rgba(139,171,216,0.14) !important;
          border-radius: 12px !important;
          background:
            radial-gradient(circle at 50% 42%, rgba(255,210,109,0.11), transparent 54%),
            rgba(255,255,255,0.032) !important;
        }

        .main .shop-icon,
        .shop-icon {
          width: 58px !important;
          height: 58px !important;
          max-width: 58px !important;
          max-height: 58px !important;
          object-fit: contain !important;
          filter: drop-shadow(0 5px 7px rgba(0,0,0,0.35)) !important;
        }

        .main .shop-info,
        .shop-info {
          min-width: 0 !important;
          display: grid !important;
          align-content: start !important;
          gap: 8px !important;
        }

        .main .shop-desc,
        .shop-desc {
          color: var(--text-secondary, #b8c7dc) !important;
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc) !important;
          font-size: 13px !important;
          line-height: 1.28 !important;
        }

        .main .shop-price,
        .shop-price {
          display: grid !important;
          gap: 6px !important;
          padding: 0 !important;
          border: 0 !important;
          border-radius: 0 !important;
          background: transparent !important;
        }

        .main .shop-price-row,
        .shop-price-row,
        .main .shop-price-flow,
        .shop-price-flow {
          gap: 6px !important;
        }

        .main .shop-coin-value,
        .shop-coin-value {
          min-height: 30px !important;
          min-width: 60px !important;
          padding: 4px 8px !important;
          border: 1px solid rgba(255,210,109,0.26) !important;
          border-radius: 9px !important;
          background: rgba(255,210,109,0.08) !important;
          color: var(--pokemon-yellow, #ffd24d) !important;
          -webkit-text-fill-color: var(--pokemon-yellow, #ffd24d) !important;
        }

        .main .shop-old-price,
        .shop-old-price {
          opacity: 0.7 !important;
          border-color: rgba(139,171,216,0.14) !important;
          background: rgba(255,255,255,0.025) !important;
          color: var(--text-muted, #77879e) !important;
          -webkit-text-fill-color: var(--text-muted, #77879e) !important;
        }

        .main .shop-coin,
        .shop-coin {
          font-size: 18px !important;
        }

        .main .shop-amount,
        .shop-amount {
          color: inherit !important;
          -webkit-text-fill-color: currentColor !important;
          font-size: 17px !important;
          font-weight: 950 !important;
          font-variant-numeric: tabular-nums !important;
        }

        .main .shop-stock,
        .shop-stock {
          color: var(--text-secondary, #b8c7dc) !important;
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc) !important;
          font-size: 11px !important;
          font-weight: 800 !important;
        }

        .main .shop-missing,
        .shop-missing {
          width: fit-content !important;
          margin-top: 0 !important;
          padding: 5px 7px !important;
          border: 1px solid rgba(255,82,99,0.24) !important;
          border-radius: 9px !important;
          background: rgba(255,82,99,0.075) !important;
          color: #ffb3bd !important;
          -webkit-text-fill-color: #ffb3bd !important;
        }

        div[data-testid="column"]:has(.shop-card) .stButton {
          display: flex !important;
          justify-content: flex-end !important;
          margin: -2px 0 12px !important;
        }

        div[data-testid="column"]:has(.shop-card) .stButton > button {
          width: auto !important;
          min-width: 104px !important;
          min-height: 32px !important;
          padding: 0 13px !important;
          border-radius: 10px !important;
          border-color: rgba(77,141,255,0.42) !important;
          background: linear-gradient(180deg, #5aa6ff, #2f6fff) !important;
          box-shadow: none !important;
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
          white-space: nowrap !important;
        }

        @media (max-width: 980px) {
          .main .mart-register-grid,
          .mart-register-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
          }
        }

        @media (max-width: 640px) {
          .main .mart-hero,
          .mart-hero {
            grid-template-columns: 1fr !important;
          }
          .mart-balance-card {
            min-width: 0;
          }
          .main .mart-register-grid,
          .mart-register-grid {
            grid-template-columns: 1fr !important;
          }
          .main .shop-body,
          .shop-body {
            grid-template-columns: 64px minmax(0, 1fr) !important;
          }
          .main .shop-icon-slot,
          .shop-icon-slot {
            width: 62px !important;
            height: 62px !important;
          }
          .main .shop-icon,
          .shop-icon {
            width: 50px !important;
            height: 50px !important;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
