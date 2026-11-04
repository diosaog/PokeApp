# Incorporación durante ChampionsLocke — registro de continuidad

Estado: PUBLICACIÓN AUTORIZADA Y EN CURSO (2026-11-04).
Fecha: 2026-11-04. Rama `codex/mid-season-enrollment`, desde
`c2e86170d5a70d0974a3d598755bc33a7ba8ee9f`. El commit que contiene este informe
agrupa implementación, pruebas y evidencias. Estado al cerrar la implementación: sin push ni cambios en producción.

Referencias: [MultiIA](../AI/PokeApp_Multi_AI_Continuity_Protocol.md),
[checkpoint](../project-checkpoint.md), [publicación 079](all-vs-all-league-start.md),
[fix independiente Pokepast.es](public-pokepaste-format.md).

## Publicación autorizada (en curso)

El propietario autorizó explícitamente SQL 080 + API con CRLF + web al
responder «si» a la solicitud final. No se volverá a pedir la misma autorización.
Se mantiene la prohibición de altas, créditos, cruces, Team Locks y pastes
artificiales sobre datos reales durante las verificaciones.

Estado remoto comprobado antes de publicar: Supabase V2 correcto y saludable,
historial hasta 079; 080 ausente. Cero jornadas abiertas, reservas de entrega
u operaciones físicas pendientes. API `ef13a7ce` SUCCESS, 131 rutas; web
`a81eb04f-ae65-4f53-821b-14e201a0a8ad` al 100%. Son los objetivos de rollback.
Respaldo fresco capturado en el directorio privado
`%LOCALAPPDATA%/PokeApp-migration-evidence/mid-season-080-release`; ensayo 080
en curso. No reaplicar 079. Aún no se ha ejecutado la migración remota.

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
- Herramientas: validador 080, plan 079 desplegada/080 pendiente, bytes 080
  fijados y ensayo requerido. SHA-256 080:
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

Próximo paso exacto, **solo tras autorización explícita del propietario**:

1. Verificar Git, proyecto Supabase y despliegues vigentes; capturar respaldo
   fresco en 079 y ensayar solo 080 con los bytes comprometidos. Revisar preflight,
   actividad, grants y ausencia de operaciones físicas pendientes. No reutilizar
   el archivo histórico como gate de publicación.
2. Aplicar una vez 080 con el runner protegido, conservar intent/result e historial;
   verificar funciones/ACL sin ejecutar altas reales.
3. Publicar API de esta rama, incluido CRLF; comprobar health, 132 rutas, 401
   anónimo y 403 participante en las operaciones nuevas.
4. Publicar web verificada y revisar el preview administrativo. No confirmar
   entrenadores, crear cruces/monedas o publicar pastes como prueba.
5. Registrar despliegues y validación; primera incorporación/Team Lock reales
   quedan al uso legítimo de los usuarios.

El fix c2e8617 puede salir solo con API, sin 080 ni web. La función completa
necesita SQL + API + web. Rollback: web/API anteriores, conservando 080 y su
historia si hubo incorporaciones. No borrar créditos, miembros ni capturas,
ni retirar el tipo de ledger usado. SQL mantiene compatibilidad con la API
anterior; las reparaciones posteriores requieren auditoría y fix-forward.

Producción no modificada: sin migración remota, Railway/Cloudflare, altas,
créditos, cruces, Team Locks o archivos Pokémon reales. Sin push.
Estado remoto: STAGING_UNVERIFIED; última publicación según el registro 079.
Los clusters se detuvieron/eliminaron y los navegadores se cerraron. Sin nuevo
sondeo/servicio. Logs crudos en TEMP y directorio privado de ensayo; el repositorio
contiene solo evidencias saneadas y capturas sintéticas.
