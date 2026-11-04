# Incorporaci?n durante ChampionsLocke ? registro de continuidad

Estado: IMPLEMENTADO Y VERIFICADO LOCALMENTE; pendiente de autorizaci?n para publicar.
Fecha: 2026-11-04. Rama `codex/mid-season-enrollment`, desde
`c2e86170d5a70d0974a3d598755bc33a7ba8ee9f`. El commit que contiene este informe
agrupa implementaci?n, pruebas y evidencias. Sin push ni cambios en producci?n.

Referencias: [MultiIA](../AI/PokeApp_Multi_AI_Continuity_Protocol.md),
[checkpoint](../project-checkpoint.md), [publicaci?n 079](all-vs-all-league-start.md),
[fix independiente Pokepast.es](public-pokepaste-format.md).

## Git y Pokepast.es

Git se comprob? antes de cambiar nada: origin/claude/all-vs-all-league-start
segu?a en `16708e9`; `c2e8617` es su descendiente directo. Ese commit conserva
la correcci?n CRLF y puede desplegarse por separado solo con API. Su transporte,
exportador privado, URL guardadas, snapshots y cola Discord no se han modificado.
Las pruebas p?blicas (24) y del exportador privado (26) siguen en la regresi?n.
Los archivos no versionados del propietario quedan excluidos. La gu?a protegida
no se ha le?do, buscado, copiado, movido, calculado su hash, editado ni a?adido al ?ndice.

## Operaci?n y reglas

Administraci?n ? temporada seleccionada ? Entrenadores ? A?adir entrenador.
Se selecciona una cuenta existente, habilitada y autenticable, todav?a ajena a
la temporada. Se reutilizan cuentas/invitaciones y no se conceden privilegios
administrativos. La ruta de altas en borrador conserva su comportamiento.
La nueva operaci?n exige administrador y temporada activa moderna todos contra
todos; rechaza formatos incompatibles, cierres no demostrables y campeonatos finalizados.

La previsualizaci?n del servidor muestra cero puntos, jornadas oficialmente
cerradas, monedas exactas, jornada de entrada y cruces nuevos. Confirmar solo
acepta entrenador y hash de esa previsualizaci?n. Los cambios en resultados,
jornada, configuraci?n, cuentas o plantilla invalidan el hash. Una respuesta
incierta conserva la solicitud y clave de idempotencia existentes.

- NET oficial inicial exactamente cero: sin victorias, derrotas, puntos ni
  muertes anteriores inventadas. Sin fuente oficial, la historia/progresi?n
  puede seguir pendiente seg?n el contrato previo; no se adivina un estado del save.
- Monedas iniciales: suma de la recompensa com?n configurada en cada snapshot
  de jornada realmente cerrada. La abierta no cuenta y no se usa su n?mero
  como multiplicador. Casos 0/10/20 y recompensa configurable de 17 probados.
- Cr?dito `enrollment_credit`, ligado a incorporaci?n, entrenador, temporada,
  administrador y evidencia de los cierres incluidos. ?ndice ?nico, transacci?n,
  receipts y locks impiden duplicarlo. Cero monedas se audita sin ledger de importe cero.
- La primera observaci?n oficial fiable liquida por cero las medallas y el
  campeonato ya presentes. Dos medallas iniciales no dan ocho monedas; la
  tercera nueva da cuatro una vez. Ocho medallas m?s campeonato iniciales
  producen nueve claims de importe cero. Los nuevos hitos posteriores usan
  la funci?n original; los participantes existentes conservan sus cr?ditos.
- Entrada en la jornada abierta o siguiente preparada/no preparada. Sin J1,
  se incorpora a su preparaci?n normal. Sin participaci?n retroactiva ni reaperturas.

Una Liga de cinco pasa a seis con cinco cruces nuevos, quince en total. Se
insertan solo parejas del reci?n llegado: los combates anteriores conservan
identidad, resultado y metadatos. Los nuevos pendientes bloquean el cierre.
Se incrementan las revisiones para invalidar resultados/cierres previsualizados
con la plantilla anterior. Si compiten cierre y alta, solo una operaci?n confirma.

