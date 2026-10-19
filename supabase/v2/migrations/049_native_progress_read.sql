-- Phase21: native facts are separate from the approved reward/readiness contract.
-- No current saves, rewards, identities or history are backfilled by this migration.
begin;

create function public.observed_native_progress(saved public.save_files,parsed public.parsed_saves,tid uuid)
returns jsonb language plpgsql immutable security invoker set search_path=pg_catalog,public as $$
declare n jsonb=parsed.payload->'native_progress'; game text=parsed.payload->>'game'; k text;
begin
  if not public.observed_save_source_valid(saved,parsed,tid)
    or saved.parser_version<>'pokeapp-reader/3;pkhex/24.11.11'
    or jsonb_typeof(saved.metadata->'trusted_registration') is distinct from 'object'
    or saved.metadata->'save_identity'->>'game' is distinct from game
    or saved.metadata->'save_identity'->'trainer' is distinct from parsed.payload->'trainer'
    or parsed.payload->'observed_progress'->>'game' is distinct from game
    or parsed.payload->'observed_progress'->'generation' is distinct from parsed.payload->'generation'
    or parsed.payload->'identity_policy_version' is distinct from '2'::jsonb
    or jsonb_typeof(n) is distinct from 'object' or n->'schema_version' is distinct from '1'::jsonb
    or n->'league_access' is distinct from 'null'::jsonb then return null; end if;
  if exists(select 1 from jsonb_object_keys(n) key where key not in (
      'schema_version','model','badge_flags','league_access','league_visited','league_fly_unlocked',
      'hall_of_fame_entered','champion_defeated','island_stamp_flags','island_challenge_completed')) then
    return null; end if;
  if game in ('X','Y','OR','AS') then
    if parsed.payload->'generation' is distinct from '6'::jsonb or n->>'model' is distinct from 'gym_badges'
      or jsonb_typeof(n->'badge_flags') is distinct from 'array' then return null; end if;
    if jsonb_array_length(n->'badge_flags')<>8 or exists(select 1 from jsonb_array_elements(n->'badge_flags') f where jsonb_typeof(f)<>'boolean')
      or n->'island_stamp_flags' is distinct from 'null'::jsonb or n->'island_challenge_completed' is distinct from 'null'::jsonb then return null; end if;
  elsif game in ('SN','MN','US','UM') then
    if parsed.payload->'generation' is distinct from '7'::jsonb or n->>'model' is distinct from 'island_challenge'
      or jsonb_typeof(n->'island_stamp_flags') is distinct from 'array' then return null; end if;
    if jsonb_array_length(n->'island_stamp_flags')<>4 or exists(select 1 from jsonb_array_elements(n->'island_stamp_flags') f where jsonb_typeof(f)<>'boolean')
      or n->'badge_flags' is distinct from 'null'::jsonb or n->'league_visited' is distinct from 'null'::jsonb
      or n->'league_fly_unlocked' is distinct from 'null'::jsonb or n->'hall_of_fame_entered' is distinct from 'null'::jsonb then return null; end if;
  else return null; end if;
  foreach k in array array['league_access','league_visited','league_fly_unlocked','hall_of_fame_entered','champion_defeated','island_challenge_completed'] loop
    if not(n ? k) or jsonb_typeof(n->k) not in ('null','boolean') then return null; end if;
  end loop;
  return n;
end $$;
revoke all on function public.observed_native_progress(public.save_files,public.parsed_saves,uuid) from public,anon,authenticated;
grant execute on function public.observed_native_progress(public.save_files,public.parsed_saves,uuid) to service_role;

