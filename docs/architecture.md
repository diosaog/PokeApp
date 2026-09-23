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

Desde Fase 3, `app/domain/` contiene contratos dependency-free para las entidades
centrales. Desde Fase 4, `app/domain/services/` contiene comportamiento puro para
las reglas que deben sobrevivir a Streamlit:

- season resolution/validation;
- ranking, standings, rewards y movimientos;
- shop promotions/pricing/purchase decision;
- trainer status/flags;
- team locks;
- snapshots/archive/Hall builders;
- ActivityEvent construction/dedupe;
- pequenas reglas de Juicios.

Los wrappers legacy pueden leer datos, llamar dominio y despues persistir, pero
el dominio no decide permisos, no persiste y no renderiza.

Desde Fase 5, `app/repositories/` separa la intencion de persistencia de la
implementacion legacy:

- `app/repositories/protocols.py` define interfaces con `typing.Protocol`.
- `app/repositories/mappers.py` centraliza conversiones legacy dict/row/json <->
  contratos de dominio.
- `app/repositories/legacy/` encapsula settings, `storage.py`, Supabase V1 y
  SQLite fallback actuales.
- `app/repositories/memory/` ofrece fakes ligeros para tests de application.
- `app/application/` empieza a contener use cases pequenos que coordinan
  repository -> domain service -> repository.

Los consumers conectados de bajo riesgo son `trainer_flags`, `activity.events`,
`tienda.discounts` y `hall_of_fame`. El resto de accesos directos quedan
inventariados en `docs/repositories.md` para Fase 6.

Desde Fase 6, Supabase V2 queda disenado como greenfield SQL-first:

- V1 se trata como referencia de comportamiento y anti-patterns, no como esquema
  a evolucionar.
- `supabase/v2/migrations` contiene el schema reproducible desde una base vacia.
- `docs/supabase-v2.md` documenta modelo, decisiones, RLS readiness, storage,
  delete policy, ledger y reset destructivo.
- No hay cutover, no se borra V1 y el runtime Streamlit sigue usando legacy.
- La fase siguiente fue RLS/seguridad sobre este modelo, antes de API/React.

Desde Fase 6.1, ese SQL se ha ejecutado contra PostgreSQL 17.11 local aislado:

- reset/build/rebuild reales pasan;
- introspeccion confirma 32 tablas, 75 FKs y 92 indices en `public`;
- fixtures validan constraints, ownership de current save, JSONB, ledger,
  archive y delete policy;
- el unico cambio SQL fue corregir `reset_dev.sql` para eliminar
  `trainer_flags` y `pokemon_flags`.

Desde Fase 7, Supabase V2 tiene una capa de seguridad real:

- RLS activo en todas las tablas de aplicacion V2.
- `trainers.auth_user_id` resuelve el trainer autenticado.
- `trainers.is_admin` define admin de forma explicita.
- Las lecturas cliente pasan por vistas `public_*` y `current_*`.
- Datos privados de saves, parsed saves, team locks privados, compras,
  redenciones y ledger quedan owner/admin.
- `raw-saves` queda como bucket privado con policies por path de `trainer_id` en
  Supabase Storage.
- Compras, ledger, redenciones y parsed saves siguen esperando API/RPC
  server-side. Team Lock + ActivityEvent ya tienen la ruta de Fase 8C validada en staging.

Desde Fase 8A.1, existe el nucleo del puente de identidad para mantener la UX de
login actual sin usar el PIN como password real de Supabase:

- La experiencia de producto sigue siendo entrenador + PIN.
- El PIN se trata como string y conserva ceros iniciales.
- `app/auth/credentials.py` deriva una password interna con HMAC-SHA256,
  `POKEAPP_AUTH_PIN_PEPPER` server-only y contexto `pokeapp-v2-auth`.
- El identificador interno de Supabase Auth es deterministico y sale del UUID
  estable del trainer: `trainer-<uuid>@auth.pokeapp.invalid`.
- `app/auth/service.py` exige que el trainer exista, este habilitado y ya tenga
  `trainers.auth_user_id` provisionado antes de iniciar sesion.
- Supabase Auth sigue siendo quien emite la sesion real; el `sub` del JWT debe
  coincidir exactamente con `trainers.auth_user_id`.
- El provisioning de Auth existe como servicio admin separado y nunca ocurre
  silenciosamente durante login.
