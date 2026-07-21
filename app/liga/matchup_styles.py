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
        .matchup-hero {
          position: relative;
          overflow: hidden;
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 18px;
          align-items: stretch;
          min-height: 136px;
          margin-bottom: 12px;
          padding: 16px;
          border: 1px solid var(--bw2-edge);
          background:
            linear-gradient(116deg, rgba(255,111,97,0.16) 0 30%, transparent 30% 100%),
            linear-gradient(180deg, rgba(43,52,64,0.96) 0%, rgba(17,24,33,0.96) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.09), 0 10px 26px rgba(0,0,0,0.24);
        }
        .matchup-hero::before {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background:
            linear-gradient(180deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 100%) 0 0 / 100% 22px,
            linear-gradient(90deg, rgba(255,255,255,0.04) 0 1px, transparent 1px 100%) 0 0 / 26px 100%;
          opacity: .5;
        }
        .matchup-hero-main,
        .matchup-hero-side {
          position: relative;
          z-index: 1;
        }
        .matchup-kicker,
        .matchup-title,
        .matchup-hero-pill,
        .matchup-mode-title {
          font-family: var(--font-pixel);
          text-transform: uppercase;
        }
        .matchup-kicker {
          display: inline-block;
          padding: 5px 8px;
          border-left: 3px solid var(--accent);
          background: rgba(0,0,0,0.28);
          color: var(--bw2-text-soft);
          font-size: 9px;
        }
        .matchup-title {
          margin-top: 12px;
          color: #ffffff;
          font-size: 32px;
          line-height: 1.05;
          text-shadow: 0 2px 0 rgba(0,0,0,0.5);
        }
        .matchup-subtitle {
          margin-top: 10px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 19px;
          line-height: 1.18;
        }
        .matchup-hero-side {
          min-width: 230px;
          display: grid;
          align-content: center;
          gap: 8px;
          padding: 12px;
          border: 1px solid rgba(216,223,232,0.18);
          background: linear-gradient(180deg, rgba(10,15,22,0.68) 0%, rgba(9,12,17,0.9) 100%);
        }
        .matchup-hero-pill {
          display: inline-flex;
          align-items: center;
          min-height: 29px;
          padding: 6px 9px;
          border: 1px solid rgba(216,223,232,0.16);
          background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02));
          color: #ffffff;
          font-size: 9px;
        }
        .matchup-mode-grid {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          gap: 10px;
          margin: 0 0 14px;
        }
        .matchup-mode-card {
          min-height: 82px;
          padding: 11px 12px;
          border: 1px solid var(--bw2-edge);
          border-left: 4px solid rgba(216,223,232,0.24);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.05), transparent 62%),
            linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
        }
        .matchup-mode-card.is-active {
          border-color: var(--bw2-edge-strong);
          border-left-color: var(--accent);
          background:
            linear-gradient(116deg, rgba(255,111,97,0.18) 0 35%, transparent 35% 100%),
            linear-gradient(180deg, #2b3340 0%, #171f2a 100%);
        }
        .matchup-mode-title {
          color: #ffffff;
          font-size: 10px;
          line-height: 1.2;
        }
        .matchup-mode-sub {
          margin-top: 8px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1.18;
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
            linear-gradient(120deg, rgba(255,111,97,0.1) 0 24%, transparent 24% 100%),
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
          min-height: 178px;
          display: grid;
          grid-template-columns: minmax(138px, .95fr) 94px minmax(178px, 1.15fr);
          gap: 10px;
          align-items: center;
          overflow: hidden;
          border: 1px solid rgba(216,223,232,0.24);
          background:
            linear-gradient(110deg, rgba(255,111,97,0.14) 0 35%, transparent 35% 100%),
            linear-gradient(180deg, rgba(43,52,64,0.94) 0%, rgba(17,24,33,0.94) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.13), 0 5px 14px rgba(0,0,0,0.25);
          padding: 12px;
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
          width: 88px;
          height: 88px;
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
          min-height: 31px;
          padding: 5px 8px;
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
        .battle-detail-stat-type {
          padding: 0;
          border: 0;
          background: transparent;
          box-shadow: none;
        }
        .battle-detail-stat-type > span {
          display: none;
        }
        .battle-detail-stat-type > strong {
          margin-top: 0;
          line-height: 0;
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
          margin-top: 7px;
          padding: 9px;
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

        /* Champions pass */
        .matchup-shell,
        .matchup-hero,
        .matchup-summary,
        .battle-board {
          border-color: rgba(238,233,255,0.34) !important;
          border-radius: 20px !important;
          background:
            linear-gradient(126deg, rgba(255,255,255,0.11) 0 24%, transparent 24% 100%),
            linear-gradient(180deg, rgba(125,101,232,0.9), rgba(73,62,171,0.88)) !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.22), 0 12px 26px rgba(18,14,54,0.24) !important;
        }

        .matchup-hero {
          min-height: 128px;
          overflow: hidden;
        }

        .matchup-hero-side,
        .matchup-hero-pill,
        .matchup-metric,
        .battle-board-top div,
        .battle-card-left,
        .battle-ability-row,
        .battle-private-line,
        .battle-ivs,
        .battle-detail-stats div {
          border-color: rgba(238,233,255,0.24) !important;
          border-radius: 14px !important;
          background:
            linear-gradient(136deg, transparent 0 74%, rgba(255,117,221,0.12) 74% 100%),
            rgba(255,255,255,0.08) !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.12) !important;
        }

        .matchup-mode-card,
        .matchup-move,
        .battle-move-link,
        .battle-no-move {
          border: 1px solid rgba(238,233,255,0.34) !important;
          border-radius: 14px !important;
          background:
            linear-gradient(136deg, transparent 0 74%, rgba(255,117,221,0.14) 74% 87%, rgba(69,209,255,0.14) 87% 100%),
            linear-gradient(180deg, rgba(238,233,255,0.96), rgba(211,204,237,0.96)) !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.5), 0 8px 17px rgba(18,14,54,0.18) !important;
          color: var(--champ-text) !important;
        }

        .matchup-mode-card *,
        .matchup-move span:last-child,
        .battle-move-link span:last-child,
        .battle-no-move {
          color: var(--champ-text) !important;
          -webkit-text-fill-color: var(--champ-text) !important;
        }

        .matchup-mode-card.is-active,
        .battle-move-link:hover,
        .battle-move-row[open] > .battle-move-link {
          border-color: rgba(246,216,59,0.95) !important;
          background:
            linear-gradient(136deg, transparent 0 70%, rgba(255,255,255,0.22) 70% 100%),
            linear-gradient(180deg, var(--champ-lime), var(--champ-lime-2)) !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.52), 0 0 0 3px rgba(246,216,59,0.16), 0 12px 23px rgba(18,14,54,0.22) !important;
        }

        .battle-team-grid,
        .matchup-team-grid {
          gap: 12px !important;
        }

        .battle-mon-card,
        .matchup-mon {
          border-color: rgba(238,233,255,0.34) !important;
          border-radius: 18px !important;
          background:
            linear-gradient(116deg, rgba(255,255,255,0.1) 0 35%, transparent 35% 100%),
            linear-gradient(180deg, rgba(119,98,229,0.9), rgba(72,62,172,0.9)) !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.18), 0 10px 22px rgba(18,14,54,0.2) !important;
        }

        .battle-mon-card {
          grid-template-columns: minmax(150px, .92fr) 124px minmax(214px, 1.16fr) !important;
          min-height: 188px !important;
        }

        .battle-mon-card::before,
        .matchup-hero::before {
          background:
            linear-gradient(180deg, rgba(255,255,255,0.07) 0 1px, transparent 1px 100%) 0 0 / 100% 20px,
            linear-gradient(90deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 100%) 0 0 / 24px 100% !important;
          opacity: .42 !important;
        }

        .battle-slot-mark {
          right: 12px;
          bottom: -3px;
          color: rgba(255,255,255,0.16) !important;
          font-size: 48px !important;
        }

        .battle-mon-name,
        .matchup-mon-title,
        .matchup-player,
        .matchup-title {
          color: #ffffff !important;
          -webkit-text-fill-color: #ffffff !important;
        }

        .battle-species,
        .battle-level,
        .battle-item,
        .matchup-mon-sub,
        .matchup-mon-extra,
        .matchup-subtitle,
        .matchup-division,
        .matchup-save {
          color: rgba(255,255,255,0.84) !important;
          -webkit-text-fill-color: rgba(255,255,255,0.84) !important;
        }

        .battle-sprite-wrap,
        .matchup-sprite {
          border-radius: 16px !important;
          background:
            radial-gradient(circle at 50% 46%, rgba(255,255,255,0.42), rgba(255,255,255,0.08) 60%, transparent 61%),
            linear-gradient(180deg, rgba(224,219,249,0.92), rgba(190,183,225,0.9)) !important;
        }

        .battle-sprite {
          width: 116px !important;
          height: 116px !important;
        }

        .matchup-sprite {
          width: 108px !important;
          height: 108px !important;
          padding: 5px !important;
        }

        .battle-type-dot {
          width: 25px !important;
          height: 25px !important;
          flex-basis: 25px !important;
          border-radius: 7px !important;
        }

        .battle-move-detail,
        .battle-move-detail-inline {
          border-color: rgba(238,233,255,0.3) !important;
          border-radius: 16px !important;
          background:
            linear-gradient(130deg, rgba(255,255,255,0.09) 0 28%, transparent 28% 100%),
            linear-gradient(180deg, rgba(92,75,202,0.96), rgba(62,52,160,0.96)) !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.16), 0 8px 18px rgba(18,14,54,0.18) !important;
        }

        .battle-move-detail-inline .battle-detail-stats div,
        .battle-detail-stats div {
          background:
            linear-gradient(180deg, rgba(238,233,255,0.95), rgba(211,204,237,0.95)) !important;
        }

        .battle-detail-stats div span,
        .battle-detail-stats div strong {
          color: var(--champ-text) !important;
          -webkit-text-fill-color: var(--champ-text) !important;
        }

        .battle-types,
        .matchup-types {
          display: inline-flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 5px;
        }

        .battle-types .poke-type-chip.has-label.battle-type-dot {
          width: auto !important;
          min-width: 78px !important;
          padding: 4px 8px !important;
        }

        .battle-type-pill.poke-type-chip {
          width: auto !important;
          min-width: 94px !important;
          height: 28px !important;
          padding: 4px 10px !important;
          border-radius: 5px !important;
        }

        .battle-mon-card-private {
          grid-template-columns: minmax(280px, .98fr) 130px minmax(236px, 1fr) !important;
          align-items: stretch !important;
        }

        .battle-mon-card-public {
          grid-template-columns: minmax(220px, .94fr) 116px minmax(210px, 1.05fr) !important;
          min-height: 156px !important;
          padding: 10px !important;
        }

        .battle-mon-card-public .battle-card-left {
          display: grid;
          align-content: center;
          gap: 6px;
          padding: 7px 8px !important;
          border: 0 !important;
          background: transparent !important;
          box-shadow: none !important;
        }

        .battle-mon-card-private .battle-card-left {
          display: grid;
          gap: 7px;
          padding: 9px !important;
        }

        .battle-mon-card-private .battle-name-row {
          min-height: 34px;
          padding: 5px 7px;
          border-radius: 10px;
          background:
            linear-gradient(180deg, rgba(255,255,255,0.16), rgba(255,255,255,0.06)),
            rgba(96,80,205,0.74);
        }

        .battle-item-row {
          display: inline-flex;
          align-items: center;
          gap: 7px;
          min-width: 0;
          color: rgba(255,255,255,0.86);
          -webkit-text-fill-color: rgba(255,255,255,0.86);
          font-family: var(--font-ui);
          font-size: 16px;
          line-height: 1.05;
        }

        .battle-item-row.is-compact {
          font-size: 15px;
        }

        .battle-item-row > span:last-child {
          min-width: 0;
          overflow-wrap: anywhere;
        }

        .battle-item-icon {
          width: 28px;
          height: 28px;
          flex: 0 0 28px;
          display: inline-grid;
          place-items: center;
          border-radius: 50%;
          border: 1px solid rgba(238,233,255,0.36);
          background:
            radial-gradient(circle at 50% 42%, rgba(255,255,255,0.55), rgba(255,255,255,0.08) 62%, transparent 63%),
            linear-gradient(180deg, rgba(238,233,255,0.94), rgba(199,192,230,0.9));
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.45), 0 4px 8px rgba(18,14,54,0.22);
        }

        .battle-item-icon img {
          width: 23px;
          height: 23px;
          object-fit: contain;
          image-rendering: pixelated;
          filter: drop-shadow(0 2px 3px rgba(18,14,54,0.2));
        }

        .battle-item-icon-empty::before {
          content: "";
          width: 13px;
          height: 13px;
          border-radius: 50%;
          background:
            radial-gradient(circle at 50% 50%, #f8fbff 0 22%, transparent 23%),
            linear-gradient(#ef3f56 0 48%, #202436 48% 54%, #f8fbff 54% 100%);
          border: 1px solid #202436;
        }

        .battle-private-info {
          display: grid;
          gap: 7px;
          margin-top: 0;
        }

        .battle-stat-stack {
          display: grid;
          gap: 5px;
          padding: 7px;
          border: 1px solid rgba(238,233,255,0.18);
          border-radius: 13px;
          background:
            linear-gradient(126deg, rgba(255,255,255,0.07) 0 32%, transparent 32% 100%),
            rgba(55,45,148,0.36);
        }

        .battle-stat-row {
          display: grid;
          grid-template-columns: 18px minmax(62px, .72fr) minmax(76px, 1fr) 28px;
          gap: 6px;
          align-items: center;
          min-height: 24px;
          padding: 3px 5px;
          border-radius: 999px;
          background: rgba(255,255,255,0.08);
        }

        .battle-stat-symbol {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 18px;
          height: 18px;
          color: #ffffff;
          -webkit-text-fill-color: #ffffff;
          font-family: var(--font-ui);
          font-size: 14px;
          line-height: 1;
          filter: drop-shadow(0 1px 0 rgba(0,0,0,0.24));
        }

        .battle-stat-symbol-heart::before { content: "♥"; }
        .battle-stat-symbol-burst::before { content: "✹"; }
        .battle-stat-symbol-shield::before { content: "✦"; }
        .battle-stat-symbol-eye::before { content: "◎"; }
        .battle-stat-symbol-hex::before { content: "⬢"; }
        .battle-stat-symbol-wind::before { content: "≋"; }

        .battle-stat-label {
          color: rgba(255,255,255,0.88);
          -webkit-text-fill-color: rgba(255,255,255,0.88);
          font-family: var(--font-ui);
          font-size: 12px;
          font-weight: 800;
          line-height: 1;
        }

        .battle-stat-bar {
          position: relative;
          height: 7px;
          overflow: hidden;
          border-radius: 999px;
          background: rgba(38,32,112,0.66);
          box-shadow: inset 0 1px 2px rgba(0,0,0,0.24);
        }

        .battle-stat-bar > span {
          display: block;
          height: 100%;
          border-radius: 999px;
          background: linear-gradient(90deg, #ffb35c, #f6d83b);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.4);
        }

        .battle-stat-row strong {
          color: #ffffff !important;
          -webkit-text-fill-color: #ffffff !important;
          font-family: var(--font-ui);
          font-size: 13px;
          font-weight: 900;
          text-align: right;
        }

        .battle-mon-card-public .battle-moves,
        .matchup-move-list {
          gap: 3px !important;
        }

        .battle-mon-card-public .battle-move-link,
        .battle-mon-card-public .battle-no-move,
        .matchup-move {
          min-height: 27px !important;
          padding: 3px 5px !important;
          border: 0 !important;
          border-radius: 7px !important;
          background: rgba(255,255,255,0.08) !important;
          box-shadow: none !important;
        }

        .battle-mon-card-public .battle-move-link:hover,
        .battle-mon-card-public .battle-move-row[open] > .battle-move-link {
          background:
            linear-gradient(136deg, transparent 0 70%, rgba(255,255,255,0.22) 70% 100%),
            linear-gradient(180deg, var(--champ-lime), var(--champ-lime-2)) !important;
        }

        .battle-mon-card-private .battle-move-link {
          min-height: 35px !important;
          border-radius: 12px !important;
        }

        .matchup-name-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
          min-width: 0;
        }

        .matchup-mon-item .battle-item-row {
          margin-top: 3px;
        }

        @media (max-width: 1100px) {
          .battle-team-grid,
          .matchup-team-grid {
            grid-template-columns: 1fr;
          }
        }
        @media (max-width: 720px) {
          .matchup-hero,
          .matchup-mode-grid {
            grid-template-columns: 1fr;
          }
          .matchup-hero-side {
            min-width: 0;
          }
          .matchup-title {
            font-size: 24px;
          }
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
            grid-template-columns: 1fr !important;
          }
          .battle-moves {
            grid-column: 1 / -1;
          }
          .battle-stat-row {
            grid-template-columns: 18px minmax(64px, .72fr) minmax(72px, 1fr) 28px;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
