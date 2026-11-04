# Gourgeist/Pumpkaboo: sprites de tamaño — 2026-11-04

Estado: VERIFICADO LOCALMENTE; publicación web autorizada y en curso.
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

Pendiente de terminar la publicación web y repetir la comprobación visual
contra los archivos servidos. Rollback web: `82349ea3-0afd-4757-847e-144f7d32040f`.
La API publicada sigue siendo `adfca5c4`; DB 080 y Launcher 0.26.11 se conservan.
No confirmar Team Lock ni generar pastes como prueba. El propietario comprobará
su equipo real desde el Launcher después de la publicación.
