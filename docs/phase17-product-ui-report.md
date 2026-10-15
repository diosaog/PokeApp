# Phase 17 — full product / UI rework

Closed 2026-10-15. **STATUS: PHASE 17 DONE. PRODUCT/UI REWORK: COMPLETE.**
Privacy PRESERVED; competitive logic UNCHANGED; Launcher final parity DEFERRED;
physical save writes NOT STARTED. [Evidence](phase17-product-ui-evidence.json),
[live record](work-in-progress/phase17-product-ui-live.md).

Entry `9efd5b324ac48dc86a54f0a9bbde519d7e5a3917`, main/origin synchronized.
17A–17F completed sequentially. Final application source
`20334d1a5fed571c38097c593c9335a1dfd48780`, committed/pushed before deployment.
Documentation closure follows separately; obtain its exact HEAD from Git.

## Visual system, assets and navigation

Deep green surfaces, coral actions, compact typography, reusable cards, sprites,
photos, badges, type labels, item images, Pokémon modal and move popover. Existing
sidebar order and authorized Admin entry remain. Mobile navigation now closes
even when selecting the current page and has an explicit close button.

1,363 available files verified against the asset manifest; the complete static
visual package is 2,207,611 bytes. Pokémon 1–721 use canonical game images,
items use explicit game-index mapping, and battle categories use canonical
Showdown-style icons. Existing trainer/shop/Sinnoh art is reused and resized;
originals remain intact. Missing images and unknown identities have honest
fallbacks, including 102 unavailable item images. No external runtime asset hosts.
[Source attribution and retained licenses](../web/public/visuals/v1/ATTRIBUTION.md)
and pinned hashes accompany the reproducible asset builder.

Images load individually/lazily; 617 Spanish move descriptions load locally on
interaction. Move mechanics are explicitly **Pokémon X/Y reference**, because the
current team projection does not identify its game. Null power/accuracy stay
unavailable. Admin loads separately: main JS approximately 480.5 kB / 152.4 kB gzip,
Admin 26 kB / 7.6 kB gzip. Existing HTTP revalidation/ETags retained.

## Screens — before / after

| Surface | Delivered presentation |
| --- | --- |
| Inicio | Seven scattered cards become four blocks: current battle, official Puntos/Monedas/Muertos, current game team with separate Team Lock status, and progress. |
| Liga | Classification is primary, with trainer identity, exact totals, reached-day navigation and existing official podium/divisions/results. |
| Batallas / Team Preview | Six compact cards in two columns on desktop; one column where needed. Four move positions are directly visible; authorized own ability/nature remain visible, IVs/EVs expand. |
| Move popover | Keyboard/click/touch interaction; Spanish name, type, canonical category icon, power, accuracy and description. Escape/light dismissal work. |
| Entrenadores | Alphabetical 3/2/1 cards, rectangular photos, Puntos/Monedas/Muertos in that order, earned/subdued badges, TÚ and inactive treatment; coral Ver Equipo y Cajas. |
| Trainer profile | One internal identity page with Equipo/Cajas/Muertos. Own current PC; rival approved public team and explicit private-box boundaries. No history tabs. |
| Mi PC | Six party slots and one populated box at a time replace the long list; arrows, bounded search and sprite grid. API omits empty boxes, so capacity is not invented. |
| Pokémon popup | Sprite, nickname/species, level, types, held item and moves; own-only ability/nature/IVs/EVs. Public modal never renders private fields. |
| Tienda / inventario | Four categories retained; actual art, clear prices/coins/actions and scannable purchases/vouchers. Confirmation/retry and redemption rules unchanged. |
| Copa | Existing rounds displayed as tournament columns on desktop and stacked rounds on mobile; real participants/results only; human state labels. |
| Hall | Trophy/portrait showcase, available season names, certified winners and existing Cup links. Intentional empty state; no fabricated finalist or team. |
| Juicios | Existing Discord decision/history workflow; human status/sanction labels and consistent cards/forms. No new voting or workflow. |
| Saves y Launcher | Current save, last synchronization, direct download/version and observed progress. Raw parser status removed. |
| Admin | Consistent spacing, grouping, fields, warnings and hierarchy; existing eligibility, confirmations, stale-state and uncertain-outcome guards preserved. |

## Validation, mobile and privacy

**104 React tests PASS**: 103 passed the closure run; the Hall mock needed the new
existing-season read and passed its focused rerun. **76 unique headless Edge cases
PASS**: 67 initial passes, nine corrected cases and one extra navigation-guard
recheck. Initial failures included obsolete copy/fixture expectations, injected
local antivirus traffic in the asset-host check, and a real same-page mobile drawer
bug. The drawer was fixed; only invalidated cases were repeated. No security
software setting was changed. Final application page errors: zero.

Desktop 1440, intermediate 900 and mobile 390 screenshots reviewed, plus existing
long-name/table responsiveness. Covered box navigation, modal viewport/focus,
move popovers, all screens, empty/error/unknown progress, direct download link,
own/rival privacy, exact decimals, command payloads, stale revision and safe retry.
Synthetic data only; no owner competitive mutations. TypeScript/Vite, formatting,
diff, asset hashes, asset-builder compile/Ruff and Worker dry-run PASS. Python
application, PG, parser, installer and historical matrices were not rerun: their
sources/contracts were unchanged.

## Delivery and preservation

Cloudflare **fd5cb5e3-c582-4923-b39c-1ca5b6a27175**, version
**49eb0430-3443-4555-b60b-53cae0a4538e**, 100%, final source above.
[Production web](https://pokeapp-web.pokeapp-v2.workers.dev).
The first coherent deployment `7db70c94-bc94-4ba7-81c6-4a2a2f92e7d8` was followed
by one small correction: the public mobile login screenshot exposed joined words
when a line break was hidden. Explicit spaces were added; final public proof was
repeated. No checkpoint-by-checkpoint deployments were made.

Final hosted proof: **23 HTTP checks** (nine routes/config/API/security checks,
13 exact built/static-asset comparisons, one installer HEAD) and **10 real browser
visits** at desktop/mobile, no interception or credentials submitted. SPA routes
retain the login gate, CSS/JS including lazy Admin match the build, API health and
unauthenticated denial/CORS pass; no unexpected 5xx. Installer remains 159,086,018
bytes; no installer upload/download-body or new checksum claim.

Railway, Supabase, V1/Shadow, Streamlit, Launcher source/artifacts and the existing
Worker download handler/configuration are unchanged. No DB, Storage or business
write was performed. No fresh full DB equality comparison is claimed for this
frontend-only delivery. Hosted authenticated owner acceptance was not repeated;
authenticated product/command/privacy journeys are local fixture evidence.
Protected guide and unrelated untracked files were untouched. No Phase17 local
server/browser runner remains; no PostgreSQL was started. Screenshots/raw evidence
are retained under `%LOCALAPPDATA%/PokeApp-migration-evidence/phase17/20261015`.

## Deferred questions and next action

Rival boxes/dead-box detail/inventory remain private under current projections.
Hall winning-team snapshots are absent from its DTO; live PC is never substituted.
Missing photos, non-Sinnoh badge artwork and missing item images use fallbacks.
No alternate forms or game-specific move mechanics are guessed. The old scouting
deep link remains compatible; the roster now leads directly to internal profiles.
No new Juicios concept was invented.

Final Launcher should share the finished React frontend near release, adding native
local-first capabilities. That integration, ORAS/Gen7, physical writes and signing/
updating are not started here. **STOP: return to Antonio for product review.**