- En Fase 8A.1 aun no habia HTTP API; no habia cutover de Streamlit y V2 no era
  source of truth del runtime actual.
- Antes de exponer login por HTTP en Fase 8B, la API debe aplicar rate limiting
  por IP, identificador de trainer y ventana temporal.

Desde Fase 8B, existe el primer esqueleto HTTP en FastAPI, aislado del runtime
Streamlit legacy:

- `app/api/main.py` expone `create_app(...)` para tests/inyeccion y
  `app = create_app()` para Uvicorn.
- Ejecucion local prevista:

```powershell
uvicorn app.api.main:app --reload
```

- `GET /health` es publico y devuelve solo estado minimo.
- `POST /v1/auth/pin-login` acepta trainer identifier + PIN solo en body, aplica
  rate limit y delega en `PinAuthBridge`.
- `POST /v1/auth/refresh` acepta refresh token en body y delega refresh a
  Supabase Auth.
- `GET /v1/me` exige `Authorization: Bearer <access_token>`, verifica el token
  con Supabase Auth `get_user` a traves de adapter/puerto y resuelve el trainer.
- Las rutas son transporte fino: no contienen reglas de negocio de Liga/Tienda.
- Fase 8B no migra mutaciones de producto; la primera mutacion real queda para
  Fase 8C: Team Lock V2.

Desde Fase 8B-H, el adapter de Auth usa el builder real PostgREST 2.27.2:
update/eq/execute y comprobacion de la fila devuelta. UUID y slug se distinguen
antes de consultar; las mutaciones exigen `require_enabled_principal`, sin
impedir que `/v1/me` describa un trainer deshabilitado con sesion valida.

Desde Fase 8C (DONE local + staging validado), la primera mutacion de producto es:

```text
PUT /v1/seasons/{season_id}/matchdays/{matchday_id}/team-lock
Bearer verificado -> trainer habilitado -> application.lock_team_v2
  -> lecturas V2 acotadas -> PrivatePokemon / PublicPokemon (exactamente 6)
  -> SupabaseTeamLockRepository -> api_upsert_team_lock
  -> upsert team_locks + TEAM_LOCKED en una transaccion PostgreSQL
```

El cliente solo envia `save_file_id`. Los snapshots y el hash proceden de filas
servidor, no del body. La RPC revalida las filas bajo bloqueo y compara el payload
parseado para rechazar cambios concurrentes. El dominio no importa SDK, FastAPI,
Streamlit ni parser; la proyeccion reutiliza DTOs y normalizacion ya existentes.
La RPC es SECURITY INVOKER, con search_path fijo y EXECUTE solo para service_role.
No se modifica el runtime Streamlit, V1, el parser ni Discord. No hay dual-write.
Migration 019 y bootstrap pasan PostgreSQL local. 019 tambien esta aplicada y
validada incrementalmente en Supabase V2 staging; no se ejecuto bootstrap remoto
ni se desplego FastAPI. Contrato, limites y reproduccion: [Phase 8C](phase8c-team-lock.md).

El contrato aprobado 8D.0 resuelve la auditoria: `seasons.current_matchday_id`
es autoridad explicita con FK misma temporada; las ventanas de Store Ban son
tipadas/inclusivas y requieren expediente `resolved`. Helpers SQL backend-only
y contratos de dominio/repositorio reutilizables, sin heuristicas ni cambio de
runtime. 020 DONE local + staging (5 checks, cleanup PASS).
021 implementa compra normal: route estricta -> application/port -> una RPC
atomica SECURITY INVOKER. Saldo SUM ledger bajo lock season_players; precio,
jornada y elegibilidad promocional server-side; receipt historico idempotente.
Compra pending + debit + PURCHASE_COMPLETED publico se confirman juntos.
DONE local + staging 021 (29 checks con contexto, cleanup PASS). API probada
localmente contra Supabase real, no desplegada. [Contrato 8D](phase8d-purchases.md).

