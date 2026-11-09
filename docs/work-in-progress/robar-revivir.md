# Robar y Revivir para toda la Liga — registro vivo

**PUBLICADO Y VERIFICADO el 2026-11-09**, con autorización expresa del propietario.
Rama `claude/net-friendship-discord`, fuente `dc2f3fa`.

| Capa | Estado | Rollback |
|---|---|---|
| Supabase | 001–085. 085 = `20261109203241` | Corrección hacia delante; no reescribe datos |
| API | Railway `909765eb` (139 rutas) | `a15cfd4f` |
| Verificador | Railway `39181f7f`, imagen `777314cc`, ciclo de 60 s | `2853bbc4` |
| Web | Cloudflare `6da892d5` | `681d7e85` |
| Launcher | 0.26.13 en el canal estable, instalador `42c1c77a…`, 159 493 659 bytes, firma Ed25519 válida | Restaurar `updates/stable.json` anterior y publicar una versión superior |
| Railway | `POKEAPP_ITEM_VERIFICATION_TRANSPORT_ENABLED=true`; `POKEAPP_TRANSFER_ENGINEERING_TRAINERS` eliminada | — |

Copia y ensayo: `%LOCALAPPDATA%/PokeApp-migration-evidence/robbery-revive-085`
(`pre-release-20261109T203011Z`, ensayo 17/17). Evidencia:
[aceptación](../evidence/robbery-revive-085/acceptance.json) y
[publicación](../evidence/robbery-revive-085/release.json).

## Reglas implementadas (decisiones del propietario)

**Robar.** Sin Team Lock ni jornadas: la lista de víctimas y Pokémon sale de la última
partida oficial aceptada (`api_robbery_board`), y solo la ve quien tiene el comodín, con
la lista pública de campos. Rotación global persistida en `redemptions` y `robbery_cycles`:

- Cuenta la adjudicación del verificador, que es irreversible y consume el comodín. Un
  intento cancelado, caducado o imposible de planificar no cuenta.
- Víctima elegible: participante activo y habilitado, con partida oficial y al menos un
  Pokémon robable. Quien no lo es no bloquea la ronda (`robbery_open_victims`).
- Índice único por temporada, ronda y víctima: dos robos simultáneos no pueden marcarla dos veces.

Protecciones al preparar y al adjudicar: blindado o ya robado, 24 h desde la primera
observación verificada por el servidor (`robbery_candidates`, sin usar la fecha del
Pokémon), último del equipo. No hay requisito de jornada ni de posición.

**Revivir.** Caja de muertos del participante (`dead_box_number`; todos en 7, y el valor
por defecto de filas nuevas pasa de 8 a 7). El Pokémon se mueve byte a byte al primer hueco
de las cajas anteriores a la de muertos, nunca a la Caja 7. El Launcher pide autorización,
reclama, aplica con el motor protegido, sube el resultado, el verificador lo prueba de
forma independiente y solo entonces el servidor consume el comodín.

Muerte y NET sin cambios: `league_death_events` es inmutable y la redención queda mapeada.

## Bloqueos corregidos además de los conocidos

- `NativeTransfer.Free` podía dejar un Pokémon robado en la Caja 7, contándolo como muerto.
- Un robo cancelado dejaba el comodín inservible (`purchase_id` único): ahora la
  autorización queda como historia (`superseded_at`) y la compra admite otro intento.
- Un intento caducado retenía para siempre a los dos entrenadores: el verificador los
  libera, y lo que no se puede planificar se cierra con el motivo.
- PKHeX 24.11.11 puede escribir una firma RSA corta en juegos de Gen 7: Revivir y Robar
  aplican la misma reparación estricta que ya usaba el entrenamiento.
- ByVisan02, sin partida, habría impedido cerrar cualquier ronda.

## Comprobaciones

- Nativo: Revivir 200 (8 juegos, Caja 7), robo de cajas 168, robo de equipo 500.
- `tools/validate_phase085_activation.py`: 63 comprobaciones sobre PostgreSQL desechable,
  API real, verificador real, motor en modo producción y partidas de prueba derivadas de
  fixtures públicos. Repetidas con el parser empaquetado del instalador.
- Web 400, Node 57, Python 1527 (4 expectativas antiguas corregidas y sus módulos repetidos).
- Ni partidas reales, ni robos, ni revividos reales. Sin cambios en puntos, muertes,
  monedas, compras o Pokémon de ningún entrenador.

## Límites reales

- Nunca se ha hecho un robo o un revivido real en la Liga; el primero será el de un entrenador.
- ByVisan02 no se puede robar hasta que registre partida.
- Revivir necesita Launcher 0.26.13 (se actualiza solo). Robar funciona desde 0.26.12.
- Un robo adjudicado pausa la sincronización de la víctima hasta que su Launcher lo entrega
  (diseño ya vigente). No se puede robar mientras haya otra operación de esos entrenadores.
- No se ofrecen huevos ni Pokémon de otro entrenador original, ni los de la Caja 8 o
  posteriores: restricciones técnicas previas (hoy, 0 casos en la Liga).
- Si un intento de Revivir no se completa en 24 h y además se ha seguido jugando, la
  sincronización queda en pausa y requiere recuperación asistida.
- Administración sigue viendo como «ligada a una operación» una compra con un intento
  anterior cancelado: no puede cancelarla desde el centro de incidencias, aunque se puede usar.
