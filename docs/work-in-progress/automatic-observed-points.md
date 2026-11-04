# Puntos desde evidencia observada, sin confirmación — 2026-11-04

Estado: PUBLICADO Y VERIFICADO. `STAGING_DONE_ZERO_RESIDUE`.
Rama `codex/automatic-observed-points`, desde `87d56b7`.
081 aplicada UNA VEZ: `20261104165722`. No reaplicar.
Web `0eef4feb` al 100%; saldos reales leídos: Samu 0, Iker −0,3.

El propietario aclara que los jugadores no deben confirmar el historial para
obtener puntos. La app debe usar automáticamente la partida oficial y los
registros disponibles. Esta instrucción sustituye el requisito funcional de
confirmación descrito en el informe anterior. No se inventa historia ausente.

## Evidencia y cambio concreto

Antes de publicar, `league_death_totals` mostraba en Samu e Iker `valid=true`,
fuente completa aceptada, contador wipe 0/revisión 0 y respectivamente 0 y
3 eventos efectivos de muerte. El bloqueo es solo
`death_history_baseline_required`; no falta sincronizar sus partidas.
Con los resultados y sanciones comprobados, los saldos son **0 y −0,3**.

La 081 cambia exclusivamente la función SQL de lectura
`league_death_totals(uuid)`. Usa eventos efectivos + offsets ya auditados y el
contador wipe vigente, sin esperar campos de confirmación del jugador. Una
fuente ausente/incompleta, salto de observación, identidad ambigua o contador
inconsistente sigue siendo desconocida; no se convierte en cero. Conserva las
correcciones 077, la deduplicación y la exclusión de muertes anteriores al alta
080. Los snapshots cerrados y el cálculo de victorias/sanciones no se modifican.

[Diff SQL revisable](../evidence/automatic-observed-points/candidate.diff).
La propuesta se probó primero sin crear una migración ni tocar producción.
Tras la autorización posterior se formalizó como 081, sin alterar 001–080 ni
añadir UPDATE de cuentas. La función coincide exactamente con ese diff.

La web publicada elimina el aviso y enlace de confirmación de Home, el botón
y diálogo del historial y la acción inline de Liga. Mantiene diagnósticos de
fuente ausente/inconsistente, los sprites y los datos auténticos. API compatible:
su lectura ya acepta recuentos conocidos con `confirmed_at=null`. No se inventan
confirmaciones, receipts, saldos o registros históricos.

## Verificación focalizada

Windows/.venv-api, PostgreSQL 17 desechable en loopback, base 001–080; después
se reemplazó temporalmente una función como `postgres` sin superusuario.
Fixtures de `tools.validate_phase079_all_vs_all` y helpers 080. Ejecución inline
local, sin conexiones remotas ni archivos de partidas reales.

- **13 SQL PASS**: reproduce el fallo anterior; NET automático 0/−0,3;
  siete tablas relevantes idénticas después de las lecturas; ninguna fecha de
  confirmación fabricada; readiness sin confirmación; offset previo conservado;
  muerte posterior una vez; wipe automático; entrada 080 a cero; fuente ausente,
  intervalo sin evidencia y contadores inconsistentes siguen desconocidos; ACL
  service-only conservada. [Resultados](../evidence/automatic-observed-points/sql.json).
- **66 web PASS**, cinco archivos: Home, historial, jornada, perfil y sprites.
- **10 API PASS**, `tools/run_unit_tests.py --pattern test_api_league_start.py`:
  incluye lectura conocida de cero sin confirmación humana ni timestamp.
- Build TypeScript/Vite con API de producción PASS; solo artefactos locales.
- **1 Playwright PASS** contra ese build: puntos 0 sin botones ni escrituras
  competitivas, Home sin etiqueta de forma y Gourgeist forma 2 correcto.
  API sintética interceptada. El primer assert incluía la renovación normal de
  autenticación; se corrigió para comprobar las escrituras competitivas, sin
  cambiar el producto. Servidor y navegadores cerrados; cluster eliminado.
  [Captura local sintética](../evidence/automatic-observed-points/home-local-synthetic.png).

## Publicación autorizada

El propietario respondió **«si»** a la autorización concreta de esta función
SQL y la web, sin modificar partidas, monedas o historiales. La restricción
anterior de nuevas migraciones queda ampliada únicamente para este cambio.
No se requiere otra autorización para completar esta publicación.

