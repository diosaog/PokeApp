-- PokeApp Supabase V2 security layer.
-- 018_public_views_visibility: keep public projections readable while private projections stay invoker-based.

begin;

do $$
declare
  view_name text;
  view_names text[] := array[
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
      'alter view public.%I set (security_invoker = false, security_barrier = true)',
      view_name
    );
  end loop;
end;
$$;

commit;
