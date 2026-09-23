# Phase 8G - Season / League Administration API Contract Audit

Fecha: 2026-09-23. **AUDIT ONLY. DONE como auditoria, no como implementacion.**

Base comprobada: `main`, HEAD `34207a9`, upstream `origin/main`, ahead/behind
`0/0`, arbol versionado limpio. Unico untracked permitido:
`docs/pokeapp-guia-completa-pestanas-y-producto.md`, conservado sin cambios.

Phase 8F completa sigue DONE. Baseline anterior: **318 tests PASS**.
Migrations existentes: **001-025**. Ultima migration de staging registrada en
el checkpoint: `025`, version `20260923180416`. Este audit no vuelve a consultar
ni modifica staging; no presenta esa evidencia anterior como una nueva prueba.

Runtime: **Streamlit/V1**. API/V2 aislada; no hay cutover ni dual-write.
Progreso global: **~57% antes, ~57% despues, cambio 0**.

Lectura rapida: [conclusiones](#2-conclusiones-prioritarias),
[permisos](#15-permisos-y-escrituras-directas),
[API propuesta](#18-api-minima-propuesta-no-implementada),
[siguiente subfase](#19-subfases-y-dependencias),
[decisiones de Antonio](#21-product-owner-decisions-required).

## 1. Como Leer Este Contrato

- **OBSERVADO**: comportamiento ejecutable en el repositorio base.
- **GARANTIA SQL**: constraint, grant, policy o funcion realmente existente.
- **PROPUESTA**: contrato recomendado para una implementacion posterior.
- **DECISION Dn**: eleccion pendiente de Antonio. No es una regla aprobada.

No se ha creado migration 026, RPC, endpoint, fixture ni nueva regla. Tampoco
se han cambiado API, dominio, runtime, Discord, parser, PKHeX o saves.
Una funcion auxiliar permisiva no equivale a una funcionalidad soportada por
el producto. Un comentario SQL que dice "immutable" no equivale a un trigger
que impida actualizar. Se distinguen ambos casos expresamente.

## 2. Conclusiones Prioritarias

1. Hay tres finales distintos: cerrar jornada competitiva; marcar temporada
   `finished`; y el boton individual "Liga Finalizada" (12 monedas, 8 medallas).
   No pueden convertirse en una sola operacion API.
2. Legacy no crea una temporada relacional: reutiliza settings globales y limpia
   datos vivos. V2 conserva temporadas identificadas por UUID. No se debe portar
   la limpieza destructiva de legacy como implementacion de `create season`.
3. "Guardar divisiones" borra progreso de Liga, incluso con jornadas anteriores.
   No es un inocuo cambio de roster. Debe separarse de asignacion inicial y de
   movimientos oficiales posteriores al cierre.
4. La inmutabilidad actual es parcial: snapshots resisten cambios normales de
   configuracion, pero existe correccion administrativa; SQL permite UPDATE de
   config/snapshots/Hall a administradores. Faltan barreras de escritura de negocio.
5. V2 no tiene una API de administracion de temporada oculta esperando cableado.
   Tiene tablas, servicios puros y adapters legacy; no la orquestacion transaccional.
6. Configuracion futura, roster efectivo y bajas no tienen aun un contrato V2
   completo. Fechas `joined_at/left_at` no sustituyen jornadas efectivas.
7. Los enums de dominio y SQL de jornadas/partidos no coinciden. Una traduccion
   automatica sin contrato cambiaria significados o produciria datos invalidos.
8. `current_matchday_id` es autoritativo y backend-owned, pero no existe todavia
   el flujo productivo que lo inicializa/avanza. NULL es valido en SQL y bloquea
   nuevas compras, no necesariamente Team Lock.

## 3. Mapa de Fuentes

Referencias `archivo:linea` relativas al repositorio base; los nombres de funciones
ayudan a localizar el comportamiento si las lineas cambian despues.

| Area | Fuentes inspeccionadas | Evidencia principal |
| --- | --- | --- |
| Entrada runtime | `main.py:22`, `utils.py:59`, `app/interfaz/pages.py:42` | Router Streamlit; Temporada se oculta a no-Anto; Liga publica delega al wrapper |
| Back office | `app/interfaz/temporada.py:545`, `:667`, `:853`, `:923`, `:1008`, `:1046`, `:1092` | Lifecycle, editor versionado, bajas, consola Liga, mantenimiento de flags y descarte |
| Permisos legacy | `app/liga/permissions.py:6`, `app/admin/actions.py:13`, `app/liga/ui.py:744` | Anto por nombre; confirmacion DESCARTAR; consola exige ACTIVE y admin no inactivo |
| Config runtime | `app/season/config.py:15`, `:76`, `:226`, `:301`, `:374`, `:431`; `app/season/validation.py:22` | JSON versionado, defaults, seleccion efectiva, ventana de cambios, validacion UI |
| Participantes | `utils.py:66`, `:99`; `app/entrenadores/trainer_flags.py:219`, `:333`; `app/domain/services/trainers.py:87` | Roster por config + filtros; tres estados inactivos distintos; no reactivacion |
| Estado Liga | `app/liga/state.py:34`, `:61`, `:186`, `:229`, `:271`, `:287` | Normalizacion, settings compartido, reescritura al restaurar, sin CAS |
| Jornada actual | `app/liga/context.py:13`; migration `020_current_matchday_store_ban_contract.sql` | `league_tramo` legacy frente a FK explicita V2 |
| Calendario/resultados | `app/liga/ui.py:602`, `:834`, `:920`, `:943`, `:1037`, `:1077`, `:1342` | Correccion, cierre, cancelacion, apertura, divisiones/reset, ganadores |
| Ranking/movimientos | `app/liga/ranking.py:87`, `:128`, `:289`, `:350`, `:430`; `app/liga/divisions.py`; `app/domain/services/league.py:39` | Parejas por division, desempates, recompensas, ascensos/descensos y correccion |
| Historial de jornada | `app/liga/snapshots.py:97`, `:211`, `:234`; `app/liga/coins.py:21` | Config/recompensas/penalizaciones congeladas; lectura snapshot-first |
| Progreso individual | `app/entrenadores/summary.py:117`, `:265`; `app/tienda/money.py:32`, `:131` | Revividos manuales, medallas, bonus individual, saldo derivado |
| Archive/Hall | `app/season/archive.py:105`, `:280`, `:308`, `:471`, `:574`, `:593`, `:661`, `:698`, `:718`; `app/interfaz/hall_of_fame.py:206`, `:372`, `:390` | Finish, archive, nueva temporada, descarte; Hall vivo y archivado |
| Persistencia legacy | `storage.py:446`, `:873`; `app/repositories/legacy/settings_store.py`; `app/repositories/legacy/season.py`; `app/repositories/legacy/league.py` | Settings Supabase/SQLite; sin transaccion global ni proteccion de lifecycle en adapters |
| Contratos puros | `app/domain/seasons.py`, `app/domain/league.py`, `app/domain/trainers.py`, `app/domain/archives.py`; `app/domain/services/season.py`, `league.py`, `rewards.py`, `trainers.py`, `archives.py`, `hall_of_fame.py` | Tipos, validaciones y builders puros; no endpoints administrativos |
| Dependencias de producto | `saves.py:167`; `app/copa/swiss.py:360`, `app/copa/elim.py:197`, `app/copa/doubles.py:575`; `app/juicios/forms.py:109`, `app/juicios/penalties.py` | Inactivos consultan saves; selectors de Copa/Juicios usan activos; sanciones separadas |
| Eventos/Discord | `app/activity/events.py:19`; `app/liga/ui.py:161`, `:242`, `:580`, `:847`; `app/discord_notify.py` | No eventos administrativos completos; notificaciones de resultados, cierres, promociones y locks faltantes |
| API actual | `app/api/main.py:10`, `app/api/security.py:25`, `:49`, `app/api/models.py`; `app/application/team_locks.py`, `normal_purchases.py`, `promotional_purchases.py`, `redemptions.py` | Auth, principal habilitado y mutaciones anteriores; sin router season/admin |
| SQL fundacional | migrations `001_core`, `002_seasons`, `003_league`, `004_shop`, `005_saves`, `006_activity_hall`, `007_competitions`, `008_indexes`, `009_seed` | Identidad/relaciones, enums, integridad, ledger, Hall, ausencia de temporada seeded |
| SQL seguridad | migrations `010` a `018` | Helpers, RLS base, vistas y cambios posteriores de visibilidad |
| Interacciones SQL | migrations `019` a `025` | Team Lock, pointer, compras, identidad, redenciones, locks y replay |
| Bootstrap | `supabase/v2/bootstrap.sql`; `tools/generate_supabase_v2_bootstrap.py` | Artefacto generado de 001-025; comprobacion sin regenerar/escribir |

Busqueda transversal: `git grep` en archivos versionados Python/SQL/docs para
config, lifecycle, season_players, divisions/memberships, current_matchday,
calendario, estados inactivos y movimientos. Se siguieron entradas reales desde
UI y SQL; los scripts de validacion crean fixtures, no funcionalidad de producto.

Tests revisados como evidencia, no como prueba de endpoints inexistentes:
`test_season_config`, `test_season_validation`, `test_season_archive`,
`test_trainer_status`, `test_liga_snapshots`, `test_liga_rewards`,
`test_hall_of_fame`, `test_domain_services`, `test_repositories`,
`test_shop_eligibility`, fixtures SQL de Team Lock/contexto de compras.
Las pruebas de config cubren ventanas efectivas; las de archive mockean storage
y Hall; no prueban transacciones V2 ni todas las transiciones posibles.

## 4. Lifecycle y Una Sola Temporada Activa

### Estados Exactos

| Capa | Estados | Default / diferencia |
| --- | --- | --- |
| Legacy `archive.py` | `draft`, `active`, `finished`, `archived`, `discarded` | Sin setting o valor invalido -> `active`. UI no ofrece crear/activar draft |
| Dominio `SeasonLifecycle` | Los mismos cinco | `Season` default `draft`; dataclass no implementa maquina de transiciones |
| SQL `seasons_status_chk` | Los mismos cinco | Default `draft`; exige timestamp correspondiente para active/finished/archived/discarded |

SQL no obliga a pasar por estados anteriores, ordenar timestamps o tener datos
competitivos. Un administrador con UPDATE puede saltar transiciones cumpliendo
los CHECKs. No hay trigger de lifecycle ni reopen RPC.

### Matriz Observada de Transiciones

En esta tabla "admin" legacy significa nombre `Anto` case-insensitive, no JWT.
Legacy no tiene `current_matchday_id`; se informa el efecto sobre `league_tramo`.

| Desde -> Hasta / operacion | Actor y precondiciones reales | Efectos, historia y pointer | Reversibilidad / eventos |
| --- | --- | --- | --- |
| Sin setting -> ACTIVE al leer | Cualquier consumidor; fallback de `load_season_lifecycle` | No INSERT temporada; no snapshot, archive, Hall o avance | No es activacion explicita; sin evento |
| Crear DRAFT / DRAFT -> ACTIVE | No flujo UI/runtime encontrado; SQL permite INSERT/UPDATE admin | Solo las filas enviadas; no provisioning implicito | No automatismo, pendiente D1 |
| ACTIVE -> FINISHED | Boton Anto; `finish_active_season`: ninguna jornada abierta y >=1 jornada cerrada | Escribe lifecycle/finished_at; conserva datos; tramo intacto; NO nuevos premios/snapshot/archive/Hall | Sin reapertura soportada, sin ActivityEvent/Discord |
| FINISHED -> FINISHED | Helper permite repetir; conserva finished_at previo | Actualiza updated_at; sin duplicar premio porque no da premio | Repeticion tolerada, sin recibo idempotente formal |
| DRAFT o DISCARDED -> FINISHED | Helper solo rechaza ARCHIVED: puede pasar si hay datos cerrados y no jornada abierta | Es una laguna del guard, no una transicion ofrecida en UI | No debe adoptarse como regla V2 |
| FINISHED -> ARCHIVED | Admin, boton nombre de archivo | Crea/reutiliza archive; lifecycle archived; Hall sync best-effort; datos vivos y tramo no se borran | Archivo existente por archive_id se devuelve sin regenerar; sin evento/Discord dedicado |
| ACTIVE -> ARCHIVED | Helper `archive_current_season` llama primero a finish; UI usa dos pasos | Mismos efectos, varias escrituras NO atomicas | Puede quedar FINISHED si falla despues |
| ARCHIVED -> ARCHIVED | Helper reutiliza archive_id existente | No recaptura datos; si falta el archivo referenciado puede reconstruir | Idempotencia operacional, no garantia transaccional |
| DRAFT/DISCARDED -> ARCHIVED | Rechazado por helper | Sin archive | Error; no evento |
| ARCHIVED o DISCARDED -> nueva ACTIVE | Admin `prepare_new_active_season`; limpieza debe reportar ok | Reutiliza espacio legacy, limpia competicion, config default, tramo=1, active=False; conserva archives/Hall/saves | No restaura temporada vieja; no nueva identidad relacional; sin evento/Discord |
| ACTIVE/FINISHED -> nueva ACTIVE | Helper rechaza; antes hay que archivar o descartar | No auto-finish ni auto-archive | No segunda temporada legacy coexistente |
| Cualquier estado -> DISCARDED | Anto + decision `discard` + texto `DESCARTAR`; no guard de origen en helper/UI Riesgo | Borra datos competitivos activos, resetea config/tramo; no crea archive/Hall; archives anteriores permanecen | Destructivo, no reversible; errores pueden dejar limpieza parcial |
| FINISHED/ARCHIVED/DISCARDED -> reabrir misma temporada | No operacion soportada | Preparar nueva no es reabrir | No proponer endpoint de reopen |

Finish UI dice "congela", pero el guard de ACTIVE esta en la consola Liga, no en
todos los helpers, editor config, editor de bajas o otras pestanas. No es un
congelado global de saves/compras/Copa/Juicios. Esta discrepancia debe resolverse
en los contratos posteriores, no corregirse en secreto en este audit.
El loader legacy conserva started_at/finished_at/archived_at/updated_at y archive_id;
no reconstruye discarded_at como hace la entidad/tabla V2. No inferir equivalencia
completa de timestamps entre los tres modelos por compartir los nombres de estados.

### Integridad V2

`008_indexes.sql:6`: **`uq_seasons_one_active`**, unique index en `((status))`
con `WHERE status = 'active'`. Garantiza como maximo una ACTIVE global, no una
por admin o por jugador. Dos activaciones concurrentes no pueden ambas confirmar;
una colision debe mapearse a error de negocio, no finalizar la otra temporada.

SQL admite multiples DRAFT/FINISHED/ARCHIVED/DISCARDED. No hay activacion o archivo
automatico. DISCARDED conserva filas en V2: consultable por admin/backend; la vista
`public_seasons` excluye ese estado. **Las vistas hijas no heredan todas ese filtro**
(ej. `public_season_players`), por lo que descartar no equivale a ocultar todo su
contenido. Estas proyecciones son para `authenticated`, no para `anon`.

## 5. Que Significa Crear Una Temporada

### Legacy Real, Sin Wizard Inventado

Primer uso: defaults de config + `ensure_state()` inicializan session state.
Tras archivar/descartar: `prepare_new_active_season()` llama a
`clear_active_season_state()` y luego marca ACTIVE. `storage.clear_active_competition_rows`
borra team_locks, shop_discounts, redemptions, pokemon_flags y purchases en storage
legacy. No se ha ejecutado ninguna de esas funciones en esta auditoria.

Resetea `league_state`, `trainer_flags`, watermark de robos y los tres estados Copa;
reescribe config con `USERS.keys()`; elimina claves de sesion de Liga/Copa/canje.
No borra archivos, saves ni sus selecciones, trainers/Auth, Hall o archives.
Tampoco resetea expresamente `badges_count:*`, `revived_after_wipe:*`,
`league_finished_reward:*`, notificaciones por ronda, ActivityEvents ni settings
de Juicios. "Nueva temporada limpia" tiene por tanto alcance limitado en legacy.

| Objeto | Legacy al preparar nueva | V2 hoy | Propuesta de responsabilidad futura |
| --- | --- | --- | --- |
| Season identificada | No; mismo settings global | Tabla, sin servicio de creacion | Crear DRAFT con UUID y actor, sin borrar otra |
| Config inicial/version | JSON default, no inserciones relacionales | Tabla sin fila seeded ni generador de version | Version validada separada; requerida antes de activar |
| Participantes | Lista de nombres + trainer_flags vacio | `season_players` unique season/trainer | Provisioning explicito por temporada; no activar a todos los trainers globales |
| Divisiones | A/B vacias en JSON; despues se reparten por orden | `divisions` generica | Configuracion inicial A/B y memberships antes de activar |
| Memberships historicas | No filas; roster mutable + snapshots | Rangos de jornada | Escribir asignacion inicial, no sobrescribir historia |
| Matchdays | tramo=1, sin fila | FK a config obligatoria | Crear jornada 1 una vez conocida config; D1 decide coupling con activation |
| Matches/calendario | Generados al acceder/abrir la jornada | Tabla vacia | Generar solo parejas conocidas de esa jornada |
| Pointer actual | Numero 1 aunque no hay calendario | `current_matchday_id` NULL por defecto | Establecer al existir jornada 1, en operacion atomica server-owned |
| Stats | No reinicio total de settings individuales | Fila stats opcional; defaults 0 si se inserta | Inicializar stats explicitamente al alta; badges reales requieren futuro pipeline saves |
| Flags | Limpia flags legacy | Sin creacion automatica | Sin flags implica false/default; no copiar robos/escudos de otra temporada |
| Economia | Borra compras; otras fuentes pueden persistir | Saldo = ledger, sin fila balance | Sin saldo heredado ni credito inventado; futuras recompensas por evento |
| Saves/identidad | Preservados globalmente | Season-scoped + FK owner | No arrastrar current_save o entidades a otra season automaticamente |
| Copa/Juicios | Resetea Copa, no todo Juicios | Relaciones season/cup/trial | Flujos separados; no crearlos como efecto oculto de crear season |
| Archive/Hall | Conserva anteriores, no placeholder | Tablas relacionales + export opcional | Solo finalizacion/archivo posterior |

`009_seed` crea trainers/catalogo/settings tecnicos y bucket; **no una temporada,
config, participantes, calendario o economia inicial**. Las filas de ese tipo en
validadores son sinteticas, no un create-season listo para produccion.

## 6. Contrato Completo de season_config_v2

No confundir el sufijo de la clave **legacy** `season_config_v2` con la nueva base
Supabase V2. Es un documento JSON en settings, schema_version=1.

Regla comun de edicion **E**: la UI admin llama a validacion y a
`save_season_version`; effective_round debe ser posterior al ultimo cerrado y,
si una jornada esta abierta, posterior a la actual. No hay guard de lifecycle
ACTIVE en este editor/helper. Por tanto FINISHED no cierra por si mismo la edicion.

| Campo | Tipo/default | Significado y consumidores | Edicion / relevancia historica |
| --- | --- | --- | --- |
| `schema_version` | int, 1 | Formato documento; coerce/load/adapters | No editable UI; no es numero de reglas |
| `active_version_id` | str, `default` | Seleccion sin round; editor y repositorio | Apunta a ultima version guardada aunque sea futura; no cambia con cierre |
| `versions` | list de versiones, una default | Config por jornada | Append logico; storage reemplaza JSON entero |
| `versions[].id` | str, `default`; nuevas `v<milliseconds>` | Identidad legacy config, snapshots y Hall | Generado; no contador secuencial ni dedupe formal |
| `name` | str, `Temporada actual` | Nombre en Temporada/Liga/Hall/archive | E; snapshot conserva nombre usado; no es Season UUID |
| `effective_round` | int, 1 | Primera jornada donde aplica | E; clave temporal de seleccion; no timestamp |
| `max_rounds` | int, 4 | Limite Liga; apertura, cierre, movimientos, Hall | E; UI 1-12; reduce/aumenta horizonte futuro, no debe reabrir cierres |
| `players` | list[str], fallback caller o [] | `utils.league_users_for_round`, active_users, Liga, selectores | E; registro USERS; orden influye en A/B inicial; nombres exactos al consumir |
| `division_count` | int, 2 | Validacion y UI | E pero UI fija 2; dominio/SQL mas genericos no autorizan N ligas |
| `division_sizes` | list[int], [5,5] | Corte A/B; suma debe coincidir con roster | E; ambas >0; snapshot conserva config/divisiones reales |
| `movement_count` | int, 3 | Ascensos/descensos al cerrar salvo final | E; validacion <=min(tamanos); helpers acotan al roster efectivo |
| `points_by_position` | map[int,int], tabla inferior | Puntos por posicion global A seguida de B | E; >=0, cubre 1..N; posiciones extras warning; freeze al cierre |
| `coins_by_position` | map[int,int], tabla inferior | Monedas por posicion global | E; mismas validaciones; no es credito ledger V2 implementado |
| `rules.team_lock_required` | bool, true | Aviso de locks faltantes al abrir jornada (`ui.py:161`) | E; no bloquea apertura/cierre por locks faltantes |
| `rules.last_b_gets_steal` | bool, true | `ranking.finalize`: compra gratuita Robar Pokemon para ultimo B | E; no es voucher de blindaje de 025; afecta tambien ultima jornada |
| `rules.cup_is_separate` | bool, true | Mostrado/preservado; RULE_DEFINITIONS lo marca no funcional | E; dominio lo clasifica como metadata; no mezclar economia Copa por cambiarlo |
| Otras claves `rules` | valores preservados | Sin consumidor funcional localizado para claves desconocidas | No inventar reglas; validar allowlist en contrato futuro |

| Posicion global | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Puntos default | 9 | 8 | 7 | 6 | 5 | 5 | 4 | 3 | 2 | 1 |
| Monedas default | 15 | 14 | 12 | 11 | 10 | 11 | 9 | 8 | 6 | 4 |

### Escritura, Seleccion e Historia

`save_season_version` verifica admin/ventana, genera ID, anade version y cambia
active_version_id; `settings_set` guarda todo el JSON. No CAS, transaccion con
league_state ni dedupe por contenido. La validacion completa es de la UI, no se
repite dentro del helper. Dos administradores/sesiones pueden perder un append.

Seleccion por jornada: ordenar `(effective_round, id)` y elegir ultima con
effective_round <= jornada. Si no hay ninguna elegible, el codigo parte de la
primera; es un fallback, no un contrato deseable de huecos V2. Sin jornada usa
active_version_id. Varias versiones legacy pueden compartir effective_round.

Config futura no reinterpreta recompensas de snapshots cerrados. Rondas legacy
sin snapshot se calculan dinamicamente desde config/resultados. `recompute_round`
reutiliza config del snapshot anterior, pero recalcula penalizaciones desde fuentes
actuales y reemplaza snapshot. No conserva revisiones numeradas en legacy.
Movimiento/max_rounds en recompute se leen de config por round; no todo el proceso
esta atado exclusivamente al JSON congelado del snapshot.

Validacion conocida: roster no vacio/unico (case-insensitive), registrado, dos
divisiones no vacias, suma correcta, rewards completos/no negativos, rango valido,
movimientos posibles. El consumidor filtra nombres con pertenencia exacta a USERS;
aceptar una variante de mayusculas en validacion no garantiza que se use ese nombre.
V2 debe usar IDs, no trasladar esa inconsistencia de nombres.

## 7. season_config_versions Relacional

Fuente: `002_seasons.sql`, `003_league.sql`, servicios puros de season y adapters.

| Aspecto | Garantia actual | Lo que falta para mutaciones |
| --- | --- | --- |
| Version | `version_number >0`, unique(season_id, version_number) | Asignacion monotona bajo lock; no sequence por season ni RPC actual |
| Vigencia | `effective_from_matchday >0`, unique(season_id, effective_from_matchday) | Decision sobre sustituir propuesta futura en misma jornada (D3); no effective_at |
| Config base | name, total_matchdays, division_count, promotion_relegation_count | Validacion cruzada de tamanos/participantes/max contra jornadas existentes |
| JSON | scoring_json, coin_rewards_json, rules_json, metadata, defaults {} | Shape canonica, claves numericas JSON y validacion de cobertura; {} permitido no significa config jugable |
| Roster/tamanos | Sin columnas participant_ids ni division_sizes | Relaciones de participantes/memberships y/o metadata versionada deben definir vigencia y reproducibilidad; no hay writer canonico |
| Version actual | No `seasons.active_version_id` SQL | Resolver por jornada efectiva, no newest created_at; dominio tiene active_version_id que no mapea 1:1 |
| Referencias | matchdays config FK same-season; snapshots config FK same-season | No constraint que obligue a que ambas FKs coincidan, ni a config efectiva correcta para ese numero |
| Inmutabilidad | `locked_at` nullable; FK restrict impide borrar filas referenciadas | locked_at no se impone; admin puede UPDATE; ninguna barrera de inmutabilidad/versionado |
| Dedupe | Unicidades de numero y vigencia | Ningun hash de contenido ni recibo de Idempotency-Key general |
| Autoria | created_by_trainer_id nullable | Actor derivado del JWT, no body; no guard lifecycle ni max-closed SQL |

El schema permite division_count cualquiera >0 y effective_from > total_matchdays,
movement_count mayor que capacidad y JSON mal formado semanticamente. No tiene
la validacion del servicio puro. No debe afirmarse que los CHECKs ya implementan
todo el contrato de producto.

**Propuesta**: append de version con configuracion completa validada, numero
asignado por servidor, ventana futura y referencias cerradas inalterables.
Nunca editar reglas de un cierre mediante PATCH generico a una version.
Roster vigente y capacidad historica requieren contrato explicito antes de 8G.1;
no se inventa migration/JSON canonico en esta auditoria.

## 8. Participantes, Bajas y Altas Tardias

Estados exactos en legacy/dominio/`season_players_status_chk`:
`active`, `retired`, `abandoned`, `disqualified`.
`robbed` es flag independiente, **no estado**. `trainers.globally_enabled` controla
acceso global, no es equivalente a ninguno de esos estados de temporada.

### Matriz de Operaciones Observadas

| Operacion | Actor / estado de temporada permitido realmente | Efecto e historia | Soporte V2 actual |
| --- | --- | --- | --- |
| Anadir registrado al roster | Anto mediante nueva config; sin guard lifecycle, ventana E | Empieza a aparecer en round efectivo; no crea stats/saves/cup/trial; reparto puede normalizarse | INSERT season_player admin permitido, sin provisioning/evento |
| Quitar del roster antes de empezar | Anto, nueva config; no boton remove separado | No borra identidad global; sin participantes/relaciones V2 | DELETE sin policy, dependencias restrict; futura operacion de dominio pendiente |
| Alta tras activacion / con cierres | El editor admite nueva lista en jornada futura | No hay wizard late-join, ni politica explicita para puntos iniciales, cup o compensaciones | No endpoint; D2 |
| ACTIVE -> RETIRED | Anto, UI deshabilitada con jornada abierta; helper no comprueba jornada/lifecycle | Guarda status/reason/actor/tiempo, inactive/retired true; limpia robbed del afectado | UPDATE admin posible sin reglas dependientes |
| ACTIVE -> ABANDONED | Mismo permiso/ventana UI | Mantiene razon abandono y etiquetas distintas; elegibilidad colectiva inactiva | No colapsar a retired al migrar |
| ACTIVE -> DISQUALIFIED | Mismo permiso/ventana UI | Razon descalificacion, no borra automaticamente premios/snapshots | No inventar anulacion retroactiva |
| Inactivo -> ACTIVE | Rechazado incluso por helper y servicio puro | No reactivacion dentro de temporada | SQL permite cambiar status: falta guard de negocio |
| Inactivo -> otro inactivo | UI lo impide; helper/servicio no validan estado anterior | Puede cambiar reason dejando flags historicos anteriores | No asumir operacion aprobada |
| Nueva temporada tras baja | Limpieza legacy elimina trainer_flags y usa USERS completos | Vuelve activo por reset de contexto, no por reabrir anterior | Nuevo season_player en otra season; historia anterior se conserva |

### Efectos Dependientes, Sin Atribuir Automatismos Inexistentes

| Area | Comportamiento actual y limite |
| --- | --- |
| Historial/puntos | Snapshots cerrados retienen entrenador y status capturado. Ranking vivo solo usa active_users; inactivos registrados salen al final con 0. Un roster futuro puede ocultar un historico vivo sin borrarlo del snapshot |
| Monedas | coins_from_league retorna 0 si no visible/activo; money_breakdown de inactivo retorna 0. No borra compras ni recompensa historica. V2 ledger/public balances no borra saldo al UPDATE status |
| Divisiones | `ensure_state/_sanitize_divisions` reordena/complete roster; filtro por config de round. El codigo construye curA/curB con normalizador que incluye retirados y no elimina todos antes del corte: no garantiza exclusion perfecta de bajas de grupos ya guardados |
| Scheduling | get_matches_for sincroniza todas las parejas del roster actual, conserva ganador de pareja inversa, descarta parejas que desaparecen. No convierte automaticamente partidos en forfeit/void al dar de baja |
| Saves | No se eliminan. UI Saves inactiva permite consulta/descarga, bloquea upload/cambiar current. No hay efecto atomico del setter de status sobre saves |
| Tienda/canjes | UI impide compra/canje a inactivo; V2 compras/redenciones exigen season_player active. No reembolso ni cancelacion automatica de compras pendientes |
| Robo | Setter legacy limpia flag robbed de esa persona, no resetea inmediatamente ciclo global. 025 serializa roster; antes/despues del robo evalua ciclo contra activos actuales. Historico inmutable de redenciones y watermark no se borran |
| Copa | Formularios de altas/listas toman active_users; competiciones guardadas tienen su propio roster/estado. Setter status no recalcula automaticamente brackets, resultados ni premios |
| Juicios | Selectores usan activos; casos/sanciones persistentes no se borran ni resuelven automaticamente al retirar alguien |
| Stats | No setter admin directo de season_player_stats en runtime; badges vienen de save/cache. Status no reinicia medallas ni otros settings individuales |

Legacy soporta tecnicamente cambiar la lista efectiva a futuro; no documenta un
contrato completo de alta tardia/remocion tras partidos. Restaurar league_state
puede normalizar resultados legacy, desplazar posiciones removidas o reescribir
settings sin CAS. Snapshots normalizados se conservan aparte. **No usar esos
efectos incidentales como politica V2 de correccion historica.**

SQL tampoco modela entrada/salida por numero de jornada: `joined_at/left_at`
son timestamps y no tienen guard ligado a status. Dominio SeasonPlayer incluye
joined_matchday/left_matchday/division_id; SQL usa memberships y no esas columnas.
Alta/baja efectiva y roster de una config no se resuelven solo con un mapper.

## 9. Divisiones y Movimientos

Legacy soportado: dos grupos, A superior y B inferior. Default 5/5 y tres
ascensos/descensos. El numero real depende de config efectiva y activos.
Inicio por orden de roster (primeros N en A) o eleccion manual de Anto.

`Guardar divisiones` (`ui.py:1037`) valida cantidad A/B y luego pone tramo=1,
active=False y vacia matches/results/movements/snapshots. El boton solo depende de
can_manage_league: no exige ausencia de historia ni jornada cerrada. No borra
compras alli. `Reiniciar liga` si intenta clear_purchases, con error absorbido;
tampoco equivale al descarte general de temporada.

Movimiento competitivo (`ranking.finalize:329`, servicios league): al cierre
no-final suben primeros B y bajan ultimos A; se conservan otros. Nueva A = quedan
A + suben; nueva B = bajan + quedan B. Se guarda movement[round]. Ultimo cierre
no genera ascensos/descensos. No hay movimiento exclusivo de final de temporada.

SQL:
- `divisions`: code uppercase, name, tier_order>0; code y tier unicos por season.
  Admite N tiers, no hay filas A/B seeded ni reglas para N divisiones.
- `division_memberships`: rango desde/hasta numero de jornada; reason
  `initial|promotion|relegation|admin|status_change`; source_matchday opcional.
- FK same-season en player/division/source; unique(player, effective_from).
  No exclusion constraint de rangos solapados, no un solo rango abierto, no
  comprobacion de capacidad, actividad o pertenencia a esa division en matches.
- `matchday_movements`: promotion/relegation/stay/admin; no unique por
  jugador/jornada/tipo que evite duplicacion por reintento.

**Limite recomendado**: asignacion inicial validada, historica y sin borrar progreso
en 8G.1. Movimiento posterior pertenece al cierre 8H; intervencion manual posterior
necesita motivo, vigencia y politica aprobada, nunca reutilizar reset legacy.

## 10. Jornadas, Calendario y Partidos

### Calendario Real

No hay calendario completo de toda la temporada ni fechas fijadas por wizard.
Cada "jornada/tramo" contiene todos contra todos **dentro de cada division**:
n(n-1)/2 parejas, 10 por grupo con 5 entrenadores, 20 combates por tramo default.
No es una jornada de un solo partido por entrenador. El proximo tramo cambia de
grupos por ascensos/descensos: no se conocen de antemano todas sus parejas.

`get_matches_for(tramo)` genera/sincroniza diccionario A/B al abrir/acceder;
`generate_pairs` es determinista segun orden de roster. No hay UI de cambiar
jugadores de un partido, reordenar numeros o borrar una jornada individual.

| Accion solicitada en audit | Legacy real | Clasificacion futura |
| --- | --- | --- |
| Crear jornada manual | Abrir/editar tramo actual, numerado automaticamente | Preparar jornada actual, no CRUD arbitrario |
| Generar calendario completo | No existe; depende de movimiento futuro | No prometerlo; a lo sumo shells de jornadas, decision separada |
| Regenerar | Sync de parejas al consumir; cancel/open rehace; reset destruye | Generacion idempotente de una jornada conocida; no regenerar con resultados/locks sin contrato |
| Editar emparejamientos | No editor; cambia indirectamente con roster/divisiones | Fuera de API minima; no inventar feature |
| Abrir | active=True, genera matches, persiste, avisa locks faltantes | Admin setup; debe validar config/roster/pointer |
| Cancelar edicion | active=False, elimina matches del tramo; NO incrementa tramo | Operacion administrativa con historia/pointer pendiente D5 |
| Cerrar | Exige ganadores A/B, snapshot, premios, movimiento, tramo+1 | Transaccion competitiva 8H, NO 8G.1 |
| Reordenar/eliminar jornada | No operacion especifica | No exponer endpoint por existir tabla |
| Reset Liga | Reinicia estado + intenta borrar compras | Riesgo, no setup ordinario; no portar a V2 |

### Estados y Transiciones de Matchday

| Capa | Valores exactos |
| --- | --- |
| Legacy | `league_active` bool + tramo + existencia de resultados/snapshot; False no distingue pendiente/cancelada/cerrada |
| Dominio `MatchdayStatus` | `planned`, `open`, `closed`, `cancelled` |
| SQL `matchdays_status_chk` | `scheduled`, `open`, `closed`, `cancelled` |

SQL exige closed_at cuando closed; no exige NULL en otros estados ni opened_at
cuando open. No limita una open por season, no max(number)<=total_matchdays y
no legal-transition trigger. Domain `planned` requiere traduccion explicita a
`scheduled`; Team Lock ya usa valores SQL, no cambiarlo por el enum puro.

| Transicion conceptual | Evidencia/actor | Efectos y limite |
| --- | --- | --- |
| inexistente -> scheduled | Shell solo existe en V2/fixtures; propuesta admin | Fijar config/jornada del mismo season; no premios |
| scheduled -> open | Equivalente a Editar jornada Anto, ACTIVE | Generar/validar parejas y marcar apertura; sin cierre |
| open -> closed | Finalizar jornada Anto, todos ganadores | Snapshot+recompensas+movimientos+avance en 8H |
| open -> pending editable | Cancelar legacy | Elimina matches, mantiene numero/locks; no estado cancelled persistido |
| cancelled -> open | No contrato V2; legacy permite volver a editar el mismo tramo | D5; no afirmar soporte porque SQL acepte UPDATE |
| closed -> open | No reapertura ordinaria | Correccion anterior reemplaza resultados/snapshot sin cambiar lifecycle a open |
| scheduled/closed -> cancelled | Sin flujo especifico equivalente | D5; rechazar por defecto hasta contrato |

### Match, No Confundir Con Matchday

Dominio `MatchStatus`: **scheduled, reported, confirmed, void**.
SQL `matches_status_chk`: **scheduled, completed, forfeit, void**.
Legacy: pair -> ganador o None, sin reported/confirmed/forfeit/void estructurados.
No soporte runtime que justifique introducir flujo report/confirm de entrenadores.

SQL exige jugadores distintos, ganador de la pareja y FKs same-season. No exige
winner para completed/forfeit ni NULL para scheduled/void. Unique conserva orden:
(A,B) y (B,A) podrian coexistir; la misma pareja en distinta division tambien.
No verifica que ambos pertenezcan a division efectiva de esa jornada.

| Operacion | Autoridad/evidencia | Efectos |
| --- | --- | --- |
| Crear pareja | Generador, no entrada libre | Setup de jornada; sin puntos/monedas |
| Editar jugadores | Sin accion UI | No endpoint minimo |
| Guardar/quitar ganador en open | Anto en consola ACTIVE, batch A/B | Persiste matches, limpia cache, Discord de resultados; no reparte premios |
| Corregir open | Mismo formulario | Cambia ganador o None antes del cierre |
| Corregir closed anterior | Anto, formulario jornada inmediatamente anterior | recompute snapshot/puntos/monedas/movimientos; puede borrar matches del tramo actual, Hall sync si final |
| Cancelar/borrar partido individual | Sin accion; se pierden con cancelar jornada/reset/sync | No inventar void/forfeit como mecanica |

Correccion legacy no reconcilia/revoca el comodin gratuito del antiguo ultimo B,
no emite ajuste ledger (no existe ledger legacy), ni revierte compras ya realizadas
con monedas previas. Eso es una decision de compensacion de 8H, no CRUD matches.
`coin_transactions` admite amount distinto de cero y tipos matchday_reward,
purchase, penalty, admin_adjustment y compensation; el enum no implementa esos
flujos. Rewards configuradas a 0 deben omitir credito, no insertar amount=0.
No hay unicidad especifica de reward por jornada/jugador en 004/008: el futuro
cierre necesita dedupe economico propio, no confiar solo en la fila snapshot.

## 11. current_matchday_id: Contrato y Preguntas Abiertas

GARANTIA existente de 020: columna nullable, FK `(current_matchday_id,id)` ->
`matchdays(id,season_id)`; no INSERT/UPDATE de esa columna para authenticated.
`api_resolve_current_matchday` toma season/day FOR SHARE, rechaza NULL o cancelled;
**acepta scheduled/open/closed**. No infiere por MAX/MIN ni por estado open.

Legacy usa `league_tramo`, incluso entre rondas y tras final: al cerrar r pasa a
r+1; despues de ultima puede ser max_rounds+1 sin jornada real.

| Momento | Actual | Propuesta / decision necesaria |
| --- | --- | --- |
| Crear DRAFT | NULL SQL permitido | Mantener NULL mientras falta config/jornada |
| Primera jornada existente | Ningun writer admin implementado | Inicializar pointer dentro de preparar/activar, nunca paso manual desde browser |
| Activar | SQL exige started_at, NO pointer | D1: recomendar activacion solo cuando jornada 1 y setup valido existan |
| ACTIVE con NULL | Valido DB; nuevas compras fallan `current_matchday_required` | No presentarlo como competicion lista; estado incompleto debe rechazarse por flujo futuro |
| Entre jornadas | Resolver admite pointer closed hasta avance | En cierre no-final, crear/preparar siguiente y mover pointer en MISMA transaccion 8H |
| Tras ultima | Legacy numero ficticio max+1; SQL FK no puede apuntar a fila inexistente | D6: conservar ultima closed durante revision o finalizar atomico; no fabricar ronda extra |
| Cancelada | Resolver falla `current_matchday_invalid` | D5: no dejar season activo inutilizable ni buscar otra jornada por heuristica |
| FINISHED/ARCHIVED | Ningun trigger modifica pointer | Proponer conservar ultimo closed por trazabilidad; nuevas compras bloquean por lifecycle, no por NULL |

Team Lock 019 exige season active, player active, matchday scheduled/open y
closed_at NULL; recibe matchday_id explicito. **No exige que sea current_matchday_id**.
Crear todos los shells de golpe permite locks en jornadas futuras por el contrato
ya terminado. Por eso la API minima no debe generar una temporada completa de
shells sin decidir ese efecto; tampoco se restringe 019 en este audit.

Las redenciones 025 no exigen season ACTIVE ni pointer/store-ban: exigen actor
habilitado y participante active. Finalizar o archivar no las bloquea por si mismo.
No cambiar ese contrato anterior con un guard administrativo indirecto.

## 12. Standings, Stats y Ajustes Manuales

Ranking de division: mas victorias; empate de dos por enfrentamiento directo,
fallback nombre; empate >=3 por muertos ajustados y nombre. No hay editor directo
de wins/losses, posicion, puntos base o coins de Liga. Ganadores y configuracion
son entradas, standings derivados. `counts_for_league_reward` hoy siempre true.

Muertos ajustados: muertos observados + max(revive redemptions, used revive items)
+ 2*revived_after_wipe. Penalizacion de 0.2 por unidad ajustada y reducciones
Juicios; ultimo snapshot fija penalizaciones para puntos ya cerrados. No hay
saldo mutable en season_player_stats: solo badges_count/metadata. Coins V2 se
calculan desde `coin_transactions`, no copiando el saldo mostrado en Streamlit.

Correcciones existentes que NO se deben borrar conceptualmente:
- Ganadores de jornada anterior, con recompute y consecuencias ya descritas.
- Puntos/coins por posicion via version futura de config.
- Juicios aplica reducciones de puntos/monedas y Store Ban; flujo distinto, no
  permiso admin para escribir cualquier total.
- Entrenador activo en perfil propio declara revividos tras wipe (0..30 UI),
  guardados en settings. No es accion exclusiva del administrador.
- Medallas se obtienen del save y se cachean (`badges_count:*`), no editor stats.
- Bonus individual "Liga Finalizada": propio perfil activo, >=8 medallas y no
  reclamado. Graba setting bool y suma **12** monedas. No comprueba season finished
  ni finalizacion competitiva; `finish_active_season` no llama a ese helper.

En V2 no hay endpoint de ajustes de badges/revividos/bonus individual todavia.
No introducir `PATCH stats` ni credito manual como sustituto. Los futuros ajustes
economicos necesitan causa y ledger, no borrar transacciones previas.

## 13. Finish, Archive y Hall

### Finish No Hace Un Cierre Competitivo

`finish_active_season`: admin, no round abierto, >=1 closed; conserva finished_at
previo. No comprueba completar max_rounds. NO genera snapshot ni final reward,
movimientos, archive, Hall, bonus individual, refund, cancelacion de promos/canjes,
save nuevo o resolucion Copa/Juicios. NO cambia tramo/pointer. UI Liga se vuelve
de consulta; otras superficies no comparten un freeze global.

Ultimo `finalize(round)` en cambio calcula ranking/rewards/snapshot, otorga Robar
Pokemon si regla activa, omite movimiento final y avanza tramo; la UI sincroniza
Hall y expira/promueve descuentos fuera del persist principal. No marca FINISHED.

### Archive Legacy

Trigger manual desde FINISHED; helper admite ACTIVE finalizandola antes. Captura:
config completa/version usada, union de roster y participantes de snapshots,
status/flags entrenador, LeagueState/resultados/movimientos/snapshots,
standings y penalizaciones finales, monedas adjudicadas, locks hasta final_round,
equipo campeon publico, estados Copa y entradas Hall derivadas, metadata/tiempos.

Equipo campeon: lock ultima jornada -> ultimo lock disponible -> snapshot legacy
actual cacheado (sin rebuild) como fallback. `public_pokemon_snapshot` excluye datos
privados; no debe copiarse private_team_snapshot a una vista publica.

ID archivo deriva de nombre/version/final_round/digests snapshots y Copa. Repetir
archive con archive_id existente devuelve documento anterior aunque datos vivos
hayan cambiado. No boton regenerar. Si falta referencia puede reconstruir; es
idempotencia parcial, no garantia ante dos sesiones concurrentes.

Guardar archive y lifecycle son escrituras separadas; Hall sync absorbe errores.
No borrar vivo al archivar. Limpiar al preparar siguiente conserva archive/Hall.
Archive no incluye como tablas completas todo el ledger/compras/saves/trials.

### Hall Dependency Map

```text
Ganadores + config + roster + penalizaciones
  -> cierre de jornada -> snapshots + standings + movimientos + premios
  -> ultimo cierre -> Hall automatico provisional legacy
  -> mark FINISHED (solo lifecycle legacy)
  -> archive capturado con equipo publico congelado
  -> merge Hall: entrada archive prevalece sobre live con el mismo id
  -> preparar nueva: archive/Hall anteriores sobreviven
```

Hall legacy tambien deriva de Copa suiza, eliminatoria y dobles terminadas.
No requiere ARCHIVED ni FINISHED de temporada para automatic entries: Liga usa
numero de cierre/max_rounds y podium. `sync_hall_of_fame_from_sources` actualiza
entries por id, conserva created_at y antepone la fuente archivada en el merge;
antes de archive una entrada live puede cambiar. Se puede sincronizar al visitar
Hall, no solo al ejecutar archive. No es inmutable por almacenamiento.

V2 conserva todas las relaciones mediante season_id; `season_archive_snapshots`
es export/auditoria opcional unique(season), **no reemplaza** fuente relacional.
`hall_of_fame_entries` tiene unique(season,competition_type), campeon/finalista,
team_snapshot publico congelado y finalized_at. Admite una entrada por tipo/season,
no multiples torneos del mismo tipo sin otro contrato. FK no exige lifecycle
archived/finished y policy admin UPDATE contradice inmutabilidad fuerte.

Finish/archive/Hall productivos pertenecen a subfase posterior, despues de cierre
consistente, politica de correccion y final rewards. No se implementan en 8G.1.

## 14. Fronteras de Inmutabilidad

| Frontera | Observado | Contrato que se debe imponer despues |
| --- | --- | --- |
| Jornada abierta | Resultados y Team Lock editables; config nueva solo para futuro | Capturar config/roster efectivo; CAS en edicion; sin recalcular reglas en vivo |
| Jornada cerrada | Snapshot-first normal; helper especial recompute lo reemplaza | Sin PATCH generico a config/matches/locks/snapshot; correccion explicita con compensaciones y revision |
| Snapshot SQL | Una fila por matchday, revision default1, comentario pide incrementar en recompute | Ni incremento automatico ni historial de revisiones garantizado; disenar atomicidad y evidencia |
| Movimientos | Legacy reemplazables por recompute; SQL filas sin dedupe especifico | Revision y coherencia con memberships de siguiente jornada |
| FINISHED | Solo consola Liga read-only; data viva aun mutable en otras rutas | Definir que se revisa/corrige; no prometer freeze universal incompatible con 025 |
| ARCHIVED | Documento legacy conservado; V2 relaciones conservadas | Config/snapshots/memberships/Hall y locks historicos no deben reinterpretarse; export/Hall a partir de datos congelados |
| Team Lock | 019 no acepta closed/cancelled ni season no-active | Mantener garantia; no borrar locks al reconfigurar/cancelar sin decision explicita |
| Ledger/efectos | Compras/canjes anteriores transaccionales | No reset/delete por setup, status o finish; pending physical effects permanecen trazables |

Un FK a una version **mutable** no congela su contenido. Un campo revision sin
guard no evita lost update. Las barreras pendientes se documentan, no se anaden hoy.

## 15. Permisos y Escrituras Directas

### Identidad de API

Futura autorizacion obligatoria: bearer verificado con Supabase Auth -> auth user
id -> lookup `trainers.auth_user_id` -> globally_enabled -> `trainers.is_admin=true`.
`app/api/security.py` ya verifica principal/habilitacion; **no existe aun dependencia
require_admin**. `AuthenticatedPrincipal` transporta is_admin. No aceptar nombre,
slug, actor_trainer_id o admin flag del body como autoridad.

`010`/`014`: helpers fijan search_path y consultan identidad habilitada/is_admin.
Legacy tiene excepciones adicionales de UI: can_manage exige no inactivo + ACTIVE
+ admin_mode; bajas bloqueadas con round abierto; descarte exige confirmacion
textual. No asumir que admin V2 necesita tambien ser participante activo: legacy
aplica ese filtro en Liga, no uniformemente en finish/config. D1 fija alcance admin.

### Grants/RLS Efectivos 001-025 (Inspeccion de Codigo)

Migration 011 habilita RLS, revoca PUBLIC/anon y concede SELECT/INSERT/UPDATE/DELETE
a authenticated en las tablas base enumeradas, ALL a service_role. Las policies
abajo limitan las filas: **un grant DELETE no autoriza borrar si no hay policy**.
En ninguna de estas ocho tablas hay policy DELETE.

| Tabla | SELECT directo authenticated | INSERT/UPDATE directo authenticated admin | DELETE | Excepciones |
| --- | --- | --- | --- | --- |
| seasons | Solo admin | Si, policy admin | Denegado por RLS | 020 revoca grant de tabla I/U y concede columnas previas EXCEPTO current_matchday_id |
| season_players | Owner o admin | Si, admin | Denegado | Puede cambiar status/owner/current_save sin flujo dependiente si satisface FKs |
| season_config_versions | Solo admin | Si, admin | Denegado | locked_at/uso historico no impiden UPDATE |
| divisions | Solo admin | Si, admin | Denegado | No regla A/B, capacidad ni freeze |
| division_memberships | Solo admin | Si, admin | Denegado | No exclusion de rangos solapados |
| matchdays | Solo admin | Si, admin | Denegado | Status/config/opened/closed alterables bajo CHECKs, no transicion atomica |
| matches | Solo admin | Si, admin | Denegado | Resultado/parejas alterables fuera de cierre |
| season_player_stats | Owner o admin | Si, admin | Denegado | Badges/metadata no pipeline autoritativo obligatorio |

`service_role` conserva acceso privilegiado; RLS no garantiza que un backend con
ese rol autorice bien. Cada futura RPC de servicio debe recibir actor resuelto por
API, comprobarlo y tener EXECUTE revocado a public/anon/authenticated, siguiendo
la arquitectura actual; no exponer una RPC privilegiada que confie en actor enviado
por browser. Tampoco introducir credenciales de servicio en React.

`012` da SELECT en vistas a authenticated; `014` hardening invoker; `015-018`
modifican visibilidad y **018 deja 24 proyecciones public_* con security_invoker=false
y security_barrier=true**. No decir que todas las vistas finales siguen invoker.
No concede INSERT/UPDATE a browser en esas vistas. `public_*` no significa anon.
Las proyecciones current_* mantienen su frontera privada. No se modifican aqui.

`020` protege pointer, `022` stock y `024` endurece tablas de efectos/compras;
no revocan el conjunto de escrituras administrativas de Liga de esta tabla.
**Conflicto real**: con permisos actuales un admin puede saltarse la futura API y
sus invariantes via Data API. Harden de tabla/columna/policy debe acompanar a la
subfase que haga backend-owned cada operacion, con prueba de acceso directo denegado.
No se aplica ese endurecimiento durante esta auditoria.

## 16. Eventos y Discord

| Operacion | ActivityEvent legacy encontrado | Discord legacy encontrado |
| --- | --- | --- |
| Crear/preparar/activar season | No dedicado | No dedicado |
| Version config/alta roster | No dedicado | No dedicado |
| Retirar/abandonar/descalificar | No dedicado | No dedicado |
| Guardar divisiones/reset Liga | No dedicado | No dedicado |
| Abrir jornada | No dedicado | Aviso de locks faltantes, si regla/notificaciones activas; setting evita repeticion |
| Guardar/corregir ganadores | No dedicado en activity_events_v1 | Aviso de resultados modificados |
| Cerrar jornada | No dedicado en ActivityEvent legacy | Resumen, podium si final y promociones; errores no deshacen cierre |
| Finish/archive | No dedicado | No dedicado; Hall sync es persistencia, no Discord |

Tipos visibles legacy de `events.py`: SAVE_UPLOADED, PURCHASE_COMPLETED,
TEAM_LOCKED. No deducir eventos administrativos por la existencia del modulo.

Propuesta futura: hecho de negocio + dedupe/actor/season/visibilidad en
`activity_events` **en la misma transaccion**. Discord solo despues de commit y
reintentable, nunca condicion del commit ni llamada bajo locks. Payload publico
sin notas privadas, auth ids, saves, private teams o datos de sancion privados.
No existe todavia outbox administrativo completo; dedupe de evento no es un recibo
idempotente general. Avisos de pruebas/migracion permanecen desactivados.

## 17. Atomicidad, Reintentos y Concurrencia

### Clasificacion por Operacion

"Single row safe" solo describe una escritura realmente aislada SIN evento u otros
efectos. Si se registra el evento recomendado, pasa a transaccion multi-write.
CAS = precondicion/revision esperada, no reutilizacion ciega de updated_at de toda
la season si cambia por una operacion ajena. Ningun CAS administrativo esta
implementado. Idempotency-Key y CAS resuelven problemas diferentes.

| Operacion futura | Frontera | Idempotency-Key | CAS/precondicion | Motivo |
| --- | --- | --- | --- | --- |
| Crear draft | Multi-write season + event + recibo | Si | No, aun sin agregado | Reintento no debe crear dos seasons; nombre no identifica operacion |
| Renombrar draft | Single-row safe sin evento; multi con event | No necesario con PUT/CAS | Si | Dos sesiones no se pisan; no tocar nombre historico |
| Anadir participante draft | Multi player + stats + membership si se aporta + event | Si | Si, estado/config/roster | Unique evita dos filas, no da recibo ni efectos completos |
| Retirar inclusion draft sin referencias | Multi roster/membership/stats + event | Si | Si | No DELETE ciego ni perdida de dependencias; D2 |
| Version config | Multi version + vinculacion de setup futuro autorizado + event | Si | Si, config base/jornadas | Numero consecutivo y vigencia sin lost update |
| Asignacion inicial divisiones | Multi divisions/memberships + event | Si | Si, roster/config | Evitar roster parcial/capacidad incorrecta |
| Preparar/generar jornada | Multi matchday + parejas + pointer si primera + event | Si | Si, config/roster/pointer | Evitar duplicados y config distinta bajo reintento |
| Activar temporada | Multi estado + setup/pointer verificados + event | Si | Si, draft/revision | One-active + consistencia, no solo PATCH status |
| Abrir jornada | Multi status + validaciones/dependencias + event | Si | Si, scheduled/version | Aunque status es una fila, carrera con locks/config/results |
| Cancelar/reset edicion | Multi status/partidos/pointer/event segun D5 | Si | Si | No perder locks/recompensas ni inutilizar compras |
| Guardar resultados abiertos | Multi batch matches + event | Si para batch | Si, revision batch/resultados | No aceptar edicion sobre cierre concurrente |
| Cerrar y avanzar | Multi snapshot/ledger/premios/movimientos/memberships/day/pointer/event | Si | Si | Un solo cierre economico; no split REST |
| Corregir cierre | Multi revision/ajustes ledger/efectos dependientes/event | Si | Si, revision de snapshot | No replay de recompensas ni reescritura silenciosa |
| Retire/abandon/disqualify | Multi player/rangos/flags/ciclo/dependencias/event | Si | Si, status/roster/jornada | Cambio de elegibilidad frente a compras/robo |
| Finish | Multi estado + verificacion final + event; liquidacion si aprobada | Si | Si | Excluir nueva competicion/compras concurrentes |
| Archive/Hall | Multi estado + snapshot opcional + Hall + event | Si | Si, fuente final | No archivos diferentes con mismo intento |
| Discard logico | Multi estado + dependencias autorizadas + event | Si | Si, estado/dependencias | Preservar ledger/identidad/locks; no reutilizar wipe legacy |
| Mantenimiento de flags Pokemon | Multi flags/evidencia/event si se llega a aprobar | Si | Si, revision identidad/efecto | Reset legacy no es permission para borrar efectos de 023-025; sin endpoint ahora |
| Ajustar insignias/progreso | Solo badge row seria single-row safe; con ledger/event multi | Segun fuente futura; no endpoint propuesto | Si/source revision | No sustituir pipeline de saves por permiso generico |
| Ajuste manual de monedas | Multi entrada compensatoria + event | Si si se aprueba | Si/version wallet cuando proceda | No existe editor libre legacy ni se propone ahora |

Regla de replay propuesta: misma clave/actor/operacion/body devuelve recibo estable,
distinto body -> conflicto. Scope, retencion y persistencia del recibo requieren
diseno tecnico futuro: 001-025 no contienen tabla universal de comandos admin.
Checks de identidad/permiso preceden al replay; orden respecto a lifecycle/estado
debe quedar explicitado como en compras anteriores, no permitir replay a deshabilitado.

### Jerarquia Existente Que No Se Puede Romper

025: trainer habilitado FOR SHARE -> **season FOR NO KEY UPDATE** -> todos los
season_players ordenados por **id UUID de fila** FOR UPDATE -> purchase/target/
identity/cycle/flags/gift/event segun efecto. No ordenar por display_name.
Los cambios de membership/status deben adquirir season primero y el conjunto
afectado en ese mismo orden. Insertar participante tambien debe serializar por
season: un nuevo row no estaba en el conjunto bloqueado antes de la insercion.

019/021/022 toman season FOR SHARE antes de rows dependientes. 019 toma day antes
de player; un futuro escritor season NO KEY UPDATE obtiene exclusividad respecto
a esas operaciones ANTES de tomar players/day, evitando invertir esos locks.
023 bloquea player para identidad; sus FKs pueden adquirir KEY SHARE de season.
No sustituir por season FOR UPDATE indiscriminadamente: el modo NO KEY UPDATE
evita conflicto innecesario con esos FK locks. Especificar modos en implementacion.

| Carrera | Riesgo | Frontera recomendada, no implementada |
| --- | --- | --- |
| Activar dos seasons distintas | Dos row locks diferentes no bastan | Unique one-active como ultima defensa; error 409 limpio, ningun auto-finish; evaluar serializacion global solo si hace falta |
| Alta duplicada | Doble stats/membership/event aunque player unique | Season lock + unique season/trainer + recibo; rollback total |
| Status/alta/remocion frente a robo | Victima/ciclo calculados con activos inconsistentes | Season -> ordered players; decidir ciclo tras cambio sin borrar historial |
| Division/config frente a close | Premios/config/membership de versiones distintas | Mismo season lock + CAS + snapshot config exacta |
| Dos generadores de calendario | Parejas inversas/duplicadas o config distinta | Season lock + unica jornada + orden canonico parejas + dedupe |
| Finish frente a compra | Compra nueva se confirma tras freeze | Season write lock incompatible con SHARE; revalidar lifecycle bajo lock |
| Finish frente a Team Lock | Lock creado sobre contexto final | Mismo season gate; 019 revalida status/day; no cambiar elegibilidad scheduled/open |
| Close frente a guardar resultado/lock | Snapshot incompleto o lock posterior | Season y day bajo transaccion; validar antes de snapshot/commit |
| Archive frente a correccion | Hall/export de revision distinta | Season gate, revision fuente y snapshot publico congelado |
| Dos versiones config | Numero/ventana duplicados y futuro ambiguo | Season lock + unique numero/vigencia + CAS; D3 para sustituir futuro |
| Direct admin REST frente a cualquier RPC | Evita locks/validaciones del backend | Revocar escrituras directas al entregar la subfase, no solo confiar en interfaz |

No se propone una RPC gigante para todo. Activar, publicar config, preparar
jornada, cerrar y archivar son transacciones de negocio diferentes.

## 18. API Minima Propuesta, NO Implementada

Prefijo propuesto **`/v1/admin`**. Todos los endpoints de la tabla requieren
**A = JWT verificado + trainer globally_enabled + is_admin**; ninguno acepta
actor/is_admin desde cliente. Errores comunes: 401 sesion invalida, 403 no admin
o disabled, 404 recurso ausente, 409 estado/revision/idempotency conflict, 422 body.
Los codigos de negocio son propuestas, no errores existentes en un nuevo router.

Respuesta mutacion **R**: `{operation_id, resource_id, state_or_revision,
replayed, event_id}` mas campos indicados. K=Idempotency-Key; V=precondicion CAS
tipada del agregado indicado. Tablas event/recibo se incluyen como efectos
propuestos; storage de recibos aun no decidido, no existe migration nueva.

Correspondencia de abreviaturas en las tablas: season -> `seasons`, player/roster
-> `season_players`, stats -> `season_player_stats`, config ->
`season_config_versions`, memberships -> `division_memberships`, day -> `matchdays`,
snapshot -> `matchday_snapshots`, ledger -> `coin_transactions`, gift -> `purchases`,
movement -> `matchday_movements`, event -> `activity_events`, ciclo ->
`robbery_cycles`, archive -> `season_archive_snapshots`, Hall -> `hall_of_fame_entries`.
`divisions` y `matches` conservan sus nombres. Flags de entrenador -> `trainer_flags`;
no cambiar flags de entidad 023-025 como efecto generico de baja de participante.

### Core de Preparacion (8G.1)

| Metodo / path | Auth | Body permitido | Respuesta | Retry | Transaccion / tablas | Errores de negocio principales |
| --- | --- | --- | --- | --- | --- | --- |
| GET `/seasons/{s}/setup` | A | Ninguno | Season + config vigente/futuras + roster/divisiones + readiness + revision | Sin K/V | Lectura consistente seasons/config/players/stats/divisions/memberships/days; nada privado innecesario | SEASON_NOT_FOUND |
| POST `/seasons` | A | name | R + season_id, status=draft | K | Crear draft/event/recibo; sin altas/default economia ocultas | IDEMPOTENCY_CONFLICT |
| PUT `/seasons/{s}/name` | A | name, expected_revision | R + name | V, sin K obligatorio | Draft season + event; no renombrar archivos | SEASON_NOT_DRAFT, STALE_REVISION |
| POST `/seasons/{s}/participants` | A | trainer_id, seed_order opcional, expected_roster_revision | R + season_player_id, stats iniciales | K+V | Alta draft + stats + event; membership separado hasta asignacion inicial | TRAINER_UNAVAILABLE, PARTICIPANT_EXISTS, SEASON_NOT_DRAFT |
| POST `/seasons/{s}/participants/{p}/remove-from-draft` | A | expected_roster_revision, reason | R + roster revision | K+V | Solo inclusion aun sin competicion/saves/compras; relaciones draft dependientes + event, D2 | PARTICIPANT_REFERENCED, SEASON_NOT_DRAFT |
| POST `/seasons/{s}/config-versions` | A | name, effective_from_matchday, total_matchdays, division_sizes A/B, movement_count, scoring, coin_rewards, rules, expected_config_revision, expected_roster_revision | R + version_id/number/effective round | K+V | Config validada + referencia a roster aprobado + event; no PATCH versiones usadas | CONFIG_WINDOW_CLOSED, EFFECTIVE_ROUND_EXISTS, INVALID_ROSTER, INVALID_REWARDS |
| POST `/seasons/{s}/config-versions/{v}/replace-unused` (solo si D3-B aprobada) | A | config completa validada, reason, expected_config_revision | R + config/revision y evidencia anterior | K+V | Version aun no usada + evidencia/event; revalidar ausencia de referencias bajo lock | CONFIG_ALREADY_USED, CONFIG_WINDOW_CLOSED, STALE_REVISION |
| PUT `/seasons/{s}/initial-divisions` | A | assignments A/B por season_player_id, expected_roster_revision, config_version_id | R + divisions/membership revision | K+V | Solo setup sin historia; divisions/memberships + event | INITIAL_SETUP_LOCKED, DUPLICATE_PLAYER, DIVISION_CAPACITY_MISMATCH |
| POST `/seasons/{s}/matchdays/prepare-current` | A | expected_setup_revision | R + day_id/number/config_id, match_count, current_matchday_id | K+V | Servidor elige numero autorizado; primera jornada/config/parejas/pointer/event. No body con winner/current pointer arbitrario | SETUP_INCOMPLETE, MATCHDAY_ALREADY_PREPARED, CONFIG_NOT_EFFECTIVE |
| POST `/seasons/{s}/activate` | A | expected_setup_revision | R + active season/pointer/started_at | K+V | Verifica setup y one-active; estado/pointer coherentes + event; D1 | ACTIVE_SEASON_EXISTS, SETUP_INCOMPLETE, SEASON_NOT_DRAFT |

Esta lista no exige un wizard visual. Prepara objetos explicitos y un informe de
readiness. `prepare-current` en 8G.1 solo inicializa primera jornada: preparar la
siguiente con movimientos pertenece a 8H. Puede componerse internamente con
activation si D1 lo aprueba; no crear dos writers distintos del pointer.
`remove-from-draft` es propuesta condicionada a D2; no usar si hay cualquier
referencia de saves/identidad/economia/competicion. No define borrado de trainer global.

### Operaciones Posteriores, No Incluidas en 8G.1

| Metodo / path | Auth | Body permitido | Respuesta | Retry | Transaccion / tablas | Errores principales / decision |
| --- | --- | --- | --- | --- | --- | --- |
| POST `/seasons/{s}/matchdays/{d}/open` | A | expected_revision | R + opened_at/status | K+V | day/config/roster verificados + event; partners deben estar preparados | MATCHDAY_NOT_SCHEDULED, SEASON_NOT_ACTIVE |
| POST `/seasons/{s}/matchdays/{d}/cancel-editing` | A | expected_revision, reason | R + estado/pointer | K+V | day/matches/pointer + event segun D5; nunca borrar locks por accidente | MATCHDAY_CLOSED, DEPENDENT_DATA_EXISTS |
| PUT `/seasons/{s}/matchdays/{d}/results` | A | lista match_id/winner_season_player_id o null, expected_results_revision | R + revision/resultados | K+V batch | Ganadores de open + event; no monedas | MATCHDAY_NOT_OPEN, WINNER_NOT_IN_MATCH, STALE_REVISION |
| POST `/seasons/{s}/matchdays/{d}/close` | A | expected_results_revision | R + snapshot/revision, awards, movements, next_pointer | K+V | 8H: matches/day/config/snapshot/ledger/gift/movements/memberships/pointer/event; promos como responsabilidad explicita | RESULTS_INCOMPLETE, ALREADY_CLOSED, CONFIG_MISMATCH |
| POST `/seasons/{s}/matchdays/{d}/correct` | A | winners corregidos, reason, expected_snapshot_revision | R + nueva revision/compensaciones | K+V | 8H: snapshot/ledger/awards/membership/event; D4, no UPDATE libre | CORRECTION_WINDOW_CLOSED, DOWNSTREAM_COMPETITION_EXISTS |
| POST `/seasons/{s}/participants/{p}/retire` | A | reason, expected_roster_revision | R + status=retired/fecha/efectivo | K+V | 8I: player/membership/flags/robbery context/event | ROUND_OPEN, ALREADY_INACTIVE; D2 |
| POST `/seasons/{s}/participants/{p}/abandon` | A | reason, expected_roster_revision | R + status=abandoned/fecha/efectivo | K+V | Misma frontera, semantica abandono conservada | ROUND_OPEN, ALREADY_INACTIVE; D2 |
| POST `/seasons/{s}/participants/{p}/disqualify` | A | reason, expected_roster_revision | R + status=disqualified/fecha/efectivo | K+V | Misma frontera; sin quitar puntos historicos implicitamente | ROUND_OPEN, ALREADY_INACTIVE; D2 |
| POST `/seasons/{s}/finish` | A | expected_revision, reason si cierre anticipado aprobado | R + finished_at | K+V | 8J: estado+verificacion cierre/economia final+event, D6 | ROUND_OPEN, SEASON_NOT_COMPLETE, PENDING_FINALIZATION |
| POST `/seasons/{s}/archive` | A | expected_revision, label opcional | R + archived_at, archive/Hall ids | K+V | 8J: estado/Hall/snapshot export opcional/event | SEASON_NOT_FINISHED, HISTORICAL_SOURCE_INCOMPLETE |
| POST `/seasons/{s}/discard` | A | reason, confirmation, expected_revision | R + discarded_at | K+V | 8J: descarte logico preservando relaciones, D7 | DISCARD_NOT_ALLOWED, DEPENDENT_COMPETITION_EXISTS |

No endpoints por ahora para reactivar/reabrir, PATCH arbitrario de season/player,
editar raw stats/ledger, full-calendar, editar pareja manual, void/forfeit individual,
reset destructivo, regenerar archive, crear Hall a mano ni mantenimiento de flags
de identidad. El nuevo frontend no necesita un CRUD de cada tabla para reemplazar
estas operaciones de producto. Reads publicos generales quedan fuera de este audit.

## 19. Subfases y Dependencias

| Subfase propuesta | Incluye | No incluye / gates |
| --- | --- | --- |
| **8G.1 - Core season setup/admin API** | Admin JWT guard, draft, roster inicial/stats, config versionada, asignacion A/B, preparar primera jornada/pointer, activar; hardening de writes que pasen a backend | Decisiones D1/D2-scope/D3 antes de implementacion; nada de cierre/rewards/finish/archive; tests locales y staging en tarea futura autorizada |
| 8H - Operacion competitiva de jornada | Apertura/cancelacion/resultados/correccion y cierre atomico: snapshot, ledger rewards, ultimo B, movimiento, memberships, promos/avance/pointer | D4/D5/D6 terminal; sin confundir ultima jornada con bonus individual; no calendario de parejas futuras desconocidas |
| 8I - Estado de participantes y mantenimiento controlado | Retire/abandon/disqualify efectivos, dependencias schedule/cup/trial, flags/ciclo; altas tardias SOLO si aprobadas | No reactivacion mecanica, no reset global ni borrar identidad/ledger; respeta locks 025 |
| 8J - Finalizacion historica | Finish/revision/archive/Hall, export optional y descarte logico aprobado | Depende de cierres reproducibles, origen de equipo publico y D6/D7; no limpieza V1 |

8I puede necesitar contrato de cambios efectivos antes de cerrar diseno 8H; las
subfases no autorizan dejar huecos mientras se habilitan escrituras. Si 8G.1 solo
acepta roster DRAFT, el conjunto activo queda fijo hasta que 8I este listo.
Los servicios de progreso individual/bonus, parser boundary, Copa/Juicios completos
y ejecucion fisica Companion siguen fuera. El denominador de progreso incluye
tambien React/Cloudflare, migracion, shadow, staging/performance, cutover, launcher,
automatizacion segura y acabado final.

**Unica siguiente subfase recomendada: Phase 8G.1 - Core season setup/admin API**,
despues de resolver las decisiones de producto que afectan a su alcance. Esta
auditoria no es autorizacion para empezarla ni para tocar staging.

## 20. Validacion y Alcance de la Entrega

Validacion ejecutada en esta entrega:

| Comando / comprobacion | Resultado |
| --- | --- |
| `py -m compileall -q .` | PASS, exit 0, sin salida |
| `py -c "from tools.generate_supabase_v2_bootstrap import BOOTSTRAP_SQL, EXPECTED_MIGRATIONS, render_bootstrap; assert BOOTSTRAP_SQL.read_text(encoding='utf-8') == render_bootstrap(); print('PASS bootstrap matches', len(EXPECTED_MIGRATIONS), 'migrations; read-only comparison')"` | PASS: 25 migrations; igualdad en memoria, sin escribir SQL |
| `git diff --check` y `git diff --cached --check` | PASS; aviso Git LF -> CRLF al preparar docs, no error de whitespace |
| Diff y staging explicito | Solo este audit y `docs/project-checkpoint.md`; sin cambios funcionales |
| SHA256 guia protegida | `6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`, igual al inicio |

No se ejecuta el generador en modo escritura ni se abre Streamlit. Commit/push
normal de documentacion; sin amend/force. La guia queda untracked y fuera del commit.

Baseline de **318 tests PASS** es el ultimo verificado en 8F; no se vuelve a ejecutar
la suite completa por un cambio solo documental. Tampoco PostgreSQL, RLS staging,
fixtures, PKHeX o saves. No se afirma un nuevo PASS de 318 tests ni de 8G endpoints.
Los resultados ejecutados y cierre Git se entregan junto al commit de esta auditoria.

## 21. Product Decisions: Approved After This Audit

2026-09-23 Phase 8G.1 instruction supersedes the pending labels below:
**D1=A, D2=A, D3=B** approved for implementation. **D4=A, D5=A, D6=A,
D7=A** approved future direction, NOT implemented by 8G.1. **D8=DEFERRED**.
The original alternatives and audit evidence are retained below as history.
Current implementation contract: [Phase 8G.1](phase8g1-season-admin-api.md).

Estas preguntas no cuestionan contratos terminados. Proponen como cerrar huecos
sin reinterpretar el runtime accidentalmente. No hay respuestas asumidas.

### D1. Activacion y Disponibilidad Competitiva (Bloquea 8G.1)

1. Evidencia: legacy arranca ACTIVE vacia; SQL permite ACTIVE sin pointer; compras
   nuevas fallan con NULL. 019 permite scheduled/open incluso no-current.
2. Hace falta decidir cuando una temporada se anuncia realmente lista y quien la
   administra si el admin no compite; los guards legacy son inconsistentes.
3. Opciones: A) activar solo con config/roster A/B/primera jornada/pointer completos,
   administracion por admin habilitado aunque no participante; B) permitir ACTIVE
   en preparacion y mantener bloqueadas compras hasta completar setup.
4. Recomendacion: **A**, draft para preparacion; ninguna finalizacion automatica
   de otra ACTIVE; no crear shells de todas las jornadas inicialmente.
5. A requiere readiness y activacion atomica; B necesita explicar claramente el
   estado parcialmente operativo y permite locks antes que compras. No permitir
   usar nombre Anto como excepcion a JWT en ninguna opcion.

### D2. Roster Inicial, Altas Tardias y Bajas (Scope 8G.1; Completo en 8I)

1. Evidencia: config permite cambiar players a futuro; baja UI solo entre jornadas;
   no reactivacion. Snapshot conserva pasado, ranking vivo pone inactivos a 0 y
   SQL ledger no borra saldo. Cup/trial no se recalculan automaticamente.
2. V2 necesita roster efectivo por jornada, destino de puntos/saldo y consistencia
   de grupos/ciclo de robo. Quitar de una lista no expresa todo eso.
3. Opciones: A) 8G.1 solo roster draft, removal sin referencias; luego bajas
   permanentes entre jornadas conservando historia/ledger, sin altas tardias hasta
   contrato explicito; B) permitir altas/remociones futuras desde primera entrega,
   definiendo jornada efectiva, capacidad, calendario, saldo inicial y cups.
4. Recomendacion: **A**; status distinto por razon, no eliminar datos economicos;
   decidir presentacion de inactivos (fila historica/puntos ganados frente a 0 live)
   al implementar 8I. Nuevo season_player en nueva season si vuelve a competir.
5. A reduce alcance y evita alterar elegibilidad de 025 sin politica; B aumenta
   schema/orquestacion/pruebas y requiere resolver inmediatamente efectos de ciclo,
   emparejamientos y resultados previos. No reactivar por cambiar globally_enabled.

### D3. Corregir Una Configuracion Futura Aun No Usada (Bloquea 8G.1)

1. Evidencia: legacy deja varias versions con igual effective_round y elige ultima
   por id; SQL unique(season,effective_from_matchday) lo prohibe. locked_at no impone
   inmutabilidad. No hay dedupe de contenido.
2. Hay que poder distinguir corregir un borrador de cambiar reglas ya utilizadas.
3. Opciones: A) append-only; misma vigencia ya publicada se rechaza y se elige otra
   jornada, todo preparado antes de publicar; B) reemplazar una version futura
   mientras no haya referencias competitivas, con revision/CAS/auditoria explicita.
