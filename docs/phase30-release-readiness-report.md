# POKEAPP 2.0 — PHASE 30 RELEASE READINESS REPORT

Date: 2026-10-28 (Europe/Madrid). Scope: bring the validated work (one league /
Liga A + Liga B, advanced administration, compatible improvements) to
production with the least risk. No new features. **Nothing was written to
production**: every remote action was a read. The release itself waits for the
owner's specific authorization (§11).

Status vocabulary: DONE LOCAL · PASS PACKAGED · PASS HOSTED · PENDING RELEASE ·
PENDING EXTERNAL · BLOCKED. Evidence: [release-readiness.json](evidence/phase30/release-readiness.json),
[cup-single-league-pg.json](evidence/phase30/cup-single-league-pg.json),
[hosted-before.json](evidence/phase30/hosted-before.json). Private evidence
(backup, raw audit, rehearsal log) stays in `%LOCALAPPDATA%/PokeApp-migration-evidence/phase30/`,
readable only by the owner and SYSTEM.

## 1. Controls

| Control | Result |
| --- | --- |
| Production state verified (Supabase, Railway, Cloudflare, R2) | PASS — §2 |
| Migrations really applied: 001–053, none of 054–064 | PASS — §3 |
| Production schema = repository 001–053 (catalog, definitions, owners, ACLs) | PASS — 1,107 columns, 137 functions, 107 policies… identical |
| Verified backup (restorable, exact rows and catalog) | PASS — §4 |
| Rehearsal 054–064 on the real backup, production privileges | PASS 24/24 — §5 |
| Data loss / historical seasons altered | PASS — none: 85 existing tables byte-identical, 42 API reads identical |
| RLS and privileges after 054–064 | PASS — 8 new tables force RLS, no new anon/authenticated privilege |
| Cup inside a one-league season | PASS 4/4 — §6 (was not covered in Phase 29) |
| TypeScript · Vitest · Python · SQL validators | PASS — tsc, 185/185, 1199/1199, parity + rehearsal + Cup |
| Playwright full suite from HEAD | PASS — 112 passed, 11 skipped, 0 failed (123) |
| Launcher updater not regressed | PASS — code unchanged since the 28/28 packaged rehearsal; node 35/35 |
| Web compatible with the public Launcher 0.25.0 | FAIL found → fixed (`2c14341`) → PASS — §7 |
| Physical save writes stay OFF after the release | PASS — §8 |
| Public hosted checks (before) | PASS 14/14 + browser 1440/390 |
| Hosted acceptance (after) | PENDING RELEASE — §10 |

## 2. Production state (read-only, 2026-10-28 00:12–00:40 CET)

| Service | Verified |
| --- | --- |
| Supabase V2 `uwleqeuzsveqlugugzba` «Pokeapp 2.0» | ACTIVE_HEALTHY, PostgreSQL 17.6.1.155, eu-central-1 |
| Platform backups | **None listed, PITR off** (WAL-G on). The logical backup of §4 is the only recovery point |
| Data | 1 trainer (owner), 1 Auth user, 1 season in **draft** (Liga A + Liga B config), 62 shop items, 2 settings, V1 shadow (135 rows). No season players, coins, purchases, redemptions, saves, Cups or Hall entries |
| In-flight work | 0 active seasons, 0 open matchdays, 0 pending purchases, 0 robberies |
| Security Advisor baseline | 24 ERROR (all `security_definer_view`, known since 24-Oct), 6 WARN, 40 INFO — step 3 compares against it |
| Railway `pokeapp-api` | Deployment `22d96f80` (source `501a399`), sleeps when idle; health 200; 88 routes; `DivisionSizes` requires A and B |
| Railway flags | `POKEAPP_ADMIN_INCIDENTS_ENABLED`, `…ITEM_VERIFICATION_TRANSPORT_ENABLED`, `…TRANSFER_ENGINEERING_ENABLED` unset (OFF); account management on |
| Cloudflare `pokeapp-web` | Version `a7e33476` at 100 % (web `3910926`); earlier `60cb95a3`, `4a8fffed` |
| Public download | `/launcher/download` = R2 `windows/0.25.0/…` — 159,293,410 bytes, SHA-256 `f02eccd0dbef2579218b7b1f4a14c6ebfcaa398433b7022827038659e983d3fa` (downloaded and hashed) |
| R2 `pokeapp-launcher-releases` | 0.16.1, 0.16.2, 0.18.0, 0.19.0, 0.20.0, 0.25.0. **No 0.26.0, no update feeds** |
| Update channel | Not deployed (the live Worker predates the `/launcher/updates/*` routes) |

