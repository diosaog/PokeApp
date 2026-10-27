# POKEAPP — LAUNCHER AUTOMATION & ADVANCED ADMIN FINAL

Phase 28 («Launcher definitivo y administración avanzada»), 2026-10-27.
Entry `a392042`; resumed the interrupted, uncommitted Launcher work without
discarding it. **DONE LOCAL — not deployed, not published.** Production is
exactly as before (see §6). Contracts: [phase28-launcher-admin.md](phase28-launcher-admin.md).
Evidence: [phase28-evidence.json](phase28-evidence.json), [evidence/phase28/](evidence/phase28/).

Legend: **PASS LOCAL** (repository, unit/integration/e2e, disposable
PostgreSQL) · **PASS PACKAGED** (private installer build, packaged app driven
with an isolated profile) · **PASS HOSTED** (production) · **PENDING EXTERNAL**
(needs a gate outside this machine) · **BLOCKED**.

## 1. Status by capability

| Capability | Status | What was proved | What remains |
| --- | --- | --- | --- |
| Save detection | PASS LOCAL · PASS PACKAGED | Lime3DS/Azahar/Citra paths listed and `stat`ed only; packaged app with an isolated APPDATA holding two synthetic files lists both and opens the selector | Real emulator saves of two players (Lime3DS certification) — PENDING EXTERNAL |
| Automatic choice | PASS LOCAL · PASS PACKAGED | One → chosen and remembered; several → selector once + notice; none → empty state; remembered save never replaced; new saves announced (path hashes) | — |
| Persistent session / one sign-in | PASS LOCAL | DPAPI session in the core; web gets an access token only, never refresh; renewal through the Launcher; logout withdraws the web token at once; preview/foreign APIs never share | Real account round trip needs the new web on production — PENDING EXTERNAL (owner deploy decision) |
| Automatic sync (real cycle) | PASS LOCAL | Existing engine (watch → stable → hash → one outbox row per content → `/receipt` before upload → CAS → read-back) plus new gates: torn bytes never queued, same content once, new content replaces the unsent snapshot, nothing after logout, auto-consent at sign-in with shared-PC protection | Hosted sync with the owner's account and a real emulator — PENDING EXTERNAL |
| Backups | PASS LOCAL · PASS PACKAGED | Real list (game, date/time, type, integrity, retention), export, hub tab | — |
| Restore with «Confirmo» | PASS LOCAL | Main-issued single-use ticket bound to that backup of that save + exact word + closed emulator + no open robbery; engine saves the current state first | Physical restore stays engineering-only in packaged builds (unchanged policy) — PENDING EXTERNAL certification |
| Inventory (Rare Candy, Heart Scale ∞) | PASS LOCAL · PASS PACKAGED | Compact rows; Launcher: native popup (quantity ±/typed, bag limit, confirmation, to the bag, never to a Pokémon); browser: honest popup + download | Physical add-to-bag is still disabled publicly — BLOCKED by certification gate (by design) |
| Simplified navigation | PASS LOCAL · PASS PACKAGED | «Escritorio» group removed, functions relocated, legacy links resolved, same sidebar in web and Launcher | — |
| Contextual robberies | PASS LOCAL | Inventory robbery cards → native deliveries dialog; Launcher notice strip; admin read-only robbery cases | — |
| Updates | PASS LOCAL · PASS PACKAGED | «Descargar Launcher» (browser) / «Buscar actualizaciones» (Launcher) re-runs the signed-manifest check; honest «no channel» popup; install needs a ticket for that version | Signing key, feed, Authenticode — PENDING EXTERNAL |
| League administration | PASS LOCAL | Three areas; all previous tabs and tools preserved; live refresh (20 s polling + invalidation after receipts) | — |
| Economic administration, refunds, cancellations | PASS LOCAL | Migration 062 + API + console: cancel pending, refund used, coin corrections; wallet lock, idempotent receipts, one reversal per purchase, never below zero, archived frozen | Apply 062 and enable the flag — PENDING RELEASE (owner authorization) |
| Incidents | PASS LOCAL · **PARTIAL** | Purchases linked to revive/robbery are listed and refused (no silent reversal); robbery cases with delivery state, read only | An admin command to cancel a *reversible* (not yet applied) robbery was **not** built: it must be designed on the 057–061 transfer flow, itself not in production. Requesters keep their existing pre-decision cancel |
| Audit | PASS LOCAL | Append-only `admin_incident_commands` (forced RLS, no grant, update/delete/truncate refused), reason required, actor, result, history in the console | — |
| Electron security | PASS LOCAL · PASS PACKAGED | Web sandboxed without preload/Node/IPC; allow-listed routes and bridge codes; forged/stale confirmations refused; foreign navigation blocked; offline fallback | — |

## 2. What changed

**Launcher (native, `companion/launcher`)** — «Saves y Launcher» hub (Mis
partidas · Copias de seguridad · Launcher), Liga Nocturna save card and sync
chip, notices strip, dialogs: save selector, restore, updates, items and
deliveries sheets, generic confirmation. Native message boxes replaced by
in-app dialogs whose text and ticket come from main
(`confirmations.cjs`); main re-validates every step before the core runs it.
Fixes found in review: dialog headers hidden in modal mode, duplicated sheet
titles, `close` events not delivered while not painting (closing is now
synchronous).

