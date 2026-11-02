-- 076: explicitly confirmed final NET championship tiebreaks only.
-- Scoring, matchday rankings/rewards and frozen historical titles are unchanged.
begin;

alter table public.league_championship_resolutions
  drop constraint league_championship_resolutions_resolution_type_check,
  drop constraint league_championship_resolutions_season_id_input_hash_key,
  alter column winner_season_player_id drop not null,
  add column outcome text,
  add column decision_json jsonb,
  add constraint championship_resolution_method check(resolution_type in
    ('championship_bo3','championship_residual','total_actual_deaths','championship_1v1')),
  add constraint championship_resolution_decision check(
    (resolution_type in ('championship_bo3','championship_residual') and winner_season_player_id is not null
      and outcome is null and decision_json is null)
    or coalesce((resolution_type in ('total_actual_deaths','championship_1v1')
      and jsonb_typeof(decision_json)='object'
      and decision_json->>'method'=resolution_type
      and jsonb_typeof(decision_json->'participants')='array'
      and decision_json->>'result'=outcome
      and ((outcome='resolved' and winner_season_player_id is not null)
        or (outcome='battle_required' and resolution_type='total_actual_deaths' and winner_season_player_id is null))),false)),
  add unique(season_id,input_hash,resolution_type);
create unique index championship_one_final_resolution on public.league_championship_resolutions(season_id,input_hash)
  where winner_season_player_id is not null;
-- The existing immutable UPDATE guard remains. Also disallow deleting a new
-- audited choice; old cleanup/legacy semantics are preserved.
create function public.championship_decision_no_delete() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  if old.resolution_type in ('total_actual_deaths','championship_1v1') then
    perform public.admin_setup_fail('historical_artifact_immutable'); end if;
  return old;
end $$;
create trigger championship_decision_no_delete before delete on public.league_championship_resolutions
  for each row execute function public.championship_decision_no_delete();

alter function public.championship_context(uuid) rename to championship_context_v075;
create function public.championship_context(sid uuid) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare ctx jsonb; source public.matchday_snapshot_revisions; p jsonb; captured jsonb; prior_input jsonb;
  players jsonb='[]'; leaders jsonb; candidates jsonb; digest text; actual bigint; champion uuid;
  chosen public.league_championship_resolutions; compared public.league_championship_resolutions;