## 3. Migrations

History: 45 records, `010_security_helpers` … `053_versioned_account_credentials`.
001–009 predate the history table; their objects are in the parity catalog. One
extra record, `030_trials_sanctions_acl_completion`, is a `revoke` already
inside the repository's `030` (parity confirms). **054–064: not recorded, none
of their objects exist.**

| File | What it does | Touches existing data/flows | Risk |
| --- | --- | --- | --- |
| 054 | Item-use authorizations + verifications (2 tables), service-only RPCs | Trigger on `redemptions` (blocks redeeming an item reserved for a use) | Low |
| 055 | Replaces `commit_pokemon_identity_v038` (same signature) | Save-identity reconciliation on every upload; superseded again by 058 | Low within the sequence; **never replay 055 after 058** |
| 056 | Verifier role (`nologin`), `item_use_artifacts`, restrictive policy on `storage.objects` | Denies browser access to `raw-saves/item-use/*` only | Low — needs `supautils.policy_grants` for postgres on `storage.objects`, **verified present**; same pattern as 044/051 |
| 057 | Transfer reservations (2 tables) | Triggers on `season_players.current_save_file_id`, `pokemon_identity_revisions`, `redemptions`, `item_use_authorizations` — no-ops without a transfer | Low |
| 058 | Provenance + permits (2 tables); replaces 055's function | Same identity function | Low |
| 059–061 | Transfer reads, party origin, adjudication | 061: trigger on `team_locks` (blocks a lock change during a robbery) | Low |
| 062 | Incident center (`admin_incident_commands`, append-only) | None | Low |
| 063 | One league: structure guard, 4 admin config RPCs replaced | Existing configs keep `{A, B}` (no backfill) | Low |
| 064 | Admin robbery cancellation | None | Low |

All eleven are additive for the existing schema: no column, function signature
or grant of an existing object is removed. Every file is its own transaction.
The old API (`501a399`) keeps working after them (proved: identical reads).

## 4. Backup and restore

- **Captured** 2026-10-27 23:16 UTC, read-only: one `REPEATABLE READ READ ONLY`
  transaction exports its snapshot; `pg_dump` runs on that snapshot while the
  same transaction fingerprints all 107 tables (count + MD5 of every row) and
  records the catalog. Archive `pre-release-20261027T231606Z.dump`, 1,274,391
  bytes, SHA-256 `94ab28edad0f3002ead5c62b32088b0702c1ce5029a479568e446f764fff56db`.
  Schemas public, auth, storage, v1_shadow, supabase_migrations. Signed-in
  session tokens (`auth.sessions`, `refresh_tokens`, MFA, one-time tokens,
  flow state) are never copied: after a restore, people sign in again.
  Storage holds 0 objects, so there are no file bytes to back up.
- **Where**: owner-only folder (ACL owner + SYSTEM), outside the repository.
- **Restore proved** into an isolated Supabase-shaped cluster (inside that
  folder, deleted afterwards): rows of all 107 tables identical; catalog
  identical to production modulo three documented `pg_dump` round-trip
  representations (owner-only ACL shown explicitly vs. NULL; an `IN` list
  stored as nested ORs re-parses flat; `USAGE` on `public` for PUBLIC is a
  default `pg_dump` omits — **the restore procedure re-grants it**).
- The connection is the Supabase CLI's short-lived platform login (same as
  the 24-Oct release). No password or token was printed or stored.

## 5. Rehearsal 054–064 on the real backup — PASS 24/24

The local cluster reproduces production's privileges (checked by the parity
above): `postgres` is not a superuser, Supabase default privileges grant
anon/authenticated on new objects, pgcrypto lives in `extensions`. Phase 29's
proof ran as a superuser without those defaults; this one does not.

