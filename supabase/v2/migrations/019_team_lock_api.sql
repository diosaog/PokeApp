-- PokeApp V2 backend-only atomic Team Lock mutation. No legacy writes.
begin;

create or replace function public.api_upsert_team_lock(
  p_season_id uuid,
  p_matchday_id uuid,
  p_trainer_id uuid,
  p_season_player_id uuid,
  p_save_file_id uuid,
  p_save_sha256 text,
  p_parsed_save_id uuid,
  p_parsed_payload jsonb,
  p_public_team_snapshot jsonb,
  p_private_team_snapshot jsonb
)
returns setof public.team_locks
language plpgsql
security invoker
set search_path = ''
as $$
declare
  trainer_row public.trainers%rowtype;
  season_row public.seasons%rowtype;
  matchday_row public.matchdays%rowtype;
  player_row public.season_players%rowtype;
  save_row public.save_files%rowtype;
  parsed_row public.parsed_saves%rowtype;
  lock_row public.team_locks%rowtype;
  locked_time timestamptz;
begin
  -- Hold eligibility/source rows stable until the lock and event commit together.
  select * into trainer_row from public.trainers where id = p_trainer_id for share;
  if not found or not trainer_row.globally_enabled then
    raise sqlstate 'PT403' using message = 'trainer_disabled';
  end if;
  select * into season_row from public.seasons where id = p_season_id for share;
  if not found then
    raise sqlstate 'PT404' using message = 'season_not_found';
  end if;
  if season_row.status <> 'active' then
    raise sqlstate 'PT409' using message = 'season_not_active';
  end if;
  select * into matchday_row from public.matchdays
    where id = p_matchday_id and season_id = p_season_id for share;
  if not found then
    raise sqlstate 'PT404' using message = 'matchday_not_found';
  end if;
  if matchday_row.status not in ('scheduled', 'open') or matchday_row.closed_at is not null then
    raise sqlstate 'PT409' using message = 'matchday_not_lockable';
  end if;
  select * into player_row from public.season_players
    where id = p_season_player_id and season_id = p_season_id and trainer_id = p_trainer_id for share;
  if not found then
    raise sqlstate 'PT404' using message = 'participation_not_found';
  end if;
  if player_row.status <> 'active' then
    raise sqlstate 'PT403' using message = 'participant_inactive';
  end if;
  select * into save_row from public.save_files
    where id = p_save_file_id and season_id = p_season_id and trainer_id = p_trainer_id for share;
  if not found then
    raise sqlstate 'PT404' using message = 'save_not_found';
  end if;
  if save_row.deleted_at is not null or save_row.parser_status <> 'parsed'
     or save_row.sha256 is distinct from p_save_sha256 then
    raise sqlstate 'PT409' using message = 'save_not_ready';
  end if;
  select * into parsed_row from public.parsed_saves
    where id = p_parsed_save_id and save_file_id = p_save_file_id
      and parser_version = save_row.parser_version for share;
  if not found then
    raise sqlstate 'PT409' using message = 'parsed_save_not_ready';
  end if;
  if parsed_row.status <> 'parsed' or parsed_row.schema_version <> 1
     or jsonb_typeof(parsed_row.payload) is distinct from 'object'
     or parsed_row.payload is distinct from p_parsed_payload then
    raise sqlstate 'PT409' using message = 'parsed_save_changed';
  end if;
  if jsonb_typeof(parsed_row.payload -> 'party') is distinct from 'array'
     or jsonb_typeof(p_public_team_snapshot) is distinct from 'array'
     or jsonb_typeof(p_private_team_snapshot) is distinct from 'array' then
    raise sqlstate 'PT409' using message = 'invalid_team_snapshot';
  end if;
  if jsonb_array_length(parsed_row.payload -> 'party') <> 6
     or jsonb_array_length(p_public_team_snapshot) <> 6
     or jsonb_array_length(p_private_team_snapshot) <> 6 then
    raise sqlstate 'PT409' using message = 'team_requires_six';
  end if;
  if exists (
    select 1 from jsonb_array_elements(p_public_team_snapshot || p_private_team_snapshot) as mon(value)
    where jsonb_typeof(value) is distinct from 'object'
       or jsonb_typeof(value -> 'species') is distinct from 'string'
       or length(btrim(value ->> 'species')) = 0
  ) then
    raise sqlstate 'PT409' using message = 'invalid_team_snapshot';
  end if;

  -- No authoritative V2 deadline exists yet. Do not persist the legacy sentinel.
  locked_time := clock_timestamp();
  insert into public.team_locks (
    season_id, matchday_id, trainer_id, season_player_id, save_file_id, save_sha256,
    locked_at, deadline_at, is_late, public_team_snapshot, private_team_snapshot
  ) values (
    p_season_id, p_matchday_id, p_trainer_id, p_season_player_id, p_save_file_id, save_row.sha256,
    locked_time, null, false, p_public_team_snapshot, p_private_team_snapshot
  )
  on conflict on constraint uq_team_locks_matchday_trainer do update set
    season_player_id = excluded.season_player_id,
    save_file_id = excluded.save_file_id,
    save_sha256 = excluded.save_sha256,
    locked_at = excluded.locked_at,
    deadline_at = excluded.deadline_at,
    is_late = excluded.is_late,
    public_team_snapshot = excluded.public_team_snapshot,
    private_team_snapshot = excluded.private_team_snapshot
  returning * into lock_row;

  insert into public.activity_events (
    season_id, type, actor_trainer_id, trainer_id, visibility, dedupe_key, context, payload, created_at
  ) values (
    p_season_id, 'TEAM_LOCKED', p_trainer_id, p_trainer_id, 'public',
    'TEAM_LOCKED:' || p_season_id::text || ':' || p_matchday_id::text || ':' || p_trainer_id::text,
    jsonb_build_object('season_id', p_season_id, 'matchday_id', p_matchday_id, 'matchday_number', matchday_row.number),
    jsonb_build_object(
      'lock_id', lock_row.id, 'matchday_number', matchday_row.number,
      'save_id', p_save_file_id, 'save_sha256', save_row.sha256, 'is_late', lock_row.is_late
    ), locked_time
  )
  on conflict (dedupe_key) where dedupe_key is not null and dedupe_key <> '' do nothing;

  return next lock_row;
end;
$$;

revoke all on function public.api_upsert_team_lock(uuid, uuid, uuid, uuid, uuid, text, uuid, jsonb, jsonb, jsonb) from public;
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'anon') then
    revoke all on function public.api_upsert_team_lock(uuid, uuid, uuid, uuid, uuid, text, uuid, jsonb, jsonb, jsonb) from anon;
  end if;
  if exists (select 1 from pg_roles where rolname = 'authenticated') then
    revoke all on function public.api_upsert_team_lock(uuid, uuid, uuid, uuid, uuid, text, uuid, jsonb, jsonb, jsonb) from authenticated;
  end if;
  if exists (select 1 from pg_roles where rolname = 'service_role') then
    grant execute on function public.api_upsert_team_lock(uuid, uuid, uuid, uuid, uuid, text, uuid, jsonb, jsonb, jsonb) to service_role;
  end if;
end;
$$;

comment on function public.api_upsert_team_lock(uuid, uuid, uuid, uuid, uuid, text, uuid, jsonb, jsonb, jsonb) is
  'Backend-only atomic Team Lock replacement and deduplicated TEAM_LOCKED event. Snapshots are projected by the application from the compared parsed payload.';

commit;
