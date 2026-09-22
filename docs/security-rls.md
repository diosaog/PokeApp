# Supabase V2 Security And RLS

Checkpoint: Phase 8B-H DONE; Phase 8C DONE + staging validated (2026-09-22).

This document is the security contract for the greenfield Supabase V2 schema. It
does not connect Streamlit or React to V2. The isolated API now implements Auth
and Team Lock/normal purchase mutations. 019-020 are applied in V2 staging;
021 normal purchase is locally validated, remote gate pending.

## Security Model

- Every PokeApp V2 application table in `public` has RLS enabled.
- Base tables are not the normal client read surface. Client reads should use the
  `public_*` and `current_*` views created in `012_security_views.sql`.
- `anon` has no app read grants. Users must be authenticated before reading app
  projections.
- `authenticated` can receive broad SQL privileges on base tables, but RLS is the
  authority that decides which rows are visible or mutable.
- `service_role` keeps privileged server access and must stay server-only. It
  must never be exposed in a browser, React app or public Worker environment.
- Admin is explicit: `trainers.is_admin = true`. It is not inferred from
  `display_name`, `slug` or the name Anto.
- Trainer identity is explicit: `trainers.auth_user_id` maps Supabase Auth users
  to PokeApp trainers.

## PIN Auth Bridge

PokeApp keeps the existing login UX: trainer + PIN. The PIN is not the Supabase
Auth password and is never stored by the new auth bridge.

The server-side bridge derives the hidden Supabase credential with HMAC-SHA256:

- pepper: `POKEAPP_AUTH_PIN_PEPPER`, server-only, never committed and never
  logged;
- context/domain separator: `pokeapp-v2-auth`;
- identity anchor: stable trainer UUID, not display name, slug, email or PIN;
- PIN input: string, preserving leading zeros.

The synthetic Supabase Auth email is deterministic and non-deliverable:

```text
trainer-<trainer_uuid>@auth.pokeapp.invalid
```

Login requires an already provisioned trainer row. If `trainers.auth_user_id` is
missing, login fails with an internal `AUTH_NOT_PROVISIONED` category; the future
HTTP layer must still map normal public failures to generic
`INVALID_CREDENTIALS` semantics to avoid account enumeration.

Provisioning is explicit and admin-only:

- create the Supabase Auth user server-side with the derived hidden credential;
- persist the created Auth UUID to `trainers.auth_user_id`;
- verify the mapping;
- if Auth creation succeeds but DB mapping fails, surface a recoverable partial
  provisioning error for operator repair.

The bridge distinguishes the normal Auth client from the privileged admin Auth
client. `service_role` remains server-only and must not be exposed to frontend
code. Phase 8B adds HTTP PIN-login rate limiting at the API boundary; the rate
limit accounts for source IP, trainer/account identifier and time window instead
of relying only on Supabase token endpoint limits.

## Phase 8B HTTP Auth API

FastAPI is the Python transport for the first API slice. It is isolated from the
legacy Streamlit runtime. Team Lock is implemented separately in Phase 8C below.

Public surface:

- `GET /health`: unauthenticated minimal status only.
- `POST /v1/auth/pin-login`: PIN in JSON body only; never query/path/header.
- `POST /v1/auth/refresh`: refresh token in JSON body.
- `GET /v1/me`: bearer access token required.

Security behavior:

- PIN login runs through a rate limiter before calling `PinAuthBridge`.
- Normal login failures map to stable `401 INVALID_CREDENTIALS`, without
  revealing trainer existence, disabled state, bad PIN or missing provisioning.
- Refresh and bearer failures map to stable `401 INVALID_SESSION`, without
  exposing Supabase exception text.
- `/v1/me` never trusts an unverified JWT payload. It calls Supabase Auth
  `get_user(access_token)` through a port/adapter and uses the verified user id.
- `/v1/me` returns trainer id, display name, `is_admin` and `globally_enabled`
  only. The client must not become the authority for admin decisions.
- The API may use `service_role` only server-side for lookup/mapping and the
  explicitly authorized Team Lock repository/RPC, never as a browser credential.

## Phase 8B-H And 8C Boundaries

- UUID vs slug is decided locally, not by an invalid UUID database query.
- Auth mapping updates verify exactly one matching trainer/Auth UUID receipt.
- `require_enabled_principal` rejects disabled principals for mutations, including
  admins. `/v1/me` still describes a verified disabled principal.
- Team Lock PUT is self-service: identity comes from verified JWT mapping. Even
  an admin cannot use this endpoint to lock another trainer's team.
