from __future__ import annotations

import streamlit as st


def ensure_league_css() -> None:
    st.markdown(
        """
        <style>
        .league-hero {
          position: relative;
          overflow: hidden;
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(270px, 0.65fr);
          gap: 14px;
          align-items: stretch;
          min-height: 112px;
          margin-bottom: 14px;
          padding: 14px;
          border: 1px solid var(--bw2-edge);
          background:
            linear-gradient(118deg, rgba(245,139,60,0.18) 0 32%, transparent 32% 100%),
            linear-gradient(180deg, rgba(43,52,64,0.97) 0%, rgba(16,22,30,0.97) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.09), 0 10px 26px rgba(0,0,0,0.24);
        }
        .league-hero::before,
        .league-division-card::before,
        .league-history-card::before {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background:
            linear-gradient(180deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 100%) 0 0 / 100% 22px,
            linear-gradient(90deg, rgba(255,255,255,0.035) 0 1px, transparent 1px 100%) 0 0 / 26px 100%;
          opacity: .48;
        }
        .league-hero-main,
        .league-hero-grid,
        .league-division-card > *,
        .league-history-card > * {
          position: relative;
          z-index: 1;
        }
        .league-kicker,
        .league-title,
        .league-status-card span,
        .league-status-card strong,
        .league-section-title,
        .league-division-name,
        .league-card-pos,
        .league-card-player-name,
        .league-movement-badge,
        .league-history-title {
          font-family: var(--font-pixel);
          text-transform: uppercase;
        }
        .league-kicker {
          display: inline-block;
          padding: 5px 8px;
          border-left: 3px solid var(--accent);
          background: rgba(0,0,0,0.28);
          color: var(--bw2-text-soft);
          font-size: 9px;
        }
        .league-title {
          margin-top: 9px;
          color: #ffffff;
          font-size: 26px;
          line-height: 1.05;
          text-shadow: 0 2px 0 rgba(0,0,0,0.5);
        }
        .league-subtitle {
          margin-top: 10px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 20px;
          line-height: 1.16;
        }
        .league-hero-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 8px;
        }
        .league-status-card {
          min-width: 0;
          min-height: 54px;
          padding: 8px 10px;
          border: 1px solid rgba(216,223,232,0.16);
          background: linear-gradient(180deg, rgba(9,15,22,0.64), rgba(8,12,18,0.88));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }
        .league-status-card span {
          display: block;
          color: var(--bw2-text-soft);
          font-size: 8px;
          line-height: 1.15;
        }
        .league-status-card strong {
          display: block;
          margin-top: 6px;
          color: #ffffff;
          font-size: 12px;
          line-height: 1.15;
          overflow-wrap: anywhere;
        }
        .league-status-card.is-live strong {
          color: #ffe2de;
        }
        .league-section-title {
          margin: 16px 0 8px;
          padding: 8px 10px;
          border-left: 4px solid var(--accent);
          background: linear-gradient(90deg, rgba(255,255,255,0.07), transparent 64%);
          color: #ffffff;
          font-size: 11px;
          line-height: 1.2;
        }
        .league-section-sub {
          margin: -4px 0 10px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1.15;
        }
        .league-division-grid,
        .league-history-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
          margin-bottom: 12px;
        }
        .league-division-card,
        .league-history-card {
          position: relative;
          overflow: hidden;
          min-width: 0;
          border: 1px solid var(--bw2-edge);
          background:
            linear-gradient(112deg, rgba(245,139,60,0.12) 0 35%, transparent 35% 100%),
            linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
          padding: 10px;
        }
        .league-division-card.is-b,
        .league-history-card.is-b {
          background:
            linear-gradient(112deg, rgba(111,168,255,0.12) 0 35%, transparent 35% 100%),
            linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
        }
        .league-division-head,
        .league-history-title {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          padding-bottom: 8px;
          border-bottom: 1px solid rgba(216,223,232,0.14);
        }
        .league-division-name,
        .league-history-title {
          color: #ffffff;
          font-size: 10px;
          line-height: 1.2;
        }
        .league-history-title {
          margin: 12px 0 8px;
          padding: 8px 10px;
          border: 1px solid rgba(216,223,232,0.18);
          border-left: 4px solid var(--accent);
          background: linear-gradient(90deg, rgba(255,255,255,0.07), transparent 64%);
        }
        .league-division-range {
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1;
          white-space: nowrap;
        }
        .league-card-list {
          display: grid;
          gap: 6px;
          margin-top: 8px;
        }
        .league-card-player {
          display: grid;
          grid-template-columns: 38px minmax(0, 1fr) auto auto auto;
          gap: 8px;
          align-items: center;
          min-height: 36px;
          padding: 7px 8px;
          border: 1px solid rgba(216,223,232,0.13);
          background: rgba(8,12,18,0.48);
        }
        .league-card-pos {
          color: var(--bw2-text-soft);
          font-size: 9px;
          text-align: right;
        }
        .league-card-player-name {
          min-width: 0;
          color: #ffffff;
          font-size: 10px;
          line-height: 1.2;
          overflow-wrap: anywhere;
        }
        .league-card-main {
          min-width: 0;
          display: grid;
          gap: 4px;
        }
        .league-card-score,
        .league-card-coins {
          display: grid;
          justify-items: end;
          min-width: 54px;
          font-family: var(--font-ui);
          line-height: 1;
        }
        .league-card-score strong,
        .league-card-coins strong {
          color: #fff;
          font-size: 18px;
          font-weight: 900;
        }
        .league-card-score span,
        .league-card-coins span {
          margin-top: 3px;
          color: var(--bw2-text-dim);
          font-size: 10px;
          font-weight: 800;
          text-transform: uppercase;
        }
        .league-card-coins strong {
          color: #fff4bd;
        }
        .league-trainer-badges {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          flex-wrap: wrap;
        }
        .league-trainer-badge {
          display: inline-flex;
          align-items: center;
          min-height: 20px;
          padding: 2px 7px 3px;
          border: 1px solid rgba(255,255,255,0.18);
          border-radius: 999px;
          color: #fff;
          font-size: 9px;
          font-weight: 900;
          line-height: 1;
          text-transform: uppercase;
        }
        .league-trainer-badge--robado {
          border-color: rgba(255,97,114,0.48);
          background: rgba(255,97,114,0.16);
          color: #ffd2d8;
        }
        .league-trainer-badge--retirado {
          border-color: rgba(179,189,205,0.3);
          background: rgba(179,189,205,0.12);
          color: var(--bw2-text-soft);
        }
        .league-card-player.is-current-player {
          border-color: rgba(69, 209, 255, 0.42);
          background:
            linear-gradient(90deg, rgba(69,209,255,0.14), transparent 56%),
            rgba(8,12,18,0.55);
          box-shadow: inset 3px 0 0 var(--accent);
        }
        .league-card-player.is-retired-player {
          opacity: .72;
        }
        .league-card-player.is-history-row {
          grid-template-columns: 38px minmax(0, 1fr) auto;
        }
        .league-movement-badge {
          min-width: 48px;
          padding: 4px 7px;
          border: 1px solid rgba(255,255,255,0.2);
          color: #ffffff;
          font-size: 8px;
          line-height: 1;
          text-align: center;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.18);
        }
        .league-movement-badge--up {
          background: linear-gradient(180deg, #49c982 0%, #267b50 100%);
        }
        .league-movement-badge--down {
          background: linear-gradient(180deg, #e05f67 0%, #8f2e36 100%);
        }
        .league-card-empty {
          padding: 12px;
          border: 1px dashed rgba(216,223,232,0.24);
          color: var(--bw2-text-dim);
          font-family: var(--font-ui);
          font-size: 18px;
          text-align: center;
        }
        @media (max-width: 980px) {
          .league-hero,
          .league-division-grid,
          .league-history-grid {
            grid-template-columns: 1fr;
          }
        }
        @media (max-width: 620px) {
          .league-hero {
            padding: 12px;
          }
          .league-title {
            font-size: 24px;
          }
          .league-hero-grid {
            grid-template-columns: 1fr;
          }
          .league-card-player {
            grid-template-columns: 32px minmax(0, 1fr) auto auto;
          }
          .league-card-score,
          .league-card-coins {
            min-width: 44px;
          }
          .league-movement-badge {
            grid-column: 2;
            justify-self: start;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
