# Module Inventory

Clasificacion inicial tras auditoria. Esta lista debe actualizarse cuando se
extraiga dominio o repositories.

## Root

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `main.py` | STREAMLIT | Configuracion, shell, login, sidebar, topbar y router. |
| `utils.py` | MIXED | Roster, secciones, session_state, saves locales y helpers. |
| `storage.py` | STORAGE/LEGACY | Fachada de Supabase/SQLite/settings/saves/wipe; `save_upload()` emite ActivityEvent cuando el save queda registrado. |
| `conex_pkhex.py` | MIXED | Bridge/parser PKHeX, cache y normalizacion a UI. |
| `dexdata.py` | MIXED | Datos Pokemon, cache local y traducciones. |
| `saves.py` | STREAMLIT | UI de subida, save actual, historial y descarga; el wipe global se movio a `Temporada/Admin` en 2.3. |
| `tienda2.py` | LEGACY WRAPPER | Wrapper a `app.tienda.ui`. |
| `liga_tabla.py` | LEGACY WRAPPER | Wrapper de liga/tabla. |
| `entrenadores.py` | LEGACY WRAPPER | Wrapper a entrenadores. |

## app/season

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `config.py` | MIXED | SeasonVersion funcional: versionado por jornada, reglas, guard admin-only y bloqueo de cambios sobre jornadas cerradas/abiertas; aun lee/escribe `settings`. |
| `archive.py` | MIXED/STORAGE | Fase 2.4: lifecycle (`draft`, `active`, `finished`, `archived`, `discarded`), SeasonArchive inmutable, Hall snapshot-safe y preparacion limpia de temporada nueva. |
| `validation.py` | PURE | Validaciones casi portables a dominio; Streamlit 2.0 valida A/B oficialmente y rechaza N divisiones. |

## app/admin

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `actions.py` | MIXED/ADMIN | Acciones peligrosas protegidas Anto-only; `discard_active_season()` exige decision y confirmacion textual y descarta la temporada activa sin destruir archivos/Hall. |

## app/activity

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `events.py` | MIXED/STORAGE | Fase 2.5: ActivityEvent legacy en `settings.activity_events_v1`, dedupe, visibilidad y emisores para save, compra y team lock. |

## app/domain

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `common.py` | DOMAIN CONTRACT | IDs, enums comunes, timestamps conceptuales y serializacion JSON-safe. |
| `trainers.py` | DOMAIN CONTRACT | `Trainer`, `TrainerStatus` y `TrainerFlags`; identidad separada de participacion. |
| `pokemon.py` | DOMAIN CONTRACT | `PublicPokemon`, `PrivatePokemon`, movimientos, spreads y flags Pokemon. |
| `seasons.py` | DOMAIN CONTRACT | `Season`, lifecycle, `SeasonVersion`, rules, metadata, `Division` y `SeasonPlayer`. |
| `league.py` | DOMAIN CONTRACT | `Matchday`, `Match`, `LeagueStanding`, `PenaltySummary` y `MatchdaySnapshot`. |
| `saves.py` | DOMAIN CONTRACT | `SaveRecord`, `ParsedSave`, slots de party/caja, cajas e inventario. |
| `shop.py` | DOMAIN CONTRACT | `ShopItem`, `ShopPromotion`, `Purchase` y `Redemption`. |
| `team_locks.py` | DOMAIN CONTRACT | `TeamLock` con equipo publico congelado y referencia de save. |
| `activity.py` | DOMAIN CONTRACT | `ActivityEvent` y tipos visibles actuales. |
| `hall_of_fame.py` | DOMAIN CONTRACT | `HallOfFameEntry` con equipo publico congelado. |
| `cup.py` | DOMAIN CONTRACT | Contrato minimo de Copa y matches. |
| `trials.py` | DOMAIN CONTRACT | `TrialCase`, votos y `Penalty` como value object. |
| `archives.py` | DOMAIN CONTRACT | `SeasonArchive` congelado. |
| `legacy.py` | DOMAIN ADAPTER | Adaptadores pequenos dict legacy -> contratos, sin imports de infraestructura. |

### app/domain/services

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `season.py` | DOMAIN SERVICE | Resolucion de version, ventana de aplicacion, validacion estructural y diff de versiones. |
| `league.py` | DOMAIN SERVICE | Pares, match maps, records, H2H, ranking, movimientos A/B, award intent y puntos con penalizaciones. |
| `rewards.py` | DOMAIN SERVICE | Puntos/monedas por posicion y construccion de `LeagueStanding`. |
| `shop.py` | DOMAIN SERVICE | Candidatos, precios, mega eligibility, rotacion, estado de promocion y decision pura de compra. |
| `trainers.py` | DOMAIN SERVICE | Semantica de status, labels, transiciones, flag robado y reset de ciclo. |
| `team_locks.py` | DOMAIN SERVICE | Validacion y construccion de `TeamLock`. |
| `snapshots.py` | DOMAIN SERVICE | Construccion contractual de `MatchdaySnapshot`. |
| `activity.py` | DOMAIN SERVICE | Construccion, dedupe y visibilidad de `ActivityEvent`. |
| `hall_of_fame.py` | DOMAIN SERVICE | Entrada de Hall desde datos congelados. |
| `archives.py` | DOMAIN SERVICE | Construccion de `SeasonArchive` desde inputs explicitos. |
| `trials.py` | DOMAIN SERVICE | Mayoria, recuento, veredicto y transiciones de caso. |