Restore exact (rows, catalog, history without 054–064) → 42 API reads answer →
054…064 each apply once as `postgres` → 85 existing tables byte-identical
(seasons, economy, saves, history, V1 shadow, storage) → 42 reads identical
(league, initial assignment, current matchday, progress, 38 public views) →
no privilege removed and **no new privilege for anon/authenticated** on any
table, view or function → 8 new tables force RLS → verifier role without
login/superuser/bypass → existing configs keep Liga A + Liga B → upgraded copy
equals a fresh Supabase-shaped 001–064 build.

Finding: in plain PostgreSQL, 056 fails with `must be owner of table objects`.
Production allows it through `supautils.policy_grants` (read from
`pg_settings`); the rehearsal emulates exactly that while 056 runs. Not a
production defect, but the reason a superuser rehearsal is not enough.

Pre-flight of the release tool (dry-run, read-only): 45 records, 11 files to
apply with the rehearsed bytes, nothing in flight, backup rehearsed, 0 problems.

## 6. Suite

| Gate | Result |
| --- | --- |
| TypeScript `tsc -b` | PASS |
| Vitest | 185/185 (26 files) |
| Python full suite | 1199/1199 (foreign `tests/test_validate_ai_repository_map.py` neither imported nor run) |
| Playwright full, from HEAD 5cff48e + the 0.25.0 fix | 112 passed, 11 skipped, 0 failed (123) |
| Playwright Launcher specs after the fix | 6/6, Launcher 0.25.0 at 1440 and 390 px |
| Worker / Launcher node | 4/4 · 35/35 (×6; one isolated failure while the machine ran Playwright and PostgreSQL together, not reproduced) |
| Production web build (scratch folder) · Prettier · ruff | PASS |
| Cup in a one-league season (PostgreSQL 17.11, 001–064) | 4/4: Swiss + doubles Cups certified during the league; standings, points, coins and champion equal a Cup-free twin; Hall keeps 1 league + 2 Cup entries; archive/history read both; a later Cup leaves history byte-identical |
| Phase 29 SQL evidence (league 9 scenarios, robbery 8/8, upgrade 34/34) | Reused: the SQL is byte-identical |

## 7. Launcher

**Decision kept: the public download stays 0.25.0.** `web/launcher-release.json`
announces 0.25.0 again, so the download card and the Worker's download key
name the object R2 really serves. `companion/launcher` stays 0.26.0 and the
updater (28/28 PASS PACKAGED, Ed25519 + SHA-512, downgrade refusal…) is
untouched for a later phase.

**Regression found and fixed (`2c14341`).** The web at HEAD was built for
0.26.0, whose native hub opens at `/saves`. Inside 0.25.0 it would have hidden
the native «Mi partida», «Copias» and «Conexión» panels (backups and restore
included), because 0.25.0 opens them only from the 27C routes the new sidebar
no longer links. Now, inside 0.25.x only, «Saves y Launcher» links to
`/escritorio/partida|copias|nube` and offers no update check that version
cannot perform. Verified against 0.25.0's own `webview.cjs`: every route the
new web produces maps to its panel; `/__launcher/session|logout` are blocked
in place (harmless: sign-in works as today). 0.25.0 still finds `.sidebar` to
place its panels.

## 8. Physical writes

They stay OFF and the release cannot turn them on: `PRODUCTION_MUTATIONS` is an
empty set compiled into the Launcher (HEAD and 0.25.0); only an in-process
engineering capability that no packaged build constructs bypasses it. With
their flags unset, the API's item verification and transfer routes answer 503.
The release sets only `POKEAPP_ADMIN_INCIDENTS_ENABLED=true`, and only after
062/064 are applied and verified. No robbery, restore or Pokémon change is
activated.

## 9. Release plan (owner authorization required)

Order: backup → database → API → web. R2 is not touched. Expected window
≈ 45 min. `EV` = the private folder; `PG` = the PostgreSQL 17.11 `bin`.

