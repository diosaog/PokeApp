-- PokeApp Supabase V2 security layer.
-- 012_security_views: safe read projections for authenticated clients.

begin;

create or replace view public.public_trainers
with (security_barrier = true)
as
select
  id,
  display_name,
  slug,
  globally_enabled,
  created_at,
  updated_at
from public.trainers
where globally_enabled = true;

create or replace view public.current_trainer_profile
with (security_barrier = true)
as
select
  id,
  display_name,
  slug,
  auth_user_id,
  globally_enabled,
  is_admin,
  metadata,
  created_at,
  updated_at
from public.trainers
where id = public.current_trainer_id()
   or public.is_current_user_admin();

create or replace view public.public_seasons
with (security_barrier = true)
as
select
  id,
  name,
  status,
  started_at,
  finished_at,
  archived_at,
  discarded_at,
  created_at,
  updated_at
from public.seasons
where status <> 'discarded';

create or replace view public.public_season_players
with (security_barrier = true)
as
select
  id,
  season_id,
  trainer_id,
  status,
  seed_order,
  joined_at,
  left_at,
  created_at,
  updated_at
from public.season_players;

create or replace view public.public_season_player_stats
with (security_barrier = true)
as
select
  season_player_id,
  season_id,
  trainer_id,
  badges_count,
  updated_at
from public.season_player_stats;

create or replace view public.public_trainer_flags
with (security_barrier = true)
as
select
  id,
  season_id,
  trainer_id,
  season_player_id,
  flag_type,
  flag_value,
  created_at,
  updated_at
from public.trainer_flags
where flag_type = 'robbed'
  and flag_value = true;

create or replace view public.current_trainer_flags
with (security_barrier = true)
as
select *
from public.trainer_flags
where trainer_id = public.current_trainer_id()
   or public.is_current_user_admin();

create or replace view public.current_pokemon_flags
with (security_barrier = true)
as
select *
from public.pokemon_flags
where trainer_id = public.current_trainer_id()
   or public.is_current_user_admin();

create or replace view public.public_season_config_versions
with (security_barrier = true)
as
select
  id,
  season_id,
  version_number,
  name,
  effective_from_matchday,
  total_matchdays,
  division_count,
  promotion_relegation_count,
  scoring_json,
  coin_rewards_json,
  rules_json,
  locked_at,
  created_at
from public.season_config_versions;

create or replace view public.public_divisions
with (security_barrier = true)
as
select
  id,
  season_id,
  code,
  name,
  tier_order,
  created_at
from public.divisions;

create or replace view public.public_division_memberships
with (security_barrier = true)
as
select
  id,
  season_id,
  season_player_id,
  division_id,
  effective_from_matchday_number,
  effective_to_matchday_number,
  source_matchday_id,
  reason,
  created_at
from public.division_memberships;

create or replace view public.public_matchdays
with (security_barrier = true)
as
select
  id,
  season_id,
  number,
  status,
  season_config_version_id,
  opened_at,
  closed_at,
  created_at,
  updated_at
from public.matchdays;

create or replace view public.public_matches
with (security_barrier = true)
as
select
  id,
  season_id,
  matchday_id,
  division_id,
  player_a_id,
  player_b_id,
  winner_id,
  status,
  result_code,
  created_at,
  updated_at
from public.matches;

create or replace view public.public_matchday_snapshots
with (security_barrier = true)
as
select
  id,
  season_id,
  matchday_id,
  config_version_id,
  revision,
  snapshot_schema_version,
  closed_at,
  snapshot,
  created_at,
  updated_at
from public.matchday_snapshots;

create or replace view public.public_matchday_movements
with (security_barrier = true)
as
select
  id,
  season_id,
  matchday_id,
  season_player_id,
  from_division_id,
  to_division_id,
  movement_type,
  reason,
  created_at
from public.matchday_movements;

create or replace view public.public_shop_items
with (security_barrier = true)
as
select
  id,
  code,
  name,
  category,
  description,
  base_price,
  enabled,
  image_key,
  created_at,
  updated_at
from public.shop_items
where enabled = true;

create or replace view public.public_shop_promotions
with (security_barrier = true)
as
select
  id,
  season_id,
  matchday_id,
  shop_item_id,
  promotion_type,
  status,
  base_price,
  effective_price,
  stock_total,
  stock_used,
  announced_at,
  activates_at,
  ends_at,
  exhausted_at,
  created_at,
  updated_at
from public.shop_promotions
where status in ('active', 'exhausted', 'ended')
  and (activates_at is null or activates_at <= now());

create or replace view public.current_purchases
with (security_barrier = true)
as
select *
from public.purchases
where trainer_id = public.current_trainer_id()
   or public.is_current_user_admin();

create or replace view public.current_redemptions
with (security_barrier = true)
as
select *
from public.redemptions
where trainer_id = public.current_trainer_id()
   or public.is_current_user_admin();

create or replace view public.current_coin_transactions
with (security_barrier = true)
as
select *
from public.coin_transactions
where trainer_id = public.current_trainer_id()
   or public.is_current_user_admin();

create or replace view public.public_coin_balances
with (security_barrier = true)
as
select
  season_id,
  trainer_id,
  coalesce(sum(amount), 0)::integer as balance
from public.coin_transactions
group by season_id, trainer_id;

create or replace view public.current_save_files
with (security_barrier = true)
as
select *
from public.save_files
where trainer_id = public.current_trainer_id()
   or public.is_current_user_admin();

create or replace view public.current_parsed_saves
with (security_barrier = true)
as
select ps.*
from public.parsed_saves as ps
join public.save_files as sf
  on sf.id = ps.save_file_id
where sf.trainer_id = public.current_trainer_id()
   or public.is_current_user_admin();