## app/liga

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `ranking.py` | MIXED WRAPPER | Sigue cerrando jornadas via Streamlit/storage, pero pares, ranking, H2H y total con penalizaciones delegan a dominio puro. |
| `state.py` | STREAMLIT/STORAGE | Serializa `st.session_state` a `settings.league_state`. |
| `rewards.py` | PURE-ish WRAPPER | Delegacion simple a season config; dominio puro vive en `app/domain/services/rewards.py`. |
| `divisions.py` | PURE-ish WRAPPER | Lee movement_count desde config legacy y delega el calculo A/B a dominio. |
| `ui.py` | STREAMLIT | Vista de Liga y consola oficial; los controles de jornada/divisiones/reset solo renderizan con `admin_mode=True` desde `Temporada/Admin`. |
| `matchup.py` | STREAMLIT/MIXED | Team Preview con UI, snapshots y detalle de ataques. |

## app/copa

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `styles.py` | STREAMLIT/CSS | Shell visual de Copa suiza/eliminatoria; pulido 1E como match center, pendiente extraer componentes visuales. |
| `swiss.py` | STREAMLIT/MIXED | Gestion de rondas, clasificacion, equipos y Top Cut. |
| `elim.py` | STREAMLIT/MIXED | Eliminatoria Bo3 con bracket editable. |
| `doubles.py` | STREAMLIT/MIXED | Copa Dobles mantiene estado en settings; CSS local pulido 1E, pendiente converger con `styles.py`. |
| `logos.py` | ASSET HELPER | Resolucion local de logos de equipos. |

## app/tienda

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `discounts.py` | MIXED WRAPPER | Seleccion/precio/estado delegan a dominio; scheduling, persistencia y avisos siguen legacy. |
| `catalog_data.py` | PURE-ish | Catalogo estatico con assets. |
| `catalog_render.py` | STREAMLIT/HTML | Render de cards; el CTA usa `st.button` fuera del HTML de la card y se integra visualmente con CSS hasta extraer `ShopItemCard`. |
| `sections.py` | STREAMLIT | Vista tienda y flujo de compra; confirmacion y compra siguen acopladas a `st.session_state`; el reset de flags queda como helper legacy no montado en la pagina normal. |
| `redeem.py` | MIXED | Canje de objetos, flags, saves y UI. |
| `money.py` | MIXED | Calculo monedas con snapshots, medallas y compras. |
| `styles.py` | STREAMLIT/CSS | Estilos tienda. |

## app/entrenadores

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `page.py` | STREAMLIT | Pantalla principal grande; concentra CSS local de Entrenadores/PC/Inspector hasta extraer design system. |
| `boxes.py` | STREAMLIT/MIXED | PC/Cajas, seleccion y mapping de slots; el orden real del save esta acoplado al render. |
| `snapshot.py` | MIXED/STORAGE | Snapshot derivado de save, guardado en settings. |
| `trainer_flags.py` | MIXED WRAPPER | Lee/escribe flags y sync historico, pero status, labels, mutaciones y ciclo robado delegan a dominio puro. |
| `cache.py` | MIXED | Cache del parser PKHeX. |
| `detail_render.py` | STREAMLIT/HTML | Inspector visual; reutiliza resolver de iconos de inventario temporalmente. |
| `summary.py` | STREAMLIT/MIXED | Resumen, monedas, puntos, medallas. |
| `inventory.py` | STREAMLIT/MIXED | Inventario y canjes. |

## app/juicios

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `ui.py` | STREAMLIT/MIXED | Bandeja, filtros, formularios y acciones de expedientes; CSS local 1E con cards de expediente. |
| `render.py` | STREAMLIT/HTML | Detalle de expediente y castigos; presentacion refinada 1E sin tocar reglas de voto. |
| `repo.py` | STORAGE/MIXED | Persistencia y permisos de juicios. |
| `forms.py` | STREAMLIT | Formularios de alta, edicion y resolucion. |
| `penalties.py` | MIXED | Lectura de sanciones activas y efectos en tienda/monedas. |

