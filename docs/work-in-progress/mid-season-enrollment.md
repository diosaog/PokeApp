# Incorporación durante ChampionsLocke — registro de continuidad

Estado: PUBLICADA (2026-11-04); comprobaciones técnicas del despliegue PASS.
Estado remoto: VALIDATION_PARTIAL, limitado a la comprobación autenticada con
sesiones legítimas y al primer uso real, pendientes como se detalla abajo.
Fecha: 2026-11-04. Rama `codex/mid-season-enrollment`, desde
`c2e86170d5a70d0974a3d598755bc33a7ba8ee9f`. El commit `332a01d` agrupa
implementación, pruebas y evidencias iniciales. Al cerrar esa implementación
todavía no había push ni cambios en producción; la publicación posterior
autorizada se registra a continuación.

Referencias: [MultiIA](../AI/PokeApp_Multi_AI_Continuity_Protocol.md),
[checkpoint](../project-checkpoint.md), [publicación 079](all-vs-all-league-start.md),
[fix independiente Pokepast.es](public-pokepaste-format.md).

## Publicación autorizada y verificación remota

El propietario autorizó explícitamente SQL 080 + API con CRLF + web al
responder «si» a la solicitud final. No se volverá a pedir la misma autorización.
Se mantiene la prohibición de altas, créditos, cruces, Team Locks y pastes
artificiales sobre datos reales durante las verificaciones.

Estado remoto comprobado antes de publicar: Supabase V2 correcto y saludable,
historial hasta 079; 080 ausente. Cero jornadas abiertas, reservas de entrega
u operaciones físicas pendientes. API `ef13a7ce` SUCCESS, 131 rutas; web
`a81eb04f-ae65-4f53-821b-14e201a0a8ad` al 100%. Son los objetivos de rollback.
Respaldo fresco capturado a las 15:31:34 UTC en el directorio privado
`%LOCALAPPDATA%/PokeApp-migration-evidence/mid-season-080-release`:
`pre-release-20261104T153100Z.dump`, SHA-256
`6cfe1e93e615ce88cc6e6e00aa4b59ffa9de1712e21374c74bb383151d68559e`.
Ensayo exclusivo 079 → 080: **17/17 PASS**, 125 tablas restauradas,
103 tablas anteriores idénticas, 116 lecturas iguales y catálogo igual a
001–080. El preflight no presentó problemas; la compra pendiente era inventario
sin usar y se conservó. No reaplicar 079. 080 se aplicó UNA VEZ:
versión `20261104153603`; no reaplicar.
Validación de base completada: 103 tablas anteriores idénticas, cero altas,
RLS/FORCE RLS y ACL service-only verificadas; RPC visible en la caché PostgREST.
Advisor: 24 ERROR/6 WARN anteriores, ningún hallazgo nuevo de esos niveles;
INFO 229 → 232. Los avisos anteriores se conservan, no se declaran resueltos.

API **SUCCESS**: `adfca5c4-fb5e-4739-a239-b08ccfbb92c2`, creada a las
15:37:16 UTC desde el bundle de `6490e3de84c575a771348c26c9fe0d0544aa6b14`
(346 archivos permitidos, solo fuentes comprometidas). Contiene la
implementación `332a01d` y el fix CRLF `c2e8617`. Health 200, OpenAPI 200,
**132 rutas / 55 operaciones administrativas autenticadas**, GET/POST nuevos
y cuerpo estricto verificados. GET y POST anónimos y con bearer inválido:
401. CORS de la web permitido; origen ajeno rechazado. POST sin identidad
se rechazó antes de ejecutar ninguna escritura.

Web **100%**: versión `82349ea3-0afd-4757-847e-144f7d32040f`, despliegue
`329cd675-112a-481d-9b28-0beb1f5b9881`, publicado a las 15:43:35 UTC.
Build con API de producción, dry-run y publicación correctos. Once
comprobaciones remotas PASS: index y JavaScript idénticos al build local,
chunk administrativo con incorporación, rutas SPA, configuración API, CSP,
feed firmado e instalador del Launcher. El primer sondeo seleccionó por
error el chunk admin-accounts; se corrigió la selección del comprobador y
pasó sin modificar el producto.

