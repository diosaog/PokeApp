# Phase 8G.1: Core Season Administration

DONE local + real V2 staging, 2026-09-23; implementation based on `089b8d6`.
Local/staging closure evidence is recorded below and in the
[complete delivery report](phase8g1-completion-report.md), not inferred from code.
The existing Streamlit runtime and V1 remain unchanged. No dual write or deployment.

## Approved Product Contract

- D1=A: prepare in DRAFT; activate only a complete playable first round. Admin
  need not participate. Another ACTIVE season is a conflict, never auto-finished.
- D2=A: initial roster only. No late join, retirement, abandonment,
  disqualification, reactivation or competitive participant removal.
- D3=B: correct unused configurations at their original effective round, with
  reason, CAS and private before/after audit. Used configurations are immutable.
- Future D4=A, D5=A, D6=A, D7=A are approved direction, not implemented here.
  D8 remains deferred. No closing/rewards/movements/finish/archive/discard/Hall.

## Authorization and API

`require_admin_principal` verifies the Supabase bearer, resolves
`auth.uid() -> trainers.auth_user_id`, then checks `globally_enabled` and
`is_admin`. No name, slug, body actor or participation grants authority.
Every backend RPC repeats the enabled-admin check under a trainer SHARE lock.

All paths below are prefixed `/v1/admin`. Request bodies forbid extra fields.
UUIDs, integer revisions, positive capacities and strict booleans are typed.

| Method/path | Contract |
| --- | --- |
| GET `/seasons/{s}/setup` | Safe setup source and machine-readable readiness |
| POST `/seasons` | `{name}`, idempotency key; season DRAFT only |
| PUT `/seasons/{s}/name` | `{name, expected_revision}`, DRAFT, CAS |
| POST `/seasons/{s}/participants` | Trainer UUID, optional seed, roster CAS |
| POST `/seasons/{s}/participants/{p}/remove-from-draft` | Reason, roster CAS; fail-closed references |
| POST `/seasons/{s}/config-versions` | Typed configuration, roster/config CAS |
| POST `/seasons/{s}/config-versions/{v}/replace-unused` | Full config, reason, same effective round, CAS |
| PUT `/seasons/{s}/initial-divisions` | Exact A/B player UUID arrays, setup/roster CAS |
| POST `/seasons/{s}/matchdays/prepare-current` | Setup CAS; first scheduled round only |
| POST `/seasons/{s}/activate` | Setup CAS; complete readiness and one-ACTIVE gate |

Every POST and multi-write PUT requires `Idempotency-Key` (1-128 visible ASCII
characters). Rename uses its revision as an internal deterministic retry key.
There is no generic status PATCH or direct browser pointer assignment.

Errors: 401 bearer; 403 disabled/non-admin; 404 scoped missing resource;
409 business/CAS/idempotency; 422 malformed body; 503 sanitized persistence.
Backend codes must match the explicit code/SQLSTATE allowlist. SQL diagnostics
and unknown/private response fields never reach the client.

## Revision and Replay Semantics

`season_admin_state` contains three monotonic bigint counters, initially zero:

| Successful operation | Setup | Roster | Config |
| --- | --- | --- | --- |
| Rename | +1 | unchanged | unchanged |
| Add/remove initial participant | +1 | +1 | unchanged |
| Create/replace configuration | +1 | unchanged | +1 |
| Initial divisions, prepare first day, activate | +1 | unchanged | unchanged |
| Replay or rejected transaction | unchanged | unchanged | unchanged |

`admin_operation_receipts` is unique by actor, operation scope (operation +
season + optional resource), key. The canonical JSONB request has a server SHA256
hash. Arrays are sorted by the public API where assignment order is not semantic.
Same actor/scope/key/body returns the original response with `replayed=true`;
different body returns IDEMPOTENCY_CONFLICT. Rename with an already consumed
revision and a different name returns STALE_REVISION. Receipts are update-immutable.
Independent administrators have independent key namespaces: two requests from
one administrator are a retry; an equal key from another administrator is not.

Each mutation writes an ADMIN-only `SEASON_ADMIN_*` ActivityEvent and receipt
in the same transaction. Replacement records before/after and reason privately.
No Discord or webhook is invoked. Failure of event/receipt rolls everything back.

