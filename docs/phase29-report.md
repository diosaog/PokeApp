# POKEAPP 2.0 — PHASE 29 FINAL REPORT

Date: 2026-10-27 (Europe/Madrid). Scope: one league or Liga A + Liga B per
season, admin cancellation of still-reversible robberies, Launcher transfer
notice reuse. Consolidation only: no redesign, no new feature areas.

Status vocabulary: DONE LOCAL · PASS PACKAGED · PASS HOSTED · PENDING RELEASE ·
PENDING EXTERNAL · BLOCKED.

## 1. Summary

| Area | Status | Evidence |
| --- | --- | --- |
| One league (Una Liga) | DONE LOCAL · PENDING RELEASE | SQL scenarios A1–A5, S1–S3; Python; Vitest; Playwright 1440/390 |
| Liga A + Liga B | DONE LOCAL (unchanged behaviour) · PENDING RELEASE | SQL B1–B2 + 3 inherited ranking/championship/final validators; Playwright |
| Calendars, standings, rewards, close, archive, history | DONE LOCAL | `league-pg.json`: 2, 3, 4, 5 players (one league), 4 and 6 (two leagues), played to archive |
| Cup | Unaffected | Independent engine (031/032) with no division dependency; championship records `cup_hall_status: independent_cup_certification`. Not re-exercised inside a one-league season |
| Admin robbery cancellation | DONE LOCAL · PENDING RELEASE | `robbery-pg.json` 8/8; Vitest; Playwright 1440/390 |
| Migrations 054–064 | DONE LOCAL · PENDING RELEASE (needs authorization) | `migrations-upgrade.json` 34/34, schema equal to a fresh 64-file bootstrap |
| Launcher transfer notice reuse | DONE LOCAL | `test_phase29_launcher_state`; 100 polls 1.28 s → 0.021 s |
| Production | Unchanged, verified read-only | §7 |

## 2. One league and Liga A + Liga B

The structure lives in the season config: `division_sizes {A: n}` is one
league, `{A, B}` two. It is real in SQL (063), API (`DivisionSizes.B`
optional), domain and UI — not a React-only hide.

- One league: no movement, no last-of-B reward, exact roster size, only for
  seasons with the observed initial assignment, admin only; free while draft,
  one structure per season, locked once started (`COMPETITION_STRUCTURE_LOCKED`).
- Web: «Estructura de competición» selector in Formato de la Liga, offered only
  where the server accepts it; fixed structure shown once the season runs. One
  league reads «Liga» in the matchday standings, «Inicio de la Liga» in the
  initial assignment and in tie-break fields. Two leagues keep División A/B.
  The matchday view takes divisions from the overview **and** the standings, so
  Liga B is never hidden.
- Historical seasons: no backfill; existing configs keep `{A, B}`.

## 3. Admin cancellation of reversible robberies

Only a robbery with no competitive decision and no physical effect can be
cancelled: both trainers released, the robbery item cancelled, its price
returned once, the command audited, the operation idempotent (replay returns
the same receipt; four concurrent cancellations produce one effect). Anything
decided or applied is refused (`ROBBERY_RECONCILIATION_REQUIRED`) and shown as
«Requiere conciliación». The dialog names both trainers, state and coins,
requires a reason and an explicit review.

## 4. Tests

| Gate | Result |
| --- | --- |
| TypeScript (`tsc -b`) | PASS |
| Vitest | 180/180 (25 files) |
| Python full suite | 1199/1199 — the 2 inherited failures are fixed (56a8627). The untracked `tests/test_validate_ai_repository_map.py` (not part of this phase) was neither imported nor run |
| Launcher node tests | 31/31 |
| Production web build (to a scratch folder) | PASS |
| Playwright full | 109 passed / 3 failed / 11 skipped (123) — the 10 inherited failures are gone |
| Playwright after fixes | Phase 29 spec 6/6; affected specs (daily-ranking, wipe-revivals, participant-results, league, admin, initial-assignment) 31/31 |
| PostgreSQL 17.11 — upgrade 053 → 064 | 34/34, schema identical to fresh bootstrap (previous session; the 11 pending files are byte-identical to that evidence) |
| PostgreSQL — league scenarios | 9 scenarios + 3 inherited validators PASS (previous session; SQL unchanged since) |
| PostgreSQL — robbery cancellation | 8/8 (previous session; SQL unchanged since) |

The full Playwright suite was not re-run after the last fixes; the three
failures were re-run in their specs together with every spec touching the
changed code.

### 4.1 Failures found and fixed this session

- **Regression (fixed):** tie-break labels lower-cased the division letter
  («división a»), breaking their accessible names. Labels keep «división A»;
  one league says «liga». Unit test added.
- **Unreachable option (fixed):** the structure selector offered «Una Liga» on
  older seasons the server refuses with `invalid_config`.
- **Visual (fixed):** radio inputs took the full-width text-field style; the
  selector fieldset re-gained the admin frame; table headers split inside
  words at 390 px («POS / .», «ENTRENADO / R»).
- **Environment (test adjusted, not relaxed):** this machine's Edge adds
  same-origin GUID-path requests (`/3DB89D56-…/…/from`, local security
  software). Narrow-read checks now count only `/v1/` reads and name any
  unexpected one. An earlier comment blamed a sound fetch; sound is
  synthesized, so it was corrected.
- **Inherited (fixed):** the 10 Playwright failures carried since 27C were
  specs asserting removed screens; realigned to the current UI with their
  original checks. The 2 Python failures were fixed in 56a8627.

