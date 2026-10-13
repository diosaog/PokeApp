-- Private, unverified Launcher inbox. Does NOT bind competitive save/identity heads.
-- Existing save_files/parsed_saves require raw-file and trusted-parser provenance.
begin;

create table public.launcher_observations (
  id uuid primary key,
  season_id uuid not null,
  trainer_id uuid not null,
  payload_digest text not null check (payload_digest ~ '^[a-f0-9]{64}$'),
  body jsonb not null check (jsonb_typeof(body)='object' and octet_length(body::text)<=2097152),
  received_at timestamptz not null default now(),
  foreign key (season_id,trainer_id) references public.season_players(season_id,trainer_id),
  unique(season_id,trainer_id,payload_digest)
);
create index launcher_observations_rate_idx on public.launcher_observations(trainer_id,received_at);
comment on table public.launcher_observations is
  'Private client-observed DTO receipt only. Unverified: never competitive progress, save head, identity or rewards.';
alter table public.launcher_observations enable row level security;
alter table public.launcher_observations force row level security;
revoke all on public.launcher_observations from public,anon,authenticated,service_role;
grant select,insert on public.launcher_observations to service_role;

create function public.api_launcher_observation(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path = '' as $$
declare
  tid uuid=(p_request->>'trainer_id')::uuid;
  sid uuid=(p_request->>'season_id')::uuid;
  oid uuid=(p_request->>'id')::uuid;
  op text=p_request->>'operation';
  receipt public.launcher_observations;
begin
  if op is null or op not in ('receipt','receive') or tid is null or sid is null or oid is null then
    raise sqlstate 'PT422' using message='invalid_request';
  end if;
  perform 1 from public.trainers where id=tid and globally_enabled for share;
  if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
  -- Player lock serializes duplicate/concurrent receipt creation and lifecycle changes.
  perform 1 from public.season_players where season_id=sid and trainer_id=tid for update;
  if not found then raise sqlstate 'PT403' using message='participant_not_found'; end if;
  select * into receipt from public.launcher_observations where id=oid and season_id=sid and trainer_id=tid;
  if found then
    if op='receive' and (receipt.payload_digest is distinct from p_request->>'payload_digest'
        or receipt.body is distinct from p_request->'body') then
      raise sqlstate 'PT409' using message='observation_conflict';
    end if;
  elsif op='receipt' then
    raise sqlstate 'PT404' using message='observation_not_found';
  else
    if not exists(select 1 from public.season_players p join public.seasons s on s.id=p.season_id
      where p.season_id=sid and p.trainer_id=tid and p.status='active' and s.status in ('draft','active')) then
      raise sqlstate 'PT409' using message='observation_scope_closed';
    end if;
    if p_request->>'payload_digest' is null or p_request->>'payload_digest' !~ '^[a-f0-9]{64}$'
      or jsonb_typeof(p_request->'body') is distinct from 'object'
      or p_request->'body'->'schema_version' is distinct from '1'::jsonb
      or p_request->'body'->>'parser_version' is distinct from 'pokeapp-reader/3;pkhex/24.11.11'
      or jsonb_typeof(p_request->'body'->'observation') is distinct from 'object'
      or octet_length((p_request->'body')::text)>2097152 then
      raise sqlstate 'PT422' using message='invalid_observation';
    end if;
    -- Bound authenticated intake; successful replay above never consumes this limit.
    if (select count(*) from public.launcher_observations
        where trainer_id=tid and received_at>now()-interval '1 hour')>=60 then
      raise sqlstate 'PT429' using message='observation_rate_limited';
    end if;
    insert into public.launcher_observations(id,season_id,trainer_id,payload_digest,body)
      values(oid,sid,tid,p_request->>'payload_digest',p_request->'body') returning * into receipt;
  end if;
  return jsonb_build_object('id',receipt.id,'trainer_id',receipt.trainer_id,'season_id',receipt.season_id,
    'payload_digest',receipt.payload_digest,'received_at',receipt.received_at,
    'trust','client_observed','competitive_authority',false);
end $$;
revoke all on function public.api_launcher_observation(jsonb) from public,anon,authenticated;
grant execute on function public.api_launcher_observation(jsonb) to service_role;
commit;
