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

- El entorno local no tiene `psql` ni Supabase CLI, asi que la validacion real
  contra Postgres/Supabase queda para staging/herramientas instaladas.

## Fase 7 - RLS Y Seguridad

Antes de React:

- Definir campos publicos y privados.
- IVs/EVs/naturaleza privada solo para propietario/admin.
- Admin solo Anto.
- Operaciones criticas solo API/RPC.

Regla:

- Si un usuario no debe verlo, tampoco debe poder pedirlo a la base.

## Fase 8 - API

API pequena para operaciones criticas:

- `POST /shop/purchase`
- `POST /team-lock`
- `POST /league/close-matchday`
- `POST /season/config`
- `POST /admin/trainer-flags`
- `POST /trials/...`
- `POST /hall-of-fame/finalize`

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
