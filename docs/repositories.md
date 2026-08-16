# Fase 5 - Repositories

Checkpoint de objetivo: separar la intencion de leer/escribir datos de la
implementacion concreta actual. Esta fase no cambia reglas, UX, SQL, API,
React, Discord ni parser. Encierra deuda para que Fase 6 pueda disenar Supabase
V2 sin que dominio ni application dependan del esquema legacy.

## Decision De Interfaz

Se eligio `typing.Protocol`.

Motivos:

- encaja con dependency inversion sin obligar a herencia;
- permite fakes/in-memory simples para tests;
- mantiene bajo acoplamiento con las implementaciones legacy;
- deja que una futura implementacion Supabase V2 cumpla por forma.

Los protocols viven en `app/repositories/protocols.py`. Las implementaciones
legacy viven en `app/repositories/legacy/`. Las implementaciones de test viven
en `app/repositories/memory/`.

## Regla De Direccion

Direccion objetivo:

```text
UI Streamlit legacy
  -> application/use case o wrapper legacy
  -> repository interface
  -> domain contract / domain service
  -> legacy repository implementation
  -> storage.py / settings / Supabase V1 / SQLite
```

Reglas:

- `app/domain` no importa repositories.
- `app/repositories/protocols.py`, `mappers.py` e in-memory no importan storage,
  Streamlit ni Supabase.
- Solo `app/repositories/legacy/*` puede conocer `storage.py`, settings o claves
  legacy.
- Los repositories persisten y convierten; no calculan rankings, recompensas,
  descuentos, flags ni lifecycle.

## Repositories Creados

| Repository | Archivo legacy | Responsabilidad | Contratos principales |
| --- | --- | --- | --- |
| `SeasonRepository` | `legacy/season.py` | Config activa, lifecycle y archives | `Season`, `SeasonVersion`, `SeasonArchive` |
| `LeagueRepository` | `legacy/league.py` | Estado de liga y snapshots oficiales | `MatchdaySnapshot` |
| `TrainerRepository` | `legacy/trainers.py` | Identidad, status y flags de entrenador | `Trainer`, `TrainerStatus`, `TrainerFlags` |
| `ShopRepository` | `legacy/shop.py` | Catalogo, promociones, compras y redenciones | `ShopItem`, `ShopPromotion`, `Purchase`, `Redemption` |
| `SaveRepository` | `legacy/saves.py` | Metadata de saves y bytes asociados | `SaveRecord` |
| `TeamLockRepository` | `legacy/team_locks.py` | Equipos fijados por jornada | `TeamLock` |
| `ActivityRepository` | `legacy/activity.py` | Eventos append/dedupe/list recent | `ActivityEvent` |
| `HallOfFameRepository` | `legacy/hall_of_fame.py` | Entradas historicas | `HallOfFameEntry` |
| `CompetitionRepository` | `legacy/competitions.py` | Estado minimo Copa/Juicios legacy | `TrialCase` + blobs de Copa |

No se creo un repository por tabla. `ShopRepository` agrupa catalogo,
promociones, purchases y redemptions porque el flujo de compra futuro necesitara
ver todo junto para poder ser transaccional. `TeamLockRepository` queda separado
porque fijar equipo es una operacion critica propia, con lifecycle y queries
suficientes.

## Mappers

`app/repositories/mappers.py` centraliza la frontera:

```text
legacy dict/row/tuple/json
  -> domain contract
domain contract
  -> legacy payload
```

Mappers cubiertos:

- `Season` desde lifecycle legacy.
- `SeasonVersion` desde `season_config_v2`.
- `Trainer` y `TrainerFlags`.
- `ShopItem`, `ShopPromotion`, `Purchase`, `Redemption`.
- `SaveRecord`.
- `ActivityEvent`.
- `HallOfFameEntry`.
- `SeasonArchive`.
- `TrialCase`.
- `TeamLock`.

La serializacion JSON sigue dentro de repositories/mappers. El dominio solo ve
dataclasses/enums JSON-safe.

## Source Of Truth Matrix

