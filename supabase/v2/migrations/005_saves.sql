-- PokeApp Supabase V2 greenfield schema.
-- 005_saves: raw save metadata, parsed save cache, current save and team locks.

begin;

create table public.save_files (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id) on delete restrict,
  trainer_id uuid not null references public.trainers(id) on delete restrict,
  storage_bucket text not null default 'raw-saves',
  storage_key text not null unique,
  original_filename text not null,
  sha256 text not null,
  parser_status text not null default 'pending',
  parser_version text not null default '',
  uploaded_at timestamptz not null default now(),
  deleted_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  constraint save_files_storage_bucket_chk
    check (length(btrim(storage_bucket)) > 0),
  constraint save_files_storage_key_chk
    check (length(btrim(storage_key)) > 0),
  constraint save_files_original_filename_chk
    check (length(btrim(original_filename)) > 0),
  constraint save_files_sha256_chk
    check (sha256 ~ '^[a-f0-9]{64}$'),
  constraint save_files_parser_status_chk
    check (parser_status in ('pending', 'parsed', 'failed', 'stale')),
  constraint uq_save_files_id_season_trainer
    unique (id, season_id, trainer_id),
  constraint uq_save_files_trainer_season_sha
    unique (trainer_id, season_id, sha256)
);

comment on table public.save_files is
  'Raw save metadata only. Bytes live in a private storage bucket and paths must not be exposed publicly.';

create table public.parsed_saves (
  id uuid primary key default gen_random_uuid(),
  save_file_id uuid not null references public.save_files(id) on delete restrict,
  parser_version text not null,
  schema_version integer not null default 1,
  parsed_at timestamptz not null default now(),
  status text not null default 'parsed',
  payload jsonb not null,
  metadata jsonb not null default '{}'::jsonb,
  constraint parsed_saves_parser_version_chk
    check (length(btrim(parser_version)) > 0),
  constraint parsed_saves_schema_version_chk
    check (schema_version > 0),
  constraint parsed_saves_status_chk
    check (status in ('parsed', 'failed')),
  constraint uq_parsed_saves_file_parser
    unique (save_file_id, parser_version)
);

comment on table public.parsed_saves is
  'Parser payload/cache. Reparse with a new parser_version without mutating the raw save.';

alter table public.season_players
  add constraint fk_season_players_current_save_same_owner
  foreign key (current_save_file_id, season_id, trainer_id)
  references public.save_files(id, season_id, trainer_id)
  on delete restrict;

comment on column public.season_players.current_save_file_id is
  'Season-scoped current save. Replaces settings.current_save:* in V2.';

create table public.team_locks (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null,
  matchday_id uuid not null,
  trainer_id uuid not null,
  season_player_id uuid not null,
  save_file_id uuid not null,
  save_sha256 text not null,
  locked_at timestamptz not null default now(),
  deadline_at timestamptz,
  is_late boolean not null default false,
  public_team_snapshot jsonb not null,
  private_team_snapshot jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint team_locks_save_sha256_chk
    check (save_sha256 ~ '^[a-f0-9]{64}$'),
  constraint team_locks_deadline_chk
    check (deadline_at is null or locked_at <= deadline_at or is_late = true),
  constraint uq_team_locks_matchday_trainer
    unique (matchday_id, trainer_id),
  constraint fk_team_locks_matchday_same_season
    foreign key (matchday_id, season_id)
    references public.matchdays(id, season_id)
    on delete restrict,
  constraint fk_team_locks_player_same_owner
    foreign key (season_player_id, season_id, trainer_id)
    references public.season_players(id, season_id, trainer_id)
    on delete restrict,
  constraint fk_team_locks_save_same_owner
    foreign key (save_file_id, season_id, trainer_id)
    references public.save_files(id, season_id, trainer_id)
    on delete restrict
);

create trigger team_locks_set_updated_at
before update on public.team_locks
for each row execute function public.set_updated_at();

comment on table public.team_locks is
  'Historical locked teams. Public snapshot is used for previews; private snapshot is owner/admin/server-only.';

commit;
