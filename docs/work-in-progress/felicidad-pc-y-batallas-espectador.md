# Felicidad máxima en el PC y Batallas › Espectador sin scroll

**PUBLICADO el 2026-11-12 con autorización del propietario.** Commit de código `fb92000`.

| Pieza | Publicado | Rollback |
|---|---|---|
| Launcher | 0.26.15 en el canal estable: instalador `9eb3a60b…`, 159 498 765 bytes, firma Ed25519 válida, mínimo 0.26.0; `/launcher/download` sirve 0.26.15 | Restaurar `updates/stable.json` de 0.26.14 y publicar una versión superior |
| Web Cloudflare | `08fb936b` | `5e241403` |
| API Railway | Sin cambios (`010a6546`) | — |

Sin SQL, sin cambios de API ni del verifier (`39181f7f`), sin datos modificados. Robar,
Revivir, Avisos y Normativa siguen como estaban (Normativa 7.3 solo cambia su texto).

## 1. Felicidad máxima: también los Pokémon del PC

**Por qué solo salía el equipo.** El filtro estaba en las tres capas del Launcher, no en la
web ni en la API:

- El lector nativo (`NativeFriendship.Inspect`) recorría solo `PartyCount`.
- El núcleo Python (`app/launcher/friendship.py`, `runtime.py`) solo aceptaba
  `location == "party"` y posiciones 0–5.
- El Launcher (`main.cjs`, `confirmations.cjs`, `renderer.js`) ataba la confirmación a
  `"<posición del equipo>:<hash>"`.

**Ahora (Launcher 0.26.15):**

- El diálogo lista el equipo y todas las posiciones ocupadas de todas las cajas, agrupados
  por sitio («Equipo», «Caja 1»…). Cada fila muestra sprite, mote, especie, nivel,
  ubicación («Equipo · 2», «Caja 5 · 18») y felicidad actual con barra.
- Filtro «Dónde» (todo, equipo o una caja), buscador por mote o especie (sin distinguir
  mayúsculas ni tildes) y casilla «Ocultar los que ya están a 255».
- Los huevos, las posiciones bloqueadas de equipos de combate y los huecos vacíos nunca se
  ofrecen.
- Misma operación `max_friendship`, sin permisos nuevos: copia completa verificada, journal,
  relectura y restauración. Un Pokémon de caja se escribe en su sitio con `WriteBoxSlot`
  (nunca se mueve al equipo).
- La confirmación queda atada al sitio exacto y a los bytes exactos del Pokémon:
  `party:<posición>:<hash>` o `box:<caja>:<posición>:<hash>`. Si en ese sitio hay otro
  Pokémon, está vacío o cambió la partida, se rechaza sin escribir.
- El verificador nativo exige que en toda la partida solo cambien el byte de felicidad del
  entrenador actual (OT `0xCA` o entrenador que lo maneja `0xA2`), el checksum de ese
  Pokémon, el checksum de su bloque y, en 7.ª generación, la firma. No cambian el afecto de
  Pokémon-Amie, los IV, los EV, la naturaleza, la habilidad, los movimientos, el objeto, el
  nivel ni la ubicación.
- Los cambios del equipo conservan su forma anterior (sin `box_index`), así que los journals
  de Launchers anteriores siguen verificándose y recuperándose igual.
- En la web, la fila de Inventario dice «de tu equipo o de tus cajas del PC» solo dentro de
  Launcher 0.26.15 o superior. Normativa 7.3 actualizada (fecha 12 de noviembre de 2026).

## 2. Batallas › Espectador: los doce Pokémon caben a la vez

**Antes:** a 1650×900, el título, las pestañas, el texto y los selectores ocupaban casi
toda la pantalla y cada tarjeta medía unos 235 px. Solo se veía el primer Pokémon y la
página medía 2357 px de alto.

**Ahora:**

- Cabecera de la página y controles compactos: pestañas, jornada, los dos selectores,
  «Fijar Equipo» y la ayuda en una sola banda.
