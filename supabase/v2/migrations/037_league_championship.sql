-- Phase 10.5F: exact accumulated League championship; immutable finish certification.
-- No backfill, historical rewrite, live-save title calculation or Cup mutation.
begin;

create table public.league_championship_resolutions (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null references public.seasons(id) on delete restrict,
  input_hash text not null check(input_hash ~ '^[a-f0-9]{64}$'),
  winner_season_player_id uuid not null,
  reason text not null check(length(btrim(reason)) between 1 and 500),
  actor_trainer_id uuid not null references public.trainers(id) on delete restrict,
  created_at timestamptz not null default clock_timestamp(),
  unique(season_id,input_hash),
  foreign key(winner_season_player_id,season_id) references public.season_players(id,season_id)
);
create index championship_resolution_actor_idx on public.league_championship_resolutions(actor_trainer_id);
create index championship_resolution_winner_idx on public.league_championship_resolutions(winner_season_player_id,season_id);
create table public.league_finalizations (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null unique references public.seasons(id) on delete restrict,
  source_snapshot_revision_id uuid not null references public.matchday_snapshot_revisions(id) on delete restrict,
  input_hash text not null check(input_hash ~ '^[a-f0-9]{64}$'),
  title jsonb not null check(jsonb_typeof(title)='object'),
  artifact jsonb not null check(jsonb_typeof(artifact)='object'),
  actor_trainer_id uuid not null references public.trainers(id) on delete restrict,
  created_at timestamptz not null default clock_timestamp()
);
create index league_finalization_source_idx on public.league_finalizations(source_snapshot_revision_id);
create index league_finalization_actor_idx on public.league_finalizations(actor_trainer_id);
alter table public.league_championship_resolutions enable row level security;
alter table public.league_finalizations enable row level security;
revoke all on public.league_championship_resolutions from public,anon,authenticated;
revoke all on public.league_finalizations from public,anon,authenticated;
grant select,insert,delete on public.league_championship_resolutions,public.league_finalizations to service_role;
revoke update,truncate on public.league_championship_resolutions from service_role;
revoke update,truncate on public.league_finalizations from service_role;
create trigger championship_resolution_immutable before update on public.league_championship_resolutions
  for each row execute function public.lifecycle_artifact_immutable();
create trigger league_finalization_immutable before update on public.league_finalizations
  for each row execute function public.lifecycle_artifact_immutable();

-- Retain 035's complete relational/snapshot validation. The pre-036 structural
-- validator deliberately avoids re-reading J1 live progress at historical finish.
create function public.championship_final_source(sid uuid) returns public.matchday_snapshot_revisions
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare finalday public.matchdays; cfg public.season_config_versions; d public.matchdays;
  snap public.matchday_snapshots; history public.matchday_snapshot_revisions; result public.matchday_snapshot_revisions;
  row jsonb; n integer;
