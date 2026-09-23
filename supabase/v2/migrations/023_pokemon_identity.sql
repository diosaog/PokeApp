-- PokeApp-owned identity. Raw evidence is private; no runtime or redemption wiring.
begin;

create table public.pokemon_entities (
  id uuid primary key,
  season_id uuid not null references public.seasons(id) on delete restrict,
  owner_trainer_id uuid not null references public.trainers(id) on delete restrict,
  identity_status text not null check (identity_status in ('unambiguous','missing','ambiguous')),
  identity_schema_version integer not null check (identity_schema_version = 1),
  candidate_key text not null check (candidate_key ~ '^[a-f0-9]{64}$'),
  initial_evidence jsonb not null check (jsonb_typeof(initial_evidence) = 'object'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(id, season_id),
  foreign key (season_id, owner_trainer_id) references public.season_players(season_id, trainer_id)
);
create index pokemon_entities_owner_idx on public.pokemon_entities(season_id, owner_trainer_id, candidate_key);

alter table public.parsed_saves add constraint uq_parsed_saves_identity_file unique(id, save_file_id);
create table public.pokemon_identity_revisions (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null,
  trainer_id uuid not null,
  save_file_id uuid not null unique,
  parsed_save_id uuid not null,
  predecessor_id uuid,
  revision_number bigint not null check(revision_number > 0),
  capture_stream_id uuid not null,
  capture_sequence bigint not null check(capture_sequence > 0),
  input_signature text not null check(input_signature ~ '^[a-f0-9]{64}$'),
  identity_schema_version integer not null default 1 check(identity_schema_version = 1),
  reconciliation_version integer not null default 1 check(reconciliation_version = 1),
  created_at timestamptz not null default now(),
  unique(id, season_id, trainer_id),
  unique(id, save_file_id, season_id, trainer_id),
  unique(season_id, trainer_id, revision_number),
  unique(season_id, trainer_id, capture_stream_id, capture_sequence),
  foreign key(save_file_id, season_id, trainer_id) references public.save_files(id, season_id, trainer_id),
  foreign key(parsed_save_id, save_file_id) references public.parsed_saves(id, save_file_id),
  foreign key(predecessor_id, season_id, trainer_id) references public.pokemon_identity_revisions(id, season_id, trainer_id),
  check ((revision_number = 1) = (predecessor_id is null))
);
create table public.pokemon_observations (
  id uuid primary key default gen_random_uuid(),
  revision_id uuid not null,
  season_id uuid not null,
  trainer_id uuid not null,
  save_file_id uuid not null,
  pokemon_entity_id uuid,
  source text not null check(source in ('party','box')),
  box_number integer not null,
  slot_number integer not null,
  outcome text not null check(outcome in ('NEW','MATCHED','AMBIGUOUS')),
  candidate_entity_ids uuid[] not null default '{}',
  evidence jsonb not null check(jsonb_typeof(evidence) = 'object'),
  candidate_key text not null check(candidate_key ~ '^[a-f0-9]{64}$'),
  observation_signature text not null check(observation_signature ~ '^[a-f0-9]{64}$'),
  legacy_fingerprints text[] not null default '{}',
  created_at timestamptz not null default now(),
  unique(save_file_id, source, box_number, slot_number),
  unique(save_file_id, pokemon_entity_id),
  foreign key(revision_id, save_file_id, season_id, trainer_id)
    references public.pokemon_identity_revisions(id, save_file_id, season_id, trainer_id),
  foreign key(pokemon_entity_id, season_id) references public.pokemon_entities(id, season_id),
  check((source='party' and box_number=0 and slot_number between 1 and 6)
     or (source='box' and box_number>0 and slot_number between 1 and 30)),
  check((outcome='AMBIGUOUS' and pokemon_entity_id is null and cardinality(candidate_entity_ids)>0)
     or (outcome<>'AMBIGUOUS' and pokemon_entity_id is not null and cardinality(candidate_entity_ids)=0))
);
create index pokemon_observations_revision_idx on public.pokemon_observations(revision_id);
create index pokemon_observations_entity_idx on public.pokemon_observations(pokemon_entity_id);

-- A link keeps the legacy flag/value authoritative. New flags need no invented fingerprint.
create table public.pokemon_entity_flags (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null,
  trainer_id uuid not null,
  pokemon_entity_id uuid not null,
  flag_type text not null check(flag_type ~ '^[a-z0-9_]+$'),
  flag_value boolean,
  legacy_flag_id uuid unique references public.pokemon_flags(id) on delete restrict,
  created_at timestamptz not null default now(),
  unique(season_id, pokemon_entity_id, flag_type),
  foreign key(pokemon_entity_id, season_id) references public.pokemon_entities(id, season_id),
  foreign key(season_id, trainer_id) references public.season_players(season_id, trainer_id),
  check((legacy_flag_id is null) = (flag_value is not null))
);
create function public.check_pokemon_entity_flag() returns trigger
language plpgsql security invoker set search_path = '' as $$
begin
  if not exists(select 1 from public.pokemon_entities where id=new.pokemon_entity_id
    and season_id=new.season_id and owner_trainer_id=new.trainer_id) then
    raise check_violation using message='identity_flag_owner_mismatch'; end if;
  if new.legacy_flag_id is not null and not exists(select 1 from public.pokemon_flags
    where id=new.legacy_flag_id and season_id=new.season_id and trainer_id=new.trainer_id
    and flag_type=new.flag_type) then
    raise check_violation using message='identity_flag_legacy_mismatch'; end if;
  return new;
end $$;
revoke all on function public.check_pokemon_entity_flag() from public,anon,authenticated;
grant execute on function public.check_pokemon_entity_flag() to service_role;
create trigger pokemon_entity_flag_scope before insert or update on public.pokemon_entity_flags
for each row execute function public.check_pokemon_entity_flag();
comment on table public.pokemon_flags is
  'Legacy fingerprint flags, retained unchanged. Safe individual links live in pokemon_entity_flags; missing link means unresolved.';
comment on table public.pokemon_entities is
  'Season-scoped PokeApp UUID, not PID/OT/slot. Current ownership may change via a future audited command; observations retain historical owner.';
comment on table public.pokemon_identity_revisions is
  'Explicit CAS predecessor chain. Capture stream/sequence must be attested by backend; upload time alone is not game chronology.';

do $$ declare t text; owner_column text; begin
  foreach t in array array['pokemon_entities','pokemon_identity_revisions','pokemon_observations','pokemon_entity_flags'] loop
    execute format('alter table public.%I enable row level security',t);
    execute format('revoke all on public.%I from public, anon, authenticated',t);
    execute format('grant select on public.%I to authenticated',t);
    execute format('grant all on public.%I to service_role',t);
    owner_column := case when t='pokemon_entities' then 'owner_trainer_id' else 'trainer_id' end;
    execute format('create policy identity_private_read on public.%I for select to authenticated using
      (public.current_user_owns_trainer(%I) or public.is_current_user_admin())',t,owner_column);
  end loop;
end $$;

create function public.commit_pokemon_identity(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path = '' as $$
declare
  season uuid := (p_request->>'season_id')::uuid;
  trainer uuid := (p_request->>'trainer_id')::uuid;
  save_id uuid := (p_request->>'save_file_id')::uuid;
  head public.pokemon_identity_revisions;
  revision public.pokemon_identity_revisions;
  saved public.save_files;
  parsed public.parsed_saves;
  item jsonb;
  entity public.pokemon_entities;
  entity_id uuid;
  legacy public.pokemon_flags;
  targets uuid[];
  unresolved boolean;
  raw_pokemon jsonb;
  occurrence_count integer;
begin
  -- Shared player lock serializes concurrent workers across all saves of this owner.
  perform 1 from public.season_players where season_id=season and trainer_id=trainer for update;
  if not found then raise sqlstate 'PT404' using message='identity_player_not_found'; end if;
  select * into saved from public.save_files where id=save_id and season_id=season and trainer_id=trainer for share;
  if not found or saved.deleted_at is not null or saved.parser_status<>'parsed' then
    raise sqlstate 'PT409' using message='identity_save_not_ready'; end if;
  select * into parsed from public.parsed_saves where id=(p_request->>'parsed_save_id')::uuid
    and save_file_id=save_id for share;
  if not found or parsed.status<>'parsed' or parsed.payload is distinct from p_request->'parsed_payload'
    or parsed.parser_version is distinct from saved.parser_version then
    raise sqlstate 'PT409' using message='identity_parsed_source_changed'; end if;
  if jsonb_typeof(p_request->'bindings') is distinct from 'array'
    or (p_request->>'identity_schema_version')::int is distinct from 1
    or (p_request->>'reconciliation_version')::int is distinct from 1 then
    raise sqlstate 'PT409' using message='identity_invalid_plan'; end if;
  if jsonb_typeof(parsed.payload->'party') is distinct from 'array'
    or jsonb_typeof(parsed.payload->'boxes') is distinct from 'array' then
    raise sqlstate 'PT409' using message='identity_incomplete_payload'; end if;
  select count(*) into occurrence_count from (
    select s->'pokemon' p from jsonb_array_elements(parsed.payload->'party') s
    union all select s->'pokemon' from jsonb_array_elements(parsed.payload->'boxes') b,
      lateral jsonb_array_elements(b->'slots') s
  ) occurrences where p is not null and p<>'null'::jsonb;
  if occurrence_count <> jsonb_array_length(p_request->'bindings') then
    raise sqlstate 'PT409' using message='identity_incomplete_plan'; end if;

  select * into revision from public.pokemon_identity_revisions where save_file_id=save_id;
  if found then
    if revision.input_signature is distinct from p_request->>'input_signature' then
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
      predecessor_id,revision_number,capture_stream_id,capture_sequence,input_signature)
    values(season,trainer,save_id,parsed.id,head.id,coalesce(head.revision_number,0)+1,
      (p_request->>'capture_stream_id')::uuid,(p_request->>'capture_sequence')::bigint,p_request->>'input_signature')
    returning * into revision;

    update public.pokemon_entities set identity_status='missing',updated_at=now()
      where season_id=season and owner_trainer_id=trainer and identity_status='unambiguous';
    for item in select value from jsonb_array_elements(p_request->'bindings') loop
      raw_pokemon := null;
      if item->>'source'='party' then
        select s->'pokemon' into raw_pokemon from jsonb_array_elements(parsed.payload->'party') s
          where s->>'slot_number'=item->>'slot_number';
      else
        select s->'pokemon' into raw_pokemon from jsonb_array_elements(parsed.payload->'boxes') b,
          lateral jsonb_array_elements(b->'slots') s where b->>'box_number'=item->>'box_number'
          and s->>'slot_number'=item->>'slot_number';
      end if;
      if raw_pokemon is null or raw_pokemon->'identity_evidence' is distinct from item->'evidence' then
        raise sqlstate 'PT409' using message='identity_evidence_source_mismatch'; end if;
      entity_id := (item->>'pokemon_entity_id')::uuid;
      if item->>'outcome'='NEW' then
        if exists(select 1 from public.pokemon_entities e where e.season_id=season and e.owner_trainer_id=trainer
          and e.initial_evidence->>'pid'=item->'evidence'->>'pid' and not exists
          (select 1 from public.pokemon_observations o where o.revision_id=revision.id and o.pokemon_entity_id=e.id)) then
          raise sqlstate 'PT409' using message='identity_new_has_prior_candidate'; end if;
        insert into public.pokemon_entities(id,season_id,owner_trainer_id,identity_status,
          identity_schema_version,candidate_key,initial_evidence)
        values(entity_id,season,trainer,'unambiguous',1,item->>'candidate_key',item->'evidence');
      elsif item->>'outcome'='MATCHED' then
        if (select count(*) from public.pokemon_entities e where e.season_id=season and e.owner_trainer_id=trainer
          and e.initial_evidence->>'pid'=item->'evidence'->>'pid') <> 1
          or (select count(*) from jsonb_array_elements(p_request->'bindings') b
            where b->'evidence'->>'pid'=item->'evidence'->>'pid') <> 1 then
          raise sqlstate 'PT409' using message='identity_multiple_candidates'; end if;
        select * into entity from public.pokemon_entities where id=entity_id and season_id=season
          and owner_trainer_id=trainer and candidate_key=item->>'candidate_key' for update;
        if not found or entity.identity_status='ambiguous' then
          raise sqlstate 'PT409' using message='identity_invalid_binding'; end if;
        update public.pokemon_entities set identity_status='unambiguous',updated_at=now() where id=entity_id;
      elsif item->>'outcome'='AMBIGUOUS' then
        for entity_id in select value::uuid from jsonb_array_elements_text(item->'candidate_entity_ids') loop
          update public.pokemon_entities set identity_status='ambiguous',updated_at=now()
            where id=entity_id and season_id=season and owner_trainer_id=trainer
              and initial_evidence->>'pid'=item->'evidence'->>'pid';
          if not found then raise sqlstate 'PT409' using message='identity_invalid_candidate'; end if;
        end loop;
      else raise sqlstate 'PT409' using message='identity_invalid_outcome'; end if;
      insert into public.pokemon_observations(revision_id,season_id,trainer_id,save_file_id,
        pokemon_entity_id,source,box_number,slot_number,outcome,candidate_entity_ids,evidence,
        candidate_key,observation_signature,legacy_fingerprints)
      values(revision.id,season,trainer,save_id,(item->>'pokemon_entity_id')::uuid,item->>'source',
        (item->>'box_number')::int,(item->>'slot_number')::int,item->>'outcome',
        array(select value::uuid from jsonb_array_elements_text(item->'candidate_entity_ids')),
        item->'evidence',item->>'candidate_key',item->>'observation_signature',
        array(select value from jsonb_array_elements_text(item->'legacy_fingerprints')));
    end loop;

    -- Consider all retained observations in THIS chain/scope, never choose first/all on a collision.
    for legacy in select * from public.pokemon_flags where season_id=season and trainer_id=trainer for share loop
      select array_agg(distinct pokemon_entity_id) filter(where pokemon_entity_id is not null),
        bool_or(pokemon_entity_id is null) into targets,unresolved
      from public.pokemon_observations where season_id=season and trainer_id=trainer
        and legacy.fingerprint=any(legacy_fingerprints);
      if cardinality(targets)=1 and not coalesce(unresolved,false) then
        insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,legacy_flag_id)
        values(season,trainer,targets[1],legacy.flag_type,legacy.id) on conflict do nothing;
      end if;
    end loop;
  end if;
  return jsonb_build_object('revision',to_jsonb(revision),'observations',coalesce(
    (select jsonb_agg(to_jsonb(o) order by source,box_number,slot_number)
     from public.pokemon_observations o where revision_id=revision.id),'[]'::jsonb));
end $$;
revoke all on function public.commit_pokemon_identity(jsonb) from public, anon, authenticated;
grant execute on function public.commit_pokemon_identity(jsonb) to service_role;

commit;
