# Supabase V2 Security And RLS

Checkpoint: Fase 7.

This document is the security contract for the greenfield Supabase V2 schema. It
does not connect Streamlit, React or API runtime yet. It defines what the future
client/API may read or mutate.

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
- Helper execution is revoked from `public` and granted only to
  `authenticated`/`service_role` when those roles exist.
- The helpers only expose identity booleans/ids. They do not expose raw table
  payloads.

## Read Surfaces

Use these views from the future frontend/API when possible:

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
- lock team for matchday;
- close matchday + rewards + snapshot + movements;
- create/update season config;
- retire/abandon/disqualify trainer;
- finalize Hall of Fame/archive.

## Storage

Bucket:

- `raw-saves`
- private (`public = false`)

Migration `009_seed.sql` creates or updates the bucket when Supabase `storage`
schema exists. Migration `013_storage_policies.sql` adds storage object policies
when `storage.objects` exists.

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

- migrations 001-013 apply in order;
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

Pending before production cutover:

- run the same bootstrap on a clean Supabase project;
- confirm `auth.uid()` path with real Supabase Auth users;
- confirm `storage.objects` policies in Supabase storage;
- set the real admin trainer row with `is_admin = true`;
- keep the service role key exclusively server-side.
