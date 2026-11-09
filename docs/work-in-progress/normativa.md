# Normativa de la ChampionsLocke — registro vivo

**PUBLICADA Y VERIFICADA el 2026-11-09**, con autorización expresa del propietario.
Rama `claude/net-friendship-discord`, fuente `9f2a1fc`. Solo web.

| Capa | Estado |
|---|---|
| Cloudflare web | `983449a9-ea75-48f1-b498-ce8383acff6f` (100 %); rollback `b4076f0a-1719-4ee0-bbd6-9e9edad81091` |
| API, SQL, verifier, Launcher | Sin cambios (DB 084, API `336f3f05`, Launcher 0.26.12) |

Contenido estático versionado: `web/src/features/normativa-content.ts`. Página:
`web/src/features/normativa.tsx`. Estilos: `web/src/design/normativa.css` y la
paleta `--c-rule-*` de `tokens.css`. Ruta `/normativa`, entrada en el grupo GENERAL
del menú, visible para todo entrenador. Escudo extraído del propio PDF con su máscara
de transparencia: `web/public/visuals/normativa/champions-cup.webp`.

Prioridad entre fuentes: decisiones del propietario, reglas vigentes en la Liga,
PDF original. Cambiar una regla es cambiar `normativa-content.ts` y su fecha
`rulebookUpdated`, y desplegar la web.

## Cobertura del PDF

| Apartado del PDF | Resultado |
|---|---|
| 1.1 Generales | Normas 1.1, 1.2, 1.4, 1.5 y 1.6 |
| 1.2 Adicionales (duplicados, legendarios, shiny, pérdida de captura, tiendas, Aarón, edición) | Normas 1.3 y 1.7 a 1.19 |
| 2.1 Límites y recompensas | Escalera de niveles, normas 2.1 a 2.5, recompensas (4 y 12, leídas de la configuración real) |
| 3.1 Tramos | Normas 3.1 y tabla de tramos |
| 3.2 Combates | 3.2; «un día antes» sustituido (ver abajo) |
| «Copa ¿!?!?» | Sin normas inventadas: 7.6 lo declara pendiente |
| 4.2 Puntuación | Sustituida por la fórmula NET |
| 4.1 Directo en Discord | 5.1 y 5.2 |
| 4.2 Caramelos y Escamas | 5.3 a 5.5 |
| 5.3 Interacción | 6.1 a 6.8 |

La numeración confusa del PDF (dos «4.2», un «5.3» sin 5.1) queda corregida por
capítulos. El «remate» de la cláusula de Aarón se omite y consta que no hay sanción.

## Reglas actualizadas respecto al PDF

- Victoria +1 (no 2). Muerte ordinaria −0,1; revivida tras wipe −0,2 en total.
- Team Lock: el PDF pedía fijarlo un día antes. Lo vigente es antes de abrir la jornada;
  si el primero llega con la jornada abierta queda «fuera de plazo»
  (`lock_timing_at`, 041). Se puede volver a fijar hasta el cierre.
- Formato: una sola Liga todos contra todos, cuatro jornadas.
- Desempate del título: menos muertes totales del Locke y después 1v1, registrado
  por Administración (076). Empates de jornada con consecuencias: 1v1 adicionales.
- Premios de jornada: 10 monedas para todos, Blindar extra al primero, Robar extra al último.
- Robo: el PDF sigue vigente (ciclo y 24 h) y se añaden las condiciones reales.

## Hechos verificados para el texto (2026-11-09, solo lectura)

Configuración viva: 4 jornadas, una división, 10 monedas por jornada, 4 por medalla,
12 por Campeón, Caja 7 como caja de muertos, 6 participantes activos.

**Revivir y Robar no se presentan como disponibles.** Se venden, pero su aplicación no
está activa: `POKEAPP_ITEM_VERIFICATION_TRANSPORT_ENABLED` sin definir y robos limitados
a 1 de los 6 participantes (lista de ingeniería). El inventario responde «Aún no se puede
aplicar. No se ha consumido». Al activarlos hay que cambiar `active` y `status` en
`wildcards`.

## Pendiente de decisión del propietario (no bloquea)

- La regla de las 24 h desde la captura (6.8) se publica porque sigue en el PDF, pero
  PokeApp no la comprueba: depende del respeto del grupo.
- «Tiendas» del PDF (1.15, 1.16) se interpreta como las tiendas de la partida, porque la
  Tienda de PokeApp vende bayas y objetos competitivos y permite recompras.
- El nivel de la J4 (82, Dianta) se deduce de «lo marca el último líder del tramo» y de
  que el tramo 4 termina con el juego.
- Las reglas de la temporada V1 (`app/interfaz/normativa.py`: Item Clause, Sleep Clause,
  baneados, Bo1/Bo3) no están en el PDF ni en PokeApp 2.0 y no se han incluido.

## Verificación

- `tsc -b`, Prettier y build de producción correctos.
- Vitest: `normativa.test.tsx` 7 PASS (cobertura del PDF, NET exacto en décimas, reglas
  sustituidas ausentes, comodines no activos), más `app-profile` y `capabilities`: 12 PASS.
- Playwright `e2e/normativa.spec.ts`, 7 PASS en Edge con API sintética: 1440, 1100 y 390 px,
  sin desplazamiento lateral ni texto cortado, índice y capítulos, enlace directo,
  entrenador sin permisos de administración, escalera a altura completa, calculadora.
- Revisión visual de capturas a las tres anchuras.
- Publicada: `index.html` y los dos chunks idénticos al build, `/normativa` 200, escudo 200,
  y 1 Playwright PASS contra la web real con API sintética interceptada.
- Launcher: carga esta misma web (`PRODUCTION_WEB` en `companion/launcher/webview.cjs`) y la
  navegación interna no pasa por `will-navigate`. No se ha abierto un Launcher instalado.

No se ejecutaron las suites completas, por indicación expresa del propietario.
