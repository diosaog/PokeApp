-- Phase 10.5C. Participant results only; admin lifecycle/corrections stay separate.
begin;
create function public.api_participant_matchday(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare op text=p_request->>'operation'; r jsonb=p_request->'request'; b jsonb=r->'body';
  actor uuid=(r->>'actor_trainer_id')::uuid; sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid;
  scope text=public.admin_setup_scope('matchday_participant_results',r); k text=r->>'idempotency_key';
  t public.trainers; s public.seasons; p public.season_players; d public.matchdays;
  cached public.admin_operation_receipts; before_results jsonb; result jsonb;
  oid uuid=gen_random_uuid(); eid uuid=gen_random_uuid();
begin
  if op is null or op not in ('state','results') then perform public.admin_setup_fail('invalid_request',422); end if;
  select * into t from public.trainers where id=actor for share;
  if not found or not t.globally_enabled then perform public.admin_setup_fail('trainer_disabled',403); end if;
  if op='results' then
    if k is null or length(k) not between 1 and 128
      or jsonb_typeof(b->'expected_results_revision') is distinct from 'number'
      or (b->>'expected_results_revision') !~ '^(0|[1-9][0-9]*)$'
      or jsonb_typeof(b->'results') is distinct from 'array' then
      perform public.admin_setup_fail('invalid_request',422); end if;
    if jsonb_array_length(b->'results') not between 1 and 1000 then
      perform public.admin_setup_fail('invalid_request',422); end if;
    perform pg_advisory_xact_lock(hashtextextended(actor::text||scope||':'||k,0));
  end if;
  -- Same order as admin/trials/status: principal, receipt, season, roster, day,
  -- matches, configuration. Authority cannot race a withdrawal or day close.
  select * into s from public.seasons where id=sid for no key update;
  if not found or s.status='discarded' then perform public.admin_setup_fail('season_not_found',404); end if;
  perform 1 from public.season_players where season_id=sid order by id for update;
  select * into p from public.season_players where season_id=sid and trainer_id=actor;
  if not found then perform public.admin_setup_fail('participant_required',403); end if;
  if p.status<>'active' then perform public.admin_setup_fail('participant_inactive',403); end if;
  select * into d from public.matchdays where id=did and season_id=sid for update;
  if not found then perform public.admin_setup_fail('matchday_not_found',404); end if;
  if not exists(select 1 from public.participant_memberships_at(sid,d.number) m where m.season_player_id=p.id) then
    perform public.admin_setup_fail('participant_ineligible',403); end if;
  if op='results' then
    select * into cached from public.admin_operation_receipts where actor_trainer_id=actor
      and operation_scope=scope and idempotency_key=k;
    if found then
      if cached.request_hash<>encode(sha256(convert_to(r::text,'UTF8')),'hex') then
        perform public.admin_setup_fail('idempotency_conflict'); end if;
      -- A receipt read never reopens history. Still requires enabled active membership.
      return cached.response_json||'{"replayed":true}'::jsonb;
    end if;
    if s.status<>'active' then perform public.admin_setup_fail('season_not_active'); end if;
    if s.current_matchday_id is distinct from did then perform public.admin_setup_fail('matchday_not_current'); end if;
    if d.status<>'open' then
      perform public.admin_setup_fail(case when d.status='closed' then 'already_closed' else 'matchday_not_open' end); end if;
    if (b->>'expected_results_revision')::bigint<>d.results_revision then perform public.admin_setup_fail('stale_revision'); end if;
    perform 1 from public.matches where matchday_id=did order by id for update;
    perform 1 from public.season_config_versions where season_id=sid order by id for share;
    perform public.matchday_validate(sid,did,false);
    select coalesce(jsonb_agg(jsonb_build_object('match_id',m.id,'winner_season_player_id',m.winner_id) order by m.id),'[]'::jsonb)
      into before_results from public.matches m where m.matchday_id=did
      and m.id in (select (x->>'match_id')::uuid from jsonb_array_elements(b->'results') x);
    perform public.matchday_results(did,b->'results');
    update public.matchdays set revision=revision+1,results_revision=results_revision+1 where id=did returning * into d;
  end if;
  result=jsonb_build_object('season_id',sid,'matchday_id',did,'state',d.status,'revision',d.revision,
    'results_revision',d.results_revision,'snapshot_revision',coalesce((select revision from public.matchday_snapshots where matchday_id=did),0),
    'current_matchday_id',s.current_matchday_id);
  if op='state' then
    return result||jsonb_build_object('matches',(select coalesce(jsonb_agg(jsonb_build_object('id',id,'player_a_id',player_a_id,
      'player_b_id',player_b_id,'winner_id',winner_id) order by id),'[]'::jsonb) from public.matches where matchday_id=did));
  end if;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
    values(eid,sid,'MATCHDAY_PARTICIPANT_RESULTS',actor,'admin','matchday-participant:'||oid::text,
      result||jsonb_build_object('operation_id',oid,'before',before_results,'after',b->'results'));
  result=result||jsonb_build_object('operation_id',oid,'event_id',eid,'replayed',false);
  insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
    values(oid,actor,sid,scope,k,encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
  return result;
end $$;
revoke all on function public.api_participant_matchday(jsonb) from public,anon,authenticated;
grant execute on function public.api_participant_matchday(jsonb) to service_role;
notify pgrst,'reload schema';
commit;