**Core (`app/launcher`)** — automatic save choice, `modified` times, new-save
notice by path hash, `last_synced`, access-token handoff for the Launcher's
web view (never in `state()`), immediate withdrawal on logout, auto-consent
with shared-PC protection.

**Web** — one navigation, `/saves` hub, compact infinite items, session bridge
(`launcher.ts`, `api/client.ts`), admin console in three areas with the
incident center, live polling option in `useRead`, incident invalidation.

**Backend (local only)** — migration 062, `/v1/admin/seasons/{id}/incidents`
(off unless `POKEAPP_ADMIN_INCIDENTS_ENABLED=true`), regenerated bootstrap and
web types, upgrade validator now 054–062.

## 3. Security decisions

- Moving confirmations into the app does not move trust into the renderer:
  main writes the text from the core's state, issues the ticket (single use,
  120 s, bound to kind/target/state fingerprint), and re-checks; the core and
  the server check again. A stale, reused, swapped or forged ticket is refused
  (unit tests and packaged IPC test).
- One sign-in never shares the refresh token; credentials pass only through
  main's memory for the one login request; the token never travels in a URL,
  log or renderer state; preview builds cannot obtain real tokens.
- Admin commands are checked twice (API dependency and inside each SQL
  function), run under the wallet lock, keep receipts for retries and never
  delete history.

## 4. Tests

| Gate | Result |
| --- | --- |
| Launcher UI smoke (Electron) | 46/46 |
| Launcher node tests (confirmations, webview, updater, quantity, design sync) | 26/26 |
| Python Phase 28 Launcher | 16/16 |
| Python incident API | 8/8 |
| Python full suite (`PYTHONPATH=tests`) | 1203/1205 — 2 inherited |
| Vitest | 173/173 |
| Playwright full | 96 passed / 10 inherited / 11 skipped (117) |
| PostgreSQL 17.11 incident gates (062) | 10/10 |
| PostgreSQL upgrade 053 → 062 vs fresh bootstrap | 30/30, schema identical |
| Private package audit | PASS |
| Packaged acceptance (isolated profile + APPDATA) | 28/28 |

### 4.1 Full suites and inherited failures

- Python, 1 205 tests: the only failures are inherited and unchanged —
  `test_accounts_transport…capability_off_default…` (capabilities payload grew in
  an earlier phase) and the `test_phase16` 0.2 s timing assertion (machine load;
  also fails on a clean `a392042` worktree). Run with `PYTHONPATH=tests`:
  without it `test_phase22c_handoff` subprocesses cannot import their fixtures
  (environment, also inherited; 13/13 with the path).
- Two contract tests were **extended** for migration 062, not relaxed: the
  migration list, the bootstrap source line and the RLS expectations of
  `admin_incident_commands` (`test_supabase_v2_schema`), and the admin route
  count (`test_api_season_admin`: 40 at entry — the account routes had never
  been counted — plus the 3 incident routes = 43; every route still must carry
  security).
- Playwright: the 10 failures are exactly the set inherited since 27C
  (final-alignment ×2, localization, participant-results ×4, performance ×2,
  team-preview). New: launcher-shell 2/2, admin-incidents 2/2.

## 5. Private build

`0.26.0-preview.1`, `-PrivateCandidate -WebPreview` (loads the local design
preview `http://127.0.0.1:4173`), unsigned, updater off, **not installed over
the owner's Launcher and not published**. Installer
`PokeApp-Launcher-Private-Setup.exe`, 159 307 708 bytes, SHA-256
`1e25c65ff80f5781275cabab37ca2c2a127c29f99acd36e09a9cf9b5bd94a5ba`, built in
`%LOCALAPPDATA%\Temp\pk28-b3-0.26.0-preview.1\release`. Owner review: run
`npm run preview:design` in `web/`, then the unpacked
`PokeApp Launcher Private.exe`.

## 6. Production state (unchanged)

Web Cloudflare `a7e33476` (source `3910926`); API Railway `501a399`; public
Launcher `0.25.0` (0.20.0 kept); database without 054–062; physical writes
OFF; incident center off. Nothing deployed, migrated or published in this
phase.

## 7. To release (needs the owner's authorization)

1. Deploy the web (27C procedure) — enables the simplified navigation, hub,
   compact items and the session bridge on production.
2. Apply 054–061 (pending since 27C), then 062; set
   `POKEAPP_ADMIN_INCIDENTS_ENABLED=true`; redeploy the API.
3. Publish a Launcher built from this HEAD (public build, no `-WebPreview`).
4. External gates unchanged: Docker worker, hosted verifier, two real players
   on Lime3DS, Windows 10, Authenticode, update channel, physical certification.

## 8. Not done in this phase

- Admin cancellation of reversible robberies (see §1).
- Real-account and hosted validation (requires deployment).
- Native web design for the browser «Copias» tab beyond capability cards
  (backups live on the player's PC by design).
