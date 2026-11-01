-- Virtual consumables: the existing paid purchase is consumed only together
-- with independently native-verified output registration and audited identity
-- continuity. No balance, historical observation, flag or closed result rewrite.
begin;

create table public.training_operations (
  operation_id uuid primary key,
  purchase_id uuid not null references public.purchases(id),
  purchase_season_id uuid not null references public.seasons(id),
  season_id uuid not null,
  trainer_id uuid not null,
  pokemon_entity_id uuid not null references public.pokemon_entities(id),
  save_file_id uuid not null references public.save_files(id),
  identity_revision_id uuid not null references public.pokemon_identity_revisions(id),
  request_hash text not null check(request_hash ~ '^[a-f0-9]{64}$'),
  intent jsonb not null check(jsonb_typeof(intent)='object'),
  status text not null check(status in ('RESERVED','APPLIED','RELEASED')),
  before_evidence jsonb,
  after_evidence jsonb,
  before_candidate_key text,
  after_candidate_key text,
  output_sha256 text check(output_sha256 is null or output_sha256 ~ '^[a-f0-9]{64}$'),
  result jsonb,
  reserved_at timestamptz not null default clock_timestamp(),
  finished_at timestamptz,
  foreign key(season_id,trainer_id) references public.season_players(season_id,trainer_id),
  check((status='RESERVED')=(finished_at is null)),
  check(status<>'APPLIED' or (output_sha256 is not null and before_evidence is not null
    and after_evidence is not null and result is not null))
);
create unique index training_purchase_live on public.training_operations(purchase_id) where status<>'RELEASED';
create unique index training_trainer_reserved on public.training_operations(season_id,trainer_id) where status='RESERVED';
create index training_entity_history on public.training_operations(pokemon_entity_id,reserved_at);
alter table public.training_operations enable row level security;
alter table public.training_operations force row level security;
revoke all on public.training_operations from public,anon,authenticated,service_role;
grant select,insert,update on public.training_operations to service_role;

create function public.training_receipt(o public.training_operations) returns jsonb
language sql stable security invoker set search_path='' as $$
  select jsonb_build_object('operation_id',o.operation_id,'purchase_id',o.purchase_id,'purchase_season_id',o.purchase_season_id,
    'season_id',o.season_id,'trainer_id',o.trainer_id,
    'pokemon_entity_id',o.pokemon_entity_id,'save_file_id',o.save_file_id,
    'identity_revision_id',o.identity_revision_id,'status',o.status,
    'intent',o.intent,'reserved_at',o.reserved_at,'finished_at',o.finished_at,'result',o.result)
$$;