| Concepto | Repository | Backend legacy actual | Futuro Supabase V2 |
| --- | --- | --- | --- |
| Season lifecycle | `SeasonRepository` | `settings.season_lifecycle_v1` | `seasons.lifecycle/status timestamps` |
| Season config/versiones | `SeasonRepository` | `settings.season_config_v2` | `season_versions` |
| Season archives | `SeasonRepository` | `settings.season_archives_v1` | `season_archives` + tablas hijas/documento versionado |
| Liga activa | `LeagueRepository` | `settings.league_state` | `matchdays`, `matches`, `division_players` |
| Round snapshots | `LeagueRepository` | `league_state.round_snapshots` | `matchday_snapshots` |
| Entrenadores globales | `TrainerRepository` | `utils.USERS` | `trainers` |
| Trainer status/flags | `TrainerRepository` | `settings.trainer_flags` | `season_players.status` + `trainer_flags` |
| Catalogo tienda | `ShopRepository` | `app/tienda/catalog_data.py` | `shop_items` |
| Promociones | `ShopRepository` | `shop_discounts` Supabase/SQLite | `shop_promotions` |
| Compras | `ShopRepository` | `purchases` Supabase/SQLite | `purchases` |
| Redenciones | `ShopRepository` | `redemptions` Supabase/SQLite | `redemptions` |
| Saves metadata | `SaveRepository` | `saves` Supabase/SQLite | `saves` |
| Saves bytes | `SaveRepository` | Supabase Storage/local files | Storage bucket |
| Team locks | `TeamLockRepository` | `team_locks` Supabase/SQLite | `team_locks` |
| ActivityEvent | `ActivityRepository` | `settings.activity_events_v1` | `activity_events` append-only |
| Hall of Fame | `HallOfFameRepository` | `settings.hall_of_fame_v1` | `hall_of_fame`, `hall_of_fame_team` |
| Copa | `CompetitionRepository` | `settings.copa_*_state` | `cups`, `cup_matches`, `cup_participants` |
| Juicios | `CompetitionRepository` | `settings.juicios_state_v1` | `trial_cases`, `trial_votes`, `trial_penalties` |
| Pokemon flags | Todavia direct legacy | `pokemon_flags` Supabase/SQLite | `pokemon_flags` |
| PIN/login | Todavia direct legacy | `settings.pin:*` | auth/backend separado o `trainer_credentials` |
| Trainer snapshots | Todavia direct legacy | `settings.trainer_snapshot:*` | `parsed_saves`/cache derivada |

## Data Flow Actual Tras Fase 5

### Season Config/Lifecycle

```text
Temporada/Admin legacy o season wrappers
  -> LegacySeasonRepository
  -> settings season_config_v2 / season_lifecycle_v1 / season_archives_v1
  -> mappers
  -> Season / SeasonVersion / SeasonArchive
```

La decision de si una version puede aplicarse sigue en
`app/domain/services/season.py`. El repository solo carga/guarda documentos.

### League State/Snapshots

```text
Liga wrappers legacy
  -> LegacyLeagueRepository
  -> settings.league_state
  -> normalize_round_snapshots + mappers
  -> MatchdaySnapshot
```

Ranking, movimientos, puntos y penalizaciones siguen en dominio puro. El estado
Streamlit sigue siendo mirror runtime y se eliminara por consumidores en fases
posteriores.

### Trainer Status/Flags

```text
app/entrenadores/trainer_flags.py
  -> LegacyTrainerRepository
  -> settings.trainer_flags
  -> domain services trainers
  -> TrainerStatus / TrainerFlags
```

El wrapper publico sigue igual. La carga/guardado de flags queda encerrada. La
sincronizacion historica de robos desde redenciones permanece en el wrapper
porque todavia cruza datos legacy.

### Shop/Promotions/Purchases

```text
app/tienda/discounts.py
  -> LegacyShopRepository
  -> storage_shop / storage facade
  -> shop_discounts / purchases / redemptions
  -> ShopPromotion / Purchase / Redemption
```

La seleccion, pricing, mega eligibility y preflight de compra siguen en
`app/domain/services/shop.py`. `storage_shop.purchase_shop_discount()` sigue
siendo la operacion atomica legacy para promociones.

### ActivityEvent

```text
storage hooks / app.activity.events emit_*
  -> LegacyActivityRepository
  -> settings.activity_events_v1
  -> mappers
  -> ActivityEvent
```

La UI sigue recibiendo dicts legacy desde `app.activity.events`, pero la
persistencia interna ya pasa por repository. `NotificationView` no se guarda.

### TeamLock

