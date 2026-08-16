-- PokeApp Supabase V2 security layer.
-- 011_rls_policies: default-deny RLS on application tables.

begin;

do $$
declare
  table_name text;
  table_names text[] := array[
    'activity_events',
    'app_settings',
    'coin_transactions',
    'cup_matches',
    'cup_participants',
    'cup_standings',
    'cups',
    'division_memberships',
    'divisions',
    'hall_of_fame_entries',
    'matchday_movements',
    'matchday_snapshots',
    'matchdays',
    'matches',
    'parsed_saves',
    'penalties',
    'pokemon_flags',
    'purchases',
    'redemptions',
    'save_files',
    'season_archive_snapshots',
    'season_config_versions',
    'season_player_stats',
    'season_players',
    'seasons',
    'shop_items',
    'shop_promotions',
    'team_locks',
    'trainer_flags',
    'trainers',
    'trial_cases',
    'trial_votes'
  ];
begin
  foreach table_name in array table_names loop
    execute format('alter table public.%I enable row level security', table_name);
    execute format('revoke all on table public.%I from public', table_name);

    if exists (select 1 from pg_roles where rolname = 'anon') then
      execute format('revoke all on table public.%I from anon', table_name);
    end if;

    if exists (select 1 from pg_roles where rolname = 'authenticated') then
      execute format(
        'grant select, insert, update, delete on table public.%I to authenticated',
        table_name
      );
    end if;

    if exists (select 1 from pg_roles where rolname = 'service_role') then
      execute format('grant all privileges on table public.%I to service_role', table_name);
    end if;
  end loop;

  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    grant usage on schema public to authenticated;
  end if;

  if exists (select 1 from pg_roles where rolname = 'service_role') then
    grant usage on schema public to service_role;
  end if;
end;
$$;

create policy app_settings_admin_read
on public.app_settings
for select
using (public.is_current_user_admin());

create policy app_settings_admin_insert
on public.app_settings
for insert
with check (public.is_current_user_admin());

create policy app_settings_admin_update
on public.app_settings
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy trainers_self_admin_read
on public.trainers
for select
using (id = public.current_trainer_id() or public.is_current_user_admin());

create policy trainers_admin_insert
on public.trainers
for insert
with check (public.is_current_user_admin());

create policy trainers_admin_update
on public.trainers
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy seasons_admin_read
on public.seasons
for select
using (public.is_current_user_admin());

create policy seasons_admin_insert
on public.seasons
for insert
with check (public.is_current_user_admin());

create policy seasons_admin_update
on public.seasons
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy season_players_owner_admin_read
on public.season_players
for select
using (trainer_id = public.current_trainer_id() or public.is_current_user_admin());

create policy season_players_admin_insert
on public.season_players
for insert
with check (public.is_current_user_admin());

create policy season_players_admin_update
on public.season_players
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy season_player_stats_owner_admin_read
on public.season_player_stats
for select
using (trainer_id = public.current_trainer_id() or public.is_current_user_admin());

create policy season_player_stats_admin_insert
on public.season_player_stats
for insert
with check (public.is_current_user_admin());

create policy season_player_stats_admin_update
on public.season_player_stats
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy trainer_flags_owner_admin_read
on public.trainer_flags
for select
using (trainer_id = public.current_trainer_id() or public.is_current_user_admin());

create policy trainer_flags_admin_insert
on public.trainer_flags
for insert
with check (public.is_current_user_admin());

create policy trainer_flags_admin_update
on public.trainer_flags
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy pokemon_flags_owner_admin_read
on public.pokemon_flags
for select
using (trainer_id = public.current_trainer_id() or public.is_current_user_admin());

create policy pokemon_flags_admin_insert
on public.pokemon_flags
for insert
with check (public.is_current_user_admin());

create policy pokemon_flags_admin_update
on public.pokemon_flags
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy season_config_versions_admin_read
on public.season_config_versions
for select
using (public.is_current_user_admin());

create policy season_config_versions_admin_insert
on public.season_config_versions
for insert
with check (public.is_current_user_admin());

create policy season_config_versions_admin_update
on public.season_config_versions
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy divisions_admin_read
on public.divisions
for select
using (public.is_current_user_admin());

create policy divisions_admin_insert
on public.divisions
for insert
with check (public.is_current_user_admin());

create policy divisions_admin_update
on public.divisions
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy division_memberships_admin_read
on public.division_memberships
for select
using (public.is_current_user_admin());

create policy division_memberships_admin_insert
on public.division_memberships
for insert
with check (public.is_current_user_admin());

create policy division_memberships_admin_update
on public.division_memberships
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy matchdays_admin_read
on public.matchdays
for select
using (public.is_current_user_admin());

create policy matchdays_admin_insert
on public.matchdays
for insert
with check (public.is_current_user_admin());

create policy matchdays_admin_update
on public.matchdays
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy matches_admin_read
on public.matches
for select
using (public.is_current_user_admin());

create policy matches_admin_insert
on public.matches
for insert
with check (public.is_current_user_admin());

create policy matches_admin_update
on public.matches
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy matchday_snapshots_admin_read
on public.matchday_snapshots
for select
using (public.is_current_user_admin());

create policy matchday_snapshots_admin_insert
on public.matchday_snapshots
for insert
with check (public.is_current_user_admin());

