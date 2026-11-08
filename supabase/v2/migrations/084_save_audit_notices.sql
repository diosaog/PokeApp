-- 084: Administración › Avisos. Compares each accepted League save with its
-- predecessor against the server's record of authorized operations and keeps
-- notices for the administrator to judge. Strictly informative and additive:
-- nothing here reads or changes points, coins, deaths, combats, Team Lock,
-- purchases or any save; no notice blocks or sanctions anything. A notice is a
-- suspicion, never a verdict: comparing saves cannot prove where a change came
-- from. Service-only functions; the tables are not reachable by any other role.
begin;

-- The reference starts here. Saves registered before this moment are never
-- analysed, only used as the starting point of the first comparison, so no
-- suspicion is invented about anything that predates the system.
create table public.save_audit_config (
  singleton boolean primary key default true check (singleton),
  activated_at timestamptz not null default clock_timestamp()
);
insert into public.save_audit_config default values;

-- One analysis per accepted save: replays and retries find it and stop here.
create table public.save_audit_runs (
  save_file_id uuid primary key references public.save_files(id),
  season_id uuid not null references public.seasons(id),
  trainer_id uuid not null references public.trainers(id),
  previous_save_file_id uuid references public.save_files(id),
  status text not null check (status in ('baseline','analyzed')),
  detector_version integer not null check (detector_version>0),
  inventory_status text not null check (inventory_status in ('baseline','compared','no_baseline','unavailable')),
  bag jsonb check (bag is null or jsonb_typeof(bag)='object'),
  friendship jsonb check (friendship is null or jsonb_typeof(friendship)='object'),
  credited_deliveries uuid[] not null default '{}',
  notice_count integer not null default 0 check (notice_count>=0),
  analyzed_at timestamptz not null default clock_timestamp(),
  foreign key (save_file_id,season_id,trainer_id) references public.save_files(id,season_id,trainer_id)
);
create index save_audit_runs_trainer on public.save_audit_runs(season_id,trainer_id,analyzed_at desc);

create table public.save_audit_notices (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id),
  trainer_id uuid not null references public.trainers(id),
  save_file_id uuid not null references public.save_files(id),
  previous_save_file_id uuid references public.save_files(id),
  group_key text not null check (length(group_key) between 1 and 160),
  game text not null check (length(game) between 1 and 24),
  category text not null check (category in ('pokemon','objetos','origen')),
  severity text not null check (severity in ('alta','media','baja')),
  status text not null default 'pending' check (status in ('pending','reviewed','justified','confirmed')),
  title text not null check (length(title) between 1 and 200),
  summary text not null check (length(summary) between 1 and 1000),
  origin text not null check (length(origin) between 1 and 80),
  pokemon jsonb check (pokemon is null or jsonb_typeof(pokemon)='object'),
  changes jsonb not null check (jsonb_typeof(changes)='array' and jsonb_array_length(changes)>0),
  operations jsonb not null default '[]'::jsonb check (jsonb_typeof(operations)='array'),
  compared jsonb not null default '{}'::jsonb check (jsonb_typeof(compared)='object'),
  detector_version integer not null check (detector_version>0),
  created_at timestamptz not null default clock_timestamp(),
  updated_at timestamptz not null default clock_timestamp(),
  -- The same change of the same save can never be noticed twice.
  unique (save_file_id,group_key),
  foreign key (save_file_id,season_id,trainer_id) references public.save_files(id,season_id,trainer_id)
);
create index save_audit_notices_season on public.save_audit_notices(season_id,created_at desc);

-- The administrative history is append-only: every status or note, reopenings
-- included, is a new row. Nothing here touches a save or the points.
create table public.save_audit_notice_events (
  operation_id uuid primary key,
  notice_id uuid not null references public.save_audit_notices(id),
  season_id uuid not null references public.seasons(id),
  actor_trainer_id uuid not null references public.trainers(id),
  from_status text not null check (from_status in ('pending','reviewed','justified','confirmed')),
  to_status text not null check (to_status in ('pending','reviewed','justified','confirmed')),
  note text not null default '' check (length(note)<=1000),
  request_hash text not null check (request_hash ~ '^[a-f0-9]{64}$'),
  created_at timestamptz not null default clock_timestamp()
);
create index save_audit_events_notice on public.save_audit_notice_events(notice_id,created_at);

create function public.save_audit_immutable() returns trigger
language plpgsql set search_path=pg_catalog as $$
begin raise exception 'save_audit_immutable'; end $$;

create function public.save_audit_notice_guard() returns trigger
language plpgsql set search_path=pg_catalog as $$
begin
  -- Only the administrative state moves; the evidence never changes.
  if (to_jsonb(new)-'status'-'updated_at') is distinct from (to_jsonb(old)-'status'-'updated_at') then
    raise exception 'save_audit_immutable';
  end if;
  return new;
