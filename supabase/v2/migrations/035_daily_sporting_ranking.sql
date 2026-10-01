-- Phase 10.5D: rule provenance and audited tie decisions in existing snapshots.
-- No historic rows rewritten; pre-D corrections retain the frozen old rule.
begin;

alter function public.matchday_context(text,jsonb) rename to matchday_context_v034;
create function public.matchday_context(op text,r jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare ctx jsonb; rule text;
begin
  ctx=public.matchday_context_v034(op,r);
  if op='correct' then
    select coalesce(snapshot#>>'{inputs,ranking,rule}','legacy_pre_10_5d') into rule
      from public.matchday_snapshots where matchday_id=(r->>'resource_id')::uuid;
  else rule='wins_adjusted_deaths_v1'; end if;
  if rule is null or rule not in ('legacy_pre_10_5d','wins_adjusted_deaths_v1') then
    perform public.admin_setup_fail('historical_source_invalid'); end if;
  return ctx||jsonb_build_object('ranking_rule',rule);
end $$;

alter function public.matchday_commit_close(text,jsonb,jsonb,jsonb) rename to matchday_commit_close_v034;
create function public.matchday_commit_close(op text,r jsonb,ctx jsonb,plan jsonb) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare row jsonb; n integer; pos integer; lastpos integer; allocation integer;
  rule text=ctx->>'ranking_rule';
begin
  if rule is null or plan#>>'{ranking,rule}' is distinct from rule
    or (op='close' and rule<>'wins_adjusted_deaths_v1') then
    perform public.admin_setup_fail('invalid_results'); end if;
  if rule='wins_adjusted_deaths_v1' then
    n=jsonb_array_length(plan->'standings');
    if jsonb_typeof(plan#>'{ranking,groups}') is distinct from 'array'
      or jsonb_typeof(plan#>'{ranking,resolutions}') is distinct from 'array'
      or plan#>>'{ranking,input_hash}' is null
      or (plan#>>'{ranking,input_hash}') !~ '^[a-f0-9]{64}$'
      or n<>(select count(distinct (x#>>'{metadata,allocation_position}')::integer)
        from jsonb_array_elements(plan->'standings') x
        where (x#>>'{metadata,allocation_position}')::integer between 1 and n) then
      perform public.admin_setup_fail('invalid_results'); end if;
    if jsonb_array_length(plan#>'{ranking,resolutions}')>0 then
      if r#>>'{body,tie_resolution,input_hash}' is distinct from plan#>>'{ranking,input_hash}'
        or r#>'{body,tie_resolution,orders}' is distinct from plan#>'{ranking,resolutions}' then
        perform public.admin_setup_fail('invalid_results'); end if;
    elsif r#>'{body,tie_resolution}' is not null then
      perform public.admin_setup_fail('invalid_results'); end if;
    for row in select value from jsonb_array_elements(plan->'standings') loop
      pos=(row->>'position')::integer;
      lastpos=(row#>>'{metadata,position_end}')::integer;
      allocation=(row#>>'{metadata,allocation_position}')::integer;
      if row#>>'{metadata,ranking_rule}' is distinct from rule
        or pos is null or lastpos is null or allocation is null
        or pos<1 or lastpos>n or allocation not between pos and lastpos then
        perform public.admin_setup_fail('invalid_results'); end if;
      if lastpos>pos then
        -- A neutral group shares its sporting rank. The allocation index is only
        -- an integrity slot, never an alternative sporting winner.
        if pos<=3 or row#>>'{metadata,tie_status}' is distinct from 'unresolved_neutral'
          or (row#>>'{metadata,tie_size}')::integer is distinct from lastpos-pos+1
          or (select count(*) from jsonb_array_elements(plan->'standings') x
            where (x->>'position')::integer=pos and x->>'division_id'=row->>'division_id')<>lastpos-pos+1
          or exists(select 1 from generate_series(pos,lastpos) k where
            ctx#>>array['inputs','config','scoring_json',k::text] is distinct from (row->>'points_awarded')
            or ctx#>>array['inputs','config','coin_rewards_json',k::text] is distinct from (row->>'coins_awarded')) then
          perform public.admin_setup_fail('invalid_results'); end if;
      elsif row#>>'{metadata,tie_status}' is null
        or row#>>'{metadata,tie_status}' not in ('unique','externally_resolved') then
        perform public.admin_setup_fail('invalid_results'); end if;
    end loop;
  elsif rule<>'legacy_pre_10_5d' or op<>'correct' then
    perform public.admin_setup_fail('invalid_results'); end if;
  -- Original commit records creator, timestamp, revision, immutable history,
  -- compensations, event and idempotency receipt atomically. Add the rule/audit
  -- to its frozen inputs; no extra table or independent mutable override.
  perform public.matchday_commit_close_v034(op,r,
    jsonb_set(ctx,'{inputs,ranking}',plan->'ranking'),plan);
end $$;

-- The remainder keeps legacy integrity checks, while recognizing explicitly
-- separate allocation slots for D snapshots with shared sporting positions.
create or replace function public.lifecycle_standings(sid uuid, rows_json jsonb) returns jsonb
language sql stable security invoker set search_path=pg_catalog,public as $$
  select coalesce(jsonb_agg(jsonb_build_object('season_player_id',p.id,'trainer_id',p.trainer_id,
    'position',(r->>'position')::integer,'division',r->>'division_id',
    'division_position',(r->>'division_position')::integer,
    'position_end',coalesce((r#>>'{metadata,position_end}')::integer,(r->>'position')::integer),
    'tie_status',coalesce(r#>>'{metadata,tie_status}','legacy_recorded'),'score',(r->>'score')::numeric,
    'points_awarded',(r->>'points_awarded')::integer,'coins_awarded',(r->>'coins_awarded')::integer)
    order by (r->>'position')::integer),'[]')
  from jsonb_array_elements(rows_json) r join public.season_players p on p.id=(r->>'trainer_id')::uuid and p.season_id=sid
$$;

create or replace function public.lifecycle_final_source(sid uuid) returns public.matchday_snapshot_revisions
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


do $$ declare f regprocedure; begin
  for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and p.proname in ('matchday_context','matchday_context_v034',
      'matchday_commit_close','matchday_commit_close_v034','lifecycle_standings','lifecycle_final_source') loop
    execute format('alter function %s security invoker',f);
    execute format('revoke all on function %s from public,anon,authenticated',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
