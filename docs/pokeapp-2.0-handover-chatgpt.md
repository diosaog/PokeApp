# PokeApp 2.0 - Macro Contexto Para Nuevo ChatGPT

Este documento resume el estado real de PokeApp para continuar el trabajo en otro
chat sin perder contexto. Debe tratarse como briefing tecnico/producto, no como
orden para implementar todo de golpe.

## 1. Que es PokeApp

PokeApp es una plataforma privada para gestionar una liga/reto Pokemon tipo
Nuzlocke/ChampionsLocke. La app permite:

- login por entrenador con PIN;
- subir saves `.sav`;
- leer equipo, cajas/PC, medallas, objetos y detalles de Pokemon mediante un
  bridge basado en PKHeX;
- mostrar perfiles de entrenadores;
- fijar equipo para Team Preview;
- gestionar Liga A/B con jornadas, resultados, clasificacion, puntos, monedas,
  ascensos/descensos y sanciones;
- gestionar Tienda, compras, redenciones, rebajas, robos, revivir Pokemon y
  flags de Pokemon;
- gestionar Copa y Juicios;
- generar Hall of Fame;
- emitir notificaciones internas y avisos por Discord.

La app actual sigue siendo Streamlit. El objetivo de PokeApp 2.0 no es tirar lo
que existe, sino separar el producto que ya funciona de la deuda de Streamlit,
settings JSON y Supabase V1.

## 2. Estado tecnico actual

Entrada principal:

- `main.py`

Capas principales:

- `app/interfaz/`: shell Streamlit, login, sidebar, home, normativa, temporada,
  notificaciones, topbar y capas visuales.
- `app/entrenadores/`: pagina de entrenador, PC/cajas, inspector, inventario,
  sprites, snapshots y flags.
- `app/liga/`: ranking, jornadas, snapshots, recompensas, tabla y Team Preview.
- `app/tienda/`: catalogo, promociones, compras, redenciones y estilos.
- `app/copa/`: swiss, eliminatoria y dobles.
- `app/juicios/`: expedientes, votos, sanciones y UI.
- `app/activity/`: eventos de actividad legacy.
- `app/domain/`: contratos de dominio dependency-free.
- `app/domain/services/`: reglas puras.
- `app/repositories/`: protocolos, mappers, repos legacy e in-memory.
- `app/application/`: use cases pequenos.
- `supabase/v2/`: schema nuevo SQL-first.
- `tools/`: validadores de schema/RLS y generador de bootstrap.

Persistencia actual de runtime:

- Supabase V1 cuando esta configurado.
- SQLite/local como fallback/dev.
- `settings` guarda gran parte del estado oficial en JSON.
- Saves: metadata en tabla `saves`, bytes en Supabase Storage o archivos locales.
- Streamlit `session_state` es espejo runtime, no fuente historica final.

## 3. Problema original de arquitectura

La app funcionaba, pero tenia estos problemas:

- muchas reglas vivian mezcladas con UI Streamlit;
- mucha informacion oficial vivia en blobs `settings`;
- el cliente Streamlit hacia operaciones criticas directamente;
- no habia RLS final para privacidad real;
- los cambios de configuracion podian reinterpretar historico si no habia
  snapshots;
- el Hall podia depender de saves vivos y moverse despues de ganar;
- la app recargaba mucho y Streamlit hacia que la experiencia fuera pesada;
- las paginas acumulaban CSS de varias fases visuales;
- Supabase V1 no era una buena base para React/Cloudflare.

La solucion acordada fue hacer una migracion por fases, conservadora y con tests:
primero cerrar producto, despues dominio, repositorios, Supabase V2, seguridad,
API, parser boundary, React/Cloudflare, migracion de datos, shadow mode y cutover.

## 4. Estado visual/producto 2.0

Se hizo una pasada visual fuerte inspirada en Pokemon Champions:

- cajas, cards, Team Preview, Entrenadores, Tienda, Liga, Saves, Normativa y Hall
  fueron llevados hacia un estilo oscuro, competitivo y con paneles tipo
  Champions;
- se redujeron textos innecesarios/sobreexplicaciones;
- se revisaron superficies antiguas, menus, botones, notificaciones, PIN,
  entrenadores y team preview;
