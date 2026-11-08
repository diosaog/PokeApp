# Administración › Avisos: vigilancia informativa de saves — 2026-11-08

Estado: **PUBLICADO / VERIFICADO** (2026-11-08). Rama
`claude/net-friendship-discord`. DB 084 `20261108192609`, API `336f3f05`
(rollback `f1d2896a`), web `b4076f0a` (rollback `9a17a56c`), fuente `72adbc4`.
Launcher y verificador sin cambios. Falta el primer análisis real (§6).

Regla fundamental (propietario, 2026-11-08): **solo informa**. Nunca bloquea
jugadores, partidas, sincronizaciones, inventarios, transferencias ni Pokémon;
no sanciona; no escribe en ningún `.sav`; no toca puntos, monedas, muertes,
combates ni Team Lock. Un aviso es una sospecha; decide el administrador.

## 1. Qué hace

Cada partida oficial aceptada se compara con la anterior del mismo entrenador
y temporada, y se contrasta con el historial autorizado del servidor:

| Fuente autorizada | Cómo se usa |
|---|---|
| `training_operations` APPLIED (Chapas, Mentas) | Se aplican en orden sobre los valores anteriores; lo que encaja no genera aviso |
| `item_deliveries` RESERVED/DELIVERED | Crédito por objeto, consumido una sola vez por análisis |
| `transfer_provenance` confirmadas | Los Pokémon recibidos por robo/transferencia no son «origen dudoso» |
| Reglas del propietario | Caramelo Raro y Escama Corazón (∞, sin registro) nunca avisan; 255 de felicidad es lo que deja la operación gratuita del Launcher |

No se consultan registros locales del Launcher ni legalidad de PKHeX: las
partidas están aleatorizadas.

**Identidad**: PID + EC (Gen 6/7) o PID + OT (Gen 3–5), nunca especie ni caja,
así que mover un Pokémon entre equipo y cajas no significa nada.

**Gravedades**: Alta (IVs, naturaleza, habilidad, shiny, sexo, datos de origen,
clones, EVs por encima del máximo). Media (objetos sin origen verificado, nivel
que baja, forma sin mecánica conocida, retroceso de evolución). Baja (especie
fuera de las evoluciones estándar, muchos movimientos a la vez, salto de EVs o
felicidad, Pokémon nuevo con OT ajeno o seis IVs a 31, avalancha de objetos
comunes o MT).

**Inventario**: mochila completa (lectura nativa de solo lectura `--audit-snapshot`)
más objetos equipados por Pokémon presentes en ambas partidas: pasar un objeto
de la mochila a un Pokémon nunca es un aumento. Objetos comunes (Pociones,
Poké Balls salvo Master/Gloria, Repelentes, etc.) solo avisan con +100 de golpe;
los raros (Cápsula Habilidad, Master Ball, vitaminas, objetos de combate…) siempre
que no haya origen verificado, aunque se puedan conseguir jugando.

## 2. Limitaciones reales (no ocultar)

- Comparar saves **no prueba el origen**: un cambio externo que deje el mismo
  resultado que una acción legítima no se distingue. Los avisos lo dicen.
- Caramelos, Escamas y Felicidad máxima no tienen registro en el servidor por
  decisión del propietario: no se pueden verificar, solo excluir por regla.
- La referencia inicial es la última partida anterior a la activación; lo
  anterior nunca se analiza. Sin partida anterior (primer save de la temporada)
  no hay comparación.
- Un Pokémon que desaparece y vuelve con otro valor no se compara (solo se
  comparan partidas consecutivas); PID+EC reescritos son un Pokémon nuevo.
- Gen 3–5: se comparan Pokémon, no mochila ni felicidad (lectura nativa solo Gen 6/7).
- Si la lectura de la mochila falla, ese análisis se registra sin inventario
  (`inventory_status`) y nunca se interpreta como cero.
