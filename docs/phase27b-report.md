# Phase27B — PokeApp Arena visual redesign (web + Launcher)

2026-10-26. **PHASE27B DONE LOCAL. Production UNCHANGED (nothing deployed, 054–061
not applied), no Launcher published, public physical writes DISABLED.** Entry
`7c00486` (27A DONE LOCAL). The owner assigned the 27B slot to the visual
redesign; the hosted-acceptance items the [27A report](phase27a-report.md) listed
as "next" remain release pending.

Design system, rules and the private preview: [design-system.md](design-system.md).

## Continuity

A first instance built most of 27B and stopped on quota at ~10:45 with nothing
committed. This session audited its working tree before changing anything:
HEAD `7c00486` = `origin/main`, 27B changes uncommitted, the preview server
still running (PID 28048, `node preview/run.mjs`, 127.0.0.1:4173/4174 only).
The earlier «Missing script: preview:design» came from running npm outside
`web/`; the script was present and `npm run preview:design` works from `web/`.
Every inherited change was kept; nothing was reset, cleaned or stashed. Files
of other agents (security-railway-supabase docs, repository-map validator,
context zip) and the protected guide were left untouched and unstaged.

## What 27B delivers

**Inherited and verified** (first instance): tokens and the Arena layer
(`web/src/design/`), 451 legacy colour literals mapped once to tokens (no
undefined tokens, no cycles, `--check` finds 0 literals left), Home game menu,
∞ inventory cards, Team Preview card width fix, Launcher stylesheet on the
shared palette with `design-sync.test.cjs`, the private preview and its
private-candidate-only Launcher integration.

**Defects found in review and fixed**

| Defect | Cause | Fix |
| --- | --- | --- |
| Only 6 distinct area colours; `art-direction.spec` (11 required) failed | Arena grouped areas | One signal per area (`--sec-*`), 11 distinct, shared by nav, page, buttons and Home tiles |
| Login/registration CTA and focus in the error pink | tokenizer mapped the legacy coral `:root --accent` to `--c-danger` | brand teal outside the shell; brand-gradient CTA |
| «MONEDA S» / «MUERTO S» on phones; «MONED…» on desktop profile; «Muertos» pill cut off in trainer cards and overlapping the inventory in the Launcher window | `min-width: 96px` pills sharing a narrow row | pills size to their label and wrap; trainer cards show stat rows beside the portrait; the profile identity switches to those rows by its own width (container query, < 520 px) |
| Dark box behind the active Admin item; «Cuentas» half hidden at 1440×900; no hint of the scrollable menu at 1366×700 | glow clipped by the scrolling nav; vertical rhythm | inner padding, compact rhythm, compact mode under 820 px height, fading lower edge |
| Two active items on /admin/cuentas | `NavLink /admin` without `end` | `end` |
| Shop icon never got its disc | `.shop-card .shop-icon` (legacy) outranked `.shop-icon` | lit counter disc applied |
| Hall card lost its gold border | `.card` (Arena) outranked `.hall-card` | gold foil border restored |
| Tags stretched across Juicios cards; adjacent tags touching | flex stretch | tags keep their size and spacing |
| Purchase dialog heading on a blue slab | legacy `--c-info-deep` | heading on the dialog surface |
| Plain links read as body text (Scouting back link, «Volver a Inicio», Cuentas link) | unstyled anchors | area-coloured links; back link with arrow |
| Home tiles left 3 empty cells (6 + 3); phone tiles of uneven height; radial «smudge» per tile | grid and decoration | complete 3 × 3 board, equal-height phone tiles, speed-stripe texture |
| Move detail panel shifted under its trigger (flaky `art-direction` 1440) | Arena lift/press transforms on the disclosure trigger | disclosure triggers stay put |
| Phone profile had a scroll inside the page scroll that cut the last item | legacy bounded inventory | one scroll per screen on phones |
| Launcher update banner muddy grey-brown | 14 % gold over navy | gold-lit banner, gold download button |