## app/interfaz

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `theme.py` | STREAMLIT/CSS | Base visual y aplica capas posteriores. |
| `champions_skin.py` | STREAMLIT/CSS | Capa principal estilo Champions. |
| `premium_phase2.py` | STREAMLIT/CSS | Capa visual 2.0 acumulada. |
| `final_polish.py` | STREAMLIT/CSS | Parches visuales finales; incluye capa 1E para pantallas secundarias. |
| `auth.py` | STREAMLIT/STORAGE | Login y PIN via settings. |
| `sidebar.py` | STREAMLIT/STORAGE | Navegacion, PIN, perfil mini. |
| `home.py` | STREAMLIT/MIXED | Menu principal y resumen. |
| `notifications.py` | MIXED | NotificationView: muestra maximo 5 ActivityEvents recientes; fallback legacy desde saves, compras y locks si no existen eventos nuevos. |
| `normativa.py` | STREAMLIT/CONTENT | Manual oficial `rulebook-*` V2: portada documental, indice compacto, articulos alineados, tablas de caps/recompensas y fichas de comodines sin `st.tabs`. |
| `temporada.py` | STREAMLIT/MIXED | Back office Admin 2.4: estado, ciclo de temporada, configuracion, gestion de entrenadores, consola Liga, historial real y zona de descarte. |
| `hall_of_fame.py` | MIXED | Logica y UI de historico; auto-sync de campeones desde fuentes vivas y archivos inmutables con equipos congelados. |

### Auditoria visual 1F

| Zona | Estado | Nota |
| --- | --- | --- |
| Cascada global | DEUDA | `theme.py`, `champions_skin.py`, `premium_phase2.py` y `final_polish.py` siguen conviviendo. La deuda principal no es falta de clases, sino selectores antiguos con `.main` + `!important` que pueden ganar a parches finales mas nuevos. |
| Normativa | CORREGIDO | Tras eliminar el legacy, la V2 corrige la composicion plana: el markup `rulebook-*` separa labels/valores, usa chapter index compacto, ArticleRow, DataTable, matriz de recompensas y ToolCards para comodines. |
| Team Preview | CORREGIDO | Los overrides finales de board, cartas, ataques, sprites y detalle de movimiento pasan a `.main .battle-*` / `.main .matchup-*` para no caer en el estilo Champions antiguo claro/morado. |
| Tienda | CORREGIDO | El pulido final de cards, precios, rebajas y cabecera se refuerza con `.main` para ganar a `app/tienda/styles.py` sin tocar logica de compra ni promociones. |
| Entrenadores / PC | CORREGIDO | Equipo actual, chips y tiles de PC quedan protegidos por selectores finales con `.main`; queda pendiente extraer `TrainerCard` y `BoxTile` al futuro sistema de componentes. |
| Liga / Hall / Saves | CORREGIDO | Superficies, tablas, badges y estados vacios quedan bajo selectores finales con `.main`. |
| Pendiente React/Cloudflare | DIFERIDO | Retirar las capas CSS acumuladas y mover estos patrones a componentes/tokens reales antes de optimizar render y routing. |

## app/storage_*

| Modulo | Tipo | Nota |
| --- | --- | --- |
| `storage_shop.py` | STORAGE | Compras, promociones, locks, inventario, redenciones; desde 2.5 emite ActivityEvents tras compras y team locks exitosos. |
| `storage_flags.py` | STORAGE | Flags de Pokemon y limpieza. |
| `storage_cache.py` | STORAGE | Cache simple en memoria. |

## Tests Actuales

| Test | Cobertura |
| --- | --- |
| `test_activity_events.py` | ActivityEvent legacy, dedupe, visibilidad y hooks de save/compra/team lock. |
| `test_domain_contracts.py` | Contratos de dominio, JSON-safe, privacidad, adaptadores legacy y regla arquitectonica recursiva. |
| `test_domain_services.py` | Servicios puros de Fase 4: season, ranking, rewards, shop, flags, team locks, snapshots, activity, Hall/archive y juicios. |
| `test_shop_promotions.py` | Rebajas, exclusiones y rotacion. |
| `test_season_config.py` | Versionado, permisos, bloqueo historico y roster explicito. |
| `test_season_validation.py` | Validacion de temporada, A/B oficial, jugadores y reglas. |
| `test_notifications.py` | Actividad reciente y limite visible. |
| `test_liga_rewards.py` | Recompensas, jornadas y movimientos desde config. |
| `test_liga_snapshots.py` | Snapshots oficiales, permisos, reglas y penalizacion de puntos snapshot-first. |
| `test_trainer_status.py` | Estados de entrenador, flag robado separado, descarte de temporada y reubicacion de controles peligrosos. |
| `test_hall_of_fame.py` | Coercion/merge de historico. |
| `test_season_archive.py` | Lifecycle, archivado idempotente, Hall congelado, descarte y nueva temporada preservando archivos. |
| `test_saves_support.py` | HTML de saves. |