## Roster and Configurations

Enrollment creates one active season_player and one zero-badge stats row. It
inherits no save, money, flags, Auth identity, Cup or trial state.
Roster changes stop once initial memberships or a matchday exist. Removal also
rejects any configuration/division, nonempty stats/metadata/current save, or
reference discovered through actual FKs to season_players.id. Only untouched
initial stats are deleted; the global trainer is never deleted.

Configuration JSON has explicit shapes: positive A/B sizes summing to the exact
registered active roster; movement in `[0,min(A,B)]`; positive total rounds;
effective round in `[1,total]`; exactly ranks 1..N with nonnegative integer
scoring/coin rewards; only `team_lock_required` and `last_b_gets_steal` booleans.
Roster revision is stored with each configuration; a later roster edit makes it
stale until corrected. Names are not roster authority.

Config creation/correction is limited to DRAFT/ACTIVE, with an effective round
strictly greater than every already prepared round. An unused future correction
keeps its UUID, version number and effective round. Full before/after evidence is
in the private event. Initial division capacities cannot change after assignment.
The existing unique constraints prevent two versions for one effective round.

Actual FK audit found exactly `matchdays.season_config_version_id` and
`matchday_snapshots.config_version_id`; either reference means USED, including a
scheduled matchday. The replacement RPC checks under the season lock. A database
trigger additionally rejects changing any referenced config, including direct
service updates. No historical snapshot is rewritten. Pre-026 fixture rows keep
NULL new fields and are not silently certified as valid admin configurations.

## Divisions, First Day and Activation

Initial assignment uses canonical A (tier 1), B (tier 2). Every participant appears
once, in its exact capacity. Membership begins at round 1, reason `initial`, no
end/source round. Assignment is one-time: subsequent calls replay their key or
return INITIAL_SETUP_LOCKED, rather than deleting history to reassign.

Preparation creates only matchday 1 (`scheduled`, not opened), references its
exact initial config, creates all unordered within-division pairs and sets the
authoritative pointer. UUID order canonicalizes pairs and a unique expression
index prevents inverse duplicates, even if a backend reverses player order.
For A/B of size 2/2 there are 2 matches; for 5/5 there are 20. No future shells.

GET setup uses a season SHARE lock for a coherent read. It exposes participants
and stats readiness, configs/current-version marker, A/B/membership history,
first day/count, pointer, revisions and these readiness checks:
`has_roster`, `has_valid_config`, `has_initial_divisions`, `memberships_complete`,
`first_matchday_prepared`, `match_pairs_complete`, `pointer_valid`,
`no_other_active_season`, `is_draft`. False checks become sorted blocking reasons.
`can_activate` is true only when all pass; React must not recreate this logic.

Activation rechecks under lock, changes DRAFT to ACTIVE and records server time.
The existing global partial unique index resolves cross-season races; its
collision becomes ACTIVE_SEASON_EXISTS. It does not open a day, finish another
season, grant currency, create saves or enroll competitions.

## SQL and Security

Additive migration `026_season_admin_setup_api.sql`; 001-025 unchanged.
Bootstrap is generated from all 26 migrations, never applied to existing staging.
The two new tables have RLS and service-only privileges, intentionally no browser
policies. All new helpers/RPCs are SECURITY INVOKER, fixed search_path, execute
revoked from PUBLIC/anon/authenticated and granted only to service_role.

Authenticated direct INSERT/UPDATE/DELETE is revoked on seasons, season_players,
season_player_stats, season_config_versions, divisions, division_memberships,
matchdays and matches. Column grants from 020 are explicitly revoked too.
Existing SELECT policies/views remain unchanged. Prior service-only 019-025
operations do not depend on those browser writes.

Locks: actor SHARE -> scoped receipt advisory lock -> season FOR NO KEY UPDATE
-> existing participant rows ordered by UUID FOR UPDATE -> specific rows.
Insertion also takes the season lock. No Python mutation mutex or automatic retry.
The season lock mode stays compatible with FK KEY SHARE and migration 025.

## Validation Commands

Run using the existing `.venv-api` interpreter with API/test dependencies.
The PostgreSQL validator requires an isolated loopback database named
`pokeapp_v2_validation_*`; its reset is destructive ONLY there.