4. Recomendacion: **B solo para configuracion aun no usada**, usada se congela y
   cambios posteriores por nueva version. No interpretar "append-only" como
   permiso para dos filas de igual vigencia en schema actual.
5. A es simple pero corregir error de setup publicado puede exigir rehacer draft;
   B requiere definir que cuenta como uso (jornada/lock/resultado), conservar
   evidencia de edicion y posible ajuste de contrato SQL posterior. Ninguna opcion
   permite reescribir config de un snapshot cerrado.

### D4. Ventana y Compensacion de Correcciones Cerradas (8H)

1. Evidencia: UI corrige jornada inmediatamente anterior, incluso si hay siguiente
   en edicion; recompute cambia snapshot y puede borrar matches siguientes; no
   ajusta comodin antiguo ni compras hechas con saldo anterior.
2. Con ledger real, reemplazar total/snapshot no revierte hechos economicos.
3. Opciones: A) solo corregir antes de que siguiente tenga resultados/efectos
   dependientes, con ajuste ledger/gift explicito; B) permitir correccion tardia
   con cascada auditada a jornadas/awards/movimientos siguientes.
4. Recomendacion: **A** como primera version, rechazar cuando no se pueda compensar
   con seguridad (p. ej. comodin ya usado). No mutar compras/redenciones completadas.
