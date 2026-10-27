-- Phase 29: a season is one league or two leagues (A and B).
-- The structure is part of the versioned config: division_sizes {A} (one
-- league, division_count 1) or {A,B} (two leagues, division_count 2, exactly
-- as before). One league has no movement and no last-of-B reward, and its
-- initial assignment creates only that league. Once a season has started the
-- structure cannot change; history and two-league seasons keep their shape.
begin;

alter table public.season_config_versions
  drop constraint config_division_sizes_shape,
  add constraint config_division_sizes_shape check (division_sizes is null or
    (jsonb_typeof(division_sizes) = 'object' and division_sizes ? 'A'
     and division_sizes - 'A' - 'B' = '{}'::jsonb
     and (division_sizes->>'A')::integer > 0
     and (not division_sizes ? 'B' or (division_sizes->>'B')::integer > 0))),
  add constraint config_division_count_shape check (division_sizes is null
    or division_count = case when division_sizes ? 'B' then 2 else 1 end);

create function public.config_division_count(sizes jsonb) returns integer
language sql immutable set search_path = pg_catalog, public as $$
  select case when sizes ? 'B' then 2 else 1 end
$$;

-- Every config of a season shares one structure. A started season (active or
-- later, or with divisions) keeps the structure it started with.
create function public.admin_setup_structure_guard(sid uuid,cid uuid,b jsonb) returns void
language plpgsql set search_path = pg_catalog, public as $$
declare wanted integer=public.config_division_count(b->'division_sizes');
begin
  if (exists(select 1 from public.seasons where id=sid and status<>'draft')
      or exists(select 1 from public.divisions where season_id=sid))
    and (exists(select 1 from public.season_config_versions where season_id=sid
        and division_sizes is not null and division_count<>wanted)
      or (select count(*) from public.divisions where season_id=sid) not in (0,wanted)) then
    perform public.admin_setup_fail('competition_structure_locked');
  end if;
  if exists(select 1 from public.season_config_versions where season_id=sid and id is distinct from cid
      and division_sizes is not null and division_count<>wanted) then
    perform public.admin_setup_fail('competition_structure_mismatch');
  end if;
end $$;

