# Phase 8G.1: Informe de Cierre

Fecha: 2026-09-23. Fuente de contrato: [administracion de temporadas](phase8g1-season-admin-api.md).
Este informe distingue pruebas locales, ejecucion real en staging y trabajo futuro.
No contiene credenciales. La API no se ha desplegado ni conectado a Streamlit.

=== POKEAPP PHASE 8G.1 ===

## RESULT

DONE: implementacion, PostgreSQL local, Supabase V2 staging y limpieza independiente.
No significa que toda la API, la migracion de runtime o la seguridad de lanzamiento
esten terminadas. Los hallazgos existentes del Advisor se registran mas abajo.

## START

- branch: `main`.
- head: `089b8d6 docs: audit season and league administration contract`.
- origin: `origin/main`, ahead/behind `0/0`.
- Arbol versionado limpio; unica guia local no versionada preservada.
- Baseline: 318 tests, migrations 001-025; staging 025 `20260923180416`.

## END

- branch: `main`, upstream `origin/main`.
- head de implementacion y validador: `c6afcde`; este informe se entrega en un
  commit documental posterior, `docs: close phase 8g1 staging validation`.
  Su hash exacto se comunica al terminar, sin autorreferencia circular del archivo.
- Cierre: push normal, origin `0/0`, arbol versionado limpio.
- La guia local protegida sigue no versionada, sin modificaciones.

## PRODUCT DECISIONS

- D1=A: preparar en DRAFT, activar solo con setup completo. Admin no participante.
- D2=A: altas/remocion segura del roster inicial, exclusivamente DRAFT.
- D3=B: corregir config aun no usada, misma vigencia, razon, CAS y auditoria.
- Futuro D4-D7=A: correccion acotada con compensaciones; cancelar edicion vuelve
  a scheduled cuando sea seguro; cierre final no termina temporada; descarte
  inicial logico DRAFT. Direccion aprobada, NO implementada en 8G.1.
- D8: DEFERRED. Sin bonus individual automatico ni transferencia de progreso.

## ADMIN AUTH

- principal: JWT Supabase verificado -> `trainers.auth_user_id` ->
  `globally_enabled` -> `is_admin=true`; dependencia `require_admin_principal`.
- participant required: NO. El admin puede no competir.
- hardcoded names: NO. Nombre, slug, actor del body y claims de rol del cliente
  no conceden administracion. La RPC revalida al admin bajo lock SHARE.

## API

Todos los paths usan `/v1/admin`. Sin PATCH generico de estado/pointer.

| Funcion | Endpoint |
| --- | --- |
| GET setup | `GET /seasons/{s}/setup` |
| POST season | `POST /seasons` |
| rename | `PUT /seasons/{s}/name` |
| add participant | `POST /seasons/{s}/participants` |
| remove draft participant | `POST /seasons/{s}/participants/{p}/remove-from-draft` |
| create config | `POST /seasons/{s}/config-versions` |
| replace unused | `POST /seasons/{s}/config-versions/{v}/replace-unused` |
| initial divisions | `PUT /seasons/{s}/initial-divisions` |
| prepare first day | `POST /seasons/{s}/matchdays/prepare-current` |
| activate | `POST /seasons/{s}/activate` |

DTOs estrictos y respuestas filtradas: sin Auth IDs, secretos, SQL ni saves privados.
401 auth; 403 no habilitado/admin; 404 recurso acotado; 409 negocio/CAS/replay;
422 request malformada; 503 persistencia saneada.

## REVISION MODEL

- setup: bigint inicial 0; +1 por mutacion confirmada.
- roster: +1 por alta/remocion; config: +1 por creacion/reemplazo.
- CAS: compara revision esperada bajo lock, nunca ultimo writer gana a ciegas.
- Replay/rechazo no incrementan revisiones. Estado durable en `season_admin_state`.

## IDEMPOTENCY

- storage: `admin_operation_receipts`, respuesta original inmutable y hash SHA256
  de JSONB canonico; mismo commit que datos/evento.
