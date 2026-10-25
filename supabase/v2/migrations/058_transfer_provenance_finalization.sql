-- Phase24A closure. LOCAL ONLY: no public route or production writer capability.
begin;
alter table public.item_use_transfers add column terminal text check(terminal in ('COMMITTED','CANCELLED'));
alter table public.item_use_transfers add column receipt jsonb;
alter table public.item_use_transfer_legs add column released boolean not null default false;
alter table public.item_use_transfer_legs drop constraint item_use_transfer_legs_season_id_trainer_id_key;
create unique index transfer_active_participant on public.item_use_transfer_legs(season_id,trainer_id) where not released;
create table public.transfer_provenance (
 authorization_id uuid primary key references public.item_use_transfers(authorization_id),
 pokemon_entity_id uuid not null references public.pokemon_entities(id),
 season_id uuid not null references public.seasons(id),
 donor_id uuid not null references public.trainers(id),
 recipient_id uuid not null references public.trainers(id),
 evidence jsonb not null, originals jsonb not null, results jsonb not null,
 proofs jsonb not null, original_flags jsonb not null, created_at timestamptz not null default clock_timestamp(),
 check(donor_id<>recipient_id)
);
-- This transient permit is unforgeable by API/worker roles, unlike a custom GUC.
-- Only the finalizer inserts it, inside the SAME transaction as all effects.
create table public.transfer_commit_permits (
 txid bigint primary key, authorization_id uuid not null references public.item_use_transfers(authorization_id)
);
alter table public.transfer_provenance enable row level security;
alter table public.transfer_provenance force row level security;
alter table public.transfer_commit_permits enable row level security;
alter table public.transfer_commit_permits force row level security;
revoke all on public.transfer_provenance,public.transfer_commit_permits from public,anon,authenticated,service_role,pokeapp_item_verifier;

create function public.transfer_identity_proven(p_entity uuid,p_trainer uuid,p_evidence jsonb) returns boolean
language sql security definer set search_path='' as $$
 select exists(select 1 from public.transfer_provenance p join public.pokemon_entities e on e.id=p.pokemon_entity_id
 join public.item_use_transfers x on x.authorization_id=p.authorization_id
 where e.id=p_entity and e.owner_trainer_id=p_trainer and p.recipient_id=p_trainer
 and e.initial_evidence=p.evidence and (p.evidence-'source_trainer_match')=(p_evidence-'source_trainer_match')
 and (x.terminal='COMMITTED' or exists(select 1 from public.transfer_commit_permits c where c.txid=txid_current() and c.authorization_id=p.authorization_id)));
$$;
revoke all on function public.transfer_identity_proven(uuid,uuid,jsonb) from public,anon,authenticated,pokeapp_item_verifier;
grant execute on function public.transfer_identity_proven(uuid,uuid,jsonb) to service_role;
create function public.transfer_foreign_collision(p_season uuid,p_trainer uuid,p_evidence jsonb) returns boolean
language sql security definer set search_path='' as $$
 select exists(select 1 from public.transfer_provenance p join public.pokemon_entities e on e.id=p.pokemon_entity_id
 where e.season_id=p_season and e.owner_trainer_id<>p_trainer
 and (e.initial_evidence->'pid'=p_evidence->'pid' or e.initial_evidence->'encryption_constant'=p_evidence->'encryption_constant'));