create or replace view public.public_team_locks
with (security_barrier = true)
as
select
  id,
  season_id,
  matchday_id,
  trainer_id,
  season_player_id,
  locked_at,
  deadline_at,
  is_late,
  public_team_snapshot,
  created_at,
  updated_at
from public.team_locks;

create or replace view public.current_team_locks
with (security_barrier = true)
as
select *
from public.team_locks
where trainer_id = public.current_trainer_id()
   or public.is_current_user_admin();

create or replace view public.public_activity_events
with (security_barrier = true)
as
select
  id,
  season_id,
  type,
  actor_trainer_id,
  trainer_id,
  visibility,
  dedupe_key,
  context,
  payload,
  created_at
from public.activity_events
where visibility = 'public';

create or replace view public.current_activity_events
with (security_barrier = true)
as
select *
from public.activity_events
where visibility = 'public'
   or public.is_current_user_admin()
   or (
     visibility = 'owner'
     and trainer_id = public.current_trainer_id()
   );

create or replace view public.public_hall_of_fame
with (security_barrier = true)
as
select
  id,
  season_id,
  competition_type,
  champion_trainer_id,
  finalist_trainer_id,
  finalized_at,
  team_snapshot,
  created_at
from public.hall_of_fame_entries;

create or replace view public.public_cups
with (security_barrier = true)
as
select
  id,
  season_id,
  name,
  competition_type,
  format,
  status,
  started_at,
  finished_at,
  created_at,
  updated_at
from public.cups
where status <> 'discarded';

create or replace view public.public_cup_participants
with (security_barrier = true)
as
select
  id,
  cup_id,
  trainer_id,
  display_name,
  seed_order,
  status,
  created_at
from public.cup_participants;

create or replace view public.public_cup_matches
with (security_barrier = true)
as
select
  id,
  cup_id,
  round_number,
  bracket_position,
  participant_a_id,
  participant_b_id,
  winner_participant_id,
  status,
  score,
  created_at,
  updated_at
from public.cup_matches;

create or replace view public.public_cup_standings
with (security_barrier = true)
as
select
  id,
  cup_id,
  participant_id,
  position,
  points,
  wins,
  losses,
  updated_at
from public.cup_standings;

create or replace view public.public_trial_cases
with (security_barrier = true)
as
select
  id,
  season_id,
  matchday_id,
  accused_trainer_id,
  created_by_trainer_id,
  title,
  description,
  status,
  created_at,
  resolved_at,
  updated_at
from public.trial_cases
where status <> 'cancelled'
  and (
    payload ->> 'is_public' is null
    or lower(payload ->> 'is_public') not in ('false', '0', 'no')
  );

create or replace view public.current_trial_cases
with (security_barrier = true)
as
select *
from public.trial_cases
where public.is_current_user_admin()
   or created_by_trainer_id = public.current_trainer_id()
   or accused_trainer_id = public.current_trainer_id()
   or (
     payload ->> 'is_public' is null
     or lower(payload ->> 'is_public') not in ('false', '0', 'no')
   );

create or replace view public.current_trial_votes
with (security_barrier = true)
as
select *
from public.trial_votes
where voter_trainer_id = public.current_trainer_id()
   or public.is_current_user_admin();

create or replace view public.public_penalties
with (security_barrier = true)
as
select
  id,
  season_id,
  trainer_id,
  matchday_id,
  trial_case_id,
  penalty_type,
  amount,
  created_at,
  resolved_at
from public.penalties;

create or replace view public.current_penalties
with (security_barrier = true)
as
select *
from public.penalties
where trainer_id = public.current_trainer_id()
   or public.is_current_user_admin();

do $$
declare
  view_name text;
  view_names text[] := array[
    'current_activity_events',
    'current_coin_transactions',
    'current_parsed_saves',
    'current_penalties',
    'current_pokemon_flags',
    'current_purchases',
    'current_redemptions',
    'current_save_files',
    'current_team_locks',
    'current_trainer_flags',
    'current_trainer_profile',
    'current_trial_cases',
    'current_trial_votes',
    'public_activity_events',
    'public_coin_balances',
    'public_cup_matches',
    'public_cup_participants',
    'public_cup_standings',
    'public_cups',
    'public_division_memberships',
    'public_divisions',
    'public_hall_of_fame',
    'public_matchday_movements',
    'public_matchday_snapshots',
    'public_matchdays',
    'public_matches',
    'public_penalties',
    'public_season_config_versions',
    'public_season_player_stats',
    'public_season_players',
    'public_seasons',
    'public_shop_items',
    'public_shop_promotions',
    'public_team_locks',
    'public_trainer_flags',
    'public_trainers',
    'public_trial_cases'
  ];
begin
  foreach view_name in array view_names loop
    execute format('revoke all on table public.%I from public', view_name);

    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on table public.%I from anon', view_name);
    end if;

    if exists (select 1 from pg_roles where rolname = 'authenticated') then
      execute format('grant select on table public.%I to authenticated', view_name);
    end if;

    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant all privileges on table public.%I to service_role', view_name);
    end if;
  end loop;
end;
$$;

comment on view public.public_trainers is
  'Safe trainer projection. Hides auth_user_id, metadata and is_admin.';
comment on view public.public_team_locks is
  'Public Team Preview projection. Exposes public_team_snapshot only.';
comment on view public.current_team_locks is
  'Owner/admin TeamLock projection. Includes private_team_snapshot.';
comment on view public.public_shop_promotions is
  'Visible promotions only. Pending/future/cancelled promotions remain admin/server-only.';
comment on view public.public_coin_balances is
  'Public balance aggregate. Detailed coin_transactions remain owner/admin.';

commit;
