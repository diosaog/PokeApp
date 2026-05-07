from __future__ import annotations

from html import escape

import streamlit as st


NORMATIVA_SECTIONS = [
    {
        "id": "nuzlocke",
        "tab": "Nuzlocke",
        "bot_title": "Normas Nuzlocke",
        "eyebrow": "Protocolo Base",
        "summary": "La capa central del reto: captura, muerte permanente y clausulas especiales.",
        "text_lines": [
            "1. Normas Nuzlocke",
            "- Todo Pokemon debilitado se considera muerto y debe enviarse a la caja de muertos.",
            "- Un Pokemon muerto no puede volver a usarse ni subir de nivel.",
            "- Solo se puede capturar el primer encuentro de cada ruta o area.",
            "- Si ese Pokemon huye, es derrotado o el combate termina por cualquier motivo, la captura de esa zona se pierde.",
            "- Mote obligatorio para todos los Pokemon.",
            "",
            "Clausulas especiales",
            "- Duplicados: si el primer encuentro pertenece a una linea evolutiva ya capturada, se debe de forzar otro encuentro, a menos que este haya muerto. Entonces podras decidir.",
            "- Legendarios principales: no estan permitidos; si aparecen como primer encuentro, se fuerza otro.",
            "- Shiny: El pokemon shiny es capturable 1 unica vez por juego, no se pueden capturar mas de 1.",
            "- Fosil: solo se puede usar una vez por ser de uso unico.",
            "- Pokemon baneados: Slaking, Deoxys.",
            "- Movimientos baneados: Esquema (Unicamente la MT, en el recuerdamovimientos si se puede).",
            "- Objetos baneados: Rocio Bondad.",
            "- El pokemon transferido entre juegos NO puede ser pseudo-legendario ni legendario. Tambien, este mismo llevara 1 ataque del juego anterior +2 ataques random elegidos antes en una ruleta y una habilidad random.",
        ],
        "visual_blocks": [
            {
                "title": "Reglas Base",
                "items": [
                    "Todo Pokemon debilitado se considera muerto y debe enviarse a la caja de muertos.",
                    "Un Pokemon muerto no puede volver a usarse ni subir de nivel.",
                    "Solo se puede capturar el primer encuentro de cada ruta o area.",
                    "Si el encuentro huye, es derrotado o el combate termina, la captura de esa zona se pierde.",
                    "Mote obligatorio para todos los Pokemon.",
                ],
            },
            {
                "title": "Clausulas Especiales",
                "items": [
                    "Duplicados: si el primer encuentro pertenece a una linea ya capturada, se fuerza otro salvo que el anterior haya muerto.",
                    "Legendarios principales: no estan permitidos; si aparecen como primer encuentro, se fuerza otro.",
                    "Shiny: solo se puede capturar 1 por juego.",
                    "Fosil: solo se puede usar una vez por ser de uso unico.",
                    "Baneados: Slaking, Deoxys, Esquema (solo la MT) y Rocio Bondad.",
                    "Pokemon transferido: no puede ser pseudo-legendario ni legendario y arrastra 1 ataque anterior + 2 random + habilidad random.",
                ],
            },
        ],
    },
    {
        "id": "equipo",
        "tab": "Equipo",
        "bot_title": "Restricciones de equipo",
        "eyebrow": "Control de Roster",
        "summary": "Limites competitivos para evitar stacks rotos y duplicados de fase.",
        "text_lines": [
            "2. Restricciones de equipo",
            "- Maximo 1 pseudo-legendario por equipo.",
            "- Maximo 1 legendario menor o singular (<= 600 BST) por equipo.",
            "- No se pueden repetir Pokemon de la misma fase evolutiva.",
            "- Si se obtiene un duplicado, debe liberarse el ultimo capturado.",
            "- Esta norma no se aplica si el Pokemon previo de esa fase ya estaba muerto.",
        ],
        "visual_blocks": [
            {
                "title": "Limites de Equipo",
                "items": [
                    "Maximo 1 pseudo-legendario por equipo.",
                    "Maximo 1 legendario menor o singular (<= 600 BST) por equipo.",
                    "No se pueden repetir Pokemon de la misma fase evolutiva.",
                    "Si se obtiene un duplicado, debe liberarse el ultimo capturado.",
                    "La norma de duplicados no se aplica si el Pokemon previo de esa fase ya estaba muerto.",
                ],
            }
        ],
    },
    {
        "id": "estructura",
        "tab": "Tramos",
        "bot_title": "Estructura y combates",
        "eyebrow": "Formato de Liga",
        "summary": "Como se divide la partida y como se resuelven los cruces entre jugadores.",
        "text_lines": [
            "3. Estructura por tramos",
            "- La partida se divide en 4 tramos mas una Liga Pokemon final.",
            "- Cada tramo finaliza tras superar determinados gimnasios.",
            "- Al cierre de cada tramo se disputa una liga competitiva entre jugadores.",
            "",
            "4. Combates entre jugadores",
            "- Liga: combates 1 vs 1, formato Bo1.",
            "- Copa: se juega tras completar la Liga Pokemon. Formato eliminatorio, Bo3.",
        ],
        "visual_blocks": [
            {
                "title": "Estructura del Recorrido",
                "items": [
                    "La partida se divide en 4 tramos mas una Liga Pokemon final.",
                    "Cada tramo finaliza tras superar determinados gimnasios.",
                    "Al cierre de cada tramo se disputa una liga competitiva entre jugadores.",
                ],
            },
            {
                "title": "Formato de Combates",
                "items": [
                    "Liga: combates 1 vs 1 en formato Bo1.",
                    "Copa: se juega tras completar la Liga Pokemon y pasa a formato eliminatorio Bo3.",
                ],
            },
        ],
    },
    {
        "id": "caps",
        "tab": "Level Caps",
        "bot_title": "Level Caps",
        "eyebrow": "Control de Progresion",
        "summary": "Topes de nivel oficiales para gimnasios, liga final y gestion de caramelos.",
        "text_lines": [
            "5. Level Caps",
            "Gimnasios",
            "- Cheren 16",
            "- Hiedra 22",
            "- Camus 29",
            "- Camila 36",
            "- Yakon 40",
            "- Gerania 47",
            "- Lirio 58",
            "- Ciprian 61",
            "",
            "Liga Pokemon",
            "- Anis 70",
            "- Aza 70",
            "- Catleya 70",
            "- Lotto 70",
            "- Iris 71",
            "",
            "Reglas de nivel",
            "- Ningun Pokemon puede superar el cap del siguiente combate oficial.",
            "- Si un Pokemon lo supera, debe enviarse a la caja y no puede utilizarse.",
            "- Los Caramelos Raros solo pueden usarse para ajustar niveles.",
            "- Si se sube de mas y se guarda, se permite resetear.",
        ],
        "visual_blocks": [
            {
                "title": "Gimnasios",
                "rows": [
                    ("Cheren", "16"),
                    ("Hiedra", "22"),
                    ("Camus", "29"),
                    ("Camila", "36"),
                    ("Yakon", "40"),
                    ("Gerania", "47"),
                    ("Lirio", "58"),
                    ("Ciprian", "61"),
                ],
            },
            {
                "title": "Liga Pokemon",
                "rows": [
                    ("Anis", "70"),
                    ("Aza", "70"),
                    ("Catleya", "70"),
                    ("Lotto", "70"),
                    ("Iris", "71"),
                ],
            },
            {
                "title": "Reglas de Nivel",
                "items": [
                    "Ningun Pokemon puede superar el cap del siguiente combate oficial.",
                    "Si un Pokemon lo supera, debe enviarse a la caja y no puede utilizarse.",
                    "Los Caramelos Raros solo pueden usarse para ajustar niveles.",
                    "Si se sube de mas y se guarda, se permite resetear.",
                ],
            },
        ],
    },
    {
        "id": "liga",
        "tab": "Liga A/B",
        "bot_title": "Divisiones, puntos y monedas",
        "eyebrow": "Sistema de Clasificacion",
        "summary": "Distribucion de divisiones, scoring global y economia oficial de la liga.",
        "text_lines": [
            "6. Divisiones (Liga A / B)",
            "- Dos divisiones: A y B, con 5 jugadores cada una.",
            "- Los jugadores solo se enfrentan contra rivales de su propia division.",
            "- Descienden los 3 ultimos de Division A; ascienden los 3 primeros de Division B.",
            "- Monedas (por posicion)",
            "",
            "1: 15 /",
            "2: 14 /",
            "3: 12 /",
            "4: 11 /",
            "5: 10 /",
            "6: 11 /",
            "7: 9 /",
            "8: 8 /",
            "9: 6 /",
            "10: 4 /",
            "",
            "- Puntos (por posicion)",
            "",
            "1: 9 /",
            "2: 8 /",
            "3: 7 /",
            "4: 6 /",
            "5: 5 /",
            "6: 5 /",
            "7: 4 /",
            "8: 3 /",
            "9: 2 /",
            "10: 1 /",
            "",
            "7. Monedas",
            "- Medallas: 4 monedas por cada medalla (max 8).",
            "- Saldo total = medallas*4 + monedas de liga - monedas gastadas.",
        ],
        "visual_blocks": [
            {
                "title": "Divisiones",
                "items": [
                    "Dos divisiones: A y B, con 5 jugadores cada una.",
                    "Los jugadores solo se enfrentan contra rivales de su propia division.",
                    "Descienden los 3 ultimos de Division A; ascienden los 3 primeros de Division B.",
                ],
            },
            {
                "title": "Monedas por Posicion",
                "rows": [
                    ("1", "15"),
                    ("2", "14"),
                    ("3", "12"),
                    ("4", "11"),
                    ("5", "10"),
                    ("6", "11"),
                    ("7", "9"),
                    ("8", "8"),
                    ("9", "6"),
                    ("10", "4"),
                ],
            },
            {
                "title": "Puntos por Posicion",
                "rows": [
                    ("1", "9"),
                    ("2", "8"),
                    ("3", "7"),
                    ("4", "6"),
                    ("5", "5"),
                    ("6", "5"),
                    ("7", "4"),
                    ("8", "3"),
                    ("9", "2"),
                    ("10", "1"),
                ],
            },
            {
                "title": "Economia Base",
                "items": [
                    "Medallas: 4 monedas por cada medalla (max 8).",
                    "Saldo total = medallas*4 + monedas de liga - monedas gastadas.",
                ],
            },
        ],
    },
    {
        "id": "comodines",
        "tab": "Comodines",
        "bot_title": "Comodines",
        "eyebrow": "Herramientas Especiales",
        "summary": "Objetos de impacto directo sobre cajas, rutas, robos y resurrecciones.",
        "text_lines": [
            "8. Comodines",
            "- Revivir: revive un Pokemon de la Caja 8; queda marcado como blindado + revivido y sigue contando como muerto a efectos de puntos (-0.2).",
            "- Robar: si el objetivo no esta blindado, se registra el robo y queda blindado.",
            "- Blindar: marca un Pokemon como blindado (no se puede volver a robarse ni blindarse).",
            "- Captura Extra: permite una captura adicional en una ruta desconocida.",
            "- Fosil: permite obtener un fosil.",
        ],
        "visual_blocks": [
            {
                "title": "Catalogo de Comodines",
                "items": [
                    "Revivir: revive un Pokemon de la Caja 8; queda blindado + revivido y sigue contando como muerto a efectos de puntos (-0.2).",
                    "Robar: si el objetivo no esta blindado, se registra el robo y queda blindado.",
                    "Blindar: marca un Pokemon como blindado y no puede volver a robarse ni blindarse.",
                    "Captura Extra: permite una captura adicional en una ruta desconocida.",
                    "Fosil: permite obtener un fosil.",
                ],
            }
        ],
    },
    {
        "id": "generales",
        "tab": "Generales",
        "bot_title": "Normas generales",
        "eyebrow": "Disciplina de Temporada",
        "summary": "Reglas de conducta, legalidad y limites de compra y entrenamiento.",
        "text_lines": [
            "9. Normas generales",
            "- No se permiten intercambios.",
            "- Si un Pokemon ha sido eliminado por un juicio y/o ilegalidad de un entrenador, este NO podra volver a tener ese Pokemon.",
            "- Queda totalmente prohibido explotar el juego, como por ejemplo forzar encuentros no random (cadenas de shiny, arboles de miel, etc.).",
            "- Las tiendas especiales solo y unicamente se puede comprar 1 objeto.",
            "- Objetos como las Master Ball de tiendas, solo se pueden comprar una vez.",
            "- Se permiten combates de practica entre jugadores de distintas ligas.",
            "- Los comodines pueden usarse sobre otros jugadores o sobre uno mismo.",
            "- El comodin Robar no puede usarse dos veces seguidas sobre el mismo jugador.",
            "- Prohibido usar equipos de otros jugadores para practicar y usar herramientas de calculos de da\u00c3\u00b1o externas al showdown.",
            "- Buscar vacios legales en el juego es ilegal, si un entrenador lo encuentra, debe avisar por el grupo y se tomara una decision en base a una votacion.",
            "- Directos obligatorios: los jugadores deben jugar en Discord en directo y avisar previamente por WhatsApp.",
        ],
        "visual_blocks": [
            {
                "title": "Disciplina General",
                "items": [
                    "No se permiten intercambios.",
                    "Un Pokemon eliminado por juicio o ilegalidad no puede volver a pertenecer al mismo entrenador.",
                    "Esta prohibido explotar el juego o forzar encuentros no random.",
                    "Las tiendas especiales solo permiten 1 compra y objetos como Master Ball solo 1 vez.",
                    "Se permiten combates de practica entre ligas y los comodines pueden usarse sobre uno mismo o sobre otros.",
                    "Robar no puede usarse dos veces seguidas sobre el mismo jugador.",
                    "Queda prohibido practicar con equipos ajenos o usar calculos de da\u00f1o externos al showdown.",
                    "Si alguien detecta un vacio legal, debe avisar al grupo y se resolvera por votacion.",
                    "Los jugadores deben jugar en directo por Discord y avisar previamente por WhatsApp.",
                ],
            }
        ],
    },
]


