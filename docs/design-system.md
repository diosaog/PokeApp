# PokeApp Arena — design system and private preview

Phase27B. One identity for the web and the Launcher: a night stadium base,
bright teal / magenta / gold signals and chunky rounded "game menu" shapes.
Inspired by the energy of modern Pokémon menus; every screen, shape and asset is
original (no copied screens or protected artwork).

## Files

| File | Role |
| --- | --- |
| [web/src/design/tokens.css](../web/src/design/tokens.css) | Palette primitives (`--c-*`), semantic aliases, area signals (`--sec-*`), type, space, radii, shadows, motion |
| [web/src/design/arena.css](../web/src/design/arena.css) | Shared visual layer, loaded last; tokens only, no page-specific copies |
| `web/src/{styles,product,art-direction,product-polish}.css` | Legacy layers; their 451 literal colours were mapped once to tokens by [tokenize-colors.mjs](../web/scripts/tokenize-colors.mjs) (report beside it). Do not run it again |
| [companion/launcher/style.css](../companion/launcher/style.css) | Native Launcher screens; its primitives must equal the web tokens ([design-sync.test.cjs](../companion/launcher/design-sync.test.cjs)) |

Load order ([main.tsx](../web/src/main.tsx)): `tokens.css` → four legacy layers →
`arena.css`.

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
