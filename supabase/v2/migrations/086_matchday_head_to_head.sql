-- 086: matchday order by direct match (owner rule of 2026-11-17).
--
-- A matchday is ordered by wins. When exactly two trainers are level
-- on wins, the winner of their direct match in that matchday goes ahead. When
-- three or more are level, fewer deaths of the stretch go ahead, and a pair
-- still level on deaths is decided by their direct match. Three or more with
-- equal wins and deaths keep the extra 1v1 battles when the podium, the first
-- or the last place depends on them, and otherwise share the place. NET points
-- never take part in the matchday order.
--
-- Rule id wins_h2h_deaths_v3 for every close and audited correction of a
-- modern League; frozen wins_segment_deaths_v2 snapshots remain readable.
--
-- Every closed matchday of an active modern League is re-ranked once, from its
-- own frozen snapshot (matches, wins, stretch deaths). Results, wins, deaths,
-- points, coins and the next matchday never change. When the order changes, a
-- new audited snapshot revision is written, the Blindar/Robar prizes follow the
-- new first and last (an unused reward is cancelled and re-issued; a reward
-- already in use aborts the whole migration) and the usual matchday_corrected
-- Discord announcement is queued.
begin;

do $$ begin
 if position('matchday_context_v079(op,r)' in pg_get_functiondef('public.matchday_context(text,jsonb)'::regprocedure))=0
  or position('public.matchday_commit_close_v074(op,r,ctx,plan)' in
      pg_get_functiondef('public.matchday_commit_close(text,jsonb,jsonb,jsonb)'::regprocedure))=0
  or position('''wins_segment_deaths_v2''' in
      pg_get_functiondef('public.matchday_commit_close(text,jsonb,jsonb,jsonb)'::regprocedure))=0
  or position('order by (x->>''wins'')::integer desc,(x->>''actual_segment_deaths'')::bigint' in
      pg_get_functiondef('public.league_live_matchday_scores(uuid,uuid)'::regprocedure))=0
  or to_regprocedure('public.matchday_commit_close_v085(text,jsonb,jsonb,jsonb)') is not null
  or to_regprocedure('public.matchday_context_v085(text,jsonb)') is not null then
   raise exception 'unexpected matchday ranking definitions before 086';
 end if;
end $$;

-- Canonical order. players: [{id, wins, deaths}]; matches: [{player_a_id,
-- player_b_id, winner_id}]. Returns one {id, rank, size, tiebreak} per player:
-- rank = 1 + trainers strictly ahead; size > 1 = still level (three or more on
-- wins and deaths, or, in live reads only, a pair whose direct match is not
-- played yet). tiebreak: head_to_head | segment_deaths | null.
create function public.league_h2h_order(players jsonb,matches jsonb) returns jsonb
language plpgsql immutable security invoker set search_path=pg_catalog,public as $$
declare result jsonb='[]'; p jsonb; peers jsonb; ahead integer; size integer; tiebreak text; other text; winner text;
begin
  for p in select value from jsonb_array_elements(coalesce(players,'[]'::jsonb)) loop
    ahead=(select count(*) from jsonb_array_elements(players) x where (x->>'wins')::integer>(p->>'wins')::integer);
    select coalesce(jsonb_agg(x),'[]'::jsonb) into peers from jsonb_array_elements(players) x
      where (x->>'wins')::integer=(p->>'wins')::integer;
    size=1; tiebreak=null;
    if jsonb_array_length(peers)>=3 then
      ahead=ahead+(select count(*) from jsonb_array_elements(peers) x where (x->>'deaths')::bigint<(p->>'deaths')::bigint);
      select coalesce(jsonb_agg(x),'[]'::jsonb) into peers from jsonb_array_elements(peers) x
        where (x->>'deaths')::bigint=(p->>'deaths')::bigint;
      if jsonb_array_length(peers)=1 then tiebreak='segment_deaths';
      elsif jsonb_array_length(peers)>=3 then size=jsonb_array_length(peers); end if;
    end if;
    if jsonb_array_length(peers)=2 then
      select x->>'id' into other from jsonb_array_elements(peers) x where x->>'id'<>p->>'id';
      select m->>'winner_id' into winner from jsonb_array_elements(coalesce(matches,'[]'::jsonb)) m
        where (m->>'player_a_id'=p->>'id' and m->>'player_b_id'=other)
           or (m->>'player_a_id'=other and m->>'player_b_id'=p->>'id')
        order by m->>'winner_id' nulls last limit 1;
      if winner=p->>'id' then tiebreak='head_to_head';
      elsif winner=other then tiebreak='head_to_head'; ahead=ahead+1;
      else size=2; end if;
    end if;
    result=result||jsonb_build_array(jsonb_build_object('id',p->>'id','rank',ahead+1,'size',size,'tiebreak',tiebreak));
  end loop;
  return result;
