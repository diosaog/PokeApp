-- 067_discord_announcements: the competition's public announcements («Aaron Avisa!»).
--
-- One outbox row per confirmed competitive fact, queued by a trigger in the
-- same transaction that records the fact in activity_events (the append-only
-- record of confirmed facts). The API delivers each row at most once through
-- its server-held Discord webhook; a team lock replaced while its matchday is
-- still open only edits the message already sent. Nothing earlier than this
-- migration is queued, so enabling the integration never replays history.
-- Saves, syncs, reads, purchases and provisional results queue nothing.
-- A failure here never blocks the competition: the fact commits regardless.
begin;

create table public.discord_announcements (
  id uuid primary key default gen_random_uuid(),
  event_key text not null unique check (length(event_key) between 1 and 200),
  kind text not null check (kind in ('season_started', 'team_locked', 'matchday_closed',
    'matchday_corrected', 'season_finished', 'cup_round_closed', 'cup_finished',
    'robbery_completed', 'trial_resolved', 'participant_status')),
  season_id uuid references public.seasons(id) on delete restrict,
  subject jsonb not null check (jsonb_typeof(subject) = 'object'),
  status text not null default 'pending' check (status in
    ('pending', 'sending', 'sent', 'failed', 'uncertain', 'expired', 'skipped')),
  revision integer not null default 1 check (revision > 0),
  delivered_revision integer not null default 0
    check (delivered_revision between 0 and revision),
  attempts integer not null default 0 check (attempts >= 0),
  next_attempt_at timestamptz not null default now(),
  claimed_at timestamptz,
  sent_at timestamptz,
  discord_message_id text check (discord_message_id ~ '^[0-9]{1,25}$'),
  last_error text check (last_error ~ '^[a-z0-9_]{1,64}$'),
  -- A post to send, or a sent message whose team lock was replaced since.
  awaiting_delivery boolean generated always as
    (status = 'pending' or (status = 'sent' and delivered_revision < revision)) stored,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (status <> 'sent' or sent_at is not null)
);

create index discord_announcements_due_idx on public.discord_announcements (next_attempt_at)
  where awaiting_delivery or status = 'sending';

create trigger discord_announcements_set_updated_at
before update on public.discord_announcements
for each row execute function public.set_updated_at();

alter table public.discord_announcements enable row level security;
alter table public.discord_announcements force row level security;
revoke all on public.discord_announcements from public, anon, authenticated, service_role;
grant select, update on public.discord_announcements to service_role;

comment on table public.discord_announcements is
  'Outbox of public competition announcements to Discord. Queued only by triggers on confirmed facts; delivered at most once by the API (an ambiguous delivery is never resent). Backend-only.';