5. A acota ventana y requiere revision/factos compensatorios; B es mucho mayor,
   afecta saldo gastado, equipo/division y comunicaciones ya emitidas. Debe aprobarse
   como operacion excepcional, no un PATCH de winner.

### D5. Significado de Cancelar Jornada (8H)

1. Evidencia: legacy borra matches del tramo pero conserva numero y locks; permite
   reabrirlo. SQL cancelled invalida pointer para compras; es distinto a pendiente.
2. V2 debe evitar borrar historia o dejar una ACTIVE sin jornada utilizable.
3. Opciones: A) cancelar edicion = volver a scheduled del mismo round, conservando
   locks, solo si no hay resultados que preservar; B) cancelled terminal, con
   sustitucion/avance explicito y reglas para compras/locks ya existentes.
4. Recomendacion: **A**, con confirmacion/revision y rechazo ante dependencias,
   no llamar cancelled a lo que sigue siendo ronda pendiente.
5. A mantiene numero/pointer y flujo legacy sin borrado ciego; B requiere politica
   de round reemplazo y numeracion, impacto Store Ban/promos y destino de locks.

### D6. Ultimo Cierre, Finish Anticipado y Periodo de Revision (8H/8J)

1. Evidencia: final close deja season ACTIVE/tramo=max+1; finish admite >=1 cierre,
   no todos. Hall live puede aparecer antes de archive; 025 canjea fuera de ACTIVE.