Launcher **0.26.11**: mismo feed byte por byte, firma Ed25519 válida e
instalador con el mismo tamaño/ETag. Verifier `2853bbc4` continúa SUCCESS,
sin nuevo despliegue. Comprobación final 15:45:35 UTC: una sola entrada 080,
**cero incorporaciones** y API SUCCESS. No se crearon cuentas ni fixtures
en producción. La tabla y el RPC nuevos siguen sin acceso anon/authenticated.

La verificación autenticada del preview administrativo y del 403 de un
participante no se ejecutó en producción: no se suplantaron identidades.
Esas protecciones y la confirmación completa están probadas localmente con
fixtures; las capturas de este informe son sintéticas. Primera incorporación,
sincronización inicial y entrega Team Lock/Discord/Pokepast.es quedan al uso
legítimo de los usuarios. No se presenta ese uso como verificado remotamente.

[Evidencia saneada de publicación](../evidence/mid-season-enrollment/release.json).
Los originales privados conservan capture/rehearsal/preflight, intent/result,
huellas anteriores/posteriores, Advisor y aceptación API/web. El plan del runner
ya marca 001–080 desplegadas y ninguna pendiente; dry-run sin escrituras:
`to_apply=[]`, `problems=[]`. Sus seis tests de gates vuelven a pasar.
La rama está publicada en `origin/codex/mid-season-enrollment`; continuar
desde su tip. El commit de cierre solo actualiza registros y el plan operativo,
sin cambiar los bytes 080 ni el código de producto desplegado desde `6490e3d`.

También se corrigieron los signos de interrogación que sustituían acentos
por la codificación de la tubería PowerShell/Python al escribir este informe.
El archivo se ha vuelto a verificar como UTF-8; no cambia código del producto.

## Git y Pokepast.es

Git se comprobó antes de cambiar nada: origin/claude/all-vs-all-league-start
seguía en `16708e9`; `c2e8617` es su descendiente directo. Ese commit conserva
la corrección CRLF y puede desplegarse por separado solo con API. Su transporte,
exportador privado, URL guardadas, snapshots y cola Discord no se han modificado.
Las pruebas públicas (24) y del exportador privado (26) siguen en la regresión.
Los archivos no versionados del propietario quedan excluidos. La guía protegida
no se ha leído, buscado, copiado, movido, calculado su hash, editado ni añadido al índice.

## Operación y reglas

Administración → temporada seleccionada → Entrenadores → Añadir entrenador.
Se selecciona una cuenta existente, habilitada y autenticable, todavía ajena a
la temporada. Se reutilizan cuentas/invitaciones y no se conceden privilegios
administrativos. La ruta de altas en borrador conserva su comportamiento.
La nueva operación exige administrador y temporada activa moderna todos contra
todos; rechaza formatos incompatibles, cierres no demostrables y campeonatos finalizados.

La previsualización del servidor muestra cero puntos, jornadas oficialmente
cerradas, monedas exactas, jornada de entrada y cruces nuevos. Confirmar solo
acepta entrenador y hash de esa previsualización. Los cambios en resultados,
jornada, configuración, cuentas o plantilla invalidan el hash. Una respuesta
incierta conserva la solicitud y clave de idempotencia existentes.

- NET oficial inicial exactamente cero: sin victorias, derrotas, puntos ni
  muertes anteriores inventadas. Sin fuente oficial, la historia/progresión
  puede seguir pendiente según el contrato previo; no se adivina un estado del save.
- Monedas iniciales: suma de la recompensa común configurada en cada snapshot
  de jornada realmente cerrada. La abierta no cuenta y no se usa su número
  como multiplicador. Casos 0/10/20 y recompensa configurable de 17 probados.
- Crédito `enrollment_credit`, ligado a incorporación, entrenador, temporada,
  administrador y evidencia de los cierres incluidos. Índice único, transacción,
  receipts y locks impiden duplicarlo. Cero monedas se audita sin ledger de importe cero.
- La primera observación oficial fiable liquida por cero las medallas y el
  campeonato ya presentes. Dos medallas iniciales no dan ocho monedas; la
  tercera nueva da cuatro una vez. Ocho medallas más campeonato iniciales
  producen nueve claims de importe cero. Los nuevos hitos posteriores usan
  la función original; los participantes existentes conservan sus créditos.