- se sustituyeron tipos Pokemon por imagenes/iconos reales cuando aplicaba;
- PC/Cajas y Equipo actual recibieron tiles visuales mas parecidos al juego;
- Normativa paso a formato de manual tecnico/rulebook con indices, articulos y
  tablas, aunque tuvo varias iteraciones porque el primer rework era demasiado
  plano.

Decision importante: no seguir puliendo Streamlit salvo bug real. El visual de
Streamlit es referencia de producto, no el futuro sistema de componentes.

## 5. Fases cerradas

Fase 0 - Base verde:

- tests/compile/diff check iniciales;
- inventario de modulos y documentacion base.

Fase 1 - Cierre visual Streamlit:

- referencia visual 2.0 practicamente cerrada;
- objetivo: que lo antiguo no pareciera legacy antes de congelar producto.

Fase 2 - Cierre funcional:

- `season_config_v2` como configuracion funcional de temporada;
- Liga A/B oficial en Streamlit 2.0;
- snapshots inmutables por jornada cerrada;
- estados de entrenador: active, retired, abandoned, disqualified;
- flags de entrenador como `robbed` separados del status;
- back office `Temporada/Admin`;
- lifecycle de temporada: active, finished, archived, discarded;
- SeasonArchive legacy;
- Hall of Fame congelado desde archives;
- ActivityEvents legacy para saves, compras y team locks;
- feature freeze funcional declarado.

Fase 3 - Contratos de dominio:

- dataclasses/enums en `app/domain/`;
- contratos para Pokemon, Trainer, Season, Division, Matchday, Match,
  Standing, Shop, Save, TeamLock, ActivityEvent, Hall, Cup, Trial, Archive;
- sin tocar runtime.

Fase 4 - Dominio puro:

- reglas puras en `app/domain/services/`;
- ranking, recompensas, movimientos, shop, trainer flags, team locks, snapshots,
  Hall/archive y juicios;
- sin SQL/API/React.

Fase 5 - Repositories:

- interfaces `typing.Protocol`;
- repos legacy sobre settings/storage/Supabase V1/SQLite;
- repos in-memory para tests;
- mappers legacy <-> dominio;
- primeros use cases en `app/application/`.

Fase 6 - Supabase V2 greenfield:

- nuevo schema desde cero en `supabase/v2/migrations`;
- no se altera V1;
- no se conecta aun Streamlit a V2;
- `bootstrap.sql` generado como comodidad para SQL Editor;
- `reset_dev.sql` destructivo separado.

Fase 6.1 - Validacion real PostgreSQL:

- schema 001-009 ejecutado en PostgreSQL 17.11 local;
- reset/build/rebuild;
- fixtures de constraints, JSONB, ledger, saves, archive y delete policy.

Fase 7 - Seguridad/RLS:

- RLS en las 32 tablas publicas V2;
- helpers de identidad/admin;
- vistas `public_*` y `current_*`;
- bucket privado `raw-saves`;
- policies de storage por `trainer_id`;
- validacion local con roles mock.

Fase 7.1 - Validacion real Supabase:

- proyecto real staging `Pokeapp 2.0`;
- validador con JWT reales, PostgREST y Storage;
- resultado final: `RESULT ok checks=13`;
- 32 tablas, 82 policies, 37 vistas, 13 security_invoker, 24 proyecciones
  publicas seguras.

Fase 7.2 - Compatibilidad Storage Cloud:

- `013_storage_policies.sql` se hizo compatible con Supabase Cloud;
- se elimino el intento prohibido de `ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY`;
- migration policy-only, idempotente y aplicada en staging.

Ultimo commit bueno/pushed conocido:

- `2947020 Finish Supabase V2 staging validation`

## 6. Supabase V2

Supabase V2 es greenfield. V1 no se borra ni se toca aun.

Archivos clave:

- `supabase/v2/migrations/001_core.sql`
- `002_seasons.sql`
- `003_league.sql`
- `004_shop.sql`
- `005_saves.sql`
- `006_activity_hall.sql`
- `007_competitions.sql`
- `008_indexes.sql`
- `009_seed.sql`
- `010_security_helpers.sql`
- `011_rls_policies.sql`
- `012_security_views.sql`
- `013_storage_policies.sql`
- `014_security_invoker_hardening.sql`
- `015_public_trainers_visibility.sql`
- `016_public_team_locks_visibility.sql`
- `017_public_coin_balances_visibility.sql`
- `018_public_views_visibility.sql`

