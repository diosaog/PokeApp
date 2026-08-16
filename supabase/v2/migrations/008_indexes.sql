-- PokeApp Supabase V2 greenfield schema.
-- 008_indexes: query indexes and uniqueness that depends on partial predicates.

begin;

create unique index uq_seasons_one_active
  on public.seasons ((status))
  where status = 'active';

create index idx_trainers_slug_enabled
  on public.trainers (slug)
  where globally_enabled = true;

create index idx_season_players_season_status
  on public.season_players (season_id, status, seed_order);

create index idx_season_config_versions_season_effective_desc
  on public.season_config_versions (season_id, effective_from_matchday desc);

create index idx_division_memberships_player_range
  on public.division_memberships (season_player_id, effective_from_matchday_number, effective_to_matchday_number);

create index idx_trainer_flags_season_type
  on public.trainer_flags (season_id, flag_type, trainer_id);

create index idx_pokemon_flags_owner_type
  on public.pokemon_flags (season_id, trainer_id, flag_type);

create index idx_matchdays_season_status
  on public.matchdays (season_id, status, number);

create index idx_matches_matchday_division
  on public.matches (matchday_id, division_id, status);

create index idx_matchday_movements_matchday
  on public.matchday_movements (matchday_id, movement_type);

create index idx_shop_items_category_enabled
  on public.shop_items (category, enabled, code);

create index idx_shop_promotions_season_matchday_status
  on public.shop_promotions (season_id, matchday_id, status, activates_at);

create unique index uq_shop_promotions_dedupe_key
  on public.shop_promotions (dedupe_key)
  where dedupe_key is not null and dedupe_key <> '';

create index idx_purchases_trainer_recent
  on public.purchases (trainer_id, purchased_at desc);

create index idx_purchases_season_item_status
  on public.purchases (season_id, shop_item_id, status);

create index idx_purchases_promotion
  on public.purchases (promotion_id)
  where promotion_id is not null;

create index idx_redemptions_purchase
  on public.redemptions (purchase_id, redeemed_at desc);

create index idx_coin_transactions_trainer
  on public.coin_transactions (season_id, trainer_id, created_at desc);

create index idx_save_files_trainer_recent
  on public.save_files (season_id, trainer_id, uploaded_at desc);

create index idx_save_files_sha256
  on public.save_files (sha256);

create index idx_parsed_saves_file_recent
  on public.parsed_saves (save_file_id, parsed_at desc);

create index idx_team_locks_matchday
  on public.team_locks (matchday_id, trainer_id);

create index idx_activity_events_recent
  on public.activity_events (created_at desc);

create index idx_activity_events_season_recent
  on public.activity_events (season_id, created_at desc);

create unique index uq_activity_events_dedupe_key
  on public.activity_events (dedupe_key)
  where dedupe_key is not null and dedupe_key <> '';

create index idx_hall_of_fame_champion
  on public.hall_of_fame_entries (champion_trainer_id, finalized_at desc);

create index idx_cups_season_status
  on public.cups (season_id, status, created_at desc);

create index idx_cup_matches_round
  on public.cup_matches (cup_id, round_number, bracket_position);

create index idx_trial_cases_season_status
  on public.trial_cases (season_id, status, created_at desc);

create index idx_penalties_trainer
  on public.penalties (season_id, trainer_id, created_at desc);

comment on index public.uq_seasons_one_active is
  'PokeApp runs one active league season at a time.';

commit;
