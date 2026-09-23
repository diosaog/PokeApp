# PokeApp 2.0 Migration Plan

## Principios

- No empezar React hasta cerrar producto, visual y mecanicas base.
- No hacer megarefactor de Streamlit salvo que ayude a definir el producto final.
- Mantener Supabase al principio.
- Medir antes de optimizar.
- Mantener Streamlit como fallback durante el corte.

## Fase 0 - Base Verde

Objetivo:

- Tests verdes.
- Compilacion verde.
- Documentacion tecnica inicial.
- Inventario de modulos actual.

Salida:

- `py -m compileall -q .`
- `py -m unittest discover -s tests`
- docs iniciales creados.

## Fase 1 - Cierre Visual Streamlit

Terminar Streamlit como referencia visual 2.0:

- Team Preview
- Tienda
- Pokemon Inspector
- Entrenadores
- Liga
- Saves
- PIN
- limpieza visual legacy

Limite:

- No invertir en ingenieria compleja de Streamlit si el cambio solo mueve detalles
  cosmeticos menores.

## Fase 2 - Cierre Funcional

Cerrar mecanicas que afectan modelo:

- Temporada configurable definitiva. Cerrada en Streamlit como A/B oficial:
  jugadores, jornadas, tamanos, ascensos/descensos, puntos, monedas y reglas
  funcionales desde `season_config_v2`.
- Hall of Fame automatico.
- Retirados, robados y abandonos.
- Notificaciones y tipos de evento.
- Panel admin de Anto.

Al terminar esta fase se declara feature freeze funcional para 2.0.

Auditoria base:

- `docs/phase2-functional-audit.md`

Estado 2.3:

- `Temporada/Admin` centraliza estado, configuracion, gestion de entrenadores,
  consola de Liga, historial conceptual y zona de riesgo.
- `TrainerStatus` ya distingue `retired`, `abandoned` y `disqualified`.
- `TrainerFlags` conserva `robbed` separado del estado competitivo.
- El reset global pasa a "descartar temporada" con doble confirmacion.
- Guardar temporadas completas en historial queda diferido a 2.4 porque necesita
  archivo verificable antes de reiniciar.

Estado 2.4:

- Lifecycle legacy activo en `settings.season_lifecycle_v1`.
- `SeasonArchive` legacy en `settings.season_archives_v1`.
- Hall of Fame prefiere entradas congeladas desde archive.
- Nueva temporada se prepara con limpieza activa quirurgica, preservando Hall,
  archivos, saves, usuarios y catalogo.
- Copa queda incluida como snapshot de estado legacy, pendiente de normalizacion
  futura.

Estado 2.5:

- `ActivityEvent` legacy activo en `settings.activity_events_v1`.
- Notificaciones principales leen eventos y solo caen a derivacion legacy si no
  existen eventos nuevos.
- Eventos implementados: save subido, compra completada y equipo fijado.
- Eventos diferidos: cambios de estado, cierre de jornada, ciclo de temporada,
  promociones y redenciones, hasta tener una capa server-side mas formal.

Estado 2.6:

- Auditoria final cerrada en `docs/phase2-freeze-audit.md`.
- Checkpoint de pausa creado en `docs/project-checkpoint.md`.
- Backlog post-2.0 creado en `docs/post-2.0-backlog.md`.
- PokeApp 2.0 queda en feature freeze funcional: no nuevas mecanicas antes de
  la migracion arquitectonica.
- Deuda aceptada principal: `settings` JSON, Streamlit/session coupling,
  seguridad sin RLS/API final, Copa/Juicios como islas legacy y helpers antiguos
  dormidos.

## Fase 3 - Contratos De Dominio

Definir contratos estables:

- Pokemon / PublicPokemon / PrivatePokemon
- Trainer
- Season
- SeasonVersion
- Division
- Matchday
- Match
- LeagueStanding
- ShopItem
- ShopPromotion
- Purchase
- ParsedSave
- TeamLock
- TrainerFlags
- ActivityEvent
- HallOfFameEntry
- Cup
- Trial / Case

Nota de alcance:

- N divisiones reales no se implementan sobre el estado Streamlit A/B. Deben
  definirse aqui como contrato de dominio antes de pasar a repositories/API.