- The body permits only `save_file_id`. Client identity, hash, snapshots,
  deadlines and late flags are rejected as extra fields.
- Application validates season/matchday/membership, own parsed non-deleted save
  and exactly six Pokemon. The SQL transaction rechecks eligibility and the
  parsed payload to prevent source changes between read and write.
- Migration 019 adds `api_upsert_team_lock`, SECURITY INVOKER with fixed empty
  search_path. EXECUTE is revoked from PUBLIC/anon/authenticated and granted to
  service_role. Existing table/view grants and RLS policies are unchanged.
- The trusted backend supplies DTO-derived snapshots. The RPC checks their
  structure and source version, not a second independent privacy projection.
- Lock upsert and deduplicated TEAM_LOCKED event commit or roll back together.
  Failures return stable API errors without backend SQL/credential details.
- Public snapshots omit ability, nature, IVs, EVs, original trainer and arbitrary
  metadata. Private snapshots remain owner/admin through existing views/RLS.

PostgreSQL local role/rollback/concurrency checks passed. Real Supabase 019
validation passed 13 checks with temporary Auth users and complete cleanup.
Direct UPDATE can return HTTP 200 with zero rows under RLS; the validator also
verifies unchanged stored rows. No policies were relaxed. Forced post-write
rollback is local-only. See [Phase 8C report](phase8c-team-lock.md).

Approved 8D.0 resolves the shop-eligibility blocker. Migration 020 adds the
explicit same-season current pointer and typed ban windows, plus backend-only
SECURITY INVOKER helpers with fixed search_path. NULL/cancelled pointer fails
closed; resolved cases and inclusive/missing-window semantics govern bans.
No existing RLS is relaxed. DONE local + staging (5 checks and cleanup PASS).
The new pointer is server-owned even for browser admins; existing column grants
are preserved. 021 normal purchase is service-role-only, SECURITY INVOKER with
empty search_path. Purchase/ledger/event share one transaction and wallet lock;
strict input, verified enabled identity, whitelist-only business errors and
private receipts. RLS/direct write restrictions are unchanged. DONE local;
021 staging pending. [Contract](phase8d-purchases.md).

## Helper Functions

Migration `010_security_helpers.sql` adds:

- `current_auth_uid()`: resolves Supabase `auth.uid()`. Local PostgreSQL
  validation falls back to `request.jwt.claim.sub`.
- `current_trainer_id()`: SECURITY DEFINER lookup from `auth_user_id` to enabled
  trainer id.
- `is_current_user_admin()`: SECURITY DEFINER check against `trainers.is_admin`.
- `current_user_owns_trainer(uuid)`: small ownership predicate.

Security notes:

- The SECURITY DEFINER functions use fixed `search_path`.
- Helper execution is revoked from `public` and `anon`, then granted only to
  `authenticated`/`service_role` when those roles exist.
- The helpers only expose identity booleans/ids. They do not expose raw table
  payloads.

## Read Surfaces

Use these views from the future frontend/API when possible:

Current/private client views use `security_invoker` plus `security_barrier`, so
PostgreSQL applies the querying user's RLS instead of the view owner's
privileges. Public projections are explicit safe exceptions that stay readable
by design.

- Public authenticated projections: `public_trainers`, `public_seasons`,
  `public_season_players`, `public_season_player_stats`,
  `public_trainer_flags`, `public_season_config_versions`, `public_divisions`,
  `public_division_memberships`, `public_matchdays`, `public_matches`,
  `public_matchday_snapshots`, `public_matchday_movements`,
  `public_shop_items`, `public_shop_promotions`, `public_coin_balances`,
  `public_team_locks`, `public_activity_events`, `public_hall_of_fame`,
  `public_cups`, `public_cup_participants`, `public_cup_matches`,
  `public_cup_standings`, `public_trial_cases`, `public_penalties`.
- Owner/admin projections: `current_trainer_profile`, `current_trainer_flags`,
  `current_pokemon_flags`, `current_purchases`, `current_redemptions`,
  `current_coin_transactions`, `current_save_files`, `current_parsed_saves`,
  `current_team_locks`, `current_activity_events`, `current_trial_cases`,
  `current_trial_votes`, `current_penalties`.

Public projections stay safe by shape and are reopened with definer semantics
where the validator and product need full public listing visibility.

Important column protections:

- `public_trainers` hides `auth_user_id`, `metadata` and `is_admin`.
- `public_team_locks` exposes `public_team_snapshot` only.
- `current_team_locks` exposes `private_team_snapshot` only to owner/admin.
- `current_parsed_saves` exposes parsed private save payload only to owner/admin.
- `public_shop_promotions` hides pending/future/cancelled promotions until they
  are visible.