```powershell
.\.venv-api\Scripts\python.exe -m unittest discover -s tests
.\.venv-api\Scripts\python.exe -m compileall -q app tools tests
.\.venv-api\Scripts\python.exe tools/generate_supabase_v2_bootstrap.py
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql <local-psql.exe> --host 127.0.0.1 --port 55439 --database pokeapp_v2_validation_phase8g1 --allow-destructive-reset
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql <local-psql.exe> --host 127.0.0.1 --port 55439 --database pokeapp_v2_validation_phase8g1 --allow-destructive-reset --build-source bootstrap
git diff --check
```

Shared real database fixtures cover business flows, direct browser denials and
races A-K. Local-only triggers inject failure after draft state, player, config,
second membership, matchday, match, pointer, activation and receipt writes;
every case compares complete public-table data snapshots before/after.

Staging is opt-in and pinned to `https://uwleqeuzsveqlugugzba.supabase.co`:

```powershell
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_season_admin.py --env-file .env.supabase-v2-rls.local --allow-staging-writes
```

It creates `phase8g1_validation_<uuid>` fixtures and temporary Auth users, runs
real JWT -> FastAPI TestClient -> production adapters -> PostgREST, and cleans up
in finally blocks. Per-worker HTTP sessions avoid shared transport state. This
does not claim a general Windows/httpx fix. No public API deployment is needed.
No raw save bytes or Storage objects are created by these setup fixtures.

## Completion Evidence

Local gates PASS, 2026-09-23:

- 343 unit tests (318 baseline preserved + 25 API/adapter/validator contract tests).
- `py -m compileall -q .` and `git diff --check` PASS. Existing Streamlit cache,
  Starlette TestClient deprecation and Git LF/CRLF warnings are not concealed.
- PostgreSQL 17.11, loopback 127.0.0.1:55439, disposable database
  `pokeapp_v2_validation_phase8g1`: migrations and bootstrap both reset/rebuild
  cleanly, each running existing 019-025 regressions and RLS/schema checks.
- Both routes pass 17 admin fixture groups, A-K races, and nine exact-state
  rollback points. Included actual FK introspection and 2/3-division all-vs-all.
- Full `pg_dump --schema-only` comparison (including grants/ownership) PASS:
  7,381 lines identical; only random dump restrict tokens are normalized.

Incremental staging validation PASS. Phase 8G.1 is DONE.
Weighted completed-project estimate moves about 57% -> 59%; 8H is next,
not implemented. This is not a whole-API or production-release completion claim.

026 was applied after push `178cc41`, as `20260923192300`, only on the pinned V2
project. Initial remote run stopped at a validator TypeError: FastAPI schema
errors use a 422 detail list, not the business error object. The harness now
asserts that distinction explicitly, with a regression test; no migration/API
behavior was changed. That attempt cleaned all fixtures/Auth users, independently
confirmed by SQL (zero seasons/receipts/temp users, ten original trainers).

Harness correction pushed as `c6afcde`. The completed run was
`phase8g1_validation_ec1accfdab004e189f9b424346812523`:

- `RESULT ok groups=17; real JWT/API/PostgREST; Auth cleanup PASS`.
- Core RG01-RG18/RG22 and A-K cases covered by 17 shared fixture groups.
- RG19: Team Lock regression, 13 checks PASS.
- RG20: current-day/Store Ban and normal purchase regression, 29 checks PASS.
- RG21: authoritative identity/redemption/robbery/voucher regression, 17 groups PASS.
- No remote failure-injection DDL and no automatic mutation retry. Per-worker
  sessions are isolated; no claim of a general Windows/httpx transport fix.
- Independent MCP SQL confirms zero fixture users, identities, sessions, seasons,
  players, stats, configs, divisions, memberships, days, matches, events, admin
  state and receipts; regression economy/identity/save/effect tables also empty.
- Existing ten trainers, 62 catalog items, three Storage objects and bucket
  definitions retain exactly their pre-run row-content fingerprints.
- 39/39 public tables with RLS, 37 views, all 23 admin functions invoker with fixed
  search_path and service-only EXECUTE; eight tables have no authenticated table
  or column writes. Advisor findings and remediation links are in the delivery
  report; the project is not advertised as Advisor-clean.