```text
Team lock wrapper actual o application.team_locks
  -> TeamLockRepository
  -> storage_shop team_locks
  -> TeamLock
```

El parser y el snapshot del equipo siguen fuera del repository. El repository
solo guarda el equipo publico congelado y referencias de save.

### Saves

```text
Saves UI / entrenadores snapshot
  -> LegacySaveRepository disponible
  -> storage.py
  -> saves table + storage bucket/local files
  -> SaveRecord
```

El parser PKHeX no se toca en Fase 5. `SaveRepository` representa metadata y
bytes, no parseo.

### Hall/Archive

```text
Hall legacy UI
  -> LegacyHallOfFameRepository
  -> settings.hall_of_fame_v1
  -> HallOfFameEntry
```

`SeasonArchive` se puede cargar mediante `LegacySeasonRepository`. La generacion
automatica de entradas sigue en Hall/Archive legacy hasta que los use cases de
temporada se migren por completo.

### Copa/Juicios

```text
Copa/Juicios legacy
  -> LegacyCompetitionRepository disponible
  -> settings.copa_*_state / settings.juicios_state_v1
  -> blobs legacy o TrialCase
```

No se sobrearquitecta Copa/Juicios aun. Copa sigue como blob porque sus flujos
son islas legacy. Juicios ya tiene mapping minimo a `TrialCase`.

## Application Layer

Se crea `app/application/` con use cases pequenos y testeables:

- `activity.record_activity()`
- `shop.purchase_discounted_item()`
- `team_locks.lock_team_for_matchday()`

Patron:

```text
repository read
  -> domain service decision
  -> repository write
```

No se crea API ni UnitOfWork todavia.

## Transaction Candidates

Fase 6/8 debe tratar estas operaciones como transaccionales o server-side:

- compra promocionada: validar stock, claimed-per-user y crear purchase;
- compra normal: crear purchase y emitir activity;
- redemption: marcar purchase used, aplicar flags/effects y guardar redemption;
- team lock: validar participante, save reference y upsert unico por jornada;
- close matchday: resultados, snapshots, rewards, movimientos y aviso;
- trainer status change: status/flags, permisos y actividad;
- season archive: lifecycle, archive, Hall y limpieza activa;
- activity append: dedupe/idempotency.

## Errors

Se crea `app/repositories/errors.py`:

- `RepositoryError`
- `NotFoundError`
- `ConflictError`
- `PersistenceError`

No se filtran errores especificos de Supabase hacia dominio/application. De
momento no se crea una jerarquia grande.

## Enclosed

Accesos ya encerrados tras Fase 5:

| Area | Acceso legacy encerrado | Consumer conectado |
| --- | --- | --- |
| Trainer flags | `settings.trainer_flags` | `app/entrenadores/trainer_flags.py` |
| Activity events | `settings.activity_events_v1` | `app/activity/events.py` |
| Shop promotion scheduling | `shop_discounts`, purchase counts, purchased items | `app/tienda/discounts.py` |
| Hall entries | `settings.hall_of_fame_v1` | `app/interfaz/hall_of_fame.py` |
| Season config/lifecycle/archive | settings keys | repository disponible |
| League state/snapshots | `settings.league_state` | repository disponible |
| Saves metadata/bytes | `storage.py` saves | repository disponible |
| Team locks | `team_locks` | repository disponible |
| Copa/Juicios | `settings.copa_*`, `juicios_state_v1` | repository disponible |

## Still Direct

Accesos directos restantes, razon y fase prevista:

