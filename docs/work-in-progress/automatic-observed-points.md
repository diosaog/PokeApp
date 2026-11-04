# Puntos desde evidencia observada, sin confirmación — 2026-11-04

Estado: PUBLICACIÓN SQL + WEB AUTORIZADA Y EN CURSO.
Rama `codex/automatic-observed-points`, desde `87d56b7`.
Estado de esta intervención: `STAGING_UNTOUCHED`, salvo consultas de lectura;
081 formalizada, respaldo fresco en curso. No se ha aplicado SQL remoto todavía.

El propietario aclara que los jugadores no deben confirmar el historial para
obtener puntos. La app debe usar automáticamente la partida oficial y los
registros disponibles. Esta instrucción sustituye el requisito funcional de
confirmación descrito en el informe anterior. No se inventa historia ausente.

## Evidencia y cambio concreto

Lectura actual de `league_death_totals`: Samu e Iker tienen `valid=true`,
fuente completa aceptada, contador wipe 0/revisión 0 y respectivamente 0 y
3 eventos efectivos de muerte. El bloqueo es solo
`death_history_baseline_required`; no falta sincronizar sus partidas.
Con los resultados y sanciones comprobados, los saldos son **0 y −0,3**.

La propuesta cambia exclusivamente la función SQL de lectura
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

La web preparada elimina el aviso y enlace de confirmación de Home, el botón
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

Siguiente paso autorizado: ensayar con respaldo fresco 080, aplicar una vez
solo 081 y publicar la web; API y
Launcher no necesitan versión nueva. Comprobar mediante lecturas los saldos
automáticos y ausencia de cambios en datos existentes. No hacer correcciones
individuales, Team Locks, monedas, pastes o mensajes de prueba. Discord por
versión continúa fuera de este cambio y pendiente de su autorización separada.

Última publicación registrada: web `4f46cbcb`, API `adfca5c4`, DB 080. Esta
rama debe continuarse desde su tip; no desplegarla ignorando el gate SQL.
MultiIA actualizado; guía protegida y archivos del propietario excluidos.
