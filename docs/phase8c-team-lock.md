# Phase 8B-H + 8C: Implementation And Staging Report

Date: 2026-09-22. RESULT: DONE local + Supabase V2 staging validated.

## Checkpoint And Scope

- Branch: `main`, upstream `origin/main`.
- Starting HEAD: `de485f773e0969882083437ed5c222c9958fbe92`.
- Starting working tree: only the user's untracked
  `docs/pokeapp-guia-completa-pestanas-y-producto.md`.
- Phase 8B-H: DONE. Phase 8C: DONE local + staging validated; API not deployed.
- Migration 019: applied incrementally to Supabase V2 staging on 2026-09-22.
- Streamlit remains the real legacy runtime. V1 is untouched and has not been
  removed. V2 is not Streamlit's source of truth. No dual-write.
- No React, data migration, parser changes, real Discord or next-phase work.

The original local evidence below is preserved; the staging section adds real
remote results. Historical Phase 7 `RESULT ok checks=13` was not rerun here;
the new Team Lock validator independently reports 13 checks.

## Phase 8B-H

### Auth Bug 1: PostgREST Update

The previous adapter chained `.select()` after `.update()`, which the installed
PostgREST 2.27.2 update builder does not support. The adapter now uses
`update(...).eq("id", canonical_uuid).execute()` with the SDK's representation
return. It requires exactly one row with the expected trainer UUID and Auth UUID.
No rows, ambiguous rows, a mismatched mapping or backend failure are not success.
Provisioning still reports partial failure if Auth creation already succeeded.

Tests H01/H02 and the backend-error case exercise the real SDK builder over
HTTPX MockTransport. No fake builder invents unsupported chaining methods.

### Auth Bug 2: Slug Lookup

Previously a slug could reach a UUID-column query and fail before a slug lookup.
The adapter parses UUIDs locally. Valid UUIDs query `id`; other nonblank inputs
query normalized `slug`. Empty/unknown identities return no trainer. Genuine
backend errors become chained `AuthBackendError`, not swallowed absence.
H03/H04/H05/H09 cover these paths and safe HTTP error handling.

### Auth Bug 3: Disabled Principal

`require_principal` proves identity but is also used by `/v1/me`, which must be
able to describe a disabled account. New `require_enabled_principal` adds the
mutation check: disabled trainers, including admins, receive 403. `/v1/me` keeps
its existing 200 response for a verified disabled principal. H06/H07/H08 cover
enabled mutation, denied disabled mutation and the preserved `/me` behavior.

### Python Environment

The old `.venv` points at a missing Python installation on another Windows user
profile. It was not overwritten. The isolated `.venv-api` uses Python 3.14.3:

```powershell
py -m venv .venv-api
.\.venv-api\Scripts\python.exe -m pip install -r requirements-api.txt
```

Verified direct versions: Supabase 2.27.2, PostgREST 2.27.2, FastAPI 0.141.1,
Starlette 1.6.0, HTTPX 0.28.1, Uvicorn 0.53.0. `requirements-api.txt` pins these
for the API/test environment without changing `requirements.txt` or deploying
dependencies to the legacy runtime. This is not a full transitive lockfile.

## Phase 8C API

```http
PUT /v1/seasons/{season_id}/matchdays/{matchday_id}/team-lock
Authorization: Bearer <verified-user-access-token>
Content-Type: application/json

{"save_file_id": "<own-v2-save-uuid>"}
```

Path/body identifiers are UUIDs. Extra body fields are forbidden, including
`trainer_id`, hash, team snapshots, deadlines and `is_late`. The trainer comes
only from verified Auth `sub` -> `trainers.auth_user_id` mapping. No admin
override exists on this self-service endpoint.

200 returns an owner receipt with: `id`, `season_id`, `matchday_id`, `trainer_id`,
`season_player_id`, `save_file_id`, `save_sha256`, `locked_at`, `deadline_at`,
`is_late`, `public_team_snapshot`, `private_team_snapshot`, `created_at`,
`updated_at`. It does not return operational credentials, raw parsed payloads,
Auth mapping IDs or Storage paths. Both snapshot arrays have exactly six entries.

| Condition | Result |
| --- | --- |
| Missing/invalid bearer | 401 |
| Globally disabled trainer or inactive participant | 403 |
| Missing/wrong-scope season, matchday, membership or save | 404 |
| Ineligible state, unready parser, changed source, malformed team | 409 |
| Invalid UUID or forbidden body fields | 422 |
| Missing backend config, persistence failure, invalid RPC receipt | 503 |

Public errors are stable and do not include SQL, keys or backend exception text.

## Authorization And Source Flow

