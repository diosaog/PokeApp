from __future__ import annotations

from html import escape

import streamlit as st


NORMATIVA_SECTIONS = [
    {
        "id": "nuzlocke",
        "tab": "Nuzlocke",
        "tab_label": "Normas Nuzlocke",
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
            "- Movimientos baneados: Esquema (Unicamente la MT, en el recuerdamovimientos si se puede) y Brecha Negra en combates dobles contra jugadores.",
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
                    "Baneados: Slaking, Deoxys, Esquema (solo la MT), Brecha Negra en dobles contra jugadores y Rocio Bondad.",
                    "Pokemon transferido: no puede ser pseudo-legendario ni legendario y arrastra 1 ataque anterior + 2 random + habilidad random.",
                ],
            },
        ],
    },
    {
        "id": "equipo",
        "tab": "Equipo",
        "tab_label": "Equipo Legal",
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
        "tab_label": "Tramos Liga",
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
            "- En combates contra jugadores se aplican Item Clause y Sleep Clause.",
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
                    "En combates contra jugadores se aplican Item Clause y Sleep Clause.",
                ],
            },
        ],
    },
    {
        "id": "caps",
        "tab": "Level Caps",
        "tab_label": "Level Caps",
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
        "tab_label": "Liga A / B",
        "bot_title": "Divisiones, puntos y monedas",
        "eyebrow": "Sistema de Clasificacion",
        "summary": "Distribucion de divisiones, scoring global y economia oficial de la liga.",
        "text_lines": [
            "6. Divisiones (Liga A / B)",
            "- La temporada empieza con 10 jugadores activos.",
            "- Liga A tiene 5 jugadores y Liga B tiene 5 jugadores.",
            "- Los jugadores solo se enfrentan contra rivales de su propia division.",
            "- Descienden los 3 ultimos de Liga A y ascienden los 3 primeros de Liga B.",
            "- El ultimo de Liga B recibe Robar Pokemon.",
            "- La Liga A/B de esta temporada finaliza al cerrar la jornada 4.",
            "- Puntos oficiales por posicion",
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
            "- Monedas oficiales por posicion",
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
            "7. Monedas",
            "- Medallas: 4 monedas por cada medalla (max 8).",
            "- Saldo total = medallas*4 + monedas de liga - monedas gastadas.",
        ],
        "visual_blocks": [
            {
                "title": "Divisiones",
                "items": [
                    "La temporada empieza con 10 jugadores activos.",
                    "Liga A tiene 5 jugadores y Liga B tiene 5 jugadores.",
                    "Los jugadores solo se enfrentan contra rivales de su propia division.",
                    "Descienden los 3 ultimos de Liga A y ascienden los 3 primeros de Liga B.",
                    "El ultimo de Liga B recibe Robar Pokemon.",
                    "La Liga A/B de esta temporada finaliza al cerrar la jornada 4.",
                ],
            },
            {
                "title": "Puntos Oficiales",
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
                "title": "Monedas Oficiales",
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
        "tab_label": "Comodines",
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
        "tab_label": "Normas Generales",
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
        .main .rulebook-hero {
          position: relative;
          overflow: hidden;
          min-height: 170px;
          margin: 0 0 16px;
          padding: 22px;
          border: 1px solid rgba(139,171,216,0.20);
          border-left: 5px solid var(--primary, #4d8dff);
          border-radius: 18px;
          background:
            linear-gradient(118deg, rgba(77,141,255,0.18) 0 34%, transparent 34% 100%),
            linear-gradient(300deg, rgba(255,210,77,0.10), transparent 46%),
            linear-gradient(180deg, rgba(18,30,49,0.98), rgba(7,12,22,0.99));
          box-shadow: var(--poke-shadow-card, 0 14px 30px rgba(0,0,0,0.24));
        }
        .main .rulebook-hero::before {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background:
            linear-gradient(90deg, rgba(255,255,255,0.026) 0 1px, transparent 1px 100%) 0 0 / 30px 100%,
            linear-gradient(180deg, rgba(255,255,255,0.022) 0 1px, transparent 1px 100%) 0 0 / 100% 26px;
          opacity: .62;
        }
        .main .rulebook-hero::after {
          content: "RULEBOOK";
          position: absolute;
          right: 22px;
          bottom: -8px;
          color: rgba(255,255,255,0.045);
          font-family: var(--font-ui);
          font-size: clamp(46px, 8vw, 106px);
          font-weight: 950;
          line-height: 1;
          letter-spacing: 0;
          pointer-events: none;
        }
        .main .rulebook-hero-content {
          position: relative;
          z-index: 1;
          max-width: 920px;
        }
        .main .rulebook-kicker-row,
        .main .rulebook-metric-row,
        .main .rulebook-section-meta {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
        }
        .main .rulebook-kicker,
        .main .rulebook-chip,
        .main .rulebook-section-code,
        .main .rulebook-block-code {
          display: inline-flex;
          align-items: center;
          min-height: 24px;
          padding: 4px 9px;
          border: 1px solid rgba(139,171,216,0.18);
          border-radius: 999px;
          background: rgba(255,255,255,0.045);
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-family: var(--font-pixel);
          font-size: 9px;
          font-weight: 900;
          text-transform: uppercase;
        }
        .main .rulebook-kicker {
          border-color: rgba(114,185,255,0.30);
          background: rgba(77,141,255,0.11);
          color: var(--primary-hover, #72b9ff);
          -webkit-text-fill-color: var(--primary-hover, #72b9ff);
        }
        .main .rulebook-title {
          margin: 14px 0 8px;
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-family: var(--font-ui);
          font-size: clamp(30px, 4.8vw, 56px);
          font-weight: 950;
          line-height: .98;
          letter-spacing: 0;
          text-transform: none;
        }
        .main .rulebook-subtitle {
          max-width: 760px;
          margin: 0;
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-size: 15px;
          font-weight: 650;
          line-height: 1.42;
        }
        .main .rulebook-metric-row {
          margin-top: 16px;
        }
        .main .rulebook-metric {
          min-width: 116px;
          padding: 9px 11px;
          border: 1px solid rgba(139,171,216,0.14);
          border-radius: 13px;
          background: rgba(255,255,255,0.04);
        }
        .main .rulebook-metric span {
          display: block;
          color: var(--text-muted, #77879e);
          -webkit-text-fill-color: var(--text-muted, #77879e);
          font-size: 10px;
          font-weight: 900;
          text-transform: uppercase;
        }
        .main .rulebook-metric strong {
          display: block;
          margin-top: 5px;
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-size: 18px;
          font-weight: 950;
          font-variant-numeric: tabular-nums;
        }
        .main .rulebook-index {
          margin: 0 0 14px;
          padding: 14px;
          border: 1px solid rgba(139,171,216,0.16);
          border-radius: 16px;
          background:
            linear-gradient(135deg, rgba(77,141,255,0.075), transparent 44%),
            rgba(10,17,29,0.95);
        }
        .main .rulebook-index-title {
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-size: 16px;
          font-weight: 950;
        }
        .main .rulebook-index-copy {
          margin-top: 3px;
          color: var(--text-muted, #77879e);
          -webkit-text-fill-color: var(--text-muted, #77879e);
          font-size: 13px;
          font-weight: 700;
        }
        .main .rulebook-nav-slot {
          display: none;
        }
        .main div[data-testid="column"]:has(.rulebook-nav-slot) div.stButton > button {
          min-height: 46px !important;
          justify-content: flex-start !important;
          padding: 0 13px !important;
          border: 1px solid rgba(139,171,216,0.16) !important;
          border-radius: 13px !important;
          background:
            linear-gradient(135deg, rgba(255,255,255,0.045), transparent 58%),
            rgba(11,19,32,0.92) !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.045) !important;
        }
        .main div[data-testid="column"]:has(.rulebook-nav-slot) div.stButton > button p {
          color: var(--text-secondary, #b8c7dc) !important;
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc) !important;
          font-size: 12px !important;
          font-weight: 900 !important;
          line-height: 1.12 !important;
          text-align: left !important;
        }
        .main div[data-testid="column"]:has(.rulebook-nav-slot.is-active) div.stButton > button {
          border-color: rgba(114,185,255,0.55) !important;
          background:
            linear-gradient(90deg, rgba(77,141,255,0.20), transparent 62%),
            rgba(13,27,49,0.98) !important;
          box-shadow: inset 4px 0 0 var(--primary, #4d8dff), inset 0 1px 0 rgba(255,255,255,0.08) !important;
        }
        .main div[data-testid="column"]:has(.rulebook-nav-slot.is-active) div.stButton > button p {
          color: var(--text-primary, #f6f9ff) !important;
          -webkit-text-fill-color: var(--text-primary, #f6f9ff) !important;
        }
        .main .rulebook-document {
          position: relative;
          overflow: hidden;
          margin-top: 16px;
          padding: 18px;
          border: 1px solid rgba(139,171,216,0.18);
          border-radius: 18px;
          background:
            linear-gradient(135deg, rgba(77,141,255,0.09), transparent 42%),
            linear-gradient(180deg, rgba(18,30,49,0.96), rgba(7,12,22,0.98));
          box-shadow: var(--poke-shadow-card, 0 14px 30px rgba(0,0,0,0.24));
        }
        .main .rulebook-document::before {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background:
            linear-gradient(90deg, rgba(255,255,255,0.018) 0 1px, transparent 1px 100%) 0 0 / 34px 100%,
            linear-gradient(180deg, rgba(255,255,255,0.018) 0 1px, transparent 1px 100%) 0 0 / 100% 28px;
          opacity: .55;
        }
        .main .rulebook-document > * {
          position: relative;
          z-index: 1;
        }
        .main .rulebook-section-head {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 14px;
          align-items: end;
          padding: 0 0 14px;
          border-bottom: 1px solid rgba(139,171,216,0.14);
        }
        .main .rulebook-section-code {
          width: fit-content;
          border-color: rgba(255,210,77,0.32);
          background: rgba(255,210,77,0.10);
          color: var(--pokemon-yellow, #ffd24d);
          -webkit-text-fill-color: var(--pokemon-yellow, #ffd24d);
        }
        .main .rulebook-section-title {
          margin-top: 10px;
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-size: clamp(24px, 3vw, 38px);
          font-weight: 950;
          line-height: 1.04;
        }
        .main .rulebook-section-summary {
          max-width: 780px;
          margin-top: 8px;
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-size: 15px;
          line-height: 1.42;
        }
        .main .rulebook-section-meta {
          justify-content: flex-end;
        }
        .main .rulebook-block-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
          gap: 12px;
          margin-top: 14px;
        }
        .main .rulebook-block {
          overflow: hidden;
          border: 1px solid rgba(139,171,216,0.15);
          border-radius: 15px;
          background:
            linear-gradient(135deg, rgba(255,255,255,0.045), transparent 44%),
            rgba(8,14,26,0.78);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.055);
        }
        .main .rulebook-block-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          min-height: 42px;
          padding: 10px 12px;
          border-bottom: 1px solid rgba(139,171,216,0.12);
          background: rgba(255,255,255,0.035);
        }
        .main .rulebook-block-title {
          min-width: 0;
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-size: 14px;
          font-weight: 950;
          line-height: 1.15;
        }
        .main .rulebook-block-code {
          flex: 0 0 auto;
          min-height: 22px;
          padding: 3px 7px;
          color: var(--primary-hover, #72b9ff);
          -webkit-text-fill-color: var(--primary-hover, #72b9ff);
        }
        .main .rulebook-article-list {
          display: grid;
          gap: 7px;
          padding: 12px;
        }
        .main .rulebook-article {
          display: grid;
          grid-template-columns: 76px minmax(0, 1fr);
          gap: 10px;
          align-items: start;
          min-height: 42px;
          padding: 9px 10px;
          border: 1px solid rgba(139,171,216,0.11);
          border-radius: 12px;
          background: rgba(255,255,255,0.032);
        }
        .main .rulebook-article-no {
          color: var(--primary-hover, #72b9ff);
          -webkit-text-fill-color: var(--primary-hover, #72b9ff);
          font-family: var(--font-pixel);
          font-size: 9px;
          font-weight: 900;
          line-height: 1.5;
          text-transform: uppercase;
          white-space: nowrap;
        }
        .main .rulebook-article-text {
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-size: 14px;
          font-weight: 650;
          line-height: 1.38;
        }
        .main .rulebook-table-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(92px, 1fr));
          gap: 8px;
          padding: 12px;
        }
        .main .rulebook-row-card {
          min-height: 66px;
          padding: 9px 10px;
          border: 1px solid rgba(139,171,216,0.12);
          border-radius: 12px;
          background:
            radial-gradient(circle at 100% 0%, rgba(255,210,77,0.10), transparent 58%),
            rgba(255,255,255,0.035);
        }
        .main .rulebook-row-card span {
          display: block;
          color: var(--text-muted, #77879e);
          -webkit-text-fill-color: var(--text-muted, #77879e);
          font-size: 10px;
          font-weight: 900;
          text-transform: uppercase;
        }
        .main .rulebook-row-card strong {
          display: block;
          margin-top: 8px;
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-size: 20px;
          font-weight: 950;
          font-variant-numeric: tabular-nums;
        }
        @media (max-width: 980px) {
          .main .rulebook-section-head {
            grid-template-columns: 1fr;
          }
          .main .rulebook-section-meta {
            justify-content: flex-start;
          }
        }
        @media (max-width: 720px) {
          .main .rulebook-hero,
          .main .rulebook-document,
          .main .rulebook-index {
            border-radius: 14px;
            padding: 14px;
          }
          .main .rulebook-block-grid {
            grid-template-columns: 1fr;
          }
          .main .rulebook-article {
            grid-template-columns: 1fr;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _section_title(section: dict) -> str:
    return str(
        section.get("tab_label")
        or section.get("tab")
        or section.get("bot_title")
        or section.get("id")
        or "Seccion"
    )


def _article_count(section: dict) -> int:
    return sum(len(block.get("items") or []) for block in section.get("visual_blocks") or [])


def _table_count(section: dict) -> int:
    return sum(len(block.get("rows") or []) for block in section.get("visual_blocks") or [])


def _total_articles() -> int:
    return sum(_article_count(section) for section in NORMATIVA_SECTIONS)


def _active_section() -> tuple[int, dict]:
    first_id = str(NORMATIVA_SECTIONS[0]["id"])
    active_id = str(st.session_state.get("normativa_rulebook_section") or first_id)
    for index, section in enumerate(NORMATIVA_SECTIONS):
        if str(section.get("id")) == active_id:
            return index, section
    st.session_state["normativa_rulebook_section"] = first_id
    return 0, NORMATIVA_SECTIONS[0]


def _render_rulebook_nav(active_id: str) -> None:
    st.markdown(
        """
        <div class='rulebook-index'>
          <div class='rulebook-index-title'>Indice del reglamento</div>
          <div class='rulebook-index-copy'>Selecciona un capitulo para consultar sus articulos oficiales.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for row_start in range(0, len(NORMATIVA_SECTIONS), 4):
        row_sections = NORMATIVA_SECTIONS[row_start: row_start + 4]
        cols = st.columns(4)
        for offset, col in enumerate(cols):
            if offset >= len(row_sections):
                continue
            section = row_sections[offset]
            section_index = row_start + offset
            section_id = str(section.get("id"))
            active = section_id == active_id
            label = f"CAP. {section_index + 1:02d} - {_section_title(section)}"
            with col:
                st.markdown(
                    f"<span class='rulebook-nav-slot{' is-active' if active else ''}'></span>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    label,
                    key=f"normativa_rulebook_nav_{section_id}",
                    type="primary" if active else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["normativa_rulebook_section"] = section_id
                    st.rerun()


def _render_list_block_html(block: dict, *, block_no: int, start_at: int) -> tuple[str, int]:
    items = list(block.get("items") or [])
    articles_html = "".join(
        (
            "<div class='rulebook-article'>"
            f"<span class='rulebook-article-no'>ART. {start_at + idx:02d}</span>"
            f"<span class='rulebook-article-text'>{escape(str(item))}</span>"
            "</div>"
        )
        for idx, item in enumerate(items)
    )
    return (
        (
            "<article class='rulebook-block'>"
            "<div class='rulebook-block-head'>"
            f"<div class='rulebook-block-title'>{escape(str(block.get('title') or 'Bloque'))}</div>"
            f"<span class='rulebook-block-code'>B{block_no:02d}</span>"
            "</div>"
            f"<div class='rulebook-article-list'>{articles_html}</div>"
            "</article>"
        ),
        start_at + len(items),
    )


def _render_rows_block_html(block: dict, *, block_no: int) -> str:
    rows_html = "".join(
        (
            "<div class='rulebook-row-card'>"
            f"<span>{escape(str(label))}</span>"
            f"<strong>{escape(str(value))}</strong>"
            "</div>"
        )
        for label, value in (block.get("rows") or [])
    )
    return (
        "<article class='rulebook-block rulebook-block-table'>"
        "<div class='rulebook-block-head'>"
        f"<div class='rulebook-block-title'>{escape(str(block.get('title') or 'Valores'))}</div>"
        f"<span class='rulebook-block-code'>T{block_no:02d}</span>"
        "</div>"
        f"<div class='rulebook-table-grid'>{rows_html}</div>"
        "</article>"
    )


def _render_section(section: dict, *, index: int) -> None:
    blocks = list(section.get("visual_blocks") or [])
    block_html: list[str] = []
    article_no = 1
    for block_no, block in enumerate(blocks, start=1):
        if block.get("rows"):
            block_html.append(_render_rows_block_html(block, block_no=block_no))
        else:
            html, article_no = _render_list_block_html(
                block,
                block_no=block_no,
                start_at=article_no,
            )
            block_html.append(html)
    st.markdown(
        (
            "<section class='rulebook-document'>"
            "<div class='rulebook-section-head'>"
            "<div>"
            f"<span class='rulebook-section-code'>CAP. {index + 1:02d}</span>"
            f"<div class='rulebook-section-title'>{escape(_section_title(section))}</div>"
            f"<div class='rulebook-section-summary'>{escape(str(section.get('summary') or ''))}</div>"
            "</div>"
            "<div class='rulebook-section-meta'>"
            f"<span class='rulebook-chip'>{len(blocks)} bloques</span>"
            f"<span class='rulebook-chip'>{_article_count(section)} articulos</span>"
            f"<span class='rulebook-chip'>{_table_count(section)} valores</span>"
            "</div>"
            "</div>"
            f"<div class='rulebook-block-grid'>{''.join(block_html)}</div>"
            "</section>"
        ),
        unsafe_allow_html=True,
    )


def render_normativa_home() -> None:
    _render_normativa_css()
    active_index, active = _active_section()
    st.markdown(
        (
            "<section class='rulebook-hero'>"
            "<div class='rulebook-hero-content'>"
            "<div class='rulebook-kicker-row'>"
            "<span class='rulebook-kicker'>Manual oficial</span>"
            "<span class='rulebook-chip'>Competicion Pokemon</span>"
            "<span class='rulebook-chip'>Temporada vigente</span>"
            "</div>"
            "<div class='rulebook-title'>Normativa oficial</div>"
            "<p class='rulebook-subtitle'>Reglamento de liga organizado por capitulos, articulos y tablas de valores. Pensado para consultar rapido sin perder el tono premium de PokeApp 2.0.</p>"
            "<div class='rulebook-metric-row'>"
            f"<div class='rulebook-metric'><span>Capitulos</span><strong>{len(NORMATIVA_SECTIONS)}</strong></div>"
            f"<div class='rulebook-metric'><span>Articulos</span><strong>{_total_articles()}</strong></div>"
            "<div class='rulebook-metric'><span>Formato</span><strong>Oficial</strong></div>"
            "</div>"
            "</div>"
            "</section>"
        ),
        unsafe_allow_html=True,
    )
    _render_rulebook_nav(str(active.get("id")))
    _render_section(active, index=active_index)


NORMATIVA_MD = get_normativa_text()