end $$;
comment on function public.league_h2h_order(jsonb,jsonb) is
  'Matchday order of the owner rule 2026-11-17: wins; two level -> direct match; three or more -> fewer stretch deaths, a pair still level -> direct match.';

-- Every new close and audited correction of a modern League uses the new rule.
alter function public.matchday_context(text,jsonb) rename to matchday_context_v085;
create function public.matchday_context(op text,r jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare ctx jsonb=public.matchday_context_v085(op,r);
begin
  if ctx->>'ranking_rule'='wins_segment_deaths_v2' then
    ctx=ctx||jsonb_build_object('ranking_rule','wins_h2h_deaths_v3'); end if;
  return ctx;
end $$;

-- Same authoritative checks as 075 (wins, losses, deaths, penalties, NET,
-- prizes, extra 1v1 evidence); only the sporting order differs.
alter function public.matchday_commit_close(text,jsonb,jsonb,jsonb) rename to matchday_commit_close_v085;
create function public.matchday_commit_close(op text,r jsonb,ctx jsonb,plan jsonb) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid;
  row jsonb; input_player jsonb; decision jsonb; battle jsonb; group_ids jsonb; canon jsonb; mine jsonb;
  n integer; wins integer; allocation integer; group_size integer; prior_units bigint; place integer; size integer;
  deduction numeric; pair_a text; pair_b text; winner text;
  moving integer; division_size integer; cut integer; tied_division_size integer;
begin
  if ctx->>'ranking_rule' is distinct from 'wins_h2h_deaths_v3' then
    perform public.matchday_commit_close_v085(op,r,ctx,plan); return; end if;
  if ctx#>>'{inputs,config,scoring_mode}' is distinct from 'league_net_v1' or op not in ('close','correct')
    or plan#>>'{ranking,rule}' is distinct from 'wins_h2h_deaths_v3'
    or jsonb_typeof(plan->'standings') is distinct from 'array'
    or jsonb_typeof(plan#>'{ranking,resolutions}') is distinct from 'array'
    or jsonb_typeof(plan#>'{ranking,groups}') is distinct from 'array'
    or coalesce(plan#>>'{ranking,input_hash}','') !~ '^[a-f0-9]{64}$' then
    perform public.admin_setup_fail('invalid_results'); end if;
  if op='correct' then perform public.matchday_results(did,r#>'{body,results}',true); end if;
  perform public.matchday_validate(sid,did,true);
  n=jsonb_array_length(ctx#>'{inputs,players}');
  moving=case when (ctx#>>'{inputs,number}')::integer=(ctx#>>'{inputs,config,total_matchdays}')::integer then 0 else
    least((ctx#>>'{inputs,config,promotion_relegation_count}')::integer,
      (select count(*) from jsonb_array_elements(ctx#>'{inputs,players}') p where p->>'division'='A'),
      (select count(*) from jsonb_array_elements(ctx#>'{inputs,players}') p where p->>'division'='B')) end;
  if jsonb_array_length(plan->'standings')<>n
    or (select count(distinct x->>'trainer_id') from jsonb_array_elements(plan->'standings') x)<>n
    or (select count(distinct (x#>>'{metadata,allocation_position}')::integer)
        from jsonb_array_elements(plan->'standings') x
        where (x#>>'{metadata,allocation_position}')::integer between 1 and n)<>n
    or exists(select 1 from jsonb_array_elements(ctx#>'{inputs,players}') p
      where jsonb_typeof(p->'segment_deaths') is distinct from 'number') then
    perform public.admin_setup_fail('invalid_results'); end if;
  if jsonb_array_length(plan#>'{ranking,resolutions}')>0 then
    if r#>>'{body,tie_resolution,input_hash}' is distinct from plan#>>'{ranking,input_hash}'
      or r#>'{body,tie_resolution,orders}' is distinct from plan#>'{ranking,resolutions}' then
      perform public.admin_setup_fail('invalid_tie_resolution'); end if;
  elsif r#>'{body,tie_resolution}' is not null and r#>'{body,tie_resolution}'<>'null'::jsonb then
    perform public.admin_setup_fail('invalid_tie_resolution'); end if;
  -- The order comes from authoritative facts only: completed matches and the
  -- stretch deaths frozen when the matchday opened.
  canon=public.league_h2h_order(
    (select jsonb_agg(jsonb_build_object('id',p->>'id','deaths',(p->>'segment_deaths')::bigint,
       'wins',(select count(*) from public.matches m where m.matchday_id=did and m.status='completed'
         and m.winner_id=(p->>'id')::uuid))) from jsonb_array_elements(ctx#>'{inputs,players}') p),
    (select coalesce(jsonb_agg(jsonb_build_object('player_a_id',m.player_a_id,'player_b_id',m.player_b_id,
       'winner_id',m.winner_id)),'[]'::jsonb) from public.matches m where m.matchday_id=did and m.status='completed'));
  for row in select value from jsonb_array_elements(plan->'standings') loop
    select value into input_player from jsonb_array_elements(ctx#>'{inputs,players}') where value->>'id'=row->>'trainer_id';
    select x into mine from jsonb_array_elements(canon) x where x->>'id'=row->>'trainer_id';
    select count(*) into wins from public.matches where matchday_id=did and status='completed' and winner_id=(row->>'trainer_id')::uuid;
    allocation=(row#>>'{metadata,allocation_position}')::integer;
    place=(mine->>'rank')::integer; size=(mine->>'size')::integer;
    prior_units=(input_player->>'prior_death_penalty_tenths')::bigint;
    deduction=((input_player->>'death_penalty_tenths')::numeric-prior_units)/10
      +(input_player->>'points_reduction')::numeric-(input_player->>'prior_points_reduction')::numeric;
    if input_player is null or mine is null or input_player->>'death_snapshot_id' is null
      or input_player->>'death_penalty_tenths' is null
      or (input_player->>'death_penalty_tenths')::bigint is distinct from
        (input_player->>'actual_deaths')::bigint+(input_player->>'wipe_deaths')::bigint
      or (input_player->>'actual_deaths')::bigint<(input_player->>'wipe_deaths')::bigint
      or row->>'division_id' is distinct from input_player->>'division'
      or (row->>'division_position')::integer is distinct from 1+(select count(*) from jsonb_array_elements(plan->'standings') x
        where x->>'division_id'=row->>'division_id' and (x#>>'{metadata,allocation_position}')::integer<allocation
          and (row#>>'{metadata,tie_status}' is distinct from 'unresolved_neutral'
            or x#>'{metadata,wins}' is distinct from row#>'{metadata,wins}'
            or x#>'{metadata,actual_segment_deaths}' is distinct from row#>'{metadata,actual_segment_deaths}'))
      or (row->>'points_awarded')::integer is distinct from wins
      or (row#>>'{metadata,wins}')::integer is distinct from wins
      or (row#>>'{metadata,losses}')::integer is distinct from n-1-wins
      or row#>>'{metadata,ranking_rule}' is distinct from 'wins_h2h_deaths_v3'
      or not coalesce(row->'metadata' ? 'tiebreak',false)
      or row#>'{metadata,tiebreak}' is distinct from mine->'tiebreak'
      or (row#>>'{metadata,tie_size}')::integer is distinct from size
      or allocation not between place and place+size-1
      or row#>>'{metadata,death_snapshot_id}' is distinct from input_player->>'death_snapshot_id'
      or (row#>>'{metadata,actual_segment_deaths}')::bigint is distinct from (input_player->>'segment_deaths')::bigint
      or (row#>>'{metadata,actual_deaths}')::bigint is distinct from (input_player->>'actual_deaths')::bigint
      or (row#>>'{metadata,wipe_deaths}')::bigint is distinct from (input_player->>'wipe_deaths')::bigint
      or (row#>>'{penalties,dead_count}')::bigint is distinct from (input_player->>'death_penalty_tenths')::bigint
      or (row#>>'{penalties,dead_points_penalty}')::numeric is distinct from (input_player->>'death_penalty_tenths')::numeric/10
      or (row#>>'{penalties,points_reduction}')::numeric is distinct from (input_player->>'points_reduction')::numeric
      or (row#>>'{metadata,point_penalties}')::numeric is distinct from deduction
      or (row#>>'{metadata,net_points}')::numeric is distinct from wins-deduction
      or row#>'{metadata,placement_rewards}' is distinct from (case
        when (row->>'position')::integer=1 then '["blindar_pokemon"]'::jsonb
        when (row->>'position')::integer=n then '["robar_pokemon"]'::jsonb else '[]'::jsonb end)
      or (row->>'position')::integer<1 or (row#>>'{metadata,position_end}')::integer>n
      or allocation not between (row->>'position')::integer and (row#>>'{metadata,position_end}')::integer then
      perform public.admin_setup_fail('invalid_results'); end if;
    if size=1 then
      if row#>>'{metadata,tie_status}' is distinct from 'unique' or (row->>'position')::integer<>allocation
        or (row#>>'{metadata,position_end}')::integer<>allocation then
        perform public.admin_setup_fail('invalid_results'); end if;
    else
      -- Every direct match is decided at close: only three or more level on
      -- wins and deaths can remain together.
      if size<3 then perform public.admin_setup_fail('invalid_results'); end if;
      select jsonb_agg(x->'id') into group_ids from jsonb_array_elements(canon) x where (x->>'rank')::integer=place;
      group_size=jsonb_array_length(group_ids);
      if group_size<>size then perform public.admin_setup_fail('invalid_results'); end if;
      select x into decision from jsonb_array_elements(plan#>'{ranking,resolutions}') x
        where (select array_agg(v order by v) from jsonb_array_elements_text(x->'player_ids') v)
          =(select array_agg(v order by v) from jsonb_array_elements_text(group_ids) v);
      if decision is null then
        if row#>>'{metadata,tie_status}' is distinct from 'unresolved_neutral'
          or (row->>'position')::integer<>place or (row#>>'{metadata,position_end}')::integer<>place+size-1
          or place<=3 or place+size-1=n then
          perform public.admin_setup_fail('ranking_tie_unresolved'); end if;
        if moving>0 then
          select count(*) into division_size from jsonb_array_elements(ctx#>'{inputs,players}') p where p->>'division'=row->>'division_id';
          select count(*) into tied_division_size from jsonb_array_elements(plan->'standings') x where
            group_ids ? (x->>'trainer_id') and x->>'division_id'=row->>'division_id';
          cut=case when row->>'division_id'='A' then division_size-moving else moving end;
          if (row->>'division_position')::integer<=cut and (row->>'division_position')::integer+tied_division_size-1>cut then
            perform public.admin_setup_fail('ranking_tie_unresolved'); end if;
        end if;
      elsif row#>>'{metadata,tie_status}' is distinct from 'externally_resolved'
        or (row->>'position')::integer<>allocation or (row#>>'{metadata,position_end}')::integer<>allocation then
        perform public.admin_setup_fail('invalid_tie_resolution'); end if;
    end if;
  end loop;
  for decision in select value from jsonb_array_elements(plan#>'{ranking,resolutions}') loop
    group_ids=decision->'player_ids';
    if jsonb_typeof(group_ids) is distinct from 'array' then perform public.admin_setup_fail('invalid_tie_resolution'); end if;
    group_size=jsonb_array_length(group_ids);
    select x into mine from jsonb_array_elements(canon) x where x->>'id'=group_ids->>0;
    if mine is null or group_size<3 or (mine->>'size')::integer<>group_size
      or (select count(*) from jsonb_array_elements(canon) x where x->>'rank'=mine->>'rank' and group_ids ? (x->>'id'))<>group_size then
      perform public.admin_setup_fail('invalid_tie_resolution'); end if;
    if (select count(distinct value) from jsonb_array_elements(group_ids))<>group_size
      or jsonb_typeof(decision->'battles') is distinct from 'array'
      or jsonb_array_length(decision->'battles')<>group_size*(group_size-1)/2
      or jsonb_typeof(decision->'reason') is distinct from 'string'
      or length(btrim(decision->>'reason')) not between 1 and 500
      or (select count(distinct (least(x->>'player_a_id',x->>'player_b_id'),greatest(x->>'player_a_id',x->>'player_b_id')))
        from jsonb_array_elements(decision->'battles') x)<>group_size*(group_size-1)/2 then
      perform public.admin_setup_fail('invalid_tie_resolution'); end if;
    for battle in select value from jsonb_array_elements(decision->'battles') loop
      pair_a=battle->>'player_a_id';pair_b=battle->>'player_b_id';winner=battle->>'winner_id';
      if pair_a is null or pair_b is null or pair_a=pair_b or not(group_ids ? pair_a) or not(group_ids ? pair_b)
        or winner is null or winner not in(pair_a,pair_b)
        or jsonb_typeof(battle->'evidence') is distinct from 'string'
        or length(btrim(battle->>'evidence')) not between 1 and 500
        or jsonb_typeof(battle->'played_at') is distinct from 'string'
        or coalesce(battle->>'played_at','') !~ '(Z|[+-][0-9]{2}:[0-9]{2})$'
        or (battle->>'played_at')::timestamptz>clock_timestamp()
        or (select ord from jsonb_array_elements_text(group_ids) with ordinality a(v,ord) where v=winner)
          >(select ord from jsonb_array_elements_text(group_ids) with ordinality a(v,ord) where v=case when winner=pair_a then pair_b else pair_a end) then
        perform public.admin_setup_fail('invalid_tie_resolution'); end if;
    end loop;
    if exists(select 1 from jsonb_array_elements_text(group_ids) with ordinality g(pid,ord)
      join lateral (select x from jsonb_array_elements(plan->'standings') x where x->>'trainer_id'=g.pid) s on true
      where (s.x#>>'{metadata,allocation_position}')::integer<>ord+(mine->>'rank')::integer-1) then
      perform public.admin_setup_fail('invalid_tie_resolution'); end if;
  end loop;
  perform public.matchday_commit_close_v034(op,r,jsonb_set(ctx,'{inputs,ranking}',plan->'ranking'),plan);
end $$;

-- Provisional order of the open matchday, same rule. A pair whose direct match
-- is not played yet shares the place until it is.
create or replace function public.league_live_matchday_scores(sid uuid,did uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare d public.matchdays; p record; totals jsonb; frozen jsonb; prior jsonb; canon jsonb;
  rows jsonb='[]'; wins integer; losses integer; deduction numeric; reduction numeric; known boolean;
begin
  select * into d from public.matchdays where id=did and season_id=sid;
  if not found or d.status='closed' then return '[]'; end if;
  for p in select sp.*,v.code from public.participant_memberships_at(sid,d.number) m
    join public.season_players sp on sp.id=m.season_player_id join public.divisions v on v.id=m.division_id order by sp.id loop
    totals=public.league_death_totals(p.id); frozen=public.league_death_snapshot(p.id,did);
    known=totals->>'known'='true' and frozen->>'death_snapshot_id' is not null;
    select row into prior from public.matchday_snapshots s join public.matchdays md on md.id=s.matchday_id,
      jsonb_array_elements(s.snapshot->'standings') row where s.season_id=sid and md.number<d.number
      and row->>'trainer_id'=p.id::text order by md.number desc limit 1;
    select count(*) filter(where winner_id=p.id),count(*) filter(where winner_id<>p.id) into wins,losses
      from public.matches where matchday_id=did and status='completed' and p.id in(player_a_id,player_b_id);
    reduction=public.league_points_reduction(sid,p.id,d.number);
    deduction=case when known then ((totals->>'death_penalty_tenths')::numeric
      -coalesce((prior#>>'{penalties,dead_count}')::numeric,0))/10
      +reduction-coalesce((prior#>>'{penalties,points_reduction}')::numeric,0) end;
    rows=rows||jsonb_build_array(jsonb_build_object('season_player_id',p.id,'division',p.code,
      'position',null,'division_position',null,'position_end',null,'tie_status',null,
      'points_awarded',wins,'score',case when known then (wins-deduction)::text end,
      'wins',wins,'losses',losses,'actual_segment_deaths',frozen->'segment_deaths',
      'point_penalties',deduction::text,'net_points',case when known then (wins-deduction)::text end,
      'placement_rewards','[]'::jsonb,'tiebreak',null));
  end loop;
  if jsonb_array_length(rows)>0
    and not exists(select 1 from jsonb_array_elements(rows) x where x->>'actual_segment_deaths' is null) then
    canon=public.league_h2h_order(
      (select jsonb_agg(jsonb_build_object('id',x->>'season_player_id','wins',(x->>'wins')::integer,
         'deaths',(x->>'actual_segment_deaths')::bigint)) from jsonb_array_elements(rows) x),
      (select coalesce(jsonb_agg(jsonb_build_object('player_a_id',m.player_a_id,'player_b_id',m.player_b_id,
         'winner_id',m.winner_id)),'[]'::jsonb) from public.matches m where m.matchday_id=did and m.status='completed'));
    select jsonb_agg(x||jsonb_build_object('position',(c->>'rank')::integer,
      'division_position',1+(select count(*) from jsonb_array_elements(rows) y
        join jsonb_array_elements(canon) cy on cy->>'id'=y->>'season_player_id'
        where y->>'division'=x->>'division' and (cy->>'rank')::integer<(c->>'rank')::integer),
      'tiebreak',c->'tiebreak') order by (c->>'rank')::integer,x->>'season_player_id') into rows
      from jsonb_array_elements(rows) x join jsonb_array_elements(canon) c on c->>'id'=x->>'season_player_id';
  end if;
  return jsonb_build_array(jsonb_build_object('matchday_id',did,'standings',coalesce(rows,'[]'::jsonb),'provisional',true));
end $$;

-- One-off: re-rank a closed matchday of an active modern League from its own
-- frozen snapshot. Returns false (and writes nothing) when the order is the same.
create function public.league_h2h_rerank_closed(did uuid,actor uuid,p_reason text) returns boolean
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare d public.matchdays; snap public.matchday_snapshots; s jsonb; players jsonb; matches jsonb; canon jsonb;
  ordered jsonb; item jsonb; row jsonb; old_decision jsonb; n integer; i integer=0; place integer; size integer;
  pos integer; pos_end integer; tie_state text; rewards jsonb; standings jsonb='[]'; audit_groups jsonb='[]';
  resolutions jsonb='[]'; members jsonb; prizes jsonb; prize jsonb; oldgift public.purchases; gift uuid; tid uuid;
  rev integer; stamp timestamptz=clock_timestamp(); changed boolean=false; pid uuid;
begin
  select * into d from public.matchdays where id=did for update;
  if d.id is null or d.status<>'closed' then return false; end if;
  select * into snap from public.matchday_snapshots where matchday_id=did for update;
  if snap.id is null then return false; end if;
  s=snap.snapshot;
  if s#>>'{inputs,config,scoring_mode}' is distinct from 'league_net_v1'
    or s#>>'{inputs,ranking,rule}' is distinct from 'wins_segment_deaths_v2' then return false; end if;
  n=jsonb_array_length(s->'standings');
  matches=s#>'{inputs,matches}';
  select jsonb_agg(jsonb_build_object('id',x->>'trainer_id','wins',(x#>>'{metadata,wins}')::integer,
    'deaths',(x#>>'{metadata,actual_segment_deaths}')::bigint)) into players from jsonb_array_elements(s->'standings') x;
  if n<2 or jsonb_typeof(matches) is distinct from 'array' or jsonb_array_length(matches)<>n*(n-1)/2
    or exists(select 1 from jsonb_array_elements(s->'standings') x where x->>'division_id' is distinct from 'A')
    or exists(select 1 from jsonb_array_elements(players) p where p->>'deaths' is null or p->>'wins' is null
      or (p->>'wins')::integer<>(select count(*) from jsonb_array_elements(matches) m where m->>'winner_id'=p->>'id'))
    or exists(select 1 from jsonb_array_elements(matches) m where m->>'winner_id' is null
      or m->>'winner_id' not in (m->>'player_a_id',m->>'player_b_id')) then
    raise exception '086: matchday % (%) cannot be re-ranked from its frozen snapshot',d.number,did; end if;
  canon=public.league_h2h_order(players,matches);
  -- Inside three or more level on wins and deaths: the recorded 1v1 decision
  -- order, else the frozen allocation order (a shared place).
  select jsonb_agg(c||jsonb_build_object('row',x,'decided',g.ord is not null)
      order by (c->>'rank')::integer,coalesce(g.ord,(x#>>'{metadata,allocation_position}')::bigint)) into ordered
    from jsonb_array_elements(canon) c
    join jsonb_array_elements(s->'standings') x on x->>'trainer_id'=c->>'id'
    left join lateral (select v.ord from jsonb_array_elements(coalesce(s#>'{inputs,ranking,resolutions}','[]'::jsonb)) r2,
        jsonb_array_elements_text(r2->'player_ids') with ordinality v(member_id,ord)
      where v.member_id=c->>'id' and (c->>'size')::integer>=3
        and (select array_agg(t order by t) from jsonb_array_elements_text(r2->'player_ids') t)
          =(select array_agg(c3->>'id' order by c3->>'id') from jsonb_array_elements(canon) c3 where c3->>'rank'=c->>'rank')
      limit 1) g on true;
  for item in select value from jsonb_array_elements(ordered) loop
    i=i+1; row=item->'row'; place=(item->>'rank')::integer; size=(item->>'size')::integer;
    if size=2 then raise exception '086: matchday % has an undecided direct match',d.number; end if;
    if size=1 then tie_state='unique'; pos=i; pos_end=i;
    elsif (item->>'decided')::boolean then tie_state='externally_resolved'; pos=i; pos_end=i;
    elsif place<=3 or place+size-1=n then
      raise exception '086: matchday % needs an extra 1v1 decision for places %-%',d.number,place,place+size-1;
    else tie_state='unresolved_neutral'; pos=place; pos_end=place+size-1; end if;
    rewards=case when pos=1 then '["blindar_pokemon"]'::jsonb when pos=n then '["robar_pokemon"]'::jsonb else '[]'::jsonb end;
    if (row->>'position')::integer is distinct from pos or (row->>'division_position')::integer is distinct from pos
      or (row#>>'{metadata,allocation_position}')::integer is distinct from i
      or (row#>>'{metadata,position_end}')::integer is distinct from pos_end
      or row#>>'{metadata,tie_status}' is distinct from tie_state
      or (row#>>'{metadata,tie_size}')::integer is distinct from size
      or row#>'{metadata,placement_rewards}' is distinct from rewards then changed=true; end if;
    standings=standings||jsonb_build_array(row||jsonb_build_object('position',pos,'division_position',pos,
      'metadata',(row->'metadata')||jsonb_build_object('allocation_position',i,'position_end',pos_end,
        'tie_status',tie_state,'tie_size',size,'ranking_rule','wins_h2h_deaths_v3','tiebreak',item->'tiebreak',
        'placement_rewards',rewards)));
    if size>=3 and i=place then
      select jsonb_agg(o->'id' order by o_ord) into members from jsonb_array_elements(ordered) with ordinality q(o,o_ord)
        where (o->>'rank')::integer=place;
      audit_groups=audit_groups||jsonb_build_array(jsonb_build_object('division','A','player_ids',members,'position',place,
        'position_end',place+size-1,'wins',(row#>>'{metadata,wins}')::integer,
        'adjusted_deaths',(row#>>'{metadata,actual_segment_deaths}')::bigint,
        'segment_deaths',(row#>>'{metadata,actual_segment_deaths}')::bigint,'status',tie_state));
      select x into old_decision from jsonb_array_elements(coalesce(s#>'{inputs,ranking,resolutions}','[]'::jsonb)) x
        where (select array_agg(t order by t) from jsonb_array_elements_text(x->'player_ids') t)
          =(select array_agg(t order by t) from jsonb_array_elements_text(members) t);
      if old_decision is not null then resolutions=resolutions||jsonb_build_array(old_decision); end if;
    end if;
  end loop;
  if not changed then return false; end if;
  rev=snap.revision+1;
  prizes=jsonb_build_array(
    jsonb_build_object('code','blindar_pokemon','season_player_id',
      (select x->>'trainer_id' from jsonb_array_elements(standings) x where (x->>'position')::integer=1)),
    jsonb_build_object('code','robar_pokemon','season_player_id',
      (select x->>'trainer_id' from jsonb_array_elements(standings) x where (x->>'position')::integer=n)));
  s=jsonb_set(s,'{inputs,ranking}',jsonb_build_object('rule','wins_h2h_deaths_v3',
      'input_hash',encode(sha256(convert_to(jsonb_build_object('rule','wins_h2h_deaths_v3','matchday_id',did,
        'players',players,'matches',matches)::text,'UTF8')),'hex'),
      'groups',audit_groups,'resolutions',resolutions,'recomputed_from_revision',snap.revision))
    ||jsonb_build_object('revision',rev,'closed_at',stamp,'standings',standings,'single_league_rewards',prizes,
      'reason',p_reason,'correction',jsonb_build_object('kind','h2h_tiebreak_rule','previous_revision',snap.revision));
  insert into public.matchday_snapshot_revisions(season_id,matchday_id,revision,snapshot,reason,created_by_trainer_id)
    values(d.season_id,did,rev,s,p_reason,actor);
  update public.matchday_snapshots set revision=rev,snapshot=s,closed_at=stamp,created_by_trainer_id=actor,updated_at=stamp
    where id=snap.id;
  -- Prizes follow the new first and last, as in an audited correction. A
  -- reward that is used, redeemed or tied to any operation never moves.
  for oldgift in select * from public.purchases where origin_matchday_id=did and status<>'cancelled' order by id for update loop
    if not exists(select 1 from jsonb_array_elements(prizes) q join public.shop_items it on it.code=q->>'code'
        where it.id=oldgift.shop_item_id and q->>'season_player_id'=oldgift.season_player_id::text) then
      if oldgift.status<>'pending'
        or exists(select 1 from public.redemptions x where x.purchase_id=oldgift.id or x.gift_purchase_id=oldgift.id)
        or exists(select 1 from public.item_use_authorizations x where x.purchase_id=oldgift.id)
        or exists(select 1 from public.item_deliveries x where x.purchase_id=oldgift.id)
        or exists(select 1 from public.training_operations x where x.purchase_id=oldgift.id)
        or exists(select 1 from public.admin_incident_commands x where x.purchase_id=oldgift.id) then
        raise exception '086: a matchday % reward (%) is already in use and cannot move',d.number,oldgift.id; end if;
      update public.purchases set status='cancelled',metadata=metadata||
        jsonb_build_object('cancelled_by_revision',rev,'reason',p_reason) where id=oldgift.id;
    end if;
  end loop;
  for prize in select value from jsonb_array_elements(prizes) loop
    pid=(prize->>'season_player_id')::uuid;
    select id into gift from public.shop_items where code=prize->>'code' and acquisition_mode='purchasable' for share;
    if gift is null or pid is null then raise exception '086: matchday % prize % unavailable',d.number,prize->>'code'; end if;
    -- A prize that keeps its recipient is never issued twice, used or not.
    if not exists(select 1 from public.purchases where origin_matchday_id=did and season_player_id=pid
        and shop_item_id=gift and status<>'cancelled') then
      select trainer_id into tid from public.season_players where id=pid;
      insert into public.purchases(season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,status,
        acquisition_type,origin_matchday_id,origin_snapshot_revision)
        values(d.season_id,tid,pid,gift,1,0,'pending','reward',did,rev);
    end if;
  end loop;
  update public.matchdays set revision=revision+1 where id=did returning * into d;
  -- Same fact as an audited correction: it queues the matchday_corrected announcement.
  insert into public.activity_events(season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
    values(d.season_id,'MATCHDAY_ADMIN_CORRECT',actor,'admin','matchday-h2h-086:'||did::text||':'||rev,
      jsonb_build_object('season_id',d.season_id,'matchday_id',did,'state',d.status,'revision',d.revision,
        'results_revision',d.results_revision,'snapshot_revision',rev,
        'current_matchday_id',(select current_matchday_id from public.seasons where id=d.season_id),
        'reason',p_reason,'source','086_h2h_tiebreak'));
  return true;
end $$;

do $$ declare day record; actor uuid; total integer=0;
begin
  select id into actor from public.trainers where is_admin order by created_at,id limit 1;
  for day in select d.id from public.matchdays d join public.seasons s on s.id=d.season_id
    where s.status='active' and d.status='closed' order by s.id,d.number loop
    if public.league_h2h_rerank_closed(day.id,actor,
        'Desempate por enfrentamiento directo (norma del 17-11-2026): mismos resultados, nueva clasificación y comodines.') then
      total=total+1; end if;
  end loop;
  raise notice '086: % closed matchdays re-ranked',total;
end $$;
drop function public.league_h2h_rerank_closed(uuid,uuid,text);

do $$ declare f regprocedure; begin
  foreach f in array array[
    'public.league_h2h_order(jsonb,jsonb)'::regprocedure,
    'public.matchday_context(text,jsonb)'::regprocedure,'public.matchday_context_v085(text,jsonb)'::regprocedure,
    'public.matchday_commit_close(text,jsonb,jsonb,jsonb)'::regprocedure,
    'public.matchday_commit_close_v085(text,jsonb,jsonb,jsonb)'::regprocedure,
    'public.league_live_matchday_scores(uuid,uuid)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;

notify pgrst,'reload schema';
commit;