$$;
revoke all on function public.transfer_foreign_collision(uuid,uuid,jsonb) from public,anon,authenticated,pokeapp_item_verifier;
grant execute on function public.transfer_foreign_collision(uuid,uuid,jsonb) to service_role;
create or replace function public.commit_pokemon_identity_v038(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare
  season uuid := (p_request->>'season_id')::uuid;
  trainer uuid := (p_request->>'trainer_id')::uuid;
  save_id uuid := (p_request->>'save_file_id')::uuid;
  head public.pokemon_identity_revisions;
  revision public.pokemon_identity_revisions;
  saved public.save_files;
  parsed public.parsed_saves;
  item jsonb;
  v_evidence jsonb;
  raw_pokemon jsonb;
  entity public.pokemon_entities;
  entity_id uuid;
  candidate_ids uuid[];
  submitted_ids uuid[];
  occurrence_count integer;
  collision_count integer;
  poisoned boolean;
  eligible boolean;
  trainer_match boolean;
  expected_outcome text;
begin
  if p_request->>'identity_schema_version'='1' and p_request->>'reconciliation_version'='1' then
    if p_request->'parsed_payload'->>'generation' in ('6','7')
      or p_request->'parsed_payload'->'identity_policy_version'='2'::jsonb then
      raise sqlstate 'PT409' using message='identity_legacy_native_forbidden'; end if;
    return public.commit_pokemon_identity_legacy_v1(p_request);
  end if;
  if p_request->>'identity_schema_version' is distinct from '2'
    or p_request->>'reconciliation_version' is distinct from '2'
    or jsonb_typeof(p_request->'bindings') is distinct from 'array' then
    raise sqlstate 'PT409' using message='identity_invalid_plan'; end if;

  perform 1 from public.season_players where season_id=season and trainer_id=trainer for update;
  if not found then raise sqlstate 'PT404' using message='identity_player_not_found'; end if;
  select * into saved from public.save_files where id=save_id and season_id=season and trainer_id=trainer for share;
  if not found or saved.deleted_at is not null or saved.parser_status<>'parsed'
    or saved.parser_version is distinct from 'pokeapp-reader/3;pkhex/24.11.11'
    or jsonb_typeof(saved.metadata->'trusted_registration') is distinct from 'object' then
    raise sqlstate 'PT409' using message='identity_save_not_ready'; end if;
  select * into parsed from public.parsed_saves where id=(p_request->>'parsed_save_id')::uuid
    and save_file_id=save_id for share;
  if not found or parsed.status<>'parsed' or parsed.payload is distinct from p_request->'parsed_payload'
    or parsed.parser_version is distinct from saved.parser_version
    or parsed.payload->'identity_policy_version' is distinct from '2'::jsonb
    or parsed.payload->'native_progress'->'schema_version' is distinct from '1'::jsonb
    or saved.metadata->'save_identity'->'trainer' is distinct from parsed.payload->'trainer'
    or saved.metadata->'save_identity'->>'game' is distinct from parsed.payload->>'game'
    or not coalesce(((parsed.payload->'generation'='6'::jsonb and parsed.payload->>'game' in ('X','Y','OR','AS'))
      or (parsed.payload->'generation'='7'::jsonb and parsed.payload->>'game' in ('SN','MN','US','UM'))),false) then
    raise sqlstate 'PT409' using message='identity_parsed_source_changed'; end if;
  if jsonb_typeof(parsed.payload->'party') is distinct from 'array'
    or jsonb_typeof(parsed.payload->'boxes') is distinct from 'array' then
    raise sqlstate 'PT409' using message='identity_incomplete_payload'; end if;
  if jsonb_array_length(parsed.payload->'party')<>6
    or jsonb_array_length(parsed.payload->'boxes')<>(case when parsed.payload->'generation'='6'::jsonb then 31 else 32 end)
    or exists(select 1 from jsonb_array_elements(parsed.payload->'party') with ordinality x(s,n)
      where s->'slot_number' is distinct from to_jsonb(n) or not(s ? 'pokemon')
        or jsonb_typeof(s->'pokemon') not in ('object','null'))
    or exists(select 1 from jsonb_array_elements(parsed.payload->'boxes') with ordinality x(b,n)
      where b->'box_number' is distinct from to_jsonb(n) or jsonb_typeof(b->'slots') is distinct from 'array') then
    raise sqlstate 'PT409' using message='identity_incomplete_payload'; end if;
  if exists(select 1 from jsonb_array_elements(parsed.payload->'boxes') b
      where jsonb_array_length(b->'slots')<>30)
    or exists(select 1 from jsonb_array_elements(parsed.payload->'boxes') b,
      lateral jsonb_array_elements(b->'slots') with ordinality x(s,n)
      where s->'slot_number' is distinct from to_jsonb(n) or not(s ? 'pokemon')
        or jsonb_typeof(s->'pokemon') not in ('object','null')) then
    raise sqlstate 'PT409' using message='identity_incomplete_payload'; end if;
  select count(*) into occurrence_count from (
    select s->'pokemon' p from jsonb_array_elements(parsed.payload->'party') s
    union all select s->'pokemon' from jsonb_array_elements(parsed.payload->'boxes') b,
      lateral jsonb_array_elements(b->'slots') s
  ) occurrences where p is not null and p<>'null'::jsonb;
  if occurrence_count<>jsonb_array_length(p_request->'bindings') then
    raise sqlstate 'PT409' using message='identity_incomplete_plan'; end if;

  select * into revision from public.pokemon_identity_revisions where save_file_id=save_id;
  if found then
    if revision.input_signature is distinct from p_request->>'input_signature'
      or revision.identity_schema_version<>2 or revision.reconciliation_version<>2 then
      raise sqlstate 'PT409' using message='identity_reparse_requires_review'; end if;
  else
    select * into head from public.pokemon_identity_revisions where season_id=season and trainer_id=trainer
      order by revision_number desc limit 1;
    if head.id is distinct from (p_request->>'expected_predecessor_id')::uuid then
      raise sqlstate 'PT409' using message='identity_head_changed'; end if;
    if p_request->>'capture_stream_id' is null or p_request->>'capture_sequence' is null then
      raise sqlstate 'PT409' using message='trusted_capture_order_required'; end if;
    if head.id is not null and (head.capture_stream_id is distinct from (p_request->>'capture_stream_id')::uuid
      or head.capture_sequence >= (p_request->>'capture_sequence')::bigint
      or saved.uploaded_at <= (select uploaded_at from public.save_files where id=head.save_file_id)) then
      raise sqlstate 'PT409' using message='identity_out_of_order'; end if;
    insert into public.pokemon_identity_revisions(season_id,trainer_id,save_file_id,parsed_save_id,
      predecessor_id,revision_number,capture_stream_id,capture_sequence,input_signature,
      identity_schema_version,reconciliation_version)
    values(season,trainer,save_id,parsed.id,head.id,coalesce(head.revision_number,0)+1,
      (p_request->>'capture_stream_id')::uuid,(p_request->>'capture_sequence')::bigint,
      p_request->>'input_signature',2,2) returning * into revision;

    for item in select value from jsonb_array_elements(p_request->'bindings') loop
      raw_pokemon := null;
      if item->>'source'='party' then
        select s->'pokemon' into raw_pokemon from jsonb_array_elements(parsed.payload->'party') s
          where s->>'slot_number'=item->>'slot_number';
      elsif item->>'source'='box' then
        select s->'pokemon' into raw_pokemon from jsonb_array_elements(parsed.payload->'boxes') b,
          lateral jsonb_array_elements(b->'slots') s where b->>'box_number'=item->>'box_number'
          and s->>'slot_number'=item->>'slot_number';
      end if;
      v_evidence := item->'evidence';
      if raw_pokemon is null or raw_pokemon->'identity_evidence' is distinct from v_evidence
        or v_evidence->'schema_version' is distinct from '2'::jsonb
        or v_evidence->'format' is distinct from parsed.payload->'generation'
        or jsonb_typeof(item->'candidate_entity_ids') is distinct from 'array'
        or jsonb_typeof(v_evidence->'is_egg') is distinct from 'boolean'
        or raw_pokemon->'is_egg' is distinct from v_evidence->'is_egg'
        or jsonb_typeof(v_evidence->'source_trainer_match') is distinct from 'boolean'
        or jsonb_typeof(v_evidence->'pid') is distinct from 'number'
        or jsonb_typeof(v_evidence->'encryption_constant') is distinct from 'number'
        or (v_evidence->>'pid')::numeric not between 0 and 4294967295
        or (v_evidence->>'encryption_constant')::numeric not between 0 and 4294967295
        or (v_evidence->>'pid') !~ '^[0-9]+$' or (v_evidence->>'encryption_constant') !~ '^[0-9]+$'
        or exists(select 1 from (values
            ('ot_tid',0,65535),('ot_sid',0,65535),('origin_version',1,255),
            ('language',1,255),('ot_gender',0,1)) limits(field,minimum,maximum)
          where jsonb_typeof(v_evidence->field) is distinct from 'number'
            or (v_evidence->>field) !~ '^[0-9]+$'
            or (v_evidence->>field)::numeric not between minimum and maximum)
        or jsonb_typeof(v_evidence->'ot_name') is distinct from 'string'
        or btrim(v_evidence->>'ot_name')=''
        or exists(select 1 from (values ('met_location',65535),('met_level',100),
            ('egg_location',65535)) limits(field,maximum)
          where v_evidence->field is null or (v_evidence->field<>'null'::jsonb and
            (jsonb_typeof(v_evidence->field) is distinct from 'number'
              or (v_evidence->>field) !~ '^[0-9]+$'
              or (v_evidence->>field)::numeric not between 0 and maximum)))
        or exists(select 1 from (values ('met_date'),('egg_date')) dates(field)
          where v_evidence->field is null or (v_evidence->field<>'null'::jsonb and
            (jsonb_typeof(v_evidence->field) is distinct from 'string'
              or (v_evidence->>field) !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$')))
        or jsonb_typeof(v_evidence->'ivs') is distinct from 'array'
        or jsonb_array_length(v_evidence->'ivs')<>6
        or exists(select 1 from jsonb_array_elements(v_evidence->'ivs') iv
          where jsonb_typeof(iv)<>'number' or iv::text !~ '^([0-9]|[12][0-9]|3[01])$')
        or item->'legacy_fingerprints' is distinct from '[]'::jsonb then
        raise sqlstate 'PT409' using message='identity_evidence_source_mismatch'; end if;
      -- Invalid calendar dates fail the transaction even when all shape guards pass.
      perform (v_evidence->>'met_date')::date, (v_evidence->>'egg_date')::date;
      trainer_match := coalesce(
        v_evidence->'ot_name'=parsed.payload->'trainer'->'name'
        and v_evidence->'ot_tid'=parsed.payload->'trainer'->'tid'
        and v_evidence->'ot_sid'=parsed.payload->'trainer'->'sid'
        and v_evidence->'ot_gender'=parsed.payload->'trainer'->'gender'
        and v_evidence->'language'=parsed.payload->'trainer'->'language',false);
      if v_evidence->'source_trainer_match' is distinct from to_jsonb(trainer_match) then
        raise sqlstate 'PT409' using message='identity_trainer_evidence_mismatch'; end if;

      select coalesce(array_agg(e.id order by e.id),'{}'::uuid[]) into candidate_ids
      from public.pokemon_entities e where e.season_id=season and e.owner_trainer_id=trainer
        and (e.initial_evidence->'pid'=v_evidence->'pid'
          or e.initial_evidence->'encryption_constant'=v_evidence->'encryption_constant');
      select count(*) into collision_count from jsonb_array_elements(p_request->'bindings') b
        where b->'evidence'->'pid'=v_evidence->'pid'
          or b->'evidence'->'encryption_constant'=v_evidence->'encryption_constant';
      select exists(select 1 from public.pokemon_observations o
        where o.season_id=season and o.trainer_id=trainer and o.outcome='AMBIGUOUS'
          and o.revision_id<>revision.id and (o.evidence->'pid'=v_evidence->'pid'
            or o.evidence->'encryption_constant'=v_evidence->'encryption_constant')) into poisoned;
      poisoned := poisoned or public.transfer_foreign_collision(season,trainer,v_evidence);
      eligible := coalesce((trainer_match or (cardinality(candidate_ids)=1 and public.transfer_identity_proven(candidate_ids[1],trainer,v_evidence))) and v_evidence->'is_egg'='false'::jsonb
        and v_evidence->'egg_location'='0'::jsonb and v_evidence->'egg_date'='null'::jsonb
        and jsonb_typeof(v_evidence->'met_location')='number'
        and (v_evidence->>'met_location')::integer between 1 and 65535
        and jsonb_typeof(v_evidence->'met_level')='number'
        and (v_evidence->>'met_level')::integer between 1 and 100
        and jsonb_typeof(v_evidence->'met_date')='string'
        and (v_evidence->>'met_date') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$',false);
      expected_outcome := 'AMBIGUOUS';
      if eligible and collision_count=1 and not poisoned then
        if cardinality(candidate_ids)=0 then expected_outcome := 'NEW';
        elsif cardinality(candidate_ids)=1 then
          select * into entity from public.pokemon_entities where id=candidate_ids[1] for update;
          if entity.identity_status='unambiguous' and entity.identity_schema_version=2
            and ((entity.initial_evidence=v_evidence and entity.candidate_key=item->>'candidate_key')
              or public.transfer_identity_proven(entity.id,trainer,v_evidence)) then
            expected_outcome := 'MATCHED';
          end if;
        end if;
      end if;
      if item->>'outcome' is distinct from expected_outcome then
        raise sqlstate 'PT409' using message='identity_invalid_binding'; end if;
      entity_id := (item->>'pokemon_entity_id')::uuid;
      select coalesce(array_agg(value::uuid order by value::uuid),'{}'::uuid[]) into submitted_ids
        from jsonb_array_elements_text(item->'candidate_entity_ids');
      if expected_outcome='NEW' then
        if entity_id is null or cardinality(submitted_ids)<>0 then
          raise sqlstate 'PT409' using message='identity_invalid_binding'; end if;
        insert into public.pokemon_entities(id,season_id,owner_trainer_id,identity_status,
          identity_schema_version,candidate_key,initial_evidence)
        values(entity_id,season,trainer,'unambiguous',2,item->>'candidate_key',v_evidence);
      elsif expected_outcome='MATCHED' then
        if entity_id is distinct from candidate_ids[1] or cardinality(submitted_ids)<>0 then
          raise sqlstate 'PT409' using message='identity_invalid_binding'; end if;
      else
        if entity_id is not null or submitted_ids is distinct from candidate_ids then
          raise sqlstate 'PT409' using message='identity_invalid_candidate'; end if;
        update public.pokemon_entities set identity_status='ambiguous',updated_at=now()
          where id=any(candidate_ids) and season_id=season and owner_trainer_id=trainer;
      end if;
      insert into public.pokemon_observations(revision_id,season_id,trainer_id,save_file_id,
        pokemon_entity_id,source,box_number,slot_number,outcome,candidate_entity_ids,evidence,
        candidate_key,observation_signature,legacy_fingerprints)
      values(revision.id,season,trainer,save_id,entity_id,item->>'source',
        (item->>'box_number')::int,(item->>'slot_number')::int,expected_outcome,submitted_ids,v_evidence,
        item->>'candidate_key',item->>'observation_signature','{}');
    end loop;
    update public.pokemon_entities e set identity_status='missing',updated_at=now()
      where e.season_id=season and e.owner_trainer_id=trainer and e.identity_status='unambiguous'
        and not exists(select 1 from public.pokemon_observations o
          where o.revision_id=revision.id and o.pokemon_entity_id=e.id);
  end if;
  return jsonb_build_object('revision',to_jsonb(revision),'observations',coalesce(
    (select jsonb_agg(to_jsonb(o) order by source,box_number,slot_number)
      from public.pokemon_observations o where revision_id=revision.id),'[]'::jsonb));
end $$;
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
      'proven_entity_ids',coalesce((select jsonb_agg(e.id) from public.pokemon_entities e where e.season_id=sid and e.owner_trainer_id=tid and public.transfer_identity_proven(e.id,tid,e.initial_evidence)),'[]'::jsonb),
      'foreign_transfer_evidence',coalesce((select jsonb_agg(e.initial_evidence) from public.pokemon_entities e where e.season_id=sid and e.owner_trainer_id<>tid and public.transfer_foreign_collision(sid,tid,e.initial_evidence)),'[]'::jsonb),
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
create or replace function public.transfer_state(p_id uuid) returns text language sql security definer set search_path='' as $$
 select coalesce((select terminal from public.item_use_transfers where authorization_id=p_id),case
  when count(*)<>2 then 'BLOCKED_UNCERTAIN'
  when count(proof)=2 then 'BOTH_VERIFIED_PENDING_IDENTITY'
  when bool_or(side='destination' and apply_started) then 'VERIFYING_BOTH'
  when bool_or(side='source' and proof is not null) then 'PENDING_DESTINATION'
  when bool_or(side='source' and apply_started) then 'VERIFYING_SOURCE'
  when count(claim_id)=2 then 'PENDING_SOURCE'
  when count(claim_id)=1 then 'WAITING_OTHER'
  else 'PREPARING' end) from public.item_use_transfer_legs where authorization_id=p_id;
$$;
create or replace function public.guard_transfer_reservation() returns trigger language plpgsql security definer set search_path='' as $$
begin
 if tg_table_name in('redemptions','item_use_authorizations') then
  if exists(select 1 from public.item_use_transfer_legs l where l.season_id=new.season_id and not l.released and not exists(select 1 from public.transfer_commit_permits p where p.txid=txid_current() and p.authorization_id=l.authorization_id) and
    (l.trainer_id=new.trainer_id or l.trainer_id in(select owner_trainer_id from public.pokemon_entities where id=new.target_pokemon_entity_id)))
  then raise sqlstate 'PT409' using message='transfer_reconciliation_required'; end if;
 else
  if exists(select 1 from public.item_use_transfer_legs l where l.season_id=new.season_id and not l.released and not exists(select 1 from public.transfer_commit_permits p where p.txid=txid_current() and p.authorization_id=l.authorization_id) and l.trainer_id=new.trainer_id)
  then raise sqlstate 'PT409' using message='transfer_reconciliation_required'; end if;
 end if;
 return new;
end $$;

alter function public.api_transfer_leg(jsonb) rename to transfer_leg_v057;
revoke all on function public.transfer_leg_v057(jsonb) from public,anon,authenticated,service_role,pokeapp_item_verifier;
create function public.api_transfer_leg(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare a public.item_use_authorizations; x public.item_use_transfers; l public.item_use_transfer_legs; r jsonb;
begin
 select * into a from public.item_use_authorizations where id=(p_request->>'authorization_id')::uuid;
 if a.id is null then raise sqlstate 'PT404' using message='transfer_not_found'; end if;
 perform 1 from public.seasons where id=a.season_id for no key update;
 select * into x from public.item_use_transfers where authorization_id=a.id for update;
 select * into l from public.item_use_transfer_legs where authorization_id=a.id and trainer_id=(p_request->>'trainer_id')::uuid and season_id=(p_request->>'season_id')::uuid;
 if l.side is null or not exists(select 1 from public.trainers where id=l.trainer_id and globally_enabled) then raise sqlstate 'PT403' using message='transfer_not_owned'; end if;
 if p_request->>'operation'='cancel' then
  if x.terminal='COMMITTED' or exists(select 1 from public.item_use_transfer_legs where authorization_id=a.id and apply_started) then
   raise sqlstate 'PT409' using message='transfer_assisted_recovery_required'; end if;
  update public.item_use_transfers set terminal='CANCELLED' where authorization_id=a.id;
  update public.item_use_transfer_legs set released=true where authorization_id=a.id;
  update public.item_use_authorizations set status='FAILED_RECOVERABLE',error_code='TRANSFER_CANCELLED' where id=a.id;
 elsif p_request->>'operation' is distinct from 'get' and x.terminal is not null then
  raise sqlstate 'PT409' using message='transfer_terminal';
 else
  r:=public.transfer_leg_v057(p_request);
 end if;
 if r is null then r:=public.transfer_leg_v057(p_request||jsonb_build_object('operation','get')); end if;
 return r||jsonb_build_object('status',public.transfer_state(a.id),'accepted_save_id',
  (select receipt->l.side->>'save_id' from public.item_use_transfers where authorization_id=a.id));
end $$;
revoke all on function public.api_transfer_leg(jsonb) from public,anon,authenticated,pokeapp_item_verifier;
grant execute on function public.api_transfer_leg(jsonb) to service_role;
create or replace function public.api_prepare_transfer(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare sid uuid:=(p_request->>'season_id')::uuid; tid uuid:=(p_request->>'trainer_id')::uuid;
 pid uuid:=(p_request->>'purchase_id')::uuid; eid uuid:=(p_request->>'pokemon_entity_id')::uuid;
 op uuid:=(p_request->>'operation_id')::uuid; a public.item_use_authorizations; e public.pokemon_entities;
 donor public.season_players; receiver public.season_players; dhead public.pokemon_identity_revisions; rhead public.pokemon_identity_revisions;
 ds public.save_files; rs public.save_files; obs public.pokemon_observations; cyc bigint;
begin
 if op is null then raise sqlstate 'PT422' using message='invalid_transfer'; end if;
 perform 1 from public.trainers where id=tid and globally_enabled for share;
 if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
 perform 1 from public.seasons where id=sid for no key update;
 perform 1 from public.season_players where season_id=sid order by id for update;
 select * into a from public.item_use_authorizations where purchase_id=pid for update;
 if found then
  if a.trainer_id is distinct from tid or a.season_id is distinct from sid or a.target_pokemon_entity_id is distinct from eid or a.operation_id is distinct from op::text
    or not exists(select 1 from public.item_use_transfers where authorization_id=a.id) then raise sqlstate 'PT409' using message='transfer_conflict'; end if;
  return jsonb_build_object('authorization_id',a.id,'status',public.transfer_state(a.id));
 end if;
 select * into e from public.pokemon_entities where id=eid and season_id=sid and identity_status='unambiguous' for update;
 if not found or e.owner_trainer_id=tid then raise sqlstate 'PT409' using message='transfer_target_invalid'; end if;
 select * into donor from public.season_players where season_id=sid and trainer_id=e.owner_trainer_id and status='active';
 select * into receiver from public.season_players where season_id=sid and trainer_id=tid and status='active';
 if donor.id is null or receiver.id is null or not exists(select 1 from public.trainers where id=e.owner_trainer_id and globally_enabled) then raise sqlstate 'PT409' using message='participant_inactive'; end if;
 perform 1 from public.purchases p join public.shop_items i on i.id=p.shop_item_id where p.id=pid and p.season_id=sid and p.trainer_id=tid and p.status='pending' and p.quantity=1 and i.code='robar_pokemon' for update of p;
 if not found then raise sqlstate 'PT409' using message='purchase_not_redeemable'; end if;
 select * into dhead from public.pokemon_identity_revisions where season_id=sid and trainer_id=donor.trainer_id order by revision_number desc limit 1;
 select * into rhead from public.pokemon_identity_revisions where season_id=sid and trainer_id=tid order by revision_number desc limit 1;
 select * into ds from public.save_files where id=donor.current_save_file_id and trainer_id=donor.trainer_id and season_id=sid and deleted_at is null and parser_status='parsed';
 select * into rs from public.save_files where id=receiver.current_save_file_id and trainer_id=tid and season_id=sid and deleted_at is null and parser_status='parsed';
 if ds.id is null or rs.id is null or dhead.id is null or rhead.id is null or dhead.save_file_id<>ds.id or rhead.save_file_id<>rs.id then raise sqlstate 'PT409' using message='save_context_changed'; end if;
 select * into obs from public.pokemon_observations where revision_id=dhead.id and pokemon_entity_id=eid and outcome in ('NEW','MATCHED');
 if not found or obs.source<>'box' or obs.box_number not between 1 and 7 then raise sqlstate 'PT409' using message='transfer_native_scope_unqualified'; end if;
 if exists(select 1 from public.pokemon_entity_flags f left join public.pokemon_flags l on l.id=f.legacy_flag_id where f.season_id=sid and f.pokemon_entity_id=eid and f.flag_type in ('blindado','robado') and coalesce(f.flag_value,l.flag_value,false)) then raise sqlstate 'PT409' using message='steal_target_shielded'; end if;
 select coalesce((select cycle_number from public.robbery_cycles where season_id=sid),1) into cyc;
 -- Match025 pre-check reset semantics, without changing the cursor before use.
 if not exists(select 1 from public.season_players sp join public.trainers t on t.id=sp.trainer_id where sp.season_id=sid and sp.status='active' and t.globally_enabled and not exists(select 1 from public.redemptions r where r.season_id=sid and r.robbery_cycle_number=cyc and r.target_owner_trainer_id=sp.trainer_id)) then cyc:=cyc+1; end if;
 if exists(select 1 from public.redemptions where season_id=sid and robbery_cycle_number=cyc and target_owner_trainer_id=donor.trainer_id) then raise sqlstate 'PT409' using message='steal_victim_already_robbed'; end if;
 if exists(select 1 from public.item_use_authorizations where season_id=sid and (target_pokemon_entity_id=eid or trainer_id in(tid,donor.trainer_id)) and status<>'APPLIED_VERIFIED' and not exists(select 1 from public.item_use_transfers x where x.authorization_id=item_use_authorizations.id and x.terminal='CANCELLED')) then raise sqlstate 'PT409' using message='transfer_reserved'; end if;
 insert into public.item_use_authorizations(operation_id,idempotency_key,purchase_id,season_id,trainer_id,target_pokemon_entity_id,save_file_id,save_sha256,identity_revision_id,effect_code)
 values(op::text,op::text,pid,sid,tid,eid,rs.id,rs.sha256,dhead.id,'steal') returning * into a;
 insert into public.item_use_transfers(authorization_id,donor_id) values(a.id,donor.trainer_id);
 insert into public.item_use_transfer_legs(authorization_id,side,season_id,trainer_id,save_file_id,identity_revision_id,source_sha256) values
 (a.id,'source',sid,donor.trainer_id,ds.id,dhead.id,ds.sha256),(a.id,'destination',sid,tid,rs.id,rhead.id,rs.sha256);
 return jsonb_build_object('authorization_id',a.id,'status','PREPARING');
end $$;

create or replace function public.check_item_use_redemption() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if new.effect_code='steal' and exists(
  select 1 from public.transfer_commit_permits c join public.item_use_authorizations a on a.id=c.authorization_id
  where c.txid=txid_current() and a.purchase_id=new.purchase_id and a.season_id=new.season_id
   and a.trainer_id=new.trainer_id and a.target_pokemon_entity_id=new.target_pokemon_entity_id
   and a.identity_revision_id=new.identity_revision_id and a.idempotency_key=new.idempotency_key
   and (select count(proof) from public.item_use_transfer_legs where authorization_id=a.id)=2
 ) then return new; end if;
 if new.effect_code in ('revive','steal') and not exists (
  select 1 from public.item_use_authorizations a join public.item_use_verifications v on v.authorization_id=a.id
  where a.purchase_id=new.purchase_id and a.season_id=new.season_id and a.trainer_id=new.trainer_id
   and a.idempotency_key=new.idempotency_key and a.target_pokemon_entity_id=new.target_pokemon_entity_id
   and a.identity_revision_id=new.identity_revision_id and a.effect_code=new.effect_code
   and a.claim_id=v.claim_id and a.operation_id=v.operation_id and a.save_sha256=v.source_sha256
   and a.status='APPLIED_VERIFIED' and a.observed_sha256=v.result_sha256
   and a.identity_revision_id=v.identity_revision_id and a.target_pokemon_entity_id=v.target_pokemon_entity_id
   and v.verified_at between a.created_at and a.expires_at and a.expires_at>clock_timestamp()
 ) then raise sqlstate 'PT409' using message='physical_verification_required'; end if;
 return new;
end $$;

-- Preserve linked legacy flag provenance while projecting current competitive owner.
create or replace function public.check_pokemon_entity_flag() returns trigger
language plpgsql security definer set search_path='' as $$
begin
 if not exists(select 1 from public.pokemon_entities e where e.id=new.pokemon_entity_id and e.season_id=new.season_id and e.owner_trainer_id=new.trainer_id) then
  raise check_violation using message='identity_flag_owner_mismatch'; end if;
 if new.legacy_flag_id is not null and not exists(select 1 from public.pokemon_flags f
  where f.id=new.legacy_flag_id and f.season_id=new.season_id and f.flag_type=new.flag_type and
   (f.trainer_id=new.trainer_id or exists(select 1 from public.transfer_provenance p
    where p.pokemon_entity_id=new.pokemon_entity_id and p.recipient_id=new.trainer_id and p.donor_id=f.trainer_id
    and exists(select 1 from jsonb_array_elements(p.original_flags) captured_flag where captured_flag->>'id'=new.id::text and captured_flag->>'legacy_flag_id'=new.legacy_flag_id::text)))) then
  raise check_violation using message='identity_flag_legacy_mismatch'; end if;
 return new;
end $$;

alter function public.transfer_verifier(jsonb) rename to transfer_verifier_v057;
revoke all on function public.transfer_verifier_v057(jsonb) from public,anon,authenticated,service_role,pokeapp_item_verifier;
create function public.transfer_verifier(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare aid uuid:=(p_request->>'authorization_id')::uuid; op text:=p_request->>'operation';
 a public.item_use_authorizations; x public.item_use_transfers; l public.item_use_transfer_legs;
 c jsonb; req jsonb; contexts jsonb:='{}'; results jsonb:='{}'; redemption jsonb;
 source_revision uuid; destination_revision uuid;
begin
 select * into a from public.item_use_authorizations where id=aid;
 if a.id is null then raise sqlstate 'PT404' using message='transfer_not_found'; end if;
 -- Match025's actor -> season -> ordered participants. No schema/business locks outside this transaction.
 perform 1 from public.trainers where id in(a.trainer_id,(select donor_id from public.item_use_transfers where authorization_id=aid)) order by id for share;
 perform 1 from public.seasons where id=a.season_id for no key update;
 perform 1 from public.season_players where season_id=a.season_id order by id for update;
 select * into x from public.item_use_transfers where authorization_id=aid for update;
 if x.authorization_id is null then raise sqlstate 'PT404' using message='transfer_not_found'; end if;
 if op='status' then return jsonb_build_object('status',public.transfer_state(aid),'receipt',x.receipt); end if;
 if x.terminal='COMMITTED' and op='finalize' then return jsonb_build_object('status','COMMITTED','receipt',x.receipt); end if;
 if x.terminal is not null then raise sqlstate 'PT409' using message='transfer_terminal'; end if;
 if op not in ('registration_context','finalize') then return public.transfer_verifier_v057(p_request); end if;
 perform 1 from public.item_use_transfer_legs where authorization_id=aid order by side for update;
 c:=public.transfer_context(aid);
 if c->'eligible' is distinct from 'true'::jsonb or c->'purchase_pending' is distinct from 'true'::jsonb
  or exists(select 1 from jsonb_each(c->'legs') v where v.value->'trainer_enabled' is distinct from 'true'::jsonb or v.value->'participant_active' is distinct from 'true'::jsonb or v.value->>'current_save_id' is distinct from v.value->'save'->>'id')
  then raise sqlstate 'PT409' using message='transfer_context_changed'; end if;
 if op='registration_context' then
  for l in select * from public.item_use_transfer_legs where authorization_id=aid loop
   contexts:=contexts||jsonb_build_object(l.side,public.api_register_save(jsonb_build_object('operation','context','season_id',l.season_id,'trainer_id',l.trainer_id)));
  end loop;
  return jsonb_build_object('context',c,'registration',contexts);
 end if;
 if c is distinct from p_request->'context' or (select count(proof) from public.item_use_transfer_legs where authorization_id=aid)<>2 then
  raise sqlstate 'PT409' using message='transfer_both_proofs_required'; end if;
 -- The private verifier binds independently reparsed original/result bytes to these requests.
 -- Neither service_role nor browser can call this function or insert proofs/permits.
 for l in select * from public.item_use_transfer_legs where authorization_id=aid loop
  req:=p_request->'requests'->l.side;
  if req is null or req->>'season_id' is distinct from l.season_id::text or req->>'trainer_id' is distinct from l.trainer_id::text
   or req->>'sha256' is distinct from l.result_sha256 or req->>'expected_save_id' is distinct from l.save_file_id::text
   or req->'identity_plan'->>'expected_predecessor_id' is distinct from l.identity_revision_id::text
   or req->'save_identity' is distinct from c->'legs'->l.side->'save'->'metadata'->'save_identity'
   or l.proof->>'result_sha256' is distinct from l.result_sha256 or l.proof->>'source_sha256' is distinct from l.source_sha256
   or l.proof->>'claim_id' is distinct from l.claim_id::text or l.proof->>'plan_sha256' is distinct from x.plans->l.side->>'plan_sha256'
   or not l.apply_started then raise sqlstate 'PT409' using message='transfer_registration_mismatch'; end if;
 end loop;
 insert into public.transfer_commit_permits values(txid_current(),aid);
 -- Execute canonical025 while donor ownership/head still match the authorized target.
 redemption:=public.api_redeem_purchase(a.season_id,a.trainer_id,a.purchase_id,a.target_pokemon_entity_id,a.idempotency_key,a.identity_revision_id);
 insert into public.transfer_provenance(authorization_id,pokemon_entity_id,season_id,donor_id,recipient_id,evidence,originals,results,proofs,original_flags)
 values(aid,a.target_pokemon_entity_id,a.season_id,x.donor_id,a.trainer_id,c->'entity'->'initial_evidence',c->'legs',
  p_request->'requests',(select jsonb_object_agg(side,proof) from public.item_use_transfer_legs where authorization_id=aid),
  coalesce((select jsonb_agg(to_jsonb(f)) from public.pokemon_entity_flags f where pokemon_entity_id=a.target_pokemon_entity_id),'[]'::jsonb));
 update public.pokemon_entities set owner_trainer_id=a.trainer_id,updated_at=now() where id=a.target_pokemon_entity_id;
 update public.pokemon_entity_flags set trainer_id=a.trainer_id where pokemon_entity_id=a.target_pokemon_entity_id;
 for l in select * from public.item_use_transfer_legs where authorization_id=aid order by side loop
  req:=p_request->'requests'->l.side;
  results:=results||jsonb_build_object(l.side,public.api_register_save(req||jsonb_build_object('operation','register')));
 end loop;
 select id into source_revision from public.pokemon_identity_revisions where save_file_id=(results->'source'->>'save_id')::uuid;
 select id into destination_revision from public.pokemon_identity_revisions where save_file_id=(results->'destination'->>'save_id')::uuid;
 if source_revision is null or destination_revision is null
  or exists(select 1 from public.pokemon_observations where revision_id=source_revision and pokemon_entity_id=a.target_pokemon_entity_id)
  or (select count(*) from public.pokemon_observations where revision_id=destination_revision and pokemon_entity_id=a.target_pokemon_entity_id and outcome='MATCHED')<>1
  or exists(select 1 from public.item_use_transfer_legs l2 join public.season_players sp on sp.season_id=l2.season_id and sp.trainer_id=l2.trainer_id
    where l2.authorization_id=aid and sp.current_save_file_id is distinct from (results->l2.side->>'save_id')::uuid)
  then raise sqlstate 'PT409' using message='transfer_identity_not_accepted'; end if;
 results:=results||jsonb_build_object('redemption',redemption,'pokemon_entity_id',a.target_pokemon_entity_id,
  'source_revision_id',source_revision,'destination_revision_id',destination_revision);
 update public.item_use_authorizations set status='APPLIED_VERIFIED',observed_sha256=(select result_sha256 from public.item_use_transfer_legs where authorization_id=aid and side='destination'),receipt=results,applied_at=now(),updated_at=now(),error_code=null where id=aid;
 update public.item_use_transfers set terminal='COMMITTED',receipt=results where authorization_id=aid;
 update public.item_use_transfer_legs set released=true where authorization_id=aid;
 delete from public.transfer_commit_permits where txid=txid_current();
 return jsonb_build_object('status','COMMITTED','receipt',results);
end $$;
revoke all on function public.transfer_verifier(jsonb) from public,anon,authenticated,service_role;
grant execute on function public.transfer_verifier(jsonb) to pokeapp_item_verifier;
comment on table public.transfer_provenance is 'Private paired-proof provenance; original OT/UUID immutable. No client proof or production writer capability.';
commit;
