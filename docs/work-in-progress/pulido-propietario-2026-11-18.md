# Pulido del propietario (18-11-2026): Revivir no blinda, ROBADO en Liga, ventanas, espectador 3×2, Launcher 0.26.17

**PUBLICADO el 2026-11-18 (~23:20 hora local)** con autorización del propietario («sí,
publícalo todo»). Código `b2d3dd7`, descarga `5ec8a5e`. Rama `claude/net-friendship-discord`.

| Pieza | Estado | Rollback |
|---|---|---|
| Supabase | 001–088 (088 = `20261118221629`) | Copia `pre-release-20261118T221412Z` (sha256 `1ca58ff3…`); volver a parchear `api_redeem_purchase` |
| API Railway | `203313d4` (imagen `588ae0d1…`, 139 rutas, OpenAPI idéntico al código) | `14ba5fa1` (compatible: los campos nuevos son opcionales) |
| Web Cloudflare | `009db1a3` (`/launcher/download` sirve 0.26.17) | `9c4ca9f6` |
| Launcher | 0.26.17 en el canal estable: instalador `4a1bf63b…`, 159 511 362 bytes, mínimo 0.26.0 | Restaurar `updates/stable.json` de 0.26.16 y publicar una versión superior |
| Verificador | Sin cambios (`79e5308c`) | — |

## Qué pidió el propietario

1. Hall de la Fama sin el recuadro «Tu próxima historia empieza aquí» (ya están las Leyendas).
2. Liga: etiqueta **ROBADO** junto a quien ya ha sido robado en la ronda de robos actual.
   La API devuelve `robbery_round` y `robbed_this_round` por fila (RPC `robbery_round` +
   robos `steal` aplicados de esa ronda). En vivo, ronda 1: Aaron y Anto.
3. Ventanas: un único sistema (cabecera fija, cuerpo con scroll, tamaños md/lg/xl), selector
   de Pokémon por tarjetas con un botón por caja. Launcher: tabla 5×5 de Mentas con +/− en
   colores, barras de IV, tarjetas en Revivir y Felicidad.
4. Team Preview espectador: 3×2 mini-tarjetas por lado, simétrico.
5. **Revivir ya no blinda** (regla nueva). 088 deja de insertar BLINDADO al canjear Revivir y
   desblinda a los Pokémon cuyo único blindaje venía de revivir. En producción: 1 Pokémon
   (sigue REVIVIDO, ya no BLINDADO); los blindajes de Blindar o de un robo se conservan.
   El perfil propio muestra siempre las etiquetas de temporada aunque se enseñe una partida
   personal más reciente.
6. «Saves y Launcher» en el Launcher: partida, cuatro accesos grandes (Objetos, Felicidad,
   Revivir, Robos), equipo con sprites y lo técnico plegado.

Rechazó cualquier mejora extra («haz lo que te comenté y con eso nos vale»).

## Comprobaciones

- Python 1570 OK, web 411 OK, `tsc` limpio, smoke de interfaz del Launcher 84 PASS,
  Node 74, validador `tools/validate_phase088_revive_shield` PASS.
- Ensayo sobre la copia de producción: PASS 18/18, «088 only turns revive-only BLINDADO flags
  off», 116 lecturas de la API idénticas, igual a un 001–088 limpio.
- En vivo: guarda `088: Revivir no blinda` presente; ningún Pokémon solo revivido sigue
  blindado; API `/health` 200, 401 sin sesión; feed 0.26.17 firmado con sus notas;
  la web sirve la etiqueta ROBADO, las ventanas nuevas y la Normativa corregida.
- 12 pruebas de Playwright (Liga, Economía, revisión visual) fallan igual en `cf9797e`:
  textos antiguos, no relacionadas.

## Incidente menor durante la publicación

El primer `npm run build` falló (faltaba `VITE_API_BASE_URL`) y el `npm run deploy`
encadenado subió la compilación antigua que había en `web/dist` (versión `3f619964`, compilada a las
12:42, anterior a `9c4ca9f6`) durante ~2 minutos. Corregido compilando con
`VITE_API_BASE_URL=https://pokeapp-api-production.up.railway.app` y desplegando `009db1a3`.
Para la próxima vez: compilar y desplegar solo si la compilación termina bien.
