-- DESTRUCTIVE DEVELOPMENT RESET FOR POKEAPP SUPABASE V2 ONLY.
-- Do not run this against production or the current V1 database.
-- This file drops V2 public tables, functions and seed data so migrations can be
-- reapplied from an empty development/staging database.

begin;

drop table if exists public.team_lock_first_fixations cascade;
drop table if exists public.matchday_start_evidence cascade;
drop table if exists public.season_reward_rule_revisions cascade;
drop function if exists public.live_reward_rules(uuid);
drop function if exists public.first_start_immutable() cascade;
drop function if exists public.record_first_matchday_start() cascade;
drop function if exists public.lock_timing_at(uuid,timestamptz);
drop function if exists public.record_first_team_fixation() cascade;

drop function if exists public.observed_progress_read(uuid,uuid);
drop table if exists public.progress_reward_claims cascade;
drop function if exists public.progress_reward_immutable() cascade;
drop function if exists public.reward_current_save_observation() cascade;
drop function if exists public.settle_observed_progress_rewards(uuid,uuid);
drop function if exists public.purchased_revive_overlap(uuid,uuid,uuid);
drop function if exists public.inventory_shield_targets(uuid,uuid);
drop function if exists public.commit_pokemon_identity_v038(jsonb);
-- Source-validation helpers depend on the row types dropped below (CASCADE).

-- Local validation only: remove the additive administration helpers and state.
do $$ declare f regprocedure; begin
  for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and (p.proname like 'championship_%' or p.proname like 'initial_assignment_%' or p.proname like 'admin_setup_%' or p.proname like 'api_admin_%' or p.proname like 'matchday_%' or p.proname like 'participant_%' or p.proname like 'api_participant_%' or p.proname like 'league_%' or p.proname like 'lifecycle_%' or p.proname like 'trials_%' or p.proname like 'api_trial%' or p.proname like 'cup_%' or p.proname like 'api_cup_%') loop
    execute format('drop function if exists %s cascade',f);
  end loop;
end $$;
drop table if exists public.league_championship_resolutions cascade;
drop table if exists public.league_finalizations cascade;
drop table if exists public.initial_division_snapshots cascade;
drop table if exists public.admin_operation_receipts cascade;
drop table if exists public.season_admin_state cascade;
drop table if exists public.matchday_snapshot_revisions cascade;

drop function if exists public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid);
-- PL/pgSQL bodies do not depend on referenced tables in the catalog. Remove
-- both 021/022 layers so repeated empty rebuilds retain the fresh comments too.
drop function if exists public.api_create_normal_purchase(uuid,uuid,uuid,text,boolean);
drop function if exists public.api_create_normal_purchase_8d(uuid,uuid,uuid,text,boolean);
drop table if exists public.robbery_cycles cascade;
drop function if exists public.check_purchase_acquisition() cascade;

drop function if exists public.commit_pokemon_identity(jsonb);
drop table if exists public.pokemon_entity_flags cascade;
drop table if exists public.pokemon_observations cascade;
drop table if exists public.pokemon_identity_revisions cascade;
drop table if exists public.pokemon_entities cascade;
drop function if exists public.check_pokemon_entity_flag();

drop table if exists public.penalties cascade;
drop table if exists public.trial_case_revisions cascade;
drop table if exists public.trial_case_counters cascade;
drop table if exists public.trial_votes cascade;
drop table if exists public.trial_cases cascade;
drop table if exists public.cup_standings cascade;
drop table if exists public.cup_certificates cascade;
drop table if exists public.cup_history cascade;
drop table if exists public.cup_side_members cascade;
drop table if exists public.cup_rounds cascade;
drop table if exists public.cup_matches cascade;
drop table if exists public.cup_participants cascade;
drop table if exists public.cups cascade;
drop table if exists public.season_archive_snapshots cascade;
drop table if exists public.hall_of_fame_entries cascade;
drop table if exists public.activity_events cascade;
drop table if exists public.team_locks cascade;
alter table if exists public.season_players
  drop constraint if exists fk_season_players_current_save_same_owner;
drop table if exists public.parsed_saves cascade;
drop table if exists public.save_files cascade;
drop table if exists public.coin_transactions cascade;
drop table if exists public.redemptions cascade;
drop table if exists public.purchases cascade;
drop table if exists public.shop_promotions cascade;
drop table if exists public.shop_items cascade;
drop table if exists public.matchday_movements cascade;
drop table if exists public.matchday_snapshots cascade;
drop table if exists public.matches cascade;
drop table if exists public.division_memberships cascade;
drop table if exists public.matchdays cascade;
drop table if exists public.divisions cascade;
drop table if exists public.season_config_versions cascade;
drop table if exists public.pokemon_flags cascade;
drop table if exists public.trainer_flags cascade;
drop table if exists public.season_player_stats cascade;
drop table if exists public.season_players cascade;
drop table if exists public.seasons cascade;
drop table if exists public.trainers cascade;
drop table if exists public.app_settings cascade;

drop function if exists public.current_user_owns_trainer(uuid) cascade;
drop function if exists public.is_current_user_admin() cascade;
drop function if exists public.current_trainer_id() cascade;
drop function if exists public.current_auth_uid() cascade;
drop function if exists public.set_updated_at() cascade;

commit;
