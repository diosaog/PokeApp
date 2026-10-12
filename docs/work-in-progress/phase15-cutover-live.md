# Phase 15A — cutover preflight

Observation: 2026-10-12 Europe/Madrid. **PHASE 15A DONE.**
**CUTOVER EXECUTION: READY.** This is a preflight record only; no cutover,
deployment, migration, data mutation or deletion was performed.

## STATUS

- Entry HEAD `0cca6e162e63a51483df0cf7da2ba4df05e1fe74`; `main` and
  `origin/main` are 0/0 and the tracked tree is clean.
- The protected guide and unrelated pre-existing untracked files remain
  untouched. This document is the only Phase 15A file added.
- Phase 14 is closed and its measured API deployment is the current compatible
  application checkpoint.

## CURRENT AUTHORITY MAP

- **Browser:** Cloudflare `pokeapp-web` serves the React application at
  `https://pokeapp-web.pokeapp-v2.workers.dev`. It has no direct V1 or Supabase
  access. Its read-only `build-config.json` points to the Railway API below.
- **API:** Railway project **PokeApp V2**, production service `pokeapp-api`,
  `https://pokeapp-api-production.up.railway.app`, deployment
  `9b75a24f-ca5e-474b-9c3c-555625cceb14`, Online, source
  `d05e28e01639d146976300dbcd7bb16baa92c9d1`, image
  `sha256:cdc7a9bcc7edd5fc2c5cf9b76fbe86b3be58b204303f5c029bd62a09246e1120`.
  FastAPI configuration and repositories point to V2 only; health returned 200.
- **Competitive database:** V2 Supabase `uwleqeuzsveqlugugzba`,
  `Pokeapp 2.0`, `eu-central-1`, `ACTIVE_HEALTHY`.
- **Legacy/reference runtime:** root `main.py` is Streamlit and `storage.py`
  retains the legacy V1-compatible storage/config path. It is not the current
  Cloudflare/Railway authority and has no production dual-read path into
  `v1_shadow`. V1 remains an intact source/reference during and after 15B.
- **Launcher/parser:** local save observations remain read-only evidence and
  are not competitive authority or a cutover dependency.

## TARGET AUTHORITY MAP

After 15B, the user-facing authority remains React/Cloudflare → FastAPI/Railway
→ V2 Supabase. V1 and private `v1_shadow` remain read-only reference/rollback
surfaces. No browser write bypasses the API, and no V1 fact is merged into the
owner's active competitive season.

The current public React/API path already has this target wiring. Any separate
legacy Streamlit ingress must be identified and placed read-only before traffic
is switched; the repository does not contain a second DNS or hosting control
that can safely be inferred.

## VERIFIED MIGRATION/DATA STATE

- V1 `fdtytpeyfzyssfrsulxd` (`diosaog's Project`, `eu-north-1`) is
  `ACTIVE_HEALTHY`. Read-only inventory matches the sparse surviving source:
  `settings` 9, `saves` 1, `purchases` 2, `redemptions` 0,
  `pokemon_flags` 0, `shop_discounts` 0, `team_locks` 0; Auth users 0,
  one Storage bucket and one object. No V1 writes occurred.
- V2 has **34 migration records**, `001`–`042`, with
  `042_v1_shadow_relational_destination` applied once as `20261011160629`.
  There is no pending Phase 15 migration and no migration replay is authorized.
- Phase 11 run `61e5eb57-34f5-57f9-9252-4ea8be8d8b66` is `reconciled`: six
  batch receipts, 57 deterministic mappings and 135 rows across 15 private
  `v1_shadow` tables, with no public foreign keys. V1 remains source/reference.
- The fresh read-only observation confirms the run, batches, mappings, private
  row count, migration history and security catalogs unchanged. Owner-stable
  business data and Storage match the prior closure. The only full-baseline
  difference is expected owner Auth/session activity; it is excluded from the
  stable business comparison.
- Phase 12 remains read-only: 92 MATCH, 6 EXPECTED_DIFFERENCE, 22 UNKNOWN,
  8 NOT_APPLICABLE and 0 BLOCKER. No fixture, reward, competitive or Storage
  write is pending.

## VERIFIED DEPLOYMENTS

- Railway is Online with only `PokeApp V2 / pokeapp-api` listed. Health:
  `GET /health` → 200, `{"service":"pokeapp-api","status":"ok"}`.
- Cloudflare latest deployment is version
  `77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11`, 100%, created 2026-10-08, source
  `eb4e402891cbaa02e0999229874ac3003e016ae0`. Read-only
  `GET /build-config.json` → 200 with API base
  `https://pokeapp-api-production.up.railway.app` and production mode.
- Both Supabase projects are `ACTIVE_HEALTHY`; no deployment or database write
  was made for this preflight.

## 15B EXACT CUTOVER CHECKLIST