1. Verify bearer and resolve a globally enabled trainer, not a client claim.
2. Load the requested season and a matchday belonging to that season.
3. Require active season and matchday `scheduled` or `open`, with no `closed_at`.
4. Require that trainer's active `season_players` row in the same season.
5. Load the exact own, same-season, non-deleted, successfully parsed save.
6. Load the parsed row for that save's recorded parser version; require
   `schema_version=1` and parsed status. Hash must be a valid server SHA-256.
7. Check optional payload save/trainer/source-hash identity fields when present.
8. Build six DTO-backed snapshots, then call the atomic repository operation.

At most five bounded source queries are used. There is no all-saves scan,
download of `.sav` bytes or on-demand PKHeX invocation. An explicitly selected
eligible own save need not equal `current_save_id`: this API does not change the
current-save pointer or invent a new current-only eligibility rule.

## Snapshot And Exact-Team Contract

Canonical existing ParsedSave `party` entries are PartySlots numbered 1-6. They
are validated for uniqueness, sorted and hydrated into `PrivatePokemon`, with
typed moves, flags, IVs and EVs. The existing flat-party SQL/legacy fixture format
uses `app.domain.legacy.pokemon_from_legacy`, not a new raw-save parser.
Unsupported schema versions, empty slots, malformed DTOs and non-six teams fail.

Private snapshots serialize the existing PrivatePokemon contract. Public
snapshots use `PrivatePokemon.to_public()` after clearing arbitrary metadata,
whose contents have no public visibility contract. Thus IVs, EVs, nature,
ability, original trainer and unreviewed metadata are not published. Approved
public fields, including items/moves/types/sprite/flags, use the existing DTO.

Nested data is copied before persistence. Updating a later parsed save cannot
mutate a stored snapshot. An explicit new eligible PUT replaces that jornada's
lock; it does not edit earlier closed jornadas or historical snapshots.

The shared creation validator now also requires exactly six. The old 1-6
acceptance was a pure-service inconsistency with the legacy UI. Its two existing
test fixtures now use six Pokemon. Historical DTOs/readers are unchanged; no
stored historical team is rewritten and no protected Streamlit code is edited.

## Replacement, Deadlines And Atomicity

The logical resource is one lock per `(matchday_id, trainer_id)` using existing
`uq_team_locks_matchday_trainer`. INSERT ... ON CONFLICT replaces the source,
hash, snapshots and lock time, preserving lock UUID and original `created_at`.
Repeating PUT does not create another lock/event. Like legacy replacement,
timestamps may change; idempotency is logical resource/deduplication, not a
byte-identical receipt. Concurrent first requests rely on the unique constraint,
not a vulnerable select-then-insert sequence.

V2 has no authoritative matchday lock deadline yet. `deadline_at=NULL` and
`is_late=false` are server-chosen, not client-controlled. Legacy lateness was
derived from `league_active` and a non-date sentinel. Neither is imported into
V2. This is a documented future temporal-contract decision, not a new mechanic.

`019_team_lock_api.sql` creates `public.api_upsert_team_lock`. A single RPC
transaction performs both the Team Lock upsert and ActivityEvent insert. It:

- locks trainer, season, matchday, membership, save and parsed-source rows;
- revalidates permissions/state and compares the source payload/hash read by
  Python, rejecting concurrent reparse/source changes;
- validates snapshot/party structure and exactly six entries;
- persists both snapshots and the authoritative hash;
- inserts public `TEAM_LOCKED`, actor = authenticated trainer, with season,
  matchday and matchday number context, plus lock/save/hash/late payload;
- deduplicates on `TEAM_LOCKED:<season>:<matchday>:<trainer>` using the existing
  partial unique activity index;
- returns the resulting lock, or rolls everything back on any failure.

The first event is immutable when the lock is replaced. Its payload records the
first lock event, not necessarily the latest save. The lock row holds the latest
snapshot. No new replacement event type or full revision-history table is added.
No real Discord message is sent.

## SQL Security And Migration

The function is SECURITY INVOKER with fixed empty search_path and qualified
application tables. PUBLIC/anon/authenticated cannot execute it; service_role
can. It does not elevate an ordinary caller or add browser write permissions.
Existing RLS/view contracts remain authoritative for reads: owner/admin private,
other logged-in trainers public projection, anon denied. Admins still cannot
directly write team_locks as authenticated clients.

The RPC trusts the server's DTO projection; it does not duplicate the entire
Python privacy projector in SQL. Its source comparison prevents stale-source
commits, but possession of service_role is privileged by design. That key stays
exclusively in the backend.

Migrations 001-018, table constraints, policies and views are unchanged. The
official generator appends 019 in order; static tests compare generated text
exactly with the ordered source migrations. Both build paths passed real local
PostgreSQL. For an existing V2 installation, a future authorized rollout applies
019 only, never reset or bootstrap. Do not run it on V1.

## Validation Commands And Results

