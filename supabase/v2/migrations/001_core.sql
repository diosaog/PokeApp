-- PokeApp Supabase V2 greenfield schema.
-- 001_core: extensions, shared helpers, global trainers and seasons.
-- Intended for an empty Supabase/Postgres database, not for patching V1.

begin;

create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table public.app_settings (
  key text primary key,
  value jsonb not null default '{}'::jsonb,
  description text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint app_settings_key_format_chk
    check (key ~ '^[a-z0-9][a-z0-9_.:-]*$')
);

create trigger app_settings_set_updated_at
before update on public.app_settings
for each row execute function public.set_updated_at();

comment on table public.app_settings is
  'Small technical/global settings only. Never store league state, snapshots, Hall, trainer status or saves here.';

create table public.trainers (
  id uuid primary key default gen_random_uuid(),
  display_name text not null,
  slug text not null unique,
  auth_user_id uuid unique,
  globally_enabled boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint trainers_display_name_non_empty_chk
    check (length(btrim(display_name)) > 0),
  constraint trainers_slug_format_chk
    check (slug = lower(slug) and slug ~ '^[a-z0-9][a-z0-9_-]*$')
);

create trigger trainers_set_updated_at
before update on public.trainers
for each row execute function public.set_updated_at();

comment on table public.trainers is
  'Global trainer identity. Season status, robbed flags, points, coins and divisions live elsewhere.';
comment on column public.trainers.auth_user_id is
  'Prepared for Supabase Auth/RLS. No FK to auth.users in V2 SQL so local Postgres builds remain reproducible.';

create table public.seasons (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  status text not null default 'draft',
  created_by_trainer_id uuid references public.trainers(id) on delete set null,
  started_at timestamptz,
  finished_at timestamptz,
  archived_at timestamptz,
  discarded_at timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint seasons_name_non_empty_chk
    check (length(btrim(name)) > 0),
  constraint seasons_status_chk
    check (status in ('draft', 'active', 'finished', 'archived', 'discarded')),
  constraint seasons_lifecycle_timestamp_chk
    check (
      (status <> 'active' or started_at is not null)
      and (status <> 'finished' or finished_at is not null)
      and (status <> 'archived' or archived_at is not null)
      and (status <> 'discarded' or discarded_at is not null)
    )
);

create trigger seasons_set_updated_at
before update on public.seasons
for each row execute function public.set_updated_at();

comment on table public.seasons is
  'Real live/historical season. Archiving sets status=archived; relational data remains in place.';

commit;