create function public.discord_announce_activity() returns trigger
language plpgsql security definer set search_path = '' as $$
declare v_kind text; v_key text; v_subject jsonb;
begin
  if new.type = 'SEASON_ADMIN_ACTIVATE' then
    v_kind := 'season_started';
    v_key := 'season_started:' || new.season_id::text;
    v_subject := jsonb_build_object('season_id', new.season_id);
  elsif new.type = 'TEAM_LOCKED' then
    -- One per first fixation: a replacement keeps the activity dedupe key.
    v_kind := 'team_locked';
    v_key := 'team_locked:' || (new.payload ->> 'lock_id');
    v_subject := jsonb_build_object('lock_id', new.payload ->> 'lock_id');
  elsif new.type in ('MATCHDAY_ADMIN_CLOSE', 'MATCHDAY_ADMIN_CORRECT') then
    v_kind := case new.type when 'MATCHDAY_ADMIN_CLOSE' then 'matchday_closed' else 'matchday_corrected' end;
    v_key := 'matchday:' || (new.payload ->> 'matchday_id') || ':' || (new.payload ->> 'snapshot_revision');
    v_subject := jsonb_build_object('matchday_id', new.payload ->> 'matchday_id',
      'revision', (new.payload ->> 'snapshot_revision')::integer);
  elsif new.type = 'SEASON_FINISHED' then
    v_kind := 'season_finished';
    v_key := 'season_finished:' || new.season_id::text;
    v_subject := jsonb_build_object('finalization_id', new.payload ->> 'finalization_id');
  elsif new.type = 'CUP_CLOSE' then
    v_kind := 'cup_round_closed';
    v_key := 'cup:' || (new.payload ->> 'cup_id') || ':' || (new.payload ->> 'revision');
    v_subject := jsonb_build_object('cup_id', new.payload ->> 'cup_id',
      'revision', (new.payload ->> 'revision')::bigint);
  elsif new.type = 'CUP_FINALIZE' then
    v_kind := 'cup_finished';
    v_key := 'cup_finished:' || (new.payload ->> 'cup_id');
    v_subject := jsonb_build_object('cup_id', new.payload ->> 'cup_id');
  elsif new.type in ('TRIAL_RESOLVED', 'TRIAL_CORRECTED') then
    -- Only cases PokeApp itself shows to every trainer.
    if not exists (select 1 from public.trial_cases c where c.id = (new.payload ->> 'case_id')::uuid
        and c.status <> 'cancelled'
        and coalesce(lower(c.payload ->> 'is_public'), 'true') not in ('false', '0', 'no')) then
      return null;
    end if;
    v_kind := 'trial_resolved';
    v_key := 'trial:' || (new.payload ->> 'revision_id');
    v_subject := jsonb_build_object('case_id', new.payload ->> 'case_id',
      'revision_id', new.payload ->> 'revision_id');
  elsif new.type = 'PARTICIPANT_STATUS_CHANGED' then
    v_kind := 'participant_status';
    v_key := 'participant:' || (new.payload ->> 'participant_id') || ':' || (new.payload ->> 'new_status');
    v_subject := jsonb_build_object('season_player_id', new.payload ->> 'participant_id',
      'status', new.payload ->> 'new_status',
      'matchday_number', (new.payload ->> 'effective_matchday_number')::integer);
  elsif new.type = 'REDEMPTION_USED' and new.payload ->> 'effect_code' = 'steal' then
    -- The robbery's competitive decision: ownership has changed for good.
    v_kind := 'robbery_completed';
    v_key := 'robbery:' || (new.payload ->> 'redemption_id');
    v_subject := jsonb_build_object('redemption_id', new.payload ->> 'redemption_id');
  else
    return null;
  end if;
  if v_key is null or v_subject is null then
    raise warning 'discord announcement not queued for % %', new.type, new.id;
    return null;
  end if;
  insert into public.discord_announcements (event_key, kind, season_id, subject)
    values (v_key, v_kind, new.season_id, v_subject || jsonb_build_object('activity_event_id', new.id))
    on conflict (event_key) do nothing;
  return null;
exception when others then
  raise warning 'discord announcement not queued for % % (%)', new.type, new.id, sqlstate;
  return null;
end $$;

create trigger discord_announce_activity after insert on public.activity_events
  for each row execute function public.discord_announce_activity();

-- A lock replaced while its matchday is open edits its message, never posts again.
create function public.discord_announce_team_lock_change() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if new.public_team_snapshot is distinct from old.public_team_snapshot then
    update public.discord_announcements
      set revision = revision + 1, next_attempt_at = greatest(next_attempt_at, now())
      where event_key = 'team_locked:' || new.id::text
        and status not in ('failed', 'uncertain', 'expired', 'skipped');
  end if;
  return null;
exception when others then
  raise warning 'discord announcement edit not queued for team lock % (%)', new.id, sqlstate;
  return null;
end $$;

create trigger discord_announce_team_lock_change after update of public_team_snapshot on public.team_locks
  for each row execute function public.discord_announce_team_lock_change();

revoke all on function public.discord_announce_activity() from public, anon, authenticated, service_role, pokeapp_item_verifier;
revoke all on function public.discord_announce_team_lock_change() from public, anon, authenticated, service_role, pokeapp_item_verifier;

commit;