end $$;

create trigger save_audit_runs_immutable before update or delete on public.save_audit_runs
  for each row execute function public.save_audit_immutable();
create trigger save_audit_runs_no_truncate before truncate on public.save_audit_runs
  for each statement execute function public.save_audit_immutable();
create trigger save_audit_events_immutable before update or delete on public.save_audit_notice_events
  for each row execute function public.save_audit_immutable();
create trigger save_audit_events_no_truncate before truncate on public.save_audit_notice_events
  for each statement execute function public.save_audit_immutable();
create trigger save_audit_notices_guard before update on public.save_audit_notices
  for each row execute function public.save_audit_notice_guard();
create trigger save_audit_notices_no_delete before delete on public.save_audit_notices
  for each row execute function public.save_audit_immutable();
create trigger save_audit_notices_no_truncate before truncate on public.save_audit_notices
  for each statement execute function public.save_audit_immutable();
create trigger save_audit_config_immutable before update or delete on public.save_audit_config
  for each row execute function public.save_audit_immutable();
create trigger save_audit_config_no_truncate before truncate on public.save_audit_config
  for each statement execute function public.save_audit_immutable();

do $$ declare t text; begin
  foreach t in array array['save_audit_config','save_audit_runs','save_audit_notices','save_audit_notice_events'] loop
    execute format('alter table public.%I enable row level security',t);
    execute format('alter table public.%I force row level security',t);
    execute format('revoke all on public.%I from public,anon,authenticated,service_role',t);
  end loop;
end $$;

-- Accepted saves still waiting for their comparison, in chain order.
create function public.save_audit_pending(p_season uuid,p_trainer uuid,p_limit integer) returns jsonb
language sql stable security definer set search_path='' as $$
  select coalesce(jsonb_agg(q order by q.season_id,q.trainer_id,q.revision_number),'[]'::jsonb) from (
    select r.season_id,r.trainer_id,r.save_file_id,r.revision_number
    from public.pokemon_identity_revisions r
    where r.created_at>=(select c.activated_at from public.save_audit_config c)
      and not exists(select 1 from public.save_audit_runs a where a.save_file_id=r.save_file_id)
      and (p_season is null or r.season_id=p_season)
      and (p_trainer is null or r.trainer_id=p_trainer)
    order by r.season_id,r.trainer_id,r.revision_number
    limit greatest(least(coalesce(p_limit,40),200),1)
  ) q
$$;

create function public.save_audit_save_row(s public.save_files) returns jsonb
language sql stable security definer set search_path='' as $$
  select jsonb_build_object('id',s.id,'season_id',s.season_id,'trainer_id',s.trainer_id,
    'sha256',s.sha256,'uploaded_at',s.uploaded_at,'storage_bucket',s.storage_bucket,'storage_key',s.storage_key)
$$;