Las configuraciones utilizadas y snapshots originales no se editan. Una
proyecci?n ampl?a las posiciones elegibles conservando recompensa com?n y reglas.
Los l?mites de incorporaci?n excluyen al nuevo entrenador de jornadas anteriores.
El cierre sigue por victorias, menos muertes del segmento y 1v1 expl?citos;
Blindar/Robar y campe?n por NET acumulado conservan sus funciones. El reci?n
llegado cobra la recompensa ordinaria de su primera jornada al cerrarse,
sin volver a pagar los cierres usados para el cr?dito inicial.

## Partida, muertes y Team Lock

La partida oficial se registra mediante Launcher con las validaciones existentes
de identidad, propietario, temporada y revisiones. La primera fuente completa
aceptada establece una base expl?cita auditada. Sus eventos de muerte se conservan
con procedencia, anteriores a esa base; no se fabrican penalizaciones retroactivas.
Las observaciones posteriores usan seguimiento, ciclos de vida y deduplicaci?n normales.

**L?mite de evidencia:** sin observaci?n inicial no puede fecharse una muerte o
medalla en el intervalo no observado. Se debe sincronizar la partida oficial
antes de continuar la progresi?n de Liga. La evidencia inicial de muertes se
conserva para revisi?n hist?rica administrativa; no se asignan fechas ni se borra
historia aut?ntica. Este l?mite se explica en la confirmaci?n del alta.

Si la jornada ya empez? se a?ade solo la captura del nuevo participante;
las capturas y per?odos de los dem?s no cambian. Las muertes posteriores cuentan
para NET y mantienen la separaci?n previa entre progresi?n y combates para el
desempate. Dos muertes reales, una revivida tras wipe, son tres d?cimas en total,
sin cobro doble. La conciliaci?n hist?rica administrativa respeta la nueva base.

Team Preview utiliza al participante y su equipo sincronizado por las v?as
existentes. Puede fijar equipo en la jornada actual sin participaci?n anterior.
Su Team Lock usa Discord/Pokepast.es existentes: una fila, reemplazos como
revisiones y la misma privacidad. El nuevo participante registra resultados
mediante el endpoint normal, sin permisos de administraci?n.

## Implementaci?n y seguridad

- 080: `league_enrollments` privado con RLS y FORCE RLS, datos base inmutables,
  cr?dito ?nico, preview/confirm SQL y ampliaciones de configuraci?n, elegibilidad,
  liquidaci?n y base de muertes. Bootstrap regenerado desde las 80 migraciones.
- API: GET/POST `/v1/admin/seasons/{season_id}/enrollment`, modelos estrictos,
  dependencia administrativa, respuestas validadas por temporada. 132 rutas
  OpenAPI distintas y 55 operaciones administrativas autenticadas.
- Web: control en la pesta?a existente, resumen, confirmaci?n, refresco tras
  conflictos y conservaci?n de solicitud incierta. Capturas inspeccionadas a 1440/390 px.
- Herramientas: validador 080, plan 079 desplegada/080 pendiente, bytes 080
  fijados y ensayo requerido. SHA-256 080:
  `297b48f306242b00ae8fd361e8bbdcd11bdc3fe0ff3e5dfb93b87c936caae5b5`.
- SQL vuelve a comprobar administrador/estado y reutiliza locks/receipts.
  anon/authenticated no acceden a tablas o funciones nuevas. Inyecci?n local
  prueba reversi?n de toda el alta. No se ampl?an privilegios del participante.

## Pruebas (2026-11-04)

Windows / .venv-api / PostgreSQL 17 Supabase-shaped desechable en loopback;
fixtures sint?ticos. Fuente c2e8617 m?s el diff del commit de este informe.

- Python: **1490 PASS**, cero errores/fallos/saltos, 153.904 s. Runner aislado
  tools.run_unit_tests.main(), 124 m?dulos versionados + test_api_enrollment,
  PYTHONPATH ra?z + tests para los subprocesos. Pruebas no versionadas del
  propietario excluidas. Incluye Liga, sesiones, econom?a, muertes, Team Lock
  y protecci?n de saves del Launcher.
