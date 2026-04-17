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
        "4. En 'Juicios' crea casos, revisa pruebas y aplica castigos.\n"
        "5. En 'Tienda' compra comodines/objetos.\n"
        "6. 'Liga y Tabla' y 'Copa' muestran clasificaciones y emparejamientos."
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
- Duplicados: si el primer encuentro pertenece a una linea evolutiva ya capturada, se debe de forzar otro encuentro, a menos que este haya muerto. Entonces podras decidir.
- Legendarios principales: no estan permitidos; si aparecen como primer encuentro, se fuerza otro.
- Shiny: El pokemon shiny es capturable 1 unica vez por juego, no se pueden capturar mas de 1.
- Fosil: solo se puede usar una vez por ser de uso unico.
- Pokemon baneados: Slaking, Deoxys.
- Movimientos baneados: Esquema (Unicamente la MT, en el recuerdamovimientos si se puede).
- Objetos baneados: Rocio Bondad.

2. Restricciones de equipo
- Maximo 1 pseudo-legendario por equipo.
- Maximo 1 legendario menor o singular (<= 600 BST) por equipo.
- No se pueden repetir Pokemon de la misma fase evolutiva.
- Si se obtiene un duplicado, debe liberarse el ultimo capturado.
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
- Monedas (por posicion)

1: 15 / 
2: 14 / 
3: 12 / 
4: 11 / 
5: 10 / 
6: 11 / 
7: 9 / 
8: 8 / 
9: 6 / 
10: 4 / 

- Puntos (por posicion)

1: 9 / 
2: 8 / 
3: 7 / 
4: 6 / 
5: 5 / 
6: 5 / 
7: 4 / 
8: 3 / 
9: 2 / 
10: 1 / 

7. Monedas
- Medallas: 4 monedas por cada medalla (max 8).
- Saldo total = medallas*4 + monedas de liga - monedas gastadas.

8. Comodines
- Revivir: revive un Pokemon de la Caja 18; queda marcado como blindado + revivido y sigue contando como muerto a efectos de puntos (-0.2).
- Robar: si el objetivo no esta blindado, se registra el robo y queda blindado.
- Blindar: marca un Pokemon como blindado (no se puede volver a robarse ni blindarse).
- Captura Extra: permite una captura adicional en una ruta desconocida.
- Fosil: permite obtener un fosil.

9. Normas generales
- No se permiten intercambios.
- Si un Pokemon ha sido eliminado por un juicio y/o ilegalidad de un entrenador, este NO podra volver a tener ese Pokemon.
- Queda totalmente prohibido explotar el juego, como por ejemplo forzar encuentros no random (cadenas de shiny, arboles de miel, etc.).
- Las tiendas especiales solo y unicamente se puede comprar 1 objeto.
- Objetos como las Master Ball de tiendas, solo se pueden comprar una vez.
- Se permiten combates de practica entre jugadores de distintas ligas.
- Los comodines pueden usarse sobre otros jugadores o sobre uno mismo.
- El comodin Robar no puede usarse dos veces seguidas sobre el mismo jugador.
- Prohibido usar equipos de otros jugadores para practicar y usar herramientas de calculos de daño externas al showdown.
- Buscar vacios legales en el juego es ilegal, si un entrenador lo encuentra, debe avisar por el grupo y se tomara una decision en base a una votacion.
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
        import copa_dobles as _doubles
        st.subheader("Copa")
        fmt = st.radio("Formato", ["Copa", "Torneo", "Copa Dobles"], horizontal=True)
        st.markdown("---")
        if fmt == "Torneo":
            _elim.page_copa()
        elif fmt == "Copa Dobles":
            _doubles.page_copa()
        else:
            _swiss.page_copa()
    except Exception as e:
        st.error(f"No se pudo cargar la copa: {e}")
