# PokeApp Architecture

Este documento es la fuente tecnica viva para la migracion 2.0. La regla base es
conservadora: no tirar la app actual, sino separar el cerebro util que ya existe
del cuerpo de Streamlit.

## Estado Actual

PokeApp es una app Streamlit con logica de liga, tienda, saves, entrenadores,
copa, juicios y Discord. La entrada principal esta en `main.py`, que aplica CSS,
abre login/sidebar/topbar y enruta cada seccion.

La persistencia actual es mixta:

- Supabase es la fuente remota principal cuando esta configurado.
- SQLite local existe como fallback/desarrollo.
- `settings` guarda varios estados agregados en JSON.
- Los saves se guardan como metadatos en tabla y bytes en storage/local.

Tablas detectadas en el modelo actual:

- `saves`
- `settings`
- `purchases`
- `redemptions`
- `pokemon_flags`
- `shop_discounts`
- `team_locks`

Claves importantes guardadas en `settings`:

- `league_state`
- `season_config_v2`
- `trainer_flags`
- `trainer_snapshot:*`
- `pin:*`
- `badges_count:*`
- marcadores de avisos, promociones y recompensas

Desde Fase 2.1, `league_state` incluye `round_snapshots` para jornadas cerradas.
Estos snapshots congelan config aplicada, divisiones, standings, puntos y monedas
otorgadas. Es una solucion compatible con la arquitectura actual, previa a tablas
Supabase V2.

Desde Fase 2.2, `season_config_v2` es la fuente funcional para temporada Streamlit:
jugadores participantes, jornadas, tamanos A/B, ascensos/descensos, puntos,
monedas y reglas funcionales. La decision documentada para Streamlit 2.0 es
soportar oficialmente dos divisiones, Liga A y Liga B; N divisiones queda para el
dominio/API futuro porque requiere cambiar estado, ranking, UI e historico a la
vez.

Desde Fase 2.3, `Temporada/Admin` es el back office funcional. Las paginas
normales deben mostrar y permitir uso, pero no gobernar estado oficial:

- `Entrenadores` ya no contiene controles para abandono/retirada/descalificacion.
- `Saves` ya no contiene wipe/reset global.
- `Liga` renderiza controles oficiales solo cuando se abre desde Admin con
  `admin_mode=True`.
- `Tienda` ya no expone reset global de flags de Pokemon; el mantenimiento queda
  en Admin.
- Las mutaciones de TrainerStatus pasan por `trainer_flags.set_trainer_status()`
  y validan Anto-only por debajo de la UI.
- El descarte de temporada pasa por `app.admin.actions.discard_active_season()`,
  tambien protegido por permiso, decision explicita y confirmacion textual.

`trainer_flags` separa ahora TrainerStatus (`active`, `retired`, `abandoned`,
`disqualified`) de TrainerFlags (`robbed`). El helper legacy
`is_trainer_retired()` sigue existiendo como compatibilidad, pero representa
inactividad competitiva.

Desde Fase 2.4, el ciclo de temporada ya no depende de un wipe tecnico:

- `settings.season_lifecycle_v1` guarda `active`, `finished`, `archived` o
  `discarded`.
- `settings.season_archives_v1` guarda `SeasonArchive` legacy.
- `Temporada/Admin` expone Finalizar, Archivar, Preparar nueva temporada y
  Descartar como acciones separadas.
- `Hall of Fame` prefiere entradas derivadas de archivos, de forma que el equipo
  campeon no cambia si se sube otro save.
- `discard_active_season()` usa limpieza activa quirurgica por defecto, no el
  wipe global legacy.

La limpieza activa conserva archivos historicos, Hall, archives, usuarios,
catalogo y saves. Solo resetea estado competitivo activo: Liga, Copa activa,
compras/promos/redenciones, flags, team locks y config activa.

Desde Fase 2.5, la actividad reciente deja de depender solo de vistas derivadas:

- `settings.activity_events_v1` guarda `ActivityEvent` legacy.
- Un `ActivityEvent` representa un hecho estructurado, no una frase renderizada.
- `NotificationView` es una decision de UI: transforma eventos recientes en
  mensajes breves.
- Los eventos prioritarios implementados son `SAVE_UPLOADED`,
  `PURCHASE_COMPLETED` y `TEAM_LOCKED`.
- Si no hay eventos nuevos, la UI usa fallback legacy desde `saves`,
  `purchases` y `team_locks` para no romper la app durante la transicion.

## Problema Principal

La deuda mas importante no es Supabase. Es que entidades centrales de competicion
viven como JSON grandes dentro de `settings` o como estado de Streamlit.

Esto funciona en Streamlit con pocos usuarios, pero para React/API/Cloudflare se
necesitan consultas directas y permisos por entidad:

- temporada activa
- jugadores de temporada
- jornada actual
- clasificacion
- equipo fijado
- promociones vigentes
- flags de entrenador
- actividad reciente

## Arquitectura Objetivo

Flujo objetivo:

```text
UI
  -> Service
  -> Domain
  -> Repository
  -> Supabase / Storage / external parser
```

Reglas:

- El dominio no sabe que Supabase existe.
- La UI no decide reglas oficiales.
- Las operaciones criticas se validan en backend/API.
- El parser de saves se trata como caja negra.
- Las lecturas publicas pueden ir directas si RLS lo permite.

## Source Of Truth

Hay que decidir y documentar una fuente de verdad por dato:

- Liga oficial: backend/repositorio, no `st.session_state`.
- Compras y promociones: transaccion server-side/RPC o API.
- Saves: metadatos en DB, bytes en storage.
- Snapshots: derivados cacheables, nunca sustituyen al save.
- Hall of Fame: derivado al finalizar temporada/copa, persistido como historico.
- SeasonArchive: fuente historica autosuficiente desde 2.4; en V2 deberia pasar
  a tablas o documentos versionados con `season_id`.
- ActivityEvent: hechos append-only de producto; hoy viven en
  `settings.activity_events_v1`, pero en V2 deben pasar a tabla
  `activity_events`.
- Flags de entrenador: entidad propia, no texto decorativo.

## Criterios De Salida Por Fase

Ninguna fase debe terminar con la suite previamente verde en rojo.

Minimo antes de avanzar:

- `py -m compileall -q .`
- `py -m unittest discover -s tests`