Estado 3:

- Contratos creados en `app/domain/`.
- Documento central creado en `docs/domain-contracts.md`.
- Los contratos son dataclasses/enums dependency-free y JSON-safe.
- No se migro runtime Streamlit, storage, parser, SQL, API ni UI.
- `Division` queda generico para no bloquear N divisiones futuras, pero la app
  actual sigue A/B.
- `NotificationView` queda clasificado como view model fuera de domain.
- `TeamLock` queda como contrato propio con equipo publico congelado y referencia
  de save.

## Fase 4 - Dominio Puro

Extraer funciones que no dependan de Streamlit:

- ranking y standings
- recompensas
- ascensos/descensos
- retirados
- rebajas y validacion de compra
- temporada
- team locks
- trainer flags

Debe poder ejecutarse desde tests, shell, Streamlit o API.

Estado 4:

- Servicios puros creados en `app/domain/services/`.
- Documento central creado en `docs/pure-domain.md`.
- Ranking, pares, H2H, desempates, total con penalizaciones y movimientos A/B
  tienen implementacion pura.
- Rewards construye `LeagueStanding` desde `SeasonVersion`.
- Season resolution/validation existe para contratos de dominio.
- Shop pricing, seleccion de promociones, estado de promo y decision de compra
  promocionada son puros con `now`/RNG explicitos.
- TrainerStatus y TrainerFlags tienen mutaciones puras; el wrapper legacy sigue
  leyendo/escribiendo flags.
- TeamLock, MatchdaySnapshot, ActivityEvent, SeasonArchive, Hall y reglas
  pequenas de Juicios tienen builders/decisiones puros.
- Runtime Streamlit sigue funcionando mediante wrappers legacy; no se migraron
  repositories, SQL, API, React, Discord ni parser.
- Copa, redemptions, money y save parsing quedan como mixed principal para fases
  posteriores.

## Fase 5 - Repositories

Separar intencion de persistencia:

- `SeasonRepository`
- `LeagueRepository`
- `TrainerRepository`
- `ShopRepository`
- `SaveRepository`
- `ActivityRepository`

El dominio no debe llamar a `supabase.table(...)`.

Estado 5:

- Protocols creados en `app/repositories/protocols.py`.
- Legacy repositories creados para Season, League, Trainer, Shop, Save,
  TeamLock, Activity, Hall of Fame y Competition.
- `app/repositories/mappers.py` centraliza conversion legacy <-> contratos de
  dominio.
- Repos in-memory creados para tests y futuros use cases.
- `app/application/` arranca con use cases pequenos para activity, compra con
  descuento y team lock.
- Consumers conectados sin cambio funcional: trainer flags, activity events,
  shop discounts y Hall of Fame.
- Auditoria y source-of-truth matrix documentadas en `docs/repositories.md`.
- No se creo SQL, API, React, Workers ni parser refactor.

## Fase 6 - Supabase V2

Estado 6:

- Decision definitiva: Supabase V2 es greenfield. V1 no se evoluciona con una
  cadena de `ALTER TABLE`.
- SQL reproducible creado en `supabase/v2/migrations`.
- Reset destructivo separado creado en `supabase/v2/reset_dev.sql`.
- Documentacion central creada en `docs/supabase-v2.md`.
- Tests estaticos de schema creados en `tests/test_supabase_v2_schema.py`.
- No se conecto Streamlit a V2, no hay cutover, no se borra V1 y no hay
  migracion de datos legacy asumida.

Modelo V2 principal:

- `trainers`, `seasons`, `season_players`, `season_config_versions`;
- `divisions`, `division_memberships`, `matchdays`, `matches`,
  `matchday_snapshots`, `matchday_movements`;
- `shop_items`, `shop_promotions`, `purchases`, `redemptions`,
  `coin_transactions`;
- `save_files`, `parsed_saves`, `team_locks`;
- `trainer_flags`, `pokemon_flags`, `activity_events`, `hall_of_fame_entries`;
- `season_archive_snapshots`, `cups`, `cup_participants`, `cup_matches`,
  `cup_standings`, `trial_cases`, `trial_votes`, `penalties`;