2. Hay que decidir hasta cuando se compra y cuando se fija Hall definitivo.
3. Opciones: A) ultimo close conserva pointer a ultima closed, luego finish manual
   tras revision; finish normal exige temporada completa y early finish separado
   con motivo; B) ultimo close marca FINISHED atomicamente, early finish igual
   requiere contrato explicito. En ambas Hall definitivo al archivar.
4. Recomendacion: **A** para mantener los pasos legacy, documentando que nuevas
   compras siguen posibles mientras ACTIVE. No conceder 12 monedas individuales
   desde finish. No bloquear canjes 025 sin otra aprobacion expresa.
5. A mantiene ventana de revision/compras y necesita accion admin; B bloquea nuevas
   compras/Team Lock inmediatamente, modifica flujo y acopla finish a 8H.
   Una politica distinta de canjes/pending physical effects es cambio de producto,
   no consecuencia implicita de archive.

### D7. Descarte y Visibilidad del Historico (8J)

1. Evidencia: legacy limpia datos activos sin snapshot; V2 conserva relaciones y
   public_seasons oculta discarded, pero vistas hijas pueden seguir mostrando filas.
2. Es necesario distinguir abandonar una preparacion, anular competicion y borrar
   datos. No son la misma orden.
3. Opciones: A) discard logico de draft sin actividad; season activa con historia
   requiere procedimiento de cierre excepcional; B) permitir discard logico tambien
   de activa, conservando ledger/locks/efectos y definiendo visibilidad publica.
