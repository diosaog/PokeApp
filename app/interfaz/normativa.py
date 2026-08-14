from __future__ import annotations

from copy import deepcopy
from html import escape

import streamlit as st

from app.season.config import current_season_version


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


def _configured_structure_section(section: dict) -> dict:
    try:
        version = current_season_version()
    except Exception:
        return section
    round_count = int(version.max_rounds)
    section = dict(section)
    section["text_lines"] = [
        "3. Estructura por tramos",
        f"- La partida se divide en {round_count} tramos mas una Liga Pokemon final.",
        "- Cada tramo finaliza tras superar determinados gimnasios.",
        "- Al cierre de cada tramo se disputa una liga competitiva entre jugadores.",
        "",
        "4. Combates entre jugadores",
        "- Liga: combates 1 vs 1, formato Bo1.",
        "- Copa: se juega tras completar la Liga Pokemon. Formato eliminatorio, Bo3.",
        "- En combates contra jugadores se aplican Item Clause y Sleep Clause.",
    ]
    visual_blocks = []
    for block in section.get("visual_blocks") or []:
        block = dict(block)
        if str(block.get("title") or "") == "Estructura del Recorrido":
            block["items"] = [
                f"La partida se divide en {round_count} tramos mas una Liga Pokemon final.",
                "Cada tramo finaliza tras superar determinados gimnasios.",
                "Al cierre de cada tramo se disputa una liga competitiva entre jugadores.",
            ]
        visual_blocks.append(block)
    section["visual_blocks"] = visual_blocks
    return section


def _configured_liga_section(section: dict) -> dict:
    try:
        version = current_season_version()
    except Exception:
        return section

    sizes = list(version.division_sizes or [5, 5])
    while len(sizes) < 2:
        sizes.append(0)
    a_size, b_size = int(sizes[0]), int(sizes[1])
    player_count = len(version.players)
    movement = min(max(int(version.movement_count or 0), 0), a_size, b_size)
    steal_enabled = bool((version.rules or {}).get("last_b_gets_steal"))
    steal_line = (
        "El ultimo de Liga B recibe Robar Pokemon."
        if steal_enabled
        else "El ultimo de Liga B no recibe Robar Pokemon en esta version."
    )
    point_rows = [
        (str(pos), str(value))
        for pos, value in sorted(version.points_by_position.items())
        if 1 <= int(pos) <= max(player_count, 1)
    ]
    coin_rows = [
        (str(pos), str(value))
        for pos, value in sorted(version.coins_by_position.items())
        if 1 <= int(pos) <= max(player_count, 1)
    ]
    section = dict(section)
    section["summary"] = "Distribucion de divisiones, scoring global y economia oficial de la temporada activa."
    section["text_lines"] = [
        "6. Divisiones (Liga A / B)",
        f"- La temporada tiene {player_count} jugadores activos configurados.",
        f"- Liga A tiene {a_size} jugadores y Liga B tiene {b_size} jugadores.",
        "- Los jugadores solo se enfrentan contra rivales de su propia division.",
        f"- Descienden los {movement} ultimos de Liga A y ascienden los {movement} primeros de Liga B.",
        f"- {steal_line}",
        f"- La Liga A/B de esta temporada finaliza al cerrar la jornada {int(version.max_rounds)}.",
        "- Puntos oficiales por posicion",
        "",
        *[f"{pos}: {value} /" for pos, value in point_rows],
        "",
        "- Monedas oficiales por posicion",
        "",
        *[f"{pos}: {value} /" for pos, value in coin_rows],
        "",
        "7. Monedas",
        "- Medallas: 4 monedas por cada medalla (max 8).",
        "- Saldo total = medallas*4 + monedas de liga - monedas gastadas.",
    ]
    section["visual_blocks"] = [
        {
            "title": "Divisiones",
            "items": [
                f"La temporada tiene {player_count} jugadores activos configurados.",
                f"Liga A tiene {a_size} jugadores y Liga B tiene {b_size} jugadores.",
                "Los jugadores solo se enfrentan contra rivales de su propia division.",
                f"Descienden los {movement} ultimos de Liga A y ascienden los {movement} primeros de Liga B.",
                steal_line,
                f"La Liga A/B de esta temporada finaliza al cerrar la jornada {int(version.max_rounds)}.",
            ],
        },
        {"title": "Puntos Oficiales", "rows": point_rows},
        {"title": "Monedas Oficiales", "rows": coin_rows},
        {
            "title": "Economia Base",
            "items": [
                "Medallas: 4 monedas por cada medalla (max 8).",
                "Saldo total = medallas*4 + monedas de liga - monedas gastadas.",
            ],
        },
    ]
    return section


