# Phase 8K — Trials / Sanctions / Cup API Contract Audit

Fecha: 2026-09-24. **AUDIT ONLY — DONE como auditoría documental. Implementación pendiente.**

Base inspeccionada: `main`, `0c8b792feec06038cecf9bb92882e3eb71dd8065`,
`origin/main` 0/0 después de fetch; árbol versionado limpio. Único untracked inicial:
`docs/pokeapp-guia-completa-pestanas-y-producto.md`. No se leyó su contenido ni se
modificó; SHA256 de control:
`6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.

Baseline **431 tests PASS**, migraciones **001–029**, 029 aplicada como
`20260923232516`: evidencia anterior de [8J](phase8j-completion-report.md), no
pruebas ni consultas remotas nuevas. Runtime sigue Streamlit/V1, API aislada.
Progreso **~66% → ~66%**. No migración 030, código, staging, despliegue ni Phase 9.

## 1. Resultado y vocabulario

La capa competitiva API **no está completa**. Faltan el ciclo judicial autorizado,
la aplicación transaccional de sanciones y la operación de Copa desde preparación
hasta certificación/Hall. No basta añadir un endpoint que copie un ganador.

Hall de Liga y 026–029 permanecen cerrados. La recomendación es **dos fases de
implementación**, 8K.1 Juicios/sanciones y 8L Copa/certificación/Hall. Las decisiones
de §10 bloquean partes de esa implementación, **no la conclusión de esta auditoría**.

Etiquetas usadas:

- **EXISTING BEHAVIOR**: código legacy ejecutable, incluidas sus limitaciones.
- **CURRENT V2 CAPABILITY**: garantías realmente presentes hasta 029.
- **GAP**: ausencia o contradicción comprobada; una tabla no implica una operación.
- **PROPOSED CONTRACT**: propuesta para trabajo posterior, no aprobada ni implementada.
- **PRODUCT DECISION REQUIRED**: elección no deducible con seguridad de las fuentes.

Los identificadores de endpoint/evento/tabla futuros de este documento son propuestas.
Las observaciones SQL son inspección del historial local; no una nueva certificación
de grants, datos o Advisor del servidor remoto.

## 2. Fuentes leídas y evidencia reproducible

Se leyeron primero [checkpoint](project-checkpoint.md), [arquitectura](architecture.md)
y [cierre 8J](phase8j-completion-report.md). Después se inspeccionaron estos archivos
o sus secciones pertinentes; los símbolos permiten encontrar la evidencia sin
depender de números de línea cambiantes:

| Área | Archivos / símbolos inspeccionados |
| --- | --- |
| Contratos anteriores | [auditoría 8G](phase8g-season-league-admin-audit.md), [8H](phase8h-matchday-operations.md), [8I](phase8i-participant-status.md), [8J](phase8j-season-finalization.md), [RLS](security-rls.md); se distingue texto histórico de contratos posteriores |
| Juicios legacy | [constants](../app/juicios/constants.py), [repo](../app/juicios/repo.py): `create_case`, `update_case`, `register_jury_vote`, `delete_case`, permisos; [forms](../app/juicios/forms.py), controles de [ui](../app/juicios/ui.py), [render](../app/juicios/render.py), [penalties](../app/juicios/penalties.py) |
| Dominio / repositorio | [trials](../app/domain/trials.py), [servicio trials](../app/domain/services/trials.py), [cup](../app/domain/cup.py), [protocols](../app/repositories/protocols.py): `CompetitionRepository`, [legacy competitions](../app/repositories/legacy/competitions.py), [mappers](../app/repositories/mappers.py): `trial_case_from_legacy`; búsqueda de adapters/fakes en `app/repositories/` |
| Consumidores | [ranking legacy](../app/liga/ranking.py): `_penalties_for_snapshot`, `current_points_total`; usos en snapshots/matchup/summary/tienda; [money](../app/tienda/money.py): `money_breakdown_from_parts`; [plan_close](../app/application/matchdays.py), [rewards](../app/domain/services/rewards.py), [shop eligibility](../app/domain/shop_eligibility.py) y [adapter](../app/repositories/supabase/shop_eligibility.py) |
| Copa legacy | [swiss](../app/copa/swiss.py), [elim](../app/copa/elim.py), [doubles](../app/copa/doubles.py): creación, resultados, avance, reset y Hall; [pages](../app/interfaz/pages.py): `page_copa`; wrappers `copa.py`, `copa2.py`, `copa_dobles.py`, `juicios.py`; `main.py` y `utils.py`: login, secciones, `active_users` |
| Hall / archive legacy | [hall_of_fame](../app/interfaz/hall_of_fame.py): `_swiss_auto_entry`, `_elim_auto_entry`, `_doubles_auto_entry`, `_merge_entries`; [archive](../app/season/archive.py): `_cup_hall_entries`, fuentes y resumen de Liga; inventario de servicio de Hall puro |
| SQL estructural / seguridad | [004](../supabase/v2/migrations/004_shop.sql): ledger; [006](../supabase/v2/migrations/006_activity_hall.sql): Hall/archive/eventos; [007](../supabase/v2/migrations/007_competitions.sql) completo; índices 008; helpers/policies/views 010–012, hardening 014, visibilidad 018; búsqueda de todas las referencias posteriores hasta 029 |
| SQL contractual | [020](../supabase/v2/migrations/020_current_matchday_store_ban_contract.sql) completo; locks/consumidores 021–025; [026](../supabase/v2/migrations/026_season_admin_setup_api.sql): grants, receipts, principal, CAS; [027](../supabase/v2/migrations/027_competitive_matchdays.sql): facts/context/correction; reemplazos [028](../supabase/v2/migrations/028_participant_status_admin.sql); fuentes, artefactos y filtros [029](../supabase/v2/migrations/029_season_finalization_archive_hall.sql) |
| API / tests | [main API](../app/api/main.py) y búsqueda de rutas/adapters/application; `tests/test_domain_contracts.py`, `test_domain_services.py`, `test_api_matchdays.py`, `test_shop_eligibility.py`, `test_hall_of_fame.py`, `test_liga_snapshots.py`; búsqueda de referencias en schema/RLS/lifecycle/status/archive/repository tests; [runner](../tools/run_unit_tests.py) |

No lectura masiva de informes históricos, bootstrap generado, credenciales ni guía
protegida. No AGENTS.md aplicable encontrado en el repositorio ni directorios padre
comprobados. No agentes delegados.

## 3. Juicios: comportamiento actual

### 3.1 Conceptos y persistencia — EXISTING BEHAVIOR

`juicios_state_v1` es un único JSON global en settings, **sin temporada propia**.
Contiene contadores y casos con id/número, creador, acusado, título, resumen, fecha
de audiencia, visibilidad, pruebas/testigos de texto, prioridad/categoría,
`public_vote`, tamaño del jurado, votos nominales, resolución, castigos y timestamps.
No hay entidad separada de acusación, lista de jurados nombrados, anexos de evidencia
ni historial de revisiones. Las identidades legacy son nombres, no UUID autenticados.

Estados: `propuesto → en_proceso → finalizado`; el último se muestra también como
«Archivado», sin equivaler a `seasons.archived`. Veredictos: pendiente, culpable,
no culpable. Jurado 3/5/7/9; mayoría `floor(n/2)+1`.

| Operación legacy | Actor / precondiciones | Estado y efectos reales | Edición / reversión |
| --- | --- | --- | --- |
| Crear | Usuario con sesión; formulario exige título, razón y acusado de `active_users()` | Propuesto/pendiente, fechas, id/número; puede guardar propuestas de castigo | Repo no valida toda la UI ni participación/temporada; JSON completo sin CAS |
| Consultar | Público o creador para un caso privado | Render muestra pruebas, testigos y votos nominales al lector autorizado | Acusado/admin no tienen excepción propia en `can_view_case` legacy |
| Editar / iniciar | Creador; UI edita detalles en propuesto | Mismo estado o siguiente; inicio no exige castigos en el repo | Helper admite editar campos incluso finalizado mientras no retroceda estado; UI terminal no muestra editor |
| Proponer castigos | Creador en proceso por UI; cantidades positivas, texto para liberación/otro | Guarda lista y notas; sin efectos mientras no finalizado | Plantillas primera falta: 1 punto; reincidencia: 12 monedas + 2 puntos + ban; grave: 20 + 4 + ban + nota Pokémon |
| Votar / cambiar voto | Caso visible, en proceso; voto propio o creador actuando por tercero | Un voto vigente por nombre, último timestamp; mayoría finaliza automáticamente | No roster de jurados, límite real de votantes, exclusión del acusado/creador ni guard basado en `public_vote` |
| Finalizar manual | Creador; UI exige al menos un castigo | Si pendiente, repo infiere culpable con castigos/no culpable sin ellos; culpa manual exige castigo; no culpable vacía lista | Mayoría culpable puede cerrar sin castigos: no usa la misma validación manual |
| Cancelar | Creador, checkbox en UI; repo sin límite de estado | **Borra permanentemente** el caso, renumera restantes; también casos terminados | Elimina la fuente de futuras deducciones vivas; no escribe compensación ni repara snapshots |

`create/update/vote/delete` escriben todo el blob; no transacción con consumidores,
CAS, receipt, evento de actividad ni evidencia append-only. No se encontraron
llamadas a Discord en estas operaciones. No importar sus permisividades como
autorización para reescribir historia V2.

### 3.2 Sanciones legacy — EXISTING BEHAVIOR

`get_user_penalties` agrega casos terminados por acusado, sin filtrar temporada ni
veredicto directamente. La normalización del repo elimina castigos no culpables,
pero el consumidor lee el JSON por su cuenta: no es una garantía transaccional.

| Tipo | Efecto comprobado | Lo que no implementa |
| --- | --- | --- |
| `store_ban` | Bloqueo de tienda/monedas disponibles; ventana inclusiva de tramos. Al resolver, si falta un límite se asigna tramo actual a ambos; históricos sin ventana permanecen activos | No cambia estado del participante ni Team Lock; no inferir nuevas restricciones de canje V2 del rótulo «ni monedas» |
| `coins_reduction` | Suma entera no negativa; disponible `max(base - gastado - reducciones, 0)` salvo ban/inactividad, que muestran 0 | No ledger, débito único, devolución explícita ni cancelación de compras. La reducción íntegra sigue consumiendo ingresos futuros si hoy supera saldo |
| `points_reduction` | Suma decimal no negativa; total legacy resta una vez sobre premios acumulados. Si existe snapshot, usa sanciones del último snapshot, no las vivas | No resta de cada premio de jornada, ni ordena por sí misma enfrentamientos/movimientos; no reescribe jornadas cerradas al borrar caso |
| `pokemon_release` | Texto en notas de sanción | No entidad Pokémon target, flag, muerte/liberación real, cambio de save ni trabajo Companion |
| `other` | Nota descriptiva | No despachador de efectos arbitrarios |

Los snapshots fijan metadatos de sanciones. El rango Store Ban no da vigencia a
reducciones de puntos/monedas. No hay suspensión temporal de elegibilidad, baja,
confiscación de equipo, alteración de robo, ascenso/descenso ni premio extra por
resolver un juicio. La retirada legacy no borra los casos. La limpieza de temporada
resetea Copa pero no convierte el JSON global judicial en sanciones season-scoped.

## 4. Cobertura V2 de Juicios y sanciones

### 4.1 CURRENT V2 CAPABILITY / GAP

| Objeto | Capacidad actual | Hueco concreto |
| --- | --- | --- |
| `trial_cases` | UUID, temporada opcional, jornada FK misma temporada, acusado/creador, título/descripción, payload y fechas; estados `open/resolved/dismissed/cancelled` | `open` no distingue propuesta/audiencia; no número estable, veredicto tipado, quorum/roster, revisiones, autoridad de resolución, razón/historial ni vínculo atómico a efectos |
| `trial_votes` | FK caso/votante, único caso/votante; `guilty/not_guilty/abstain/other`, payload, fecha de creación | No validez por fase, elegibilidad/jurado, timestamp de revisión, actor delegado, inmutabilidad terminal ni agregación autoritativa; abstain/other no son votos legacy soportados |
| `penalties` | Temporada/trainer requeridos; caso opcional; jornada FK; tipo texto, amount **integer**, payload, creador/fechas | No catálogo de efectos, CHECK positivo general, estado aplicado/anulado, receipt, source revision, dedupe por efecto ni ledger FK; caso no exige mismo acusado/temporada por FK; fracciones legacy se perderían |
| 020 | Ventana tipada inclusiva; `api_is_store_banned` exige caso **resolved**, acusado coincidente y temporada igual o NULL | Consumidor completo; **sin writer judicial**. `resolved_at` de penalty no extingue ban. Si cualquiera de los límites es NULL, ban activo por compatibilidad. Ban suelto sin caso no aplica |
| 027 / reemplazo 028 | Contexto congela sumas de puntos/monedas aplicables al trainer/season y jornada exacta o NULL; admite penalty admin sin caso o caso resolved compatible | Es evidencia de cierre, **no aplicación monetaria**. No hay ids/revisiones de cada sanción en esa suma; no ventana futura de puntos. `start/end_matchday_number` solo se usa para Store Ban |
| Ledger 004 y compras 021/022 | Tipo `penalty` permitido, saldo SUM ledger, serialización por season_player | Ninguna RPC aquí produce el débito judicial. Insertar `coins_reduction` solo en penalties no reduce saldo comprable |
| Dominio puro | `TrialCase`, `Penalty`, `JuryVote`, mayoría/transición; contratos sin dependencias | No servicio transaccional ni autorización. `Penalty.amount` float frente a integer SQL; `TrialStatus` no coincide con SQL |
| Repositorios | `CompetitionRepository` y `LegacyCompetitionRepository` cargan/guardan blobs | No adapter Supabase de casos/votos/sanciones ni casos de uso V2. No asumir que el wrapper legacy usa esos servicios puros |

Contradicción adicional localizada: `trial_case_from_legacy` reconoce `inocente`
y `not_guilty`, pero no el `no_culpable` que emiten las constantes/repo actuales;
puede convertirlo en pendiente y omitir ese voto. Es evidencia directa de un
mapper incompleto, no permiso para rehacer Fases 3–5. La migración/importación futura
deberá tener fixtures de ambos vocabularios; no se ha corregido código en este audit.

**Puntos, premios y Hall son cosas distintas.** `plan_close` ordena por resultados y
muertes mediante `rank_division`; `build_standings_from_rankings` conserva premios
configurados y adjunta `PenaltySummary`. No usa `points_reduction` para cambiar
posición, movimiento, last-B ni monedas concedidas. El test
`test_penalties_not_deducted_from_each_round_reward` preserva esto. 029 elige Hall de
Liga por posiciones del último snapshot: una nueva API de sanciones no puede
prometer cambiar ese campeón restando puntos. Una clasificación acumulada sancionada
necesita definir una proyección separada, sin reinterpretar ese contrato cerrado.

### 4.2 Matriz de efectos y fronteras

| Área | CURRENT V2 CAPABILITY | PROPOSED CONTRACT / decisión pendiente |
| --- | --- | --- |
| Puntos históricos | Snapshots/revisiones 027 conservados; corrección usa inputs congelados | Ningún UPDATE retroactivo de puntos/rewards. Efectividad de nueva deducción: T3 |
| Elegibilidad futura / status | 028 ya proporciona retire/abandon/disqualify permanentes y corte efectivo | No convertir condena automáticamente en baja ni suspensión; usar contrato 028 explícito. Nueva suspensión sería otro producto |
| SCHEDULED / OPEN | Cierre recoge penas aplicables; no writer ni fecha judicial efectiva | Escritor nuevo debe serializar con open/close; T3 decide ventana. No tocar parejas ni ganadores |
| Movimiento / rewards | Derivados de ranking de ronda, no del total sancionado | Preservar importes, last-B y movimientos. No retirar gifts o recomputar rondas por sentencia |
| Economía | Saldo ledger; resumen de coin penalty no debita | Débito único completo, entero y trazable; no descontar otra vez en el cierre. Igualar reducción íntegra legacy implica deuda contable si excede saldo, sin perdón tácito; proyección gastable puede mostrar 0 |
| Team Lock / Pokémon | 019 histórico y 023 identidad; pena de liberación aún textual | No borrar/reemplazar locks, flags o saves. Liberación/otro conservados como notas no ejecutables |
| Robo / canjes | 024/025 verifican elegibilidad propia, no Store Ban; 028 gestiona ciclo al dar baja | No alterar ciclo, entitlements, vouchers ni pending physical por una pena. Ban de compras no se amplía a canjes |
| Tienda | 020–022 ya consumen ban | Resolución + activación de pena atómicas; compras anteriores válidas; carrera por season/player resuelta una vez |
| Hall / archive | 029 artefactos inmutables, League Hall fijado | Sin reelegir campeón, regenerar archivo o cambiar su checksum; anotaciones futuras separadas si se aprueban |

### 4.3 Caso/sanción según el momento competitivo

Esta tabla distingue el comportamiento vigente de la propuesta conservadora. La
existencia de un caso **no suspende por sí sola** una jornada, compra o cierre.

| Momento | CURRENT V2 CAPABILITY | PROPOSED CONTRACT / límite |
| --- | --- | --- |
| Jornada SCHEDULED | Penas pueden ser leídas al cerrar después; 028 rechaza baja si hay trial/penalty ligado a esta jornada, incluso sin relación con el jugador que sale | Se puede preparar expediente; emisión requiere scope/ventana y locks. Distinguir jornada del hecho denunciado de jornada de efecto para no crear dependencias accidentales; T3 |
| Jornada OPEN | 028 rechaza bajas. Contexto de close toma penas; una variación entre plan y commit invalida fingerprint | T3: efecto en esta ronda aún no cerrada o diferido. Nunca reintentar close automáticamente con datos nuevos ni cambiar resultados |
| Jornada CLOSED, temporada aún ACTIVE | Snapshot fijo; caso/pena nuevos cambian external_facts e invalidan corrección 027. Si es cierre final, no hay otra jornada que absorba puntos | No usar `/correct` para inyectar penas nuevas: reutiliza inputs históricos. T3 decide efecto futuro o pendiente sin efecto competitivo. Compras aún posibles con pointer final CLOSED; Store Ban puede seguir aplicando según 020 |
| Temporada FINISHED | 029 no exige ausencia de juicios pendientes; bloquea nuevas operaciones competitivas existentes. Canjes 024/025 conservan reglas | T3 debe definir si se permite resolución documental o económica tardía. Recomendación inicial: conservar expediente pendiente/consulta, sin nuevo efecto; no fingir que 029 ya tiene ese guard judicial |
| Temporada ARCHIVED | Hall/archive no cambian. Tablas judiciales antiguas no tienen guard global de lifecycle | Nuevos writers deben impedir efectos retroactivos. Resolución/anotación posterior, si se aprueba, sería separada y sin editar paquete/Hall; T3/T4 |

No añadir un bloqueo de finish/archive por juicios pendientes como supuesto oculto:
sería modificar 029. Tampoco transferir penas a otra temporada a partir del JSON V1.

## 5. Copa: dominio y comportamiento legacy

### 5.1 EXISTING BEHAVIOR

Tres estados globales separados: `copa_swiss_state`, `copa_elim_state`,
`copa_dobles_state`. Un estado activo por modo, con `hall_run_id` basado en tiempo
para cada nueva ejecución. No ledger/puntos de Liga ni temporada relacional propia.
Selectores usan participantes activos legacy. La entrada general exige login;
`sections_for_user` solo oculta Temporada a no-Anto. Los tres módulos de Copa,
wrappers y dispatcher **no tienen guard admin**: sus controles de mutación están
disponibles para el usuario que accede. No trasladar eso a autoridad oficial V2.

| Modo | Preparación / rondas | Resultados / avance / ganador | Corrección y límites observados |
| --- | --- | --- | --- |
| Suiza / «Copa» | Desde 2 jugadores en UI, máximo 7 rondas por defecto. Agrupa por victorias y baraja; evita revancha si encuentra alternativa, la admite si no. Bye aleatorio preferentemente sin bye anterior; si se agotan repite | 4 victorias clasifican, 3 derrotas eliminan. Bye suma victoria. Cierra ronda explícita y genera Top 4 al alcanzar 4 clasificados o agotar rondas; completa plazas por W/Buchholz/nombre. Semis 1–4 y 2–3; ganador de final explícito | Edición manual de roster, W/L y parejas sin reconciliar historia. Helper de desempate head-to-head existe, pero `_build_topcut` no lo invoca. Con 2/3 jugadores no puede construir Top 4. No certificación ni rollback |
| Eliminatoria / «Torneo Bo3» | Al menos 2, orden elegido o barajado; rellena hasta potencia de 2 con NULL; un rival ausente implica BYE | Marcadores distintos 0..99; ganador por mayor score, **no validación Bo3 real**. Cerrar ronda recoge ganadores y crea siguiente; con <=1 restante termina y llama Hall | UI permite guardar/limpiar cualquier ronda, sin invalidar sucesores. En `_render_bracket` esas acciones cambian memoria y llaman rerun **sin `_persist_elim_state`**; luego restore recarga settings. Hueco de persistencia identificado estáticamente, no reproducido en UI en este audit |
| Dobles | Equipos con id local/nombre y exactamente 2 entrenadores; nombres únicos y sin entrenador repetido entre equipos. Round-robin por rotación, descanso sin match si número impar | Solo 2–0/2–1/1–2/0–2. Ranking: series ganadas, diferencia de juegos, juegos ganados; empate de dos usa enfrentamiento, de más/nada resuelto usa nombre. Tras todos los partidos, final entre Top 2; campeón es **equipo**, no primer integrante | Edición de cualquier jornada/final. `_sync_final` limpia final si liga incompleta o cambian sus lados; conserva resultado si siguen iguales aunque cambie evidencia. No historial inmutable |

Los tres permiten resetear estado; persisten blobs completos sin CAS/receipts.
Persistencia y sync Hall capturan excepciones silenciosamente. Sorteos no guardan
algoritmo/semilla certificada. Swiss muestra pokepaste de snapshot vivo, sin Team
Lock competitivo propio de Copa. No encontramos autoridad de equipos Pokémon
participantes ni premios económicos de Copa que deban inventarse en V2.

### 5.2 Hall legacy

Swiss toma `topcut.champion`; eliminatoria exige última ronda con un solo match y
winner; dobles toma final Bo3 válida y mapa de equipos. Esas lecturas **no prueban
todo el recorrido del torneo**. El nombre de temporada se resuelve al sincronizar,
no desde FK congelada. Hall live hace upsert por `hall_run_id` o digest de fallback;
conserva fecha, puede cambiar campeón, conserva entradas de ejecuciones anteriores
tras reset. Singles puede tomar equipo vivo como fallback; dobles muestra nombre
de equipo e integrantes en notas, equipo Pokémon vacío.

Archive legacy añade sus entradas después de live, por lo que prevalecen cuando
comparten id; Cup archive usa equipos Pokémon vacíos. Nada de esto certifica
automáticamente un Cup/Hall V2 importado.

## 6. Copa V2 y certificación pendiente

### 6.1 CURRENT V2 CAPABILITY / GAP

007 sigue siendo la estructura principal; 029 añade filtros de visibilidad y
preserva Hall. No hay router, caso de uso o RPC de Copa. `app/domain/cup.py` solo
contiene dataclasses; `champion_id` es trainer, insuficiente para dobles.

| Objeto | Existe | Falta para ser autoridad |
| --- | --- | --- |
| `cups` | Temporada nullable, categoría cup/tournament/doubles_cup, formato swiss/elimination/doubles/manual, status draft/active/finished/archived/discarded | **No existe status `completed` en cups**; sí en cup_matches. Ningún status certifica campeón; no revisión, reglas inmutables, final inequívoca ni certificado |
| `cup_participants` | Un lado con trainer nullable, display_name, seed, status y metadata | No membership relacional de parejas; no trainer único por Cup, cup/player season FK, cardinalidad 1/2 ni orden de seeding único |
| `cup_matches` | Ronda/posición, lados, ganador, score texto, status | No fase suiza/semis/final tipada, grafo de avances, resultado revisionado, semilla, reglas de score o cierre. FK simple admite lados de otra Cup y CHECK no prohíbe autoenfrentamiento |
| CHECK winner | Expresión ganador NULL o igual a un lado | No completa integridad: si un lado es NULL y ganador distinto del otro, la expresión puede ser SQL NULL y pasar CHECK. No tomarla como prueba de ganador válido |
| `cup_standings` | Único cup/participant, posición nullable, puntos/W/L | Posición no única; FK no obliga mismo Cup; no vínculo a resultados/revisión ni fuente de desempate |
| Hall 006/029 | Champion trainer obligatorio; único season/category; guard de UPDATE y provenance League | No cup_id/certificado ni champion-side/members. Dobles no puede representarse eligiendo un miembro. Provenance 029 permite sus campos nuevos no NULL solo para League |
| Views | Public cups/participants/matches/standings safe-by-shape | No members tipados, fase final, certificado, regla/version o hash. Leerlas no demuestra integridad |

Schema permite **varias copas del mismo tipo en una temporada** y copas sin temporada.
Legacy también conserva varias ejecuciones en Hall por source id. No imponer una
sola Copa como «arreglo técnico» del índice Hall; la propuesta conserva pluralidad.

### 6.2 PROPOSED CONTRACT: ciclo mínimo correcto

1. **DRAFT**: Cup con temporada explícita para este primer flujo API; categoría,
   formato/reglas, roster y lados validados; revisiones editables con CAS. Copas
   antiguas sin season quedan fuera del flujo certificado, sin asignarles una ficticia.
2. **ACTIVE** mediante comando de inicio: congela reglas, roster, identidad de lados,
   miembros, orden/sorteo y primera fase. Motor distingue suiza + Top 4, eliminación
   y round-robin de parejas + final; no usa «doubles» como algoritmo por sí solo.
3. Registro de resultados válido y cierre/avance explícito de ronda/fase. Cada
   transición guarda evidencia y crea dependencias una sola vez. Final reconocible
   por tipo y enlaces de origen, no por `max(round_number)`.
4. **Resultados completos / pendiente de certificación**: estado derivado/readiness
   mientras Cup permanece ACTIVE; no necesita otro enum si no aporta semántica.
5. **CUP FINALIZED**: hecho creado por `POST .../finalize`, estado `finished` más
   certificado tipado e inmutable. Final resultado y certificación separados para
   revisar coherencia; la escritura de último score no se convierte en Hall implícito.
6. ARCHIVED, si se necesita presentación separada, solo preserva ese certificado;
   no vuelve a calcular. DRAFT sin dependencias puede descartarse lógicamente.
   No reset destructivo, nuevo sorteo tras comenzar, ni reopen genérico.

`finalize` verifica bajo locks todas las fuentes: roster legal, lados misma Cup,
grafo/rondas completos, byes justificables, resultados válidos, avances consistentes,
clasificación y desempates reproducibles, una única final autorizada con dos lados
distintos y ganador perteneciente a ella. Valida semis o round-robin/Top 2 según
formato. No acepta del cliente campeón, standings, hash o snapshot.

C1 decide la discrepancia Bo3 y C2 la política de correcciones con dependencias.
La incapacidad suiza con menos de 4 es un error de readiness: rechazar configuración
incompleta para suiza+Top4, sin inventar mini-topcuts. Desempates existentes se
documentan/versionan, incluidos fallback por nombre y qué helper no se usa.
La edición libre de W/L no sustituye los resultados verificables.

### 6.3 Evidencia congelada y campeón de dobles

Certificado con versión, cup/season/category/format, revision final, reglas,
roster/lados/miembros y nombres históricos, sorteo/orden y versión de algoritmo,
fases/parejas/byes, resultados y revisiones, decisiones de desempate, final y
champion/finalist **participant-side IDs**, fecha/actor y checksum. Guardar resultado
del sorteo además de semilla: esta no basta sin versión de algoritmo.

Singles: lado con exactamente 1 trainer miembro. Dobles: exactamente 2 distintos,
únicos dentro de la Cup, nombre de equipo congelado. `winner_participant_id` identifica
el lado; miembros por FKs/filas tipadas, no por análisis de texto JSON. No confundir
pareja de entrenadores con su equipo de seis Pokémon.

Para Hall, certificado público saneado y detalle interno separados. No pruebas
judiciales, metadata libre, Auth ni private Team Locks. Copa no tiene hoy fuente
autoritativa de equipo Pokémon de final: **guardar `[]`/fuente ausente**, como Cup
archive legacy, y nunca usar save vivo ni fingir que un lock de Liga es equipo Cup.
Un lock específico de Cup sería contrato nuevo, no requisito para inventar equipo.

### 6.4 Hall determinista e historia

**PROPOSED CONTRACT**: certificación + estado + Hall + revision + evento + receipt
en una transacción. No dos writers independientes ni polling que deduzca ganador.
Clave única nueva por `cup_id`/certificado; categoría es dato, no identidad del torneo.
Preservar unicidad de League por season y separar las filas Cup con procedencia
explícita, mediante extensión compatible de Hall o tabla Cup Hall enlazada. La
elección física es técnica, no pregunta de producto, pero debe cubrir ambos miembros
y lecturas públicas y mantener 029 sin alteración de filas históricas.

Si se extiende Hall, reemplazar su índice global mediante migración incremental,
manteniendo una restricción equivalente para League y los legacy sin cup_id, más
unicidad para nuevas Cups. No asignar cup_id/miembros a entradas antiguas por nombre;
un enlace histórico, si llegara a probarse, va en evidencia adicional sin UPDATE del
artefacto protegido. Un conflicto no se resuelve con upsert destructivo.

Inmutables: todas las filas Hall existentes, archivos de temporada y fuentes League
027–029; futuros certificados y resultados/roster/reglas que los sustentan. Las tablas
Cup legacy **no están globalmente congeladas hoy por 029**: se preservan en esta
auditoría y la implementación debe cerrar sus writes antes de certificar. Entradas
viejas sin evidencia se conservan como legacy/no certificadas, sin recatalogarlas
como nuevos hechos certificados ni borrarlas para superar constraints.

Importación incompleta/ambigua: estado de validación pendiente y diagnóstico preciso
(final inexistente/múltiple, miembros sin UUID, resultado inválido, vínculo season
ausente, etc.). `finished`, `completed`, posición 1 o nombre de campeón no bastan.
No se propone endpoint «poner campeón». Una futura atestación manual de históricos
sería otro contrato y no se exige decidirlo para implementar nuevas Cups.

League archive sigue sin esperar Copa. El `cup_hall_status=pending_cup_api` de un
paquete 029 ya creado **no se actualiza**; Hall Cup posterior, si C3 lo permite, es
artefacto independiente. No modificar Hall League, su checksum ni snapshot fuente.

## 7. Inventario exacto de cobertura

Las etiquetas describen **operaciones**, no porcentajes. Una operación puede tener
tablas y seguir MISSING como API. «Complete» se limita al contrato indicado.

| Estado | Operaciones / capacidades |
| --- | --- |
| **ALREADY COMPLETE** | 026 setup/revisions/receipts admin; 027 open/results/close/correction acotada; 028 bajas permanentes; 029 finish/archive/League Hall/discard de temporada; consumo Store Ban 020–022; 024/025 efectos de canje con sus propias reglas |
| **PARTIALLY COMPLETE** | Lecturas judiciales/Cup mediante views; representaciones de dominio; agregación/congelación de penas en close; elegibilidad cruzada con 028; integración Hall solo para Liga |
| **MISSING** | API/RPC de propuesta/audiencia/voto/resolución/cancelación judicial; efectos judiciales monetarios únicos; autorización/revisión/evento/provenance de sanciones; API de setup/resultados/avance/corrección/certificación Cup; campeón de pareja y Hall por Cup |
| **LEGACY-ONLY** | Workflow del creador/jurado, templates, deducción viva sin ledger, borrado/renumeración de casos; motores suizo/eliminatorio/dobles, manual W/L/pairings, resets, sincronización live de Cup Hall |
| **SCHEMA-ONLY** | Trial lifecycle SQL y votos abstain/other; tipos arbitrarios de penalty y ledger penalty sin emisor; admin penalty sin juicio; Cup status/standings/forfeit/void/dropped/disqualified/manual sin comandos certificados |
| **PRODUCT DECISION REQUIRED** | T1–T5 y C1–C4 de §10; en particular autoridad judicial, electorado, efectos temporales y reversión; scores/corrección/temporada/cancelación de Cup |

No hay endpoint oculto de trials/cups en `app/api/main.py` ni adapter en
`app/repositories/supabase/`; búsquedas cruzadas solo encuentran consumidores de
sanciones en application matchdays. El protocolo genérico de competición no sustituye
puertos tipados. Sin escrituras certificadas tampoco puede considerarse completa
una lectura de readiness que solo inspeccione flags en metadata.

### 7.1 Convenciones del catálogo propuesto

Todos los siguientes contratos son **PROPOSED CONTRACT**, no rutas existentes.
`S=/v1/seasons/{season_id}`, `A=/v1/admin/seasons/{season_id}`; `c` es case UUID,
`u` Cup UUID y `r` ronda/fase UUID futura (no una jornada de Liga).

Perfiles que se aplican a **cada fila** de las dos tablas siguientes:

| Perfil | Actor, security boundary, idempotencia, CAS, locks y rollback |
| --- | --- |
| **READ** | JWT habilitado + autorización del objeto; lectura consistente y saneada. Sin writes/evento/key/CAS/rollback. Admin recibe diagnóstico interno; lector público autenticado solo proyección permitida |
| **J** | Usuario habilitado o admin según fila/T1/T2, derivado de JWT y revalidado en RPC service-only. Key obligatoria; scope actor/season/case/operación/cuerpo semántico. Case revision CAS (crear: revisión de colección/season y número asignado bajo lock). Principal → advisory receipt → season NO KEY UPDATE → players UUID ordenados → días dependientes → caso/jurado/votos/propuestas → revisión/evento privado/receipt. Todo o nada |
| **JS** | J + revalidar ventana, acusado y wallet bajo mismos locks; aplicar penas/ledger/provenance antes de evento/receipt. CAS de case + revisión de efectos/season y del día relevante leídos por cliente/servidor; inputs revalidados para evitar close con evidencia anterior. Mismos órdenes 021–029, ningún wallet antes de season. Fallo en cualquier efecto revierte veredicto y todos los efectos |
| **C** | Admin habilitado (no exige competir), JWT → API → RPC invoker service-only. Key actor/season/Cup/operación/cuerpo; Cup revision CAS (crear: revisión de colección/season). Principal → advisory → season NO KEY UPDATE → players UUID → días de Liga que se deban comprobar → Cup → miembros/rondas/matches ordenados → historial/certificado/Hall → revision/evento admin/receipt. Rollback íntegro |

Replay exacto devuelve receipt original aunque haya cambiado estado después, tras
verificar identidad/autorización del solicitante; no relee sources para inventar
otro resultado. Otra semántica con misma key: conflicto. CAS stale: conflicto sin
retry automático, incremento extra ni efecto parcial. Voto se serializa contra
resolución; si T1 elige mayoría con efectos automáticos, **el voto decisivo usa JS**
y se hace todo en esa transacción. No encadenar voto HTTP y resolución HTTP como
si fueran atómicos.

026 `admin_setup_begin` **exige admin**: no se puede reutilizar sin cambios para
propuestas/votos self-service ni relajar su guard. Crear helper específico con el
mismo orden y namespaces/restricciones equivalentes. Case/Cup revisions y receipts
necesarios no existen hoy. Reusar infraestructura compatible sin acoplar esos CAS
a cambios irrelevantes de config/roster. Nombres/campos exactos se fijarán al implementar.

Evento judicial privado: detalle admin y, si se necesita, proyección autorizada para
actor/partes; nunca pruebas/votos privados en `visibility=public`. Evento Cup público
opcional separado, solo facts saneados. No entrega Discord ni nuevo servicio externo.

### 7.2 Operaciones judiciales faltantes

Las columnas de cada fila más el perfil definen endpoint, actor, precondiciones,
transición, writes, key/CAS/locks, evento, seguridad, efecto histórico, rollback,
carreras y migración. **030** significa candidata futura, no archivo creado.

| ID / endpoint propuesto / perfil | Actor y precondiciones → transición | Writes atómicos y evento propuesto | Historia, carreras, rollback particular, migración |
| --- | --- | --- | --- |
| J1 GET `S/trials`, `S/trials/{c}`; GET `A/trials/{c}/review` — READ | Lector autorizado T5; review admin. Scope season exacto; devuelve estado, revisions, efectos ya aplicados y readiness | Ninguno; consulta caso/votos/penas/provenance bajo permisos | Sin evento/rollback; consistencia frente a voto/resolución concurrentes. DTO/views nuevas dependen de 030 |
| J2 POST `S/trials` — J | Creador JWT; acusado/season válidos, propuesta completa y ventana T3 → proposed | Caso, número estable no reutilizado, revision inicial, `TRIAL_PROPOSED`, receipt | No efecto de pena. Carrera dos números/key duplicada/finish; rollback del número/registro si falla evento. 030 |
| J3 PUT `S/trials/{c}/proposal` — J | Creador o actor aprobado T1; propuesta aún editable, expected_case_revision → nueva revisión de propuesta | Campos permitidos, historial de cambios; `TRIAL_PROPOSAL_UPDATED` | Prohibir body con verdict/applied/state/actor. Carrera editar/iniciar/cancelar; error deja versión previa completa. 030 |
| J4 POST `A/trials/{c}/start` — J | Admin propuesto T1; expediente listo, jurado/quorum T2 → audiencia abierta | Fase, evidencia/roster/quorum congelados, `TRIAL_STARTED` | Ruta bajo S en alternativa de autoridad del creador, nunca guardar dos autoridades distintas. Carrera start/edit/vote; rollback roster/fase. 030 |
| J5 PUT `A/trials/{c}/proposed-sanctions` — J | Admin propuesto T1; aún sin sentencia y antes del punto de congelación de voto elegido; tipos/amount/ventanas válidos | Propuesta versionada, notas, `TRIAL_SANCTIONS_PROPOSED` | No insertar propuestas como penalties efectivas. Carrera voto/resolve: invalida revisión, no cambia pena después de consentirse sin regla. 030 |
| J6 PUT `S/trials/{c}/vote` — J o JS decisivo | Votante propio, audiencia abierta, T2; body vote + expected_case_revision. Proxy, si aprobado: POST `A/trials/{c}/proxy-votes` con miembro/motivo y actor real | Voto único/revisión, quorum derivado, `TRIAL_VOTE_RECORDED`; si auto-resolve T1, también todo J7 | No suplantar actor con trainer_id del cliente; CAS ante votos simultáneos/último voto/close/edición. Rollback voto y sentencia conjunta si falla cualquier efecto. 030 |
| J7 POST `A/trials/{c}/resolve` — JS | Autoridad T1, fase/veredicto/evidencia y penas legalmente configuradas; ventana T3 → resolved culpable / dismissed no culpable con veredicto tipado | Decisión inmutable, penas efectivas, débito ledger único si monedas, ids/source revision de efectos, revisions, `TRIAL_RESOLVED`, receipt | No culpable no aplica propuestas. Culpa sin pena requiere regla coherente con T1, no inferir por lista vacía. Carreras close/purchase/promo/status/finish/vote; rollback en cada pena, ledger, evento y receipt. 030 |
| J8 POST `S/trials/{c}/cancel` — J | Creador/admin según T1/T4, caso sin sentencia efectiva; reason + CAS → cancelled lógico | Historial, cancelación, `TRIAL_CANCELLED`, receipt; conserva número/votos | Nunca DELETE ni renumeración. Cancel/resolve concurrentes, a lo sumo uno. Rollback historial/estado. 030 |
| J9 POST `A/sanctions` — JS, **condicional** | Admin; solo si T1 habilita emisión sin juicio, acusado/season y ventana válidos → efecto certificado | Penas + ledger + fuente administrativa/reason + `SANCTION_ISSUED` | SQL acepta penas sueltas de puntos/monedas, pero no hay flujo legacy equivalente. Store Ban sigue exigiendo caso resolved por 020: no fabricar caso ni ampliar helper por accidente. Si no se aprueba, no endpoint. Carreras/rollback JS. 030 o diferida |
| J10 POST `A/trials/{c}/review-decisions` — JS, **condicional T4** | Admin, resolución existente, evidencia/motivo y revisión; solo efectos prospectivos/compensables aprobados → nueva decisión vinculada | Historial nuevo, compensación firmada ledger si procede, vigencia futura de penas, `TRIAL_REVIEW_DECIDED` | No UPDATE/DELETE de sentencia/ledger/snapshot; no reversión de robo/gift/compras. Carreras compra/close/otra apelación; rollback de compensación y decisión. Requiere soporte explícito del consumidor 020/028; 030 si incluido, otra migración si diferido |

Mapeo de estados propuesto: conservar `status=open` para ambas fases iniciales con
fase tipada; `resolved` solo para decisión culpable aplicable; `dismissed` no culpable;
`cancelled` cancelación sin efectos. Otra representación es posible, pero no puede
cambiar qué entiende 020 por resolved. Guardar veredicto explícito: ni número de
penas ni existencia de payload lo sustituyen. Penas propuestas separadas de las
efectivas; no basta publicarlas anticipadamente y confiar en una UI.

No endpoints de «set points», «set balance», ban de canjes, suspensión, matar Pokémon,
editar snapshot/Hall, borrar juicio resuelto o reactivar participante. No son huecos
que se deban rellenar con un CRUD libre para declarar completa la fase.

### 7.3 Operaciones de Copa faltantes

**031** supone 030 judicial completada antes. Se reservará número real al implementar.

| ID / endpoint propuesto / perfil | Actor y precondiciones → transición | Writes atómicos y evento propuesto | Historia, carreras, rollback particular, migración |
| --- | --- | --- | --- |
| C01 GET `S/cups`, `S/cups/{u}`; GET `A/cups/{u}/readiness` — READ | Lector público autenticado/admin; scope exacto, parent visible | Ninguno; contrato versionado de lados/miembros/fases/resultados/certificación | Readiness diagnóstico, no permiso para finalize sin revalidación. Carrera con resultados/certificación; sin rollback. Views/DTO de 031 |
| C02 POST `A/cups` — C | Admin; season elegible C3; categoría/formato/rules soportados → DRAFT | Cup UUID propio, revision, `CUP_CREATED`, receipt | Varias Cups misma categoría permitidas; nombres no son key. Carrera dos creates/finish/discard season; rollback sin Cup parcial. 031 |
| C03 PUT `A/cups/{u}/setup` — C | DRAFT, CAS; roster activo elegible y lados 1/2 miembros distintos, nombres/orden/reglas válidos | Roster/miembros/rules/seeds como un aggregate, historial, `CUP_SETUP_UPDATED` | Solo reemplazo de preparación aún sin historia. Carrera setup/start/status028; rollback todo aggregate. 031 |
| C04 POST `A/cups/{u}/start` — C | DRAFT listo; revalidar todos los miembros y season C3 → ACTIVE | Reglas/roster congelados, sorteo persistido, fase/ronda/matches iniciales, `CUP_STARTED` | Replays no sortean otra vez. Carrera start/setup/retire; fallo tras match N revierte sorteo/fase entera. 031 |
| C05 PUT `A/cups/{u}/rounds/{r}/results` — C | ACTIVE, ronda editable, winners/scores legítimos C1, CAS Cup y ronda | Resultados revisionados del batch, `CUP_RESULTS_RECORDED` | No acepta standings/campeón certificado. Carrera edits/close/finalize; batch inválido revierte todo. Final usa el mismo contrato de resultados. 031 |
| C06 POST `A/cups/{u}/rounds/{r}/close` — C | Todos los resultados requeridos/byes válidos, fuente de ranking completa | Cierra revisión de ronda, recalcula standings, clasificados/eliminados, genera siguiente ronda/Top4/semis/final; `CUP_ROUND_CLOSED` | Congela entrada/salida de algoritmo; no puntos/economía Liga. Carrera doble avance/results/correction; rollback después de cada fase/dependencia. Final cerrada queda pendiente de certificar. 031 |
| C07 POST `A/cups/{u}/rounds/{r}/correct` — C | ACTIVE no certificada; reason, CAS source, ventana y dependencias C2 | Nueva revisión de resultado/ronda, evidencia anterior retenida; solo derivados futuros seguros; `CUP_RESULTS_CORRECTED` | Rechazo con sucesores jugados si C2=A; no UPDATE de evidencia finalizada. Carrera advance/finalize/correction; rollback exacto de standings/ramas. 031 |
| C08 POST `A/cups/{u}/finalize` — C | ACTIVE con final y recorrido completo; revisión y evidencia autoritativas; C3 → FINISHED certificado | Certificado + snapshot/checksum + winner-side/members + Hall Cup + revision + `CUP_FINALIZED` + receipt | Exactamente una certificación/Hall por Cup; dos admins/keys no duplican. Carreras result/correct/finalize/season archive/status; fallo en certificado/Hall/evento/receipt revierte todo. 031 |
| C09 POST `A/cups/{u}/discard` — C | DRAFT sin historia o ACTIVE solo si C4=A; motivo/confirmación/CAS; jamás certificado → DISCARDED lógico | Estado, razón/evidencia, `CUP_DISCARDED`, receipt; relaciones conservadas | No ganador/Hall; no borrar matches. Carrera start/results/finalize; revisión evita ocultar campeón ya certificado. Rollback estado/evento. 031 |
| C10 POST `A/cups/{u}/archive` — C, **opcional** | FINISHED con certificado; CAS → ARCHIVED | Solo presentación/lifecycle, `CUP_ARCHIVED`, receipt | No nueva certificación/Hall ni cambios de fuentes; carrera mismo archive/lectura; rollback lifecycle. 031 solo si se expone esta acción |

La sincronización Hall pertenece a C08, no a endpoint genérico de rebuild ni
segunda transacción. Si se elige almacenamiento Cup Hall separado, las mismas
garantías y la lectura unificada son obligatorias. No API de importar campeón por
nombre o setear `completed`; tampoco writes directos de standings.

## 8. Restricciones históricas 026–029 y seguridad

### 8.1 Contratos cerrados que condicionan los nuevos writers

- **026**: principal habilitado/admin, namespaces de receipt, hash semántico,
  season/players locks y CAS. No confundir nombre Anto con rol. No romper acceso
  admin sin participación ni replays anteriores.
- **027/028**: las penas/casos/Cups forman parte del hash externo. Emitir/cambiar
  estos datos puede cerrar la ventana de corrección incluso si no afecta el
  resultado; no eliminar entradas del hash para facilitar la nueva API. Cualquier
  Cup de esa season bloquea corrección 027, incluso finished/discarded: es más
  conservador que la dependencia de bajas 028. Nuevas tablas de efecto deben estar
  cubiertas por el hash/contexto o por revisions autoritativas incluidas en él.
- **028**: baja solo ACTIVE + current SCHEDULED, sin Team Lock propio ni otras
  dependencias. Cup draft/active con trainer correspondiente **o lado trainer NULL**
  bloquea; el último caso bloquea conservadoramente incluso a otros jugadores.
  Un equipo de dos no autoriza elegir primer miembro ni aflojar este guard. Al
  añadir members tipados, cualquier adaptación incremental deberá preservar el
  rechazo conservador para Cup legacy sin evidencia. No aplicar disqualify como
  subrutina judicial después de insertar un trial del día: sus propios guards lo
  rechazarían; no bypass ni doble commit encubierto.
- **029**: finish/archive League no espera Cup/Trial; Cup pendiente permanece
  explícita. Hall/archivo no admiten UPDATE efectivo ni con service_role, aunque
  limpieza privilegiada de fixtures puede DELETE. No se ha probado inmutabilidad
  universal de todas las tablas con un comentario SQL. Draft discard bloquea
  dependencias Cup/Trial/penalty; nuevos writers deben tomar season lock también
  para no competir con ese control.

### 8.2 Derechos actuales que siguen siendo un GAP

011 concedió DML a authenticated y lo limitó con RLS. Las revocaciones 026/027/029
se aplican a sus tablas explícitas y **no** cerraron todos los writers siguientes:

| Tabla | INSERT/UPDATE que sigue permitido según migraciones locales | Riesgo concreto al habilitar nueva API |
| --- | --- | --- |
| `trial_cases` | INSERT con created_by=current trainer; UPDATE creador o admin, sin restricción de columnas/fase | Puede crear/marcar resolved o modificar acusado/season/payload sin regla judicial. Un caso usado por penas cambia su aplicabilidad sin transacción de efectos |
| `trial_votes` | INSERT voto propio; UPDATE propio/admin, sin fase/quorum/visibilidad del caso en policy | Votar sobre caso ajeno por UUID o después de resuelto, sin autoridad de jurado ni efecto atómico |
| `penalties` | INSERT/UPDATE admin | Cambia ban/sumas sin ledger, event, CAS ni locks del negocio |
| `cups`, `cup_participants`, `cup_matches`, `cup_standings` | INSERT/UPDATE admin | Salta grafo, validaciones, congelación, miembros y certificado |

No hay policies DELETE para esas tablas en 011: grant DELETE **no implica** borrado
permitido por RLS. No se afirma vulnerabilidad de anon ni nueva explotación remota.
La capacidad heredada es un bloqueo de seguridad para declarar completos los
writers nuevos, documentado sin modificarla durante este audit.

Migraciones futuras deben revocar DML de tabla **y columna**, incluyendo browser
admins, PUBLIC y anon, y garantizar que no hay ruta de view escribible alternativa.
API revalida permisos y SQL invoker de search_path fijo solo ejecutable por
service_role revalida actor, scope, estado y fuentes. Credencial service_role nunca
en React/browser/Launcher; JWT del usuario no se sustituye por API key.

### 8.3 Lecturas y privacidad

`public_trial_cases` expone título/descripción/estado y fechas si payload.is_public
no indica false/0/no; NULL se interpreta público. Omite payload completo.
`current_trial_cases` es invoker: aunque su WHERE incluye público, RLS base limita
filas a creador/ acusado/admin. Un tercero no obtiene pruebas por esa rama pública.
`current_trial_votes` limita a votante/admin. Legacy, en cambio, muestra pruebas y
votos de casos visibles: diferencia real a resolver T5, no simple fallo de UI.

`public_penalties` publica tipo/amount/referencias/fechas incluso si el caso es
privado; no expone payload/notas ni las columnas de ventana añadidas en 020 porque
su SELECT es explícito. Para lectura de efectos se necesita proyección segura de
vigencia/provenance, no abrir payload. Views Cup omiten metadata, por lo que hoy no
pueden mostrar miembros fiables de dobles. 029 preserva filtros de padres descartados;
los nuevos views deben mantenerlos y respetar lecturas privadas históricas.

Revisar definición, invoker/definer, fixed search_path, EXECUTE, table/column DML y
checksums de helpers tocados. Advisor baseline anterior **24 ERROR / 4 WARN / 4 INFO**
se conserva como evidencia 8J, no se consultó de nuevo. Comparar object/finding/severity
en futura entrega, sin modificar vistas 018 ajenas para reducir recuentos.

## 9. Secuencia de implementación, migraciones y pruebas esperadas

### 9.1 Dos fases por dependencia transaccional

**8K.1 — Juicios/sanciones**, después de resolver T1–T5: vocabulario y DTO,
revisiones/decisiones/propuestas, self-service autorizado y resolución oficial,
efectos tipados/ledger, consumo compatible en tienda/cierre y cierre de DML directo.
Completar toda la transacción de sentencia antes de habilitar votos con efectos.
No publicar una ruta que inserte penas a la espera de aplicar dinero más tarde.

**8L — Operación de Copa, certificación y Hall**, después de C1–C4: setup/miembros,
reglas/algoritmos/resultados y avances, corrección acotada, certificado/Hall y
lecturas. Es una fase mayor que «añadir finalize»; puede trabajarse por incrementos
locales de setup → resultados/avance → certificación, pero no declarar completo el
dominio publicando solo el último endpoint.

Motivo de separación: comparten season/player locks y auth, pero no agregados,
máquinas de estado ni efectos. Juicios toca consumers 020/027/028, ledger y carreras
de compras; Copa introduce estructura propia y singularidad/provenance Hall, con
carreras de bracket y de archive. Dos gates independientes reducen alcance de DDL
y permiten validar regresiones de cada dominio sin mezclar decisiones. Ninguna
requiere reabrir 026–029, aunque nuevas migraciones deban adaptar helpers actuales
preservando sus garantías.

No comenzar Phase 9 automáticamente. Cerrar ambas fases y verificar el inventario
de Fase 8; el bono individual D8 sigue diferido y este audit no declara completados
parser, progreso individual, deployment ni migración de datos.

### 9.2 EXPECTED MIGRATIONS — candidatas, ninguna creada

| Futura | Contenido mínimo esperado |
| --- | --- |
| **030** si es la siguiente | Fase/veredicto/revision judicial tipados, identidad/número estable, jurado/votos según decisiones, evidencia de resolución y propuestas separadas; cantidades decimales exactas para puntos manteniendo monedas enteras; efecto/débito con fuente y dedupe; vigencia requerida por T3 y reversión solo si T4 la incluye; RPC/receipts/events/guards y grants. Adaptación incremental de consumers/hashes únicamente donde sea necesaria |
| **031** después de la anterior | Revisiones/reglas y miembros tipados Cup, FKs misma Cup/season, fases/rondas/grafo y resultados completos; certificado/snapshot inmutable y fuente de Hall por Cup/side/members; unicidad compatible con League/legacy; RPC/events/receipts, cierre de writes y proyecciones seguras; adaptación conservadora de dependencia 028 si procede |

No garantizar dos archivos con independencia de las decisiones: si reversión o
cascada amplían el contrato, pueden requerir fase/migración adicional. 001–029 no
se editan; 029 **no se reaplica**. Preflight de datos legacy/V2 antes de introducir
constraints: no rellenar por defecto veredictos, temporadas, ganadores o miembros
que no se pueden probar. Datos incompatibles se conservan y clasifican explícitamente;
la estrategia de compatibilidad no es borrar datos para que aplique el DDL.

### 9.3 EXPECTED TEST / CONCURRENCY / ROLLBACK SCOPE

Se inspeccionó cobertura existente: mayoría/objetos de dominio, Store Ban, snapshot
de penas y límites Hall; no se encontraron suites dedicadas a mutaciones V2 de
Trials/Cup. Los tests legacy de Hall validan limpieza/upsert/Bo3, **no certificación
end-to-end de un campeón**. Los 431 anteriores no prueban estos writers inexistentes.

| Área futura | Pruebas que aportan evidencia necesaria |
| --- | --- |
| Juicios dominio/API | Traducción de estados/votos, incluido `no_culpable`; cantidades 0.5/1.5 exactas, moneda entera y valores finitos; fases, jurado/quorum, cambio/proxy de voto, visibilidad, creación/cancelación/números; culpable sin pena coherente con regla aprobada; scope/actor/body falsos; enabled JWT/admin; DTO 422 separado de conflicto 409 |
| Sanciones | Propuesta no efectiva; sentencia aplica una sola vez; no culpable sin efectos; tipos desconocidos rechazados; Store Ban límites/NULL históricos/resolved_at sin caducidad; penalty sin caso no produce ban; coincidencia acusado/season; monedas debitan una sola vez, saldo insuficiente mantiene reducción íntegra; lectura de puntos no descuenta cada jornada; notas Pokémon no tocan entidad/save |
| Ventanas / historia | Todas las filas de §4.3; pena tras snapshot y final close; finish/archive intactos; 027 usa inputs originales en correct; 028 scheduled dependency/NULL team; no nuevas bajas por juicio; replay de comandos antiguos y revocación prospectiva si se aprueba |
| Cup dominio/API | 2/3/4 y número impar según formato, potencias de 2/byes, autopareja y lados cruzados, miembros repetidos, seed/replay estable; Swiss W/L/Buchholz/topcut y fallback real; Bo3 y final de dobles; resultados incompletos, fase final no única, standings duplicados/inventados; solo avances desde resultados; corrección con dependencias y status C3/C4 |
| Certificado/Hall | Varias Cups misma season/categoría; campeón singles y ambos miembros dobles; final coherente con recorrido; un certificado/Hall por Cup; timestamp/hash/revision estables en replay; null/legacy/ambiguous fail closed; Cup team vacío, sin fallback vivo; Hall/archivo existentes byte-intactos y sin repoblar campos League |
| SQL/security | Nuevas FKs/CHECKs/NULL semantics; RLS reads por actor/privacidad; anon/usuario/admin-browser sin writes de tabla/columna/view ni EXECUTE; invoker/search_path/grants; event/receipt sin datos privados; políticas de padres discarded; columnas añadidas no ganan permiso accidental |

Concurrencia PostgreSQL real, con conexiones/JWT/transports independientes:

1. Dos creaciones/números; edit/start; cambio de propuesta/último voto; votos que
   alcanzan mayoría a la vez; resolve/cancel/review; mismo actor/key/body, key con
   cuerpo distinto, distintos admins/keys. No voto perdido ni doble resolución.
2. Sentencia monetaria/ban contra compra normal, promocional, otro débito y cierre;
   sentencia contra planificación/commit de 027, baja 028, finish/archive 029.
   Resultado serial válido o conflicto, sin compensación inventada ni retry oculto.
3. Dos starts de Cup (un sorteo), dos closes (una siguiente ronda), results/advance,
   correction/advance/finalize, dos finalize con mismos/distintos actores/keys,
   dos Cups misma categoría, discard/finalize, Cup start/028 y finalize/029.

Rollback local por inyección **después de cada punto de escritura**: decisión,
pena N, ledger, provenance/revision, event, receipt; Cup roster/sorteo/match N,
standings/avance, revisión de corrección, certificado, Hall, event, receipt. Comparar
estado completo anterior/posterior, incluidos contadores/revisiones/ledger/artefactos;
no solo status HTTP. No inyección DDL en staging.

Durante desarrollo: `tools/run_unit_tests.py --pattern ...` y runners PostgreSQL
en DBs desechables distintas, según el cambio. Gate final por fase de implementación:
suite completa, compileall, rebuild 001–N, bootstrap **generado** desde migrations,
schema/grants/ownership parity de dumps ordenados (solo normalizar tokens aleatorios
restrict/unrestrict), regresiones compartidas y concurrencia/rollback pertinentes,
`git diff --check`. No repetir el universo por cada edición pequeña.

Staging será otra tarea autorizada de implementación: commit/push verde antes de
incremental DDL, verificar proyecto V2 exacto/history/latest/objetos y baseline real
nuevo; fixtures únicas y cleanup por sus ids. Verificación independiente posterior
de public, Auth users/identities/sessions/refresh_tokens y Storage relevante, además
de Advisor por objeto/finding/severity. Aquí no se ejecutó ninguno de esos pasos.

## 10. PRODUCT DECISIONS REQUIRED

Solo decisiones que cambian comportamiento o resuelven evidencia contradictoria.
No se pide elegir locks, UUID, CAS, servicio SQL, representación física Hall o
tipos numéricos: son responsabilidades técnicas. Todas siguen **pendientes**.

### DECISION T1 — Autoridad de la sentencia y sanciones oficiales

**CONTEXT:** convertir creador/jurado en autoridad que ahora debita dinero real.

**CURRENT EVIDENCE:** legacy da control al creador y mayoría automática; V2 permite
casos del propietario, penas admin y enum ledger sin writer. 026 tiene admin
explícito; no existe contrato aprobado que resuelva esta divergencia judicial.

**OPTION A:** usuarios proponen/votan; admin inicia, valida pena y dicta sentencia
explícita con efectos. Votación es evidencia, no ejecuta el débito. No emisión libre
de sanciones fuera de expediente en la primera versión.

**OPTION B:** conservar cierre efectivo por creador o mayoría; el servidor aplica
reglas y efectos atómicos al voto decisivo. La propuesta de pena debe quedar fijada
antes de votar; no convertir sin más al creador en emisor de cualquier débito.

**OPTION C:** si se necesita realmente, autoridad A más sanción administrativa sin
juicio para puntos/monedas/notas, con motivo/provenance; Store Ban sigue vía caso.

**TECHNICAL CONSEQUENCES:** A usa JS admin en J7; B también necesita JS en J6,
permisos judiciales propios y reglas coherentes para mayoría culpable sin castigo;
C habilita J9. Ninguna autoriza browser DML.

**RECOMMENDATION:** A, conservando propuestas y votos como participación. Es un
cambio respecto al flujo legacy, no se presenta como ya aprobado.

### DECISION T2 — Quién forma el jurado y si se admite voto delegado

**CONTEXT:** un tamaño numérico no identifica electorado legítimo.

**CURRENT EVIDENCE:** legacy admite cualquier usuario que vea el caso, creador por
terceros, voto modificable y sin tope real; `public_vote` es informativo. Dominio
solo cuenta votos; SQL añade abstain/other sin regla de quorum.

**OPTION A:** lista nominal de 3/5/7/9 personas fijada al abrir audiencia, mayoría
del tamaño fijado, voto propio modificable hasta sentencia; sin proxy en primera
versión. Creador y acusado excluidos del jurado.

**OPTION B:** votación abierta a lectores habilitados con umbral configurado como
legacy; creador puede registrar voto de terceros identificado como delegado y con
actor real. Sin afirmar que ese umbral limita el número de votantes.

**TECHNICAL CONSEQUENCES:** A requiere members y comprobar quorum posible; B exige
reglas explícitas de proxies, cambios, carrera de mayorías y elegibilidad. En ambas,
solo guilty/not_guilty inicialmente; no atribuir significado a otros enums SQL.

**RECOMMENDATION:** A; si no hay suficientes elegibles, no abrir audiencia. No
reducir jurado ni aceptar al acusado automáticamente para hacer pasar readiness.

### DECISION T3 — Cuándo entran en vigor las sanciones

**CONTEXT:** legacy mezcla efecto monetario inmediato y puntos del último snapshot;
no existe vigencia judicial season-scoped completa.

**CURRENT EVIDENCE:** 020 ya acepta ban sobre pointer SCHEDULED/OPEN/CLOSED;
027 congela agregados y no descuenta premios; 029 cierra League sin esperar casos.
No hay escritor que decida qué hacer con sentencia durante OPEN o tras último close.

**OPTION A:** sentencia efectiva durante temporada ACTIVE: monedas/ban desde commit;
puntos como deducción acumulada, una vez en la proyección de total, desde la próxima
captura de una jornada aún no cerrada (incluida OPEN). Sin jornada futura válida,
rechazar nuevas penas de puntos. FINISHED/ARCHIVED conservan consulta/pendientes,
sin nuevas sentencias con efectos en la primera versión.

**OPTION B:** todas las nuevas sanciones competitivas entran solo en una jornada
SCHEDULED posterior; resolver durante OPEN requiere guardar decisión pendiente de
efectividad. Sin jornada posterior quedan pendientes, nunca retroactivas.

**TECHNICAL CONSEQUENCES:** A necesita vigencia/provenance y proyección acumulada
sin tocar positions/Hall; B además necesita activación futura inequívoca de efectos
y economía. En ambas, scope diario/temporal y terminación deben distinguirse del
matchday del hecho acusado; no usar las ventanas de ban como ventanas de puntos.
Una transacción con pena no aplicable falla completa, no omite esa pena en silencio.

**RECOMMENDATION:** A por cercanía a efectos legacy y menor mecanismo de pendientes.
La recomendación no cambia el campeón 029 ni introduce sentencias económicas después
de finish. Si se desea esa capacidad tardía, necesita aprobación adicional explícita.

### DECISION T4 — Rectificación o cancelación después de sentencia

**CONTEXT:** eliminar caso resuelto legacy puede deshacer deducciones vivas sin
compensar historia; V2 ya tiene ledger y snapshots irreversibles por CRUD.

**CURRENT EVIDENCE:** `delete_case` admite cualquier fase; el repo también edita
campos terminales. No hay apelación tipada, deuda compensada ni cascada soportada.

**OPTION A:** primera versión permite cancelar solo casos no resueltos; sentencia
y efectos terminales no tienen editor/cancelación. Error posterior queda pendiente
de procedimiento excepcional, sin afirmar que existe reversión.

**OPTION B:** revisión admin explícita desde primera versión, nueva decisión y
efectos prospectivos/compensaciones monetarias trazables; historia anterior conservada.
No reabrir rounds ni recuperar compras/gifts ya usados.

**TECHNICAL CONSEQUENCES:** B exige J10, links de revisión, guards de vigencia y
consumidores que distingan efecto vigente de evidencia antigua; no basta cambiar
`resolved_at`, que 020 no interpreta como cese. A acota fase/migración y retira el
borrado terminal legacy del producto soportado.

**RECOMMENDATION:** A para el primer contrato seguro; B solo con reglas precisas de
compensación/vigencia acordadas antes de habilitarla. No dejar un PATCH alternativo.

### DECISION T5 — Publicidad de pruebas y votos

**CONTEXT:** los lectores autorizados difieren entre legacy y V2.

**CURRENT EVIDENCE:** legacy expone pruebas/votos a lectores del caso y privado
solo al creador; V2 protege payload para creador/acusado/admin y voto para votante/admin,
con resumen público. `public_vote` no cambia permisos en legacy.

**OPTION A:** conservar privacidad V2: pruebas para partes/admin, votos individuales
para votante/admin; resumen público saneado y resultado final. Miembros del jurado
aprobado acceden por API a la evidencia necesaria del caso, no por abrir todo payload.

**OPTION B:** casos públicos muestran también pruebas y votos nominales como legacy;
casos privados restringidos con acceso explícito de partes/jurado/admin. Requiere
consentir esa publicación como contrato, sin inferirla de `is_public` antiguo.

**TECHNICAL CONSEQUENCES:** A requiere lectura de evidencia por jurado T2 con permiso
del caso; B cambia proyecciones/exposición pública. Revisar conjuntamente sanciones
públicas que referencian caso privado, sin volcar notas ni archivos sensibles.

**RECOMMENDATION:** A. No convertir una proyección safe-by-shape en SELECT payload
por comodidad del frontend. No cambio de privacidad en esta auditoría.

### DECISION C1 — Marcador oficial de «Torneo Bo3»

**CONTEXT:** nombre del formato y validación eliminatoria se contradicen.

**CURRENT EVIDENCE:** UI dice Bo3 pero admite cualquier score desigual 0..99;
dobles sí limita a cuatro resultados Bo3. Swiss registra ganador sin score.

**OPTION A:** eliminación y dobles exigen 2–0/2–1/1–2/0–2; Swiss mantiene ganador
sin inventar un marcador que legacy no guardó.

**OPTION B:** eliminación conserva score libre sin empate, con esa regla explícita
versionada; no certificarla ni presentarla como Bo3 estricto.

**TECHNICAL CONSEQUENCES:** cambia validación de C05/C08 y admisibilidad de históricos.
Un resultado legacy incompatible permanece no certificado, sin normalizarlo a 2–1.

**RECOMMENDATION:** A; confirmar la regla deportiva, no deducirla del control defectuoso.

### DECISION C2 — Ventana de corrección de Copa

**CONTEXT:** editar una ronda anterior puede cambiar finalistas y campeón.

**CURRENT EVIDENCE:** legacy permite edición amplia sin reconciliación transaccional;
dobles limpia final solo al cambiar lados/incompletitud. No hay historial certificado.

**OPTION A:** corregir con revisión/motivo antes de certificar y solo sin resultados
dependientes; se pueden reconstruir sucesores preparados pero no jugados conservando
evidencia. Si hay resultados posteriores, conflicto explícito.

**OPTION B:** permitir corrección tardía antes de certificar con invalidación expresa
de partidos/resultados descendientes y nueva disputa; exige política de comunicación
y aceptación del alcance. Nunca modificar Cup ya certificada ni Hall existente.

**TECHNICAL CONSEQUENCES:** A permite grafo y rollback acotados; B necesita motor de
invalidaciones, revisiones en cascada y pruebas considerablemente mayores.

**RECOMMENDATION:** A. No reconstruir en silencio una rama jugada ni copiar la
restricción 027 a Copa sin comprobar sus propias dependencias.

### DECISION C3 — Copa pendiente cuando Liga termina o se archiva

**CONTEXT:** 029 permite archivar Liga aunque Cup esté pendiente; falta lifecycle
propio de Cup que diga si puede continuar después.

**CURRENT EVIDENCE:** Copa legacy es independiente; V2 permite Cup de season
finished/archived estructuralmente, pero no tiene writer autorizado. Archivo 029
declara pending_cup_api y no puede cambiarse después.

**OPTION A:** permitir continuar y certificar una Cup ya iniciada después del
finish/archive de Liga, en sus propias tablas/artefactos; no crear nuevas Cups de
esa temporada terminada ni editar datos/archivo/Hall de Liga.

**OPTION B:** prohibir nuevas operaciones Cup al terminar Liga; Cups incompletas
quedan pendientes sin campeón. No bloquear/revertir retroactivamente finish 029.

**TECHNICAL CONSEQUENCES:** A requiere guards por lifecycle Cup y resultado serial
frente a archive; su Hall se añade por Cup como artefacto separado. B necesita
mostrar pending y no afirmar que hay forma normal de completarla después.

**RECOMMENDATION:** A por separación ya observada y porque League archive no espera
Copa. No permite reabrir Cup certificada/archived ni completar históricos ambiguos.

### DECISION C4 — Cancelar una Copa activa sin campeón

**CONTEXT:** los resets legacy permiten abandonar torneos iniciados, pero destruyen
datos y no son una operación portable.

**CURRENT EVIDENCE:** `cups.discarded` existe solo como estado; 028 bloquea bajas por
Cups draft/active y no define cómo desistir de ellas. No premios Cup que reembolsar.

**OPTION A:** admin puede descartar lógicamente Cup no certificada con motivo,
confirmación/CAS, preservando resultados y marcándola sin campeón/Hall nuevo. Una
nueva edición recibe otro Cup UUID. Sin retirada individual/forfeit inventado.

**OPTION B:** solo se descarta DRAFT sin historia; la activa debe completarse o
quedar pendiente de procedimiento excepcional, conservando bloqueos de 028.

**TECHNICAL CONSEQUENCES:** A amplía C09; la Cup discarded deja de ser bloqueo
draft/active de 028, pero **sigue** bloqueando corrección de Liga 027 como cualquier
Cup existente. B es más pequeño pero no reemplaza el reset activo legacy.

**RECOMMENDATION:** A, sin borrar historia ni deducir ganador por abandono.

## 11. Validación y entrega de esta auditoría

Alcance exclusivo: este documento y referencia mínima en `project-checkpoint.md`.
No se ha ejecutado runtime, parser, PKHeX, SQL, bootstrap, fixtures, servidor local
ni acceso a Supabase. No credenciales leídas, cambios de dependencias o mensajes externos.

Validación ejecutada: inspección estática de fuentes/contratos/tests; **43 enlaces
locales válidos**, inventario AST de **30 rutas decoradas sin rutas Trial/Sanction/Cup**,
**29 migraciones** hasta 029 y ninguna 030. El script solo leyó archivos, sin importar
runtime. Diff de `app/`, `supabase/`, `tools/`, `tests/` contra HEAD inicial vacío;
SHA256 de guía igual al inicio. `git diff --check` PASS. El gate de index usa además
`git diff --cached --check` y verifica exactamente los dos documentos autorizados.
Los resultados Git concretos se reportan tras commit/push, sin insertar en el archivo
su propio hash. No se vuelve a ejecutar la suite completa ni se atribuye un nuevo
PASS a los 431 tests históricos. El runner aislado se leyó para documentar el gate futuro.

Commit normal previsto: `docs: audit remaining trials and cup api gaps`.
Staging explícito de los dos Markdown; push normal, sin amend/rebase/force ni guía.
La auditoría puede entregarse con las decisiones anteriores pendientes porque no
las transforma en contrato implementado. Siguiente tarea: resolver decisiones y
autorizar una implementación concreta. **No se inicia automáticamente.**