| Archivo/Zona | Acceso directo | Razon | Fase prevista |
| --- | --- | --- | --- |
| `app/season/config.py` | `settings_get/set season_config_v2`, `league_state` | Es fuente funcional actual y tiene guards admin/round status; migrarlo entero requiere use case de season config | Fase 6/8 |
| `app/season/archive.py` | lifecycle/archive/settings, team locks, Hall sync | Orquesta muchas fuentes legacy; mover sin SQL nuevo aumentaria riesgo | Fase 6/8 |
| `app/liga/state.py`, `app/liga/ui.py` | `league_state`, `st.session_state` | Liga Streamlit mantiene mirror runtime y UI admin | Fase 8/10 |
| `app/liga/coins.py`, `app/tienda/money.py` | settings/snapshots/compras | Calculos mixtos con medallas, snapshots y purchases legacy | Fase 6/8 |
| `app/tienda/sections.py`, `redeem.py` | purchases/redemptions/flags/session | Flujo de compra/canje aun UI-coupled | Fase 8 |
| `app/entrenadores/snapshot.py`, `boxes.py`, `page.py` | snapshots, saves, parser/session | Dependen del parser PKHeX y render Streamlit | Fase 9/10 |
| `app/interfaz/auth.py`, `sidebar.py` | `settings.pin:*` | Login/PIN se redisenara con frontend/API | Fase 7/8/10 |
| `app/interfaz/notifications.py` | fallback legacy saves/purchases/locks | Fallback hasta que ActivityEvent sea fuente unica | Fase 6/8 |
| `app/copa/*` | `settings.copa_*_state` | Isla legacy funcional; se conserva blob temporal | Fase 6/8 |
| `app/juicios/repo.py`, `penalties.py` | `settings.juicios_state_v1`, `league_state` | Casos y penalizaciones siguen UI/storage mixed | Fase 6/8 |
| `storage.py`, `storage_shop.py`, `storage_flags.py` | Supabase/SQLite/settings | Infra legacy source actual, no se borra en Fase 5 | Fase 11/15 |
| `discord_notify.py` | settings y HTTP Discord | Notificaciones externas quedan fuera de repositories por ahora | Fase 8 |

## Auditoria De Persistencia

Resumen por operacion:

| Area | READ | WRITE/UPDATE | DELETE/CLEAR | Fuente actual | Fallback |
| --- | --- | --- | --- | --- | --- |
| Saves | list/current/load bytes | upload/set current | wipe active/global | Supabase `saves` + bucket | SQLite + local files |
| Settings | many `settings_get` | many `settings_set` | wipe/reset keys | Supabase `settings` | SQLite |
| League | load state/snapshots | save state on close/admin | reset/discard | `settings.league_state` | SQLite settings |
| Season | load config/lifecycle/archive | save versions/lifecycle/archive | discard/prepare | settings keys | SQLite settings |
| Trainers | load flags/history | set status/robbed flags | clear active flags | `settings.trainer_flags`, redemptions | SQLite settings |
| Pokemon flags | flags by fingerprint | upsert flags | clear owner/all | `pokemon_flags` | SQLite |
| Shop | catalog/promos/purchases/redemptions | purchase/create promo/redeem/status | expire/clear | Supabase tables | SQLite |
| Activity | list/recent/dedupe | append/replace | limit/dedupe overwrite | `settings.activity_events_v1` | SQLite settings |
| Hall | load saved/archive entries | save merged entries | overwrite list | `settings.hall_of_fame_v1` | SQLite settings |
| Copa | load mode states | save mode states | reset modes | settings blobs | SQLite settings |
| Juicios | load case state/penalties | create/update/delete/vote | delete case | `settings.juicios_state_v1` | SQLite settings |

## Backward Compatibility

No se migran datos. Las implementaciones legacy siguen entendiendo:

- JSON existentes en settings;
- rows tuple de SQLite;
- rows dict de Supabase;
- snapshots historicos en `league_state`;
- archives actuales;
- activity events actuales;
- ids numericos legacy como strings en contratos.

## Tests

Se anade `tests/test_repositories.py` con cobertura de:

- dependency direction;
- mapping de season config/lifecycle;
- ActivityRepository legacy, dedupe y visibilidad;
- TrainerRepository legacy status/flags;
- ShopRepository legacy catalog/promos/purchases;
- in-memory repositories;
- use cases de application;
- mappers de frontera.

Los tests actuales de Fase 4 se mantienen.

## Lo Que Puede Asumir Fase 6

Fase 6 puede disenar Supabase V2 contra conceptos, no contra llamadas dispersas:

- existe una lista de repositories por agregado;
- los contratos de dominio ya son el lenguaje de entrada/salida;
- los mappers legacy marcan el shape actual que debe migrarse;
- ActivityEvent, TeamLock, ShopPromotion, Purchase, SeasonVersion,
  MatchdaySnapshot, SeasonArchive y HallOfFameEntry ya tienen frontera clara;
- las operaciones transaccionales estan identificadas;
- no hace falta que dominio conozca tablas nuevas.

Fase 6 no debe empezar a borrar storage legacy. Debe disenar schema V2 y plan de
compatibilidad usando esta matriz.
