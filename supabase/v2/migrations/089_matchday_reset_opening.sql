-- 089: «Cancelar jornada» (owner request 2026-11-19).
--
-- An administrator who opened the current matchday by mistake puts it back,
-- while it is still open and not closed, exactly as it was before opening:
--
-- * the per-trainer death snapshots frozen by the opening are removed; the
--   next real opening freezes them again from the data of that moment;
-- * the first-start evidence is "not started" again, so death tracking is
--   back in the progression phase of that matchday;
-- * deaths recorded while it was open by mistake (phase battle of that
--   matchday) are progression deaths of that same matchday again;
-- * Team Locks first fixed while it was open (late) are on time again and
--   stay fixed;
-- * provisional results are discarded.
--
-- Nothing else changes: closed matchdays and their snapshots, coins, prizes,
-- robberies, purchases, Team Lock confirmations and announcements stay.
-- «Cancelar edición» (operation cancel) keeps its contract: it preserves the
-- first frozen boundary.
--
-- Death snapshots and death events stay immutable for every other write. The
-- guard admits only this operation, scoped to one matchday through a
-- transaction-local setting, and only these two changes: removing that
-- matchday's snapshots and moving its battle events to progression.
begin;

create function public.matchday_reset_artifact_guard() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  if coalesce(current_setting('pokeapp.matchday_reset',true),'')=old.matchday_id::text then
    if tg_table_name='matchday_death_snapshots' and tg_op='DELETE' then return old; end if;
    if tg_table_name='league_death_events' and tg_op='UPDATE' and old.phase='battle' and new.phase='progression'
      and to_jsonb(new)-'phase'=to_jsonb(old)-'phase' then return new; end if;
  end if;
  if tg_op='DELETE' or new is distinct from old then perform public.admin_setup_fail('historical_artifact_immutable'); end if;
  return new;
end $$;
revoke all on function public.matchday_reset_artifact_guard() from public,anon,authenticated;

drop trigger league_death_event_immutable on public.league_death_events;
create trigger league_death_event_immutable before update or delete on public.league_death_events
  for each row execute function public.matchday_reset_artifact_guard();
drop trigger matchday_death_snapshot_immutable on public.matchday_death_snapshots;
create trigger matchday_death_snapshot_immutable before update or delete on public.matchday_death_snapshots
  for each row execute function public.matchday_reset_artifact_guard();
grant delete on public.matchday_death_snapshots to service_role;
grant update (phase) on public.league_death_events to service_role;

-- Runs after matchday_lock('reset'): administrator, receipt, active season,
-- current matchday, status open, expected revision, valid roster and pairs.
create function public.matchday_reset_opening(sid uuid,did uuid) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare d public.matchdays; started timestamptz; results jsonb; snapshots jsonb; events jsonb;
  fixations jsonb; late uuid[];
begin
  select * into d from public.matchdays where id=did and season_id=sid for update;
  if d.id is null or d.status<>'open' then perform public.admin_setup_fail('matchday_not_open'); end if;
  if exists(select 1 from public.matchday_snapshots where matchday_id=did)
    or exists(select 1 from public.matchday_movements where matchday_id=did) then
    perform public.admin_setup_fail('dependent_data_exists'); end if;
  -- A save sync in flight holds its participant row and still sees the day
  -- open: wait for it, so its battle-phase events are moved below too.
  perform 1 from public.season_players where season_id=sid order by id for update;
  select first_started_at into started from public.matchday_start_evidence where matchday_id=did for update;

  select coalesce(jsonb_agg(jsonb_build_object('match_id',id,'winner_season_player_id',winner_id) order by id),'[]'::jsonb)
    into results from public.matches where matchday_id=did and winner_id is not null;
  update public.matches set winner_id=null,status='scheduled' where matchday_id=did and winner_id is not null;

  perform set_config('pokeapp.matchday_reset',did::text,true);
  select coalesce(jsonb_agg(to_jsonb(x) order by x.season_player_id),'[]'::jsonb) into snapshots
    from public.matchday_death_snapshots x where x.matchday_id=did;
  delete from public.matchday_death_snapshots where matchday_id=did;
  select coalesce(jsonb_agg(e.id order by e.id),'[]'::jsonb) into events
    from public.league_death_events e where e.matchday_id=did and e.phase='battle';
  update public.league_death_events set phase='progression' where matchday_id=did and phase='battle';
  perform set_config('pokeapp.matchday_reset','',true);

  -- Fixed after the mistaken start: on time for the real one, still fixed.
  select coalesce(array_agg(f.lock_id order by f.lock_id),'{}'::uuid[]),
      coalesce(jsonb_agg(to_jsonb(f) order by f.lock_id),'[]'::jsonb)
    into late,fixations from public.team_lock_first_fixations f join public.team_locks l on l.id=f.lock_id
    where l.matchday_id=did and f.timing_status='late' and started is not null and f.first_fixed_at>started;
  delete from public.team_lock_first_fixations where lock_id=any(late);
  insert into public.team_lock_first_fixations(lock_id,first_fixed_at,timing_status)
    select (x->>'lock_id')::uuid,(x->>'first_fixed_at')::timestamptz,'on_time' from jsonb_array_elements(fixations) x;
  update public.team_locks set is_late=false where id=any(late) and is_late;

  delete from public.matchday_start_evidence where matchday_id=did;
  insert into public.matchday_start_evidence(matchday_id,first_started_at) values(did,null);
  update public.matchdays set status='scheduled',opened_at=null,revision=revision+1,results_revision=results_revision+1
    where id=did;
  return jsonb_build_object('first_started_at',started,'discarded_results',results,'removed_death_snapshots',snapshots,
    'death_events_back_to_progression',events,'team_locks_back_on_time',to_jsonb(late));
end $$;

alter function public.api_admin_matchday(jsonb) rename to api_admin_matchday_v088;
create function public.api_admin_matchday(p_request jsonb) returns jsonb
language plpgsql set search_path=pg_catalog,public as $$
declare op text=p_request->>'operation'; r jsonb=p_request->'request'; cached jsonb; result jsonb; reverted jsonb;
  sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid; oid uuid=gen_random_uuid(); eid uuid=gen_random_uuid();
begin
  if op is distinct from 'reset' then return public.api_admin_matchday_v088(p_request); end if;
  cached=public.matchday_lock(op,r); if cached is not null then return cached; end if;
  reverted=public.matchday_reset_opening(sid,did);
  select jsonb_build_object('season_id',sid,'matchday_id',did,'state',x.status,'revision',x.revision,'results_revision',x.results_revision,
    'snapshot_revision',0,'current_matchday_id',s.current_matchday_id) into result
    from public.matchdays x join public.seasons s on s.id=x.season_id where x.id=did;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
    values(eid,sid,'MATCHDAY_ADMIN_RESET',(r->>'actor_trainer_id')::uuid,'admin','matchday-admin:'||oid::text,
      result||jsonb_build_object('reason',r->'body'->>'reason','operation_id',oid,'reverted',reverted));
  result=result||jsonb_build_object('operation_id',oid,'event_id',eid,'replayed',false);
  insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
    values(oid,(r->>'actor_trainer_id')::uuid,sid,public.admin_setup_scope('matchday_'||op,r),r->>'idempotency_key',
      encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
  return result;
end $$;

do $$ declare f regprocedure; begin
  foreach f in array array['public.matchday_reset_opening(uuid,uuid)'::regprocedure,
      'public.api_admin_matchday(jsonb)'::regprocedure] loop
    execute format('revoke all on function %s from public,anon,authenticated',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