- SQL: `python -m tools.validate_phase080_enrollment --regressions --output
  docs/evidence/mid-season-enrollment/sql.json`. Seis momentos de alta,
  permisos/CAS/reversi?n, muertes/medallas/wipe/Team Lock y tres concurrencias.
  Diez regresiones: 075 muertes/Liga/divisiones/legacy/guards, 076 campe?n,
  077 correcciones, 078 pastes, 079 y jornadas de participantes.
- React: **45 ficheros / 378 PASS**, npm test.
- Playwright: **9 PASS**, enrollment.spec.ts + league-start.spec.ts; CSS real,
  alta en m?vil/escritorio, conflicto obsoleto, J1, perfil, Fijar Equipo y Team Preview.
- Launcher/Node: **70 PASS**, node --test en los tests del Launcher, lector
  p?blico, firma de actualizaciones y worker. Sin nueva versi?n del Launcher.
- npm run build con VITE_API_BASE_URL=https://pokeapp-api-production.up.railway.app:
  TypeScript/build correctos, solo artefactos locales. compileall app/tests/validador,
  lint de archivos nuevos y git diff --check correctos.
- La primera pasada Python detect? el caso RLS a?n no a?adido al inventario
  del test; se actualiz? junto con FORCE RLS. La suite completa final es verde.
  La primera compilaci?n sin VITE_API_BASE_URL fue rechazada por la protecci?n
  existente; se repiti? con esa variable sin modificar la protecci?n.

[SQL](../evidence/mid-season-enrollment/sql.json),
[ensayo hist?rico](../evidence/mid-season-enrollment/rehearsal.json),
[escritorio](../evidence/mid-season-enrollment/enrollment-1440.png),
[m?vil](../evidence/mid-season-enrollment/enrollment-390.png).
No se han publicado pastes ni probado equipos reales contra Discord/Pokepast.es.

## Ensayo, publicaci?n y rollback

Se restaur? el archivo verificado pre-release-20261104T114551Z.dump, anterior
a 079. Se ensay? localmente 078 ? 079 ? 080: **19 comprobaciones PASS**,
101 tablas anteriores con datos id?nticos, 104 lecturas iguales, permisos sin
ampliaciones, fixtures revertidos y cat?logo igual a una base vac?a 001?080.
Los datos reales solo estuvieron en la copia privada local. Este ensayo hist?rico
no sustituye al respaldo fresco/preflight que necesita una publicaci?n.

Pr?ximo paso exacto, **solo tras autorizaci?n expl?cita del propietario**:

1. Verificar Git, proyecto Supabase y despliegues vigentes; capturar respaldo
   fresco en 079 y ensayar solo 080 con los bytes comprometidos. Revisar preflight,
   actividad, grants y ausencia de operaciones f?sicas pendientes. No reutilizar
   el archivo hist?rico como gate de publicaci?n.
2. Aplicar una vez 080 con el runner protegido, conservar intent/result e historial;
   verificar funciones/ACL sin ejecutar altas reales.
3. Publicar API de esta rama, incluido CRLF; comprobar health, 132 rutas, 401
   an?nimo y 403 participante en las operaciones nuevas.
4. Publicar web verificada y revisar el preview administrativo. No confirmar
   entrenadores, crear cruces/monedas o publicar pastes como prueba.
5. Registrar despliegues y validaci?n; primera incorporaci?n/Team Lock reales
   quedan al uso leg?timo de los usuarios.

El fix c2e8617 puede salir solo con API, sin 080 ni web. La funci?n completa
necesita SQL + API + web. Rollback: web/API anteriores, conservando 080 y su
historia si hubo incorporaciones. No borrar cr?ditos, miembros ni capturas,
ni retirar el tipo de ledger usado. SQL mantiene compatibilidad con la API
anterior; las reparaciones posteriores requieren auditor?a y fix-forward.

Producci?n no modificada: sin migraci?n remota, Railway/Cloudflare, altas,
cr?ditos, cruces, Team Locks o archivos Pok?mon reales. Sin push.
Estado remoto: STAGING_UNVERIFIED; ?ltima publicaci?n seg?n el registro 079.
Los clusters se detuvieron/eliminaron y los navegadores se cerraron. Sin nuevo
sondeo/servicio. Logs crudos en TEMP y directorio privado de ensayo; el repositorio
contiene solo evidencias saneadas y capturas sint?ticas.