Artefactos:

- `supabase/v2/bootstrap.sql`: SQL completo para levantar una base V2 vacia desde
  Supabase SQL Editor.
- `supabase/v2/reset_dev.sql`: destructivo, solo dev/staging, nunca V1/produccion.
- `supabase/v2/README.md`: instrucciones operativas.
- `docs/supabase-v2.md`: contrato tecnico completo.
- `docs/security-rls.md`: contrato de seguridad/RLS.

Tablas principales V2:

- core: `trainers`, `seasons`, `app_settings`;
- temporada: `season_players`, `season_player_stats`, `trainer_flags`,
  `pokemon_flags`, `season_config_versions`, `divisions`;
- liga: `division_memberships`, `matchdays`, `matches`,
  `matchday_snapshots`, `matchday_movements`;
- tienda/economia: `shop_items`, `shop_promotions`, `purchases`,
  `redemptions`, `coin_transactions`;
- saves: `save_files`, `parsed_saves`, `team_locks`;
- actividad/historia: `activity_events`, `hall_of_fame_entries`,
  `season_archive_snapshots`;
- competiciones: `cups`, `cup_participants`, `cup_matches`,
  `cup_standings`, `trial_cases`, `trial_votes`, `penalties`.

Decisiones clave:

- UUIDs para entidades principales.
- Todo dato competitivo importante lleva `season_id`.
- `season_players.status` guarda el status del entrenador en temporada.
- monedas por ledger `coin_transactions`, no saldo mutable.
- saves raw fuera de Postgres en bucket `raw-saves`.
- `parsed_saves.payload` JSONB cacheado por parser version.
- current save es season-scoped.
- Hall y Team Locks usan snapshots congelados.
- `settings` deja de ser fuente de verdad en V2.
- SQLite no sera fallback silencioso en produccion V2.

## 7. RLS y seguridad

Modelo:

- `anon` no puede leer la app.
- `authenticated` lee mediante vistas.
- `service_role` solo backend/server.
- admin real = `trainers.is_admin = true`, no nombre hardcodeado.
- identidad = `trainers.auth_user_id` mapeado con `auth.uid()`.

Helpers:

- `current_auth_uid()`
- `current_trainer_id()`
- `is_current_user_admin()`
- `current_user_owns_trainer(uuid)`

Vistas:

- `public_*`: informacion publica segura para usuarios autenticados.
- `current_*`: informacion del owner/admin.

Privacidad:

- `public_trainers` no expone `auth_user_id`, `metadata`, `is_admin`.
- `public_team_locks` solo expone `public_team_snapshot`.
- `current_team_locks` expone snapshot privado solo a owner/admin.
- `current_parsed_saves` expone payload privado solo a owner/admin.
- `public_coin_balances` expone saldo agregado, no ledger privado.
- saves, compras, redenciones, ledger y parsed saves son owner/admin.

Storage:

- bucket: `raw-saves`;
- privado;
- path esperado: `{trainer_id}/{...}`;
- entrenador solo puede leer/escribir su namespace;
- admin puede leer/escribir cualquiera;
- anon bloqueado;
- service_role solo server.

## 8. API pendiente

La Fase 8 todavia no se ha empezado. Objetivo: API pequena para operaciones
criticas, no mega backend.

Operaciones candidatas:

- compra normal: purchase + ledger + activity event;
- compra promocionada: reclamar stock atomico + purchase;
- redencion: purchase status + efecto + redemption + activity;
- team lock: validar participante/save/jornada + upsert;
- cerrar jornada: resultados + rewards + ledger + snapshot + movements;
- config de temporada;
- cambios de trainer status/flags;
- upload save metadata + storage + cola/parser;
- escribir parsed save desde parser;
- finalizar/archivar temporada + Hall.

La idea es que React/cliente no haga mutaciones oficiales directamente. Las
mutaciones criticas deben pasar por API/RPC/server con service role controlado.

## 9. Discord / Aaron Avisa

Archivo principal:

- `app/discord_notify.py`

Config:

- `DISCORD_WEBHOOK_URL`
- `DISCORD_WEBHOOK_USERNAME`
- `DISCORD_NOTIFICATIONS_ENABLED`
- `DISCORD_WEBHOOK_TIMEOUT_SECONDS`
- `DISCORD_WEBHOOK_RETRIES`