- scope: actor + operacion + temporada/recurso aplicable + key.
- replay: misma identidad/scope/key/body devuelve respuesta original,
  `replayed=true`, sin duplicar filas, evento ni revision.
- conflict: key reutilizada con contenido diferente -> IDEMPOTENCY_CONFLICT.
- Rename usa key interna derivada de revision; cambiar nombre con revision
  consumida -> STALE_REVISION. Los otros writes exigen `Idempotency-Key`.
- Aclaracion A/B: dos peticiones del MISMO admin son retry. Dos administradores
  distintos tienen namespaces distintos, segun el scope por actor del contrato;
  una key coincidente no fusiona borradores ajenos.

## SETUP READINESS

- rules: roster/stats, config vigente y revision de roster, A/B, membresias,
  primera jornada scheduled, todas las parejas, pointer correcto, DRAFT y ausencia
  de otra ACTIVE. GET toma lock SHARE para leer un estado coherente.
- blocking reasons: claves ordenadas de checks no satisfechos; `can_activate`
  solo true cuando todos pasan. React no reconstruira las reglas por su cuenta.

## CONFIG

- schema: A/B positivas, total de jornadas, movement_count, tablas scoring y
  coin_rewards por rango, reglas booleanas allowlisted y revision del roster.
- validation: capacidades suman roster real; ranks exactos 1..N; importes enteros
  no negativos; movimientos <= min(A,B); vigencia dentro de temporada y posterior
  a toda jornada preparada. Sin defaults que oculten setup incompleto.
- unused definition: ninguna FK desde `matchdays.season_config_version_id` ni
  `matchday_snapshots.config_version_id`; esas son las dos referencias reales
  encontradas por introspeccion. Una jornada scheduled ya cuenta como uso.
- immutability: RPC + trigger impiden cambiar config usada; correccion inutilizada
  conserva UUID/version/vigencia, con razon y before/after privados. Regla nueva
  tras uso necesita nueva version posterior. Snapshots historicos intactos.

## ROSTER

- draft-only: SI; altas/remociones paran al existir setup competitivo inicial.
- stats: una fila inicial a cero; sin saves, economia, flags, Copa o Juicios heredados.
- remove rule: solo limpio/no referenciado. Comprueba stats/metadata/current save,
  configs/divisiones/jornadas y FKs reales a season_players; fail-closed.
  No elimina trainer global ni historia economica.
- late join: NO; tampoco retiro, abandono, descalificacion o reactivacion (8I).

## DIVISIONS

- A: codigo A, tier 1; B: codigo B, tier 2; capacidades exactas de config.
- memberships: todo participante una vez, desde jornada 1, reason initial,
  sin final/source. Asignacion unica: replay o rechazo, nunca borrar/recrear historia.

## FIRST MATCHDAY

- status: solo jornada 1 scheduled, sin abrir ni ganador.
- config: referencia exacta de config inicial validada.
- pairs: todos contra todos dentro de cada division; UUIDs canonicos e indice
  unico no ordenado impiden duplicados inversos. 2/2 -> 2; 2/3 -> 4; 5/5 -> 20.
- pointer: `prepare-current` lo inicializa en servidor, no acepta UUID del cliente.
- future shells: NO; no avance, premios, ledger ni apertura de jornada.

## ACTIVATION

- requirements: revalidacion completa bajo lock, DRAFT -> ACTIVE y started_at server.
- one-active: indice global existente resuelve carreras entre temporadas;
  colision -> ACTIVE_SEASON_EXISTS.
- auto-finish: NO. No finaliza la temporada anterior ni abre/crea otra jornada.

## SECURITY

- direct browser writes: revocadas INSERT/UPDATE/DELETE en seasons, season_players,
  season_player_stats, season_config_versions, divisions, division_memberships,
  matchdays y matches. Incluye grants de columnas previos de 020.
- RPC grants: las 23 funciones/helpers nuevas son INVOKER, search_path fijo,
  PUBLIC/anon/authenticated sin EXECUTE; service_role autorizado.