begin
  ctx=public.championship_context_v075(sid);
  if not public.league_net_season(sid) or ctx->>'state' in ('incomplete','legacy','frozen') then return ctx; end if;
  select * into source from public.matchday_snapshot_revisions
    where id=(ctx->>'_source_snapshot_revision_id')::uuid and season_id=sid;
  if source.id is null then perform public.admin_setup_fail('historical_source_invalid'); end if;
  for p in select value from jsonb_array_elements(ctx->'players') loop
    select x into captured from jsonb_array_elements(source.snapshot->'standings') x where x->>'trainer_id'=p->>'season_player_id';
    select x into prior_input from jsonb_array_elements(source.snapshot#>'{inputs,players}') x where x->>'id'=p->>'season_player_id';
    actual=null;
    if jsonb_typeof(captured#>'{metadata,actual_deaths}')='number'
      and captured#>>'{metadata,actual_deaths}' ~ '^(0|[1-9][0-9]*)$'
      and captured#>'{metadata,actual_deaths}'=prior_input->'actual_deaths' then
      actual=(captured#>>'{metadata,actual_deaths}')::bigint;
    end if;
    players=players||jsonb_build_array(p||jsonb_build_object('actual_deaths',actual));
  end loop;
  ctx=jsonb_set(ctx,'{players}',players);
  -- A unique NET champion retains the existing finish and fingerprint contract.
  if ctx->>'state'='ready' then return ctx; end if;
  if ctx->>'blocking_reason' is distinct from 'league_net_championship_tie_rule_required' then return ctx; end if;
  leaders=ctx->'tied_player_ids';
  digest=encode(sha256(convert_to((ctx->>'input_hash')||':explicit_net_title_076_v1','UTF8')),'hex');
  select * into chosen from public.league_championship_resolutions
    where season_id=sid and input_hash=digest and outcome='resolved';
  select * into compared from public.league_championship_resolutions
    where season_id=sid and input_hash=digest and resolution_type='total_actual_deaths';
  candidates=case when compared.outcome='battle_required' then compared.decision_json->'candidate_player_ids' else leaders end;
  if chosen.id is not null then
    if not (leaders ? chosen.winner_season_player_id::text) then
      perform public.admin_setup_fail('historical_source_invalid'); end if;
    select trainer_id into champion from public.season_players where id=chosen.winner_season_player_id and season_id=sid;
    return ctx||jsonb_build_object('state','ready','input_hash',digest,'tied_player_ids',candidates,
      'champion_trainer_id',champion,'resolution_type',chosen.resolution_type,
      'tiebreak_method',chosen.resolution_type,'blocking_reason',null,
      '_resolution',jsonb_build_object('id',chosen.id,'type',chosen.resolution_type,
        'winner_season_player_id',chosen.winner_season_player_id,'reason',chosen.reason,
        'actor_trainer_id',chosen.actor_trainer_id,'created_at',chosen.created_at,
        'decision',chosen.decision_json,'prior_deaths_decision_id',compared.id));
  end if;
  return ctx||jsonb_build_object('state',case when compared.id is null then 'tiebreak_required' else 'battle_required' end,
    'input_hash',digest,'tied_player_ids',candidates,'champion_trainer_id',null,'resolution_type',null,
    'tiebreak_method',case when compared.id is not null then 'total_actual_deaths' end,
    'blocking_reason',case when compared.id is null then 'championship_tiebreak_required' else 'championship_battle_required' end);
end $$;

-- Validate recorded results, not a generated schedule/order. Multiway evidence
-- must support one undefeated winner covering the whole candidate set through
-- actual recorded victories. Disconnected, cyclic or ambiguous evidence fails.
create function public.championship_verify_battles(candidates jsonb,winner text,battles jsonb) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare b jsonb; a text; opponent text; won text; stamp text; reached integer; undefeated integer;
begin
  if jsonb_typeof(candidates) is distinct from 'array' or jsonb_array_length(candidates)<2
    or winner is null or not(candidates ? winner) or jsonb_typeof(battles) is distinct from 'array'
    or jsonb_array_length(battles) not between 1 and 1000 then
    perform public.admin_setup_fail('championship_battle_invalid'); end if;
  if jsonb_array_length(candidates)=2 and jsonb_array_length(battles)<>1 then
    perform public.admin_setup_fail('championship_battle_ambiguous'); end if;
  if (select count(distinct (least(x->>'player_a_id',x->>'player_b_id'),greatest(x->>'player_a_id',x->>'player_b_id')))
    from jsonb_array_elements(battles) x)<>jsonb_array_length(battles) then
    perform public.admin_setup_fail('championship_battle_invalid'); end if;
  for b in select value from jsonb_array_elements(battles) loop
    a=b->>'player_a_id';opponent=b->>'player_b_id';won=b->>'winner_id';stamp=b->>'played_at';
    if jsonb_typeof(b) is distinct from 'object' or b-array['player_a_id','player_b_id','winner_id','played_at','evidence']<>'{}'::jsonb
      or a is null or opponent is null or won is null or a=opponent
      or not(candidates ? a) or not(candidates ? opponent) or won not in(a,opponent)
      or jsonb_typeof(b->'evidence') is distinct from 'string' or length(btrim(b->>'evidence')) not between 1 and 500
      or jsonb_typeof(b->'played_at') is distinct from 'string' or coalesce(stamp,'') !~ '(Z|[+-][0-9]{2}:[0-9]{2})$' then
      perform public.admin_setup_fail('championship_battle_invalid'); end if;
    begin
      if stamp::timestamptz>clock_timestamp() then perform public.admin_setup_fail('championship_battle_invalid'); end if;
    exception when invalid_datetime_format or datetime_field_overflow then
      perform public.admin_setup_fail('championship_battle_invalid');
    end;
  end loop;
  if exists(select 1 from jsonb_array_elements(battles) x where x->>'winner_id'<>winner and winner in(x->>'player_a_id',x->>'player_b_id')) then
    perform public.admin_setup_fail('championship_battle_ambiguous'); end if;
  select count(*) into undefeated from jsonb_array_elements_text(candidates) c(pid)
    where not exists(select 1 from jsonb_array_elements(battles) x
      where x->>'winner_id'<>c.pid and c.pid in(x->>'player_a_id',x->>'player_b_id'));
  if exists(with recursive edges as (
    select x->>'winner_id' as victor,case when x->>'winner_id'=x->>'player_a_id' then x->>'player_b_id' else x->>'player_a_id' end as defeated
    from jsonb_array_elements(battles) x
  ), paths(victor,defeated) as (
    select victor,defeated from edges union
    select p.victor,e.defeated from paths p join edges e on e.victor=p.defeated
  ) select 1 from paths where victor=defeated) then
    perform public.admin_setup_fail('championship_battle_ambiguous'); end if;
  with recursive edges as (
    select x->>'winner_id' as victor,case when x->>'winner_id'=x->>'player_a_id' then x->>'player_b_id' else x->>'player_a_id' end as defeated
    from jsonb_array_elements(battles) x
  ), proof(pid) as (
    select winner union select e.defeated from proof p join edges e on e.victor=p.pid
  ) select count(*) into reached from proof;
  if undefeated<>1 or reached<>jsonb_array_length(candidates) then
    perform public.admin_setup_fail('championship_battle_ambiguous'); end if;
end $$;

alter function public.api_admin_season_lifecycle(jsonb) rename to api_admin_season_lifecycle_v075;
create function public.api_admin_season_lifecycle(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare r jsonb=p_request; b jsonb=r->'body'; sid uuid=(r->>'season_id')::uuid;
  actor uuid=(r->>'actor_trainer_id')::uuid; cached jsonb; review jsonb; facts jsonb; candidates jsonb;
  method text=b->>'method'; outcome text; winner uuid; minimum_deaths bigint;
  resolution_id uuid; operation_id uuid=gen_random_uuid(); event_id uuid=gen_random_uuid(); stamp timestamptz;
  result jsonb; source_id uuid;
begin
  if r->>'operation' is distinct from 'championship_tiebreak' then
    return public.api_admin_season_lifecycle_v075(r); end if;
  perform public.admin_setup_principal(actor);
  if sid is null or jsonb_typeof(b) is distinct from 'object'
    or r-array['operation','actor_trainer_id','season_id','body','idempotency_key']<>'{}'::jsonb
    or b-array['expected_revision','input_hash','method','confirmation','reason','winner_season_player_id','battles']<>'{}'::jsonb
    or jsonb_typeof(b->'expected_revision') is distinct from 'number' or coalesce(b->>'expected_revision','') !~ '^[0-9]+$'
    or coalesce(b->>'input_hash','') !~ '^[a-f0-9]{64}$'
    or b->'confirmation' is distinct from 'true'::jsonb
    or method is null or method not in ('total_actual_deaths','championship_1v1')
    or jsonb_typeof(b->'reason') is distinct from 'string' or length(btrim(b->>'reason')) not between 1 and 500 then
    perform public.admin_setup_fail('invalid_request',422); end if;
  cached=public.admin_setup_begin('lifecycle',r);if cached is not null then return cached; end if;
  if not exists(select 1 from public.seasons where id=sid and status='active') then
    perform public.admin_setup_fail('season_not_active'); end if;
  perform public.admin_setup_cas(sid,b);
  review=public.championship_context(sid);
  if review->>'state' not in ('tiebreak_required','battle_required') or not public.league_net_season(sid) then
    perform public.admin_setup_fail('championship_tiebreak_not_required'); end if;
  if b->>'input_hash' is distinct from review->>'input_hash' then
    perform public.admin_setup_fail('championship_review_stale'); end if;
  candidates=review->'tied_player_ids';source_id=(review->>'_source_snapshot_revision_id')::uuid;
  if method='total_actual_deaths' then
    if review->>'state'='battle_required' then perform public.admin_setup_fail('championship_resolution_conflict'); end if;
    if coalesce(b->'winner_season_player_id','null'::jsonb)<>'null'::jsonb
      or coalesce(b->'battles','null'::jsonb) not in ('null'::jsonb,'[]'::jsonb) then
      perform public.admin_setup_fail('invalid_request',422); end if;
    if exists(select 1 from jsonb_array_elements(review->'players') p where candidates ? (p->>'season_player_id')
      and p->>'actual_deaths' is null) then perform public.admin_setup_fail('championship_deaths_unavailable'); end if;
    select min((p->>'actual_deaths')::bigint) into minimum_deaths from jsonb_array_elements(review->'players') p
      where candidates ? (p->>'season_player_id');
    select jsonb_agg(p->'season_player_id' order by p->>'season_player_id') into candidates
      from jsonb_array_elements(review->'players') p where review->'tied_player_ids' ? (p->>'season_player_id')
        and (p->>'actual_deaths')::bigint=minimum_deaths;
    if jsonb_array_length(candidates)=1 then winner=(candidates->>0)::uuid;outcome='resolved';
    else outcome='battle_required'; end if;
  else
    perform public.championship_verify_battles(candidates,b->>'winner_season_player_id',b->'battles');
    winner=(b->>'winner_season_player_id')::uuid;outcome='resolved';
  end if;
  stamp=clock_timestamp();
  select jsonb_agg(p-'display_name' order by p->>'season_player_id') into facts
    from jsonb_array_elements(review->'players') p where review->'tied_player_ids' ? (p->>'season_player_id');
  insert into public.league_championship_resolutions(season_id,input_hash,winner_season_player_id,reason,
    actor_trainer_id,resolution_type,outcome,decision_json)
    values(sid,review->>'input_hash',winner,btrim(b->>'reason'),actor,method,outcome,
      jsonb_build_object('schema_version',1,'method',method,'participants',facts,
        'candidate_player_ids',candidates,'source_snapshot_revision_id',source_id,
        'battles',case when method='championship_1v1' then b->'battles' else '[]'::jsonb end,
        'confirmation',true,'result',outcome,'winner_season_player_id',winner)) returning id into resolution_id;
  update public.season_admin_state set setup_revision=setup_revision+1 where season_id=sid;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
    values(event_id,sid,'LEAGUE_CHAMPIONSHIP_TIEBREAK',actor,'admin','championship-tiebreak:'||operation_id::text,
      jsonb_build_object('operation_id',operation_id,'resolution_id',resolution_id,'method',method,
        'participants',facts,'candidate_player_ids',candidates,'result',outcome,'winner_season_player_id',winner,
        'reason',btrim(b->>'reason'),'input_hash',review->>'input_hash'));
  select jsonb_build_object('operation_id',operation_id,'event_id',event_id,'season_id',sid,
    'operation','championship_tiebreak','state','active','actor_trainer_id',actor,'changed_at',stamp,
    'setup_revision',a.setup_revision,'current_matchday_id',s.current_matchday_id,
    'archive_id',null,'hall_id',null,'replayed',false) into result
    from public.season_admin_state a join public.seasons s on s.id=a.season_id where s.id=sid;
  insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
    values(operation_id,actor,sid,public.admin_setup_scope('lifecycle',r),r->>'idempotency_key',
      encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
  return result;
end $$;

do $$ declare f regprocedure; begin
  foreach f in array array[
    'public.championship_decision_no_delete()'::regprocedure,
    'public.championship_context(uuid)'::regprocedure,'public.championship_context_v075(uuid)'::regprocedure,
    'public.championship_verify_battles(jsonb,text,jsonb)'::regprocedure,
    'public.api_admin_season_lifecycle(jsonb)'::regprocedure,'public.api_admin_season_lifecycle_v075(jsonb)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