create or replace function public.api_register_save(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare
  sid uuid=(p_request->>'season_id')::uuid;
  tid uuid=(p_request->>'trainer_id')::uuid;
  operation text=p_request->>'operation';
  p public.season_players;
  saved public.save_files;
  head public.pokemon_identity_revisions;
  identity jsonb;
  registered jsonb;
  payload jsonb=p_request->'payload';
  plan jsonb=p_request->'identity_plan';
  saved_id uuid=(p_request->>'save_id')::uuid;
  parsed_id uuid=(p_request->>'parsed_id')::uuid;
  parsed public.parsed_saves;
begin
  if operation not in ('context','receipt','register') or operation is null then
    raise sqlstate 'PT422' using message='save_invalid_operation'; end if;
  if operation='register' then
    -- Cross-owner identity claims serialize before either player lock.
    perform pg_advisory_xact_lock(hashtextextended(sid::text||(p_request->'save_identity')::text,0));
    perform 1 from public.seasons where id=sid for share;
    select * into p from public.season_players where season_id=sid and trainer_id=tid for update;
  else
    select * into p from public.season_players where season_id=sid and trainer_id=tid;
  end if;
  if p.id is null or not exists(select 1 from public.trainers where id=tid and globally_enabled) then
    raise sqlstate 'PT403' using message='save_owner_required'; end if;
  if operation in ('receipt','register') then
    select * into saved from public.save_files where season_id=sid and trainer_id=tid and sha256=p_request->>'sha256';
    if saved.id is not null then
      registered=saved.metadata->'trusted_registration';
      if saved.deleted_at is not null or saved.parser_status<>'parsed' or registered is null
        or not exists(select 1 from public.parsed_saves where save_file_id=saved.id
          and parser_version=saved.parser_version and status='parsed' and schema_version=1) then
        raise sqlstate 'PT409' using message='save_existing_unproven'; end if;
      if operation='register' and registered->>'observation_digest' is distinct from p_request->>'observation_digest' then
        raise sqlstate 'PT409' using message='save_parse_changed'; end if;
      return registered||jsonb_build_object('is_current',coalesce(p.current_save_file_id=saved.id,false));
    elsif operation='receipt' then
      raise sqlstate 'PT404' using message='save_not_registered';
    end if;
  end if;
  if p.status<>'active' or not exists(select 1 from public.seasons where id=sid and status='active') then
    raise sqlstate 'PT409' using message='save_context_not_active'; end if;
  select * into saved from public.save_files where id=p.current_save_file_id and season_id=sid and trainer_id=tid;
  identity=saved.metadata->'save_identity';
  select * into head from public.pokemon_identity_revisions where season_id=sid and trainer_id=tid
    order by revision_number desc limit 1;
  if operation='context' then
    return jsonb_build_object('current_save_id',p.current_save_file_id,'save_identity',identity,
      'head',case when head.id is null then null else to_jsonb(head) end,
      'unresolved_evidence',coalesce((select jsonb_agg(distinct o.evidence) from public.pokemon_observations o where o.season_id=sid and o.trainer_id=tid and o.outcome='AMBIGUOUS' and o.evidence->'schema_version'='2'::jsonb),'[]'::jsonb),
      'entities',coalesce((select jsonb_agg(to_jsonb(e) order by id) from public.pokemon_entities e
        where season_id=sid and owner_trainer_id=tid),'[]'::jsonb));
  end if;
  if not (p_request ? 'expected_save_id') or p.current_save_file_id is distinct from (p_request->>'expected_save_id')::uuid then
    raise sqlstate 'PT409' using message='save_current_changed'; end if;
  if p.current_save_file_id is not null and (identity is null or identity is distinct from p_request->'save_identity') then
    raise sqlstate 'PT409' using message='save_identity_changed'; end if;
  if exists(select 1 from public.save_files where season_id=sid and trainer_id<>tid
      and metadata->'save_identity'=p_request->'save_identity') then
    raise sqlstate 'PT409' using message='save_identity_other_owner'; end if;
  if saved_id is null or parsed_id is null
    or p_request->>'sha256' is null or p_request->>'observation_digest' is null
    or jsonb_typeof(payload) is distinct from 'object'
    or (p_request->>'sha256') !~ '^[0-9a-f]{64}$'
    or (p_request->>'observation_digest') !~ '^[0-9a-f]{64}$'
    or p_request->>'parser_version' is distinct from 'pokeapp-reader/3;pkhex/24.11.11'
    or p_request->>'storage_key' is distinct from 'trusted/'||tid::text||'/'||sid::text||'/'||(p_request->>'sha256')||'.sav'
    or payload->>'save_record_id' is distinct from saved_id::text
    or payload->>'trainer_id' is distinct from tid::text
    or payload->>'source_hash' is distinct from p_request->>'sha256'
    or jsonb_typeof(payload->'party') is distinct from 'array'
    or jsonb_array_length(payload->'party')<>6
    or jsonb_typeof(payload->'boxes') is distinct from 'array'
    or jsonb_typeof(p_request->'save_identity'->'trainer') is distinct from 'object'
    or payload->'trainer' is distinct from p_request->'save_identity'->'trainer'
    or payload->>'game' is distinct from p_request->'save_identity'->>'game'
    or payload->>'game' not in ('R','S','RS','E','FR','LG','FRLG','D','P','DP','Pt','HG','SS','HGSS','B','W','BW','B2','W2','B2W2','X','Y','OR','AS','SN','MN','US','UM') then
    raise sqlstate 'PT422' using message='save_invalid_registration'; end if;
  if payload->>'generation' in ('6','7') and payload->'identity_policy_version'='2'::jsonb then
    if plan->'identity_schema_version' is distinct from '2'::jsonb or plan->'reconciliation_version' is distinct from '2'::jsonb
      or plan->>'season_id' is distinct from sid::text or plan->>'trainer_id' is distinct from tid::text
      or plan->>'save_file_id' is distinct from saved_id::text or plan->>'parsed_save_id' is distinct from parsed_id::text
      or plan->'parsed_payload' is distinct from payload
      or payload->'native_progress'->'schema_version' is distinct from '1'::jsonb
      or payload->'observed_progress'->'progress' is distinct from 'null'::jsonb then
      raise sqlstate 'PT422' using message='native_unapproved_competitive_evidence'; end if;
  elsif payload->>'generation'='6' then
    if payload->>'game' not in ('X','Y','OR','AS') or plan is distinct from 'null'::jsonb
      or payload->'observed_progress'->'progress' is distinct from 'null'::jsonb then
      raise sqlstate 'PT422' using message='xy_unapproved_competitive_evidence'; end if;
  elsif payload->>'generation'='7' then
    if payload->>'game' not in ('SN','MN','US','UM') or plan is distinct from 'null'::jsonb
      or payload->'observed_progress'->'progress' is distinct from 'null'::jsonb
      or jsonb_array_length(payload->'boxes')<>32 then
      raise sqlstate 'PT422' using message='sm_unapproved_competitive_evidence'; end if;
  elsif payload->>'game' in ('SN','MN','US','UM') then
    raise sqlstate 'PT422' using message='sm_invalid_generation';
  elsif jsonb_typeof(plan) is distinct from 'object'
      or plan->>'season_id' is distinct from sid::text or plan->>'trainer_id' is distinct from tid::text
      or plan->>'save_file_id' is distinct from saved_id::text or plan->>'parsed_save_id' is distinct from parsed_id::text
      or plan->'parsed_payload' is distinct from payload then
    raise sqlstate 'PT422' using message='save_identity_plan_required';
  end if;
  registered=jsonb_build_object('status','registered','save_id',saved_id,'season_id',sid,'trainer_id',tid,
    'sha256',p_request->>'sha256','parser_version',p_request->>'parser_version',
    'observation_digest',p_request->>'observation_digest');
  insert into public.save_files(id,season_id,trainer_id,storage_bucket,storage_key,original_filename,
    sha256,parser_status,parser_version,uploaded_at,metadata)
  values(saved_id,sid,tid,'raw-saves',p_request->>'storage_key','save.sav',p_request->>'sha256',
    'parsed',p_request->>'parser_version',clock_timestamp(),
    jsonb_build_object('trusted_registration',registered,'save_identity',p_request->'save_identity'));
  insert into public.parsed_saves(id,save_file_id,parser_version,schema_version,status,payload)
    values(parsed_id,saved_id,p_request->>'parser_version',1,'parsed',payload);
  if payload->'identity_policy_version'='2'::jsonb then
    select * into saved from public.save_files where id=saved_id;
    select * into parsed from public.parsed_saves where id=parsed_id;
    if public.observed_native_progress(saved,parsed,tid) is null then
      raise sqlstate 'PT422' using message='native_invalid_progress_source'; end if;
  end if;
  if jsonb_typeof(plan)='object' then perform public.commit_pokemon_identity(plan); end if;
  update public.season_players set current_save_file_id=saved_id where id=p.id;
  -- Existing pointer hook settles only certified supported observations, once.
  return registered||jsonb_build_object('is_current',true);
end $$;
revoke all on function public.api_register_save(jsonb) from public,anon,authenticated;
grant execute on function public.api_register_save(jsonb) to service_role;
comment on function public.api_register_save(jsonb) is
 'Server native-parse registration only. Atomic save/identity/current pointer and existing reward hooks. Client observations never enter this boundary.';

create or replace function public.observed_progress_read(p_season_id uuid, p_trainer_id uuid default null)
returns jsonb language plpgsql stable security invoker
set search_path=pg_catalog,public as $$
declare result jsonb;
begin
  if not exists(select 1 from public.seasons where id=p_season_id and status<>'discarded') then
    return null;
  end if;
  if (select count(*) from public.season_players where season_id=p_season_id)>500 then
    raise exception 'Progress read capacity exceeded';
  end if;
  -- One statement snapshot binds current pointer, latest accepted identity revision,
  -- owned source and parsed payload. A stale pointer is not current evidence.
  select coalesce(jsonb_agg(jsonb_build_object(
    'id',p.id,'trainer_id',p.trainer_id,
    'game',case when (proof.progress is not null or proof.native_progress is not null) then parsed.payload#>>'{observed_progress,game}' end,
    'observed_at',case when (proof.progress is not null or proof.native_progress is not null) then head.created_at end,
    'progress',proof.progress,'native_progress',proof.native_progress) order by p.id),'[]'::jsonb) into result
  from public.season_players p
  left join lateral (
    select i.* from public.pokemon_identity_revisions i
    where i.season_id=p.season_id and i.trainer_id=p.trainer_id
    order by i.revision_number desc limit 1
  ) head on head.save_file_id=p.current_save_file_id
  left join public.save_files saved on saved.id=head.save_file_id
    and saved.season_id=p.season_id and saved.trainer_id=p.trainer_id
  left join public.parsed_saves parsed on parsed.id=head.parsed_save_id
    and parsed.save_file_id=saved.id
  cross join lateral (select public.observed_save_progress(saved,parsed,p.trainer_id) as progress, public.observed_native_progress(saved,parsed,p.trainer_id) as native_progress) proof
  where p.season_id=p_season_id and (p_trainer_id is null or p.trainer_id=p_trainer_id);
  return result;
end $$;
revoke all on function public.observed_progress_read(uuid,uuid) from public,anon,authenticated;
grant execute on function public.observed_progress_read(uuid,uuid) to service_role;


commit;
