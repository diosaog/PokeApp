-- Phase 10.5E. Initial divisions from observed save progress and adjusted deaths.
-- Historical seasons retain their original setup/ranking contract.
begin;

create table public.initial_division_snapshots (
  season_id uuid primary key references public.seasons(id) on delete restrict,
  config_version_id uuid not null references public.season_config_versions(id) on delete restrict,
  rule text not null check(rule='observed_deaths_v1'),
  input_hash text not null check(input_hash ~ '^[a-f0-9]{64}$'),
  inputs jsonb not null,
  assignments jsonb not null,
  audit jsonb not null,
  actor_trainer_id uuid not null references public.trainers(id) on delete restrict,
  created_at timestamptz not null default now()
);
alter table public.initial_division_snapshots enable row level security;
revoke all on public.initial_division_snapshots from public,anon,authenticated;
grant select,insert,delete on public.initial_division_snapshots to service_role;
revoke update,truncate on public.initial_division_snapshots from service_role;

create function public.initial_assignment_modern(sid uuid) returns boolean
language sql stable security invoker set search_path=pg_catalog,public as $$
  select coalesce((select metadata->>'initial_assignment_rule'='observed_deaths_v1'
    from public.seasons where id=sid),false)
$$;

create or replace function public.admin_setup_config_used(cid uuid) returns boolean
language sql stable security invoker set search_path=pg_catalog,public as $$
  select exists(select 1 from public.matchdays where season_config_version_id=cid)
    or exists(select 1 from public.matchday_snapshots where config_version_id=cid)
    or exists(select 1 from public.initial_division_snapshots where config_version_id=cid)
$$;

