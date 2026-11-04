# Gourgeist/Pumpkaboo: sprites de tamaño — 2026-11-04

Estado: PUBLICADO Y VERIFICADO. Estado remoto de este fix visual:
`STAGING_DONE_ZERO_RESIDUE`; las comprobaciones de datos del equipo usan fixtures.
Rama `codex/gourgeist-sprite-forms`, desde `85d99d4`.

El propietario autoriza este fix y su publicación puntual, solo web. No se
modifican API, SQL, Launcher, partidas, Liga, Team Lock, Showdown o Pokepast.es.
Los archivos no versionados del propietario y la guía protegida quedan excluidos.

## Causa y corrección

`PokemonSprite` exige una correspondencia explícita para formas distintas de
cero. `visual-forms.json` no incluía Gourgeist (711) ni Pumpkaboo (710), y sus
imágenes alternativas tampoco estaban en la colección local. Por eso mostraba
`CircleHelp` antes de solicitar una imagen; no era un error HTTP o del save.

Se añaden únicamente seis correspondencias al generador existente y se
regeneran sus catálogos: formas 1 pequeña, 2 grande y 3 extragrande de ambas
especies. La forma 0 media conserva sus recursos. Índices verificados contra
[PKHeX 24.11.11](https://github.com/kwsch/PKHeX/blob/24.11.11/PKHeX.Core/PKM/Util/Conversion/FormConverter.cs#L274)
y recursos por nombre explícito en el
[CSV PokeAPI fijado](https://github.com/PokeAPI/pokeapi/blob/81d20919845b6a445969b9265aab5cec6b04cece/data/v2/csv/pokemon.csv#L1053).
Se reutilizan los commits fijados de imágenes: 18 PNG locales (colección
general, X/Y y US/UM), 54.408 bytes, con URL y SHA-256 en el manifiesto.
Todos los registros anteriores del manifiesto permanecen idénticos.
No hay refactor ni cambio en `PokemonSprite`, datos del Pokémon o animaciones.

## Verificación específica

- Vitest: **29 PASS** en `presentation.test.tsx` y `animation.test.tsx`.
  Incluye los cuatro tamaños de ambas especies en Y, UM y sin contexto de
  generación, y rechazo de formas inválidas. Los tres casos de tamaños
  fallaban antes de regenerar el catálogo.
- Build TypeScript/Vite con API de producción: **PASS**.
- Playwright sobre ese build: **1 PASS**, equipo sintético en Entrenadores.
  Jalowin mantiene `form=2` y «Forma 2»; su PNG X/Y carga con dimensiones
  naturales mayores que cero, seis sprites y ninguna interrogación.
  Captura inspeccionada visualmente. Todas las peticiones API interceptadas;
  no se usa ninguna partida ni identidad real.
- 18 PNG nuevos decodificados y hashes comprobados. No se ejecuta la suite
  completa ni una auditoría general. API y migraciones no se despliegan.

## Publicación

Commit desplegado: **`1ab6cdbd1810d32e917eeb129842d53cb604ca1c`**, subido a
`origin/codex/gourgeist-sprite-forms`. Web Cloudflare **100%**:
`babf0ab2-88be-4cb7-a603-72655c993a54`, despliegue
`327bc47e-7c16-4876-afcc-ee180b6dabc1`, 2026-11-04 15:58:26 UTC.
Dry-run y publicación PASS. Rollback web:
`82349ea3-0afd-4757-847e-144f7d32040f`.

Comprobaciones remotas 15:59 UTC: **18/18 PNG**, HTTP 200, MIME correcto,
hash exacto y píxeles decodificados. Index idéntico al build. Playwright
repetido sobre la web publicada: **1 PASS**, Jalowin con el sprite correcto,
«Forma 2» intacta y seis imágenes sin interrogaciones. API totalmente
interceptada en el navegador: esta es verificación visual de la web publicada
con datos sintéticos, no una lectura del Pokémon real del propietario.
[Captura inspeccionada](../evidence/gourgeist-sprite/jalowin-hosted-synthetic.png),
[evidencia de publicación](../evidence/gourgeist-sprite/release.json).

La API `adfca5c4` continúa SUCCESS sin nuevo despliegue. Feed del Launcher
idéntico y mismo tamaño/ETag del instalador. Ninguna actuación SQL ni sobre
partidas, Liga, Team Lock, Showdown o Pokepast.es; datos y forma auténtica
intactos. Sin llamadas reales de confirmación, exportación o envío Discord.
Servidor local detenido y navegadores de pruebas cerrados. No se dejan
fixtures remotos. El propietario comprobará su equipo real desde el Launcher.
El commit de cierre solo actualiza MultiIA, este registro y evidencias; no
requiere otro despliegue.