081 `081_automatic_observed_points.sql` solo sustituye la función de lectura,
con guard de la definición previa; conserva owner/ACL y no modifica tablas.
SHA-256: `06f9c9911a3c375d67f793e5189ef7d3dc772bc01dd8cb348e9bcad3fba0d7c0`.
Bootstrap regenerado 001–081, runner fijado a esos bytes y ensayo focalizado
reproducible en `tools.validate_phase081_observed_points`. La 081 completa
supera 13 comprobaciones SQL, incluida apertura normal J1 sin confirmar
historiales; 15 tests de esquema y 6 gates del runner PASS. Build web repetido PASS.
Proyecto remoto correcto ACTIVE_HEALTHY, historial hasta 080, función anterior
con hash esperado; API `adfca5c4` SUCCESS y web `4f46cbcb` al 100%.

## Resultado remoto, respaldo y cierre

Fuente comprometida/publicada: `add17d386bcfb5759cc678ddc485a26e6860b8f9`,
que incluye la preparación `617a570`. SQL 081 registrada una sola vez como
`20261104165722`, a las 16:57 UTC. Web Cloudflare
**`0eef4feb-835c-4203-b581-ed1bd9692586` al 100%**, despliegue
`526a4fff-2399-4e8a-9024-1f2811845ca7`, 16:58:47 UTC.

Respaldo fresco 080: `pre-release-20261104T165409Z.dump`, capturado 16:54:41
UTC, SHA-256 `161a1e54372e172d94a9a9437952a8c73fd83acf0d4881164beb841312eede1e`.
Privado en `%LOCALAPPDATA%/PokeApp-migration-evidence/automatic-observed-points-081`.
Ensayo **17/17 PASS**, 126 tablas restauradas, 104 tablas de datos idénticas,
116 lecturas de compatibilidad iguales, 13 checks funcionales 081 PASS,
fixtures revertidos y catálogo igual a 001–081. Preflight sin problemas.
El primer intento de preparar la conexión del respaldo falló antes de crear
archivo o ejecutar migración; un reintento secuencial permitió capturar el
respaldo fresco. No se reutilizó un archivo anterior como gate.

Verificación remota 16:58 UTC: **Samu 0 puntos / 4 monedas / 0 muertos;
Iker −0,3 / 8 / 3**. Ambos `known=true`, `can_confirm=false`, `confirmed_at=null`
y `actual_offset=null`: no se simula ni registra una confirmación humana.
La respuesta real valida contra los modelos de la API existente. Las 104
tablas mantienen sus huellas antes/después; no hay cambios de filas. Función
exacta, STABLE/invoker, owner postgres y ACL service-only conservados. Advisor
antes/después: 24 ERROR / 6 WARN / 232 INFO, ningún hallazgo nuevo o resuelto;
los anteriores no se declaran corregidos.

Verificación web 17:00 UTC: index/chunks idénticos al build, controles manuales
ausentes y **1 Playwright PASS** sobre la web publicada, con API interceptada
y equipo sintético. API `adfca5c4` SUCCESS, health 200, 132 rutas; verifier
`2853bbc4` SUCCESS. Launcher 0.26.11, feed idéntico e instalador con mismo
tamaño/ETag. No se publican API, verifier o Launcher ni se cambia su optimización.
[Evidencia saneada](../evidence/automatic-observed-points/release.json),
[captura publicada sintética](../evidence/automatic-observed-points/home-hosted-synthetic.png).

Runner actualizado a 001–081 desplegadas y ninguna pendiente. Backup,
preflight, intent/result, Advisor y huellas quedan en el directorio privado;
logs transitorios en TEMP. Clusters y navegadores de pruebas cerrados. Sin
datos de prueba remotos, Team Locks, pastes, envíos Discord o ajustes individuales.
Discord por versión sigue pendiente de autorización separada.

Continuar desde el tip de `origin/codex/automatic-observed-points`. El commit
de cierre solo actualiza registros, evidencias y plan operativo. Rollback web:
`4f46cbcb-c83c-4d97-96dd-56dc4bc3b714`; SQL por fix-forward conservando la
historia, sin restaurar cuentas o partidas para revertir una función de lectura.
MultiIA actualizado; guía protegida y archivos del propietario excluidos.