### 4.2 Captures

`docs/evidence/phase29/web-*.png`: structure selector (two / one league),
matchday standings (one league / two), incident center robberies and the
cancellation dialog — each at 1440 and 390 px. No console errors, no
horizontal scroll.

## 5. Commits

Already local before this session: `c8a7039` (063/064), `c103c17` (robbery
cancellation API/SQL), `2bef35e` (one league), `56a8627` (Launcher notice).
This session: `4bed8a4` API types/messages · `6767d10` one league web ·
`33f68e5` robbery cancellation web · `1502681` rival picker and results dialog
fixes · `0e73676` inherited E2E realignment · `cf8a473` Phase 29 E2E +
captures · this report.

## 6. Launcher

`app/launcher/write_control.py` reuses the transfer notice while the engine
database (inode, mtime, size) and the selected save are unchanged; any change
reads again with every check, and an unreadable database is never cached as
clear. The update system (28/28 PASS PACKAGED) was not touched.

## 7. Production state — verified read-only, 2026-10-27 ~23:20

| Item | Verified value |
| --- | --- |
| Web (Cloudflare `pokeapp-web`) | Version `a7e33476` at 100 %, source `3910926`; assets `index-CF2T_spG.js`; API origin Railway production |
| Update routes | `/launcher/updates/stable.json` returns the SPA page: channel not deployed |
| API (Railway `pokeapp-api`) | Deployment `22d96f80` SUCCESS, image `sha256:1ac8a528…` = source `501a399` (27C record); health ok; OpenAPI 88 routes; no incident, item-use or transfer routes; `DivisionSizes` requires `B` |
| Public Launcher | 159 293 410 bytes, SHA-256 `f02eccd0…83d3fa` = 0.25.0 |
| R2 | `windows/0.25.0/` present; **`windows/0.26.0/` absent** |
| Migrations 054–064 | Not queried (no database credentials used). Consistent with NOT APPLIED: the hosted API predates them |
| Physical writes | OFF — the hosted API has no item-use or transfer routes |
| Incident center | OFF — route absent (404) |
| Auto-deploy | None: Railway service has no repo source; Cloudflare deploys come from wrangler; the only GitHub workflow builds the Linux bridge on `Bridge/**` changes |

Nothing was deployed, migrated or published in this phase.

## 8. Why nothing was published

The new-publication policy asks to ship validated, independent and safe
changes. None of Phase 29 is independent:

- One league needs 063 + the new API; the hosted API rejects `{A}` (422). A
  web-only deploy would show an option that cannot work.
- Robbery cancellation needs 062 + 064 + the new API + the incident flag.
- The web at HEAD announces Launcher 0.26.0 (`web/launcher-release.json`), whose
  installer is not in R2: «Descargar Launcher» would break.

## 9. Release plan (each step needs the owner's explicit authorization)

Order: database → API → web → Launcher. 054–064 are additive (no function
dropped, no grant revoked), so the current API keeps working between steps.

0. **Pre-flight (read-only):** list remote migrations and confirm exactly
   001–053 applied; confirm no season is mid-close and no robbery or item use
   is pending; record row counts of trainers, seasons, coin ledger, purchases.
1. **Backup:** Supabase backup/PITR point plus a logical dump of the public
   schema, stored outside the repo. Note its time.
2. **Migrations:** apply 054 → 064 once each, in order, each file in its own
   transaction as written. Stop at the first error (an error rolls that file
   back). Never replay 055 after 061 (`UNSAFE_HISTORICAL_REPLAY`). Rollback is
   fix-forward; restore from step 1 only for data loss.
3. **Verify DB:** the 8 new tables exist, force RLS and are closed to
   anon/authenticated (as in the upgrade proof); row counts unchanged;
   existing season reads unchanged.
4. **API:** deploy HEAD to Railway with `POKEAPP_ADMIN_INCIDENTS_ENABLED=true`;
   keep `POKEAPP_ITEM_VERIFICATION_TRANSPORT_ENABLED` and
   `POKEAPP_TRANSFER_ENGINEERING_ENABLED` unset (physical writes OFF).
   Rollback: redeploy `22d96f80` (image `1ac8a528…`).
5. **Verify API:** health; OpenAPI 104 routes; `DivisionSizes.B` optional;
   protected routes 401 without a session; admin incident overview reads.
6. **Launcher artifact:** before the web, either upload a public 0.26.0
   installer built from this HEAD to `windows/0.26.0/` (unsigned, as every
   public build so far; updater channel stays off), or set
   `web/launcher-release.json` back to 0.25.0 for this deploy.
7. **Web:** build with the production API URL, `npm run deploy`. Rollback:
   `wrangler rollback` to `a7e33476`.
8. **Hosted acceptance:** login, Liga (existing season unchanged, División A/B),
   Administración → three areas, incident center reads, installer HEAD and
   hash, no console errors at 1440/390. A one-league season and a robbery
   cancellation are verified only on synthetic data or a new draft season,
   never on live players' data without consent.

Only after step 8 can anything be called PASS HOSTED.

## 10. Still pending

- PENDING RELEASE: steps 0–8 above.
- PENDING EXTERNAL: Launcher signing key and update feed, Authenticode,
  Windows 10, two real players on Lime3DS, hosted verifier and Docker worker,
  physical-write certification.
- Not covered: a Cup played inside a one-league season (engine independent of
  divisions, not exercised together).

## 11. Next action

Authorize steps 0–3 (backup and migrations 054–064), then 4–8 in the same
window.
