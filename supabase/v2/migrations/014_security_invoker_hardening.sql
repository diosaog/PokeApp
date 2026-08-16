-- PokeApp Supabase V2 security layer.
-- 014_security_invoker_hardening: make client views use caller RLS and lock anon helper RPC access.

begin;

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
    execute format(
      'alter view public.%I set (security_invoker = true, security_barrier = true)',
      view_name
    );
  end loop;
end;
$$;

revoke all on function public.current_auth_uid() from public;
revoke all on function public.current_trainer_id() from public;
revoke all on function public.is_current_user_admin() from public;
revoke all on function public.current_user_owns_trainer(uuid) from public;

do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on function public.current_auth_uid() from anon;
    revoke all on function public.current_trainer_id() from anon;
    revoke all on function public.is_current_user_admin() from anon;
    revoke all on function public.current_user_owns_trainer(uuid) from anon;
  end if;

  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    grant execute on function public.current_auth_uid() to authenticated;
    grant execute on function public.current_trainer_id() to authenticated;
    grant execute on function public.is_current_user_admin() to authenticated;
    grant execute on function public.current_user_owns_trainer(uuid) to authenticated;
  end if;

  if exists (select 1 from pg_roles where rolname = 'service_role') then
    grant execute on function public.current_auth_uid() to service_role;
    grant execute on function public.current_trainer_id() to service_role;
    grant execute on function public.is_current_user_admin() to service_role;
    grant execute on function public.current_user_owns_trainer(uuid) to service_role;
  end if;
end;
$$;

commit;