1. **Freeze and re-observe.** Capture V1/V2 refs, migration history, owner-stable
   hashes, `v1_shadow` run state, Storage metadata and deployment IDs. Abort on
   any drift; do not retry a remote operation without reconciliation.
2. **Gate legacy writes.** At the actual legacy Streamlit ingress, enter the
   approved maintenance/read-only window. Verify the public legacy surface is
   read-only and no active write is in flight. If its ingress or operator access
   cannot be identified, stop before traffic changes.
3. **Verify API authority.** Keep or deploy only a committed, tested Railway
   source whose environment points to V2 Supabase. Verify health, JWT/PIN login,
   representative reads, privacy denials and absence of V1 endpoints. Abort on
   wrong project, auth failure or any 5xx; restore the last known good Railway
   deployment.
4. **Verify web authority.** Keep or publish a tested Cloudflare build whose
   `VITE_API_BASE_URL` is the Railway URL. Verify HTTPS, SPA fallback, CSP,
   CORS, MIME/nosniff, login and read-only screens. Abort on asset/API mismatch;
   restore version `77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11`.
5. **Switch the public entry.** Point the declared user-facing entry to the
   verified Cloudflare React surface, preserving the legacy host read-only for
   rollback. Record the exact DNS/hosting control and propagation result; never
   infer an unrecorded legacy route.
6. **Post-switch proof.** Run fresh browser/API reads for login, General,
   profile/privacy, Shop/inventory, Team Preview/scouting, Admin read-only,
   Hall/history and error/permission paths. Confirm V2 migration history,
   `v1_shadow` receipts/rows, owner-stable hashes and Storage are unchanged.
7. **Rollback window.** Hold the agreed observation window. Any auth/privacy
   failure, unexpected write, data drift, migration mismatch or sustained 5xx
   aborts the window and invokes the rollback below. Do not delete V1 or
   `v1_shadow` after a successful switch.

## ROLLBACK PLAN

- Restore public routing to the prior entry, then restore Cloudflare version
  `77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11` and, if required, Railway deployment
  `3845ce2d-6488-43ef-893a-1459c2aed0bb` (previous compatible checkpoint).
- Roll back traffic and application artifacts only. Never roll back or rewrite
  V2 migrations, owner rows, frozen history, Storage, V1, or private
  `v1_shadow` data as part of a traffic rollback.
- For an unknown command/deployment outcome, reconcile live status and hashes
  before retrying. A partial or ambiguous migration outcome is a stop condition,
  not permission to replay.
- Success requires healthy API/web probes, authenticated read proof, unchanged
  owner-stable and Shadow evidence, no unexpected writes and no unresolved
  security/privacy regression.

## 15C PROOF MATRIX

| Surface | Required proof after cutover | Mode |
|---|---|---|
| Login/session | PIN login, refresh, logout, invalid/expired denial | Read/auth only |
| General/seasons | current season, matchdays, rankings and history load | Read only |
| Profile/privacy | self details; rival private fields denied | Read/denial |
| Shop/inventory | balances, catalogue, inventory and ownership boundaries | Read only |
| Team Preview/scouting | approved public projection; private fields absent | Read/denial |
| Admin | human labels, guards and read-only controls | Read only |
| Hall/history | frozen League/Cup history and team snapshots | Read only |
| Security | browser direct-table/RPC denial, JWT/role checks, CORS/CSP | Read/denial |
| Data preservation | owner-stable V2, V1 source, Storage and Shadow hashes | Read only |
| Migration state | 34 records through 042; reconciled run, six batches, 57 maps, 135 rows | Read only |

Any deliberate production mutation requires a separately authorized, reversible
test and its own before/after reconciliation; 15A executes none.

## BLOCKERS

**None identified for Phase 15A.** The only execution gate carried into 15B is
to identify and verify the actual legacy Streamlit ingress/operator control if a
traffic switch is required. The repository does not justify inventing a DNS
route. If that control is unavailable at the 15B start gate, cutover is blocked
before any write or traffic change.

## DO NOT REPEAT

Do not rerun Phases 11–14, replay migration 042, rebuild the shadow mapping,
mutate the owner season, create fixtures, delete V1/`v1_shadow`, run broad suites,
deploy from an uncommitted source, or read/touch the protected guide. Do not
start Phase 15C from this preflight.

## NEXT EXACT ACTION

Stop after this preflight. A separately authorized Phase 15B execution may begin
by rerunning step 1, confirming the legacy ingress gate, and then following the
numbered checklist in order. Phase 15C starts only after 15B traffic and rollback
evidence is complete.

---

# Phase 15B — production cutover execution attempt

Observation: 2026-10-12 Europe/Madrid. **STATUS: PHASE 15B BLOCKED.**
**CUTOVER: NOT EXECUTED.** The block was reached before any traffic, deployment,
database or business-data change.

## Fresh entry reconciliation

