-- 065_personal_saves: a trainer's own latest save, readable outside any season.
--
-- Season saves (005/044–049) stay the competitive record: they need a season
-- participation and feed identities, robberies and standings. A trainer who
-- is not in an active season still has a game: the Launcher syncs it here so
-- «Mi PC» can show it. Server-parsed with the same parser and observation
-- digest check as season saves; no raw bytes are kept; never competitive
-- evidence. One row per trainer (the latest synced version).
begin;

create table public.trainer_personal_saves (
  trainer_id uuid primary key references public.trainers(id),
  sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
  observation_digest text not null check (observation_digest ~ '^[0-9a-f]{64}$'),
  parser_version text not null check (length(parser_version) between 1 and 80),
  game text not null check (length(game) between 1 and 16),
  payload jsonb not null check (jsonb_typeof(payload) = 'object'),
  uploaded_at timestamptz not null default now()
);

alter table public.trainer_personal_saves enable row level security;
alter table public.trainer_personal_saves force row level security;
revoke all on public.trainer_personal_saves from public, anon, authenticated;
grant select, insert, update on public.trainer_personal_saves to service_role;

comment on table public.trainer_personal_saves is
  'Latest synced save of a trainer for Mi PC outside seasons. Server-parsed, no raw bytes, not competitive evidence.';

commit;
