# Desempate por enfrentamiento directo y retirada del Blindaje por Robo — registro vivo

**PUBLICADO Y VERIFICADO el 2026-11-18 (00:20 hora local)**, con autorización expresa del propietario.
Rama `claude/net-friendship-discord`. Evidencia: [release.json](../evidence/h2h-086-087/release.json).

| Capa | Estado | Rollback |
|---|---|---|
| Supabase | 001–087. 086 = `20261117231718`, 087 = `20261117231721` | Corrección hacia delante (086 reescribe la J1 con revisión auditada) |
| API | Railway `14ba5fa1` (fuente `b6671ea`, 139 rutas) | `010a6546` (solo antes de 086: no lee snapshots v3) |
| Web | Cloudflare `165bfc7d` | `08fb936b` |
| Launcher / verificador | Sin cambios | — |

Copia y ensayo: `%LOCALAPPDATA%/PokeApp-migration-evidence/h2h-086-087`
(`pre-release-20261117T231117Z`, ensayo 20/20).

**Resultado en producción:** J1 en revisión 2: Iker 1.º (Blindar pendiente), Anto 2.º (su Blindar,
sin usar, cancelado), Samu 3.º, STeeLAG 4.º y Aaron 5.º (antes 4.º compartido, ahora por
combate directo), ByVisan02 6.º (su Robar, ya usado, intacto). «Jornada 1 corregida» enviada a
Discord. Vales «Blindaje por Robo»: 0 pendientes, 2 retirados (ByVisan02, STeeLAG).

**Robo en curso al publicar:** autorización `febddd4b…` (víctima Aaron, adjudicado 21:59 UTC),
a la espera del Launcher. Estaba en la copia ensayada y 086/087 no tocan transferencias; se
aceptó con `phase30_apply_migrations --in-flight-ok`.

**Fallos encontrados por el ensayo y corregidos antes de publicar:** la 086 habría emitido un
segundo Robar al último si ya había usado el suyo (`b6671ea`), y el emparejamiento de la jornada
siguiente de la Liga no filtraba la temporada del segundo jugador (`5426002`).

## Regla (decisión del propietario, 2026-11-17)

Clasificación de cada jornada:

1. Victorias y derrotas.
2. Si empatan **dos**: va delante quien ganó su combate directo en esa jornada.
3. Si empatan **tres o más**: va delante quien tuvo menos muertes del tramo (las que se
   congelan al abrir la jornada). Si después siguen empatados dos, decide su combate directo.
   Si siguen empatados tres o más con las mismas muertes, se usan los combates 1v1 extra de
   siempre cuando afecta al podio, al primero o al último; si no, comparten puesto.

Los puntos NET nunca cuentan para el orden de la jornada. Los comodines (Blindar al primero,
Robar al último) siguen al nuevo orden.

**Retroactivo:** toda jornada ya cerrada de la Liga activa se reordena con la regla nueva.
Caso conocido: Iker ganó a Anto en el directo, pero el Blindar se le dio a Anto (menos
muertes). Anto confirma que **no lo ha usado**. La corrección se anuncia en Discord.

## Blindaje por Robo retirado (decisión del propietario, 2026-11-17)

Robar ya deja el Pokémon robado ROBADO y BLINDADO, así que el vale «Blindaje por Robo» que
recibía quien roba sobra. La 087:

- deja de emitirlo en `api_redeem_purchase` (el recibo de un robo nuevo lleva
  `gift_purchase_id = null`);
- relaja `redemption_boundary_chk` solo en eso (los robos anteriores conservan su vale);
- cancela todo vale no usado (`metadata.cancelled_by_migration = '087'`), que desaparece de
  los inventarios. Los usados y sus blindajes quedan como historia.

API: un recibo de robo es válido con o sin vale. Web: la Normativa ya no lo lista y explica que
el robado queda blindado; el inventario muestra «Comodín retirado» si quedara alguno.

## Qué cambia

| Capa | Cambio |
|---|---|
| Dominio | `rank_head_to_head` en `app/domain/services/league.py` |
| Cierre | regla `wins_h2h_deaths_v3` en `app/application/daily_ranking.py`; `tiebreak` por fila |
| SQL 086 | `league_h2h_order`; contexto y cierre con v3; orden provisional con v3; reordenación única de las jornadas cerradas |
| SQL 087 | robo sin vale; `redemption_boundary_chk` sin exigir vale al robo; vales no usados cancelados |
| API | lee snapshots v3; `StandingRead.tiebreak`; anuncio «Jornada N corregida» con el motivo y «🎁 Comodines de la jornada» |
| Web | columna «Desempate»: «Combate directo» / «Menos muertes»; formulario de 1v1 también con v3; Normativa III |

La 086 reordena desde el propio snapshot congelado (combates, victorias, muertes del tramo).
No cambia resultados, victorias, muertes, puntos, monedas ni la jornada siguiente. Si el orden
cambia: nueva revisión auditada del snapshot, el comodín sin usar se cancela y se entrega al
nuevo destinatario, y se encola el anuncio `matchday_corrected`. Si el comodín que tendría que
moverse ya está usado o ligado a una operación, la migración entera se aborta sin cambiar nada.

## Orden de publicación

1. **API primero.** La API actual rechaza un snapshot v3 («Unsupported official ranking») y un
   recibo de robo sin vale, así que la API nueva (acepta ambos) debe estar viva antes de 086/087.
2. Copia de producción y ensayo (`phase30_backup_rehearsal capture` + `rehearse`). El ensayo
   comprueba fila a fila que solo cambian las jornadas reordenadas, sus comodines, su revisión
   y su anuncio (`tools/rehearsal_086.py`), e informa del orden anterior y nuevo por nombre.
3. 086 y 087 con `phase30_apply_migrations --apply --owner-authorized --backup <manifest>`.
4. Web (`npm run build` + `npm run deploy`).

Sin Launcher.

## Verificación

- Python: suite completa 1549 OK. Web: 47 ficheros / 403 tests; `tsc -b` limpio.
- SQL (PostgreSQL 17.2 portátil en `%LOCALAPPDATA%/PokeAppDev/pg17`):
  `validate_phase086_h2h_tiebreak` PASS (cierres, corrección, orden provisional, 1v1, 087 y
  retroactiva). 075 Liga, dos divisiones, legado y jornadas de participantes PASS en 001–087.
  `validate_phase079_all_vs_all` falla igual en 001–085 (aserción de preparación anterior).
- Ensayo sobre la copia de producción: 20/20, cambios fila a fila solo en lo previsto.
- Producción: API sana con 139 rutas; snapshot J1 leído por el código de la API; web con la regla
  nueva y sin «Blindaje por Robo».

## Cola del propietario (solo después de cerrar esto)

Tramos nuevos (J2 = 5.ª medalla, J3 = 7.ª), el robo sin objeto equipado y el robo entregado
directamente.
