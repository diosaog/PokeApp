-- 073: prospective single-day League scoring and lighter adjusted-death deductions.
-- Closed snapshots, purchases, balances and results are never rewritten here.
-- Every new closing freezes its scoring mode/rate; corrections use those inputs.
begin;

create function public.single_round_robin_config(c public.season_config_versions) returns boolean
language sql immutable security invoker set search_path=pg_catalog,public as $$
  select c.total_matchdays=1 and c.division_sizes ? 'A' and not (c.division_sizes ? 'B')
$$;

-- Reuse the existing configured reward map. No amount is chosen by this migration.
create function public.single_league_common_coins(rewards jsonb) returns integer
language plpgsql immutable security invoker set search_path=pg_catalog,public as $$
declare amount integer;
begin
  if jsonb_typeof(rewards) is distinct from 'object' or rewards='{}'::jsonb
    or (select count(distinct value::integer) from jsonb_each_text(rewards))<>1 then
    raise sqlstate 'PT409' using message='single_league_common_coins_required';
  end if;
  select value::integer into amount from jsonb_each_text(rewards) limit 1;
  return amount;
end $$;

alter function public.admin_setup_validate_config(uuid,jsonb) rename to admin_setup_validate_config_v072;
create function public.admin_setup_validate_config(sid uuid,b jsonb) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  perform public.admin_setup_validate_config_v072(sid,b);
  if (b->>'total_matchdays')::integer=1 and not (b->'division_sizes' ? 'B') then
    perform public.single_league_common_coins(b->'coin_rewards');
  end if;
end $$;