- Entrada en la jornada abierta o siguiente preparada/no preparada. Sin J1,
  se incorpora a su preparación normal. Sin participación retroactiva ni reaperturas.

Una Liga de cinco pasa a seis con cinco cruces nuevos, quince en total. Se
insertan solo parejas del reción llegado: los combates anteriores conservan
identidad, resultado y metadatos. Los nuevos pendientes bloquean el cierre.
Se incrementan las revisiones para invalidar resultados/cierres previsualizados
con la plantilla anterior. Si compiten cierre y alta, solo una operación confirma.

Las configuraciones utilizadas y snapshots originales no se editan. Una
proyección amplía las posiciones elegibles conservando recompensa común y reglas.
Los límites de incorporación excluyen al nuevo entrenador de jornadas anteriores.
El cierre sigue por victorias, menos muertes del segmento y 1v1 explícitos;
Blindar/Robar y campeón por NET acumulado conservan sus funciones. El reción
llegado cobra la recompensa ordinaria de su primera jornada al cerrarse,
sin volver a pagar los cierres usados para el crédito inicial.

## Partida, muertes y Team Lock

La partida oficial se registra mediante Launcher con las validaciones existentes
de identidad, propietario, temporada y revisiones. La primera fuente completa
aceptada establece una base explícita auditada. Sus eventos de muerte se conservan
con procedencia, anteriores a esa base; no se fabrican penalizaciones retroactivas.
Las observaciones posteriores usan seguimiento, ciclos de vida y deduplicación normales.

**Límite de evidencia:** sin observación inicial no puede fecharse una muerte o
medalla en el intervalo no observado. Se debe sincronizar la partida oficial
antes de continuar la progresión de Liga. La evidencia inicial de muertes se
conserva para revisión histórica administrativa; no se asignan fechas ni se borra
historia auténtica. Este límite se explica en la confirmación del alta.

Si la jornada ya empezó se añade solo la captura del nuevo participante;
las capturas y períodos de los demás no cambian. Las muertes posteriores cuentan
para NET y mantienen la separación previa entre progresión y combates para el
desempate. Dos muertes reales, una revivida tras wipe, son tres décimas en total,
sin cobro doble. La conciliación histórica administrativa respeta la nueva base.

Team Preview utiliza al participante y su equipo sincronizado por las vías
existentes. Puede fijar equipo en la jornada actual sin participación anterior.
Su Team Lock usa Discord/Pokepast.es existentes: una fila, reemplazos como
revisiones y la misma privacidad. El nuevo participante registra resultados
mediante el endpoint normal, sin permisos de administración.

## Implementación y seguridad

- 080: `league_enrollments` privado con RLS y FORCE RLS, datos base inmutables,
  crédito único, preview/confirm SQL y ampliaciones de configuración, elegibilidad,
  liquidación y base de muertes. Bootstrap regenerado desde las 80 migraciones.
- API: GET/POST `/v1/admin/seasons/{season_id}/enrollment`, modelos estrictos,
  dependencia administrativa, respuestas validadas por temporada. 132 rutas
  OpenAPI distintas y 55 operaciones administrativas autenticadas.
- Web: control en la pestaña existente, resumen, confirmación, refresco tras
  conflictos y conservación de solicitud incierta. Capturas inspeccionadas a 1440/390 px.
- Herramientas: validador 080, plan inicial 079 desplegada/080 pendiente,
  actualizado a 080 desplegada tras la publicación; bytes 080 fijados y
  ensayo requerido. SHA-256 080:
  `297b48f306242b00ae8fd361e8bbdcd11bdc3fe0ff3e5dfb93b87c936caae5b5`.
- SQL vuelve a comprobar administrador/estado y reutiliza locks/receipts.
  anon/authenticated no acceden a tablas o funciones nuevas. Inyección local
  prueba reversión de toda el alta. No se amplían privilegios del participante.

## Pruebas (2026-11-04)

Windows / .venv-api / PostgreSQL 17 Supabase-shaped desechable en loopback;
fixtures sintéticos. Fuente c2e8617 más el diff del commit de este informe.

- Python: **1490 PASS**, cero errores/fallos/saltos, 153.904 s. Runner aislado
  tools.run_unit_tests.main(), 124 módulos versionados + test_api_enrollment,
  PYTHONPATH raíz + tests para los subprocesos. Pruebas no versionadas del
  propietario excluidas. Incluye Liga, sesiones, economía, muertes, Team Lock
  y protección de saves del Launcher.