**New in this session (owner's art freedom)**

- Home: 3 × 3 game-menu board, sliding selection chevron, speed stripes; phone
  icon grid with the detail kept in the accessible name.
- ∞ items: slow holographic border (Rare Candy, Heart Scale).
- Hall of Fame: gold foil with an occasional sheen; shop cards: light sweep and
  item lift on hover.
- Pokémon hop on hover (PC, Home team, Team Preview); screen fade on route
  change (opacity only); themed scrollbars; visible 2 px focus on menu links,
  tiles, cards and buttons. All decorative motion off with reduced motion.
- New palette primitive `--c-leaf` (Mi PC).
- Launcher: section ribbons like the web, brand border on quick items, lift on
  Pokémon slots.
- Preview hardening: the production delivery headers (CSP `connect-src 'self'
  http://127.0.0.1:4174`, nosniff, DENY framing) are served by the preview, so
  the browser itself blocks any other host; `Host` other than loopback → 403
  (DNS rebinding); non-loopback `Origin` → 403; malformed requests answer
  400/no crash; the banner moved to a same-origin sheet to satisfy the CSP.
- Gallery covers the accounts mode production uses (registration, Cuentas,
  not-found route, phone menu).
- `tokenize-colors.mjs` re-runs can no longer erase the migration record.

Copy aligned with 27A (kept from the first instance): a pending robbery in the
inventory now reads «PokeApp decide el robo; la entrega física se completa en
cada partida con el Launcher», matching the 27A contract (decision and per-save
delivery shown separately). No business rule, economy, permission or
authentication change.

## Routes covered: 15/15 + 2 outside the shell

`/`, `/liga`, `/battle`, `/copa/*`, `/entrenadores`, `/entrenadores/scouting`,
`/entrenadores/:id` (profile + inventory ∞), `/pc`, `/tienda` (+ purchase
dialog), `/hall`, `/juicios`, `/saves`, `/admin`, `/admin/cuentas`, `*`
(not found); login and registration. Each at 1440 and 390 px in
`gallery-v5` (38 captures) plus targeted captures at 1366×700, 1100 and the
phone menu.

## Evidence (Windows 11, Edge via Playwright 1.63, Electron 44.7.0)

Evidence folder: `%LOCALAPPDATA%\PokeApp-migration-evidence\phase27b\`.

| Check | Result |
| --- | --- |
| TypeScript `tsc -b` | PASS |
| Vitest | 22 files, **159/159** |
| Production bundle build (scratch outDir, not deployed) | PASS |
| Prettier (src, e2e, preview) | PASS |
| Token integrity (undefined / cycles / literals left) | 0 / 0 / 0 |
| Style specs `art-direction` ×4, `product-ui`, `product-polish` | PASS (12/12 art-direction runs) |
| Design gallery (4 tests) | **4/4**, `gallery-v5` |
| Launcher Node tests | **15/15** |
| Launcher Electron UI smoke | **28/28**, `launcher-mi-partida-v2.png` |
| Preview HTTP/security probes | PASS (see design-system.md) |
| Private build `0.24.0-preview.2` (`-PrivateCandidate -WebPreview`) | build PASS, audit PASS: private, web origin `http://127.0.0.1:4173`, updates off, unsigned; installer sha256 `9cb82496…1243436` |
| Packaged Launcher over CDP, throw-away profile | **11/11**: preview origin loaded, production never loaded, no Node, no preload, CSP blocks production fetch, navigation pinned, synthetic sign-in, ∞ quick actions present (`packaged-preview-2/`) |
| Full Playwright suite (final tree, `e2e-final-27b.log`) | **86 passed / 14 failed / 11 skipped** of 111: the 13 baseline failures plus the Kaspersky-affected `wipe-revivals` read count, all reproduced on clean `7c00486`; skipped = 7 baseline + 4 gallery tests without `POKEAPP_GALLERY_DIR`. **No new regression** |

### Inherited E2E failures

The pre-redesign baseline (`e2e-baseline.log`) had 13 failures. To separate
inherited from new, the failing specs were also run on a clean worktree of
`7c00486` (`e2e-head-7c00486-subset.log`): the same 13 fail there (plus two
flaky ones), so they predate 27B. They cover voucher target selection
(`economy`, `localization`, `performance`), the empty-team text of a trainer
profile (`final-alignment`), results registration (`participant-results`,
`team-preview`) and item-use pending states (`phase23-item-use`) — expectations
or fixtures behind features from earlier phases; none is visual and 27B touches
none of those flows. Two further findings:

- `art-direction` «sections remain distinct» also fails 3/3 on clean HEAD: the
  test measured before the Batallas team arrived. Fixed in the test (wait for
  the first move) — it now passes and guards the 11-colour contract.
- `wipe-revivals` «narrow reads» fails intermittently on clean HEAD too: the
  Kaspersky browser script on this machine injects a
  `GET /3DB89D56-…/…/from` on form submission, which the test counts as an app
  read. Environmental; the «narrow reads» failures in `performance` and
  `participant-results` are likely the same interference.

## Limits

- The packaged preview was built and audited privately; it is unsigned and not
  distributed. Its PokeApp tab shows the web only while the local preview runs.
  Building it runs `npm ci` in `companion/launcher`, which removes the dev
  Electron runtime; restore it with `node node_modules/electron/install.js`
  (done in this session; dev smoke 28/28 afterwards relies on it).
- The private build `0.24.0-preview.1` of the first instance is superseded by
  `preview.2` (same security code, final native styles).
- Gallery captures are full-page screenshots: the fixed sidebar appears only in
  the first viewport (it is sticky in the real page).
- Phones with 12 destinations scroll the menu (44 px touch targets kept); the
  fading edge signals it.

## Pending only for release

Deploy of the redesigned web (with owner authorization), real two-player
acceptance on Lime3DS, hosted verifier acceptance, worker image where Docker
exists, Windows 10, Authenticode certificate, update channel, physical
certification, production 054–061. None blocks the design work.