The runner executes normal unittest discovery and real temporary SQLite storage,
with Streamlit secrets replaced by an empty test mapping and live credential
environment variables removed in the test process. It does not use the previous
audit harness that blocked persistence. Existing fixtures are not skipped.

```powershell
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py --pattern 'test_auth*.py'
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py --pattern 'test_api*.py'
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py --pattern 'test_team_lock*.py'
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py --pattern 'test_repositories.py'
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py --pattern 'test_supabase_v2_schema.py'
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py
.\.venv-api\Scripts\python.exe -m compileall -q -x '[\\/](\.venv[^\\/]*|\.git|node_modules)[\\/]' .
.\.venv-api\Scripts\python.exe tools/generate_supabase_v2_bootstrap.py
git diff --check
```

| Gate | Result |
| --- | --- |
| Auth | 29 passed |
| API | 47 passed, including 37 Team Lock endpoint tests |
| Team Lock repository/domain | 8 passed |
| Existing repositories | 8 passed |
| Supabase schema/static bootstrap | 14 passed |
| Full suite | 203 passed, 0 failed, 0 skipped |
| Compileall, project excluding venv/vendor/Git directories | PASS |
| Generated bootstrap equality | PASS |
| Git diff-check | PASS |
| Real Supabase / remote 019 | PASS, see staging section |
| Real Discord | NOT RUN |

Warnings retained: Streamlit bare-mode/cache/session-state warnings, Starlette's
HTTPX TestClient deprecation, and Git's LF-to-CRLF notices. None is a test failure.
The new API tests use in-process TestClient, not a running development server.

### Real Local PostgreSQL

PostgreSQL 17.11 portable was initialized in a new temporary directory, listening
only on 127.0.0.1:55439. The disposable database was
`pokeapp_v2_validation_phase8c`. No existing database was reset.

```powershell
$psql = "$env:TEMP\pokeapp_pg17_phase8c_20260922\portable\pgsql\bin\psql.exe"
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql $psql --host 127.0.0.1 --port 55439 --database pokeapp_v2_validation_phase8c --allow-destructive-reset
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql $psql --host 127.0.0.1 --port 55439 --database pokeapp_v2_validation_phase8c --allow-destructive-reset --build-source bootstrap
```

Both exited 0 with `Supabase V2 schema validation completed against real
Postgres.` Each ran build/reset/rebuild, seeds, 019 reapplication, schema/RLS
fixtures and the new SQL contract tests. Those tests verify actual service_role
execution, forbidden anon/authenticated RPC, owner/other/admin reads, denied
direct writes, replacement/identity, snapshot independence, stale payload
rejection, eligibility checks and first-event dedupe.

A forced failing ActivityEvent trigger proves rollback for both initial insert
and replacement. Four concurrent independent SQL sessions prove exactly one
lock and one deduplicated event. These are real SQL checks, separate from the
in-memory test double. The validator now refuses non-loopback hosts and database
names outside `pokeapp_v2_validation*`.

The temporary server is stopped after validation. To reproduce, start your own
isolated PostgreSQL instance and substitute its binary/port/database; never point
the destructive validator at staging or V1. Plain PostgreSQL does not provide
Supabase Storage/Auth services; remote validation remains a separate gate.

## Files And Protected Areas

Created:

- `requirements-api.txt`
- `app/api/routes/team_locks.py`
- `app/repositories/supabase/__init__.py`, `team_locks.py`
- `supabase/v2/migrations/019_team_lock_api.sql`
- `tests/test_auth_hardening.py`, `test_api_team_lock.py`,
  `test_team_lock_repository.py`, `team_lock_fixtures.py`
- `tests/sql/team_lock_setup.sql`, `team_lock_checks.sql`, `team_lock_cleanup.sql`
- `tools/run_unit_tests.py`
- this report

Modified:

- `.gitignore`; `app/api/supabase_repository.py`, `security.py`, `dependencies.py`,
  `main.py`, `schemas.py`
- `app/application/team_locks.py`; `app/domain/team_locks.py`,
  `app/domain/services/team_locks.py`
- `app/repositories/errors.py`, `protocols.py`
- `tests/test_domain_services.py`, `test_repositories.py`,
  `test_supabase_v2_schema.py`
- `tools/generate_supabase_v2_bootstrap.py`, `validate_supabase_v2_schema.py`
- `supabase/v2/bootstrap.sql`, `supabase/v2/README.md`
- `docs/project-checkpoint.md`, `architecture.md`, `security-rls.md`,
  `supabase-v2.md`, `migration-plan.md`

