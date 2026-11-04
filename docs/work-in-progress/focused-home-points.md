# Home, anuncios Team Lock y puntos pendientes — 2026-11-04

Estado: CORRECCIONES WEB PUBLICADAS Y VERIFICADAS; diagnóstico completado.
Estado global `VALIDATION_PARTIAL`: Discord detenido por límite de
autorización, pues requiere migración nueva. No se declara implementado.
Rama `codex/home-points-followup`, desde `3f64ba3`; contiene 080 y el fix
Gourgeist/Pumpkaboo `1ab6cdb`. Historial remoto verificado hasta 080
(`20261104153603`). No se aplican ni crean migraciones.

## Correcciones pequeñas de web

- Home elimina únicamente el texto numérico «Forma N». `form` sigue llegando
  a `PokemonSprite`; el sprite X/Y de Gourgeist forma 2 permanece correcto.
  La ficha del entrenador conserva su presentación. Sin cambios en formas,
  género, Team Lock, exportación privada Showdown o transporte CRLF Pokepast.es.
- Si la fuente de puntos indica `death_history_baseline_required`, Home
  explica el «—» y enlaza a la ficha propia. El historial explica que también
  hay que confirmar cuando se observan cero muertes; botón explícito
  «Confirmar historial de muertes». No se convierte un saldo desconocido en cero.
- Se encontró además un fallo de caché: confirmar el historial invalidaba
  historial/readiness, pero no la clasificación. Ahora invalida también Liga
  y overview del mismo usuario y temporada. El test de invalidación fallaba
  antes del cambio. No se modifica el cálculo del servidor.

## Samu e Iker: evidencia actual de solo lectura

Consultas 2026-11-04, aproximadamente 16:08–16:16 UTC. No se inició sesión
como ningún entrenador. SQL con `read_only=true`; helpers de lectura con la
identidad de servicio, sin actor ni parámetros de confirmación. El helper
`league_participant_death_state` tiene cuerpo de consultas inspeccionado;
su POST de transporte no ejecuta el endpoint de confirmación. Una primera
consulta con el rol read-only no tenía permiso para ejecutar un helper; no se
alteraron grants y las lecturas se realizaron por las vías de servicio existentes.

| Hecho | Samu | Iker |
|---|---|---|
| Partida oficial | Y, registrada y procesada | Y, registrada y procesada |
| Última subida oficial / fuente aceptada actual | 04-11 15:57:32 UTC | 03-11 18:40:09 UTC |
| Medallas observadas | 1 | 2 |
| Monedas | 4, un claim badge:1 y ledger badge_reward de 4 | 8, dos claims de 4 |
| Muertes observadas | 0 | 3 |
| Historial confirmado | No | No |
| Motivo oficial de «—» | death_history_baseline_required | death_history_baseline_required |
| Puede confirmar por sí mismo | Sí | Sí |
| Propuesta real / wipe / progresión | 0 / 0 / 0 | 3 / 0 / 3 |
| Victorias y reducción adicional de puntos | 0 y 0 | 0 y 0 |
| NET esperado tras confirmar esos valores | 0 | −0,3 |

La clasificación del servidor devuelve `total_points=null` en ambos casos.
Por tanto, su «—» actual representa la falta de confirmación y no una cifra
numérica ya válida oculta por la web. El fallo de refresco corregido afecta al
paso posterior a confirmar; no sustituye la confirmación pendiente.
Los valores coinciden con la evidencia del propietario. No se conceden puntos,
se inventan muertes, se tocan monedas ni se confirma en su nombre.

Instrucciones para cada uno: entrar en su cuenta → Inicio → «Ir a confirmar
mi historial», o Entrenadores → su ficha → «Confirmar historial de muertes» →
revisar 0/0/0 (Samu) o 3/0/3 (Iker) → «Confirmar estos valores». Si una nueva
sincronización muestra otros valores, debe revisarlos antes de confirmar.
[Evidencia saneada](../evidence/focused-home-points/diagnosis.json).

## Discord: bloqueo concreto, sin cambio parcial inseguro

067 mantiene una fila `event_key=team_locked:<lock_id>` con UNIQUE, y el
reemplazo sobrescribe `team_locks.public_team_snapshot`. El trigger incrementa
la revisión de esa misma fila y excluye estados failed/uncertain/expired/skipped.
Se verificaron el constraint y el trigger reales. Un reemplazo con idéntico
snapshot público ni siquiera aumenta la revisión de anuncio. El worker edita el mensaje
anterior; la recuperación de un envío también usa ese ID como prueba de edición.

Cambiar solo edit por POST no garantiza un anuncio por versión confirmada:
dos reemplazos rápidos pueden perder el snapshot intermedio, una versión
posterior puede quedar bloqueada tras entrega incierta y la recuperación puede
confundir el ID anterior con el intento nuevo. Hace falta persistir una clave,
snapshot y estado de entrega por versión dentro de la transacción de confirmación.
Esto requiere migración, expresamente no autorizada. Esta parte se detiene sin
crear SQL ni modificar worker, cola o registros productivos. No se envían
mensajes ni se crean Team Locks/pastes reales. El comportamiento anterior sigue
vigente; no se afirma que los reemplazos ya generen mensajes nuevos.

## Pruebas y publicación

50 tests web de cinco archivos: Home, historial, invalidación, sprites y
animación; 9 tests API de `test_api_league_start.py`; TypeScript/Vite PASS.
Una prueba Playwright contra el build: Home sin etiqueta, forma auténtica
conservada, aviso/enlace, confirmación exacta 0/0/0 con idempotencia y refresco
de clasificación a 0 sin recargar. API totalmente interceptada, equipo sintético.
No se ejecutan las suites completas ni una auditoría general.

Publicación solo web: fuente **`e57fe2c4e8d15883562a741e6411465ffe9908d5`**,
Cloudflare **`4f46cbcb-c83c-4d97-96dd-56dc4bc3b714` al 100%**, despliegue
`04109b7d-9679-41c9-b433-416b4d76d43a`, 2026-11-04 16:17:19 UTC.
Comprobaciones 16:18 UTC: index y chunks idénticos al build, API configurada
correctamente, health 200, OpenAPI 132 rutas y API `adfca5c4` SUCCESS sin
despliegue nuevo. Feed del Launcher idéntico y mismo instalador por tamaño/ETag.
Verifier y optimización Railway sin cambios.

Playwright repetido sobre los archivos publicados: **1 PASS** para el mismo
recorrido, incluyendo la confirmación sintética y el refresco inmediato.
[Captura inspeccionada](../evidence/focused-home-points/home-hosted-synthetic.png),
[despliegue y verificación](../evidence/focused-home-points/release.json).
La confirmación real de Samu/Iker sigue reservada a sus propias cuentas;
estas pruebas no la ejecutan ni afirman haberla ejecutado.

Rollback web: `babf0ab2-88be-4cb7-a603-72655c993a54`. Para continuar trabajo,
usar el tip de `origin/codex/home-points-followup`. El commit de cierre solo
actualiza registros y evidencias; no necesita otro despliegue.
Servidor local detenido; navegadores cerrados y sin fixtures remotos. Archivos
no versionados del propietario excluidos y guía protegida sin leer, buscar,
copiar, mover, calcular hash, editar o indexar.