- SQL: `python -m tools.validate_phase080_enrollment --regressions --output
  docs/evidence/mid-season-enrollment/sql.json`. Seis momentos de alta,
  permisos/CAS/reversión, muertes/medallas/wipe/Team Lock y tres concurrencias.
  Diez regresiones: 075 muertes/Liga/divisiones/legacy/guards, 076 campeón,
  077 correcciones, 078 pastes, 079 y jornadas de participantes.
- React: **45 ficheros / 378 PASS**, npm test.
- Playwright: **9 PASS**, enrollment.spec.ts + league-start.spec.ts; CSS real,
  alta en móvil/escritorio, conflicto obsoleto, J1, perfil, Fijar Equipo y Team Preview.
- Launcher/Node: **70 PASS**, node --test en los tests del Launcher, lector
  público, firma de actualizaciones y worker. Sin nueva versión del Launcher.
- npm run build con VITE_API_BASE_URL=https://pokeapp-api-production.up.railway.app:
  TypeScript/build correctos, solo artefactos locales. compileall app/tests/validador,
  lint de archivos nuevos y git diff --check correctos.
- La primera pasada Python detectó el caso RLS aún no añadido al inventario
  del test; se actualizó junto con FORCE RLS. La suite completa final es verde.
  La primera compilación sin VITE_API_BASE_URL fue rechazada por la protección
  existente; se repitió con esa variable sin modificar la protección.

[SQL](../evidence/mid-season-enrollment/sql.json),
[ensayo histórico](../evidence/mid-season-enrollment/rehearsal.json),
[escritorio](../evidence/mid-season-enrollment/enrollment-1440.png),
[móvil](../evidence/mid-season-enrollment/enrollment-390.png).
No se han publicado pastes ni probado equipos reales contra Discord/Pokepast.es.

## Ensayo, publicación y rollback

Se restauró el archivo verificado pre-release-20261104T114551Z.dump, anterior
a 079. Se ensayó localmente 078 → 079 → 080: **19 comprobaciones PASS**,
101 tablas anteriores con datos idénticos, 104 lecturas iguales, permisos sin
ampliaciones, fixtures revertidos y catálogo igual a una base vacía 001–080.
Los datos reales solo estuvieron en la copia privada local. Este ensayo histórico
no sustituye al respaldo fresco/preflight que necesita una publicación.

La publicación autorizada se ejecutó con un respaldo nuevo en 079 y solo 080,
seguida de API y web. No repetir migraciones ni despliegues por los pasos del
plan histórico. Próximo paso funcional: un administrador legítimo puede abrir
Administración → Entrenadores → Añadir entrenador y revisar el preview; solo
confirmará una incorporación que realmente corresponda. El usuario nuevo debe
sincronizar su partida oficial antes de continuar la progresión de Liga.

El fix c2e8617 ya está publicado en la misma API. Rollback: API anterior
`ef13a7ce-6d2c-476a-bb2e-78ace27b594b` (referencia de despliegue; Railway la
marca REMOVED tras sustituirla, por lo que puede requerir redeploy de su fuente
`f2f799c`) y web `a81eb04f-ae65-4f53-821b-14e201a0a8ad`, conservando 080 y su
historia si hubo incorporaciones. No borrar créditos, miembros ni capturas,
ni retirar el tipo de ledger usado. SQL mantiene compatibilidad con la API
anterior; las reparaciones posteriores requieren auditoría y fix-forward.

Producción actualizada únicamente con SQL 080, API y web autorizadas.
Sin altas, créditos, cruces, Team Locks ni archivos Pokémon reales usados como
prueba; sin pastes nuevos o mensajes Discord de prueba. No se modificó el Launcher.
Estado remoto VALIDATION_PARTIAL por los límites autenticados descritos arriba;
base, ACL, despliegues y aceptación HTTP comprobados remotamente.
Los clusters se detuvieron/eliminaron y los navegadores se cerraron. Sin nuevo
sondeo/servicio. Logs crudos en TEMP y directorio privado de ensayo; el repositorio
contiene solo evidencias saneadas y capturas sintéticas.