- `app_settings` solo para settings tecnicas pequenas.

Decisiones clave:

- UUID para entidades principales.
- `season_id` en todo dato competitivo relevante.
- `TrainerStatus` vive en `season_players.status`.
- Monedas viven en ledger (`coin_transactions`), no en saldo mutable.
- Hall y team locks usan snapshots congelados.
- Archive es `seasons.status = archived` mas snapshot opcional, no copia de media
  base.
- SQLite no sera fallback silencioso en produccion V2.

Limitacion:

- Cerrada en Fase 6.1: el schema se ejecuto contra PostgreSQL 17.11 local
  aislado con build, reset y rebuild reales.

## Fase 6.1 - Validacion Real Del Schema V2

Estado 6.1:

- PostgreSQL 17.11 portable local usado como entorno real de validacion.
- Base temporal: `pokeapp_v2_validation`.
- `001_core.sql` -> `009_seed.sql`: OK.
- `009_seed.sql` reejecutado: OK, sin duplicados.
- `reset_dev.sql`: OK tras correccion.
- Rebuild completo `001_core.sql` -> `009_seed.sql`: OK.
- Introspeccion real: 32 tablas publicas V2, 75 FKs y 92 indices.
- Fixtures reales: UUIDs, timestamps, JSONB, current save ownership, uniques,
  checks, coin ledger, archive preservation y delete policy.
- Problema real corregido: `reset_dev.sql` no borraba `trainer_flags` ni
  `pokemon_flags`.
- No se toco Supabase V1, no hubo RLS, API, React ni cutover.

## Fase 7 - RLS Y Seguridad

Estado 7:

- RLS activo en las 32 tablas publicas de Supabase V2.
- Identidad por `trainers.auth_user_id`.
- Admin explicito por `trainers.is_admin`.
- Helpers seguros: `current_auth_uid()`, `current_trainer_id()`,
  `is_current_user_admin()` y `current_user_owns_trainer(uuid)`.
- Vistas seguras `public_*` y `current_*` para lecturas cliente.
- `public_team_locks` expone solo `public_team_snapshot`.
- `current_team_locks` expone `private_team_snapshot` solo owner/admin.
- Saves, parsed saves, compras, redenciones y ledger detallado son owner/admin.
- Escrituras criticas quedan server/API only para Fase 8.
- Bucket `raw-saves` privado con policies sobre `storage.objects` cuando existe
  Supabase Storage, sin cambios de ownership ni `ALTER TABLE` sobre Storage en
  Cloud.
- Validado contra PostgreSQL 17.11 real con roles mock de Supabase y fixtures
  RLS.

Documento:

- `docs/security-rls.md`

## Fase 7.1 - Validacion Real En Supabase

Estado 7.1:

- `tools/validate_supabase_v2_rls.py` creado para validar una Supabase V2 staging
  real con JWT reales y Storage real.
- `.env.supabase-v2-rls.example` creado como plantilla sin secretos.
- El validador cubre Auth users A/B/Admin/orphan, `auth.uid()`, mapping trainer,
  vistas publicas/privadas, aislamiento ParsedSave/TeamLock/economia, activity
  visibility, mutaciones directas bloqueadas, service role y bucket `raw-saves`.
- No toca V1, no conecta Streamlit, no inicia React y no implementa API.
- Ejecucion real completada en Fase 7.1: `RESULT ok checks=13`. Fase 7.2 Storage
  Cloud aplicada. Ese validador completo no se ha repetido durante 8B-H/8C;
  la mutacion 019 tiene una validacion remota independiente de 13 checks.

Regla:

- No empezar Fase 8 hasta que Fase 7.1 pase contra Supabase real.

## Fase 8 - API

API pequena para operaciones criticas:

- `POST /shop/purchase`
- `PUT /v1/seasons/{season_id}/matchdays/{matchday_id}/team-lock` (8C DONE + staging)
- `POST /league/close-matchday`
- `POST /season/config`
- `POST /admin/trainer-flags`
- `POST /trials/...`
- `POST /hall-of-fame/finalize`

Estado 2026-09-22:

- 8A.1: bridge PIN -> Supabase Auth, cerrado.
- 8B: FastAPI Auth/me, cerrado. 8B-H: SDK, UUID/slug y guard de habilitado, DONE.
- 8C: primera mutacion Team Lock V2, DONE local + staging validado el 2026-09-22;
  019 aplicada incrementalmente, 13 checks remotos y fixtures limpiadas.
  Sin dual-write ni conexion Streamlit V2. Rollback forzado validado localmente.
- Contrato 8D.0 en 020 DONE local + staging (5 checks y cleanup PASS).
  Resuelve jornada vigente/sanciones sin heuristicas.
- 8D compra normal + ledger + evento atomicos en 021 DONE local (239 tests,
  PostgreSQL migrations/bootstrap) + staging (29 checks, cleanup PASS).
  [Contrato 8D](phase8d-purchases.md).
- 8E claim promocional atomica en 022 DONE local + staging: 255 tests, PostgreSQL
  17.11 migrations/bootstrap, rollback y siete carreras stock/wallet/retry;
  27 checks reales, regresion 8D de 29 checks y limpieza PASS.
  [Contrato 8E](phase8e-promotional-purchases.md).
  Siguiente: 8F redemption/effect boundary, no implementado.
  Actualizacion 2026-09-23: auditoria 8F BLOCKED, fingerprints colisionan y los
  cuatro canjes existentes requieren Pokemon individual. No 023 ni API nueva.
  8F.0 DONE local + staging (2026-09-23): 023 aplicada como `20260923165532`,
  19 checks reales PASS, 36/36 tablas RLS, 37 vistas intactas y limpieza independiente
  PASS. Fallos intermitentes de transporte y avisos existentes registrados en el informe.
  Retomar 8F con pokemon_entity_id; no implementado en este cierre. Sin endpoint nuevo,
  runtime, dual-write ni escritura de saves. [Contrato y validacion](phase8f0-pokemon-identity.md).
  [Auditoria y limites](phase8f-redemption-effects.md).
  Los endpoints restantes de la lista siguen pendientes: 8C no cierra toda la API.
  8F actual: subconjunto Blindar/Revivir implementado en 024; staging pendiente.
  Compra usada = derecho consumido, no save modificado. Revive queda fisicamente
  pending. Robo Y su comodin no soportados: falta el ShopItem/codigo canonico del
  regalo. No inventado. Siguiente tras validar staging: 8F.1 contrato de catalogo
  del comodin por robo. [Contrato actual](phase8f-redemption-effects.md).
- React/Cloudflare, migracion de datos, shadow mode y cutover no han empezado.

Contrato y evidencias: [Phase 8C](phase8c-team-lock.md).

## Fase 9 - Parser De Saves

Tratar PKHeX/bridge como caja negra:

```text
.sav/.dsv -> parser -> ParsedSave
```

PokeApp consume `ParsedSave`, no detalles internos del bridge.

## Fase 10 - React / Cloudflare

Construir nuevo cliente:

1. Shell
2. Login
3. Normativa
4. Hall of Fame
5. Home
6. Liga lectura
7. Entrenadores
8. PC/Cajas
9. Inspector
10. Tienda
11. Team Preview
12. Saves
13. Copa
14. Juicios
15. Temporada

Cloudflare Pages encaja para frontend. Workers/API solo donde haga falta backend.

## Fase 11 - Migracion De Datos

Transformar JSON de `settings` a tablas V2 con scripts.

Validar equivalencia:

- ranking antes = ranking despues
- monedas antes = monedas despues
- locks antes = locks despues
- flags antes = flags despues

## Fase 12 - Shadow Mode

Durante unos dias:

- Streamlit y React leen los mismos datos.
- Admin compara resultados.
- No se borra Streamlit todavia.

## Fase 13 - Staging Con Datos Clonados

Simular:

- compras
- locks
- saves
- cierre de jornadas
- retiradas
- Hall of Fame
- resets

## Fase 14 - Performance

Medir:

- Home
- Liga
- PC/Cajas
- Team Preview
- Tienda
- save parsing

Optimizar solo con datos reales.

## Fase 15 - Cutover

- Nueva PokeApp como principal.
- Streamlit como fallback temporal.
- Archivo final de Streamlit cuando la nueva este estable.
