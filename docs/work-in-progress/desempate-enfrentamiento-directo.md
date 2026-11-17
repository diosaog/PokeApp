# Desempate por enfrentamiento directo y retirada del Blindaje por Robo — registro vivo

**PREPARADO, SIN PUBLICAR LA BASE DE DATOS (2026-11-17).** Rama `claude/net-friendship-discord`.
Migraciones 086 y 087 pendientes de validar en PostgreSQL (ver «Verificación»).

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

- Python: suite completa 1549 tests OK (módulos versionados + `tests/test_phase086_h2h_tiebreak.py`).
- Web: 47 ficheros / 403 tests; `tsc -b` limpio.
- SQL: **pendiente**. `tools/validate_phase086_h2h_tiebreak.py` (cierres reales, plan v2 y
  orden falsificado rechazados, corrección auditada, orden provisional, 086 retroactiva que
  aborta con comodín usado y mueve el Blindar sin usar; `validate_087`). El PostgreSQL
  portátil de `%LOCALAPPDATA%/Temp/phase10-5l-pg17` perdió sus DLL; los binarios oficiales
  17.2 están descargados en `%LOCALAPPDATA%/PokeAppDev/pg17-download/pg17.zip`, pero el
  control de permisos de Claude Code bloquea extraerlos y ejecutarlos. Sin PostgreSQL local
  tampoco se puede hacer la copia (`pg_dump`) ni el ensayo, así que 086/087 no se aplican.
  Comando, una vez extraído en `%LOCALAPPDATA%/PokeAppDev/pg17`:
  `python -m tools.validate_phase086_h2h_tiebreak --pg-bin %LOCALAPPDATA%/PokeAppDev/pg17/pgsql/bin`.

## Cola del propietario (solo después de cerrar esto)

Tramos nuevos (J2 = 5.ª medalla, J3 = 7.ª), el robo sin objeto equipado y el robo entregado
directamente.
