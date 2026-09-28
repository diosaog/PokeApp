-- Phase 8L Advisor completion: 031 duplicated an existing identity constraint.
-- Cup and historical foreign keys already use uq_season_players_id_season_trainer.
-- Keep that authoritative unique key; RESTRICT prevents dropping dependencies.
begin;
alter table public.season_players drop constraint cup_player_identity;
commit;