Protected: trainer UI, Liga, shop, Copa, Juicios, Discord implementation,
`storage.py`, `app/storage_shop.py`, parser/PKHeX/bridge/desktop and migrations
001-018 remain unchanged. The user's untracked guide is neither edited nor
staged. Its baseline SHA-256 is
`6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.

## Limitations And Next

- No blocker for DONE local or the completed remote gate for 019.
- Snapshots support current schema v1 only. Raw parsing and parser upgrades are
  outside this endpoint and remain the Phase 9 boundary work.
- Actual deadlines/late adjudication need an authoritative V2 temporal contract
  before cutover; no legacy sentinel was silently mapped to a timestamp.
- Existing Auth in-memory rate limiting and credential lifecycle/deployment
  hardening remain separate operational concerns, not redesigned in this slice.
- Remote gate completed under the authorized 8C-staging + 8D macro.
- Next: continue the existing Phase 8 roadmap with purchase + ledger + activity
  atomic API work. League/season/admin/trials/Hall APIs remain pending. Only then
  advance through parser boundary, React/Cloudflare, migration, shadow and cutover.
- No next-phase implementation is included in this checkpoint.

## Commits

- `3dc016c api: harden phase 8 authentication`
- `891ed8a api: add atomic v2 team lock mutation`
- Companion documentation checkpoint: `docs: close phase 8c` (contains this
  report; obtain its hash with `git log -1 --oneline` at this checkpoint).

The original three commits were pushed to origin/main before remote validation.
The original user guide remains deliberately untracked and unmodified.

## Supabase V2 Staging Validation

Date: 2026-09-22. Authorized target: `Pokeapp 2.0`, project ref
`uwleqeuzsveqlugugzba`. MCP `get_project_url`, local V2 env URL and service-role
REST preflight agreed. The existing RPC was absent; only 019 was applied through
MCP `apply_migration`, not bootstrap/reset. Function body MD5
`5cd4280a83ba20f53f9e45e89ef702cd` matches the local migration. Catalog checks
confirmed SECURITY INVOKER, empty search_path, no PUBLIC/anon/authenticated
EXECUTE and service_role EXECUTE. Migrations 001-019 were not edited.

```powershell
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_team_lock.py --env-file .env.supabase-v2-rls.local --allow-staging-writes
```

This opt-in tool refuses every host except the approved V2 staging URL. It uses
the real FastAPI application in-process, real Auth JWT verification and real
Supabase adapters/PostgREST. No mocked API repositories or deployed web server.
Three temporary Auth users (owner/other/admin) and uniquely marked DB fixtures
are created. No save bytes are uploaded/modified and no Discord message is sent.

| Remote check | Result |
| --- | --- |
| TL01 first authenticated API lock / service RPC | PASS |
| TL02 exactly six; five rejected | PASS |
| TL03 replacement, same lock ID, one logical row | PASS |
| TL04 TEAM_LOCKED referencing the new lock | PASS |
| TL05 retry/replacement preserve one immutable first event | PASS |
| TL06 other user/forged trainer ID rejected by API | PASS |
| TL07 foreign save rejected | PASS |
| TL08 wrong season/matchday rejected | PASS |
| TL09 anon/authenticated direct RPC denied | PASS |
| TL10 owner/admin direct INSERT/UPDATE cannot change rows | PASS |
| TL11 owner/admin private and current reads | PASS |
| TL12 other/public projection, no private fields; anon denied | PASS |
| TL13 stale parsed payload/hash rejected, lock/event unchanged | PASS |
| TL14 forced failure after write | LOCAL PASS; NOT RUN remotely |

The first run stopped because the new validator incorrectly required HTTP 403
for UPDATE. Existing RLS filters that UPDATE to zero rows (HTTP 200, `[]`). The
validator was corrected, not RLS; it now also verifies the whole stored lock is
unchanged after each denied operation. Both runs cleaned up successfully.
Forced post-write rollback needs intrusive failure injection; existing real
local PostgreSQL insert/replacement rollback tests cover it instead.

Final run: `phase8c_validation_3e973bd632e04bd4bcd33abc5004af1e`:
`RESULT ok checks=13; TL14=local-only`, `CLEANUP PASS`. Cleanup deletes only
recorded fixture UUIDs / the unique fixture season's generated locks/events and
verifies absence, including Auth users. Independent SQL confirmed zero remaining
`phase8c_validation_*` trainers, seasons, save records and Auth users.

Full unit suite: 208 passed, 0 failed/skipped (203 previous + 5 validator safety
tests). Compileall and diff-check passed. Existing Streamlit bare-mode warnings
and Starlette TestClient deprecation remain warnings, not suppressed failures.
V1, runtime Streamlit, parser, mechanics and Discord remain untouched.

The subsequent authorized shop audit reached a product-contract stop before
any 8D implementation. See [Phase 8D audit](phase8d-purchases.md): current-jornada
and store-ban eligibility must be defined for V2 before creating purchase RPC
020. This does not reopen or invalidate the completed Phase 8C gate.