- RLS: 39/39 tablas publicas, dos nuevas backend-only; 37 vistas preservadas.
- admin/non-admin: denegaciones reales probadas; ser admin en navegador NO
  permite saltarse API escribiendo tablas o invocando RPC privilegiada.
- Los eventos SEASON_ADMIN_* son ADMIN privados. No Discord/webhook.

## ATOMICITY

- lock order: actor SHARE -> advisory de recibo -> season FOR NO KEY UPDATE ->
  participantes ordenados por UUID FOR UPDATE -> filas propias de operacion.
  Compatible con FK KEY SHARE y locks 025. Insercion serializa por temporada.
- failure injection: solo PostgreSQL local, nueve puntos: draft, participante,
  config, segunda membresia, jornada, match, pointer, activacion y recibo.
- rollback: snapshot de DATOS de todas las tablas publicas antes/despues, igualdad
  exacta en los nueve casos. Sin mutex Python ni retries automaticos de mutacion.

## CONCURRENCY

- duplicate participant: una fila/stats/evento; revision vieja pierde sin efectos.
- config: un ganador por base; corregir vs primer uso queda serializado.
- prepare: mismo key replay; keys/admins distintos no duplican jornada ni parejas.
- activation: una transicion y recibo original reutilizable.
- two seasons: como maximo una ACTIVE; no cierre implicito de la otra.
- A-K incluyen cambios roster/config/divisiones concurrentes; PASS local y remoto.

## MIGRATION

- 026: aditiva, `026_season_admin_setup_api.sql`; revisions/receipts, campos minimos
  config, indices/guards, RPCs y grants. Bootstrap generado, no duplicado manualmente.
- 001-025 unchanged: SI, verificado contra `089b8d6`.
- `reset_dev.sql` actualizado solo para rebuild local aislado. Nunca ejecutado
  en staging/V1; tampoco se uso bootstrap sobre staging existente.

## LOCAL

- tests: **343 PASS** = 318 baseline + 25 nuevos, con
  `.\.venv-api\Scripts\python.exe -m unittest discover -s tests`.
- PostgreSQL migrations: **PASS**, 17.11 en 127.0.0.1:55439, base desechable
  `pokeapp_v2_validation_phase8g1`, `tools/validate_supabase_v2_schema.py`.
- PostgreSQL bootstrap: **PASS**, mismo comando con `--build-source bootstrap`.
- Paridad: 7,381 lineas de pg_dump schema-only iguales, incluidos grants/ownership;
  solo se normalizan tokens aleatorios de restrict/unrestrict del dump.
- races: 17 grupos por cada rebuild, incluidas A-K.
- rollback: nueve fallos inducidos con igualdad exacta por cada rebuild.
- regressions: 019-025, Auth, RLS/schema, Team Lock, contexto/Store Ban, compra normal,
  promo, identidad, canjes y robo/comodin. Los asserts antiguos de escritura directa
  admin ahora esperan denegacion por 026; no se elimina cobertura.
- compileall: `py -m compileall -q .` PASS.
- diff-check: `git diff --check` PASS.
- Warnings conservados: Streamlit cache/sin runtime, deprecacion Starlette/httpx
  TestClient y conversion Git LF/CRLF. No son fallos de estos gates.

## STAGING

- target: Pokeapp 2.0, `https://uwleqeuzsveqlugugzba.supabase.co`, verificado por MCP.
- 026: aplicada sola tras push `178cc41`, version **20260923192300**.
- checks: run `phase8g1_validation_ec1accfdab004e189f9b424346812523`, **17 grupos PASS**.
- previous API regressions: Team Lock **13**, compra/contexto **29**,
  identidad/redencion/robo/comodin **17 grupos**, todos PASS.
- Resultado literal: `RESULT ok groups=17; real JWT/API/PostgREST; Auth cleanup PASS`.
- Comando: `.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_season_admin.py --env-file .env.supabase-v2-rls.local --allow-staging-writes`.
- security: verificacion independiente SQL de 39/39 RLS, 37 vistas, 23 funciones
  restringidas y ausencia de grants de tabla/columna en las ocho tablas.