4. Recomendacion: **A inicialmente**; nunca reset masivo como equivalente API.
   Admin conserva consulta; archive normal es camino historico preferido.
5. A evita ambiguedad de premios/canjes en temporada anulada; B necesita decidir
   refunds, resultados, Hall, ventanas Store Ban y exposicion de vistas hijas.
   B no puede prometer cancelacion de canjes ya aprobados por 025 automaticamente.

### D8. Premio Individual y Progreso al Cambiar de Temporada (Fuera de 8G.1)

1. Evidencia: claim "Liga Finalizada" es propio con 8 medallas, 12 monedas;
   clear_active_season_state no borra su key ni badges/revividos individuales.
2. Relacionar esos hechos con una season nueva requiere saber si se conserva la
   misma partida o empieza reto nuevo; copiar saldo global es incorrecto.
3. Opciones: A) progreso/bonus por temporada y save autorizado; nuevo reto empieza
   sin claim heredado, cada credito ledger deduplicado; B) bonus unico por partida
   persistente entre temporadas, con identidad de partida y regla de transferencia.
4. Recomendacion: **A para retos nuevos**, pero confirmar uso real antes de migrar
   historicos. No conceder ni resetear nada como efecto de este audit.
5. A requiere fuente autoritativa saves y dedupe season/player; B requiere identidad
   y politica de continuidad entre seasons que aun no existen en el writer.