-- Both saves of one comparison and the server's own record of what PokeApp
-- authorized. Local Launcher records are never consulted.
create function public.save_audit_context(p_season uuid,p_trainer uuid,p_save uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare
  r public.pokemon_identity_revisions; prev public.pokemon_identity_revisions;
  c public.save_files; p public.save_files; run public.save_audit_runs;
  current_payload jsonb; previous_payload jsonb;
begin
  select * into r from public.pokemon_identity_revisions
    where save_file_id=p_save and season_id=p_season and trainer_id=p_trainer;
  if not found then raise exception 'save_audit_unknown_save'; end if;
  select * into c from public.save_files where id=p_save;
  select q.payload into current_payload from public.parsed_saves q where q.id=r.parsed_save_id;
  if r.predecessor_id is not null then
    select * into prev from public.pokemon_identity_revisions where id=r.predecessor_id;
    select * into p from public.save_files where id=prev.save_file_id;
    select q.payload into previous_payload from public.parsed_saves q where q.id=prev.parsed_save_id;
    select * into run from public.save_audit_runs where save_file_id=prev.save_file_id;
  end if;
  return jsonb_build_object(
    'current',jsonb_build_object('save',public.save_audit_save_row(c),'payload',current_payload,
      'revision',r.revision_number),
    'previous',case when prev.id is null then null else jsonb_build_object(
      'save',public.save_audit_save_row(p),'payload',previous_payload,'revision',prev.revision_number,
      'bag',run.bag,'friendship',run.friendship) end,
    'operations',jsonb_build_object(
      'training',coalesce((select jsonb_agg(jsonb_build_object('operation_id',t.operation_id,
          'finished_at',t.finished_at,'item_code',t.intent#>>'{mutation,item_code}',
          'stat',t.intent#>>'{mutation,stat}','nature_id',t.intent#>>'{mutation,nature_id}',
          'pid',t.before_evidence->'pid','ec',t.before_evidence->'encryption_constant'))
        from public.training_operations t
        where t.season_id=p_season and t.trainer_id=p_trainer and t.status='APPLIED'),'[]'::jsonb),
      'deliveries',coalesce((select jsonb_agg(jsonb_build_object('id',d.id,'purchase_id',d.purchase_id,
          'item_code',d.item_code,'game_item_id',d.game_item_id,'status',d.status,
          'reserved_at',d.reserved_at,'finished_at',d.finished_at,
          'item_name',(select i.name from public.purchases q join public.shop_items i on i.id=q.shop_item_id where q.id=d.purchase_id)))
        from public.item_deliveries d
        where d.season_id=p_season and d.trainer_id=p_trainer and d.kind='bag'
          and d.status in ('RESERVED','DELIVERED')),'[]'::jsonb),
      'transfers_in',coalesce((select jsonb_agg(jsonb_build_object('pid',pv.evidence->'pid',
          'ec',pv.evidence->'encryption_constant'))
        from public.transfer_provenance pv join public.item_use_transfers x on x.authorization_id=pv.authorization_id
        where pv.season_id=p_season and pv.recipient_id=p_trainer
          and (x.terminal='COMMITTED' or x.adjudicated_at is not null)),'[]'::jsonb),
      'credited',coalesce((select jsonb_agg(distinct d::text)
        from public.save_audit_runs a cross join lateral unnest(a.credited_deliveries) d
        where a.season_id=p_season and a.trainer_id=p_trainer),'[]'::jsonb)));
end $$;

create function public.save_audit_record(p_request jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare
  sid uuid=(p_request->>'season_id')::uuid;
  tid uuid=(p_request->>'trainer_id')::uuid;
  save_id uuid=(p_request->>'save_file_id')::uuid;
  previous_id uuid=(p_request->>'previous_save_file_id')::uuid;
  item jsonb;
  inserted integer=0;
begin
  if sid is null or tid is null or save_id is null
     or jsonb_typeof(p_request->'notices') is distinct from 'array' then
    raise exception 'invalid_audit_record'; end if;
  insert into public.save_audit_runs(save_file_id,season_id,trainer_id,previous_save_file_id,status,
    detector_version,inventory_status,bag,friendship,credited_deliveries,notice_count)
  values(save_id,sid,tid,previous_id,p_request->>'status',(p_request->>'detector_version')::integer,
    p_request->>'inventory_status',nullif(p_request->'bag','null'::jsonb),nullif(p_request->'friendship','null'::jsonb),
    array(select value::uuid from jsonb_array_elements_text(coalesce(p_request->'credited_deliveries','[]'::jsonb))),
    jsonb_array_length(p_request->'notices'))
  on conflict (save_file_id) do nothing;
  if not found then
    return jsonb_build_object('save_file_id',save_id,'recorded',false,'notices',0);
  end if;
  for item in select value from jsonb_array_elements(p_request->'notices') loop
    insert into public.save_audit_notices(season_id,trainer_id,save_file_id,previous_save_file_id,group_key,
      game,category,severity,title,summary,origin,pokemon,changes,operations,compared,detector_version)
    values(sid,tid,save_id,previous_id,item->>'group_key',p_request->>'game',item->>'category',item->>'severity',
      item->>'title',item->>'summary',item->>'origin',nullif(item->'pokemon','null'::jsonb),item->'changes',
      item->'operations',coalesce(item->'compared','{}'::jsonb),(p_request->>'detector_version')::integer)
    on conflict (save_file_id,group_key) do nothing;
    if found then inserted:=inserted+1; end if;
  end loop;
  return jsonb_build_object('save_file_id',save_id,'recorded',true,'notices',inserted);
end $$;

create function public.save_audit_notice_json(n public.save_audit_notices) returns jsonb
language sql stable security definer set search_path='' as $$
  select jsonb_build_object('id',n.id,'season_id',n.season_id,'trainer_id',n.trainer_id,
    'display_name',(select t.display_name from public.trainers t where t.id=n.trainer_id),
    'game',n.game,'detected_at',n.created_at,'updated_at',n.updated_at,'category',n.category,
    'severity',n.severity,'status',n.status,'title',n.title,'summary',n.summary,'origin',n.origin,
    'pokemon',n.pokemon,'changes',n.changes,'operations',n.operations,'compared',n.compared,
    'detector_version',n.detector_version,
    'events',coalesce((select jsonb_agg(jsonb_build_object('at',e.created_at,
        'actor',(select t.display_name from public.trainers t where t.id=e.actor_trainer_id),
        'from_status',e.from_status,'to_status',e.to_status,'note',e.note) order by e.created_at)
      from public.save_audit_notice_events e where e.notice_id=n.id),'[]'::jsonb))
$$;

create function public.admin_save_audit_read(p_actor uuid,p_season uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare s public.seasons; started timestamptz;
begin
  perform public.admin_incident_actor(p_actor);
  select * into s from public.seasons where id=p_season;
  if not found then raise exception 'season_not_found'; end if;
  select activated_at into started from public.save_audit_config limit 1;
  return jsonb_build_object('season_id',s.id,'season_status',s.status,'activated_at',started,
    'pending_saves',(select count(*) from public.pokemon_identity_revisions r where r.season_id=s.id
      and r.created_at>=started
      and not exists(select 1 from public.save_audit_runs a where a.save_file_id=r.save_file_id)),
    'analyzed_saves',(select count(*) from public.save_audit_runs a where a.season_id=s.id and a.status='analyzed'),
    'last_analyzed_at',(select max(a.analyzed_at) from public.save_audit_runs a where a.season_id=s.id),
    'trainers',coalesce((select jsonb_agg(jsonb_build_object('trainer_id',sp.trainer_id,
        'display_name',t.display_name) order by t.display_name)
      from public.season_players sp join public.trainers t on t.id=sp.trainer_id where sp.season_id=s.id),'[]'::jsonb),
    'notices',coalesce((select jsonb_agg(public.save_audit_notice_json(n) order by n.created_at desc)
      from (select * from public.save_audit_notices q where q.season_id=s.id
            order by q.created_at desc limit 500) n),'[]'::jsonb));
end $$;

-- The sidebar counter: cheap and polled, so it never loads the notices.
create function public.admin_save_audit_summary(p_actor uuid,p_season uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
begin
  perform public.admin_incident_actor(p_actor);
  return jsonb_build_object('season_id',p_season,
    'pending',(select count(*) from public.save_audit_notices n where n.season_id=p_season and n.status='pending'),
    'pending_high',(select count(*) from public.save_audit_notices n where n.season_id=p_season and n.status='pending' and n.severity='alta'));
end $$;

create function public.admin_save_audit_update(p_actor uuid,p_season uuid,p_notice uuid,p_status text,
  p_note text,p_operation uuid,p_hash text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare n public.save_audit_notices; e public.save_audit_notice_events; note_text text=btrim(coalesce(p_note,''));
begin
  perform public.admin_incident_actor(p_actor);
  if p_operation is null or p_hash is null or p_hash !~ '^[a-f0-9]{64}$'
     or p_status is null or p_status not in ('pending','reviewed','justified','confirmed')
     or length(note_text)>1000 then
    raise exception 'invalid_notice_request'; end if;
  select * into n from public.save_audit_notices where id=p_notice and season_id=p_season for update;
  if not found then raise exception 'notice_not_found'; end if;
  select * into e from public.save_audit_notice_events where operation_id=p_operation;
  if found then
    if e.notice_id<>p_notice or e.actor_trainer_id<>p_actor or e.request_hash<>p_hash then
      raise exception 'idempotency_conflict'; end if;
    return public.save_audit_notice_json(n)||jsonb_build_object('replayed',true);
  end if;
  -- Deciding something needs a word about why; an observation alone is also valid.
  if p_status in ('justified','confirmed') and length(note_text)<3 then
    raise exception 'notice_note_required'; end if;
  if p_status=n.status and length(note_text)=0 then
    raise exception 'notice_note_required'; end if;
  insert into public.save_audit_notice_events(operation_id,notice_id,season_id,actor_trainer_id,from_status,to_status,note,request_hash)
    values(p_operation,n.id,p_season,p_actor,n.status,p_status,note_text,p_hash);
  update public.save_audit_notices set status=p_status,updated_at=clock_timestamp() where id=n.id returning * into n;
  return public.save_audit_notice_json(n)||jsonb_build_object('replayed',false);
end $$;

do $$ declare f regprocedure; begin
  foreach f in array array[
    'public.save_audit_pending(uuid,uuid,integer)'::regprocedure,
    'public.save_audit_context(uuid,uuid,uuid)'::regprocedure,
    'public.save_audit_record(jsonb)'::regprocedure,
    'public.admin_save_audit_read(uuid,uuid)'::regprocedure,
    'public.admin_save_audit_summary(uuid,uuid)'::regprocedure,
    'public.admin_save_audit_update(uuid,uuid,uuid,text,text,uuid,text)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
  foreach f in array array[
    'public.save_audit_save_row(public.save_files)'::regprocedure,
    'public.save_audit_notice_json(public.save_audit_notices)'::regprocedure,
    'public.save_audit_immutable()'::regprocedure,
    'public.save_audit_notice_guard()'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
  end loop;
end $$;

comment on table public.save_audit_notices is
  'Administración › Avisos: informative suspicions from comparing successive saves. Never blocks, sanctions or changes anything; status is purely administrative.';
notify pgrst,'reload schema';
commit;
