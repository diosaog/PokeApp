-- Phase 8J: explicit completion, frozen relational provenance, non-destructive discard.
begin;

alter table public.season_archive_snapshots
  add column source_snapshot_revision_id uuid references public.matchday_snapshot_revisions(id),
  add column checksum text check (checksum ~ '^[0-9a-f]{64}$'),
  add column label text check (length(btrim(label)) between 1 and 120),
  add constraint archive_provenance_complete check (
    (source_snapshot_revision_id is null and checksum is null and label is null) or
    (source_snapshot_revision_id is not null and checksum is not null and label is not null));
alter table public.hall_of_fame_entries
  add column archive_snapshot_id uuid references public.season_archive_snapshots(id),
  add column source_snapshot_revision_id uuid references public.matchday_snapshot_revisions(id),
  add column source_team_lock_id uuid references public.team_locks(id),
  add constraint hall_archive_provenance check (
    (archive_snapshot_id is null and source_snapshot_revision_id is null and source_team_lock_id is null) or
    (competition_type='league' and archive_snapshot_id is not null and source_snapshot_revision_id is not null));

revoke insert,update,delete on public.season_archive_snapshots,public.hall_of_fame_entries from public,anon,authenticated;
do $$ declare t text; c text; begin
  foreach t in array array['season_archive_snapshots','hall_of_fame_entries'] loop
    select string_agg(quote_ident(attname),',') into c from pg_attribute
      where attrelid=('public.'||t)::regclass and attnum>0 and not attisdropped;
    execute format('revoke insert (%s),update (%s) on public.%I from public,anon,authenticated',c,c,t);
  end loop;
end $$;

create function public.lifecycle_artifact_immutable() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  if new is distinct from old then perform public.admin_setup_fail('historical_artifact_immutable'); end if;
  return new;
end $$;
create trigger archive_immutable before update on public.season_archive_snapshots
  for each row execute function public.lifecycle_artifact_immutable();
create trigger hall_immutable before update on public.hall_of_fame_entries
  for each row execute function public.lifecycle_artifact_immutable();

-- Re-project rather than copy arbitrary JSON, including nested move metadata.
create function public.lifecycle_public_team(team jsonb) returns jsonb
language plpgsql immutable security invoker set search_path=pg_catalog,public as $$
declare mon jsonb; safe jsonb; result jsonb='[]'; k text;
begin
  if jsonb_typeof(team) is distinct from 'array' then return '[]'; end if;
  if jsonb_array_length(team)<>6 then return '[]'; end if;
  for mon in select value from jsonb_array_elements(team) loop
    if jsonb_typeof(mon->'species') is distinct from 'string' or length(btrim(mon->>'species'))=0 then return '[]'; end if;
    safe='{}';
    foreach k in array array['species','nickname','gender','item','sprite_url','form_name'] loop
      if jsonb_typeof(mon->k)='string' then safe=safe||jsonb_build_object(k,mon->k); end if;
    end loop;
    foreach k in array array['level','form_index'] loop
      if jsonb_typeof(mon->k)='number' and mon->>k ~ '^[0-9]+$' then safe=safe||jsonb_build_object(k,mon->k); end if;
    end loop;
    if jsonb_typeof(mon->'is_shiny')='boolean' then safe=safe||jsonb_build_object('is_shiny',mon->'is_shiny'); end if;
    if jsonb_typeof(mon->'types')='array' then
      safe=safe||jsonb_build_object('types',(select coalesce(jsonb_agg(value order by ord),'[]') from
        jsonb_array_elements(mon->'types') with ordinality a(value,ord) where ord<=2 and jsonb_typeof(value)='string'));
    end if;
    if jsonb_typeof(mon->'moves')='array' then
      safe=safe||jsonb_build_object('moves',(select coalesce(jsonb_agg(jsonb_build_object('name',value->>'name') order by ord),'[]')
        from jsonb_array_elements(mon->'moves') with ordinality a(value,ord)
        where ord<=4 and jsonb_typeof(value->'name')='string'));
    end if;
    result=result||jsonb_build_array(safe);
  end loop;
  return result;
end $$;