create policy matchday_snapshots_admin_update
on public.matchday_snapshots
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy matchday_movements_admin_read
on public.matchday_movements
for select
using (public.is_current_user_admin());

create policy matchday_movements_admin_insert
on public.matchday_movements
for insert
with check (public.is_current_user_admin());

create policy matchday_movements_admin_update
on public.matchday_movements
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy shop_items_admin_read
on public.shop_items
for select
using (public.is_current_user_admin());

create policy shop_items_admin_insert
on public.shop_items
for insert
with check (public.is_current_user_admin());

create policy shop_items_admin_update
on public.shop_items
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy shop_promotions_admin_read
on public.shop_promotions
for select
using (public.is_current_user_admin());

create policy shop_promotions_admin_insert
on public.shop_promotions
for insert
with check (public.is_current_user_admin());

create policy shop_promotions_admin_update
on public.shop_promotions
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy purchases_owner_admin_read
on public.purchases
for select
using (trainer_id = public.current_trainer_id() or public.is_current_user_admin());

create policy redemptions_owner_admin_read
on public.redemptions
for select
using (trainer_id = public.current_trainer_id() or public.is_current_user_admin());

create policy coin_transactions_owner_admin_read
on public.coin_transactions
for select
using (trainer_id = public.current_trainer_id() or public.is_current_user_admin());

create policy save_files_owner_admin_read
on public.save_files
for select
using (trainer_id = public.current_trainer_id() or public.is_current_user_admin());

create policy parsed_saves_owner_admin_read
on public.parsed_saves
for select
using (
  public.is_current_user_admin()
  or exists (
    select 1
    from public.save_files as sf
    where sf.id = parsed_saves.save_file_id
      and sf.trainer_id = public.current_trainer_id()
  )
);

create policy team_locks_owner_admin_read
on public.team_locks
for select
using (trainer_id = public.current_trainer_id() or public.is_current_user_admin());

create policy activity_events_visibility_read
on public.activity_events
for select
using (
  visibility = 'public'
  or public.is_current_user_admin()
  or (
    visibility = 'owner'
    and trainer_id = public.current_trainer_id()
  )
);

create policy hall_of_fame_entries_admin_read
on public.hall_of_fame_entries
for select
using (public.is_current_user_admin());

create policy hall_of_fame_entries_admin_insert
on public.hall_of_fame_entries
for insert
with check (public.is_current_user_admin());

create policy hall_of_fame_entries_admin_update
on public.hall_of_fame_entries
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy season_archive_snapshots_admin_read
on public.season_archive_snapshots
for select
using (public.is_current_user_admin());

create policy season_archive_snapshots_admin_insert
on public.season_archive_snapshots
for insert
with check (public.is_current_user_admin());

create policy season_archive_snapshots_admin_update
on public.season_archive_snapshots
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy cups_admin_read
on public.cups
for select
using (public.is_current_user_admin());

create policy cups_admin_insert
on public.cups
for insert
with check (public.is_current_user_admin());

create policy cups_admin_update
on public.cups
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy cup_participants_admin_read
on public.cup_participants
for select
using (public.is_current_user_admin());

create policy cup_participants_admin_insert
on public.cup_participants
for insert
with check (public.is_current_user_admin());

create policy cup_participants_admin_update
on public.cup_participants
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy cup_matches_admin_read
on public.cup_matches
for select
using (public.is_current_user_admin());

create policy cup_matches_admin_insert
on public.cup_matches
for insert
with check (public.is_current_user_admin());

create policy cup_matches_admin_update
on public.cup_matches
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy cup_standings_admin_read
on public.cup_standings
for select
using (public.is_current_user_admin());

create policy cup_standings_admin_insert
on public.cup_standings
for insert
with check (public.is_current_user_admin());

create policy cup_standings_admin_update
on public.cup_standings
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

create policy trial_cases_owner_admin_read
on public.trial_cases
for select
using (
  public.is_current_user_admin()
  or created_by_trainer_id = public.current_trainer_id()
  or accused_trainer_id = public.current_trainer_id()
);

create policy trial_cases_owner_insert
on public.trial_cases
for insert
with check (created_by_trainer_id = public.current_trainer_id());

create policy trial_cases_owner_update
on public.trial_cases
for update
using (
  public.is_current_user_admin()
  or created_by_trainer_id = public.current_trainer_id()
)
with check (
  public.is_current_user_admin()
  or created_by_trainer_id = public.current_trainer_id()
);

create policy trial_votes_voter_admin_read
on public.trial_votes
for select
using (voter_trainer_id = public.current_trainer_id() or public.is_current_user_admin());

create policy trial_votes_voter_insert
on public.trial_votes
for insert
with check (voter_trainer_id = public.current_trainer_id());

create policy trial_votes_voter_update
on public.trial_votes
for update
using (voter_trainer_id = public.current_trainer_id() or public.is_current_user_admin())
with check (voter_trainer_id = public.current_trainer_id() or public.is_current_user_admin());

create policy penalties_owner_admin_read
on public.penalties
for select
using (trainer_id = public.current_trainer_id() or public.is_current_user_admin());

create policy penalties_admin_insert
on public.penalties
for insert
with check (public.is_current_user_admin());

create policy penalties_admin_update
on public.penalties
for update
using (public.is_current_user_admin())
with check (public.is_current_user_admin());

commit;