def _section_text(section: dict) -> str:
    return "\n".join(section.get("text_lines") or []).strip()


def get_normativa_text() -> str:
    body = "\n\n".join(_section_text(section) for section in NORMATIVA_SECTIONS).strip()
    return f"Normativa ChampionsLocke\n\n{body}".strip()


def get_normativa_section_payloads() -> dict[str, dict[str, str]]:
    payloads: dict[str, dict[str, str]] = {}
    for section in NORMATIVA_SECTIONS:
        payloads[str(section["id"])] = {
            "title": str(section.get("bot_title") or section.get("tab") or section["id"]),
            "text": _section_text(section),
        }
    return payloads


def _render_normativa_css() -> None:
    st.markdown(
        """
        <style>
        .norma-hero {
          position: relative;
          overflow: hidden;
          border: 1px solid var(--bw2-edge);
          background:
            radial-gradient(circle at top right, rgba(110,168,255,0.24) 0 110px, transparent 170px),
            radial-gradient(circle at bottom left, rgba(245,125,49,0.18) 0 120px, transparent 180px),
            linear-gradient(135deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 62%, #10151b 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.32);
          padding: 18px 18px 16px;
          margin-bottom: 14px;
        }
        .norma-hero:after {
          content: "";
          position: absolute;
          width: 128px;
          height: 128px;
          right: -26px;
          top: -30px;
          border-radius: 50%;
          background:
            radial-gradient(circle at center, rgba(255,255,255,0.78) 0 10px, rgba(255,255,255,0.16) 11px 26px, transparent 27px),
            radial-gradient(circle at center, rgba(245,125,49,0.5) 0 44px, rgba(245,125,49,0.14) 45px 60px, transparent 61px);
          opacity: 0.72;
          transform: rotate(-16deg);
        }
        .norma-kicker {
          display: inline-block;
          padding: 6px 10px;
          border: 1px solid var(--bw2-edge-strong);
          background: linear-gradient(180deg, var(--accent) 0%, var(--accent-dark) 100%);
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          font-weight: 700;
          text-transform: uppercase;
          clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
        }
        .norma-title {
          margin-top: 14px;
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 18px;
          line-height: 1.45;
          text-transform: uppercase;
        }
        .norma-subtitle {
          margin-top: 10px;
          max-width: 920px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 22px;
          line-height: 1.25;
        }
        .norma-chip-row {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 14px;
        }
        .norma-chip {
          padding: 6px 10px;
          border: 1px solid rgba(255,255,255,0.14);
          background: linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%);
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        .norma-summary {
          margin-bottom: 12px;
          padding: 10px 12px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 20px;
          line-height: 1.25;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.07);
        }
        .norma-eyebrow {
          display: inline-block;
          margin-bottom: 10px;
          padding: 5px 9px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-panel-3) 0%, var(--bw2-panel) 100%);
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        .norma-block {
          height: 100%;
          margin-bottom: 12px;
          border: 1px solid var(--bw2-edge);
          background: linear-gradient(180deg, var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(0,0,0,0.28);
        }
        .norma-block-head {
          padding: 8px 10px;
          border-bottom: 1px solid rgba(255,255,255,0.08);
          background: linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(0,0,0,0.03) 100%);
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 10px;
          text-transform: uppercase;
        }
        .norma-block-body {
          padding: 12px;
        }
        .norma-list {
          display: grid;
          gap: 8px;
        }
        .norma-list-item {
          display: grid;
          grid-template-columns: 16px 1fr;
          gap: 10px;
          color: var(--bw2-text-soft);
          font-family: var(--font-ui);
          font-size: 20px;
          line-height: 1.15;
        }
        .norma-list-bullet {
          color: var(--accent-soft);
          font-family: var(--font-pixel);
          font-size: 12px;
          line-height: 1.7;
        }
        .norma-row-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
          gap: 8px;
        }
        .norma-row-card {
          padding: 10px 10px 8px;
          border: 1px solid rgba(255,255,255,0.08);
          background: linear-gradient(180deg, var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
          text-align: center;
        }
        .norma-row-label {
          color: var(--bw2-text-soft);
          font-family: var(--font-pixel);
          font-size: 9px;
          text-transform: uppercase;
        }
        .norma-row-value {
          margin-top: 7px;
          color: #ffffff;
          font-family: var(--font-pixel);
          font-size: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_list_block(block: dict) -> None:
    items_html = "".join(
        (
            "<div class='norma-list-item'>"
            "<div class='norma-list-bullet'>>></div>"
            f"<div>{escape(item)}</div>"
            "</div>"
        )
        for item in block.get("items") or []
    )
    st.markdown(
        (
            "<div class='norma-block'>"
            f"<div class='norma-block-head'>{escape(str(block.get('title') or 'Bloque'))}</div>"
            f"<div class='norma-block-body'><div class='norma-list'>{items_html}</div></div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_rows_block(block: dict) -> None:
    rows_html = "".join(
        (
            "<div class='norma-row-card'>"
            f"<div class='norma-row-label'>{escape(str(label))}</div>"
            f"<div class='norma-row-value'>{escape(str(value))}</div>"
            "</div>"
        )
        for label, value in (block.get("rows") or [])
    )
    st.markdown(
        (
            "<div class='norma-block'>"
            f"<div class='norma-block-head'>{escape(str(block.get('title') or 'Valores'))}</div>"
            f"<div class='norma-block-body'><div class='norma-row-grid'>{rows_html}</div></div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_section(section: dict) -> None:
    st.markdown(
        (
            f"<div class='norma-eyebrow'>{escape(str(section.get('eyebrow') or 'Seccion'))}</div>"
            f"<div class='norma-summary'>{escape(str(section.get('summary') or ''))}</div>"
        ),
        unsafe_allow_html=True,
    )
    blocks = list(section.get("visual_blocks") or [])
    if not blocks:
        return
    for idx in range(0, len(blocks), 2):
        pair = blocks[idx: idx + 2]
        cols = st.columns(len(pair))
        for col, block in zip(cols, pair):
            with col:
                if block.get("rows"):
                    _render_rows_block(block)
                else:
                    _render_list_block(block)


def render_normativa_home() -> None:
    _render_normativa_css()
    st.markdown(
        """
        <div class='norma-hero'>
          <div class='norma-kicker'>Normativa ChampionsLocke</div>
          <div class='norma-title'>Panel reglamentario de temporada</div>
          <div class='norma-subtitle'>
            Todo el reglamento de la liga concentrado en una portada mas legible,
            visual y alineada con la interfaz de PokeApp.
          </div>
          <div class='norma-chip-row'>
            <div class='norma-chip'>7 bloques clave</div>
            <div class='norma-chip'>8 gimnasios + liga final</div>
            <div class='norma-chip'>Sistema A/B, puntos y monedas</div>
            <div class='norma-chip'>Comodines, castigos y disciplina</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    tabs = st.tabs([str(section.get("tab") or section.get("bot_title") or section["id"]) for section in NORMATIVA_SECTIONS])
    for tab, section in zip(tabs, NORMATIVA_SECTIONS):
        with tab:
            _render_section(section)


NORMATIVA_MD = get_normativa_text()
