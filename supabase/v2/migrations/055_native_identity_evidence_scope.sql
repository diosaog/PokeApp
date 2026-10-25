-- Phase23C: real native ingestion revealed SQLSTATE42702.
-- Rename the local evidence variable; no policy, columns, grants or data changed.
-- Forward only: applied048 is preserved. NOT DEPLOYED.
begin;
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
      eligible := coalesce(trainer_match and v_evidence->'is_egg'='false'::jsonb
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
            and entity.initial_evidence=v_evidence and entity.candidate_key=item->>'candidate_key' then
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
commit;