create function public.lifecycle_standings(sid uuid, rows_json jsonb) returns jsonb
language sql stable security invoker set search_path=pg_catalog,public as $$
  select coalesce(jsonb_agg(jsonb_build_object('season_player_id',p.id,'trainer_id',p.trainer_id,
    'position',(r->>'position')::integer,'division',r->>'division_id',
    'division_position',(r->>'division_position')::integer,'score',(r->>'score')::numeric,
    'points_awarded',(r->>'points_awarded')::integer,'coins_awarded',(r->>'coins_awarded')::integer)
    order by (r->>'position')::integer),'[]')
  from jsonb_array_elements(rows_json) r join public.season_players p on p.id=(r->>'trainer_id')::uuid and p.season_id=sid
$$;

create function public.lifecycle_final_source(sid uuid) returns public.matchday_snapshot_revisions
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare finalday public.matchdays; cfg public.season_config_versions; d public.matchdays;
  snap public.matchday_snapshots; history public.matchday_snapshot_revisions; result public.matchday_snapshot_revisions;
  row jsonb; n integer;
begin
  select md.* into finalday from public.matchdays md join public.seasons s on s.current_matchday_id=md.id
    where s.id=sid and md.season_id=sid;
  select * into cfg from public.season_config_versions where id=finalday.season_config_version_id;
  if finalday.id is null or finalday.status<>'closed' or finalday.number is distinct from cfg.total_matchdays
    or cfg.division_sizes is null or exists(select 1 from public.matchdays where season_id=sid and status<>'closed')
    or exists(select 1 from public.season_config_versions where season_id=sid and effective_from_matchday>finalday.number)
    or (select count(*) from public.matchdays where season_id=sid)<>finalday.number
    or (select min(number) from public.matchdays where season_id=sid)<>1
    or (select max(number) from public.matchdays where season_id=sid)<>finalday.number then
    perform public.admin_setup_fail('competition_incomplete'); end if;
  for d in select * from public.matchdays where season_id=sid order by number for update loop
    perform 1 from public.matches where matchday_id=d.id order by id for update;
    perform public.matchday_validate(sid,d.id,true);
    select * into snap from public.matchday_snapshots where matchday_id=d.id for share;
    select * into history from public.matchday_snapshot_revisions where matchday_id=d.id and revision=snap.revision for share;
    if snap.id is null or history.id is null or snap.snapshot_schema_version<>2 or snap.config_version_id<>d.season_config_version_id
      or history.snapshot is distinct from snap.snapshot or history.season_id<>sid
      or snap.revision<>(select max(revision) from public.matchday_snapshot_revisions where matchday_id=d.id)
      or (history.snapshot->>'final')::boolean is distinct from (d.id=finalday.id)
      or history.snapshot#>>'{inputs,season_id}' is distinct from sid::text
      or history.snapshot#>>'{inputs,day_id}' is distinct from d.id::text
      or history.snapshot#>>'{inputs,config,id}' is distinct from d.season_config_version_id::text
      or jsonb_typeof(history.snapshot->'standings') is distinct from 'array' then
      perform public.admin_setup_fail('historical_source_invalid'); end if;
    if (select coalesce(jsonb_agg(jsonb_build_object('id',m.id,'player_a_id',m.player_a_id,'player_b_id',m.player_b_id,
        'winner_id',m.winner_id,'division',v.code) order by m.id),'[]') from public.matches m join public.divisions v on v.id=m.division_id
        where m.matchday_id=d.id) is distinct from
      (select coalesce(jsonb_agg(value order by (value->>'id')::uuid),'[]') from jsonb_array_elements(history.snapshot#>'{inputs,matches}')) then
      perform public.admin_setup_fail('historical_source_invalid'); end if;
    n=jsonb_array_length(history.snapshot->'standings');
    if n<>(select count(*) from public.participant_memberships_at(sid,d.number))
      or n<>(select count(distinct r->>'trainer_id') from jsonb_array_elements(history.snapshot->'standings') r)
      or n<>(select count(distinct (r->>'position')::integer) from jsonb_array_elements(history.snapshot->'standings') r
        where (r->>'position')::integer between 1 and n) then perform public.admin_setup_fail('historical_source_invalid'); end if;
    for row in select value from jsonb_array_elements(history.snapshot->'standings') loop
      if not exists(select 1 from public.participant_memberships_at(sid,d.number) where season_player_id=(row->>'trainer_id')::uuid)
        or (row->>'coins_awarded')::integer is distinct from (select coalesce(sum(amount),0) from public.coin_transactions
          where reward_matchday_id=d.id and season_player_id=(row->>'trainer_id')::uuid) then
        perform public.admin_setup_fail('historical_source_invalid'); end if;
    end loop;
    if history.snapshot->>'last_b_player_id' is not null and not exists (
      select 1 from public.purchases p join public.shop_items i on i.id=p.shop_item_id
      where p.origin_matchday_id=d.id and p.season_player_id=(history.snapshot->>'last_b_player_id')::uuid
        and p.acquisition_type='reward' and p.unit_price=0 and p.status not in ('cancelled','refunded') and i.code='robar_pokemon'
    ) then perform public.admin_setup_fail('historical_source_invalid'); end if;
    if d.id=finalday.id then result=history; end if;
  end loop;
  return result;
end $$;

create function public.lifecycle_draft_safe(sid uuid) returns boolean
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare t text; occupied boolean;
begin
  -- Pure draft roster/config/divisions are retained. Prepared rounds are ambiguous
  -- and require a separate exceptional contract, not silent deletion.
  foreach t in array array['matchdays','matches','matchday_snapshots','matchday_snapshot_revisions','matchday_movements',
    'team_locks','save_files','parsed_saves','pokemon_entities','pokemon_observations','pokemon_identity_revisions',
    'pokemon_entity_flags','pokemon_flags','trainer_flags','robbery_cycles','purchases','redemptions','coin_transactions',
    'shop_promotions','cups','trial_cases','penalties','hall_of_fame_entries','season_archive_snapshots'] loop
    -- parsed_saves is owned through save_files; the parent check suffices.
    if t='parsed_saves' then continue; end if;
    execute format('select exists(select 1 from public.%I where season_id=$1)',t) into occupied using sid;
    if occupied then return false; end if;
  end loop;
  return not exists(select 1 from public.season_players where season_id=sid and
      (status<>'active' or current_save_file_id is not null))
    and not exists(select 1 from public.season_player_stats where season_id=sid and
      (badges_count<>0 or revived_after_wipe<>0));
end $$;

create function public.api_admin_season_lifecycle(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare r jsonb=p_request; b jsonb=r->'body'; op text=r->>'operation'; sid uuid=(r->>'season_id')::uuid;
  actor uuid=(r->>'actor_trainer_id')::uuid; s public.seasons; source public.matchday_snapshot_revisions;
  cached jsonb; result jsonb; artifact jsonb; roster jsonb; rounds jsonb; team jsonb='[]'; standings jsonb;
  champion uuid; finalist uuid; lockid uuid; lockrow record; stamp timestamptz; label text;
  aid uuid; hid uuid; oid uuid=gen_random_uuid(); eid uuid=gen_random_uuid(); destination text;
begin
  if op not in ('finish','archive','discard') or op is null or sid is null
    or jsonb_typeof(b) is distinct from 'object'
    or jsonb_typeof(b->'expected_revision') is distinct from 'number'
    or b->>'expected_revision' !~ '^[0-9]+$'
    or (op='finish' and b-'expected_revision'<>'{}')
    or (op='archive' and (b-array['expected_revision','label']<>'{}' or
      (b->'label' is not null and b->'label'<>'null' and (jsonb_typeof(b->'label')<>'string' or length(btrim(b->>'label')) not between 1 and 120))))
    or (op='discard' and (b-array['expected_revision','reason','confirmation']<>'{}' or b->>'confirmation' is distinct from 'DISCARD'
      or jsonb_typeof(b->'reason') is distinct from 'string' or length(btrim(b->>'reason')) not between 1 and 500)) then
    perform public.admin_setup_fail('invalid_request',422); end if;
  cached=public.admin_setup_begin('lifecycle',r); if cached is not null then return cached; end if;
  select * into s from public.seasons where id=sid;
  if op='finish' and s.status<>'active' then perform public.admin_setup_fail('season_not_active'); end if;
  if op='archive' and s.status<>'finished' then perform public.admin_setup_fail('season_not_finished'); end if;
  if op='discard' and (s.status<>'draft' or not public.lifecycle_draft_safe(sid)) then
    perform public.admin_setup_fail('discard_not_allowed'); end if;
  perform public.admin_setup_cas(sid,b);
  if op in ('finish','archive') then source=public.lifecycle_final_source(sid); end if;
  stamp=clock_timestamp();
  destination=case op when 'finish' then 'finished' when 'archive' then 'archived' else 'discarded' end;
  if op='finish' then
    update public.seasons set status='finished',finished_at=stamp where id=sid;
  elsif op='discard' then
    update public.seasons set status='discarded',discarded_at=stamp where id=sid;
  else
    standings=public.lifecycle_standings(sid,source.snapshot->'standings');
    champion=(standings->0->>'trainer_id')::uuid; finalist=(standings->1->>'trainer_id')::uuid;
    -- The existing Hall requires a real champion; an empty final competition
    -- cannot fabricate one. Missing team evidence, unlike champion, is optional.
    if champion is null then perform public.admin_setup_fail('historical_source_invalid'); end if;
    if exists(select 1 from public.season_archive_snapshots where season_id=sid)
      or exists(select 1 from public.hall_of_fame_entries where season_id=sid and competition_type='league') then
      perform public.admin_setup_fail('historical_artifact_exists'); end if;
    for lockrow in select l.* from public.team_locks l join public.matchdays d on d.id=l.matchday_id
      where l.season_id=sid and l.trainer_id=champion and d.season_id=sid and d.status='closed'
        and d.number<=(select number from public.matchdays where id=source.matchday_id)
      order by d.number desc,l.id for share of l loop
      team=public.lifecycle_public_team(lockrow.public_team_snapshot);
      if jsonb_array_length(team)=6 then lockid=lockrow.id; exit; end if;
    end loop;
    label=coalesce(btrim(b->>'label'),s.name); aid=gen_random_uuid(); hid=gen_random_uuid();
    select coalesce(jsonb_agg(jsonb_build_object('id',p.id,'trainer_id',p.trainer_id,'display_name',t.display_name,
      'status',p.status,'status_effective_matchday_number',p.status_effective_matchday_number,'seed_order',p.seed_order)
      order by p.id),'[]') into roster from public.season_players p join public.trainers t on t.id=p.trainer_id where p.season_id=sid;
    select jsonb_agg(jsonb_build_object('id',d.id,'number',d.number,'config_version_id',d.season_config_version_id,
      'snapshot_revision',x.revision,'closed_at',x.closed_at,'standings',public.lifecycle_standings(sid,x.snapshot->'standings'))
      order by d.number) into rounds from public.matchdays d join public.matchday_snapshots x on x.matchday_id=d.id where d.season_id=sid;
    artifact=jsonb_build_object('schema_version',1,'season',jsonb_build_object('id',sid,'name',s.name,'label',label,
      'started_at',s.started_at,'finished_at',s.finished_at,'archived_at',stamp),
      'source_snapshot_revision_id',source.id,'final_matchday_id',source.matchday_id,'roster',roster,'standings',standings,'rounds',rounds,
      'config_versions',(select jsonb_agg(jsonb_build_object('id',c.id,'version',c.version_number,'name',c.name,
        'effective_from_matchday',c.effective_from_matchday,'total_matchdays',c.total_matchdays,'division_sizes',c.division_sizes,
        'movement_count',c.promotion_relegation_count,'scoring',c.scoring_json,'coin_rewards',c.coin_rewards_json,'rules',c.rules_json)
        order by c.version_number) from public.season_config_versions c where c.season_id=sid),
      'movements',(select coalesce(jsonb_agg(jsonb_build_object('matchday_id',m.matchday_id,'season_player_id',m.season_player_id,
        'from_division_id',m.from_division_id,'to_division_id',m.to_division_id,'type',m.movement_type) order by m.id),'[]')
        from public.matchday_movements m where m.season_id=sid),
      'league',jsonb_build_object('champion_trainer_id',champion,'finalist_trainer_id',finalist,'team',team,'source_team_lock_id',lockid),
      'cup_hall_status','pending_cup_api');
    update public.seasons set status='archived',archived_at=stamp where id=sid;
    insert into public.season_archive_snapshots(id,season_id,snapshot_schema_version,snapshot,created_by_trainer_id,
      source_snapshot_revision_id,checksum,label,created_at)
      values(aid,sid,1,artifact,actor,source.id,encode(sha256(convert_to(artifact::text,'UTF8')),'hex'),label,stamp);
    insert into public.hall_of_fame_entries(id,season_id,competition_type,champion_trainer_id,finalist_trainer_id,
      finalized_at,team_snapshot,archive_snapshot_id,source_snapshot_revision_id,source_team_lock_id)
      values(hid,sid,'league',champion,finalist,stamp,team,aid,source.id,lockid);
  end if;
  update public.season_admin_state set setup_revision=setup_revision+1 where season_id=sid;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
    values(eid,sid,'SEASON_'||upper(destination),actor,'admin','season-lifecycle:'||oid::text,
      jsonb_build_object('operation_id',oid,'before',s.status,'after',destination,'reason',b->>'reason',
        'final_matchday_id',s.current_matchday_id,'archive_id',aid,'hall_id',hid));
  select jsonb_build_object('operation_id',oid,'event_id',eid,'season_id',sid,'operation',op,'state',destination,
    'actor_trainer_id',actor,'changed_at',stamp,'setup_revision',setup_revision,'current_matchday_id',s.current_matchday_id,
    'archive_id',aid,'hall_id',hid,'replayed',false) into result from public.season_admin_state where season_id=sid;
  insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
    values(oid,actor,sid,public.admin_setup_scope('lifecycle',r),r->>'idempotency_key',encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
  return result;
end $$;

-- Keep existing view projections/options/grants; add the missing parent filter.
-- Direct table SELECT also needs a restrictive policy: views are not the only API.
do $$ declare v record; t record; definition text; begin
  for v in select c.table_name from information_schema.columns c join pg_views p on p.schemaname=c.table_schema and p.viewname=c.table_name
    where c.table_schema='public' and c.column_name='season_id' and c.table_name like 'public_%' order by c.table_name loop
    select pg_get_viewdef(('public.'||v.table_name)::regclass,true) into definition;
    execute format('create or replace view public.%I with (security_invoker=false,security_barrier=true) as
      select v.* from (%s) v where v.season_id is null or exists(select 1 from public.seasons s where s.id=v.season_id and s.status<>''discarded'')',
      v.table_name,rtrim(definition,'; '||chr(10)));
  end loop;
  for v in select unnest(array['public_cup_participants','public_cup_matches','public_cup_standings']) as name loop
    select pg_get_viewdef(('public.'||v.name)::regclass,true) into definition;
    execute format('create or replace view public.%I with (security_invoker=false,security_barrier=true) as
      select v.* from (%s) v where exists(select 1 from public.cups c left join public.seasons s on s.id=c.season_id
      where c.id=v.cup_id and c.status<>''discarded'' and (c.season_id is null or s.status<>''discarded''))',v.name,rtrim(definition,'; '||chr(10)));
  end loop;
  create policy lifecycle_discarded_visibility on public.seasons as restrictive for select to authenticated
    using (status<>'discarded' or public.is_current_user_admin());
  for t in select c.table_name from information_schema.columns c join pg_tables p on p.schemaname=c.table_schema and p.tablename=c.table_name
    where c.table_schema='public' and c.column_name='season_id'
      and c.table_name in ('season_players','season_player_stats','season_config_versions','divisions','division_memberships')
      order by c.table_name loop
    execute format('create policy lifecycle_discarded_visibility on public.%I as restrictive for select to authenticated
      using (public.is_current_user_admin() or season_id is null or exists(select 1 from public.public_seasons s where s.id=season_id))',t.table_name);
  end loop;
  -- Owner-only redemption/history reads retain the 024/025 contract, including
  -- pre-029 imported discarded seasons. Public activity must still be hidden.
  create policy lifecycle_discarded_visibility on public.activity_events as restrictive for select to authenticated
    using (visibility<>'public' or public.is_current_user_admin() or season_id is null
      or exists(select 1 from public.public_seasons s where s.id=season_id));
  for t in select unnest(array['cup_participants','cup_matches','cup_standings']) as name loop
    execute format('create policy lifecycle_discarded_visibility on public.%I as restrictive for select to authenticated
      using (public.is_current_user_admin() or exists(select 1 from public.public_cups c where c.id=cup_id))',t.name);
  end loop;
end $$;

do $$ declare f regprocedure; begin
  for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and (p.proname like 'lifecycle_%' or p.proname='api_admin_season_lifecycle') loop
    execute format('revoke all on function %s from public,anon,authenticated',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