- cleanup: cero Auth users/identities/sessions del prefijo; cero seasons, players,
  stats, configs, divisions, memberships, days, matches, activity, admin receipts y
  admin state. Las tablas de regresion economia/identidad/save/efectos tambien vacias.
- Datos originales: 10 trainers, 62 catalog items y 3 Storage objects intactos;
  fingerprints de contenido antes/despues iguales (tabla siguiente).
- transport: real JWT -> FastAPI TestClient -> adapters productivos -> PostgREST.
  Sesiones por worker, sin retries de mutaciones ni DDL de fallo remoto.
  No se afirma arreglo global de la intermitencia Windows/httpx.

Primer intento remoto: `phase8g1_validation_3e19f27697fe430c907b913f8e481ae5` fallo
por TypeError del validador al interpretar lista 422 como objeto de error de negocio.
Se limpio y verifico independientemente. `c6afcde` corrigio SOLO el harness y anadio
un test; mantiene distintos los asserts 422-malformed y 409-business. La ejecucion
completa posterior es la evidencia de cierre, no se oculta el fallo previo.

| Conjunto real | MD5 del JSONB agregado ordenado, igual antes/despues |
| --- | --- |
| trainers | `99db01fe5335bad3bd3fa7466b44e8d4` |
| shop_items | `76d1c1d5137e6288f508d62786a6d312` |
| storage.objects | `744470d4653ef586ffd402c7abbc7691` |
| storage.buckets | `391ce69bf761cb4c199bbe89b510082a` |

### Advisor y Limites

No se declara Advisor limpio ni aprobacion global de seguridad de lanzamiento.

- **24 ERROR existentes**: vistas publicas definer/safe-by-shape de 018.
  No nuevas en 026. [Criterio y revision](https://supabase.com/docs/guides/database/database-linter?lint=0010_security_definer_view).
- **1 WARN existente**: search_path de `set_updated_at`.
  [Remediacion](https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable).
- **3 WARN existentes**: helpers definer de identidad ejecutables authenticated:
  current_trainer_id, current_user_owns_trainer, is_current_user_admin.
  [Revision de privilegios](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable).
- **3 INFO** RLS sin policies: robbery_cycles y las dos tablas nuevas de 026.
  Intencional backend-only, sin grants browser; no crear policies cliente para
  ocultar el aviso. [Explicacion](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).
- Una respuesta intermedia tambien mostro `auth_leaked_password_protection` WARN;
  no aparecio en la ultima respuesta de Advisor. No se tocaron ajustes Auth, no se
  considera resuelto por ausencia posterior. Revisarlo antes de exposicion publica.
  [Proteccion de contrasenas](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

## GIT

- `178cc41 api: add atomic season setup administration`.
- `c6afcde test: distinguish schema and business validation failures`.
- Commit documental de cierre: `docs: close phase 8g1 staging validation`.
- push: normal, sin force ni amend; origin/main `0/0` al entregar.
- guide untouched: SHA256
  `6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`;
  `docs/pokeapp-guia-completa-pestanas-y-producto.md` sigue untracked, no staged.
- No cambios en Streamlit, V1, legacy setup, dominio, Discord, PKHeX, operaciones
  fisicas del bridge/saves, React, Companion, Copa/Juicios ni flujos 8H/8I/8J.

## PROGRESO GLOBAL

- BEFORE: ~57%.
- AFTER: ~59%.
- CHANGE: aproximadamente +2 puntos porcentuales, estimacion ponderada, no metrica
  automatica de tests ni porcentaje de endpoints.
- WHY: setup/admin completo y probado local/remoto; faltan 8H/8I/8J, otras APIs
  competitivas, parser, React/Cloudflare, migracion, shadow, rendimiento, cutover,
  Launcher/Companion, automatizacion fisica segura y endurecimiento final.

## CHECKPOINT

8G.1 complete: **YES**. Runtime actual sigue Streamlit/V1, sin dual-write.

## NEXT

**Phase 8H**, administracion competitiva de jornadas/cierre/avance, con su propio
contrato y validacion. **No implementada en esta tarea.**

=== END REPORT ===
