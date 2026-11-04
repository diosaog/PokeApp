# Puntos desde evidencia observada, sin confirmación — 2026-11-04

Estado: CAMBIO PREPARADO Y PROBADO LOCALMENTE; NO PUBLICADO.
Rama `codex/automatic-observed-points`, desde `87d56b7`.
Estado de esta intervención: `STAGING_UNTOUCHED`, salvo consultas de lectura.

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
Es una propuesta de función, aplicada únicamente al PostgreSQL local de prueba;
no se ha creado ninguna migración nueva en `supabase/v2/migrations`, alterado
001–080, añadido un UPDATE de cuentas ni aplicado SQL remoto.

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

## Autorización pendiente y siguiente paso

La petición anterior excluía explícitamente «New SQL migrations without further
approval». Por ello no se aplica esta función a producción ni se publica una
web que prometa puntos automáticos contra el SQL antiguo. La autorización
pendiente es del despliegue SQL por el propietario, nunca una confirmación de
los jugadores.

Tras autorizar esa corrección SQL: formalizar una migración con esta función,
ensayar con respaldo fresco 080, aplicar una vez y publicar solo la web; API y
Launcher no necesitan versión nueva. Comprobar mediante lecturas los saldos
automáticos y ausencia de cambios en datos existentes. No hacer correcciones
individuales, Team Locks, monedas, pastes o mensajes de prueba. Discord por
versión continúa fuera de este cambio y pendiente de su autorización separada.

Última publicación registrada: web `4f46cbcb`, API `adfca5c4`, DB 080. Esta
rama preparada debe continuarse desde su tip; no desplegarla ignorando el gate
SQL. MultiIA actualizado; guía protegida y archivos del propietario excluidos.
