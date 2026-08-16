-- PokeApp Supabase V2 greenfield schema.
-- 006_activity_hall: append-only activity, Hall of Fame and archive snapshots.

begin;

create table public.activity_events (
  id uuid primary key default gen_random_uuid(),
  season_id uuid references public.seasons(id) on delete restrict,
  type text not null,
  actor_trainer_id uuid references public.trainers(id) on delete set null,
  trainer_id uuid references public.trainers(id) on delete set null,
  visibility text not null default 'public',
  dedupe_key text,
  context jsonb not null default '{}'::jsonb,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint activity_events_type_chk
    check (type = upper(type) and type ~ '^[A-Z0-9_]+$'),
  constraint activity_events_visibility_chk
    check (visibility in ('public', 'owner', 'admin', 'server_only'))
);

comment on table public.activity_events is
  'Append-only product facts. Notification views are derived and not stored.';

create table public.hall_of_fame_entries (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id) on delete restrict,
  competition_type text not null,
  champion_trainer_id uuid not null references public.trainers(id) on delete restrict,
  finalist_trainer_id uuid references public.trainers(id) on delete restrict,
  finalized_at timestamptz not null default now(),
  team_snapshot jsonb not null,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint hall_of_fame_entries_competition_type_chk
    check (competition_type in ('league', 'cup', 'tournament', 'doubles_cup')),
  constraint uq_hall_of_fame_season_competition
    unique (season_id, competition_type)
);

comment on table public.hall_of_fame_entries is
  'Immutable winner records. Champion team comes from a frozen snapshot, never from mutable current save.';

create table public.season_archive_snapshots (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null unique references public.seasons(id) on delete restrict,
  snapshot_schema_version integer not null default 1,
  snapshot jsonb not null,
  created_by_trainer_id uuid references public.trainers(id) on delete set null,
  created_at timestamptz not null default now(),
  constraint season_archive_snapshots_schema_version_chk
    check (snapshot_schema_version > 0)
);

comment on table public.season_archive_snapshots is
  'Optional final audit/export document. Relational season data remains authoritative and is not duplicated here.';

commit;
