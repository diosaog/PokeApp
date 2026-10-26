# Project Artistic Evolution — "Liga Nocturna"

2026-10-26. **ARTISTIC EVOLUTION DONE LOCAL — not deployed** (the owner reviews
it first). Entry `2ffdb29` (27C DONE LOCAL, main = origin/main). Production
unchanged: Cloudflare still serves the Arena web (27C), Railway the 27C API;
no migration, no Launcher publication, physical writes off. Design reference:
[design-system.md](design-system.md#artistic-evolution--liga-nocturna).

## Direction

Arena (27B) was a solid, approved base; it read as a polished dark dashboard
with Pokémon in it. Liga Nocturna keeps its structure, sidebar, colours per
area and every function, and pushes the feel towards a Pokémon game:

1. **Pokémon first** — the ball as signature (title band, loading ball, the
   giant ball turning behind Home), Pokémon standing on lit platforms, cards
   and the Pokédex coloured by type, box wallpapers like the DS PC.
2. **Game colour and dynamism** — Galar-style diagonal ribbons, a VS badge,
   stadium beams, a market awning, a golden spotlight for champions.
3. **Esports and premium as touches** — scoreboard stats, gold league table,
   one rounded sporty family (Rubik) with confident weights.

Intensity follows the screen's job: show (Inicio, Tienda, Liga, Hall, PC),
balanced (profile, inventory), competitive (Team Preview, Scouting, battles:
static, readable), calm (Administración: flat, no effects).

## What changed

| Area | Result |
| --- | --- |
| Typography | One family, Rubik variable (OFL, self-hosted), web and Launcher |
| Inicio | Stadium hero: portrait, greeting, season, scoreboard, team on lit platforms under sweeping beams and a turning ball; menu board; versus card against the next rival. All former data and links kept |
| Scouting | One-click rival portraits (labelled select kept for keyboards and tests), licence-card identity, type-tinted team cards |
| Pokédex dialog | National number, type stage, ribbon, level chip, data and moves in the approved three columns; bottom sheet on phones; Escape, focus return and labels unchanged |
| Tienda | Market awning, ₽ purse badge, gold price chips; descriptions always visible; purchase dialog and its guards unchanged |
| Inventario ∞ | Holographic border kept; integrates with profile and settings |
| Liga | Championship scoreboard: gold header, framed table, glowing round selector |
| Hall de la Fama | Golden spotlight, starry foil cards, glowing trophy, gold-framed champions; no invented data |
| Mi PC | Framed box system, pill box title, six DS-style wallpapers by box number. **Arrow navigation, slot positions and box order untouched** (only a presentational `data-wallpaper` attribute was added) |
| Team Preview / battles | Same layouts; move disclosures never move; colours only |
| Administración | Flat cards, no lift or glow |
| Types | Eighteen distinct type colours again (27B's token migration had merged them into eight) |
| Sounds | On by default, original Web Audio synthesis, quiet, never on hover, only after a gesture |
| Preferences | Own profile → Ajustes de la app: Sonidos on/off, Volumen, Animaciones Activadas/Reducidas; quick mute in the sidebar; `localStorage`; system reduced motion always wins |
| Stability | CLS 0.258 → 0 (main area fills the window; season picker keeps its place) — a pre-existing defect. Animated sprites keep their still image until the GIF has loaded. First paint waits for the brand font (max 1.2 s) |
| Launcher | Same Rubik family packaged locally (`font-src 'self'`), ribbon panel titles, ball band; package list and asar audit allow exactly the font and its licence |

Own initiative (not requested): the VS card, sprite preloading, the font-ready first paint, the turning ball, DS box
wallpapers, the national Pokédex number, the market awning and ₽ purse,
type-coloured cards, the wobbling loading ball, restoring eighteen type
colours, the quick mute, and fixing the layout shift.

## Evidence

Evidence folder: `%LOCALAPPDATA%\PokeApp-migration-evidence\artistic\`
(`index.html` = before/after gallery).

| Check | Result |
| --- | --- |
| TypeScript, Prettier | PASS |
| Vitest | 22 files, 161/161 |
| New `preferences.spec.ts` | 2/2 (defaults, persistence, reduced motion stops sprites and stage effects, system wins, no console errors) |
| Style contracts (`art-direction`, `product-ui`, `product-polish`, `preferences`) ×3 | 36/36 after real fixes: three-column dex restored, phone sheet kept inside the viewport, brand font awaited before first paint (late swap moved text under clicks) |
| Sound probe | 0 sounds on login and hover; navigation and dialogs play; no errors |
| Unified Launcher (dev, preview web) | 18/18 |
| Private review Launcher `0.25.0-preview.1` (`-PrivateCandidate -WebPreview`) | build + audit PASS (private, origin `http://127.0.0.1:4173`, updates off, unsigned, asar = previous list + Rubik + OFL); installer sha256 `51769d94…a06001342`; packaged unified checks 18/18 on a throw-away profile. Not distributed |
| Launcher Node / Electron UI | 17/17 · 28/28 |
| Full Playwright suite (`e2e-final.log`, HEAD 764a8ef) | **92 passed / 10 failed / 11 skipped** of 113. The 10 failures are exactly the inherited set of the 27C gate (final-alignment ×2, localization, participant-results ×4, performance ×2, team-preview); the two new preference tests pass. **No new regression** |
| Galleries | before 38 / after 38 captures at 1440 and 390, plus 1366, 360, dialogs, Launcher |

### Performance (Edge, 1440×900, synthetic API, median of 5)

Measured at `2086154` (before the sprite-preload and font-ready commits),
same machine and API for both builds; raw numbers in `perf.json`.

| Metric | Before (2ffdb29) | After |
| --- | --- | --- |
| Login → Home with team | 186 ms | 161 ms |
| Screen change (median of 7) | 9.7 ms | 10.7 ms |
| Long tasks / total | 2 / 140 ms | 1 / 92 ms |
| Frame rate on Home | 165 fps | 165 fps |
| Layout shift (CLS) | 0.258 | **0** |
| JS gzip | 169.3 KB | 171.4 KB |
| CSS gzip | 19.6 KB | 24.3 KB |
| Font | system | Rubik Latin 35 KB (other scripts only if used) |

### Test changes (none hides a product failure)

- `art-direction` «sections remain distinct»: waits for the area to change
  before reading its colour (React Router renders navigations as
  transitions); still requires 11 distinct colours.
- New `preferences.spec.ts` (2 tests).

## How the owner reviews it

1. In `web/`: `npm run preview:design`, then open http://127.0.0.1:4173
   (any trainer name and PIN; fictional data; nothing is saved).
2. Before/after gallery: open
   `%LOCALAPPDATA%\PokeApp-migration-evidence\artistic\index.html`.
3. Inside the Launcher (with the preview running), from PowerShell, using a
   throw-away profile so no personal save is touched:

   ```powershell
   $env:POKEAPP_LAUNCHER_PROFILE = "$env:TEMP\pokeapp-review-profile"
   & "$env:LOCALAPPDATA\PokeApp-builds\0.25.0-preview.1-private-art\release\win-unpacked\PokeApp Launcher Private.exe"
   ```

## Limits

- Not deployed: production keeps Arena until the owner approves.
- No new raster art was added: every new decoration is CSS. A future pass
  could add licensed or commissioned illustrations (stadium, trainer cards).
- The private Launcher candidate with the preview origin is built for the
  owner's review only; the stable channel is unchanged.
- Inherited E2E failures from 27B/27C remain as recorded there.

## Pending for release (unchanged)

Deploy of this redesign after owner approval, plus the 27C release items:
production 054–061, hosted verifier, Docker worker image, two-player Lime3DS,
Windows 10, Authenticode, update channel, physical certification.
