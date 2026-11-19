# «Cancelar jornada» (089) — 2026-11-19

## Motivo

El propietario abrió la J2 de ChampionsLocke por error el 2026-11-19 a las
15:25:38 UTC, antes de que todos llegaran a la medalla del tramo. Al abrirla:

- se congelaron las muertes del tramo de los 6 (`matchday_death_snapshots`,
  tabla inmutable): Anto 3, Iker 1 y el resto 0;
- se marcó la primera apertura (`matchday_start_evidence.first_started_at`).

«Cancelar edición» (operación `cancel`) devuelve la jornada a programada, pero
conserva ambas cosas. Por eso las muertes posteriores se registran como fase
`battle` y no cuentan para el tramo de J2, y al reabrir se reutiliza la foto
antigua. El validador lo reproduce en 088: tras cancelar y reabrir, el tramo de
J2 queda en 1 y se pierden 2 muertes.

## Qué hace

Botón «Cancelar jornada» en Administración › Competición, junto a «Cerrar
jornada» y «Cancelar edición». Solo lo puede usar un administrador, con la
jornada actual abierta y la revisión vigente.
Ruta `POST /v1/admin/seasons/{season}/matchdays/{day}/reset` (cuerpo
`CancelDayBody`), operación SQL `reset` en `api_admin_matchday`
(`matchday_reset_opening`). En una sola transacción auditada
(`MATCHDAY_ADMIN_RESET` con todo lo revertido, y un recibo idempotente):

1. borra las fotos de muertes de esa jornada; las demás jornadas no se tocan;
2. deja `first_started_at` vacío: la jornada vuelve a la fase de progresión;
3. pasa a `progression` las muertes registradas en fase `battle` de esa jornada;
4. los equipos fijados durante la ventana pasan de «tarde» a «a tiempo» y
   siguen fijados;
5. descarta los resultados provisionales;
6. deja la jornada en `scheduled` sin `opened_at`.

La siguiente apertura congela de nuevo las muertes con los datos de ese momento.

Para mantener la inmutabilidad, los triggers de `league_death_events` y
`matchday_death_snapshots` usan `matchday_reset_artifact_guard()`. Solo admiten
dos cambios, y únicamente con el ajuste local de transacción
`pokeapp.matchday_reset` igual a esa jornada:

- borrar sus fotos;
- cambiar `battle` → `progression` (y nada más) en sus eventos.

`service_role` recibe `delete` en las fotos y `update(phase)` en los eventos.
Los roles del navegador no reciben nada.

## Pruebas

- `python -m tools.validate_phase089_matchday_reset --port <libre>` (PG
  desechable): reproduce el fallo en 088 y valida el 089 completo.
- El ensayo de copia (`phase30_backup_rehearsal rehearse`) ejecuta además
  `validate_restored`: sobre la copia restaurada de producción, cancela y
  reabre la jornada actual (con rollback) y comprueba que se congelan los
  mismos números.
- Python `test_api_matchdays` (ruta, solo admin, motivo obligatorio), web
  `admin.test.tsx` (texto del modal y POST).