-- Every authorizing read is scoped to the authenticated trainer supplied by
-- the API, then rechecked under the participant lock before reservation.
create function public.training_context(sid uuid,tid uuid) returns jsonb
language plpgsql stable security invoker set search_path='' as $$
declare p public.season_players; s public.save_files; h public.pokemon_identity_revisions; payload jsonb;
begin
  select * into p from public.season_players where season_id=sid and trainer_id=tid;
  if not found or p.status<>'active' or not exists(select 1 from public.trainers where id=tid and globally_enabled)
    then raise sqlstate 'PT403' using message='training_participant_required'; end if;
  if not exists(select 1 from public.seasons where id=sid and status='active') then
    raise sqlstate 'PT409' using message='training_season_inactive'; end if;
  select * into s from public.save_files where id=p.current_save_file_id and season_id=sid and trainer_id=tid
    and deleted_at is null and parser_status='parsed';
  select * into h from public.pokemon_identity_revisions where season_id=sid and trainer_id=tid
    order by revision_number desc limit 1;
  if s.id is null or h.save_file_id is distinct from s.id then
    raise sqlstate 'PT409' using message='training_save_required'; end if;
  select parsed.payload into payload from public.parsed_saves parsed where parsed.id=h.parsed_save_id
    and parsed.save_file_id=s.id and parsed.status='parsed' and parsed.parser_version=s.parser_version;
  if payload->>'game' not in ('X','Y','OR','AS','SN','MN','US','UM')
    or payload->'identity_policy_version' is distinct from '2'::jsonb then
    raise sqlstate 'PT409' using message='training_save_required'; end if;
  return jsonb_build_object('player',to_jsonb(p),'save',to_jsonb(s),'revision',to_jsonb(h),'payload',payload,
    'registration',public.api_register_save(jsonb_build_object('operation','context','season_id',sid,'trainer_id',tid)),
    'observations',coalesce((select jsonb_agg(to_jsonb(o) order by o.source,o.box_number,o.slot_number)
      from public.pokemon_observations o join public.pokemon_entities e on e.id=o.pokemon_entity_id
      where o.revision_id=h.id and o.season_id=sid and o.trainer_id=tid and e.owner_trainer_id=tid
        and e.identity_status='unambiguous' and o.outcome in ('NEW','MATCHED')
        and not(o.source='box' and o.box_number=p.dead_box_number)
        and o.evidence->'is_egg'='false'::jsonb),'[]'::jsonb),
    'purchases',coalesce((select jsonb_agg(jsonb_build_object('purchase_id',q.id,'purchase_season_id',q.season_id,'item_code',i.code,'name',i.name))
      from public.purchases q join public.shop_items i on i.id=q.shop_item_id
      where q.trainer_id=tid and q.status='pending' and q.acquisition_type='paid'
        and q.quantity=1 and i.code in ('menta_naturaleza','chapa_plateada','chapa_dorada')
        and not exists(select 1 from public.item_deliveries d where d.purchase_id=q.id and d.status<>'RELEASED')),'[]'::jsonb),
    'operations',coalesce((select jsonb_agg(public.training_receipt(t) order by reserved_at)
      from public.training_operations t where t.season_id=sid and t.trainer_id=tid and t.status='RESERVED'),'[]'::jsonb));
end $$;

create function public.training_assert_available(sid uuid,tid uuid) returns void
language plpgsql security definer set search_path='' as $$
begin
  if exists(select 1 from public.item_deliveries where season_id=sid and trainer_id=tid and status='RESERVED')
    or exists(select 1 from public.item_use_transfer_legs where season_id=sid and trainer_id=tid and not released)
    or exists(select 1 from public.item_use_authorizations a where a.season_id=sid and a.trainer_id=tid
      and a.status<>'APPLIED_VERIFIED' and not exists(select 1 from public.item_use_transfers x
        where x.authorization_id=a.id and x.terminal='CANCELLED')) then
    raise sqlstate 'PT409' using message='training_save_busy'; end if;
  if exists(select 1 from public.team_locks l join public.seasons s on s.id=l.season_id
    where l.season_id=sid and l.trainer_id=tid and l.matchday_id=s.current_matchday_id) then
    raise sqlstate 'PT409' using message='training_competitive_lock'; end if;
end $$;

