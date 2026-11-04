-- 083: one Discord announcement per explicit «Fijar Equipo» confirmation.
--
-- Owner rule (2026-11-04): every deliberate, successful confirmation (first
-- lock, a different team, or the same team again) is a new announcement; an
-- automatic retry of the same confirmation (same Idempotency-Key) is not.
-- Earlier messages are never edited or deleted.
--
-- 067 kept one outbox row per lock and edited it when the public snapshot
-- changed, so a replacement with the same team announced nothing and a deleted
-- message was never replaced. Each confirmation is now an immutable record
-- (its own public snapshot, trainer, matchday, key and request hash) and queues
-- its own outbox row (own delivery state, message ID, paste and at-most-once
-- POST). Two quick replacements are two records: no intermediate version is lost.
--
-- api_upsert_team_lock is unchanged: the same authorization, eligibility,
-- save/parse checks and lockable-matchday rules apply to every new key.
-- The legacy 10-argument call (an API from before this release) still queues
-- the 067 first-lock row; replacements no longer edit any message.
begin;

do $$ begin
 if md5(replace(pg_get_functiondef('public.discord_announce_activity()'::regprocedure),chr(13),''))
    <> '3be76889d5199303b059c51f2e3dd654'
  or md5(replace(pg_get_functiondef('public.discord_announce_team_lock_change()'::regprocedure),chr(13),''))
    <> 'e405d20a13d9cbb2f2ad90a79d2ee54e'
  or md5(replace(pg_get_functiondef('public.api_upsert_team_lock(uuid,uuid,uuid,uuid,uuid,text,uuid,jsonb,jsonb,jsonb)'::regprocedure),chr(13),''))
    <> 'bd0f5c3428e72b85d9f026801a081d5d' then
   raise exception 'unexpected Team Lock announcement definitions before 083';
 end if;
end $$;

create table public.team_lock_confirmations (
  id uuid primary key default gen_random_uuid(),
  team_lock_id uuid not null references public.team_locks(id) on delete restrict,
  season_id uuid not null references public.seasons(id) on delete restrict,
  matchday_id uuid not null references public.matchdays(id) on delete restrict,
  trainer_id uuid not null references public.trainers(id) on delete restrict,
  season_player_id uuid not null references public.season_players(id) on delete restrict,
  save_file_id uuid not null references public.save_files(id) on delete restrict,
  save_sha256 text not null check (save_sha256 ~ '^[a-f0-9]{64}$'),
  public_team_snapshot jsonb not null check (jsonb_typeof(public_team_snapshot) = 'array'),
  is_replacement boolean not null,
  idempotency_key text not null check (length(idempotency_key) between 1 and 128),
  request_hash text not null check (request_hash ~ '^[a-f0-9]{64}$'),
  confirmed_at timestamptz not null default clock_timestamp(),
  unique (trainer_id, idempotency_key)
);
create index team_lock_confirmations_lock_idx on public.team_lock_confirmations (team_lock_id, confirmed_at);

create trigger team_lock_confirmation_immutable before update or delete on public.team_lock_confirmations
  for each row execute function public.lifecycle_artifact_immutable();

alter table public.team_lock_confirmations enable row level security;
alter table public.team_lock_confirmations force row level security;
revoke all on public.team_lock_confirmations from public, anon, authenticated, service_role;
grant select, insert on public.team_lock_confirmations to service_role;

comment on table public.team_lock_confirmations is
  'Immutable record of each explicit Team Lock confirmation (Idempotency-Key), with the public snapshot it announced. Backend-only.';

-- Same as 067, except that a TEAM_LOCKED fact recorded through the
-- per-confirmation command is announced by its confirmation row instead.
create or replace function public.discord_announce_activity() returns trigger
language plpgsql security definer set search_path = '' as $$
declare v_kind text; v_key text; v_subject jsonb;
begin
  if new.type = 'SEASON_ADMIN_ACTIVATE' then
    v_kind := 'season_started';
    v_key := 'season_started:' || new.season_id::text;
    v_subject := jsonb_build_object('season_id', new.season_id);
  elsif new.type = 'TEAM_LOCKED' then
    if coalesce(current_setting('pokeapp.team_lock_announcements', true), '') = 'per_confirmation' then
      return null;
    end if;
    -- Legacy call: one per first fixation (the activity dedupe key).
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

-- A replaced lock no longer edits the message already sent.
drop trigger discord_announce_team_lock_change on public.team_locks;
drop function public.discord_announce_team_lock_change();