022 extiende la misma infraestructura con compra promocionada: body vacio `{}`,
promocion/item/precio autoritativos, una claim por trainer/promo mediante indice
unico y una transaccion stock + purchase pending + ledger + PURCHASE_COMPLETED.
Orden compartido: trainer/season -> season_player wallet -> day -> item -> promo.
Reutiliza auth/guard, helpers 020, idempotency parsing, DTO base y error mapping.
El cuerpo SQL 8D se conserva como `api_create_normal_purchase_8d`; un wrapper en
el nombre anterior solo rechaza replays cruzados normal/promocion. No redisenia
su contrato ni elegibilidad. `stock_used` queda reservado al backend, incluso
frente a admin via navegador. DONE local + staging (27 checks, 8D regression 29,
cleanup PASS, cuerpos SQL verificados). API no desplegada. Sin redencion,
dual-write ni runtime nuevo. [Contrato 8E](phase8e-promotional-purchases.md).

Auditoria historica 8F (2026-09-23): BLOCKED antes de implementar. Los cuatro canjes legacy
usan una huella Pokemon que puede coincidir entre individuos distintos; bridge
y DTO normalizado no aportan identidad individual suficiente. No se sustituye
por especie/nombre/slot ni se consumen compras para efectos ambiguos. No hay flujo
legacy de canje sin target seguro para portar como subconjunto. 8F.0 debe cerrar
identidad individual y reconciliacion antes de retomar el boundary. Sin 023/API
nueva ni ejecucion PKHeX en aquella auditoria. [Auditoria](phase8f-redemption-effects.md).

8F.0 implementa ahora identidad individual separada de evidencia PKHeX: entidades,
observaciones, revisiones CAS y enlaces de flags en 023. Reconciliador puro en
`app/domain/pokemon_identity.py`, boundary opt-in en `app/application/pokemon_identity.py`
y adapter Supabase backend-only. PID es evidencia, no UUID; clones ambiguos no se
asignan. El bridge solo enriquece lectura. No runtime/dual-write/canje nuevo.
Capturas sin orden fiable no se promocionan; Companion debera aportar una cadena
fiable, no un contador basado en la llegada HTTP. [Contrato](phase8f0-pokemon-identity.md).

## Problema Principal

Phase 8F.1 extends the isolated redemption route with the approved canonical
reward-only voucher and atomic robbery/cycle/gift in migration 025. Entity ownership
is resolved server-side; no physical transfer occurs. See the authoritative
[four-effect contract and lock order](phase8f1-robbery-voucher.md). DONE local + staging:
025 `20260923180416`, 318 tests, 17 robbery and 19 regression check groups, cleanup PASS.
Evidence in [delivery](phase8f-completion-report.md); no API deployment.

Historical 024 checkpoint: Phase 8F adds an isolated JWT self-service redemption route -> typed application
request -> Supabase repository -> backend-only atomic RPC (024). Only exact item
codes for shield/revive are supported. Identity head/owner/location are revalidated
under the same participant lock used by reconciliation. Entitlement consumption
and internal effects are distinct from pending physical work. Private event and
receipt are atomic, without ledger or Storage changes. Browser effect writes,
including admin writes, are revoked on the affected tables. Robbery/voucher remain
blocked by the missing canonical gift item. Streamlit, V1 and physical bridge paths
are untouched. [Contract](phase8f-redemption-effects.md).
The safe subset is validated locally and in V2 staging (024 `20260923172957`),
not deployed as an API. Overall 8F stays PARTIAL until the gift catalog/remaining
effects contract is completed. [Delivery](phase8f-completion-report.md).

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

Supabase V2 greenfield fija la direccion futura:

- `settings` deja de ser fuente de verdad para temporada, liga, Hall, snapshots,
  flags o saves.
- Todo dato competitivo relevante queda scopeado por `season_id`.
- Archive no duplica media base: `seasons.status = archived` conserva las
  relaciones y `season_archive_snapshots` queda como auditoria/export opcional.
- Monedas pasan a ledger (`coin_transactions`) y no a saldo mutable unico.

## Criterios De Salida Por Fase

Ninguna fase debe terminar con la suite previamente verde en rojo.

Minimo antes de avanzar:

- `.venv-api\Scripts\python.exe -m compileall -q -x '[\\/](\.venv[^\\/]*|\.git|node_modules)[\\/]' .`
- `.venv-api\Scripts\python.exe tools/run_unit_tests.py`
- `git diff --check`

Desde 8C, la suite usa SQLite temporal y no hereda credenciales reales. El runner
ejecuta unittest normal; no sustituye errores de persistencia por respuestas
vacias. Entorno y comandos SQL locales: `docs/phase8c-team-lock.md`.
