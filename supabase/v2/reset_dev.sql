-- DESTRUCTIVE DEVELOPMENT RESET FOR POKEAPP SUPABASE V2 ONLY.
-- Do not run this against production or the current V1 database.
-- This file drops V2 public tables, functions and seed data so migrations can be
-- reapplied from an empty development/staging database.

begin;

drop table if exists public.penalties cascade;
drop table if exists public.trial_votes cascade;
drop table if exists public.trial_cases cascade;
drop table if exists public.cup_standings cascade;
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

drop function if exists public.set_updated_at() cascade;

commit;