| # | Step | Command / check | If it fails |
| --- | --- | --- | --- |
| 0 | Pre-flight (read-only) | `python -m tools.phase30_apply_migrations --dir EV` → 0 problems | Stop; nothing changed |
| 1 | Fresh backup + rehearsal on it | `python -m tools.phase30_backup_rehearsal capture --pg-bin PG --dir EV`, then `rehearse --dump <new>.dump --output EV/rehearsal.json` → PASS 24/24 | Stop; nothing changed |
| 2 | Migrations 054→064 | `python -m tools.phase30_apply_migrations --dir EV --backup <manifest> --apply --owner-authorized` (stops at the first error; that file rolls back) | Fix-forward: reconcile the failed file from its intent/result, never reapply blindly; old API keeps working. Restore only for data loss (§9.1) |
| 3 | Verify DB | `phase30_release_audit parity --upto 64` → identical; new `capture` → fingerprints of the 107 previous tables equal step 1; Security Advisor without new ERROR | Fix-forward; API/web not yet changed |
| 4 | API | `railway variables --set POKEAPP_ADMIN_INCIDENTS_ENABLED=true --skip-deploys` (IDs in `deploy/README.md`), then `build_api_deploy_bundle` from the pushed HEAD and `railway up … --path-as-root --detach` | Railway dashboard → Rollback to `22d96f80` (image `sha256:1ac8a528…`), unset the flag. Safe: the schema is additive |
| 5 | Verify API | health 200; 104 routes; `DivisionSizes` requires only A; protected routes 401; incident overview reads | As 4 |
| 6 | R2 | No action: 0.25.0 stays | — |
| 7 | Web | `cd web; $env:VITE_API_BASE_URL='https://pokeapp-api-production.up.railway.app'; npm run build; npm run deploy` | `npx wrangler rollback a7e33476-698c-4f7e-b4cf-60c46032d9f2` |
| 8 | Hosted acceptance | `phase30_hosted_acceptance --stage after --full-download`, `node tools/phase30_hosted_browser.mjs …`, then §10 walk-through | Roll back web (7), then API (4) as needed |

Only after step 8 passes can anything be called PASS HOSTED.

### 9.1 Recovery

- Failed migration: that file rolls back by itself; later files are not
  applied; the old API and web keep working. Diagnose, fix forward in a new
  migration, rehearse, apply.
- Data loss (not expected; nothing in 054–064 deletes or rewrites rows):
  restore the step-1 archive into a scratch database, then copy back only the
  affected tables after the owner approves. A full restore into the project
  needs the owner (Dashboard), re-granting `USAGE` on `public` to PUBLIC, and
  everyone signing in again.
- API: Railway rollback (4). Web: `wrangler rollback` (7). Each is independent
  of the database because 054–064 are additive and the web tolerates both APIs
  (one league and the incident center appear only where the server accepts them).

## 10. Hosted acceptance (after the release)

Automated, no session: web/API/download/channel/CORS/traversal (14 checks; the
`before` run passed against today's production) and the sign-in screen at 1440
and 390 px without console errors or horizontal scroll.

Owner walk-through, **read-only** (no purchases, robberies, season or config
changes), browser at 1440 and 390 px and inside Launcher 0.25.0: sign in ·
every sidebar section · Liga (the draft keeps Liga A + Liga B) · Administración
(three areas; incident center reads, no robberies) · Economía/Tienda/Inventario
(lists only) · Clasificaciones · Copa · Historial · Scouting · «Saves y Launcher»
(browser: download v0.25.0; Launcher: the three panel links open Mi partida,
Copias and Conexión) · the downloaded file's SHA-256 · no console errors.

A one-league season and a robbery cancellation are proved on synthetic data
(Phase 29 + §5/§6); proving them hosted would need a new draft season or test
accounts in production — a separate authorization, not part of this release.

## 11. Actions that need the owner's approval

1. Steps 1–3: fresh backup, **apply 054–064 to production**, verify.
2. Step 4: set `POKEAPP_ADMIN_INCIDENTS_ENABLED=true` and **deploy API HEAD** to Railway.
3. Step 7: **deploy web HEAD** (with the Worker's read-only update routes; no feed is published).
4. Optional, separate: synthetic data in production for hosted one-league/cancellation checks.

Not requested: physical-write flags, R2 uploads, a new Launcher, the update feed.

## 12. HEAD and commits

Base `5cff48e` (Phase 29). This phase: `2c14341` web compatibility with
Launcher 0.25.0 · `5c2a273` read-only audit, backup, rehearsal, release and
hosted-check tools · `26912bd` Cup inside one league · this report. The eight
foreign untracked files and the protected guide were not opened, staged or
modified (the security closure document was read, not changed).
