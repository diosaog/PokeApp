-- PokeApp Supabase V2 greenfield schema.
-- 002_seasons: season participants, stats, config versions and divisions.

begin;

create table public.season_players (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id) on delete restrict,
  trainer_id uuid not null references public.trainers(id) on delete restrict,
  status text not null default 'active',
  seed_order integer,
  joined_at timestamptz not null default now(),
  left_at timestamptz,
  current_save_file_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint season_players_status_chk
    check (status in ('active', 'retired', 'abandoned', 'disqualified')),
  constraint season_players_seed_order_chk
    check (seed_order is null or seed_order > 0),
  constraint season_players_left_after_join_chk
    check (left_at is null or left_at >= joined_at),
  constraint uq_season_players_season_trainer
    unique (season_id, trainer_id),
  constraint uq_season_players_id_season
    unique (id, season_id),
  constraint uq_season_players_id_season_trainer
    unique (id, season_id, trainer_id)
);

create trigger season_players_set_updated_at
before update on public.season_players
for each row execute function public.set_updated_at();

comment on table public.season_players is
  'Trainer participation in a season. Current season status lives here, not on trainers.';
comment on column public.season_players.current_save_file_id is
  'Added as nullable now; the FK to save_files is added in 005_saves after save_files exists.';

create table public.season_player_stats (
  season_player_id uuid primary key,
  season_id uuid not null,
  trainer_id uuid not null,
  badges_count integer not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  constraint season_player_stats_badges_chk
    check (badges_count >= 0),
  constraint fk_season_player_stats_player
    foreign key (season_player_id, season_id, trainer_id)
    references public.season_players(id, season_id, trainer_id)
    on delete restrict
);

create trigger season_player_stats_set_updated_at
before update on public.season_player_stats
for each row execute function public.set_updated_at();

comment on table public.season_player_stats is
  'Season-scoped lightweight trainer stats such as badges. Coins are not stored here; they come from coin_transactions.';

create table public.trainer_flags (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null,
  trainer_id uuid not null,
  season_player_id uuid not null,
  flag_type text not null,
  flag_value boolean not null default true,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint trainer_flags_type_chk
    check (flag_type = lower(flag_type) and flag_type ~ '^[a-z0-9_]+$'),
  constraint uq_trainer_flags_season_trainer_type
    unique (season_id, trainer_id, flag_type),
  constraint fk_trainer_flags_player_same_owner
    foreign key (season_player_id, season_id, trainer_id)
    references public.season_players(id, season_id, trainer_id)
    on delete restrict
);

create trigger trainer_flags_set_updated_at
before update on public.trainer_flags
for each row execute function public.set_updated_at();

comment on table public.trainer_flags is
  'Season-scoped trainer flags such as robbed. Competitive status remains in season_players.status.';

create table public.pokemon_flags (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null,
  trainer_id uuid not null,
  season_player_id uuid not null,
  fingerprint text not null,
  flag_type text not null,
  flag_value boolean not null default true,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint pokemon_flags_fingerprint_chk
    check (length(btrim(fingerprint)) > 0),
  constraint pokemon_flags_type_chk
    check (flag_type = lower(flag_type) and flag_type ~ '^[a-z0-9_]+$'),
  constraint uq_pokemon_flags_season_owner_fingerprint_type
    unique (season_id, trainer_id, fingerprint, flag_type),
  constraint fk_pokemon_flags_player_same_owner
    foreign key (season_player_id, season_id, trainer_id)
    references public.season_players(id, season_id, trainer_id)
    on delete restrict
);

create trigger pokemon_flags_set_updated_at
before update on public.pokemon_flags
for each row execute function public.set_updated_at();

comment on table public.pokemon_flags is
  'Season-scoped Pokemon flags. Fingerprint is the stable Pokemon identity until the parser exposes a stronger id.';

create table public.season_config_versions (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id) on delete restrict,
  version_number integer not null,
  name text not null,
  effective_from_matchday integer not null,
  total_matchdays integer not null,
  division_count integer not null,
  promotion_relegation_count integer not null default 0,
  scoring_json jsonb not null default '{}'::jsonb,
  coin_rewards_json jsonb not null default '{}'::jsonb,
  rules_json jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  locked_at timestamptz,
  created_by_trainer_id uuid references public.trainers(id) on delete set null,
  created_at timestamptz not null default now(),
  constraint season_config_versions_number_chk
    check (version_number > 0),
  constraint season_config_versions_name_chk
    check (length(btrim(name)) > 0),
  constraint season_config_versions_effective_chk
    check (effective_from_matchday > 0),
  constraint season_config_versions_total_matchdays_chk
    check (total_matchdays > 0),
  constraint season_config_versions_division_count_chk
    check (division_count > 0),
  constraint season_config_versions_movement_chk
    check (promotion_relegation_count >= 0),
  constraint uq_season_config_versions_season_number
    unique (season_id, version_number),
  constraint uq_season_config_versions_season_effective
    unique (season_id, effective_from_matchday),
  constraint uq_season_config_versions_id_season
    unique (id, season_id)
);

comment on table public.season_config_versions is
  'Versioned season configuration. Used matchdays point to the exact config version so history is not reinterpreted.';

create table public.divisions (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id) on delete restrict,
  code text not null,
  name text not null,
  tier_order integer not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint divisions_code_chk
    check (code = upper(code) and code ~ '^[A-Z0-9_-]+$'),
  constraint divisions_name_chk
    check (length(btrim(name)) > 0),
  constraint divisions_tier_order_chk
    check (tier_order > 0),
  constraint uq_divisions_season_code
    unique (season_id, code),
  constraint uq_divisions_season_tier
    unique (season_id, tier_order),
  constraint uq_divisions_id_season
    unique (id, season_id)
);

comment on table public.divisions is
  'Season divisions. Supports A/B today and more tiers later without changing identity.';

commit;
