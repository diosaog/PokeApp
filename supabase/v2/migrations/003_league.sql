-- PokeApp Supabase V2 greenfield schema.
-- 003_league: matchdays, matches, division history, snapshots and movements.

begin;

create table public.matchdays (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id) on delete restrict,
  number integer not null,
  status text not null default 'scheduled',
  season_config_version_id uuid not null,
  opened_at timestamptz,
  closed_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint matchdays_number_chk
    check (number > 0),
  constraint matchdays_status_chk
    check (status in ('scheduled', 'open', 'closed', 'cancelled')),
  constraint matchdays_closed_timestamp_chk
    check (status <> 'closed' or closed_at is not null),
  constraint uq_matchdays_season_number
    unique (season_id, number),
  constraint uq_matchdays_id_season
    unique (id, season_id),
  constraint fk_matchdays_config_same_season
    foreign key (season_config_version_id, season_id)
    references public.season_config_versions(id, season_id)
    on delete restrict
);

create trigger matchdays_set_updated_at
before update on public.matchdays
for each row execute function public.set_updated_at();

comment on table public.matchdays is
  'Official matchday/jornada. Closed matchdays keep their config version and snapshot.';

create table public.division_memberships (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id) on delete restrict,
  season_player_id uuid not null,
  division_id uuid not null,
  effective_from_matchday_number integer not null,
  effective_to_matchday_number integer,
  source_matchday_id uuid,
  reason text not null default 'initial',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint division_memberships_from_chk
    check (effective_from_matchday_number > 0),
  constraint division_memberships_to_chk
    check (
      effective_to_matchday_number is null
      or effective_to_matchday_number >= effective_from_matchday_number
    ),
  constraint division_memberships_reason_chk
    check (reason in ('initial', 'promotion', 'relegation', 'admin', 'status_change')),
  constraint uq_division_memberships_player_from
    unique (season_player_id, effective_from_matchday_number),
  constraint fk_division_memberships_player_same_season
    foreign key (season_player_id, season_id)
    references public.season_players(id, season_id)
    on delete restrict,
  constraint fk_division_memberships_division_same_season
    foreign key (division_id, season_id)
    references public.divisions(id, season_id)
    on delete restrict,
  constraint fk_division_memberships_source_matchday_same_season
    foreign key (source_matchday_id, season_id)
    references public.matchdays(id, season_id)
    on delete restrict
);

comment on table public.division_memberships is
  'Historical division membership. Do not overwrite current division in season_players and lose history.';

create table public.matches (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null,
  matchday_id uuid not null,
  division_id uuid not null,
  player_a_id uuid not null,
  player_b_id uuid not null,
  winner_id uuid,
  status text not null default 'scheduled',
  result_code text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint matches_status_chk
    check (status in ('scheduled', 'completed', 'forfeit', 'void')),
  constraint matches_players_different_chk
    check (player_a_id <> player_b_id),
  constraint matches_winner_is_player_chk
    check (winner_id is null or winner_id = player_a_id or winner_id = player_b_id),
  constraint uq_matches_matchday_pair
    unique (matchday_id, division_id, player_a_id, player_b_id),
  constraint fk_matches_matchday_same_season
    foreign key (matchday_id, season_id)
    references public.matchdays(id, season_id)
    on delete restrict,
  constraint fk_matches_division_same_season
    foreign key (division_id, season_id)
    references public.divisions(id, season_id)
    on delete restrict,
  constraint fk_matches_player_a_same_season
    foreign key (player_a_id, season_id)
    references public.season_players(id, season_id)
    on delete restrict,
  constraint fk_matches_player_b_same_season
    foreign key (player_b_id, season_id)
    references public.season_players(id, season_id)
    on delete restrict,
  constraint fk_matches_winner_same_season
    foreign key (winner_id, season_id)
    references public.season_players(id, season_id)
    on delete restrict
);

create trigger matches_set_updated_at
before update on public.matches
for each row execute function public.set_updated_at();

comment on table public.matches is
  'Actual league matches. Only stores data PokeApp uses: players, winner/status and metadata.';

create table public.matchday_snapshots (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null,
  matchday_id uuid not null,
  config_version_id uuid not null,
  revision integer not null default 1,
  snapshot_schema_version integer not null default 1,
  closed_at timestamptz not null,
  snapshot jsonb not null,
  created_by_trainer_id uuid references public.trainers(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint matchday_snapshots_revision_chk
    check (revision > 0),
  constraint matchday_snapshots_schema_version_chk
    check (snapshot_schema_version > 0),
  constraint uq_matchday_snapshots_matchday
    unique (matchday_id),
  constraint fk_matchday_snapshots_matchday_same_season
    foreign key (matchday_id, season_id)
    references public.matchdays(id, season_id)
    on delete restrict,
  constraint fk_matchday_snapshots_config_same_season
    foreign key (config_version_id, season_id)
    references public.season_config_versions(id, season_id)
    on delete restrict
);

create trigger matchday_snapshots_set_updated_at
before update on public.matchday_snapshots
for each row execute function public.set_updated_at();

comment on table public.matchday_snapshots is
  'One official closed snapshot per matchday. Admin recompute should update this row and increment revision explicitly.';

create table public.matchday_movements (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null,
  matchday_id uuid not null,
  season_player_id uuid not null,
  from_division_id uuid,
  to_division_id uuid,
  movement_type text not null,
  reason text not null default '',
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint matchday_movements_type_chk
    check (movement_type in ('promotion', 'relegation', 'stay', 'admin')),
  constraint fk_matchday_movements_matchday_same_season
    foreign key (matchday_id, season_id)
    references public.matchdays(id, season_id)
    on delete restrict,
  constraint fk_matchday_movements_player_same_season
    foreign key (season_player_id, season_id)
    references public.season_players(id, season_id)
    on delete restrict,
  constraint fk_matchday_movements_from_division_same_season
    foreign key (from_division_id, season_id)
    references public.divisions(id, season_id)
    on delete restrict,
  constraint fk_matchday_movements_to_division_same_season
    foreign key (to_division_id, season_id)
    references public.divisions(id, season_id)
    on delete restrict
);

comment on table public.matchday_movements is
  'Official promotions/relegations/stays for queries and Discord/API summaries. Full closed state also remains in matchday_snapshots.';

commit;