- `public_coin_balances` exposes aggregate balances, not full ledger details.

The public views are intentionally projections, not full table mirrors. They are
safe-by-shape: if a column is private, it should not appear in the view.

## Table Audit

| Table | Classification | Client read path | Write path |
| --- | --- | --- | --- |
| `app_settings` | Admin | base table admin only | admin/server |
| `trainers` | Private identity + public profile | `public_trainers`, `current_trainer_profile` | admin/server |
| `seasons` | Public competition metadata | `public_seasons` | admin/server |
| `season_players` | Public participation + private admin fields | `public_season_players`, own/admin base | admin/server |
| `season_player_stats` | Public season stats | `public_season_player_stats` | admin/server |
| `trainer_flags` | Public only for robbed=true, otherwise owner/admin | `public_trainer_flags`, `current_trainer_flags` | admin/server |
| `pokemon_flags` | Owner/admin | `current_pokemon_flags` | admin/server |
| `season_config_versions` | Public rules once created | `public_season_config_versions` | admin/server |
| `divisions` | Public competition structure | `public_divisions` | admin/server |
| `division_memberships` | Public competition structure | `public_division_memberships` | admin/server |
| `matchdays` | Public schedule/status | `public_matchdays` | admin/server |
| `matches` | Public results | `public_matches` | admin/server |
| `matchday_snapshots` | Public official snapshot | `public_matchday_snapshots` | admin/server |
| `matchday_movements` | Public movement history | `public_matchday_movements` | admin/server |
| `shop_items` | Public catalog | `public_shop_items` | admin/server |
| `shop_promotions` | Visible promotions public, pending hidden | `public_shop_promotions` | admin/server/API |
| `purchases` | Owner/admin | `current_purchases` | server/API only |
| `redemptions` | Owner/admin | `current_redemptions` | server/API only |
| `coin_transactions` | Owner/admin details, public aggregate balance | `current_coin_transactions`, `public_coin_balances` | server/API only |
| `save_files` | Owner/admin | `current_save_files` | server/API only |
| `parsed_saves` | Owner/admin private payload | `current_parsed_saves` | server/parser only |
| `team_locks` | Public team + private own/admin team | `public_team_locks`, `current_team_locks` | server/API only |
| `activity_events` | Visibility-based | `public_activity_events`, `current_activity_events` | server/API only |
| `hall_of_fame_entries` | Public historical | `public_hall_of_fame` | admin/server |
| `season_archive_snapshots` | Admin audit/export | base table admin only | admin/server |
| `cups` | Public cup metadata | `public_cups` | admin/server |
| `cup_participants` | Public cup participants | `public_cup_participants` | admin/server |
| `cup_matches` | Public cup matches | `public_cup_matches` | admin/server |
| `cup_standings` | Public cup standings | `public_cup_standings` | admin/server |
| `trial_cases` | Public if marked public, own/admin full | `public_trial_cases`, `current_trial_cases` | owner/admin/server |
| `trial_votes` | Voter/admin | `current_trial_votes` | voter/admin/server |
| `penalties` | Public sanitized, owner/admin full | `public_penalties`, `current_penalties` | admin/server |

## Mutations

Fase 7 deliberately does not implement the Fase 8 API. The security boundary is
prepared for it:

- Purchases, redemptions, coin ledger, save metadata, parsed saves, team locks and
  activity events have no general user insert/update policy.
- These operations should be performed by server/API/RPC code using
  `service_role` or tightly scoped transaction functions.
- Admin-managed official state uses `is_current_user_admin()` policies.
- Trainer-created trials/votes have narrow owner/voter policies because they are
  user-originated product actions.

Critical future API operations:

- purchase item + ledger + activity event;
- redeem purchase + flags/effect + activity event;
- upload save metadata + storage write + parse queue;
- write parsed save from parser;
- lock team for matchday: implemented and staging-validated in Phase 8C via backend-only RPC;
- close matchday + rewards + snapshot + movements;
- create/update season config;
- retire/abandon/disqualify trainer;
- finalize Hall of Fame/archive.

## Storage

Bucket:

- `raw-saves`
- private (`public = false`)

Migration `009_seed.sql` creates or updates the bucket when Supabase `storage`
schema exists. Migration `013_storage_policies.sql` is policy-only and
compatible with Supabase Cloud; it does not try to change ownership or toggle
RLS on `storage.objects`.

Path convention:

```text
{trainer_id}/{file-or-subpath}
```

Storage object policy:

- authenticated trainer can read/write only objects whose first path segment is
  their own `current_trainer_id()`;
- admin can read/write any `raw-saves` object;
- anon receives no app storage access;
- service_role remains server-only.

Plain PostgreSQL validation skips storage policy creation if there is no
`storage` schema. Real Supabase/local Supabase must still be checked before
cutover.

## Validated

Validated against PostgreSQL 17.11 local with Supabase role mocks:

- migrations 001-021 apply in order (purchase/ban checks added in 8D);
- `bootstrap.sql` applies as a single SQL Editor artifact;
- reset/build/rebuild works;
- all 32 public V2 tables have RLS enabled;
- normal trainer A sees only own private saves, purchases and team locks;
- normal trainer B sees only own private saves, purchases and team locks;
- public team lock view exposes both public teams without private snapshots;
- admin sees both private rows and can update admin-managed season state;
- admin cannot directly insert into the server-only coin ledger;
- anon cannot read authenticated app projections;
- service_role bypass sees private rows as expected.
- Migration 019 permissions, replacement, frozen snapshots, event dedupe,
  real rollback on event failure and four concurrent writes pass locally.

Pending before production cutover:

- run the same bootstrap on a clean Supabase project;
- confirm `auth.uid()` path with real Supabase Auth users;
- confirm `storage.objects` policies in Supabase storage;
- set the real admin trainer row with `is_admin = true`;
- keep the service role key exclusively server-side.

## Real Supabase Validation

Fase 7.1 adds an automated validator for a real clean Supabase staging project:

```powershell
py tools\validate_supabase_v2_rls.py --env-file .env.supabase-v2-rls.local
```

Local env template:

```text
.env.supabase-v2-rls.example
```

Required variables:

- `POKEAPP_V2_SUPABASE_URL`
- `POKEAPP_V2_SUPABASE_ANON_KEY`
- `POKEAPP_V2_SUPABASE_SERVICE_ROLE_KEY`

Optional:

- `POKEAPP_V2_TEST_EMAIL_DOMAIN`

The validator does not print passwords or tokens. It creates temporary Auth
users and fixture rows with a unique `run_id`, runs real JWT requests through
Supabase Auth/PostgREST/Storage, and cleans up by default.

Real test matrix covered by the validator:

- Auth users: Trainer A, Trainer B, Admin and authenticated user without trainer.
- `auth.uid()` through real JWT requests.
- `current_trainer_id()` mapping for Trainer A/B.
- `is_current_user_admin()` true only for Admin.
- `anon` cannot read authenticated app projections.
- `public_trainers` hides `auth_user_id`, `metadata` and `is_admin`.
- Trainer A/B can read public league/shop surfaces.
- Trainer A cannot read Trainer B save metadata, parsed saves, purchases,
  redemptions, ledger rows or private TeamLock.
- `public_team_locks` exposes public snapshots without private snapshot columns.
- `current_team_locks` exposes private snapshot only to owner/admin.
- public coin balance view exposes aggregate balances only.
- Activity visibility: public + own owner events for normal trainers, admin sees
  all.
- Normal trainers cannot directly mutate matches, matchdays, official snapshots,
  purchases, redemptions, coin ledger or promotion stock.
- Admin can read private rows and update admin-managed season state.
- Admin still cannot directly insert API-only economy rows such as
  `coin_transactions` and `purchases`.
- `service_role` can perform backend-only fixture operations.
- `raw-saves` bucket is private.
- Trainer A can upload/read only inside its own storage namespace.
- Trainer A cannot upload/list/read Trainer B storage namespace.
- Anon cannot read raw saves.
- Service role can read backend storage objects.

Status as of this checkpoint:

- Validator implemented locally.
- Real Supabase staging `Pokeapp 2.0` has migrations 010, 011, 012, 013, 014,
  015, 016, 017 and 018 applied through the Supabase connector.
- SQL-level staging checks confirmed 32 public tables, 32 RLS-enabled public
  tables, 82 public policies, 37 views, 13 `security_invoker` views and 24 safe
  public definer views.
- Storage policies from 013 are policy-only, Cloud-safe and already applied in
  the real staging project.
- The real validator passed against the live staging project with
  `RESULT ok checks=13`.
- Fase 7.1 and Fase 7.2 are closed. Auth bridge/API and 8B-H are implemented;
  Phase 8C is DONE and migration 019 is applied/validated in V2 staging.
  Runtime remains Streamlit legacy and V2 is not its source of truth.