create or replace function public.admin_setup_validate_config(sid uuid,b jsonb) returns void
language plpgsql set search_path = pg_catalog, public as $$
declare n integer; a integer; z integer; single boolean; effective integer; total integer; k text; rewards jsonb; v jsonb;
begin
  select count(*) into n from public.season_players where season_id=sid;
  if n=0 or exists(select 1 from public.season_players where season_id=sid and status<>'active') then
    perform public.admin_setup_fail('invalid_roster');
  end if;
  if jsonb_typeof(b->'division_sizes') is distinct from 'object'
     or not (b->'division_sizes' ? 'A') or (b->'division_sizes')-'A'-'B'<>'{}'::jsonb then
    perform public.admin_setup_fail('invalid_config');
  end if;
  -- Without B the season is one league: no movement and no last-of-B reward.
  -- It needs the observed initial assignment, which creates only that league.
  single=not (b->'division_sizes' ? 'B');
  a=(b->'division_sizes'->>'A')::integer; z=coalesce((b->'division_sizes'->>'B')::integer,0);
  if single and (not public.initial_assignment_modern(sid) or b#>'{rules,last_b_gets_steal}'='true'::jsonb) then
    perform public.admin_setup_fail('invalid_config');
  end if;
  effective=(b->>'effective_from_matchday')::integer; total=(b->>'total_matchdays')::integer;
  if a<=0 or (z<=0 and not single) or a+z<>n or (b->>'movement_count')::integer not between 0 and least(a,z)
    or total<1 or effective not between 1 and total or length(btrim(b->>'name')) not between 1 and 120 then
    perform public.admin_setup_fail('invalid_config');
  end if;
  foreach k in array array['scoring','coin_rewards'] loop
    rewards=b->k;
    if jsonb_typeof(rewards) is distinct from 'object'
      or (select count(*) from jsonb_object_keys(rewards))<>n then
      perform public.admin_setup_fail('invalid_rewards');
    end if;
    for i in 1..n loop
      v=rewards->i::text;
      if jsonb_typeof(v) is distinct from 'number' or v::text !~ '^[0-9]+$' then
        perform public.admin_setup_fail('invalid_rewards');
      end if;
    end loop;
  end loop;
  if jsonb_typeof(b->'rules') is distinct from 'object' or
    (b->'rules')-'team_lock_required'-'last_b_gets_steal'-'badge_reward_coins'-'game_completion_reward_coins'<>'{}'::jsonb or
    jsonb_typeof(b->'rules'->'team_lock_required') is distinct from 'boolean' or
    jsonb_typeof(b->'rules'->'last_b_gets_steal') is distinct from 'boolean' then
    perform public.admin_setup_fail('invalid_config');
  end if;
  foreach k in array array['badge_reward_coins','game_completion_reward_coins'] loop
    if b->'rules' ? k then
      v=b->'rules'->k;
      if jsonb_typeof(v) is distinct from 'number' or v::text !~ '^[0-9]+$'
        or length(v::text)>10 or v::numeric>2147483647 then
        perform public.admin_setup_fail('invalid_rewards'); end if;
    end if;
  end loop;
end $$;

create or replace function public.api_admin_create_config(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare cached jsonb; sid uuid=(p_request->>'season_id')::uuid; b jsonb=p_request->'body'; cid uuid;
begin
  cached=public.admin_setup_begin('create_config',p_request); if cached is not null then return cached; end if;
  perform public.admin_setup_cas(sid,b); perform public.admin_setup_validate_config(sid,b); perform public.admin_setup_config_window(sid,b);
  perform public.admin_setup_structure_guard(sid,null,b);
  if exists(select 1 from public.season_config_versions where season_id=sid and effective_from_matchday=(b->>'effective_from_matchday')::integer) then
    perform public.admin_setup_fail('effective_round_exists'); end if;
  insert into public.season_config_versions(season_id,version_number,name,effective_from_matchday,total_matchdays,
    division_count,promotion_relegation_count,scoring_json,coin_rewards_json,rules_json,division_sizes,roster_revision,created_by_trainer_id)
    values(sid,(select coalesce(max(version_number),0)+1 from public.season_config_versions where season_id=sid),
      b->>'name',(b->>'effective_from_matchday')::integer,(b->>'total_matchdays')::integer,public.config_division_count(b->'division_sizes'),(b->>'movement_count')::integer,
      b->'scoring',b->'coin_rewards',b->'rules',b->'division_sizes',(b->>'expected_roster_revision')::bigint,(p_request->>'actor_trainer_id')::uuid)
    returning id into cid;
  update public.season_admin_state set config_revision=config_revision+1,setup_revision=setup_revision+1 where season_id=sid;
  return public.admin_setup_finish('create_config',p_request,sid,cid);
end $$;

create or replace function public.api_admin_replace_config(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare cached jsonb; sid uuid=(p_request->>'season_id')::uuid; b jsonb=p_request->'body'; cid uuid=(p_request->>'resource_id')::uuid; old public.season_config_versions;
begin
  cached=public.admin_setup_begin('replace_config',p_request); if cached is not null then return cached; end if;
  select * into old from public.season_config_versions where id=cid and season_id=sid for update;
  if not found then perform public.admin_setup_fail('config_not_found',404); end if;
  if public.admin_setup_config_used(cid) then perform public.admin_setup_fail('config_already_used'); end if;
  perform public.admin_setup_cas(sid,b); perform public.admin_setup_validate_config(sid,b); perform public.admin_setup_config_window(sid,b);
  perform public.admin_setup_structure_guard(sid,cid,b);
  if old.effective_from_matchday<>(b->>'effective_from_matchday')::integer or length(btrim(b->>'reason')) not between 1 and 500 then
    perform public.admin_setup_fail('invalid_config'); end if;
  if old.effective_from_matchday=1 and exists(select 1 from public.division_memberships where season_id=sid)
    and old.division_sizes is distinct from b->'division_sizes' then perform public.admin_setup_fail('initial_setup_locked'); end if;
  update public.season_config_versions set name=b->>'name',total_matchdays=(b->>'total_matchdays')::integer,
    promotion_relegation_count=(b->>'movement_count')::integer,scoring_json=b->'scoring',coin_rewards_json=b->'coin_rewards',
    rules_json=b->'rules',division_sizes=b->'division_sizes',division_count=public.config_division_count(b->'division_sizes'),roster_revision=(b->>'expected_roster_revision')::bigint where id=cid;
  update public.season_admin_state set config_revision=config_revision+1,setup_revision=setup_revision+1 where season_id=sid;
  return public.admin_setup_finish('replace_config',p_request,sid,cid,
    jsonb_build_object('reason',b->>'reason','before',to_jsonb(old),'after',b));
end $$;

create or replace function public.api_admin_finalize_initial_assignment(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare r jsonb=p_request->'request'; b jsonb=r->'body'; sid uuid=(r->>'season_id')::uuid;
  plan jsonb=p_request->'plan'; ctx jsonb; cached jsonb; assignments jsonb=plan->'assignments';
  division_code text; division_id uuid; day_id uuid; cid uuid; n integer; cut integer; ids jsonb;
  ordered jsonb; boundary jsonb; boundary_ids jsonb; chosen jsonb; tie jsonb=b->'tie_resolution'; threshold bigint; boundary_start integer;
begin
  cached=public.admin_setup_begin('initial_assignment',r); if cached is not null then return cached; end if;
  if not public.initial_assignment_modern(sid) or exists(select 1 from public.initial_division_snapshots where season_id=sid) then
    perform public.admin_setup_fail('initial_assignment_locked'); end if;
  perform public.admin_setup_cas(sid,b);
  ctx=public.initial_assignment_inputs(sid);
  if b->>'input_hash' is distinct from ctx->>'input_hash'
    or p_request->>'input_hash' is distinct from ctx->>'input_hash' then
    perform public.admin_setup_fail('initial_assignment_review_stale'); end if;
  if not (ctx->>'ready')::boolean then perform public.admin_setup_fail('initial_assignment_not_ready'); end if;
  cid=(ctx->>'config_version_id')::uuid;
  if (b->>'config_version_id')::uuid is distinct from cid then perform public.admin_setup_fail('config_not_effective'); end if;
  n=jsonb_array_length(ctx->'players'); cut=(ctx#>>'{division_sizes,A}')::integer;
  if jsonb_typeof(assignments) is distinct from 'object' or assignments-'A'-'B'<>'{}'::jsonb
    or jsonb_typeof(assignments->'A') is distinct from 'array' or jsonb_typeof(assignments->'B') is distinct from 'array'
    or plan#>>'{audit,rule}' is distinct from 'observed_deaths_v1'
    or plan#>>'{audit,input_hash}' is distinct from ctx->>'input_hash' then
    perform public.admin_setup_fail('invalid_initial_assignment_plan'); end if;
  ids=(assignments->'A')||(assignments->'B');
  if jsonb_array_length(ids)<>n or jsonb_array_length(assignments->'A')<>cut
    or (select count(distinct value) from jsonb_array_elements(ids))<>n
    or exists((select value from jsonb_array_elements(ids) except select p->'id' from jsonb_array_elements(ctx->'players') p)
      union all (select p->'id' from jsonb_array_elements(ctx->'players') p except select value from jsonb_array_elements(ids))) then
    perform public.admin_setup_fail('invalid_initial_assignment_plan'); end if;
  select jsonb_agg(p order by (p->>'adjusted_deaths')::bigint,p->>'id') into ordered from jsonb_array_elements(ctx->'players') p;
  threshold=(ordered->(cut-1)->>'adjusted_deaths')::bigint;
  if threshold=(ordered->cut->>'adjusted_deaths')::bigint then
    select jsonb_agg(p order by p->>'id') into boundary from jsonb_array_elements(ordered) p
      where (p->>'adjusted_deaths')::bigint=threshold;
    select jsonb_agg(p->'id' order by p->>'id') into boundary_ids from jsonb_array_elements(boundary) p;
    select count(*) into boundary_start from jsonb_array_elements(ordered) p where (p->>'adjusted_deaths')::bigint<threshold;
    if tie is null or tie='null'::jsonb then perform public.admin_setup_fail('initial_boundary_tie_unresolved'); end if;
    if tie->>'input_hash' is distinct from ctx->>'input_hash' then perform public.admin_setup_fail('initial_assignment_review_stale'); end if;
    if jsonb_typeof(tie->'orders') is distinct from 'array' or jsonb_array_length(tie->'orders')<>1
      or jsonb_typeof(tie#>'{orders,0,player_ids}') is distinct from 'array'
      or jsonb_typeof(tie#>'{orders,0,reason}') is distinct from 'string'
      or length(btrim(tie#>>'{orders,0,reason}')) not between 1 and 500 then
      perform public.admin_setup_fail('invalid_tie_resolution'); end if;
    chosen=tie#>'{orders,0,player_ids}';
    if jsonb_array_length(chosen)<>jsonb_array_length(boundary_ids)
      or (select count(distinct value) from jsonb_array_elements(chosen))<>jsonb_array_length(chosen)
      or exists((select value from jsonb_array_elements(chosen) except select value from jsonb_array_elements(boundary_ids))
       union all(select value from jsonb_array_elements(boundary_ids) except select value from jsonb_array_elements(chosen))) then
      perform public.admin_setup_fail('invalid_tie_resolution'); end if;
    if exists(select 1 from jsonb_array_elements(chosen) with ordinality x(pid,ord)
      where (ord<=cut-boundary_start) is distinct from ((assignments->'A') ? (pid#>>'{}'))) then
      perform public.admin_setup_fail('invalid_initial_assignment_plan'); end if;
  elsif tie is not null and tie<>'null'::jsonb then perform public.admin_setup_fail('invalid_tie_resolution'); end if;
  -- Technical order may transport neutral blocks; only deaths and the explicit
  -- boundary decision can decide which side receives a participant.
  if exists(select 1 from jsonb_array_elements(ordered) p
    where ((p->>'adjusted_deaths')::bigint<threshold and not((assignments->'A') ? (p->>'id')))
      or ((p->>'adjusted_deaths')::bigint>threshold and ((assignments->'A') ? (p->>'id')))) then
    perform public.admin_setup_fail('invalid_initial_assignment_plan'); end if;
  if plan#>'{audit,resolution}' is distinct from coalesce(tie#>'{orders,0}','null'::jsonb)
    or plan#>'{audit,boundary_tie}' is distinct from (case when boundary_ids is null then 'null'::jsonb else
      jsonb_build_object('player_ids',boundary_ids,'adjusted_deaths',threshold,'places_in_a',cut-boundary_start) end) then
    perform public.admin_setup_fail('invalid_initial_assignment_plan'); end if;
  -- One league creates only its own division: never an empty B.
  foreach division_code in array case when ctx->'division_sizes' ? 'B' then array['A','B'] else array['A'] end loop
    insert into public.divisions(season_id,code,name,tier_order)
      values(sid,division_code,case when ctx->'division_sizes' ? 'B' then 'Division '||division_code else 'Liga' end,
        case division_code when 'A' then 1 else 2 end) returning id into division_id;
    insert into public.division_memberships(season_id,season_player_id,division_id,effective_from_matchday_number,reason)
      select sid,value::uuid,division_id,1,'initial' from jsonb_array_elements_text(assignments->division_code);
  end loop;
  insert into public.matchdays(season_id,number,season_config_version_id) values(sid,1,cid) returning id into day_id;
  insert into public.matches(season_id,matchday_id,division_id,player_a_id,player_b_id)
    select sid,day_id,m.division_id,m.season_player_id,x.season_player_id from public.division_memberships m
    join public.division_memberships x on x.division_id=m.division_id and m.season_player_id<x.season_player_id
    where m.season_id=sid order by m.division_id,m.season_player_id,x.season_player_id;
  insert into public.initial_division_snapshots(season_id,config_version_id,rule,input_hash,inputs,assignments,audit,actor_trainer_id)
    values(sid,cid,'observed_deaths_v1',ctx->>'input_hash',ctx,assignments,plan->'audit',(r->>'actor_trainer_id')::uuid);
  update public.seasons set current_matchday_id=day_id where id=sid;
  update public.season_admin_state set setup_revision=setup_revision+1 where season_id=sid;
  return public.admin_setup_finish('initial_assignment',r,sid,day_id,jsonb_build_object('rule','observed_deaths_v1',
    'input_hash',ctx->>'input_hash','assignments',assignments,'resolution',tie));
end $$;

revoke all on function public.config_division_count(jsonb),
  public.admin_setup_structure_guard(uuid,uuid,jsonb) from public, anon, authenticated;
grant execute on function public.config_division_count(jsonb),
  public.admin_setup_structure_guard(uuid,uuid,jsonb) to service_role;
notify pgrst,'reload schema';
commit;
