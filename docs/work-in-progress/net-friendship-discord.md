# NET con revividos tras wipe, Felicidad máxima y anuncios Team Lock — 2026-11-04/05

Estado: **PARCIAL PUBLICADO**. Rama `claude/net-friendship-discord`, desde
`68c674f` (tip de `codex/automatic-observed-points`). Producción: DB 001–081.

| Commit | Contenido | Estado |
|---|---|---|
| `9e83cee` | Gourgeist sin sufijo de tamaño; refresco del recuento wipe en la ficha | **PUBLICADO**: API `3c6b1d9f`, web `43e98b76` |
| `c49888c` | SQL 082 (NET con wipe) y 083 (anuncio por confirmación) + API Discord | Preparado; **requiere aprobación** |
| `0ab7a6e` | «Felicidad máxima» (nativo, Launcher, web) | Preparado; **requiere aprobación** y Launcher 0.26.12 |

## 1. Puntos NET

**Defecto real (081).** `league_death_totals` trataba los revividos tras wipe
como un subconjunto de las muertes vistas en la Caja 7. Un wipe cura al equipo
en el juego, así que esas muertes casi nunca llegan a la Caja 7. Resultado: con
más revividos que muertes observadas el NET pasaba a desconocido
(`death_history_inconsistent`, «—»); con menos, cada revivido costaba solo 0,1
(4 muertos + 1 wipe = −0,5 en vez de −0,6). El estado de la jornada no es una
entrada de la función: preparada, abierta o cerrada da el mismo total.

**082** (solo la función de lectura; guard del hash 081 de producción
`5719f5f6…`): muertes reales = offset auditado + eventos efectivos (077/080) +
revividos tras wipe no incluidos ya en una línea base auditada − muertes
observadas que el propio wipe revivió (vistas muertas y luego vivas sin comodín
ni revivido auditado). Penalización = muertes + revividos tras wipe: 0,1 por
muerte ordinaria, 0,2 por muerte revivida tras wipe, nunca doble. Fuentes
ausentes, huecos, caja cambiada y revivals sin mapear siguen siendo
desconocidos. No modifica tablas, filas, snapshots ni ACL.

**Samu.** El «11» es el contador propio del 038, no 11 eventos:
`WIPE_REVIVALS_UPDATED` del propio Samu, 2026-11-04 18:07:22 UTC, 0 → 11
(revisión 1). Es posterior a su primera partida oficial (15:56 UTC) y a la
verificación de 081 (16:58 UTC, cuando tenía 0 puntos). En ninguna de sus 11
lecturas (15:56–18:30) hubo un Pokémon en la Caja 7; tiene 0 eventos, ningún
offset ni confirmación y es participante original (no alta 080). Hoy su «—» no
se debe a la línea base sino a la guarda 11 > 0. Con 082: 11 muertes revividas
tras wipe = **−2,2**. Aviso: 11 supera el equipo de 6, así que implica al menos
dos wipes. La partida no puede probar un wipe. Si el número es un error, Samu
puede corregirlo él mismo («Revividos tras wipe», editable mientras J1 está
programada o abierta) y el NET se recalcula solo.

**Resto, solo lectura (2026-11-04):** Aaron 4 efectivas (5 − 1 corrección 077)
→ −0,4; Iker 3 → −0,3; Anto 0; STeeLAG 0; ByVisan02 sin partida de Liga → «—»
hasta que su propio Launcher la registre. Nadie más tiene revividos tras wipe;
0 victorias y 0 sanciones.

## 2. Felicidad máxima (255)

Nativo `NativeFriendship.cs` (PKHeX 24.11.11). El juego lee la amistad del
manejador actual (`CurrentFriendship`): OT `0xCA` o manejador `0xA2` si fue
intercambiado. El afecto de Pokémon-Amie (`0xCB`/`0xA3`) no se toca. Diff
exacto: ese byte + checksum del PKM. En la partida: ese hueco del equipo + el
checksum de su bloque (+ firma SM/USUM). No se consulta legalidad ni
sugerencias de PKHeX: los aleatorizados no se rechazan. Huevo, equipo cambiado
o ya en 255 se rechazan antes de escribir; repetir es inocuo.