def normativa_sections() -> list[dict]:
    sections = deepcopy(NORMATIVA_SECTIONS)
    for index, section in enumerate(sections):
        section_id = str(section.get("id"))
        if section_id == "estructura":
            sections[index] = _configured_structure_section(section)
        elif section_id == "liga":
            sections[index] = _configured_liga_section(section)
    return sections


def get_normativa_text() -> str:
    body = "\n\n".join(_section_text(section) for section in normativa_sections()).strip()
    return f"Normativa ChampionsLocke\n\n{body}".strip()


def get_normativa_section_payloads() -> dict[str, dict[str, str]]:
    payloads: dict[str, dict[str, str]] = {}
    for section in normativa_sections():
        payloads[str(section["id"])] = {
            "title": str(section.get("bot_title") or section.get("tab") or section["id"]),
            "text": _section_text(section),
        }
    return payloads


def _render_normativa_css() -> None:
    st.markdown(
        """
        <style>
        .rulebook-hero,
        .rulebook-index,
        .rulebook-document {
          width: min(100%, 1160px);
          margin-left: auto;
          margin-right: auto;
        }
        .rulebook-hero {
          position: relative;
          overflow: hidden;
          display: grid;
          grid-template-columns: minmax(0, 1fr) 180px;
          gap: 18px;
          align-items: stretch;
          margin-bottom: 14px;
          padding: 18px;
          border: 1px solid rgba(139,171,216,0.22);
          border-left: 5px solid var(--primary, #4d8dff);
          border-radius: 18px;
          background:
            linear-gradient(118deg, rgba(77,141,255,0.15) 0 32%, transparent 32% 100%),
            linear-gradient(300deg, rgba(255,210,77,0.08), transparent 50%),
            linear-gradient(180deg, rgba(18,30,49,0.98), rgba(7,12,22,0.99));
          box-shadow: var(--poke-shadow-card, 0 14px 30px rgba(0,0,0,0.24));
        }
        .rulebook-hero::before,
        .rulebook-document::before {
          content: "";
          position: absolute;
          inset: 0;
          pointer-events: none;
          background:
            linear-gradient(90deg, rgba(255,255,255,0.024) 0 1px, transparent 1px 100%) 0 0 / 30px 100%,
            linear-gradient(180deg, rgba(255,255,255,0.020) 0 1px, transparent 1px 100%) 0 0 / 100% 26px;
          opacity: .55;
        }
        .rulebook-hero-content,
        .rulebook-hero-seal,
        .rulebook-document > * {
          position: relative;
          z-index: 1;
        }
        .rulebook-eyebrow-row,
        .rulebook-chapter-facts {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
        }
        .rulebook-eyebrow,
        .rulebook-chip,
        .rulebook-chapter-code,
        .rulebook-block-code,
        .rulebook-table-code {
          display: inline-flex;
          align-items: center;
          width: fit-content;
          min-height: 22px;
          padding: 4px 9px;
          border: 1px solid rgba(139,171,216,0.18);
          border-radius: 999px;
          background: rgba(255,255,255,0.045);
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-family: var(--font-pixel);
          font-size: 8.5px;
          font-weight: 900;
          text-transform: uppercase;
        }
        .rulebook-eyebrow,
        .rulebook-chapter-code {
          border-color: rgba(114,185,255,0.30);
          background: rgba(77,141,255,0.11);
          color: var(--primary-hover, #72b9ff);
          -webkit-text-fill-color: var(--primary-hover, #72b9ff);
        }
        .rulebook-title {
          margin: 12px 0 8px;
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-family: var(--font-ui);
          font-size: clamp(32px, 4.2vw, 52px);
          font-weight: 950;
          line-height: 1;
          letter-spacing: 0;
          text-transform: none;
        }
        .rulebook-subtitle {
          max-width: 700px;
          margin: 0;
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-size: 15px;
          font-weight: 650;
          line-height: 1.42;
        }
        .rulebook-meta-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(118px, 1fr));
          gap: 9px;
          max-width: 540px;
          margin-top: 16px;
        }
        .rulebook-meta-card {
          min-height: 62px;
          padding: 10px 12px;
          border: 1px solid rgba(139,171,216,0.14);
          border-radius: 13px;
          background:
            linear-gradient(135deg, rgba(255,255,255,0.055), transparent 62%),
            rgba(255,255,255,0.032);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.045);
        }
        .rulebook-meta-card span,
        .rulebook-chapter-fact span {
          display: block;
          color: var(--text-muted, #77879e);
          -webkit-text-fill-color: var(--text-muted, #77879e);
          font-size: 10px;
          font-weight: 900;
          text-transform: uppercase;
        }
        .rulebook-meta-card strong,
        .rulebook-chapter-fact strong {
          display: block;
          margin-top: 5px;
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-size: 19px;
          font-weight: 950;
          font-variant-numeric: tabular-nums;
        }
        .rulebook-hero-seal {
          display: grid;
          align-content: center;
          justify-items: center;
          min-height: 150px;
          border: 1px solid rgba(139,171,216,0.16);
          border-radius: 16px;
          background:
            radial-gradient(circle at 50% 32%, rgba(255,255,255,0.12), transparent 38%),
            linear-gradient(135deg, rgba(77,141,255,0.10), rgba(255,210,77,0.06)),
            rgba(255,255,255,0.032);
        }
        .rulebook-seal-mark {
          display: grid;
          place-items: center;
          width: 72px;
          height: 72px;
          border: 2px solid rgba(246,249,255,0.28);
          border-radius: 50%;
          color: rgba(246,249,255,0.92);
          -webkit-text-fill-color: rgba(246,249,255,0.92);
          font-size: 34px;
          font-weight: 950;
          box-shadow: inset 0 -20px 0 rgba(255,255,255,0.055);
        }
        .rulebook-seal-text {
          margin-top: 10px;
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-family: var(--font-pixel);
          font-size: 9px;
          font-weight: 900;
          text-align: center;
          text-transform: uppercase;
        }
        .rulebook-index {
          margin: 0 0 14px;
          padding: 13px 14px 12px;
          border: 1px solid rgba(139,171,216,0.16);
          border-radius: 16px;
          background:
            linear-gradient(135deg, rgba(77,141,255,0.075), transparent 44%),
            rgba(10,17,29,0.95);
        }
        .rulebook-index-head {
          display: flex;
          align-items: end;
          justify-content: space-between;
          gap: 12px;
          margin-bottom: 10px;
          padding-bottom: 10px;
          border-bottom: 1px solid rgba(139,171,216,0.12);
        }
        .rulebook-index-title {
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-size: 17px;
          font-weight: 950;
        }
        .rulebook-index-copy {
          margin-top: 3px;
          color: var(--text-muted, #77879e);
          -webkit-text-fill-color: var(--text-muted, #77879e);
          font-size: 13px;
          font-weight: 700;
        }
        .rulebook-index-badge {
          flex: 0 0 auto;
          color: var(--pokemon-yellow, #ffd24d);
          -webkit-text-fill-color: var(--pokemon-yellow, #ffd24d);
          font-family: var(--font-pixel);
          font-size: 9px;
          font-weight: 900;
          text-transform: uppercase;
        }
        .rulebook-chapter-slot {
          display: none;
        }
        div[data-testid="column"]:has(.rulebook-chapter-slot) {
          min-width: 0 !important;
        }
        div[data-testid="column"]:has(.rulebook-chapter-slot) div.stButton > button {
          min-height: 42px !important;
          justify-content: flex-start !important;
          padding: 0 11px !important;
          border: 1px solid rgba(139,171,216,0.16) !important;
          border-radius: 12px !important;
          background:
            linear-gradient(135deg, rgba(255,255,255,0.04), transparent 58%),
            rgba(12,21,36,0.94) !important;
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.04) !important;
        }
        div[data-testid="column"]:has(.rulebook-chapter-slot) div.stButton > button p {
          color: var(--text-secondary, #b8c7dc) !important;
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc) !important;
          font-size: 11.5px !important;
          font-weight: 900 !important;
          line-height: 1.15 !important;
          text-align: left !important;
          white-space: normal !important;
        }
        div[data-testid="column"]:has(.rulebook-chapter-slot.is-active) div.stButton > button {
          border-color: rgba(114,185,255,0.55) !important;
          background:
            linear-gradient(90deg, rgba(77,141,255,0.18), transparent 68%),
            rgba(13,27,49,0.98) !important;
          box-shadow:
            inset 4px 0 0 var(--primary, #4d8dff),
            inset 0 1px 0 rgba(255,255,255,0.08) !important;
        }
        div[data-testid="column"]:has(.rulebook-chapter-slot.is-active) div.stButton > button p {
          color: var(--text-primary, #f6f9ff) !important;
          -webkit-text-fill-color: var(--text-primary, #f6f9ff) !important;
        }
        .rulebook-document {
          position: relative;
          overflow: hidden;
          margin-top: 14px;
          padding: 18px;
          border: 1px solid rgba(139,171,216,0.18);
          border-radius: 18px;
          background:
            linear-gradient(135deg, rgba(77,141,255,0.075), transparent 42%),
            linear-gradient(180deg, rgba(14,24,39,0.98), rgba(7,12,22,0.99));
          box-shadow: var(--poke-shadow-card, 0 14px 30px rgba(0,0,0,0.24));
        }
        .rulebook-chapter-head {
          display: grid;
          grid-template-columns: minmax(0, 1fr) auto;
          gap: 14px;
          align-items: end;
          padding-bottom: 14px;
          border-bottom: 1px solid rgba(139,171,216,0.14);
        }
        .rulebook-chapter-eyebrow {
          margin-top: 7px;
          color: var(--text-muted, #77879e);
          -webkit-text-fill-color: var(--text-muted, #77879e);
          font-family: var(--font-pixel);
          font-size: 9px;
          font-weight: 900;
          text-transform: uppercase;
        }
        .rulebook-chapter-title {
          margin-top: 10px;
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-size: clamp(24px, 3vw, 38px);
          font-weight: 950;
          line-height: 1.04;
        }
        .rulebook-chapter-summary {
          max-width: 780px;
          margin-top: 8px;
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-size: 15px;
          line-height: 1.42;
        }
        .rulebook-chapter-facts {
          justify-content: flex-end;
          max-width: 330px;
        }
        .rulebook-chapter-fact {
          min-width: 92px;
          padding: 8px 10px;
          border: 1px solid rgba(139,171,216,0.13);
          border-radius: 12px;
          background: rgba(255,255,255,0.035);
        }
        .rulebook-content-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
          gap: 14px;
          margin-top: 16px;
        }
        .rulebook-section-card {
          overflow: hidden;
          border: 1px solid rgba(139,171,216,0.16);
          border-radius: 16px;
          background:
            linear-gradient(135deg, rgba(255,255,255,0.045), transparent 48%),
            rgba(8,14,26,0.84);
          box-shadow: inset 0 1px 0 rgba(255,255,255,0.055);
        }
        .rulebook-section-card.is-wide {
          grid-column: 1 / -1;
        }
        .rulebook-block-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 10px;
          min-height: 44px;
          padding: 11px 13px;
          border-bottom: 1px solid rgba(139,171,216,0.12);
          background: rgba(255,255,255,0.035);
        }
        .rulebook-block-title {
          min-width: 0;
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-size: 14px;
          font-weight: 950;
          line-height: 1.15;
        }
        .rulebook-block-code,
        .rulebook-table-code {
          flex: 0 0 auto;
          color: var(--primary-hover, #72b9ff);
          -webkit-text-fill-color: var(--primary-hover, #72b9ff);
        }
        .rulebook-article-list {
          display: grid;
          padding: 8px 13px 10px;
        }
        .rulebook-article {
          display: grid;
          grid-template-columns: 78px minmax(0, 1fr);
          gap: 14px;
          align-items: start;
          padding: 10px 0;
          border-bottom: 1px solid rgba(139,171,216,0.10);
        }
        .rulebook-article:last-child {
          border-bottom: 0;
        }
        .rulebook-article-no {
          color: var(--primary-hover, #72b9ff);
          -webkit-text-fill-color: var(--primary-hover, #72b9ff);
          font-family: var(--font-pixel);
          font-size: 9px;
          font-weight: 900;
          line-height: 1.65;
          text-transform: uppercase;
          white-space: nowrap;
        }
        .rulebook-article-text {
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-size: 14px;
          font-weight: 650;
          line-height: 1.48;
        }
        .rulebook-data-table-wrap {
          padding: 12px 13px 13px;
        }
        .rulebook-data-table {
          width: 100%;
          border-collapse: collapse;
          table-layout: fixed;
          overflow: hidden;
          border: 1px solid rgba(139,171,216,0.12);
          border-radius: 12px;
          background: rgba(255,255,255,0.025);
        }
        .rulebook-data-table th,
        .rulebook-data-table td {
          padding: 10px 12px;
          border-bottom: 1px solid rgba(139,171,216,0.10);
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-size: 13px;
          font-weight: 750;
        }
        .rulebook-data-table tr:last-child td {
          border-bottom: 0;
        }
        .rulebook-data-table th {
          color: var(--text-muted, #77879e);
          -webkit-text-fill-color: var(--text-muted, #77879e);
          font-size: 10px;
          font-weight: 900;
          text-align: left;
          text-transform: uppercase;
        }
        .rulebook-data-table td:last-child,
        .rulebook-data-table th:last-child {
          text-align: right;
        }
        .rulebook-data-table td:last-child {
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-weight: 950;
          font-variant-numeric: tabular-nums;
        }
        .rulebook-score-matrix th:nth-child(1),
        .rulebook-score-matrix td:nth-child(1) {
          width: 34%;
        }
        .rulebook-score-matrix th:nth-child(2),
        .rulebook-score-matrix td:nth-child(2),
        .rulebook-score-matrix th:nth-child(3),
        .rulebook-score-matrix td:nth-child(3) {
          text-align: right;
        }
        .rulebook-league-flow {
          display: grid;
          grid-template-columns: minmax(0, 1fr) 58px minmax(0, 1fr);
          gap: 10px;
          padding: 13px;
          border-bottom: 1px solid rgba(139,171,216,0.10);
        }
        .rulebook-league-node {
          min-height: 112px;
          padding: 13px;
          border: 1px solid rgba(139,171,216,0.14);
          border-radius: 14px;
          background:
            linear-gradient(135deg, rgba(77,141,255,0.08), transparent 58%),
            rgba(255,255,255,0.032);
        }
        .rulebook-league-node span,
        .rulebook-transfer-label,
        .rulebook-tool-code {
          display: block;
          color: var(--text-muted, #77879e);
          -webkit-text-fill-color: var(--text-muted, #77879e);
          font-family: var(--font-pixel);
          font-size: 9px;
          font-weight: 900;
          text-transform: uppercase;
        }
        .rulebook-league-node strong {
          display: block;
          margin-top: 7px;
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-size: 22px;
          font-weight: 950;
        }
        .rulebook-league-node em {
          display: block;
          margin-top: 8px;
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-size: 13px;
          font-style: normal;
          font-weight: 700;
          line-height: 1.35;
        }
        .rulebook-league-transfer {
          display: grid;
          place-items: center;
          color: var(--pokemon-yellow, #ffd24d);
          -webkit-text-fill-color: var(--pokemon-yellow, #ffd24d);
          font-size: 26px;
          font-weight: 950;
        }
        .rulebook-tool-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 10px;
          padding: 13px;
        }
        .rulebook-tool-card {
          min-height: 128px;
          padding: 12px;
          border: 1px solid rgba(139,171,216,0.13);
          border-radius: 14px;
          background:
            radial-gradient(circle at 100% 0%, rgba(255,210,77,0.08), transparent 54%),
            rgba(255,255,255,0.032);
        }
        .rulebook-tool-card strong {
          display: block;
          margin-top: 7px;
          color: var(--text-primary, #f6f9ff);
          -webkit-text-fill-color: var(--text-primary, #f6f9ff);
          font-size: 15px;
          font-weight: 950;
        }
        .rulebook-tool-card p {
          margin: 7px 0 0;
          color: var(--text-secondary, #b8c7dc);
          -webkit-text-fill-color: var(--text-secondary, #b8c7dc);
          font-size: 13px;
          font-weight: 650;
          line-height: 1.42;
        }
        @media (max-width: 980px) {
          .rulebook-hero,
          .rulebook-chapter-head {
            grid-template-columns: 1fr;
          }
          .rulebook-hero-seal {
            min-height: 96px;
          }
          .rulebook-chapter-facts {
            justify-content: flex-start;
            max-width: none;
          }
        }
        @media (max-width: 720px) {
          .rulebook-hero,
          .rulebook-document,
          .rulebook-index {
            border-radius: 14px;
            padding: 14px;
          }
          .rulebook-meta-grid,
          .rulebook-content-grid,
          .rulebook-league-flow {
            grid-template-columns: 1fr;
          }
          .rulebook-article {
            grid-template-columns: 1fr;
            gap: 4px;
          }
          .rulebook-league-transfer {
            min-height: 34px;
            transform: rotate(90deg);
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
    return sum(1 for block in section.get("visual_blocks") or [] if block.get("rows"))


def _total_articles(sections: list[dict]) -> int:
    return sum(_article_count(section) for section in sections)


def _active_section(sections: list[dict]) -> tuple[int, dict]:
    first_id = str(sections[0]["id"])
    active_id = str(st.session_state.get("normativa_rulebook_section") or first_id)
    for index, section in enumerate(sections):
        if str(section.get("id")) == active_id:
            return index, section
    st.session_state["normativa_rulebook_section"] = first_id
    return 0, sections[0]


def _render_rulebook_nav(active_id: str, sections: list[dict]) -> None:
    st.markdown(
        f"""
        <div class='rulebook-index'>
          <div class='rulebook-index-head'>
            <div>
              <div class='rulebook-index-title'>Indice del reglamento</div>
              <div class='rulebook-index-copy'>Selecciona un capitulo para consultar reglas, tablas y criterios oficiales.</div>
            </div>
            <div class='rulebook-index-badge'>{len(sections)} capitulos</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for row_start in range(0, len(sections), 4):
        row_sections = sections[row_start: row_start + 4]
        cols = st.columns(4)
        for offset, col in enumerate(cols):
            if offset >= len(row_sections):
                continue
            section = row_sections[offset]
            section_index = row_start + offset
            section_id = str(section.get("id"))
            active = section_id == active_id
            label = f"{section_index + 1:02d}  {_section_title(section)}"
            with col:
                st.markdown(
                    f"<span class='rulebook-chapter-slot{' is-active' if active else ''}'></span>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    label,
                    key=f"normativa_rulebook_nav_{section_id}",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state["normativa_rulebook_section"] = section_id
                    st.rerun()


def _article_rows_html(items: list[str], *, start_at: int) -> str:
    return "".join(
        (
            "<div class='rulebook-article'>"
            f"<span class='rulebook-article-no'>ART. {start_at + idx:02d}</span> "
            f"<span class='rulebook-article-text'>{escape(str(item))}</span>"
            "</div>"
        )
        for idx, item in enumerate(items)
    )


def _render_list_block_html(
    block: dict,
    *,
    block_no: int,
    start_at: int,
    intro_html: str = "",
    wide: bool = False,
) -> tuple[str, int]:
    items = list(block.get("items") or [])
    articles_html = _article_rows_html([str(item) for item in items], start_at=start_at)
    wide_class = " is-wide" if wide else ""
    return (
        (
            f"<article class='rulebook-section-card{wide_class}'>"
            "<div class='rulebook-block-head'>"
            f"<div class='rulebook-block-title'>{escape(str(block.get('title') or 'Bloque'))}</div>"
            f"<span class='rulebook-block-code'>B{block_no:02d}</span>"
            "</div>"
            f"{intro_html}"
            f"<div class='rulebook-article-list'>{articles_html}</div>"
            "</article>"
        ),
        start_at + len(items),
    )


def _render_rows_block_html(block: dict, *, block_no: int, section_id: str) -> str:
    rows = list(block.get("rows") or [])
    if section_id == "caps":
        left_header = "Entrenador"
        right_header = "Level Cap"
        table_class = " rulebook-level-table"
    else:
        left_header = "Etiqueta"
        right_header = "Valor"
        table_class = ""
    rows_html = "".join(
        (
            "<tr>"
            f"<td>{escape(str(label))}</td>"
            f"<td>{escape(str(value))}</td>"
            "</tr>"
        )
        for label, value in rows
    )
    return (
        "<article class='rulebook-section-card rulebook-block-table'>"
        "<div class='rulebook-block-head'>"
        f"<div class='rulebook-block-title'>{escape(str(block.get('title') or 'Valores'))}</div>"
        f"<span class='rulebook-table-code'>T{block_no:02d}</span>"
        "</div>"
        "<div class='rulebook-data-table-wrap'>"
        f"<table class='rulebook-data-table{table_class}'>"
        "<thead><tr>"
        f"<th>{escape(left_header)}</th>"
        f"<th>{escape(right_header)}</th>"
        "</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table>"
        "</div>"
        "</article>"
    )


def _split_named_rule(item: str) -> tuple[str, str]:
    if ":" not in item:
        return item, ""
    title, body = item.split(":", 1)
    return title.strip(), body.strip()


def _render_tool_block_html(block: dict, *, block_no: int, start_at: int) -> tuple[str, int]:
    items = [str(item) for item in (block.get("items") or [])]
    cards_html = ""
    for idx, item in enumerate(items):
        title, body = _split_named_rule(item)
        fallback_body = item if not body else body
        cards_html += (
            "<div class='rulebook-tool-card'>"
            f"<span class='rulebook-tool-code'>ART. {start_at + idx:02d}</span>"
            f"<strong>{escape(title)}</strong>"
            f"<p>{escape(fallback_body)}</p>"
            "</div>"
        )
    return (
        (
            "<article class='rulebook-section-card is-wide'>"
            "<div class='rulebook-block-head'>"
            f"<div class='rulebook-block-title'>{escape(str(block.get('title') or 'Comodines'))}</div>"
            f"<span class='rulebook-block-code'>B{block_no:02d}</span>"
            "</div>"
            f"<div class='rulebook-tool-grid'>{cards_html}</div>"
            "</article>"
        ),
        start_at + len(items),
    )


def _render_league_flow_html() -> str:
    try:
        version = current_season_version()
        sizes = list(version.division_sizes or [5, 5])
        while len(sizes) < 2:
            sizes.append(0)
        a_size, b_size = int(sizes[0]), int(sizes[1])
        movement = min(max(int(version.movement_count or 0), 0), a_size, b_size)
    except Exception:
        a_size, b_size, movement = 5, 5, 3
    return (
        "<div class='rulebook-league-flow'>"
        "<div class='rulebook-league-node'>"
        "<span>Liga A</span>"
        f"<strong>{int(a_size)} jugadores</strong>"
        f"<em>Los {int(movement)} ultimos descienden al cierre del tramo.</em>"
        "</div>"
        "<div class='rulebook-league-transfer'>"
        "<div><span class='rulebook-transfer-label'>Rotacion</span><strong>&#8645;</strong></div>"
        "</div>"
        "<div class='rulebook-league-node'>"
        "<span>Liga B</span>"
        f"<strong>{int(b_size)} jugadores</strong>"
        f"<em>Los {int(movement)} primeros ascienden al cierre del tramo.</em>"
        "</div>"
        "</div>"
    )


def _find_block(blocks: list[dict], title: str) -> dict | None:
    for block in blocks:
        if str(block.get("title") or "").lower() == title.lower():
            return block
    return None


def _render_score_matrix_html(blocks: list[dict], *, block_no: int) -> str:
    points_block = _find_block(blocks, "Puntos Oficiales")
    coins_block = _find_block(blocks, "Monedas Oficiales")
    if not points_block or not coins_block:
        return ""
    points = {str(label): str(value) for label, value in (points_block.get("rows") or [])}
    coins = {str(label): str(value) for label, value in (coins_block.get("rows") or [])}

    def _sort_key(value: str) -> tuple[int, str]:
        try:
            return int(value), value
        except ValueError:
            return 999, value

    rows_html = "".join(
        (
            "<tr>"
            f"<td>Pos. {escape(position)}</td>"
            f"<td>{escape(points.get(position, '-'))}</td>"
            f"<td>{escape(coins.get(position, '-'))}</td>"
            "</tr>"
        )
        for position in sorted(set(points) | set(coins), key=_sort_key)
    )
    return (
        "<article class='rulebook-section-card is-wide rulebook-block-table'>"
        "<div class='rulebook-block-head'>"
        "<div class='rulebook-block-title'>Puntos y monedas oficiales</div>"
        f"<span class='rulebook-table-code'>T{block_no:02d}</span>"
        "</div>"
        "<div class='rulebook-data-table-wrap'>"
        "<table class='rulebook-data-table rulebook-score-matrix'>"
        "<thead><tr><th>Posicion</th><th>Puntos</th><th>Monedas</th></tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        "</table>"
        "</div>"
        "</article>"
    )


def _render_section(section: dict, *, index: int) -> None:
    blocks = list(section.get("visual_blocks") or [])
    block_html: list[str] = []
    article_no = 1
    section_id = str(section.get("id") or "")
    for block_no, block in enumerate(blocks, start=1):
        block_title = str(block.get("title") or "")
        if section_id == "liga" and block_title == "Puntos Oficiales":
            score_html = _render_score_matrix_html(blocks, block_no=block_no)
            if score_html:
                block_html.append(score_html)
            continue
        if section_id == "liga" and block_title == "Monedas Oficiales":
            continue
        if section_id == "comodines" and block_title == "Catalogo de Comodines":
            html, article_no = _render_tool_block_html(
                block,
                block_no=block_no,
                start_at=article_no,
            )
            block_html.append(html)
        elif block.get("rows"):
            block_html.append(_render_rows_block_html(block, block_no=block_no, section_id=section_id))
        else:
            intro_html = _render_league_flow_html() if section_id == "liga" and block_title == "Divisiones" else ""
            html, article_no = _render_list_block_html(
                block,
                block_no=block_no,
                start_at=article_no,
                intro_html=intro_html,
                wide=bool(intro_html),
            )
            block_html.append(html)
    st.markdown(
        (
            "<section class='rulebook-document'>"
            "<div class='rulebook-chapter-head'>"
            "<div>"
            f"<span class='rulebook-chapter-code'>CAP. {index + 1:02d}</span>"
            f"<div class='rulebook-chapter-eyebrow'>{escape(str(section.get('eyebrow') or 'Documento oficial'))}</div>"
            f"<div class='rulebook-chapter-title'>{escape(_section_title(section))}</div>"
            f"<div class='rulebook-chapter-summary'>{escape(str(section.get('summary') or ''))}</div>"
            "</div>"
            "<div class='rulebook-chapter-facts'>"
            f"<div class='rulebook-chapter-fact'><span>Bloques</span> <strong>{len(blocks)}</strong></div>"
            f"<div class='rulebook-chapter-fact'><span>Articulos</span> <strong>{_article_count(section)}</strong></div>"
            f"<div class='rulebook-chapter-fact'><span>Tablas</span> <strong>{_table_count(section)}</strong></div>"
            "</div>"
            "</div>"
            f"<div class='rulebook-content-grid'>{''.join(block_html)}</div>"
            "</section>"
        ),
        unsafe_allow_html=True,
    )


def render_normativa_home() -> None:
    _render_normativa_css()
    sections = normativa_sections()
    active_index, active = _active_section(sections)
    st.markdown(
        (
            "<section class='rulebook-hero'>"
            "<div class='rulebook-hero-content'>"
            "<div class='rulebook-eyebrow-row'>"
            "<span class='rulebook-eyebrow'>Manual oficial</span> "
            "<span class='rulebook-chip'>Competicion Pokemon</span> "
            "<span class='rulebook-chip'>Temporada vigente</span>"
            "</div>"
            "<div class='rulebook-title'>Normativa de Liga</div>"
            "<p class='rulebook-subtitle'>Reglamento vigente de PokeApp, organizado como dossier tecnico para encontrar rapido caps, divisiones, comodines y normas clave.</p>"
            "<div class='rulebook-meta-grid'>"
            f"<div class='rulebook-meta-card'><span>Capitulos</span> <strong>{len(sections)}</strong></div>"
            f"<div class='rulebook-meta-card'><span>Articulos</span> <strong>{_total_articles(sections)}</strong></div>"
            "<div class='rulebook-meta-card'><span>Formato</span> <strong>Oficial</strong></div>"
            "</div>"
            "</div>"
            "<aside class='rulebook-hero-seal'>"
            "<div class='rulebook-seal-mark'>P</div>"
            "<div class='rulebook-seal-text'>PokeApp League<br>Rulebook</div>"
            "</aside>"
            "</section>"
        ),
        unsafe_allow_html=True,
    )
    _render_rulebook_nav(str(active.get("id")), sections)
    _render_section(active, index=active_index)