create function public.api_training_operation(r jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare sid uuid=(r->>'season_id')::uuid; tid uuid=(r->>'trainer_id')::uuid;
  op uuid=(r->>'operation_id')::uuid; action text=r->>'operation'; t public.training_operations;
  p public.purchases; code text; c jsonb; o jsonb; e public.pokemon_entities;
  registration jsonb; v_result jsonb; before jsonb; after jsonb; observed jsonb; m jsonb; identity jsonb;
begin
  if action='context' then return public.training_context(sid,tid); end if;
  if action='load' then
    select * into t from public.training_operations where operation_id=op and season_id=sid and trainer_id=tid;
    return case when t.operation_id is null then null else public.training_receipt(t) end;
  end if;
  if action not in ('reserve','complete','release') or op is null then
    raise sqlstate 'PT422' using message='training_invalid_request'; end if;
  -- Same advisory/season/participant ordering as accepted-save registration.
  -- In particular, no guard can be checked before waiting behind a reservation.
  select s.metadata->'save_identity' into identity from public.season_players sp
    join public.save_files s on s.id=sp.current_save_file_id where sp.season_id=sid and sp.trainer_id=tid;
  if identity is not null then perform pg_advisory_xact_lock(hashtextextended(sid::text||identity::text,0)); end if;
  perform 1 from public.seasons where id=sid for share;
  perform 1 from public.season_players where season_id=sid and trainer_id=tid for update;
  if not found then raise sqlstate 'PT403' using message='training_participant_required'; end if;
  select * into t from public.training_operations where operation_id=op for update;
  if found and (t.season_id<>sid or t.trainer_id<>tid) then
    raise sqlstate 'PT404' using message='training_not_found'; end if;
  if action='release' then
    if t.operation_id is null then raise sqlstate 'PT404' using message='training_not_found'; end if;
    if t.status='APPLIED' then raise sqlstate 'PT409' using message='training_already_applied'; end if;
    update public.training_operations set status='RELEASED',finished_at=coalesce(finished_at,clock_timestamp())
      where operation_id=op returning * into t;
    return public.training_receipt(t);
  end if;
  if action='reserve' and t.operation_id is not null then
    if t.request_hash is distinct from r->>'request_hash' then
      raise sqlstate 'PT409' using message='training_idempotency_conflict'; end if;
    return public.training_receipt(t);
  end if;
  if action='complete' then
    if t.operation_id is null then raise sqlstate 'PT404' using message='training_not_found'; end if;
    if t.status='APPLIED' then
      if t.output_sha256 is distinct from r->>'output_sha256' then
        raise sqlstate 'PT409' using message='training_idempotency_conflict'; end if;
      return public.training_receipt(t);
    end if;
    if t.status<>'RESERVED' then raise sqlstate 'PT409' using message='training_not_reserved'; end if;
  end if;
  c=public.training_context(sid,tid);
  perform public.training_assert_available(sid,tid);
  if action='reserve' then
    -- The owner explicitly authorizes old paid virtual purchases to be used on
    -- the current linked save. Original purchase/season/price/ledger stay intact.
    select * into p from public.purchases where id=(r->>'purchase_id')::uuid and trainer_id=tid for update;
    select i.code into code from public.shop_items i where i.id=p.shop_item_id;
    if p.id is null or p.status<>'pending' or p.quantity<>1 or p.acquisition_type<>'paid'
      or code not in ('menta_naturaleza','chapa_plateada','chapa_dorada') then
      raise sqlstate 'PT409' using message='training_purchase_unavailable'; end if;
    if exists(select 1 from public.training_operations where purchase_id=p.id and status<>'RELEASED')
      or exists(select 1 from public.item_deliveries where purchase_id=p.id and status<>'RELEASED')
      or exists(select 1 from public.training_operations where season_id=sid and trainer_id=tid and status='RESERVED') then
      raise sqlstate 'PT409' using message='training_save_busy'; end if;
    select x into o from jsonb_array_elements(c->'observations') x
      where x->>'pokemon_entity_id'=r->>'pokemon_entity_id';
    m=r->'intent'->'mutation';
    if o is null or r->>'save_file_id' is distinct from c#>>'{save,id}'
      or r->>'identity_revision_id' is distinct from c#>>'{revision,id}'
      or r#>>'{intent,expected_sha256}' is distinct from c#>>'{save,sha256}'
      or m->>'item_code' is distinct from code or m->>'kind'<>'virtual_training'
      or m->>'attempt' is distinct from op::text
      or m->>'location' is distinct from o->>'source'
      or (m->>'slot_index')::int is distinct from (o->>'slot_number')::int-1
      or (m->>'box_index')::int is distinct from (case when o->>'source'='box' then (o->>'box_number')::int-1 else null end)
      or r->>'request_hash' !~ '^[a-f0-9]{64}$' then
      raise sqlstate 'PT409' using message='training_source_changed'; end if;
    insert into public.training_operations(operation_id,purchase_id,purchase_season_id,season_id,trainer_id,pokemon_entity_id,
      save_file_id,identity_revision_id,request_hash,intent,status)
      values(op,p.id,p.season_id,sid,tid,(r->>'pokemon_entity_id')::uuid,(r->>'save_file_id')::uuid,
        (r->>'identity_revision_id')::uuid,r->>'request_hash',r->'intent','RESERVED') returning * into t;
    return public.training_receipt(t);
  end if;
  if c#>>'{save,id}' is distinct from t.save_file_id::text
    or c#>>'{revision,id}' is distinct from t.identity_revision_id::text
    or c#>>'{save,sha256}' is distinct from t.intent->>'expected_sha256'
    or r->>'output_sha256' is null or r->>'output_sha256' !~ '^[a-f0-9]{64}$'
    or r->>'output_sha256'=t.intent->>'expected_sha256'
    or not exists(select 1 from jsonb_array_elements(c->'observations') q
      where q->>'pokemon_entity_id'=t.pokemon_entity_id::text) then
    raise sqlstate 'PT409' using message='training_source_changed'; end if;
  select * into p from public.purchases where id=t.purchase_id for update;
  select * into e from public.pokemon_entities where id=t.pokemon_entity_id and season_id=sid and owner_trainer_id=tid for update;
  before=r->'before_evidence'; after=r->'after_evidence'; observed=r->'observed_evidence';
  if p.status<>'pending' or e.identity_status<>'unambiguous'
    or e.initial_evidence is distinct from before
    or (before-'ivs'-'source_trainer_match') is distinct from (after-'ivs'-'source_trainer_match')
    or before->'source_trainer_match' is distinct from after->'source_trainer_match'
    or (after-'source_trainer_match') is distinct from (observed-'source_trainer_match')
    or (observed->'source_trainer_match' is distinct from 'true'::jsonb
        and not public.transfer_identity_proven(e.id,tid,before))
    or after->>'schema_version'<>'2' or r->>'after_candidate_key' !~ '^[a-f0-9]{64}$'
    or r#>>'{registration,sha256}' is distinct from r->>'output_sha256'
    or r#>>'{registration,expected_save_id}' is distinct from t.save_file_id::text
    or not exists(select 1 from jsonb_array_elements(r#>'{registration,identity_plan,bindings}') b
      where b->>'pokemon_entity_id'=e.id::text and b->>'outcome'='MATCHED'
        and b->'evidence'=observed and b->>'candidate_key'=r->>'observed_candidate_key') then
    raise sqlstate 'PT409' using message='training_verification_required'; end if;
  -- Audited current identity transition, same UUID/owner/flags. Every older
  -- observation, snapshot and original evidence is retained unchanged.
  update public.training_operations set before_evidence=before,after_evidence=after,
    before_candidate_key=e.candidate_key,after_candidate_key=r->>'after_candidate_key',
    output_sha256=r->>'output_sha256',status='APPLIED',finished_at=clock_timestamp(),result=r->'result'
    where operation_id=op returning * into t;
  update public.pokemon_entities set initial_evidence=after,candidate_key=r->>'after_candidate_key',updated_at=now()
    where id=e.id;
  registration=public.api_register_save((r->'registration')||jsonb_build_object('operation','register'));
  update public.purchases set status='used' where id=p.id;
  v_result=coalesce(r->'result','{}'::jsonb)||jsonb_build_object('registration',registration);
  update public.training_operations set result=v_result where operation_id=op returning * into t;
  insert into public.activity_events(season_id,type,actor_trainer_id,trainer_id,visibility,dedupe_key,payload)
    values(sid,'VIRTUAL_TRAINING_APPLIED',tid,tid,'owner','virtual_training:'||op::text,
      jsonb_build_object('operation_id',op,'purchase_id',p.id,'purchase_season_id',p.season_id,'pokemon_entity_id',e.id,
        'save_file_id',t.save_file_id,'output_sha256',t.output_sha256,'mutation',t.intent->'mutation'));
  return public.training_receipt(t);
end $$;

create function public.training_guard_competing_write() returns trigger
language plpgsql security definer set search_path='' as $$
begin
  perform 1 from public.season_players where season_id=new.season_id and trainer_id=new.trainer_id for update;
  if exists(select 1 from public.training_operations where season_id=new.season_id
    and trainer_id=new.trainer_id and status='RESERVED') then
    raise sqlstate 'PT409' using message='training_save_busy'; end if;
  return new;
end $$;
create trigger training_guards_team_lock before insert or update on public.team_locks
  for each row execute function public.training_guard_competing_write();
create trigger training_guards_item_use before insert or update on public.item_use_authorizations
  for each row execute function public.training_guard_competing_write();
create trigger training_guards_transfer_leg before insert or update on public.item_use_transfer_legs
  for each row execute function public.training_guard_competing_write();

-- An active physical operation owns its exact save until independently verified
-- completion. Normal auto-sync cannot create a new/ambiguous entity meanwhile.
alter function public.api_register_save(jsonb) rename to api_register_save_v073;
create function public.api_register_save(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
begin
  if p_request->>'operation'='register' then
    perform pg_advisory_xact_lock(hashtextextended((p_request->>'season_id')||(p_request->'save_identity')::text,0));
    perform 1 from public.seasons where id=(p_request->>'season_id')::uuid for share;
    perform 1 from public.season_players where season_id=(p_request->>'season_id')::uuid
      and trainer_id=(p_request->>'trainer_id')::uuid for update;
    if exists(select 1 from public.training_operations where season_id=(p_request->>'season_id')::uuid
      and trainer_id=(p_request->>'trainer_id')::uuid and status='RESERVED') then
      raise sqlstate 'PT409' using message='training_reconciliation_required'; end if;
  end if;
  return public.api_register_save_v073(p_request);
end $$;

-- A proven foreign-OT transfer stays the same entity after audited IV training.
-- Original immutable transfer provenance is compared with the first retained
-- before-evidence; the incoming bytes must equal the CURRENT authorized identity.
create or replace function public.transfer_identity_proven(p_entity uuid,p_trainer uuid,p_evidence jsonb) returns boolean
language sql stable security definer set search_path='' as $$
 select exists(select 1 from public.transfer_provenance p join public.pokemon_entities e on e.id=p.pokemon_entity_id
  join public.item_use_transfers x on x.authorization_id=p.authorization_id
  where e.id=p_entity and e.owner_trainer_id=p_trainer and p.recipient_id=p_trainer
    and (x.terminal='COMMITTED' or x.adjudicated_at is not null
      or exists(select 1 from public.transfer_commit_permits c where c.txid=txid_current() and c.authorization_id=p.authorization_id))
    and e.identity_status='unambiguous'
    and (e.initial_evidence-'source_trainer_match')=(p_evidence-'source_trainer_match')
    and p.evidence=coalesce((select t.before_evidence from public.training_operations t
      where t.pokemon_entity_id=e.id and t.trainer_id=p_trainer and t.status='APPLIED'
        and t.reserved_at>=p.created_at order by t.reserved_at limit 1),e.initial_evidence))
$$;

alter function public.api_reserve_item_delivery(uuid,uuid,uuid,uuid,text,integer,text) rename to api_reserve_item_delivery_v073;
create function public.api_reserve_item_delivery(p_season_id uuid,p_trainer_id uuid,p_purchase_id uuid,p_operation_id uuid,
  p_item_code text,p_game_item_id integer,p_game text) returns jsonb
language plpgsql security invoker set search_path='' as $$
begin
  perform 1 from public.season_players where season_id=p_season_id and trainer_id=p_trainer_id for update;
  if exists(select 1 from public.purchases p join public.shop_items i on i.id=p.shop_item_id
    where p.id=p_purchase_id and i.code in ('menta_naturaleza','chapa_plateada','chapa_dorada')) then
    raise sqlstate 'PT409' using message='delivery_not_supported'; end if;
  if exists(select 1 from public.training_operations where season_id=p_season_id and trainer_id=p_trainer_id and status='RESERVED') then
    raise sqlstate 'PT409' using message='delivery_in_progress'; end if;
  return public.api_reserve_item_delivery_v073(p_season_id,p_trainer_id,p_purchase_id,p_operation_id,p_item_code,p_game_item_id,p_game);
end $$;

create function public.training_guard_purchase_status() returns trigger
language plpgsql security definer set search_path='' as $$
begin
  if new.status is distinct from old.status and exists(select 1 from public.training_operations
    where purchase_id=old.id and status='RESERVED') then
    raise exception 'purchase_linked_to_save_operation'; end if;
  return new;
end $$;
create trigger training_guards_purchase_status before update of status on public.purchases
  for each row execute function public.training_guard_purchase_status();

-- Reuse the existing cancellation/physical-operation count and protect the
-- context until reconciliation. A pending physical write must not be stranded
-- by retirement, a dead-box change, unlinking or a season/day transition.
alter function public.lifecycle_physical_counts(uuid) rename to lifecycle_physical_counts_v073;
create function public.lifecycle_physical_counts(sid uuid) returns jsonb
language sql stable security definer set search_path='' as $$
 select jsonb_set(c,'{open_item_uses}',to_jsonb((c->>'open_item_uses')::bigint+
   (select count(*) from public.training_operations where season_id=sid and status='RESERVED')))
 from (select public.lifecycle_physical_counts_v073(sid) c) q
$$;

create function public.training_guard_context_transition() returns trigger
language plpgsql security definer set search_path='' as $$
declare sid uuid; tid uuid;
begin
  if tg_table_name='season_players' then
    sid=old.season_id; tid=old.trainer_id;
    if new.status is not distinct from old.status and new.dead_box_number=old.dead_box_number
      and new.current_save_file_id is not distinct from old.current_save_file_id then return new; end if;
  elsif tg_table_name='seasons' then
    sid=old.id;
    if new.status is not distinct from old.status then return new; end if;
  else
    sid=old.season_id;
    if new.status is not distinct from old.status then return new; end if;
  end if;
  if exists(select 1 from public.training_operations where season_id=sid and status='RESERVED'
    and (tid is null or trainer_id=tid)) then
    raise sqlstate 'PT409' using message='training_save_busy'; end if;
  return new;
end $$;
create trigger training_guards_player_context before update of status,dead_box_number,current_save_file_id on public.season_players
  for each row execute function public.training_guard_context_transition();
create trigger training_guards_season_context before update of status on public.seasons
  for each row execute function public.training_guard_context_transition();
create trigger training_guards_matchday_context before update of status on public.matchdays
  for each row execute function public.training_guard_context_transition();

alter function public.admin_incident_read(uuid,uuid) rename to admin_incident_read_v073;
create function public.admin_incident_read(p_actor uuid,p_season uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare result jsonb; rows jsonb;
begin
  result=public.admin_incident_read_v073(p_actor,p_season);
  select coalesce(jsonb_agg(case when exists(select 1 from public.training_operations t
    where t.purchase_id=(p->>'id')::uuid and t.status='RESERVED') then
      p||jsonb_build_object('linked_operation',true,'cancellable',false,'refundable',false) else p end),'[]'::jsonb)
    into rows from jsonb_array_elements(result->'purchases') p;
  return jsonb_set(result,'{purchases}',rows);
end $$;

alter function public.admin_purchase_resolve(uuid,uuid,uuid,text,uuid,text,text) rename to admin_purchase_resolve_v073;
create function public.admin_purchase_resolve(p_actor uuid,p_season uuid,p_purchase uuid,p_kind text,p_operation uuid,p_hash text,p_reason text)
returns jsonb language plpgsql security definer set search_path='' as $$
begin
  perform public.admin_incident_actor(p_actor);
  if exists(select 1 from public.training_operations where purchase_id=p_purchase and status='RESERVED') then
    raise exception 'purchase_linked_to_save_operation'; end if;
  return public.admin_purchase_resolve_v073(p_actor,p_season,p_purchase,p_kind,p_operation,p_hash,p_reason);
end $$;

do $$ declare f regprocedure; begin
  for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and p.proname in ('training_receipt','training_context','training_assert_available','training_guard_competing_write',
      'api_training_operation','api_register_save','api_register_save_v073','transfer_identity_proven',
      'api_reserve_item_delivery','api_reserve_item_delivery_v073','admin_purchase_resolve','admin_purchase_resolve_v073',
      'training_guard_purchase_status','training_guard_context_transition','lifecycle_physical_counts','lifecycle_physical_counts_v073',
      'admin_incident_read','admin_incident_read_v073') loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