Launcher: mismo motor que Caramelos y Escamas (emulador cerrado, bytes exactos,
copia independiente verificada, diario, relectura nativa y restauración/
recuperación), con diálogo nativo «Felicidad máxima» (equipo, nivel, felicidad
actual, una confirmación ligada a los bytes de ese Pokémon). Web: fila en
Inventario › Objetos ilimitados → `/escritorio/felicidad` desde Launcher 0.26.12.

**Puerta:** `max_friendship` NO está en `PRODUCTION_MUTATIONS`. El Launcher
0.26.11 publicado no lo tiene y uno nuevo lo rechazaría en producción.

## 3. Anuncios Team Lock

Causa: 067 guardaba una fila por Team Lock y la editaba al cambiar el snapshot
público. Volver a fijar el mismo equipo no anunciaba nada, y un mensaje borrado
nunca se reponía (comprobado: Anto J1, enviado 15:50:46 UTC, re-fijado 16:24 sin
mensaje nuevo).

**083:** `team_lock_confirmations` inmutable (snapshot público, entrenador,
jornada, clave de idempotencia, hash de petición) y una fila del outbox por
confirmación, con su propio estado, ID de mensaje y paste. `api_confirm_team_lock`
reutiliza `api_upsert_team_lock` sin cambios (autorización y jornadas
cerradas). La misma clave reproduce la respuesta sin duplicar; la misma clave
con otra petición da `idempotency_conflict`. Se elimina el trigger de edición:
los mensajes anteriores no se editan ni se borran. La web ya envía una
`Idempotency-Key` nueva por clic y la repite solo en reintentos inciertos. El
dispatcher anuncia el snapshot de la confirmación, nunca el último del Lock.

**Gourgeist:** se exporta como `Gourgeist` en la exportación privada y en
Pokepast.es (Jalowin: `Jalowin (Gourgeist) (F) @ Rocky Helmet`; el `(F)` es
su género real). Limitación: Showdown simula entonces el tamaño Medio, cuyos
PS/Ataque/Velocidad difieren del Grande (65/90/84 frente a 75/95/69 base).
La forma real (2) se conserva en PokeApp y en la partida. Pumpkaboo no cambia.

## Verificación (focalizada)

- SQL (PG17 desechable, rollback): defecto 081 reproducido (2); 082 **13
  PASS**; 083 **11 PASS**; 082 sigue 13 PASS con 083.
  [Resultado](../evidence/net-friendship-discord/sql-082-083.json).
- C# `--friendship-checks`: **256 PASS** en los 8 juegos, sobre copias en
  memoria de las fixtures públicas.
  [Resultado](../evidence/net-friendship-discord/friendship-native-checks.json).
- Python: 116 (Team Lock/Discord/Showdown/esquema/puertas) + 87 (Launcher,
  incl. 9 de Felicidad con parser y motor reales: escritura, relectura, copia,
  restauración, corte tras publicar recuperado, repetición, producción
  rechazada). Node 18. Web 66 + `tsc -b`. Los tests nuevos de Discord, Gourgeist e
  invalidación fallaban antes de su corrección.

## Publicado y pendiente

Publicado (sin migración): [registro](../evidence/net-friendship-discord/release-9e83cee.json).
API `3c6b1d9f` (rollback `adfca5c4`), web `43e98b76` (rollback `0eef4feb`).
Sin cambios: verifier, Launcher 0.26.11, optimización Railway, DB 001–081.

Requiere aprobación del propietario:
1. **082 + 083**: copia fresca → ensayo `phase30_backup_rehearsal` (ventana
   082–083 ya fijada) → `phase30_apply_migrations --apply --owner-authorized`
   → API desde `c49888c` o posterior (necesita 083) → comprobar Samu −2,2 y que
   una nueva confirmación crea fila nueva.
2. **Felicidad**: cualificación con una copia de una partida Y real elegida por
   el propietario → añadir `max_friendship` a `PRODUCTION_MUTATIONS` y
   `PUBLIC_READY_MUTATIONS` → Launcher 0.26.12 firmado → después, la web.
   No publicar la fila web antes del Launcher.

No se usaron partidas, Team Locks, pastes ni mensajes Discord reales como
fixtures. Guía protegida y archivos ajenos sin tocar.