- Cada Pokémon es una fila: sprite, mote, especie, nivel, tipos, objeto y los cuatro
  movimientos con sus PP y colores de tipo en una cuadrícula de 2×2.
- Los dos equipos quedan enfrentados alrededor de una línea con el medallón «VS». El
  segundo equipo va en espejo y los sprites del primero miran hacia el centro.
- En pantallas bajas (≤ 820 px) o columnas estrechas, los tipos pasan a iconos junto al
  mote. El nombre del tipo sigue disponible en el texto accesible y al pasar el ratón.
- Por debajo de 900 px de ancho los equipos se apilan, sin barras de scroll internas.
- El detalle de un movimiento flota sobre el equipo (las filas inferiores lo abren hacia
  arriba) y no desplaza la página.
- En Batallas el área principal ocupa exactamente el espacio entre la cabecera y el pie,
  sin el `min-height: 100dvh` global que empujaba el pie fuera de la pantalla.
- Solo presentación (`web/src/design/matchup.css` y `MatchupRoster` en
  `team-preview.tsx`). Misma lectura pública: sin habilidad, naturaleza ni IV. El modo
  Batalla no cambia.

| Resolución | Resultado |
|---|---|
| 1650×900 | 12/12 visibles, sin scroll vertical ni horizontal |
| 1920×1080 | 12/12 visibles, sin scroll |
| 1366×768 | 12/12 visibles, sin scroll (tipos como iconos) |
| 1024×768 | Equipos lado a lado con las tarjetas apiladas por dentro; la página baja, sin recortes |
| 390×844 | Equipos uno debajo del otro, PP visibles, sin scroll horizontal |

Capturas antes y después:
[evidencias](../evidence/2026-11-12-batallas-felicidad/).

## 3. Pruebas realizadas (focalizadas)

- C# `--friendship-checks` sobre copias en memoria de los fixtures públicos de los 8 juegos
  (X, Y, OR, AS, SN, MN, US, UM): **PASS, 548 comprobaciones**. Incluye la Caja 1, la
  última posición de la última caja, un hueco vacío, un huevo en caja, Pokémon recibidos por
  intercambio, salidas falsificadas que tocan otra posición, sitio o hash equivocados y
  cajas fuera de rango.
- Python `test_launcher_friendship` (15): motor real con journal, copia, relectura,
  restauración y recuperación tras un corte, en el equipo y en las cajas, en modo
  producción. También `test_item_use_verification` y `test_phase22_write_engine` (44).
  Siempre sobre carpetas temporales, nunca sobre partidas reales.
- Launcher: tests node (59) y prueba visual del diálogo en Electron
  (`tools/launcher_friendship_ui_smoke`, 23/23). También la prueba visual general
  (`tools/launcher_ui_smoke`, 84/84).
- Web: Vitest 47 archivos / 401 tests (una ejecución intermedia tuvo 3 fallos transitorios por carga que no se repitieron); Playwright `spectator-fit.spec.ts` (6, con
  mediciones de scroll, recortes y solapes) y `team-preview.spec.ts` (6).

## 4. Publicación y verificación en producción

- Build `%LOCALAPPDATA%/PokeApp-builds/0.26.15-public` (PASS, 334 ficheros de runtime). El
  parser empaquetado lee 790 Pokémon de cajas del fixture Y, incluidas Caja 1 · 1 y Caja 31 · 30.
- `publish_launcher_release.mjs --apply --owner-authorized`: instalador, relectura pública
  SHA-512 y, al final, `updates/stable.json`. Feed público: 0.26.15, firma válida.
- Web desplegada con `npm run deploy` (`08fb936b`); sirve el CSS nuevo y la descarga 0.26.15.
- `spectator-fit.spec.ts` contra el sitio desplegado (API simulada en el navegador, ninguna
  petición llega a producción): 6/6. Las capturas `despues-*` son de esa ejecución.

**Pendiente de uso real:** la primera Felicidad máxima sobre un Pokémon de caja en una partida
real. Los Launchers anteriores a 0.26.15 siguen mostrando solo el equipo hasta actualizarse
(el aviso de actualización aparece solo).