- Evoluciones aleatorizadas: un cambio de especie fuera de las evoluciones
  estándar genera un aviso Bajo aunque sea legítimo (lo indica el motivo).

## 3. Arquitectura

- Lectura nativa nueva: `companion/parser/PokeApp.Parser/NativeAudit.cs`
  (`--audit-snapshot`), verificada con partidas reales de los 8 juegos. El Launcher
  no la usa; el protocolo de lectura y escritura no cambia.
- Reglas puras: `app/domain/save_audit.py`, `app/domain/pokemon_evolutions.py`.
- Servicio: `app/application/save_audit.py`, con hilo propio tras registrar una
  partida (`TrustedSaveIngestion.after_registration`); nunca ralentiza ni falla
  una sincronización. Recoge lo que quede pendiente, en orden de la cadena.
- SQL 084: `save_audit_config`, `save_audit_runs` (un análisis por save, PK),
  `save_audit_notices` (único por save+grupo, evidencia inmutable),
  `save_audit_notice_events` (historial append-only). RLS forzada, sin acceso
  directo; solo RPC de servicio y de administrador (`admin_incident_actor`).
- API admin: `/v1/admin/seasons/{id}/notices` (GET, `/summary`, `/analyze`,
  `/{id}/status` con Idempotency-Key), 136 rutas.
- Web: `web/src/features/admin-notices.tsx` (Administración › Avisos y
  `/admin/avisos`), contador en el menú.

## 4. Pruebas

| Comprobación | Resultado |
|---|---|
| Suite Python completa (incluye `tests/test_save_audit.py`: los 7 escenarios pedidos, objeto equipado y decisión) | **1526 OK** |
| Validador PostgreSQL `tools/validate_phase084_save_audit.py` (real, con el detector y el contrato de la API) | 25/25 PASS |
| Ensayo sobre copia restaurada de producción | 17/17 + 25/25 PASS; filas existentes idénticas |
| Lectura nativa real en los 8 juegos (fixtures públicas, vía el wrapper Python) | PASS |
| Vitest | 46 ficheros / 393 OK |
| Node (`companion`, `tools`, worker web) | 71 OK |
| Playwright focalizado (`admin-notices` 1440/390 px, `admin-incidents`) | 4 OK |

`e2e/admin.spec.ts` tiene 5 fallos **preexistentes**: los mismos 5 fallan en
`6f19f3c` (locator duplicado «Cambio confirmado.» y similares).

**Prueba con datos reales** (copia local restaurada, sin mochila): 38 comparaciones
de 6 entrenadores y **1 aviso** en todo el historial (cambio de habilidad de un
Pokémon de Anto, compatible con una Cápsula). Sin avisos de ruido.

## 5. Decisiones del propietario respetadas

Publicación tras pruebas completas autorizada expresamente el 2026-11-08 por
encima de la petición previa de presentar el plan de migración.

## 6. Publicación

Hecho el 2026-11-08 con la autorización expresa del propietario:

1. Copia `pre-release-20261108T192328Z` y ensayo en clúster desechable: PASS.
2. `084_save_audit_notices` aplicada una vez como `20261108192609`. Aditiva: no
   cambia filas existentes. Activación 19:26:09 UTC.
3. API `336f3f05` (imagen con el lector nativo nuevo; comprobaciones del
   Dockerfile PASS): 136 rutas, salud 200, anónimo y token inválido 401, CORS correcto.
4. Web `b4076f0a` al 100 %; el paquete servido contiene la pantalla. Evidencia:
   `docs/evidence/save-audit-notices/release-084.json`.

**Pendiente de uso real:** el primer análisis ocurrirá con la siguiente
sincronización de un entrenador (al publicar: 0 análisis y 0 avisos, lo esperado).
La pantalla autenticada de administración no se ha abierto en producción: desde
aquí no se usa ninguna sesión del propietario.

Rollback sin tocar datos: API `f1d2896a`, web `9a17a56c`. La 084 es aditiva y
puede quedarse.
