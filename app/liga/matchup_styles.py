from __future__ import annotations

import streamlit as st


def ensure_matchup_css() -> None:
    st.markdown(
        """
        <style>
        .matchup-shell {
          display: inline-block;
          padding: 8px 10px;
          border: 1px solid var(--bw2-edge-strong);
          background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
          clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
          margin-bottom: 10px;
        }
        .matchup-note {
          margin-bottom: 12px;
          padding: 10px 12px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 20px;
          line-height: 1.2;
        }
        .matchup-summary {
          margin-bottom: 12px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
          padding: 12px;
        }
        .matchup-summary-head {
          display: grid;
          grid-template-columns: 116px 1fr;
          gap: 12px;
          align-items: center;
        }
        .matchup-avatar {
          width: 116px;
          height: 116px;
          display: flex;
          align-items: center;
          justify-content: center;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
          overflow: hidden;
        }
        .matchup-avatar img {
          width: 100%;
          height: 100%;
          object-fit: contain;
          image-rendering: pixelated;
        }
        .matchup-avatar-fallback {
          color: var(--bw2-text-dim);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-align: center;
          line-height: 1.6;
        }
        .matchup-player {
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 13px;
          text-transform: uppercase;
        }
        .matchup-division,
        .matchup-save {
          margin-top: 8px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 19px;
          line-height: 1.1;
        }
        .matchup-status-row {
          margin-top: 10px;
        }
        .matchup-ok,
        .matchup-alert {
          display: inline-block;
          padding: 4px 8px;
          border: 1px solid var(--bw2-edge);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        .matchup-ok {
          background: linear-gradient(180deg, #58d18e 0%, #2a8d5c 100%);
          color: #ffffff;
        }
        .matchup-alert {
          background: linear-gradient(180deg, #ef5e68 0%, #962d37 100%);
          color: #ffffff;
        }
        .matchup-metric-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 8px;
          margin-top: 12px;
        }
        .matchup-metric {
          padding: 8px 10px;
          border: 1px solid rgba(255,255,255,0.08);
          background: linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
        }
        .matchup-metric span {
          display: block;
          color: var(--bw2-text-soft);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        .matchup-metric strong {
          display: block;
          margin-top: 7px;
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 12px;
        }
        .matchup-team-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
        }
        .matchup-mon {
          min-height: 230px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
          padding: 10px;
        }
        .matchup-mon-empty {
          display: flex;
          flex-direction: column;
          justify-content: center;
          text-align: center;
        }
        .matchup-mon-head {
          display: grid;
          grid-template-columns: 82px 1fr;
          gap: 10px;
          align-items: center;
        }
        .matchup-sprite {
          width: 82px;
          height: 82px;
          object-fit: contain;
          image-rendering: pixelated;
          filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
        }
        .matchup-mon-title {
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
          line-height: 1.45;
        }
        .matchup-mon-sub,
        .matchup-mon-extra {
          margin-top: 6px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1.05;
        }
        .matchup-mon-item {
          overflow-wrap: anywhere;
        }
        .matchup-move-list {
          display: grid;
          gap: 6px;
          margin-top: 10px;
        }
        .matchup-move {
          display: flex;
          align-items: center;
          gap: 7px;
          padding: 7px 8px;
          border: 1px solid rgba(255,255,255,0.08);
          background: linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
          color: #ffffff;
          font-family: var(--font-ui);
          font-size: 19px;
          line-height: 1.05;
        }
        .matchup-move span:last-child {
          color: #ffffff;
          overflow-wrap: anywhere;
        }
        .matchup-versus {
          margin-bottom: 12px;
          padding: 10px 12px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
        }
        .matchup-versus strong {
          font-size: 12px;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] {
          gap: 8px;
          margin-bottom: 12px;
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label {
          min-height: 38px;
          padding: 8px 12px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label:has(input:checked) {
          border-color: var(--bw2-edge-strong);
          background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
        }
        div[data-testid="stRadio"] div[role="radiogroup"] label p {
          color: #ffffff !important;
          font-family: var(--font-pixel) !important;
          font-size: 10px !important;
          text-transform: uppercase;
        }
        .battle-type-dot {
          width: 22px;
          height: 22px;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          flex: 0 0 22px;
          border-radius: 50%;
          border: 1px solid rgba(255,255,255,0.55);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.35), 0 1px 3px rgba(0,0,0,0.35);
          font-family: var(--font-pixel);
          font-size: 7px;
          line-height: 1;
          text-transform: uppercase;
        }
        .battle-board {
          margin-top: 8px;
          border: 1px solid var(--bw2-edge);
          background:
            linear-gradient(120deg, rgba(121,185,245,0.08) 0 24%, transparent 24% 100%),
            linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.07), 0 0 0 1px rgba(0,0,0,0.35);
          padding: 10px;
        }
        .battle-board-top {
          display: grid;
          grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
          gap: 10px;
          margin-bottom: 10px;
        }
        .battle-board-top div {
          min-width: 0;
          padding: 8px 10px;
          border-left: 3px solid var(--accent);
          background: rgba(0,0,0,0.22);
        }
        .battle-board-top span,
        .battle-detail-kicker {
          display: block;
          color: var(--bw2-text-soft);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        .battle-board-top strong {
          display: block;
          margin-top: 4px;
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 12px;
          overflow-wrap: anywhere;
          text-transform: uppercase;
        }
        .battle-team-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
        }
        .battle-mon-card {
          position: relative;
          min-height: 166px;
          display: grid;
          grid-template-columns: minmax(126px, .95fr) 88px minmax(168px, 1.15fr);
          gap: 8px;
          align-items: center;
          overflow: hidden;
          border: 1px solid rgba(178,219,255,0.34);
          background:
            linear-gradient(110deg, rgba(63,152,210,0.18) 0 38%, transparent 38% 100%),
            linear-gradient(180deg, rgba(37,71,103,0.92) 0%, rgba(19,43,62,0.92) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.13), 0 5px 14px rgba(0,0,0,0.25);
          padding: 10px;
        }
        .battle-mon-card::before {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background:
            linear-gradient(180deg, rgba(255,255,255,0.06) 0 1px, transparent 1px 100%) 0 0 / 100% 18px,
            linear-gradient(90deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 100%) 0 0 / 24px 100%;
          opacity: .55;
        }
        .battle-empty-card {
          display: flex;
          flex-direction: column;
          justify-content: center;
          min-height: 128px;
          background: linear-gradient(180deg, rgba(38,45,55,0.86) 0%, rgba(21,25,32,0.86) 100%);
        }
        .battle-slot-mark {
          position: absolute;
          right: 12px;
          bottom: 0;
          color: rgba(255,255,255,0.13);
          font-family: var(--font-pixel);
          font-size: 42px;
          line-height: 1;
        }
        .battle-card-left,
        .battle-sprite-wrap,
        .battle-moves,
        .battle-empty-title,
        .battle-empty-sub {
          position: relative;
          z-index: 1;
        }
        .battle-name-row {
          display: flex;
          align-items: center;
          gap: 7px;
          min-width: 0;
        }
        .battle-mon-name {
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 11px;
          line-height: 1.3;
          text-transform: uppercase;
          overflow-wrap: anywhere;
        }
        .battle-types {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          flex-wrap: wrap;
        }
        .battle-species,
        .battle-level,
        .battle-item,
        .battle-empty-sub {
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1.08;
        }
        .battle-species,
        .battle-level,
        .battle-item {
          margin-top: 7px;
        }
        .battle-item {
          overflow-wrap: anywhere;
        }
        .battle-private-info {
          display: grid;
          gap: 6px;
          margin-top: 9px;
        }
        .battle-ability-row,
        .battle-private-line,
        .battle-ivs {
          min-width: 0;
          border: 1px solid rgba(255,255,255,0.13);
          background: rgba(9,15,22,0.44);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
        }
        .battle-ability-row > summary,
        .battle-private-line,
        .battle-ivs {
          padding: 6px 7px;
        }
        .battle-ability-row > summary {
          cursor: pointer;
          list-style: none;
        }
        .battle-ability-row > summary::-webkit-details-marker {
          display: none;
        }
        .battle-ability-row span,
        .battle-private-line span,
        .battle-ivs > span,
        .battle-iv span {
          display: block;
          color: var(--bw2-text-soft);
          font-family: var(--font-pixel);
          font-size: 8px;
          line-height: 1.15;
          text-transform: uppercase;
        }
        .battle-ability-row strong,
        .battle-private-line strong,
        .battle-iv strong {
          display: block;
          margin-top: 4px;
          color: #ffffff;
          font-family: var(--font-ui);
          font-size: 17px;
          line-height: 1.05;
          overflow-wrap: anywhere;
        }
        .battle-ability-row[open] {
          border-color: var(--accent-soft);
        }
        .battle-ability-desc {
          padding: 0 7px 7px;
          color: var(--bw2-text);
          font-family: var(--font-ui);
          font-size: 17px;
          line-height: 1.12;
        }
        .battle-ivs-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 5px;
          margin-top: 6px;
        }
        .battle-iv {
          min-width: 0;
          padding: 4px 5px;
          border: 1px solid rgba(255,255,255,0.08);
          background: rgba(255,255,255,0.04);
        }
        .battle-iv strong {
          font-size: 16px;
        }
        .battle-gender {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 18px;
          height: 18px;
          margin-left: 4px;
          border-radius: 50%;
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 8px;
          vertical-align: middle;
        }
        .battle-gender-m { background: #2f6ad9; }
        .battle-gender-f { background: #d6447a; }
        .battle-sprite-wrap {
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 0;
        }
        .battle-sprite {
          width: 84px;
          height: 84px;
          object-fit: contain;
          image-rendering: pixelated;
          filter: drop-shadow(0 4px 7px rgba(0,0,0,0.45));
        }
        .battle-moves {
          display: grid;
          gap: 6px;
          min-width: 0;
        }
        .battle-move-link,
        .battle-no-move {
          display: flex;
          align-items: center;
          gap: 7px;
          width: 100%;
          min-height: 28px;
          padding: 4px 7px;
          border: 1px solid rgba(255,255,255,0.18);
          background: rgba(9,15,22,0.56);
          color: #ffffff;
          font-family: var(--font-ui);
          font-size: 19px;
          line-height: 1.05;
          text-decoration: none;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.07);
        }
        .battle-move-row {
          min-width: 0;
        }
        .battle-move-row > summary {
          cursor: pointer;
          list-style: none;
        }
        .battle-move-row > summary::-webkit-details-marker {
          display: none;
        }
        .battle-move-link span:last-child {
          color: #ffffff;
          overflow-wrap: anywhere;
        }
        .battle-move-link:hover,
        .battle-move-link.is-active,
        .battle-move-row[open] > .battle-move-link {
          border-color: var(--accent-soft);
          background: linear-gradient(180deg, rgba(245,125,49,0.35) 0%, rgba(104,52,24,0.62) 100%);
          color: #ffffff;
        }
        .battle-empty-title {
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 11px;
          text-align: center;
          text-transform: uppercase;
        }
        .battle-empty-sub {
          margin-top: 8px;
          text-align: center;
        }
        .battle-move-detail {
          margin-top: 12px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
          padding: 12px;
        }
        .battle-detail-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          margin-top: 6px;
        }
        .battle-detail-head strong {
          display: block;
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 14px;
          text-transform: uppercase;
        }
        .battle-detail-head span {
          display: block;
          margin-top: 5px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 19px;
        }
        .battle-detail-stats {
          display: grid;
          grid-template-columns: repeat(5, minmax(0, 1fr));
          gap: 8px;
          margin-top: 10px;
        }
        .battle-detail-stats div {
          min-width: 0;
          padding: 7px 8px;
          border: 1px solid rgba(255,255,255,0.08);
          background: linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
        }
        .battle-detail-stats > div > span {
          display: block;
          color: var(--bw2-text-soft);
          font-family: var(--font-pixel);
          font-size: 8px;
          text-transform: uppercase;
        }
        .battle-detail-stats > div > strong {
          display: block;
          margin-top: 5px;
          color: #ffffff;
          font-family: var(--font-ui);
          font-size: 18px;
          overflow-wrap: anywhere;
        }
        .battle-type-pill {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          min-width: 96px;
          min-height: 27px;
          padding: 4px 12px;
          border: 2px solid;
          border-radius: 0;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.26), inset 0 -2px 0 rgba(0,0,0,0.25), 0 2px 0 rgba(0,0,0,0.35);
          font-family: var(--font-pixel);
          font-size: 9px;
          line-height: 1;
          text-transform: uppercase;
          text-shadow: 0 1px 0 rgba(0,0,0,0.45);
        }
        .battle-category-value {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          color: #ffffff;
        }
        .battle-category-icon {
          position: relative;
          width: 48px;
          height: 28px;
          flex: 0 0 48px;
          border: 2px solid rgba(0,0,0,0.45);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.22), inset 0 -2px 0 rgba(0,0,0,0.24), 0 2px 0 rgba(0,0,0,0.35);
        }
        .battle-category-text {
          color: #ffffff;
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1;
        }
        .battle-category-icon-physical {
          background: linear-gradient(180deg, #f46a3c 0%, #b63826 100%);
        }
        .battle-category-icon-physical::before {
          content: "";
          position: absolute;
          left: 50%;
          top: 50%;
          width: 22px;
          height: 22px;
          transform: translate(-50%, -50%);
          background: #21130f;
          clip-path: polygon(50% 0%, 59% 30%, 86% 13%, 70% 41%, 100% 50%, 70% 59%, 86% 87%, 59% 70%, 50% 100%, 41% 70%, 14% 87%, 30% 59%, 0% 50%, 30% 41%, 14% 13%, 41% 30%);
          opacity: .9;
        }
        .battle-category-icon-special {
          background: linear-gradient(180deg, #6f8fc5 0%, #435f92 100%);
        }
        .battle-category-icon-special::before {
          content: "";
          position: absolute;
          inset: 5px 14px;
          border-radius: 50%;
          border: 3px double rgba(24,32,48,0.95);
          box-shadow: 0 0 0 3px rgba(226,235,255,0.35), inset 0 0 0 2px rgba(226,235,255,0.28);
        }
        .battle-category-icon-special::after {
          content: "";
          position: absolute;
          left: 50%;
          top: 50%;
          width: 5px;
          height: 5px;
          transform: translate(-50%, -50%);
          border-radius: 50%;
          background: rgba(24,32,48,0.95);
        }
        .battle-category-icon-status {
          background: linear-gradient(180deg, #b8b29b 0%, #77715f 100%);
        }
        .battle-category-icon-status::before {
          content: "";
          position: absolute;
          left: 50%;
          top: 50%;
          width: 23px;
          height: 23px;
          transform: translate(-50%, -50%);
          border-radius: 50%;
          background:
            radial-gradient(circle at 50% 28%, #ffffff 0 3px, transparent 4px),
            radial-gradient(circle at 50% 72%, #6b6658 0 3px, transparent 4px),
            linear-gradient(90deg, #ffffff 0 50%, #6b6658 50% 100%);
          border: 2px solid rgba(32,34,36,0.65);
        }
        .battle-detail-desc {
          margin-top: 10px;
          color: var(--bw2-text);
          font-family: var(--font-ui);
          font-size: 21px;
          line-height: 1.15;
        }
        .battle-move-detail-inline {
          margin-top: 6px;
          padding: 8px;
          background: linear-gradient(180deg, rgba(28,33,41,0.98) 0%, rgba(18,24,32,0.98) 100%);
        }
        .battle-move-detail-inline .battle-detail-kicker {
          display: none;
        }
        .battle-move-detail-inline .battle-detail-head {
          margin-top: 0;
        }
        .battle-move-detail-inline .battle-detail-head strong {
          font-size: 10px;
        }
        .battle-move-detail-inline .battle-detail-head span {
          display: none;
        }
        .battle-move-detail-inline .battle-detail-stats {
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 6px;
        }
        .battle-move-detail-inline .battle-detail-stats div {
          padding: 5px 6px;
        }
        .battle-move-detail-inline .battle-detail-desc {
          font-size: 18px;
        }
        @media (max-width: 1100px) {
          .battle-team-grid,
          .matchup-team-grid {
            grid-template-columns: 1fr;
          }
        }
        @media (max-width: 720px) {
          .matchup-summary-head {
            grid-template-columns: 86px 1fr;
          }
          .matchup-avatar {
            width: 86px;
            height: 86px;
          }
          .matchup-metric-grid,
          .battle-board-top,
          .battle-detail-stats {
            grid-template-columns: repeat(2, minmax(0, 1fr));
          }
          .battle-mon-card {
            grid-template-columns: 1fr 82px;
          }
          .battle-moves {
            grid-column: 1 / -1;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
