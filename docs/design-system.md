# PokeApp Arena — design system and private preview

Phase27B. One identity for the web and the Launcher: a night stadium base,
bright teal / magenta / gold signals and chunky rounded "game menu" shapes.
Inspired by the energy of modern Pokémon menus; every screen, shape and asset is
original (no copied screens or protected artwork).

**Artistic Evolution ("Liga Nocturna")** builds on Arena: Pokémon game feel
first, then game colour and dynamism, with touches of esports and premium.
See [Artistic Evolution](#artistic-evolution--liga-nocturna) below.

## Files

| File | Role |
| --- | --- |
| [web/src/design/tokens.css](../web/src/design/tokens.css) | Palette primitives (`--c-*`), semantic aliases, area signals (`--sec-*`), type, space, radii, shadows, motion |
| [web/src/design/arena.css](../web/src/design/arena.css) | Shared visual layer (27B); tokens only, no page-specific copies |
| [web/src/design/evolution.css](../web/src/design/evolution.css) | Artistic Evolution layer, loaded last: typography, ribbons, per-area scenes, types, Pokédex, motion switch |
| [web/src/preferences.ts](../web/src/preferences.ts), [web/src/sound.ts](../web/src/sound.ts) | Audio-visual preferences and the synthesised interface sounds |
| `web/src/{styles,product,art-direction,product-polish}.css` | Legacy layers; their 451 literal colours were mapped once to tokens by [tokenize-colors.mjs](../web/scripts/tokenize-colors.mjs) (report beside it). Do not run it again |
| [companion/launcher/style.css](../companion/launcher/style.css) | Native Launcher screens; its primitives must equal the web tokens ([design-sync.test.cjs](../companion/launcher/design-sync.test.cjs)) |

Load order ([main.tsx](../web/src/main.tsx)): Rubik → `tokens.css` → four legacy
layers → `arena.css` → `evolution.css`.

## Rules

- **Colour literals live only in the palette primitives.** Components use the
  semantic aliases (`--surface`, `--text-body`, `--primary`, `--error`…) or
  `color-mix()` over primitives.
- **One signal colour per area** (`--sec-*`), shared by the navigation pill, the
  page ribbon, primary buttons and the Home tile. Eleven areas, eleven distinct
  signals (Phase 17.1 contract, checked by `art-direction.spec.ts`): main areas
  use the saturated family, archive/ops areas the soft one.

  | Area | Signal | Area | Signal |
  | --- | --- | --- | --- |
  | Inicio | teal `--c-accent` | Tienda | orange `--c-warm` |
  | Liga | gold `--c-gold` | Hall de la Fama | champagne `--c-gold-soft` |
  | Batallas | magenta `--c-magenta` | Juicios | lavender `--c-violet-soft` |
  | Copa | violet `--c-violet` | Saves y Launcher | ice `--c-info-soft` |
  | Entrenadores | blue `--c-info` | Administración | peach `--c-warm-soft` |
  | Mi PC | leaf `--c-leaf` | login / registration | brand gradient |

- **Primary buttons** are filled with the area colour (`background-color` is the
  signal; a light sheen gradient sits on top) with `--on-primary` ink text.
- **Danger is only for errors.** `--c-danger` never acts as an accent.
- **Motion** is short and soft (`--t-fast/base/slow`); `prefers-reduced-motion`
  sets every duration to 0 and switches off the decorative loops (background
  drift, holographic ∞ border, Hall foil, sprite hop, route fade).
- **Focus** is always visible: glow ring on fields, 2 px outline on menu links,
  tiles, cards and buttons.

## Signature pieces

- **Home menu**: a complete 3 × 3 board of the nine areas — wide menu buttons
  with a sliding selection chevron on desktop, an icon grid on phones (the
  detail text stays in the accessible name).
- **Sidebar**: grouped game-menu pills; every destination (Cuentas included)
  fits 1440 × 900, shorter screens get a compact rhythm and a fading scroll edge.
- **Trainer card**: portrait plus stat rows (Puntos / Monedas / Muertos). The
  profile identity uses the same rows whenever the card itself is narrower than
  520 px (container query), so it adapts to phones and the Launcher window.
  Stat labels are never truncated or broken inside a word.
- **Shop**: items on a lit counter disc, a light sweep on hover, gold coins kept
  separate from the orange area signal.
- **Infinite items (∞)**: Rare Candy and Heart Scale cards wear a slow
  holographic border; the logic (free, unlimited, no coins, Launcher-limited by
  the physical bag) is unchanged from 26C.
- **Hall of Fame**: champion cards in gold foil with an occasional sheen.

## Artistic Evolution — Liga Nocturna

**One family:** Rubik (variable 300–900, rounded and sporty, very legible
numbers) for every screen of the web and the Launcher, in different weights
only. Web: `@fontsource-variable/rubik@5.3.0`, bundled and split by script
(the Latin file, 35 KB, is the only one normally fetched). Launcher: the same
Latin file packaged in `assets/fonts` with `font-src 'self'`.

**Signature language**

- Galar-style diagonal ribbon for screen eyebrows, in the area colour.
- The ball band (two bars and a centre button) under every screen title and
  the Launcher's main title; a wobbling ball for loading states.
- Pokémon stand on lit platforms; cards and the Pokédex stage take the
  Pokémon's primary type colour (18 type tokens `--type-*`, original values).

**Intensity by area**

| Level | Areas | What moves |
| --- | --- | --- |
| Show | Inicio, Tienda, Liga, Hall, Mi PC | stadium beams, turning ball, VS pulse, awning, gold spotlight and trophy glow, box wallpapers |
| Balanced | Perfil, Inventario, navigation | licence card, ∞ holographic border, route fade |
| Competitive | Team Preview, Scouting, Combates | static layouts; hover feedback only; move panels never move |
| Calm | Administración | flat cards, no lift or glow |

**Screens**

- *Inicio*: a stadium hero (portrait, greeting, scoreboard, the team on lit
  platforms), the 3 × 3 menu board, a versus card against the next rival.
- *Scouting*: one-click rival portraits (the labelled select stays for
  keyboards), licence-card identity, type-tinted team cards.
- *Pokédex dialog*: national number, type stage, data and moves in the three
  approved columns; a bottom sheet on phones.
- *Tienda*: market awning, ₽ purse, gold price chips; descriptions are always
  visible text (never hover-only).
- *Mi PC*: framed box system, pill box title, six DS-style wallpapers chosen by
  box number (`data-wallpaper`, presentation only). The arrow navigation,
  slot positions and box order are unchanged.

**Sounds** (on by default): original Web Audio synthesis, no files, no game
music. `nav` on screen change, `open`/`close` for dialogs, `confirm`, `coin`
after a purchase, `error`/`notice` for refused or uncertain commands, `select`
for segmented tabs and `data-sfx` buttons. Quiet (master 0.22 × volume),
slightly detuned so repeats never sound identical, 60 ms debounce, never on
hover, and only after a user gesture (browser autoplay rules are respected;
no audio means silence, never an error).

**Preferences** (own profile → *Ajustes de la app*; quick mute in the
sidebar): Sonidos Activados/Desactivados, Volumen, Animaciones
Activadas/Reducidas. Stored in `localStorage` (`pokeapp.preferences.v1`),
presentation only, never sent to the API. `html[data-motion="reduced"]` turns
every animation and transition off and stops animated sprites; the system's
`prefers-reduced-motion` always forces it. Inside the Launcher the web keeps
its own preferences in its own isolated session.

**Stability and performance**: the main area always fills the window, so
nothing shifts while data arrives (CLS 0.258 → 0 over login and seven
screens). Animations use transform and opacity, except the existing ∞ border
and the Hall trophy glow.

### Assets and licences

| Asset | Source | Licence |
| --- | --- | --- |
| Rubik variable (web + Launcher) | Rubik Project via `@fontsource-variable/rubik` 5.3.0 | SIL OFL 1.1 ([copy](../companion/launcher/assets/fonts/OFL.txt)) |
| Interface sounds | Synthesised at run time by `web/src/sound.ts` | Original project code |
| Ribbons, ball band, stadium beams, wallpapers, awning, VS badge | Pure CSS in `evolution.css` | Original project code |
| Type colours `--type-*` | Chosen for the night palette | Original values |
| Pokémon, item and type images | Unchanged; see [ATTRIBUTION.md](../web/public/visuals/v1/ATTRIBUTION.md) | As recorded there |

No new third-party images, no hotlinks and no extracted game audio.

## Private design preview

Shows the undeployed web with synthetic data only. Never part of the product
bundle or a deployment.

```
cd web
npm run preview:design      # builds dist-preview/ (git-ignored), then serves
```

- Web `http://127.0.0.1:4173`, synthetic API `http://127.0.0.1:4174`, both bound
  to 127.0.0.1; requests with another `Host` (DNS rebinding) or a non-loopback
  `Origin` get 403.
- The API is the Playwright fixture (`web/e2e/fixtures.ts`): fictional trainers
  and Pokémon, any name and PIN enter, nothing is stored. Every page shows a
  fixed «VISTA PREVIA LOCAL» banner. The bundle's only API host is
  `127.0.0.1:4174`.
- `node preview/run.mjs --no-build` restarts the servers over an existing build.

### Inside the Launcher (private candidates only)

`tools/build_launcher_windows.ps1 -PrivateCandidate -WebPreview` bakes the one
loopback origin `http://127.0.0.1:4173` into the package metadata. The guards:

- `-WebPreview` without `-PrivateCandidate` fails in the script and in
  `electron-builder.cjs`; `audit_launcher_package.py` rejects any other preview
  origin and any preview in a public build.
- `webview.webOrigin()` honours the preview only when the packaged metadata is a
  private candidate with exactly that origin; a run-time variable can never
  redirect a packaged build.
- The preview gets its own session partition (`persist:pokeapp-web-preview`),
  never the real web session; sandbox, context isolation, no preload, no Node,
  navigation pinned to the origin and permission requests denied — unchanged.
- The updater stays off (no key/feed baked into the preview candidate).

## Review gallery

`web/e2e/design-gallery.spec.ts` captures every route at 1440 and 390 px, plus
the accounts mode production uses (registration, Cuentas, not-found route, phone
menu). It is skipped unless `POKEAPP_GALLERY_DIR` points outside git:

```
POKEAPP_GALLERY_DIR=%LOCALAPPDATA%\PokeApp-migration-evidence\phase27b\gallery-vN npx playwright test e2e/design-gallery.spec.ts
```

Launcher native screen: run `tools/launcher_ui_smoke/main.cjs` with Electron and
`POKEAPP_LAUNCHER_SHOT=<png>` (unset `ELECTRON_RUN_AS_NODE` when launching from
an editor terminal).