alter function public.api_admin_create_season(jsonb) rename to api_admin_create_season_v035;
create function public.api_admin_create_season(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare result jsonb;
begin
  result=public.api_admin_create_season_v035(p_request);
  if not (result->>'replayed')::boolean then
    update public.seasons set metadata=metadata||'{"initial_assignment_rule":"observed_deaths_v1"}'::jsonb
      where id=(result->>'season_id')::uuid;
  end if;
  return result;
end $$;

create function public.initial_assignment_observations(sid uuid) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare p record; saved public.save_files; parsed public.parsed_saves; ident public.pokemon_identity_revisions;
  envelope jsonb; progress jsonb; regions jsonb; flags jsonb; box jsonb;
  primary_region text; expected_regions jsonb; valid boolean; source_valid boolean; progress_valid boolean; badges integer; deaths bigint;
  result jsonb='[]'; provenance jsonb; revive_count bigint; wipe_count integer;
begin
  if (select count(*) from public.season_players where season_id=sid)>500 then
    perform public.admin_setup_fail('read_capacity_exceeded',503); end if;
  -- Row locks bind the selected owned save, parsed evidence and adjustments to one
  -- observation. Identity commits use the same participant lock before save rows.
  perform 1 from public.season_players where season_id=sid order by id for update;
  for p in select sp.*,t.display_name,t.globally_enabled from public.season_players sp
    join public.trainers t on t.id=sp.trainer_id where sp.season_id=sid order by sp.id loop
    saved=null; parsed=null; ident=null; flags=null; badges=null; deaths=null;
    select * into saved from public.save_files where id=p.current_save_file_id
      and season_id=sid and trainer_id=p.trainer_id for share;
    select * into ident from public.pokemon_identity_revisions where save_file_id=saved.id
      and season_id=sid and trainer_id=p.trainer_id for share;
    select * into parsed from public.parsed_saves where id=ident.parsed_save_id
      and save_file_id=saved.id for share;
    select revived_after_wipe into wipe_count from public.season_player_stats
      where season_player_id=p.id for share;
    perform 1 from public.pokemon_observations where save_file_id=saved.id order by id for share;
    envelope=parsed.payload->'observed_progress'; progress=envelope->'progress';
    valid=saved.id is not null and saved.deleted_at is null and saved.parser_status='parsed'
      and parsed.id is not null and parsed.status='parsed' and parsed.schema_version=1
      and saved.parser_version='pokeapp-reader/2;pkhex/24.11.11'
      and parsed.parser_version=saved.parser_version
      and (not(parsed.payload ? 'save_record_id') or parsed.payload->>'save_record_id'=saved.id::text)
      and (not(parsed.payload ? 'trainer_id') or parsed.payload->>'trainer_id'=p.trainer_id::text)
      and (not(parsed.payload ? 'source_hash') or parsed.payload->>'source_hash'=saved.sha256)
      and envelope->'schema_version'='1'::jsonb and envelope->>'source_hash'=saved.sha256;
    source_valid=coalesce(valid,false);
    primary_region=case
      when envelope->>'game' in ('R','S','RS','E') and envelope->'generation'='3'::jsonb then 'hoenn'
      when envelope->>'game' in ('FR','LG','FRLG') and envelope->'generation'='3'::jsonb then 'kanto'
      when envelope->>'game' in ('D','P','DP','Pt') and envelope->'generation'='4'::jsonb then 'sinnoh'
      when envelope->>'game' in ('HG','SS','HGSS') and envelope->'generation'='4'::jsonb then 'johto'
      when envelope->>'game' in ('B','W','BW','B2','W2','B2W2') and envelope->'generation'='5'::jsonb then 'unova'
      end;
    expected_regions=case when primary_region='johto' then '["johto","kanto"]'::jsonb
      else jsonb_build_array(primary_region) end;
    valid=source_valid and progress->'schema_version'='1'::jsonb and primary_region is not null
      and progress->>'primary_region'=primary_region and jsonb_typeof(progress->'regions')='array';
    if valid then
      select jsonb_agg(r->'region' order by ord) into regions
        from jsonb_array_elements(progress->'regions') with ordinality x(r,ord);
      valid=regions=expected_regions;
      for box in select value from jsonb_array_elements(progress->'regions') loop
        if jsonb_typeof(box->'badge_flags') is distinct from 'array' then valid=false; exit; end if;
        if jsonb_array_length(box->'badge_flags')<>8 or exists(select 1
          from jsonb_array_elements(box->'badge_flags') f where jsonb_typeof(f)<>'boolean') then valid=false; exit; end if;
      end loop;
      flags=progress#>'{regions,0,badge_flags}';
    end if;
    progress_valid=coalesce(valid,false);
    if progress_valid then
      select count(*) into badges from jsonb_array_elements(flags) f where f='true'::jsonb;
    end if;
    -- Absence from a partially parsed box cannot be interpreted as zero deaths.
    valid=source_valid and wipe_count is not null and jsonb_typeof(parsed.payload->'boxes')='array';
    if valid then
      if (select count(*) from jsonb_array_elements(parsed.payload->'boxes') b where b->'box_number'='8'::jsonb)<>1 then
        valid=false;
      else
        select b into box from jsonb_array_elements(parsed.payload->'boxes') b where b->'box_number'='8'::jsonb;
        valid=jsonb_typeof(box->'slots')='array';
        if valid then
          valid=jsonb_array_length(box->'slots')=30 and not exists(select 1 from generate_series(1,30) n
            where (select count(*) from jsonb_array_elements(box->'slots') slot where slot->'slot_number'=to_jsonb(n))<>1)
            and not exists(select 1 from jsonb_array_elements(box->'slots') slot where not(slot ? 'pokemon')
              or jsonb_typeof(slot->'pokemon') not in ('object','null'));
          if valid then
            valid=not exists(
              (select (slot->>'slot_number')::integer,slot#>'{pokemon,identity_evidence}'
                 from jsonb_array_elements(box->'slots') slot where slot->'pokemon'<>'null'::jsonb
               except select slot_number,evidence from public.pokemon_observations
                 where revision_id=ident.id and source='box' and box_number=8)
              union all
              (select slot_number,evidence from public.pokemon_observations
                 where revision_id=ident.id and source='box' and box_number=8
               except select (slot->>'slot_number')::integer,slot#>'{pokemon,identity_evidence}'
                 from jsonb_array_elements(box->'slots') slot where slot->'pokemon'<>'null'::jsonb));
          end if;
        end if;
      end if;
    end if;
    select greatest((select count(*) from public.redemptions e where e.season_id=sid
      and e.trainer_id=p.trainer_id and e.effect_code='revive' and e.status='applied'),
      (select count(*) from public.purchases u join public.shop_items i on i.id=u.shop_item_id
       where u.season_player_id=p.id and u.status='used' and i.code='revivir_pokemon')) into revive_count;
    if coalesce(valid,false) then
      select count(*)+revive_count+2::bigint*wipe_count into deaths from public.pokemon_observations
        where save_file_id=saved.id and source='box' and box_number=8;
    end if;
    provenance=jsonb_build_object('status',p.status,'status_effective_matchday_number',p.status_effective_matchday_number,
      'globally_enabled',p.globally_enabled,'save_file_id',saved.id,'source_hash',saved.sha256,
      'deleted_at',saved.deleted_at,'parser_status',saved.parser_status,'parser_version',saved.parser_version,
      'parsed_save_id',parsed.id,'parsed_hash',encode(sha256(convert_to(coalesce(parsed.payload::text,''),'UTF8')),'hex'),
      'identity_revision_id',ident.id,'identity_signature',ident.input_signature,'revivals',revive_count,'wipes',wipe_count,
      'observed_progress',case when progress_valid then jsonb_build_object('schema_version',1,
        'game',envelope->>'game','generation',envelope->'generation','source_hash',saved.sha256,
        'progress',jsonb_build_object('schema_version',1,'primary_region',primary_region,'regions',
          (select jsonb_agg(jsonb_build_object('region',item->>'region','badge_flags',item->'badge_flags') order by ord)
           from jsonb_array_elements(progress->'regions') with ordinality x(item,ord)))) end);
    result=result||jsonb_build_array(jsonb_build_object('id',p.id,'trainer_id',p.trainer_id,
      'display_name',p.display_name,'progress_state',case when progress_valid then 'observed' else 'unknown' end,
      'observed_badges',badges,'cap_reached',coalesce(progress_valid and flags->0='true'::jsonb and flags->1='true'::jsonb,false),
      'adjusted_deaths',deaths,'_source',provenance));
  end loop;
  return result;
end $$;

alter function public.api_admin_initial_divisions(jsonb) rename to api_admin_initial_divisions_v035;
create function public.api_admin_initial_divisions(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  perform public.admin_setup_principal((p_request->>'actor_trainer_id')::uuid);
  if public.initial_assignment_modern((p_request->>'season_id')::uuid) then
    perform public.admin_setup_fail('initial_assignment_required');
  end if;
  return public.api_admin_initial_divisions_v035(p_request);
end $$;

alter function public.api_admin_prepare_first_matchday(jsonb) rename to api_admin_prepare_first_matchday_v035;
create function public.api_admin_prepare_first_matchday(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  perform public.admin_setup_principal((p_request->>'actor_trainer_id')::uuid);
  if public.initial_assignment_modern((p_request->>'season_id')::uuid) then
    perform public.admin_setup_fail('initial_assignment_required');
  end if;
  return public.api_admin_prepare_first_matchday_v035(p_request);
end $$;

alter function public.admin_setup_readiness(uuid) rename to admin_setup_readiness_v035;
create function public.admin_setup_readiness(sid uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare result jsonb; checks jsonb; reasons jsonb;
begin
  result=public.admin_setup_readiness_v035(sid);
  if not public.initial_assignment_modern(sid) then return result; end if;
  -- A modern season starts its first gameplay leg before divisions exist.
  -- This permits collecting saves; it does not permit competitive results.
  checks=jsonb_build_object('has_roster',result#>'{checks,has_roster}',
    'has_valid_config',result#>'{checks,has_valid_config}',
    'no_other_active_season',result#>'{checks,no_other_active_season}',
    'is_draft',result#>'{checks,is_draft}',
    'initial_assignment_pending',not exists(select 1 from public.division_memberships where season_id=sid)
      and not exists(select 1 from public.matchdays where season_id=sid));
  select coalesce(jsonb_agg(key order by key),'[]'::jsonb) into reasons
    from jsonb_each(checks) where value is distinct from 'true'::jsonb;
  return jsonb_build_object('checks',checks,'blocking_reasons',reasons,'can_activate',reasons='[]'::jsonb);
end $$;

alter function public.api_admin_get_setup(jsonb) rename to api_admin_get_setup_v035;
create function public.api_admin_get_setup(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  return public.api_admin_get_setup_v035(p_request)||jsonb_build_object('initial_assignment_rule',
    case when public.initial_assignment_modern((p_request->>'season_id')::uuid) then 'observed_deaths_v1' end);
end $$;

create function public.initial_assignment_inputs(sid uuid) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare s public.seasons; a public.season_admin_state; cfg public.season_config_versions;
  frozen public.initial_division_snapshots; players jsonb; reasons jsonb='[]'; result jsonb; fingerprint jsonb; valid_config boolean=false;
begin
  select * into s from public.seasons where id=sid;
  if not found or s.status='discarded' then perform public.admin_setup_fail('season_not_found',404); end if;
  select * into a from public.season_admin_state where season_id=sid;
  if not public.initial_assignment_modern(sid) then
    return jsonb_build_object('season_id',sid,'rule',null,'state','legacy','config_version_id',null,
      'division_sizes',null,'setup_revision',coalesce(a.setup_revision,0),'roster_revision',coalesce(a.roster_revision,0),
      'input_hash',encode(sha256(convert_to(sid::text||':legacy','UTF8')),'hex'),'ready',false,
      'blocking_reasons','["initial_assignment_legacy"]'::jsonb,'players','[]'::jsonb);
  end if;
  select * into frozen from public.initial_division_snapshots where season_id=sid;
  if found then
    return frozen.inputs||jsonb_build_object('state','assigned','ready',false,
      'assignments',frozen.assignments,'blocking_reasons','["initial_assignment_locked"]'::jsonb);
  end if;
  select * into cfg from public.season_config_versions where season_id=sid and effective_from_matchday=1 for share;
  players=public.initial_assignment_observations(sid);
  if cfg.id is not null and cfg.roster_revision=a.roster_revision then
    begin
      perform public.admin_setup_validate_config(sid,jsonb_build_object('name',cfg.name,'division_sizes',cfg.division_sizes,
        'effective_from_matchday',1,'total_matchdays',cfg.total_matchdays,'movement_count',cfg.promotion_relegation_count,
        'scoring',cfg.scoring_json,'coin_rewards',cfg.coin_rewards_json,'rules',cfg.rules_json));
      valid_config=true;
    exception when sqlstate 'PT409' then valid_config=false; end;
  end if;
  if s.status<>'active' then reasons=reasons||'"season_not_active"'::jsonb; end if;
  if jsonb_array_length(players)=0 or exists(select 1 from jsonb_array_elements(players) p
    where p#>>'{_source,status}'<>'active' or p#>'{_source,globally_enabled}'<>'true'::jsonb) then
    reasons=reasons||'"invalid_roster"'::jsonb;
  end if;
  if not valid_config then reasons=reasons||'"config_not_effective"'::jsonb; end if;
  if exists(select 1 from jsonb_array_elements(players) p where p->>'progress_state'='unknown') then
    reasons=reasons||'"progress_unobserved"'::jsonb;
  end if;
  if exists(select 1 from jsonb_array_elements(players) p where p->>'progress_state'='observed' and p->'cap_reached'<>'true'::jsonb) then
    reasons=reasons||'"cap_not_reached"'::jsonb;
  end if;
  if exists(select 1 from jsonb_array_elements(players) p where p->'adjusted_deaths'='null'::jsonb) then
    reasons=reasons||'"death_inputs_unobserved"'::jsonb;
  end if;
  if exists(select 1 from public.division_memberships where season_id=sid)
    or exists(select 1 from public.matchdays where season_id=sid) then
    reasons=reasons||'"initial_assignment_locked"'::jsonb;
  end if;
  result=jsonb_build_object('season_id',sid,'rule','observed_deaths_v1','state','pending',
    'config_version_id',cfg.id,'division_sizes',cfg.division_sizes,'setup_revision',a.setup_revision,
    'roster_revision',a.roster_revision,'ready',reasons='[]'::jsonb,'blocking_reasons',reasons,'players',players);
  fingerprint=jsonb_build_object('season_status',s.status,'setup_revision',a.setup_revision,'roster_revision',a.roster_revision,
    'config',to_jsonb(cfg),'players',(select jsonb_agg(p-'display_name' order by p->>'id') from jsonb_array_elements(players) p));
  return result||jsonb_build_object('input_hash',encode(sha256(convert_to(fingerprint::text,'UTF8')),'hex'));
end $$;

create function public.initial_assignment_context(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare r jsonb=p_request->'request'; sid uuid=(r->>'season_id')::uuid; cached jsonb;
begin
  if p_request->>'operation'='finalize' then
    cached=public.admin_setup_begin('initial_assignment',r);
    if cached is not null then return jsonb_build_object('receipt',cached); end if;
  elsif p_request->>'operation'='read' then
    if not exists(select 1 from public.trainers where id=(r->>'actor_trainer_id')::uuid and globally_enabled) then
      perform public.admin_setup_fail('trainer_disabled',403);
    end if;
    perform 1 from public.seasons where id=sid for share;
    if not found then perform public.admin_setup_fail('season_not_found',404); end if;
  else perform public.admin_setup_fail('invalid_request',422); end if;
  return public.initial_assignment_inputs(sid);
end $$;

create function public.api_admin_finalize_initial_assignment(p_request jsonb) returns jsonb
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
  foreach division_code in array array['A','B'] loop
    insert into public.divisions(season_id,code,name,tier_order)
      values(sid,division_code,'Division '||division_code,case division_code when 'A' then 1 else 2 end) returning id into division_id;
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

alter function public.matchday_validate(uuid,uuid,boolean) rename to matchday_validate_v035;
create function public.matchday_validate(sid uuid,did uuid,complete boolean) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare players jsonb;
begin
  perform public.matchday_validate_v035(sid,did,complete);
  if public.initial_assignment_modern(sid) and exists(select 1 from public.matchdays where id=did and number=1) then
    if not exists(select 1 from public.initial_division_snapshots where season_id=sid) then
      perform public.admin_setup_fail('initial_assignment_required'); end if;
    players=public.initial_assignment_observations(sid);
    if exists(select 1 from jsonb_array_elements(players) p
      where (p#>>'{_source,status}'='active' or coalesce((p#>>'{_source,status_effective_matchday_number}')::integer,0)>1)
        and (p->'cap_reached'<>'true'::jsonb or p->>'progress_state'<>'observed')) then
      perform public.admin_setup_fail('initial_assignment_not_ready'); end if;
    if complete and exists(select 1 from jsonb_array_elements(players) p
      where (p#>>'{_source,status}'='active' or coalesce((p#>>'{_source,status_effective_matchday_number}')::integer,0)>1)
        and p->'adjusted_deaths'='null'::jsonb) then
      perform public.admin_setup_fail('ranking_inputs_unavailable'); end if;
  end if;
end $$;

alter function public.league_general_read(uuid) rename to league_general_read_v035;
create function public.league_general_read(p_season_id uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare result jsonb;
begin
  result=public.league_general_read_v035(p_season_id);
  if result is null then return result; end if;
  return jsonb_set(result,'{season,initial_assignment_rule}',
    case when public.initial_assignment_modern(p_season_id) then '"observed_deaths_v1"'::jsonb else 'null'::jsonb end);
end $$;

do $$ declare f regprocedure; begin
  for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and (p.proname like 'initial_assignment_%'
      or p.proname in ('api_admin_finalize_initial_assignment','api_admin_create_season','api_admin_create_season_v035',
        'api_admin_initial_divisions','api_admin_initial_divisions_v035','api_admin_prepare_first_matchday',
        'api_admin_prepare_first_matchday_v035','admin_setup_readiness','admin_setup_readiness_v035',
        'api_admin_get_setup','api_admin_get_setup_v035','matchday_validate','matchday_validate_v035',
        'league_general_read','league_general_read_v035')) loop
    execute format('revoke all on function %s from public,anon,authenticated',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
