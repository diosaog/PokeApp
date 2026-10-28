-- Preparation facts and safe logical cancellation. No backfill or reward change.
begin;

create function public.lifecycle_precompetition_safe(sid uuid) returns boolean
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare t text; occupied boolean;
begin
  -- Save registration/identity evidence is retained. Competitive and economic
  -- facts, even an unfinished scheduled round, prevent cancellation.
  foreach t in array array['matchdays','matches','initial_division_snapshots',
    'division_memberships','matchday_snapshots','matchday_snapshot_revisions','matchday_movements',
    'team_locks','pokemon_entity_flags','pokemon_flags','trainer_flags','robbery_cycles',
    'purchases','redemptions','coin_transactions','progress_reward_claims','shop_promotions',
    'cups','trial_cases','penalties','hall_of_fame_entries','season_archive_snapshots','league_finalizations'] loop
    execute format('select exists(select 1 from public.%I where season_id=$1)',t) into occupied using sid;
    if occupied then return false; end if;
  end loop;
  return not exists(select 1 from public.season_players where season_id=sid and status<>'active')
    and not exists(select 1 from public.season_player_stats where season_id=sid and revived_after_wipe<>0);
end $$;

-- Extend only the retained discard operation, keeping its principal, locks,
-- CAS, confirmation, receipt and audit. Finish/archive bypass stays forbidden.
do $$ declare definition text; old_condition text;
begin
  select pg_get_functiondef('public.api_admin_season_lifecycle_v036(jsonb)'::regprocedure) into definition;
  old_condition='(s.status<>''draft'' or not public.lifecycle_draft_safe(sid))';
  if position(old_condition in definition)=0 or position('if op is distinct from ''discard''' in definition)=0 then
    raise exception 'unexpected retained discard contract'; end if;
  definition=replace(definition,old_condition,
    '(not ((s.status=''draft'' and public.lifecycle_draft_safe(sid)) or (s.status=''active'' and public.lifecycle_precompetition_safe(sid))))');
  execute definition;
end $$;

alter function public.api_admin_get_setup(jsonb) rename to api_admin_get_setup_v067;
create function public.api_admin_get_setup(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare result jsonb; sid uuid=(p_request->>'season_id')::uuid; allowed boolean;
begin
  result=public.api_admin_get_setup_v067(p_request);
  allowed=case result#>>'{season,status}'
    when 'draft' then public.lifecycle_draft_safe(sid)
    when 'active' then public.lifecycle_precompetition_safe(sid) else false end;
  return result||jsonb_build_object('can_discard',allowed);
end $$;

alter function public.championship_final_source(uuid) rename to championship_final_source_v067;
create function public.championship_final_source(sid uuid) returns public.matchday_snapshot_revisions
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  -- No competition yet is incomplete, not damaged historical evidence.
  if exists(select 1 from public.seasons where id=sid and status='active' and current_matchday_id is null)
    and not exists(select 1 from public.matchdays where season_id=sid)
    and not exists(select 1 from public.league_finalizations where season_id=sid)
    and not exists(select 1 from public.season_archive_snapshots where season_id=sid)
    and not exists(select 1 from public.hall_of_fame_entries where season_id=sid) then
    perform public.admin_setup_fail('competition_incomplete'); end if;
  return public.championship_final_source_v067(sid);
end $$;

alter function public.initial_assignment_observations(uuid) rename to initial_assignment_observations_v067;
create function public.initial_assignment_observations(sid uuid) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare result jsonb='[]'; row jsonb; saved public.save_files; parsed public.parsed_saves; native jsonb;
begin
  -- Reuse exact-save/identity/Box8/death checks. Only observed Gen6 gym badges
  -- extend readiness; Gen7 stamps and all reward policies remain unchanged.
  for row in select * from jsonb_array_elements(public.initial_assignment_observations_v067(sid)) loop
    if row->>'progress_state'='unknown' then
      select * into saved from public.save_files where id=(row#>>'{_source,save_file_id}')::uuid
        and season_id=sid and trainer_id=(row->>'trainer_id')::uuid;
      select * into parsed from public.parsed_saves where id=(row#>>'{_source,parsed_save_id}')::uuid and save_file_id=saved.id;
      native=public.observed_native_progress(saved,parsed,(row->>'trainer_id')::uuid);
      if native->>'model'='gym_badges' then
        row=row||jsonb_build_object('progress_state','observed',
          'observed_badges',(select count(*) from jsonb_array_elements(native->'badge_flags') flag where flag='true'::jsonb),
          'cap_reached',native#>'{badge_flags,0}'='true'::jsonb and native#>'{badge_flags,1}'='true'::jsonb,
          '_source',(row->'_source')||jsonb_build_object('native_progress',native));
      end if;
    end if;
    result=result||jsonb_build_array(row);
  end loop;
  return result;
end $$;

alter function public.initial_assignment_inputs(uuid) rename to initial_assignment_inputs_v067;
create function public.initial_assignment_inputs(sid uuid) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare result jsonb;
begin
  result=public.initial_assignment_inputs_v067(sid);
  if result->>'state'='pending' and jsonb_array_length(result->'players')<2 then
    result=result||jsonb_build_object('ready',false,'blocking_reasons',
      (result->'blocking_reasons')||'"opponent_missing"'::jsonb);
  end if;
  return result;
end $$;

do $$ declare f regprocedure; begin
  foreach f in array array[
    'public.lifecycle_precompetition_safe(uuid)'::regprocedure,
    'public.api_admin_get_setup(jsonb)'::regprocedure,'public.api_admin_get_setup_v067(jsonb)'::regprocedure,
    'public.championship_final_source(uuid)'::regprocedure,'public.championship_final_source_v067(uuid)'::regprocedure,
    'public.initial_assignment_observations(uuid)'::regprocedure,'public.initial_assignment_observations_v067(uuid)'::regprocedure,
    'public.initial_assignment_inputs(uuid)'::regprocedure,'public.initial_assignment_inputs_v067(uuid)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
commit;