begin
  if public.initial_assignment_modern(sid) and not exists(
    select 1 from public.initial_division_snapshots where season_id=sid
  ) then perform public.admin_setup_fail('historical_source_invalid'); end if;
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
    perform public.matchday_validate_v035(sid,d.id,true);
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
      or n<>(select count(distinct case when history.snapshot#>>'{inputs,ranking,rule}'='wins_adjusted_deaths_v1'
          then (r#>>'{metadata,allocation_position}')::integer else (r->>'position')::integer end)
        from jsonb_array_elements(history.snapshot->'standings') r
        where (case when history.snapshot#>>'{inputs,ranking,rule}'='wins_adjusted_deaths_v1'
          then (r#>>'{metadata,allocation_position}')::integer else (r->>'position')::integer end) between 1 and n) then perform public.admin_setup_fail('historical_source_invalid'); end if;
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

create function public.championship_context(sid uuid) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare s public.seasons; source public.matchday_snapshot_revisions; frozen public.league_finalizations;
  resolution public.league_championship_resolutions; result jsonb; players jsonb; leaders jsonb;
  facts jsonb; fingerprint text; champion uuid; winner uuid; minimum_deaths bigint;
  mode text; state text; reason text; setup bigint; row jsonb;
begin
  select * into s from public.seasons where id=sid;
  if not found or s.status='discarded' then perform public.admin_setup_fail('season_not_found',404); end if;
  select setup_revision into setup from public.season_admin_state where season_id=sid;
  result=jsonb_build_object('season_id',sid,'state','incomplete','setup_revision',coalesce(setup,0),
    'input_hash',null,'players','[]'::jsonb,'tied_player_ids','[]'::jsonb,'champion_trainer_id',null,
    'resolution_type',null,'finalist_status','OWNER_DECISION_REQUIRED','blocking_reason','competition_incomplete');
  select * into frozen from public.league_finalizations where season_id=sid;
  if found then
    return frozen.title||jsonb_build_object('state','frozen','setup_revision',setup);
  end if;
  if s.status in ('finished','archived') then
    return result||jsonb_build_object('state','legacy','blocking_reason','legacy_title_uncertified');
  end if;
  if s.status<>'active' then return result; end if;
  begin
    source=public.championship_final_source(sid);
  exception when sqlstate 'PT409' then
    if sqlerrm='competition_incomplete' then return result; end if;
    raise;
  end;
  -- Reject malformed captures instead of allowing the accumulated view's legacy
  -- COALESCEs to turn missing official penalties into zero.
  for row in select v from public.matchday_snapshots x,
    jsonb_array_elements(x.snapshot->'standings') v where x.season_id=sid loop
    if jsonb_typeof(row->'points_awarded') is distinct from 'number'
      or row->>'points_awarded' !~ '^[0-9]+$'
      or coalesce(row#>>'{penalties,points_reduction}','') !~ '^[0-9]+(\.[0-9]+)?$'
      or coalesce(row#>>'{penalties,dead_points_penalty}','') !~ '^[0-9]+(\.[0-9]+)?$' then
      perform public.admin_setup_fail('historical_source_invalid'); end if;
  end loop;
  -- Eligibility remains the official final-day membership, including irreversible
  -- participant exit cutoffs. GENERAL still retains every historical participant.
  select coalesce(jsonb_agg(jsonb_build_object('season_player_id',p.id,'trainer_id',p.trainer_id,
      'display_name',t.display_name,'total_points',points.sanctioned_points::text,
      'adjusted_deaths',case when jsonb_typeof(r#>'{penalties,dead_count}')='number'
        and r#>>'{penalties,dead_count}' ~ '^[0-9]+$'
        and r#>'{penalties,dead_count}'=inputs->'dead_count'
        then (r#>>'{penalties,dead_count}')::bigint end)
      order by points.sanctioned_points desc,p.id),'[]') into players
    from jsonb_array_elements(source.snapshot->'standings') r
    join public.season_players p on p.id=(r->>'trainer_id')::uuid and p.season_id=sid
    join public.trainers t on t.id=p.trainer_id
    left join public.public_sanctioned_points points on points.season_id=sid and points.season_player_id=p.id
    left join lateral (select x as inputs from jsonb_array_elements(source.snapshot#>'{inputs,players}') x
      where x->>'id'=p.id::text) i on true;
  if jsonb_array_length(players)=0 or jsonb_array_length(players)<>jsonb_array_length(source.snapshot->'standings')
    or exists(select 1 from jsonb_array_elements(players) p where p->>'total_points' is null
      or p->>'total_points' !~ '^-?[0-9]+(\.[0-9]+)?$') then
    perform public.admin_setup_fail('historical_source_invalid'); end if;
  -- Bind every official day/revision and full frozen inputs, not just the final
  -- day's score or a live setup revision. Names and rendering order cannot decide.
  select jsonb_agg(jsonb_build_object('id',h.id,'day_id',h.matchday_id,'revision',h.revision,
      'snapshot',h.snapshot) order by d.number) into facts
    from public.matchday_snapshots x join public.matchday_snapshot_revisions h
      on h.matchday_id=x.matchday_id and h.revision=x.revision
    join public.matchdays d on d.id=x.matchday_id where x.season_id=sid;
  fingerprint=encode(sha256(convert_to(jsonb_build_object('rule','final_accumulated_points_v1',
    'season_id',sid,'days',facts,'players',(select jsonb_agg(p-'display_name' order by p->>'season_player_id')
      from jsonb_array_elements(players) p))::text,'UTF8')),'hex');
  select jsonb_agg(p->'season_player_id' order by p->>'season_player_id') into leaders
    from jsonb_array_elements(players) p where (p->>'total_points')::numeric=(players->0->>'total_points')::numeric;
  state='ready';
  if jsonb_array_length(leaders)=1 then
    winner=(leaders->>0)::uuid; mode='unique_points';
  elsif jsonb_array_length(leaders)=2 then
    select * into resolution from public.league_championship_resolutions
      where season_id=sid and input_hash=fingerprint;
    if found then
      if not(leaders ? resolution.winner_season_player_id::text) then
        perform public.admin_setup_fail('historical_source_invalid'); end if;
      winner=resolution.winner_season_player_id; mode='championship_bo3';
    else state='bo3_required'; reason='championship_bo3_required'; end if;
  elsif jsonb_array_length(leaders)=3 then
    if exists(select 1 from jsonb_array_elements(players) p where leaders ? (p->>'season_player_id')
      and p->'adjusted_deaths'='null'::jsonb) then
      state='owner_decision_required'; reason='championship_deaths_unavailable';
    else
      select min((p->>'adjusted_deaths')::bigint) into minimum_deaths from jsonb_array_elements(players) p
        where leaders ? (p->>'season_player_id');
      if (select count(*) from jsonb_array_elements(players) p where leaders ? (p->>'season_player_id')
        and (p->>'adjusted_deaths')::bigint=minimum_deaths)=1 then
        select (p->>'season_player_id')::uuid into winner from jsonb_array_elements(players) p
          where leaders ? (p->>'season_player_id') and (p->>'adjusted_deaths')::bigint=minimum_deaths;
        mode='triple_adjusted_deaths';
      else state='owner_decision_required'; reason='championship_triple_unresolved'; end if;
    end if;
  else state='owner_decision_required'; reason='championship_many_tied'; end if;
  select trainer_id into champion from public.season_players where id=winner and season_id=sid;
  return result||jsonb_build_object('state',state,'input_hash',fingerprint,'players',players,
    'tied_player_ids',case when jsonb_array_length(leaders)>1 then leaders else '[]'::jsonb end,
    'champion_trainer_id',champion,'resolution_type',mode,'blocking_reason',reason,
    '_source_snapshot_revision_id',source.id,'_resolution',case when resolution.id is not null
      then jsonb_build_object('id',resolution.id,'type','championship_bo3','winner_season_player_id',winner,
        'reason',resolution.reason,'actor_trainer_id',resolution.actor_trainer_id,'created_at',resolution.created_at) end);
end $$;

create function public.api_admin_championship_read(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare sid uuid=(p_request->>'season_id')::uuid;
begin
  perform public.admin_setup_principal((p_request->>'actor_trainer_id')::uuid);
  -- Same season/participant/day ordering as writes; no temporary source mixture.
  perform 1 from public.seasons where id=sid for no key update;
  if not found then perform public.admin_setup_fail('season_not_found',404); end if;
  perform 1 from public.season_players where season_id=sid order by id for update;
  return public.championship_context(sid)-'_source_snapshot_revision_id'-'_resolution';
end $$;

create function public.championship_artifact(sid uuid,review jsonb,stamp timestamptz) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare s public.seasons; source public.matchday_snapshot_revisions;
  champion uuid=(review->>'champion_trainer_id')::uuid; standings jsonb;
  team jsonb='[]'; lockrow record; lockid uuid; roster jsonb; rounds jsonb; artifact jsonb; label text;
begin
  if champion is null then perform public.admin_setup_fail('championship_unresolved'); end if;
  select * into s from public.seasons where id=sid;
  select * into source from public.matchday_snapshot_revisions
    where id=(review->>'_source_snapshot_revision_id')::uuid and season_id=sid;
  if not found then perform public.admin_setup_fail('historical_source_invalid'); end if;
  standings=public.lifecycle_standings(sid,source.snapshot->'standings');
    for lockrow in select l.* from public.team_locks l join public.matchdays d on d.id=l.matchday_id
      where l.season_id=sid and l.trainer_id=champion and d.season_id=sid and d.status='closed'
        and d.number<=(select number from public.matchdays where id=source.matchday_id)
      order by d.number desc,l.id for share of l loop
      team=public.lifecycle_public_team(lockrow.public_team_snapshot);
      if jsonb_array_length(team)=6 then lockid=lockrow.id; exit; end if;
    end loop;
    label=s.name;
    select coalesce(jsonb_agg(jsonb_build_object('id',p.id,'trainer_id',p.trainer_id,'display_name',t.display_name,
      'status',p.status,'status_effective_matchday_number',p.status_effective_matchday_number,'seed_order',p.seed_order)
      order by p.id),'[]') into roster from public.season_players p join public.trainers t on t.id=p.trainer_id where p.season_id=sid;
    select jsonb_agg(jsonb_build_object('id',d.id,'number',d.number,'config_version_id',d.season_config_version_id,
      'snapshot_revision',x.revision,'closed_at',x.closed_at,'standings',public.lifecycle_standings(sid,x.snapshot->'standings'))
      order by d.number) into rounds from public.matchdays d join public.matchday_snapshots x on x.matchday_id=d.id where d.season_id=sid;
    artifact=jsonb_build_object('schema_version',2,'season',jsonb_build_object('id',sid,'name',s.name,'label',label,
      'started_at',s.started_at,'finished_at',stamp,'archived_at',null),
      'championship',review-'_source_snapshot_revision_id'-'_resolution','final_standings',review->'players',
      'source_snapshot_revision_id',source.id,'final_matchday_id',source.matchday_id,'roster',roster,'standings',standings,'rounds',rounds,
      'config_versions',(select jsonb_agg(jsonb_build_object('id',c.id,'version',c.version_number,'name',c.name,
        'effective_from_matchday',c.effective_from_matchday,'total_matchdays',c.total_matchdays,'division_sizes',c.division_sizes,
        'movement_count',c.promotion_relegation_count,'scoring',c.scoring_json,'coin_rewards',c.coin_rewards_json,'rules',c.rules_json)
        order by c.version_number) from public.season_config_versions c where c.season_id=sid),
      'movements',(select coalesce(jsonb_agg(jsonb_build_object('matchday_id',m.matchday_id,'season_player_id',m.season_player_id,
        'from_division_id',m.from_division_id,'to_division_id',m.to_division_id,'type',m.movement_type) order by m.id),'[]')
        from public.matchday_movements m where m.season_id=sid),
      'league',jsonb_build_object('champion_trainer_id',champion,'finalist_trainer_id',null,'finalist_status','OWNER_DECISION_REQUIRED','team',team,'source_team_lock_id',lockid),
      'cup_hall_status','independent_cup_certification');
  return artifact;
end $$;

alter function public.api_admin_season_lifecycle(jsonb) rename to api_admin_season_lifecycle_v036;
create function public.api_admin_season_lifecycle(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare r jsonb=p_request; b jsonb=r->'body'; op text=r->>'operation'; sid uuid=(r->>'season_id')::uuid;
  actor uuid=(r->>'actor_trainer_id')::uuid; s public.seasons; frozen public.league_finalizations;
  cached jsonb; review jsonb; result jsonb; artifact jsonb; stamp timestamptz; destination text;
  aid uuid; hid uuid; fid uuid; rid uuid; oid uuid=gen_random_uuid(); eid uuid=gen_random_uuid(); label text;
begin
  if op='discard' then return public.api_admin_season_lifecycle_v036(r); end if;
  if op is null or op not in ('finish','archive','championship_bo3') or sid is null
    or jsonb_typeof(b) is distinct from 'object'
    or jsonb_typeof(b->'expected_revision') is distinct from 'number'
    or b->>'expected_revision' !~ '^[0-9]+$'
    or (op='finish' and (b-array['expected_revision','input_hash']<>'{}'
      or (b ? 'input_hash' and coalesce(b->>'input_hash','') !~ '^[a-f0-9]{64}$')))
    or (op='championship_bo3' and (b-array['expected_revision','input_hash','winner_season_player_id','reason']<>'{}'
      or coalesce(b->>'input_hash','') !~ '^[a-f0-9]{64}$'
      or coalesce(b->>'winner_season_player_id','') !~ '^[a-f0-9-]{36}$'
      or jsonb_typeof(b->'reason') is distinct from 'string' or length(btrim(b->>'reason')) not between 1 and 500))
    or (op='archive' and (b-array['expected_revision','label']<>'{}' or
      (b->'label' is not null and b->'label'<>'null' and (jsonb_typeof(b->'label')<>'string'
        or length(btrim(b->>'label')) not between 1 and 120)))) then
    perform public.admin_setup_fail('invalid_request',422); end if;
  -- Preserve historical finish/archive receipt replay. A missing finish hash can
  -- only recover an exact successful receipt; it never authorizes a new finish.
  cached=public.admin_setup_begin('lifecycle',r); if cached is not null then return cached; end if;
  if op='finish' and not(b ? 'input_hash') then perform public.admin_setup_fail('invalid_request',422); end if;
  select * into s from public.seasons where id=sid;
  if op in ('finish','championship_bo3') and s.status<>'active' then
    perform public.admin_setup_fail('season_not_active'); end if;
  if op='archive' and s.status<>'finished' then perform public.admin_setup_fail('season_not_finished'); end if;
  perform public.admin_setup_cas(sid,b);
  stamp=clock_timestamp();
  if op in ('finish','championship_bo3') then
    review=public.championship_context(sid);
    if review->>'state'='incomplete' then perform public.admin_setup_fail('competition_incomplete'); end if;
    if b->>'input_hash' is distinct from review->>'input_hash' then
      perform public.admin_setup_fail('championship_review_stale'); end if;
    if op='championship_bo3' then
      if review->>'state'<>'bo3_required' then perform public.admin_setup_fail('championship_bo3_not_required'); end if;
      if not((review->'tied_player_ids') ? (b->>'winner_season_player_id')) then
        perform public.admin_setup_fail('invalid_championship_winner'); end if;
      insert into public.league_championship_resolutions(season_id,input_hash,winner_season_player_id,reason,actor_trainer_id)
        values(sid,review->>'input_hash',(b->>'winner_season_player_id')::uuid,btrim(b->>'reason'),actor) returning id into rid;
      destination='active';
    else
      if review->>'state'='bo3_required' then perform public.admin_setup_fail('championship_bo3_required'); end if;
      if review->>'state'<>'ready' or review->>'champion_trainer_id' is null then
        perform public.admin_setup_fail('championship_unresolved'); end if;
      artifact=public.championship_artifact(sid,review,stamp);
      insert into public.league_finalizations(season_id,source_snapshot_revision_id,input_hash,title,artifact,actor_trainer_id,created_at)
        values(sid,(review->>'_source_snapshot_revision_id')::uuid,review->>'input_hash',review,artifact,actor,stamp) returning id into fid;
      update public.seasons set status='finished',finished_at=stamp where id=sid;
      destination='finished';
    end if;
  else
    select * into frozen from public.league_finalizations where season_id=sid;
    if not found then perform public.admin_setup_fail('legacy_title_uncertified'); end if;
    if frozen.title->>'champion_trainer_id' is null or frozen.artifact#>>'{league,champion_trainer_id}'
      is distinct from frozen.title->>'champion_trainer_id' then perform public.admin_setup_fail('historical_source_invalid'); end if;
    if exists(select 1 from public.season_archive_snapshots where season_id=sid)
      or exists(select 1 from public.hall_of_fame_entries where season_id=sid and competition_type='league') then
      perform public.admin_setup_fail('historical_artifact_exists'); end if;
    label=coalesce(btrim(b->>'label'),frozen.artifact#>>'{season,name}'); aid=gen_random_uuid(); hid=gen_random_uuid();
    artifact=jsonb_set(jsonb_set(frozen.artifact,'{season,archived_at}',to_jsonb(stamp)),
      '{season,label}',to_jsonb(label));
    update public.seasons set status='archived',archived_at=stamp where id=sid;
    insert into public.season_archive_snapshots(id,season_id,snapshot_schema_version,snapshot,created_by_trainer_id,
      source_snapshot_revision_id,checksum,label,created_at)
      values(aid,sid,2,artifact,actor,frozen.source_snapshot_revision_id,
        encode(sha256(convert_to(artifact::text,'UTF8')),'hex'),label,stamp);
    insert into public.hall_of_fame_entries(id,season_id,competition_type,champion_trainer_id,finalist_trainer_id,
      finalized_at,team_snapshot,archive_snapshot_id,source_snapshot_revision_id,source_team_lock_id)
      values(hid,sid,'league',(frozen.title->>'champion_trainer_id')::uuid,null,stamp,
        artifact#>'{league,team}',aid,frozen.source_snapshot_revision_id,(artifact#>>'{league,source_team_lock_id}')::uuid);
    destination='archived'; fid=frozen.id;
  end if;
  update public.season_admin_state set setup_revision=setup_revision+1 where season_id=sid;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
    values(eid,sid,case when op='championship_bo3' then 'LEAGUE_CHAMPIONSHIP_BO3' else 'SEASON_'||upper(destination) end,
      actor,'admin','season-lifecycle:'||oid::text,jsonb_build_object('operation_id',oid,'before',s.status,'after',destination,
        'type',case when op='championship_bo3' then 'championship_bo3' else op end,'reason',b->>'reason',
        'winner_season_player_id',b->>'winner_season_player_id','input_hash',b->>'input_hash',
        'finalization_id',fid,'resolution_id',rid,'archive_id',aid,'hall_id',hid));
  select jsonb_build_object('operation_id',oid,'event_id',eid,'season_id',sid,'operation',op,'state',destination,
    'actor_trainer_id',actor,'changed_at',stamp,'setup_revision',setup_revision,'current_matchday_id',s.current_matchday_id,
    'archive_id',aid,'hall_id',hid,'replayed',false) into result from public.season_admin_state where season_id=sid;
  insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
    values(oid,actor,sid,public.admin_setup_scope('lifecycle',r),r->>'idempotency_key',encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
  return result;
end $$;

-- The prior implementation remains callable only for draft discard. Its historical
-- finish/archive entry points must not provide a service-side bypass of certification.
revoke all on function public.api_admin_season_lifecycle_v036(jsonb) from public,anon,authenticated,service_role;
-- Wrapper needs discard without elevating security: isolate the retained discard
-- implementation in the public entry point below through an operation guard.
do $$ declare definition text; begin
  select pg_get_functiondef('public.api_admin_season_lifecycle_v036(jsonb)'::regprocedure) into definition;
  definition=replace(definition,chr(13),'');
  definition=replace(definition,'begin'||chr(10)||'  if op not in',
    'begin'||chr(10)||'  if op is distinct from ''discard'' then perform public.admin_setup_fail(''invalid_request'',422); end if;'||chr(10)||'  if op not in');
  if position('if op is distinct from ''discard''' in definition)=0 then raise exception 'discard guard missing'; end if;
  execute definition;
end $$;
grant execute on function public.api_admin_season_lifecycle_v036(jsonb) to service_role;

do $$ declare f regprocedure; begin
  for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and (p.proname like 'championship_%' or p.proname in
      ('api_admin_championship_read','api_admin_season_lifecycle','api_admin_season_lifecycle_v036')) loop
    execute format('revoke all on function %s from public,anon,authenticated',f);
    execute format('grant execute on function %s to service_role',f);
    execute format('alter function %s security invoker',f);
    execute format('alter function %s set search_path=pg_catalog,public',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