-- One outbox row per confirmation, queued in the confirming transaction.
create function public.discord_announce_team_lock_confirmation() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  insert into public.discord_announcements (event_key, kind, season_id, subject)
    values ('team_lock_confirmation:' || new.id::text, 'team_locked', new.season_id,
      jsonb_build_object('lock_id', new.team_lock_id, 'confirmation_id', new.id))
    on conflict (event_key) do nothing;
  return null;
exception when others then
  -- An announcement problem never undoes the confirmed Team Lock.
  raise warning 'discord announcement not queued for team lock confirmation % (%)', new.id, sqlstate;
  return null;
end $$;

create trigger discord_announce_team_lock_confirmation after insert on public.team_lock_confirmations
  for each row execute function public.discord_announce_team_lock_confirmation();

create function public.api_confirm_team_lock(
  p_season_id uuid,
  p_matchday_id uuid,
  p_trainer_id uuid,
  p_season_player_id uuid,
  p_save_file_id uuid,
  p_save_sha256 text,
  p_parsed_save_id uuid,
  p_parsed_payload jsonb,
  p_public_team_snapshot jsonb,
  p_private_team_snapshot jsonb,
  p_idempotency_key text
)
returns setof public.team_locks
language plpgsql security invoker set search_path = pg_catalog, public as $$
declare
  request_hash text;
  previous public.team_lock_confirmations;
  lock_row public.team_locks;
  existed boolean;
begin
  if p_idempotency_key is null or length(p_idempotency_key) not between 1 and 128
     or p_idempotency_key !~ '^[!-~]+$' then
    raise sqlstate 'PT409' using message = 'invalid_idempotency_key';
  end if;
  request_hash := encode(sha256(convert_to(concat_ws(':', p_season_id, p_matchday_id, p_trainer_id,
    p_season_player_id, p_save_file_id, p_save_sha256, p_parsed_save_id), 'UTF8')), 'hex');
  -- Concurrent deliveries of the same confirmation wait here and then replay.
  perform pg_advisory_xact_lock(hashtextextended('team_lock_confirmation:' || p_trainer_id::text || ':' || p_idempotency_key, 0));
  select * into previous from public.team_lock_confirmations
    where trainer_id = p_trainer_id and idempotency_key = p_idempotency_key;
  if found then
    if previous.request_hash <> request_hash then
      raise sqlstate 'PT409' using message = 'idempotency_conflict';
    end if;
    -- The same confirmation: no second write, record or announcement.
    select * into lock_row from public.team_locks where id = previous.team_lock_id;
    if lock_row.save_file_id is distinct from previous.save_file_id
       or lock_row.save_sha256 is distinct from previous.save_sha256 then
      raise sqlstate 'PT409' using message = 'team_lock_superseded';
    end if;
    return next lock_row;
    return;
  end if;
  existed := exists (select 1 from public.team_locks where matchday_id = p_matchday_id and trainer_id = p_trainer_id);
  perform set_config('pokeapp.team_lock_announcements', 'per_confirmation', true);
  select * into lock_row from public.api_upsert_team_lock(p_season_id, p_matchday_id, p_trainer_id,
    p_season_player_id, p_save_file_id, p_save_sha256, p_parsed_save_id, p_parsed_payload,
    p_public_team_snapshot, p_private_team_snapshot);
  perform set_config('pokeapp.team_lock_announcements', '', true);
  insert into public.team_lock_confirmations (team_lock_id, season_id, matchday_id, trainer_id,
    season_player_id, save_file_id, save_sha256, public_team_snapshot, is_replacement,
    idempotency_key, request_hash)
  values (lock_row.id, lock_row.season_id, lock_row.matchday_id, lock_row.trainer_id,
    lock_row.season_player_id, lock_row.save_file_id, lock_row.save_sha256,
    lock_row.public_team_snapshot, existed, p_idempotency_key, request_hash);
  return next lock_row;
end $$;

revoke all on function public.api_confirm_team_lock(uuid,uuid,uuid,uuid,uuid,text,uuid,jsonb,jsonb,jsonb,text)
  from public, anon, authenticated;
grant execute on function public.api_confirm_team_lock(uuid,uuid,uuid,uuid,uuid,text,uuid,jsonb,jsonb,jsonb,text)
  to service_role;
revoke all on function public.discord_announce_team_lock_confirmation()
  from public, anon, authenticated, service_role, pokeapp_item_verifier;

comment on function public.api_confirm_team_lock(uuid,uuid,uuid,uuid,uuid,text,uuid,jsonb,jsonb,jsonb,text) is
  'Backend-only «Fijar Equipo»: api_upsert_team_lock plus one immutable confirmation and announcement per Idempotency-Key.';

notify pgrst, 'reload schema';
commit;
