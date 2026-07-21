from __future__ import annotations

import html as _html

import streamlit as st


MODE_INFO = {
    "Copa": {
        "label": "Liga suiza",
        "detail": "Rondas, clasificacion y top cut.",
    },
    "Torneo": {
        "label": "Eliminatoria Bo3",
        "detail": "Bracket directo con avance por ronda.",
    },
    "Copa Dobles": {
        "label": "Copa Dobles",
        "detail": "Equipos de 2, liga regular y final.",
    },
}


def render_copa_styles() -> None:
    st.markdown(
        """
        <style>
        .cup-hero {
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
            linear-gradient(116deg, rgba(207,116,255,0.16) 0 30%, transparent 30% 100%),
            linear-gradient(180deg, rgba(43,52,64,0.96) 0%, rgba(17,24,33,0.96) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.09), 0 10px 26px rgba(0,0,0,0.24);
        }
        .cup-hero::before {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background:
            linear-gradient(180deg, rgba(255,255,255,0.05) 0 1px, transparent 1px 100%) 0 0 / 100% 22px,
            linear-gradient(90deg, rgba(255,255,255,0.04) 0 1px, transparent 1px 100%) 0 0 / 26px 100%;
          opacity: .5;
        }
        .cup-hero-main,
        .cup-hero-side {
          position: relative;
          z-index: 1;
        }
        .cup-kicker,
        .cup-title,
        .cup-pill,
        .cup-section-title,
        .cup-card-label,
        .cup-card-value,
        .cup-vs,
        .cup-round-title,
        .cup-player,
        .cup-score {
          font-family: var(--font-pixel);
        }
        .cup-kicker {
          display: inline-block;
          padding: 5px 8px;
          border-left: 3px solid var(--accent);
          background: rgba(0,0,0,0.28);
          color: var(--bw2-text-soft);
          font-size: 9px;
          text-transform: uppercase;
        }
        .cup-title {
          margin-top: 12px;
          color: #ffffff;
          font-size: clamp(21px, 3vw, 34px);
          line-height: 1.05;
          text-transform: uppercase;
          text-shadow: 0 2px 0 rgba(0,0,0,0.5);
        }
        .cup-sub {
          margin-top: 10px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 19px;
          line-height: 1.18;
        }
        .cup-hero-side {
          min-width: 230px;
          display: grid;
          align-content: center;
          gap: 8px;
          padding: 12px;
          border: 1px solid rgba(216,223,232,0.18);
          background: linear-gradient(180deg, rgba(10,15,22,0.68) 0%, rgba(9,12,17,0.9) 100%);
        }
        .cup-pill {
          display: inline-flex;
          align-items: center;
          min-height: 29px;
          padding: 6px 9px;
          border: 1px solid rgba(216,223,232,0.16);
          background: linear-gradient(180deg, rgba(255,255,255,0.07), rgba(255,255,255,0.02));
          color: #ffffff;
          font-size: 9px;
          text-transform: uppercase;
        }
        .cup-mode-grid,
        .cup-metric-grid {
          display: grid;
          gap: 10px;
          margin: 10px 0 14px;
        }
        .cup-mode-grid {
          grid-template-columns: repeat(3, minmax(0, 1fr));
        }
        .cup-metric-grid {
          grid-template-columns: repeat(4, minmax(0, 1fr));
        }
        .cup-mode-card,
        .cup-metric,
        .cup-section,
        .cup-vs-card,
        .cup-paste-card,
        .cup-match {
          border: 1px solid var(--bw2-edge);
          background:
            linear-gradient(90deg, rgba(255,255,255,0.05), transparent 62%),
            linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
        }
        .cup-mode-card {
          min-height: 94px;
          padding: 12px;
          border-left: 4px solid rgba(216,223,232,0.24);
        }
        .cup-mode-card.is-active {
          border-color: var(--bw2-edge-strong);
          border-left-color: var(--accent);
          background:
            linear-gradient(116deg, rgba(207,116,255,0.18) 0 35%, transparent 35% 100%),
            linear-gradient(180deg, #2b3340 0%, #171f2a 100%);
        }
        .cup-card-label {
          color: #ffffff;
          font-size: 10px;
          line-height: 1.25;
          text-transform: uppercase;
        }
        .cup-card-sub {
          margin-top: 8px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1.18;
        }
        .cup-section {
          margin: 12px 0 10px;
          padding: 12px;
        }
        .cup-section-title {
          color: #ffffff;
          font-size: 12px;
          line-height: 1.2;
          text-transform: uppercase;
        }
        .cup-section-sub {
          margin-top: 7px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 18px;
          line-height: 1.18;
        }
        .cup-metric {
          min-height: 82px;
          padding: 10px 12px;
        }
        .cup-card-value {
          margin-top: 9px;
          color: #ffffff;
          font-size: 15px;
          line-height: 1.15;
        }
        .cup-vs-card {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 62px minmax(0, 1fr);
          align-items: stretch;
          min-height: 58px;
          overflow: hidden;
        }
        .cup-vs-player {
          display: flex;
          align-items: center;
          min-width: 0;
          padding: 11px 12px;
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          line-height: 1.25;
          text-transform: uppercase;
          overflow-wrap: anywhere;
        }
        .cup-vs {
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ffffff;
          font-size: 11px;
          border-left: 1px solid rgba(216,223,232,0.14);
          border-right: 1px solid rgba(216,223,232,0.14);
          background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
        }
        .cup-bracket {
          display: flex;
          gap: 18px;
          align-items: flex-start;
          overflow-x: auto;
          padding: 6px 0 4px;
        }
        .cup-round-col {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .cup-round-title {
          display: inline-block;
          margin: 4px 0 7px;
          padding: 7px 9px;
          border: 1px solid var(--bw2-edge-strong);
          background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
          color: #ffffff;
          font-size: 10px;
          text-transform: uppercase;
        }
        .cup-match {
          position: relative;
          width: 270px;
          padding: 10px 12px;
        }
        .cup-player {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 12px;
          min-height: 28px;
          color: var(--bw2-text-soft);
          font-size: 9px;
          line-height: 1.2;
        }
        .cup-player.is-winner {
          color: #ffffff;
        }
        .cup-score {
          flex: 0 0 auto;
          color: #ffe08b;
          font-size: 9px;
        }
        .cup-paste-card {
          min-height: 116px;
          padding: 10px;
          margin-bottom: 10px;
        }
        .cup-paste-name {
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
        }
        .cup-paste-meta {
          margin-top: 8px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 17px;
          line-height: 1.2;
        }
        @media (max-width: 980px) {
          .cup-hero,
          .cup-mode-grid,
          .cup-metric-grid {
            grid-template-columns: 1fr;
          }
          .cup-hero-side {
            min-width: 0;
          }
        }
        @media (max-width: 620px) {
          .cup-vs-card {
            grid-template-columns: 1fr;
          }
          .cup-vs {
            min-height: 34px;
            border-left: none;
            border-right: none;
            border-top: 1px solid rgba(216,223,232,0.14);
            border-bottom: 1px solid rgba(216,223,232,0.14);
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_copa_header(selected_mode: str) -> None:
    info = MODE_INFO.get(selected_mode, MODE_INFO["Copa"])
    label = _html.escape(info["label"])
    st.markdown(
        (
            "<div class='cup-hero'>"
            "<div class='cup-hero-main'>"
            "<div class='cup-title'>Copa</div>"
            "</div>"
            "<div class='cup-hero-side'>"
            f"<span class='cup-pill'>{label}</span>"
            "</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_copa_mode_cards(selected_mode: str) -> None:
    cards = []
    for key, info in MODE_INFO.items():
        active = " is-active" if key == selected_mode else ""
        cards.append(
            "<div class='cup-mode-card"
            f"{active}'>"
            f"<div class='cup-card-label'>{_html.escape(info['label'])}</div>"
            "</div>"
        )
    st.markdown(
        "<div class='cup-mode-grid'>" + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


def render_copa_section(title: str, subtitle: str | None = None) -> None:
    st.markdown(
        (
            "<div class='cup-section'>"
            f"<div class='cup-section-title'>{_html.escape(title)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_copa_metric(label: str, value: str, sub: str | None = None) -> str:
    sub_html = f"<div class='cup-card-sub'>{_html.escape(sub)}</div>" if sub else ""
    return (
        "<div class='cup-metric'>"
        f"<div class='cup-card-label'>{_html.escape(label)}</div>"
        f"<div class='cup-card-value'>{_html.escape(value)}</div>"
        f"{sub_html}"
        "</div>"
    )


def render_copa_metrics(metrics: list[tuple[str, str, str | None]]) -> None:
    html = "".join(render_copa_metric(label, value, sub) for label, value, sub in metrics)
    st.markdown(f"<div class='cup-metric-grid'>{html}</div>", unsafe_allow_html=True)


def render_vs_card(left: str, right: str, *, middle: str = "VS") -> None:
    st.markdown(
        (
            "<div class='cup-vs-card'>"
            f"<div class='cup-vs-player'>{_html.escape(left or '-')}</div>"
            f"<div class='cup-vs'>{_html.escape(middle)}</div>"
            f"<div class='cup-vs-player'>{_html.escape(right or '-')}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