create or replace function public.matchday_context(op text,r jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare ctx jsonb; rule text; c public.season_config_versions; config jsonb;
begin
  ctx=public.matchday_context_v034(op,r);
  if op='correct' then
    select coalesce(snapshot#>>'{inputs,ranking,rule}','legacy_pre_10_5d') into rule
      from public.matchday_snapshots where matchday_id=(r->>'resource_id')::uuid;
  else
    rule='wins_adjusted_deaths_v1';
    select c0.* into c from public.matchdays d join public.season_config_versions c0
      on c0.id=d.season_config_version_id where d.id=(r->>'resource_id')::uuid;
    config=ctx#>'{inputs,config}';
    config=config||jsonb_build_object('death_penalty_per_mon','0.1',
      'scoring_mode',case when public.single_round_robin_config(c)
        then 'single_round_robin_v1' else 'position_v1' end);
    if public.single_round_robin_config(c) then
      perform public.single_league_common_coins(config->'coin_rewards_json');
    end if;
    ctx=jsonb_set(ctx,'{inputs,config}',config);
  end if;
  if rule is null or rule not in ('legacy_pre_10_5d','wins_adjusted_deaths_v1') then
    perform public.admin_setup_fail('historical_source_invalid'); end if;
  return ctx||jsonb_build_object('ranking_rule',rule);
end $$;

create or replace function public.matchday_commit_close_v034(op text,r jsonb,ctx jsonb,plan jsonb) returns void
language plpgsql set search_path=pg_catalog,public as $$
declare sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid; actor uuid=(r->>'actor_trainer_id')::uuid;
  d public.matchdays; cfg public.season_config_versions; nxtcfg public.season_config_versions;
  old public.matchday_snapshots; v_snapshot jsonb; rev integer; final boolean; nextid uuid; divisionid uuid;
  pid uuid; tid uuid; gift uuid; giftplayer uuid; oldgift public.purchases; row jsonb; divcode text;
  v_amount integer; prior integer; stamp timestamptz=clock_timestamp();
  rr boolean=ctx#>>'{inputs,config,scoring_mode}'='single_round_robin_v1';
  common_coins integer; prize jsonb; prizes jsonb; expected_points integer;
begin
  select * into d from public.matchdays where id=did;
  select * into cfg from public.season_config_versions where id=d.season_config_version_id;
  select * into old from public.matchday_snapshots where matchday_id=did;
  rev=coalesce(old.revision,0)+1; final=d.number=cfg.total_matchdays;
  if op='correct' then
    perform public.matchday_results(did,r->'body'->'results',true);
    perform public.matchday_validate(sid,did,true);
  end if;
  if jsonb_typeof(plan->'standings') is distinct from 'array' or jsonb_array_length(plan->'standings')<>
    (select count(*) from public.participant_memberships_at(sid,d.number))
    or (select count(distinct value->>'trainer_id') from jsonb_array_elements(plan->'standings'))<>jsonb_array_length(plan->'standings') then
    perform public.admin_setup_fail('invalid_results'); end if;
  if rr then
    if cfg.total_matchdays<>1 or not public.single_round_robin_config(cfg) then
      perform public.admin_setup_fail('config_mismatch'); end if;
    common_coins=public.single_league_common_coins(ctx#>'{inputs,config,coin_rewards_json}');
    if jsonb_typeof(plan->'single_league_rewards') is distinct from 'array'
      or jsonb_array_length(plan->'single_league_rewards')<>2 then
      perform public.admin_setup_fail('invalid_results'); end if;
    prizes=jsonb_build_array(
      jsonb_build_object('code','blindar_pokemon','season_player_id',
        (select x->>'trainer_id' from jsonb_array_elements(plan->'standings') x where (x->>'position')::integer=1)),
      jsonb_build_object('code','robar_pokemon','season_player_id',
        (select x->>'trainer_id' from jsonb_array_elements(plan->'standings') x where
          (x->>'position')::integer=jsonb_array_length(plan->'standings'))));
    if plan->'single_league_rewards' is distinct from prizes then
      perform public.admin_setup_fail('invalid_results'); end if;
    for prize in select value from jsonb_array_elements(prizes) loop
      if prize->>'season_player_id' is null or not exists(select 1 from public.shop_items
        where code=prize->>'code' and acquisition_mode='purchasable') then
        perform public.admin_setup_fail('reward_item_unavailable'); end if;
    end loop;
  elsif plan ? 'single_league_rewards' then perform public.admin_setup_fail('invalid_results'); end if;
  for row in select value from jsonb_array_elements(plan->'standings') loop
    if rr then
      select 2*count(*) into expected_points from public.matches m where m.matchday_id=did
        and m.status='completed' and m.winner_id=(row->>'trainer_id')::uuid;
    else expected_points=(cfg.scoring_json->>(row->>'position'))::integer; end if;
    if not exists(select 1 from public.season_players where id=(row->>'trainer_id')::uuid and season_id=sid
      and (status='active' or d.number<status_effective_matchday_number))
      or (row->>'coins_awarded')::integer is distinct from (case when rr then common_coins else (cfg.coin_rewards_json->>(row->>'position'))::integer end)
      or (row->>'points_awarded')::integer is distinct from expected_points then
      perform public.admin_setup_fail('invalid_results'); end if;
  end loop;
  giftplayer=(plan->>'last_b_player_id')::uuid;
  if (cfg.rules_json->>'last_b_gets_steal')::boolean and exists (
    select 1 from public.participant_memberships_at(sid,d.number) m join public.divisions v on v.id=m.division_id where v.code='B'
  ) then
    select id into gift from public.shop_items where code='robar_pokemon' and acquisition_mode='purchasable' for share;
    if gift is null or giftplayer is null then perform public.admin_setup_fail('reward_item_unavailable'); end if;
  elsif giftplayer is not null then perform public.admin_setup_fail('invalid_results'); end if;
  v_snapshot=jsonb_build_object('schema_version',2,'revision',rev,'closed_at',stamp,'inputs',
    jsonb_set(ctx->'inputs','{matches}',plan->'matches'),'standings',plan->'standings',
    'new_divisions',plan->'new_divisions','last_b_player_id',giftplayer,'external_facts',ctx->'external_facts',
    'single_league_rewards',coalesce(prizes,'[]'::jsonb),'final',final,'reason',case when op='correct' then r->'body'->>'reason' else 'close' end);
  insert into public.matchday_snapshot_revisions(season_id,matchday_id,revision,snapshot,reason,created_by_trainer_id)
    values(sid,did,rev,v_snapshot,v_snapshot->>'reason',actor);
  if old.id is null then
    insert into public.matchday_snapshots(season_id,matchday_id,config_version_id,revision,snapshot_schema_version,closed_at,snapshot,created_by_trainer_id)
      values(sid,did,cfg.id,rev,2,stamp,v_snapshot,actor);
  else
    update public.matchday_snapshots set revision=rev,snapshot=v_snapshot,closed_at=stamp,created_by_trainer_id=actor where id=old.id;
  end if;
  for row in select value from jsonb_array_elements(plan->'standings') loop
    pid=(row->>'trainer_id')::uuid;
    select trainer_id into tid from public.season_players where id=pid;
    prior=0;
    if old.id is not null then select (x->>'coins_awarded')::integer into prior from jsonb_array_elements(old.snapshot->'standings') x where x->>'trainer_id'=pid::text; end if;
    v_amount=(row->>'coins_awarded')::integer-coalesce(prior,0);
    if v_amount<0 and (select coalesce(sum(amount),0) from public.coin_transactions where season_player_id=pid)+v_amount<0 then
      perform public.admin_setup_fail('correction_window_closed'); end if;
    if v_amount<>0 then
      insert into public.coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type,reference_type,reference_id,
        reward_matchday_id,reward_revision,created_by_trainer_id,metadata)
        values(sid,tid,pid,v_amount,case when op='close' then 'matchday_reward' else 'compensation' end,
          'matchday_snapshot_revision',(select id from public.matchday_snapshot_revisions where matchday_id=did and revision=rev),
          did,rev,actor,jsonb_build_object('reason',v_snapshot->>'reason','previous_revision',rev-1));
    end if;
  end loop;
  if rr then
    -- Existing rewards remain valid when a correction leaves their recipient in place.
    -- The outer correction lock already refuses a spent reward or a redemption.
    for oldgift in select * from public.purchases where origin_matchday_id=did
      and status='pending' order by id for update loop
      if not exists(select 1 from jsonb_array_elements(prizes) q join public.shop_items i
        on i.code=q->>'code' where i.id=oldgift.shop_item_id
        and q->>'season_player_id'=oldgift.season_player_id::text) then
        update public.purchases set status='cancelled',metadata=metadata||
          jsonb_build_object('cancelled_by_revision',rev,'reason',v_snapshot->>'reason') where id=oldgift.id;
      end if;
    end loop;
    for prize in select value from jsonb_array_elements(prizes) loop
      pid=(prize->>'season_player_id')::uuid;
      select id into gift from public.shop_items where code=prize->>'code' and acquisition_mode='purchasable' for share;
      if not exists(select 1 from public.purchases where origin_matchday_id=did and
        season_player_id=pid and shop_item_id=gift and status='pending') then
        select trainer_id into tid from public.season_players where id=pid;
        insert into public.purchases(season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,status,
          acquisition_type,origin_matchday_id,origin_snapshot_revision)
          values(sid,tid,pid,gift,1,0,'pending','reward',did,rev);
      end if;
    end loop;
  else
  select * into oldgift from public.purchases where origin_matchday_id=did and status='pending' order by origin_snapshot_revision desc limit 1 for update;
  if oldgift.id is not null and oldgift.season_player_id is distinct from giftplayer then
    update public.purchases set status='cancelled',metadata=metadata||jsonb_build_object('cancelled_by_revision',rev,'reason',v_snapshot->>'reason') where id=oldgift.id;
  end if;
  if giftplayer is not null and (oldgift.id is null or oldgift.season_player_id<>giftplayer) then
    select trainer_id into tid from public.season_players where id=giftplayer;
    insert into public.purchases(season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,status,
      acquisition_type,origin_matchday_id,origin_snapshot_revision)
      values(sid,tid,giftplayer,gift,1,0,'pending','reward',did,rev);
  end if;
  end if;
  if not final then
    select * into nxtcfg from public.season_config_versions where season_id=sid and effective_from_matchday<=d.number+1
      order by effective_from_matchday desc limit 1;
    if nxtcfg.total_matchdays<d.number+1 or nxtcfg.division_sizes<>cfg.division_sizes then
      perform public.admin_setup_fail('config_mismatch'); end if;
    select id into nextid from public.matchdays where season_id=sid and number=d.number+1;
    if op='close' and nextid is not null then perform public.admin_setup_fail('dependent_data_exists'); end if;
    if op='correct' then
      delete from public.matchday_movements where matchday_id=did;
      delete from public.matches where matchday_id=nextid;
      delete from public.division_memberships where source_matchday_id=did;
    end if;
    update public.division_memberships set effective_to_matchday_number=d.number where season_id=sid
      and effective_from_matchday_number<=d.number and coalesce(effective_to_matchday_number,d.number)>=d.number
      and (eligibility_ends_before_matchday_number is null or d.number<eligibility_ends_before_matchday_number);
    foreach divcode in array array['A','B'] loop
      select id into divisionid from public.divisions where season_id=sid and code=divcode;
      for pid in select value::uuid from jsonb_array_elements_text(plan->'new_divisions'->divcode) loop
        insert into public.matchday_movements(season_id,matchday_id,season_player_id,from_division_id,to_division_id,movement_type,metadata)
          select sid,did,pid,m.division_id,divisionid,case when m.division_id=divisionid then 'stay' when divcode='A' then 'promotion' else 'relegation' end,
            jsonb_build_object('snapshot_revision',rev) from public.division_memberships m where m.season_player_id=pid
            and m.effective_from_matchday_number<=d.number and m.effective_to_matchday_number=d.number;
        insert into public.division_memberships(season_id,season_player_id,division_id,effective_from_matchday_number,source_matchday_id,reason)
          select sid,pid,divisionid,d.number+1,did,case when movement_type='stay' then 'initial' else movement_type end
            from public.matchday_movements where matchday_id=did and season_player_id=pid;
      end loop;
    end loop;
    if nextid is null then
      insert into public.matchdays(season_id,number,season_config_version_id) values(sid,d.number+1,nxtcfg.id) returning id into nextid;
    end if;
    insert into public.matches(season_id,matchday_id,division_id,player_a_id,player_b_id)
      select sid,nextid,a.division_id,a.season_player_id,b.season_player_id from public.division_memberships a
      join public.division_memberships b on a.division_id=b.division_id and a.season_player_id<b.season_player_id
      where a.season_id=sid and a.effective_from_matchday_number=d.number+1 and b.effective_from_matchday_number=d.number+1;
    perform public.matchday_validate(sid,nextid,false);
    if op='close' then
      for row in select value from jsonb_array_elements(plan->'promotions') loop
        insert into public.shop_promotions(season_id,matchday_id,shop_item_id,promotion_type,status,base_price,effective_price,stock_total,
          announced_at,activates_at,dedupe_key,metadata)
          values(sid,nextid,(row->>'shop_item_id')::uuid,row->>'promotion_type','pending',(row->>'base_price')::integer,
            (row->>'effective_price')::integer,(row->>'stock_total')::integer,stamp,stamp+interval '24 hours',
            'matchday:'||did::text||':'||(row->>'shop_item_id'),jsonb_build_object('source_matchday_id',did));
      end loop;
    end if;
    update public.seasons set current_matchday_id=nextid where id=sid;
  end if;
  if op='close' then
    update public.shop_promotions set status='ended',ends_at=stamp where season_id=sid and status in ('pending','active','exhausted')
      and matchday_id in (select id from public.matchdays where season_id=sid and number<=d.number);
  end if;
  update public.matchdays set status='closed',closed_at=coalesce(closed_at,stamp),revision=revision+1,results_revision=results_revision+1 where id=did;
end $$;

create or replace function public.matchday_commit_close(op text,r jsonb,ctx jsonb,plan jsonb) returns void
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare row jsonb; n integer; pos integer; lastpos integer; allocation integer;
  rule text=ctx->>'ranking_rule';
  rr boolean=ctx#>>'{inputs,config,scoring_mode}'='single_round_robin_v1';
  input_player jsonb; rate numeric=coalesce((ctx#>>'{inputs,config,death_penalty_per_mon}')::numeric,0.2);
begin
  if rate not in (0.1,0.2) then perform public.admin_setup_fail('invalid_results'); end if;
  for row in select value from jsonb_array_elements(plan->'standings') loop
    select value into input_player from jsonb_array_elements(ctx#>'{inputs,players}')
      where value->>'id'=row->>'trainer_id';
    if input_player is null or (row#>>'{penalties,dead_count}')::bigint is distinct from
        (input_player->>'dead_count')::bigint
      or (row#>>'{penalties,dead_points_penalty}')::numeric is distinct from
        round(rate*(input_player->>'dead_count')::numeric,1) then
      perform public.admin_setup_fail('invalid_results'); end if;
  end loop;
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
            (not coalesce(rr,false) and ctx#>>array['inputs','config','scoring_json',k::text] is distinct from (row->>'points_awarded'))
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

create or replace function public.check_purchase_acquisition() returns trigger
language plpgsql security invoker set search_path='' as $$
declare v_item public.shop_items; v_origin public.redemptions;
begin
  select * into v_item from public.shop_items where id=new.shop_item_id for share;
  if new.acquisition_type='paid' and v_item.acquisition_mode<>'purchasable' then
    raise sqlstate 'PT409' using message='item_unavailable'; end if;
  if new.acquisition_type='reward' and new.origin_matchday_id is not null then
    if v_item.acquisition_mode<>'purchasable' or not exists (
      select 1 from public.matchday_snapshot_revisions r join public.season_players p
        on p.id=new.season_player_id and p.season_id=r.season_id
      where r.matchday_id=new.origin_matchday_id and r.revision=new.origin_snapshot_revision
        and r.season_id=new.season_id and p.trainer_id=new.trainer_id and (
          (v_item.code='robar_pokemon' and r.snapshot->>'last_b_player_id'=p.id::text)
          or (r.snapshot#>>'{inputs,config,scoring_mode}'='single_round_robin_v1'
            and v_item.code in ('blindar_pokemon','robar_pokemon') and exists(
              select 1 from jsonb_array_elements(r.snapshot->'single_league_rewards') prize
              where prize->>'season_player_id'=p.id::text and prize->>'code'=v_item.code)))
    ) then raise sqlstate 'PT409' using message='invalid_reward_origin'; end if;
  elsif new.acquisition_type='reward' then
    select * into v_origin from public.redemptions where id=new.origin_redemption_id;
    if not found or v_item.code<>'robbery_shield_voucher' or v_item.acquisition_mode<>'reward_only'
      or v_origin.effect_code is distinct from 'steal' or v_origin.status<>'applied'
      or v_origin.season_id<>new.season_id or v_origin.trainer_id<>new.trainer_id
      or v_origin.season_player_id<>new.season_player_id or v_origin.gift_purchase_id is distinct from new.id then
      raise sqlstate 'PT409' using message='invalid_reward_origin'; end if;
  end if;
  return new;
end $$;

create or replace function public.league_general_read(p_season_id uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare result jsonb; next_number integer; next_id uuid; live boolean; rows jsonb; rr boolean; c public.season_config_versions;
begin
  result=public.league_general_read_v068(p_season_id);
  if result is null then return result; end if;
  live=result#>>'{season,status}'='active';
  select cfg.* into c from public.season_config_versions cfg where cfg.season_id=p_season_id
    order by cfg.effective_from_matchday desc limit 1;
  rr=public.single_round_robin_config(c);
  select id,number into next_id,next_number from public.matchdays
    where season_id=p_season_id and status<>'closed' order by number limit 1;
  if next_number is null then
    -- A final closed day's official figure stays frozen even before Finish.
    if exists(select 1 from public.matchdays where season_id=p_season_id
      and number=c.total_matchdays and status='closed') then live=false; end if;
    select coalesce(max(number),0)+1 into next_number from public.matchdays where season_id=p_season_id;
  end if;
  select jsonb_agg(z.item order by z.total desc,lower(z.item->>'display_name') collate "C",
      (z.item->>'trainer_id')::uuid) into rows
  from (
    select (x.r-array['provisional_matchday_number','provisional_dead_count',
          'provisional_points_reduction','provisional_points'])||jsonb_build_object(
        'official_points',x.r->>'total_points',
        'total_points',coalesce(f.current,(x.r->>'total_points')::numeric)::text,
        'dead_box_number',p.dead_box_number,
        'dead_count',seen.dead,
        'dead_count_source',case when seen.dead is null then 'unknown' else 'observed_current_save' end,
        'dead_count_observed_at',case when seen.dead is not null then seen.parsed_at end) as item,
      coalesce(f.current,(x.r->>'total_points')::numeric) as total
    from jsonb_array_elements(result->'rows') x(r)
    join public.season_players p on p.id=(x.r->>'season_player_id')::uuid and p.season_id=p_season_id
    left join public.season_player_stats st on st.season_player_id=p.id
    -- The occupants of the participant's dead box in the accepted current save
    -- (same evidence chain as 033); a missing or partial box is unknown, never 0.
    left join lateral (
      select public.league_observed_dead_count(parsed.payload,p.dead_box_number) as dead,parsed.parsed_at
      from public.save_files saved
      join public.pokemon_identity_revisions identity on identity.save_file_id=saved.id
        and identity.season_id=p.season_id and identity.trainer_id=p.trainer_id
      join public.parsed_saves parsed on parsed.id=identity.parsed_save_id
        and parsed.save_file_id=saved.id and parsed.parser_version=saved.parser_version
        and parsed.status='parsed' and parsed.schema_version=1
        and (not (parsed.payload ? 'save_record_id') or parsed.payload->>'save_record_id'=saved.id::text)
        and (not (parsed.payload ? 'trainer_id') or parsed.payload->>'trainer_id'=p.trainer_id::text)
        and (not (parsed.payload ? 'source_hash') or parsed.payload->>'source_hash'=saved.sha256)
      where saved.id=p.current_save_file_id and saved.season_id=p.season_id
        and saved.trainer_id=p.trainer_id and saved.deleted_at is null and saved.parser_status='parsed'
      order by parsed.parsed_at desc limit 1) seen on true
    cross join lateral (select
      coalesce((select sp.earned_points from public.public_sanctioned_points sp
        where sp.season_id=p_season_id and sp.season_player_id=p.id),0)
        +case when rr then 2*(select count(*) from public.matches m join public.matchdays d on d.id=m.matchday_id
          where d.season_id=p_season_id and d.status='open' and m.status='completed' and m.winner_id=p.id) else 0 end as earned,
      -- A save the closing could not read yet (no identity) is unknown.
      case when p.current_save_file_id is null or exists(select 1 from public.pokemon_identity_revisions i
          where i.save_file_id=p.current_save_file_id) then
        (select count(*) from public.pokemon_observations o where o.save_file_id=p.current_save_file_id
          and o.source='box' and o.box_number=p.dead_box_number)
        +greatest((select count(*) from public.redemptions e where e.season_id=p_season_id and e.trainer_id=p.trainer_id
            and e.effect_code='revive' and e.status='applied'),
          (select count(*) from public.purchases u join public.shop_items i on i.id=u.shop_item_id
            where u.season_player_id=p.id and u.status='used' and i.code='revivir_pokemon'))
        -public.purchased_revive_overlap(p_season_id,p.trainer_id,p.current_save_file_id)
        +2::bigint*coalesce(st.revived_after_wipe,0) end as deaths,
      coalesce((select sum(greatest(coalesce(points_amount,amount::numeric),0)) from public.penalties pe
        where pe.season_id=p_season_id and pe.trainer_id=p.trainer_id and public.trials_penalty_current(pe)
          and (pe.effective_from_matchday_number is null or pe.effective_from_matchday_number<=next_number)
          and pe.penalty_type='points_reduction' and (pe.matchday_id is null or pe.matchday_id=next_id)
          and (pe.trial_case_id is null or exists(select 1 from public.trial_cases tc where tc.id=pe.trial_case_id
            and tc.status='resolved' and tc.accused_trainer_id=p.trainer_id
            and (tc.season_id is null or tc.season_id=p_season_id)))),0) as reduction) g
    cross join lateral (select case when live and g.deaths is not null
      then g.earned-g.reduction-round(0.1*g.deaths,1) end as current) f
  ) z;
  -- Every official row keeps its place; a mismatch keeps the 068 read as is.
  if jsonb_array_length(coalesce(rows,'[]'::jsonb))<>jsonb_array_length(result->'rows') then return result; end if;
  return jsonb_set(result,'{rows}',coalesce(rows,'[]'::jsonb));
end $$;

do $$ declare f regprocedure; begin
  foreach f in array array[
    'public.single_round_robin_config(public.season_config_versions)'::regprocedure,
    'public.single_league_common_coins(jsonb)'::regprocedure,
    'public.admin_setup_validate_config(uuid,jsonb)'::regprocedure,
    'public.admin_setup_validate_config_v072(uuid,jsonb)'::regprocedure,
    'public.matchday_context(text,jsonb)'::regprocedure,
    'public.matchday_commit_close(text,jsonb,jsonb,jsonb)'::regprocedure,
    'public.matchday_commit_close_v034(text,jsonb,jsonb,jsonb)'::regprocedure,
    'public.check_purchase_acquisition()'::regprocedure,
    'public.league_general_read(uuid)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