Comportamiento:

- si notificaciones estan desactivadas, responde que Aaron Avisa esta silenciado
  para preparar 2.0;
- valida que el webhook parezca URL real de Discord;
- envia embeds con retries;
- muchas llamadas tienen version async con thread daemon.

Eventos soportados por Discord:

- compra normal;
- promociones/rebajas creadas;
- compra con rebaja;
- equipo fijado;
- faltan equipos por fijar;
- jornada finalizada con tabla/resultados;
- resultado de combate;
- entrenador retirado;
- test notification;
- cambios de normativa mediante hash/sections.

Decision operativa:

- no enviar anuncios de Discord por trabajos ocultos de migracion;
- Discord queda fuera del dominio/repos por ahora;
- en Fase 8 deberia colgar de eventos server-side o jobs, no de UI.

## 10. Parser, PKHeX y saves

Archivos clave:

- `conex_pkhex.py`
- `Bridge/PKHeXBridge/Program.cs`
- `PKHeX.Core.dll`

Modelo actual:

- Python llama a un ejecutable C# bridge;
- el bridge usa PKHeX.Core para abrir saves Gen 3/4/5;
- devuelve JSON con trainer, party, boxes, moves, IVs/EVs, items, ability,
  badges, etc.;
- Python normaliza ese JSON a formato UI;
- hay cache por save/mtime/caja/modo para no recalcular todo.

Comandos/flags bridge:

- lectura general: `PKHeXBridge <sav>`;
- lectura caja: `--box N`;
- modo: `--mode auto|prop|m0|m1|m2`;
- operaciones de escritura legacy: `--op revive`, `--op steal`.

Limitacion:

- El parser sigue acoplado a Streamlit/saves actuales.
- Fase 9 debe tratarlo como caja negra:
  `.sav/.dsv/.srm -> parser -> ParsedSave`.
- PokeApp no deberia depender internamente de detalles raros del bridge.

## 11. Launcher y app de escritorio

Existen launchers locales actuales:

- `PokeApp.bat`: abre Streamlit en puerto libre 8501-8510 y navegador.
- `run_app.bat`: crea/usa `.venv`, instala requirements, abre Streamlit.
- `desktop/`: wrapper Electron.

Electron actual:

- `desktop/main.js` abre `https://pokeapp.streamlit.app`;
- empaquetado con `electron-builder`;
- hay build local en `desktop/dist/`;
- es wrapper de una web, no launcher inteligente final.

Idea futura del launcher:

- una app/companion local que detecte o seleccione automaticamente el `.sav`
  del emulador;
- lea cambios del save;
- envie el raw save o parsed payload a la API/Supabase;
- permita refrescar PokeApp sin que el usuario tenga que subir manualmente cada
  vez;
- posiblemente gestione rutas locales, watcher de archivos, login/token y cola
  de subida.

Estado real:

- aun no esta implementado como producto final;
- pertenece a Fase 9/10 o posterior;
- no debe mezclarse con el redisenio React hasta definir bien seguridad y flujo.

## 12. Migracion a React / Cloudflare

Plan futuro:

- Fase 8: API critica;
- Fase 9: parser boundary;
- Fase 10: React / Cloudflare frontend;
- Fase 11: migracion de datos V1/settings -> V2;
- Fase 12: shadow mode;
- Fase 13: staging con datos clonados;
- Fase 14: performance;
- Fase 15: cutover.

Por que Cloudflare/React mejora:

- Streamlit rerenderiza mucho y puede sentirse como "recargas" al tocar cosas;
- React permite interacciones mas fluidas, estados locales, componentes reales y
  menos sensacion de pagina pesada;
- Cloudflare Pages da frontend rapido y estable;
- Workers/API pueden centralizar operaciones criticas;
- Supabase V2 + RLS da seguridad y datos normalizados;
- permite tener app nueva y Streamlit como fallback durante shadow mode.

Decision:

- no borrar Streamlit hasta shadow mode y cutover;
- no borrar Supabase V1 hasta verificar V2 y migracion;
- no conectar React antes de cerrar API/parser;
- no migrar datos sin scripts de equivalencia.

## 13. Problemas del host anterior / Streamlit actual

Problemas observados o asumidos de la version actual:

- recargas/rerenders molestos cada vez que se interactua;
- UI dependiente de Streamlit, poco control sobre transiciones y estado local;
- carga visual pesada por capas CSS acumuladas;
- dificil hacer un launcher/local companion elegante;
- seguridad real limitada porque Streamlit actua como cliente confiable;
- operaciones criticas dispersas entre UI/storage/helpers;
- fallback SQLite puede ocultar fallos remotos en rutas no estrictas;
- dependencia fuerte de `settings` JSON y `session_state`;
- Electron actual solo envuelve URL Streamlit, no soluciona arquitectura.

Beneficio de la migracion:

- experiencia mas rapida y profesional;
- separacion frontend/backend;
- API transaccional;
- RLS real;
- datos consultables por entidad;
- mejor base para app movil/desktop/launcher futuro;
- menos deuda en CSS y render.

## 14. Validaciones y tests

Comandos habituales:

```powershell
py -m compileall -q .
py -m unittest discover -s tests
git diff --check
```

Validacion Supabase V2 schema local:

```powershell
py tools\validate_supabase_v2_schema.py `
  --psql "<ruta-psql>" `
  --host 127.0.0.1 `
  --port 55432 `
  --user postgres `
  --database pokeapp_v2_validation `
  --allow-destructive-reset
```

Validacion RLS real Supabase:

```powershell
py tools\validate_supabase_v2_rls.py --env-file .env.supabase-v2-rls.local
```

Ultimo resultado conocido de RLS real:

- `RESULT ok checks=13`

Tests actuales conocidos tras Fase 7.1/7.2:

- suite alrededor de 117 tests verdes en el ultimo cierre documentado.

## 15. Archivos docs mas importantes

- `docs/project-checkpoint.md`: estado maestro actual.
- `docs/migration-plan.md`: plan por fases.
- `docs/architecture.md`: arquitectura viva.
- `docs/module-inventory.md`: mapa de modulos.
- `docs/domain-contracts.md`: contratos.
- `docs/pure-domain.md`: servicios puros.
- `docs/repositories.md`: repositories y source-of-truth matrix.
- `docs/supabase-v2.md`: schema V2.
- `docs/security-rls.md`: RLS/security.
- `docs/post-2.0-backlog.md`: backlog post-freeze.
- `docs/phase2-freeze-audit.md`: cierre funcional.

## 16. Que queda por hacer

Siguiente fase exacta:

- Fase 8 - API para operaciones criticas.

Despues:

- Fase 9 - parser boundary / launcher companion.
- Fase 10 - React + Cloudflare.
- Fase 11 - migracion de datos.
- Fase 12 - shadow mode.
- Fase 13 - staging con datos clonados.
- Fase 14 - medir rendimiento.
- Fase 15 - cutover.

Pendientes importantes:

- decidir stack API exacto (Workers, Supabase RPC, server Python o mixto);
- disenar endpoints de Fase 8;
- conectar API a Supabase V2 con service role seguro;
- no exponer service role en navegador;
- migrar ActivityEvents a tabla real;
- migrar compras/ledger/redenciones/team locks a operaciones server-side;
- encapsular parser;
- plan de export/import desde V1/settings;
- equivalencia antes/despues: ranking, monedas, locks, flags, saves, Hall;
- mantener Streamlit como fallback hasta cutover.

## 17. Aviso de estado local actual

En el momento de generar este handover, el working tree tenia una modificacion
local en:

- `tools/validate_supabase_v2_schema.py`

Esa modificacion no forma parte del ultimo commit bueno conocido y parece incluir
un caracter suelto `m` que podria romper el script. Antes de seguir programando,
conviene revisar ese diff y decidir si es cambio intencionado o hay que limpiarlo.

## 18. Instruccion para el nuevo ChatGPT/Codex

No reinventes la app ni empieces React directamente. Continua desde el checkpoint:

- V2 schema/RLS/storage ya estan validados.
- No borrar Supabase V1.
- No conectar runtime a V2 sin Fase 8/11/12.
- No anadir mecanicas nuevas.
- No tocar visual Streamlit salvo bug claro.
- Siguiente trabajo recomendado: preparar Fase 8 API critica con plan pequeno,
  tests, endpoints/RPC y documentacion.

La filosofia del proyecto es: producto congelado, migracion conservadora,
equivalencia demostrable, seguridad primero, cutover solo cuando Streamlit y la
nueva app puedan convivir en shadow mode.