- Entry HEAD remained `c6bf6bef8655bc40c7657ae486c5b8bd13b3c903`, with
  `main`/`origin/main` at 0/0 and only the pre-existing unrelated untracked
  files plus the protected guide listed by Git.
- Railway remained Online at deployment
  `9b75a24f-ca5e-474b-9c3c-555625cceb14`; `GET /health` returned 200.
- Cloudflare remained at version
  `77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11`; `GET /build-config.json` returned 200
  with the Railway API origin.
- Read-only V1/V2 project checks returned `ACTIVE_HEALTHY`. V1 still has the
  sparse seven-table inventory (settings 9, saves 1, purchases 2, all other
  public legacy tables empty, one bucket and one object). V2 still has 34
  migration records through 042 once.
- The fresh V2 observation at `2026-10-12T16:11:40Z` confirmed the reconciled
  Phase 11 run `61e5eb57-34f5-57f9-9252-4ea8be8d8b66`, six batches, 57 maps,
  135 private Shadow rows, unchanged owner-stable data and security catalogs,
  and zero remote writes. The full baseline difference remains only expected
  owner Auth/session activity.

## CUTOVER BRANCH: C

`https://pokeapp.streamlit.app/` is an actually reachable Streamlit ingress:
the root returned the Streamlit Cloud shell with HTTP 200, and `/healthz`
returned `{"status":"ok"}`. Repository evidence (`main.py`, `desktop/main.js`)
confirms the URL is the legacy entry, but does not provide hosting ownership or
a safe traffic/write gate. Current Railway/Cloudflare inventory contains no
Streamlit deployment or DNS control, and no Streamlit operator credentials are
available in the execution environment. The `.streamlit` directory is local
runtime configuration, not proof of hosted control.

Because an active legacy ingress exists while its write gate and routing control
cannot be positively identified, Phase 15B stops under the required Branch C
rule. No maintenance mode, DNS change, deployment, migration, V1/V2 write,
Shadow write or owner-data mutation was attempted.

## PUBLIC ENTRY BEFORE / AFTER

- **Before:** legacy `https://pokeapp.streamlit.app/` remains reachable; the
  already published V2 surface is
  `https://pokeapp-web.pokeapp-v2.workers.dev/` → Railway → V2.
- **After:** unchanged. No traffic switch was performed.

## CHANGES ACTUALLY MADE

Only this documentation update. No application, SQL, environment, hosting,
Cloudflare, Railway, Supabase, V1 or Storage change.

## AUTHORITY PROOF

The verified V2 path is Cloudflare React → Railway FastAPI → Supabase V2. V1 and
`v1_shadow` remain preserved reference data. Because the legacy Streamlit host is
still publicly reachable, exclusive production authority cannot be declared
until its operator can place it read-only and control the public entry.

## IMMEDIATE PROOF RESULTS

The safe pre-cutover probes passed: V2 API health, Cloudflare reachability and
API-origin configuration, V1/V2 health, migration head, Shadow reconciliation,
owner-stable preservation and security comparison. The authenticated 15C-style
read matrix was not started because Branch C requires stopping before traffic
changes and before treating the public authority as cut over.

## PRESERVATION RESULTS

V1 source, V2 owner-stable business data, results, economy, Team Locks, Storage,
34 migration records, Shadow run/batches/maps/rows and security catalogs remain
unchanged. Remote business writes and fixtures: zero.

## ROLLBACK STATE

No rollback was needed because no change occurred. Existing rollback artifacts
remain available: Cloudflare version `77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11` and
Railway deployment `3845ce2d-6488-43ef-893a-1459c2aed0bb` as the prior compatible
checkpoint. V1 and `v1_shadow` were not altered.

## OBSERVATION RESULT

The bounded read-only observation was clean: API/web health stayed 200, no
unexpected 5xx or write was observed, and the intermittent historical READ 503
did not reproduce. This does not override the unresolved legacy ingress control.

## BLOCKERS

Single concrete blocker: provide verified operator/hosting or DNS control for
`https://pokeapp.streamlit.app/` sufficient to gate legacy writes and switch the
declared public entry safely. Do not infer this control from `main.py`, the
Electron launcher or local `.streamlit` files.

## 15C READINESS

**NOT READY.** Do not start Phase 15C until the legacy ingress is controlled,
placed read-only and the public entry switch is executed and recorded.

## DO NOT REPEAT

Do not rerun Phases 11–14, replay migration 042, rebuild Shadow, mutate the
owner season, create fixtures, delete V1/`v1_shadow`, deploy uncommitted source,
or read/touch/stage the protected guide. Do not retry traffic changes without
the missing legacy control.

## NEXT EXACT ACTION

Obtain and verify the Streamlit hosting/DNS operator control and the safe legacy
write gate. Then resume Phase 15B from the fresh baseline; if that control cannot
be obtained, keep production authority unchanged and do not start Phase 15C.
