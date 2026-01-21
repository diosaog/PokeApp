from __future__ import annotations

import streamlit as st

from app.interfaz.theme import render_poke_separator


def page_inicio() -> None:
    user = st.session_state.get("user") or "-"
    st.header(f"Bienvenido, {user}")
    render_poke_separator()
    st.subheader("Guia rapida")
    st.markdown(
        "1. Ve a 'Saves' y sube tu archivo .sav.\n"
        "2. Configura el lector en 'Entrenadores' si es necesario.\n"
        "3. En 'Entrenadores' puedes ver equipo, cajas y detalles.\n"
        "4. En 'Tienda' compra comodines/objetos.\n"
        "5. 'Liga y Tabla' y 'Copa' muestran clasificaciones y emparejamientos."
    )

    normativa_md = """
Normativa ChampionsLocke

1. Normas Nuzlocke
- Todo Pokemon debilitado se considera muerto y debe enviarse a la caja de muertos.
- Un Pokemon muerto no puede volver a usarse ni subir de nivel.
- Solo se puede capturar el primer encuentro de cada ruta o area.
- Si ese Pokemon huye, es derrotado o el combate termina por cualquier motivo, la captura de esa zona se pierde.
- Mote obligatorio para todos los Pokemon.

Clausulas especiales
- Duplicados: si el primer encuentro pertenece a una linea evolutiva ya capturada, se puede forzar otro encuentro.
- Legendarios principales: no estan permitidos; si aparecen como primer encuentro, se fuerza otro.
- Shiny: un Pokemon shiny es siempre capturable y no consume la captura de la ruta.
- Fosil: solo se puede usar una vez por ser de uso unico.

2. Restricciones de equipo
- Maximo 1 pseudo-legendario por equipo.
- Maximo 1 legendario menor o singular (<= 600 BST) por equipo.
- No se pueden repetir Pokemon en la misma fase evolutiva.
- Si se obtiene un duplicado de fase, debe liberarse el ultimo capturado.
- Esta norma no se aplica si el Pokemon previo de esa fase ya estaba muerto.

3. Estructura por tramos
- La partida se divide en 4 tramos mas una Liga Pokemon final.
- Cada tramo finaliza tras superar determinados gimnasios.
- Al cierre de cada tramo se disputa una liga competitiva entre jugadores.

4. Combates entre jugadores
- Liga: combates 1 vs 1, formato Bo1.
- Copa: se juega tras completar la Liga Pokemon. Formato eliminatorio, Bo3.

5. Level Caps
Gimnasios
- Roco 17
- Gardenia 26
- Fantina 31
- Brega 38
- Mananti 44
- Aceron 49
- Inverna 53
- Lectro 60

Liga Pokemon
- Alecran 64
- Gaia 66
- Fausto 68
- Delos 71
- Cintia 74

Reglas de nivel
- Ningun Pokemon puede superar el cap del siguiente combate oficial.
- Si un Pokemon lo supera, debe enviarse a la caja y no puede utilizarse.
- Los Caramelos Raros solo pueden usarse para ajustar niveles.
- Si se sube de mas y se guarda, se permite resetear.

6. Divisiones (Liga A / B)
- Dos divisiones: A y B, con 5 jugadores cada una.
- Los jugadores solo se enfrentan contra rivales de su propia division.
- Descienden los 3 ultimos de Division A; ascienden los 3 primeros de Division B.

7. Monedas
- Medallas: 4 monedas por cada medalla (max 8).
- Saldo total = medallas*4 + monedas de liga - monedas gastadas.

8. Comodines
- Revivir: revive un Pokemon de la Caja 18; queda marcado como blindado + revivido.
- Robar: si el objetivo no esta blindado, se registra el robo y queda blindado.
- Blindar: marca un Pokemon como blindado (no se puede volver a robarse ni blindarse).
- Captura Extra: permite una captura adicional en una ruta desconocida.
- Fosil: permite obtener un fosil.

9. Normas generales
- Se permiten intercambios y combates de practica.
- Los comodines pueden usarse sobre otros jugadores o sobre uno mismo.
- El comodin Robar no puede usarse dos veces seguidas sobre el mismo jugador.
- Directos obligatorios: los jugadores deben jugar en Discord en directo y avisar previamente por WhatsApp.
"""
    with st.expander("Normativa ChampionsLocke", expanded=False):
        st.markdown(normativa_md)


def page_entrenadores() -> None:
    try:
        import entrenadores as _ent
        if hasattr(_ent, "page_entrenadores"):
            _ent.page_entrenadores()
    except Exception as e:
        st.error(f"No se pudo cargar la vista de entrenadores: {e}")


def page_tabla() -> None:
    try:
        import liga_tabla as _lt
        _lt.page_tabla()
    except Exception as e:
        st.error(f"No se pudo cargar la tabla: {e}")


def page_copa() -> None:
    try:
        import copa as _swiss
        import copa2 as _elim
        st.subheader("Copa")
        fmt = st.radio("Formato", ["Copa", "Torneo"], horizontal=True)
        st.markdown("---")
        if fmt == "Torneo":
            _elim.page_copa()
        else:
            _swiss.page_copa()
    except Exception as e:
        st.error(f"No se pudo cargar la copa: {e}")
