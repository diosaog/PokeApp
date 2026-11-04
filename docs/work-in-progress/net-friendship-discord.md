# NET con revividos tras wipe, Felicidad máxima y anuncios Team Lock — 2026-11-04/05

Estado: **082/083, API, web y Launcher 0.26.12 PUBLICADOS Y VERIFICADOS**.
«Felicidad máxima» **DISPONIBLE** en Launcher 0.26.12 (autorización del
propietario 2026-11-05); solo se habilitó `max_friendship`.
Rama `claude/net-friendship-discord`, desde `68c674f` (tip de
`codex/automatic-observed-points`). Producción: DB 001–083.

| Commit | Contenido | Estado |
|---|---|---|
| `9e83cee` | Gourgeist sin sufijo de tamaño; refresco del recuento wipe en la ficha | Publicado (API `3c6b1d9f`, web `43e98b76`) |
| `c49888c` | SQL 082 (NET con wipe) y 083 (anuncio por confirmación) + API Discord | **Publicado**: 082 `20261104232636`, 083 `20261104232638`, API `f1d2896a` |
| `0ab7a6e`, `5627f8c`, `b954ad1` | «Felicidad máxima» (nativo, Launcher, web) | **Publicada**: Launcher 0.26.12 en el feed estable; web `9a17a56c` |

Los datos de los entrenadores son válidos y se respetan (instrucción del
propietario, 2026-11-05): 082 aplica las reglas oficiales a los registros
existentes sin modificar ningún valor ni fila.

## 1. Puntos NET

**Defecto (081).** `league_death_totals` trataba los revividos tras wipe como
un subconjunto de las muertes vistas en la Caja 7. Un wipe cura al equipo en
el juego, así que esas muertes no llegan a la caja. Con más revividos que
muertes observadas el NET pasaba a desconocido (`death_history_inconsistent`,
«—»); con menos, cada revivido costaba solo 0,1. El estado de la jornada no
interviene: preparada, abierta o cerrada da el mismo total.

**082** (solo la función de lectura, con guard del hash 081): muertes = offset
auditado + eventos efectivos (077/080) + revividos tras wipe no incluidos en
una línea base auditada − muertes observadas que el propio wipe revivió.
Penalización: 0,1 por muerte ordinaria y 0,2 por muerte revivida tras wipe,
nunca doble. Fuentes ausentes, huecos y revivals sin mapear siguen siendo
desconocidos. Sin cambios de tablas, filas, snapshots ni ACL.

**Resultado sobre los registros reales** (lectura oficial sobre una restauración
desechable de la copia de 23:24 UTC, antes → después de 082):

| Entrenador | Antes | Después |
|---|---|---|
| Aaron | −0,4 | −0,4 |
| Anto | 0 | 0 |
| ByVisan02 | — | — (sin partida de Liga registrada) |
| Iker | −0,3 | −0,3 |
| Samu | — | **−2,2** (11 revividos tras wipe registrados) |
| STeeLAG | 0 | 0 |

El «11» de Samu es su contador registrado de revividos tras wipe (038); se
aplica tal cual según las reglas oficiales. 0 victorias y 0 sanciones.

## 2. Felicidad máxima (255)

Nativo `NativeFriendship.cs` (PKHeX 24.11.11): la amistad que lee el juego para
el manejador actual (`CurrentFriendship`: OT `0xCA` o manejador `0xA2`). El
afecto de Pokémon-Amie (`0xCB`/`0xA3`) no se toca. El diff de la partida queda
limitado a ese hueco del equipo + checksum del bloque (+ firma SM/USUM). No se
consulta legalidad: los aleatorizados no se rechazan. Huevo, equipo cambiado o
ya en 255 se rechazan antes de escribir. Launcher: mismo motor protegido que
Caramelos/Escamas y diálogo nativo `/escritorio/felicidad`. Web: fila en
Inventario › Objetos ilimitados, visible solo dentro del Launcher 0.26.12+.

**Publicada en Launcher 0.26.12** (2026-11-04 23:42 UTC, feed estable): build
auditado, manifest Ed25519 válido, instalador público idéntico al build
(159 472 702 bytes, SHA-256 `3fa8b195…`). Prueba empaquetada con el parser
publicado en modo producción sobre copia aislada de Y: emulador cerrado
comprobado, copia verificada, 70 → 255 tras relectura, restauración exacta.
`/launcher/download` sigue en 0.26.11 hasta el próximo despliegue web (ya
fijado a 0.26.12 en el repositorio); esa versión se actualiza sola por el feed.
[Evidencia](../evidence/net-friendship-discord/launcher-0.26.12.json).

## 3. Anuncios Team Lock

067 editaba una única fila por Team Lock: volver a fijar el mismo equipo no
anunciaba nada y un mensaje borrado no se reponía. **083**:
`team_lock_confirmations` inmutable y una fila de outbox por confirmación
explícita (`Idempotency-Key`), con su propio estado, mensaje y paste;
`api_confirm_team_lock` reutiliza `api_upsert_team_lock` sin cambios
(autorización y jornadas cerradas intactas). Una clave repetida no duplica; los
mensajes anteriores nunca se editan ni se borran. El primer «Fijar Equipo» real
tras la publicación creará la primera confirmación (aún 0 en producción).

**Gourgeist:** `Jalowin (Gourgeist) (F) @ Rocky Helmet` en la exportación
privada y en Pokepast.es. Showdown simula entonces el tamaño Medio (base
PS/Ataque/Velocidad 65/90/84 frente a 75/95/69 del Grande); la forma 2 se
conserva en PokeApp y en la partida.

## Verificación

- Local: defecto 081 reproducido; 082 13 PASS; 083 11 PASS
  ([SQL](../evidence/net-friendship-discord/sql-082-083.json)); C# 256 PASS en
  8 juegos ([nativo](../evidence/net-friendship-discord/friendship-native-checks.json));
  Python 116 + 87 (incl. 9 de Felicidad con parser y motor reales); Node 18;
  web 45 archivos / 389 tests + `tsc -b`.
- Publicación ([registro](../evidence/net-friendship-discord/release-082-083.json)):
  copia fresca `pre-release-20261104T232419Z.dump` (126 tablas), ensayo
  **19/19 PASS** sobre esa misma copia (104 tablas con filas idénticas, 116
  lecturas iguales, sin cambios de privilegios, igual a 001–083 limpio);
  preflight sin problemas; 082/083 aplicadas una vez. Verificación de solo
  lectura en producción: objetos, RLS y ACL correctos, trigger de edición
  eliminado, filas y contadores sin cambios.
- API `f1d2896a` SUCCESS (health 200, 132 rutas, `Idempotency-Key` opcional;
  rollback `3c6b1d9f`, compatible con 083). Web `9a17a56c` idéntica al build
  (rollback `43e98b76`). Verifier, Launcher 0.26.11 y optimización Railway sin
  cambios. Copia, ensayo e intent/result en
  `%LOCALAPPDATA%/PokeApp-migration-evidence/net-friendship-discord-082-083`.

Rollback: SQL por fix-forward (082/083 no reescriben datos). No reaplicar
082/083. No se usaron partidas, Team Locks, pastes ni mensajes Discord reales
como fixtures. Guía protegida y archivos ajenos sin tocar.
