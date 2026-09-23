-- Phase 8I: permanent competitive withdrawal, never account disabling or history deletion.
begin;

alter table public.season_players
  add column status_effective_matchday_number integer,
  add column status_reason text,
  add column status_changed_by_trainer_id uuid references public.trainers(id),
  add constraint participant_status_evidence_chk check (
    (status_effective_matchday_number is null and status_reason is null and status_changed_by_trainer_id is null)
    or (status<>'active' and status_effective_matchday_number>0 and status_effective_matchday_number is not null
      and status_reason is not null and length(btrim(status_reason)) between 1 and 500
      and status_changed_by_trainer_id is not null and left_at is not null));

-- Original assignment ranges remain evidence, including an assignment cancelled
-- before its first competitive round. Intersection with this exclusive boundary
-- expresses an empty range without deleting history or inventing round zero.
alter table public.division_memberships
  add column eligibility_ends_before_matchday_number integer
    check (eligibility_ends_before_matchday_number>0);

-- Preserve 018 safe-by-shape public projections; expose only the new round
-- boundaries, not admin reasons/actors or any private source data.
create or replace view public.public_season_players
with (security_invoker=false,security_barrier=true) as
select id,season_id,trainer_id,status,seed_order,joined_at,left_at,created_at,updated_at,
  status_effective_matchday_number from public.season_players;
create or replace view public.public_division_memberships
with (security_invoker=false,security_barrier=true) as
select id,season_id,season_player_id,division_id,effective_from_matchday_number,effective_to_matchday_number,
  source_matchday_id,reason,created_at,eligibility_ends_before_matchday_number from public.division_memberships;

create function public.participant_memberships_at(sid uuid, round_number integer)
returns setof public.division_memberships language sql stable
security invoker set search_path=pg_catalog,public as $$
  select m.* from public.division_memberships m join public.season_players p on p.id=m.season_player_id
  where m.season_id=sid and m.effective_from_matchday_number<=round_number
    and coalesce(m.effective_to_matchday_number,round_number)>=round_number
    and (m.eligibility_ends_before_matchday_number is null or round_number<m.eligibility_ends_before_matchday_number)
    and (p.status='active' or round_number<p.status_effective_matchday_number)
$$;

create function public.participant_status_immutable() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
  if old.status_effective_matchday_number is not null and
    (new.status,new.status_effective_matchday_number,new.status_reason,new.status_changed_by_trainer_id,new.left_at)
    is distinct from (old.status,old.status_effective_matchday_number,old.status_reason,old.status_changed_by_trainer_id,old.left_at) then
    perform public.admin_setup_fail('participant_already_inactive');
  end if;
  return new;
end $$;
create trigger participant_status_evidence_immutable before update on public.season_players
  for each row execute function public.participant_status_immutable();

create function public.api_admin_participant_status(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare r jsonb=p_request; b jsonb=r->'body'; sid uuid=(r->>'season_id')::uuid;
  pid uuid=(r->>'resource_id')::uuid; actor uuid=(r->>'actor_trainer_id')::uuid;
  destination text; cached jsonb; s public.seasons; p public.season_players; d public.matchdays;
  cycle public.robbery_cycles; active_ids uuid[]; result jsonb; stamp timestamptz;
  oid uuid=gen_random_uuid(); eid uuid=gen_random_uuid();
begin
  destination=case r->>'operation' when 'retire' then 'retired' when 'abandon' then 'abandoned'
    when 'disqualify' then 'disqualified' end;
  if destination is null or b is null or jsonb_typeof(b)<>'object'
    or b-array['reason','expected_roster_revision']<>'{}'::jsonb
    or jsonb_typeof(b->'reason') is distinct from 'string' or length(btrim(b->>'reason')) not between 1 and 500
    or jsonb_typeof(b->'expected_roster_revision') is distinct from 'number'
    or (b->>'expected_roster_revision') !~ '^[0-9]+$' then
    perform public.admin_setup_fail('invalid_request',422); end if;
  cached=public.admin_setup_begin('participant_status',r);
  if cached is not null then return cached; end if;
  select * into s from public.seasons where id=sid;
  if s.status<>'active' then perform public.admin_setup_fail('season_not_active'); end if;
  select * into p from public.season_players where id=pid and season_id=sid;
  if not found then perform public.admin_setup_fail('participant_not_found',404); end if;
  if p.status<>'active' then perform public.admin_setup_fail('participant_already_inactive'); end if;
  perform public.admin_setup_cas(sid,b);
  select * into d from public.matchdays where id=s.current_matchday_id and season_id=sid for update;
  if d.status='open' then perform public.admin_setup_fail('round_open'); end if;
  if d.id is null or d.status<>'scheduled' then perform public.admin_setup_fail('matchday_not_scheduled'); end if;
  perform 1 from public.division_memberships where season_id=sid order by id for update;
  perform 1 from public.matches where matchday_id=d.id order by id for update;
  if exists(select 1 from public.team_locks where matchday_id=d.id and season_player_id=pid) then
    perform public.admin_setup_fail('participant_has_current_team_lock'); end if;
  if exists(select 1 from public.matches where matchday_id=d.id and (winner_id is not null or status<>'scheduled' or result_code<>''))
    or exists(select 1 from public.matchday_snapshots where matchday_id=d.id)
    or exists(select 1 from public.matchday_snapshot_revisions where matchday_id=d.id)
    or exists(select 1 from public.matchday_movements where matchday_id=d.id)
    or exists(select 1 from public.coin_transactions where reward_matchday_id=d.id
      or (transaction_type='matchday_reward' and reference_id=d.id))
    or exists(select 1 from public.purchases where origin_matchday_id=d.id)
    or exists(select 1 from public.penalties where matchday_id=d.id)
    or exists(select 1 from public.trial_cases where matchday_id=d.id)
    or exists(select 1 from public.matchdays where season_id=sid and number>d.number) then
    perform public.admin_setup_fail('dependent_data_exists'); end if;
  -- Unknown team membership cannot be safely inferred from arbitrary Cup JSON.
  if exists(select 1 from public.cups c join public.cup_participants cp on cp.cup_id=c.id
      where c.season_id=sid and c.status in ('draft','active')
      and (cp.trainer_id=p.trainer_id or cp.trainer_id is null)) then
    perform public.admin_setup_fail('ongoing_competition_dependency'); end if;
  perform public.matchday_validate(sid,d.id,false);
  stamp=clock_timestamp();
  update public.season_players set status=destination,left_at=stamp,status_reason=btrim(b->>'reason'),
    status_effective_matchday_number=d.number,status_changed_by_trainer_id=actor where id=pid;
  update public.division_memberships set eligibility_ends_before_matchday_number=d.number
    where season_player_id=pid and coalesce(effective_to_matchday_number,d.number)>=d.number;
  -- Only remove the departing player's unpublished pairs. Other match IDs and
  -- every remaining player's day/save Team Lock stay exactly the same.
  delete from public.matches where matchday_id=d.id and pid in (player_a_id,player_b_id);
  perform public.matchday_validate(sid,d.id,false);
  update public.matchdays set revision=revision+1,results_revision=results_revision+1 where id=d.id;
  update public.trainer_flags set flag_value=false,payload='{}'
    where season_id=sid and trainer_id=p.trainer_id and flag_type='robbed';
  select * into cycle from public.robbery_cycles where season_id=sid for update;
  select coalesce(array_agg(trainer_id order by id),array[]::uuid[]) into active_ids
    from public.season_players where season_id=sid and status='active';
  -- Same durable-cycle completeness and watermark rule as 025. No empty-set
  -- rollover: with no active participants there is no next eligible robbery.
  if cycle.season_id is not null and cardinality(active_ids)>0 and not exists (
    select 1 from unnest(active_ids) t(id) where not exists (
      select 1 from public.redemptions e where e.season_id=sid
        and e.robbery_cycle_number=cycle.cycle_number and e.target_owner_trainer_id=t.id)) then
    update public.robbery_cycles set cycle_number=cycle_number+1,history_watermark_id=last_redemption_id where season_id=sid;
    update public.trainer_flags set flag_value=false,payload='{}'
      where season_id=sid and flag_type='robbed' and trainer_id=any(active_ids);
  end if;
  update public.season_admin_state set roster_revision=roster_revision+1,setup_revision=setup_revision+1 where season_id=sid;
  select jsonb_build_object('operation_id',oid,'event_id',eid,'season_id',sid,'participant_id',pid,
    'old_status','active','new_status',destination,'reason',btrim(b->>'reason'),'effective_matchday_id',d.id,
    'effective_matchday_number',d.number,'actor_trainer_id',actor,'changed_at',stamp,
    'roster_revision',a.roster_revision,'setup_revision',a.setup_revision,'replayed',false) into result
    from public.season_admin_state a where season_id=sid;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
    values(eid,sid,'PARTICIPANT_STATUS_CHANGED',actor,'admin','participant-status:'||oid::text,result);
  insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
    values(oid,actor,sid,public.admin_setup_scope('participant_status',r),r->>'idempotency_key',
      encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
  return result;
end $$;

-- 027 replacements below only adapt eligibility, empty divisions and correction
-- invalidation. Existing rewards, movements and receipts keep their contract.

create or replace function public.matchday_external_facts(sid uuid) returns text
language plpgsql set search_path=pg_catalog,public as $$
declare result jsonb='{}'; rows jsonb; t text; extra text;
begin
  -- Content hashes, not timestamps: a waiting transaction can carry an older now().
  foreach t in array array['purchases','coin_transactions','redemptions','team_locks','save_files',
    'pokemon_identity_revisions','pokemon_entity_flags','pokemon_flags','trainer_flags','season_player_stats',
    'penalties','cups','trial_cases'] loop
    extra=case t when 'purchases' then ' and origin_matchday_id is null'
      when 'coin_transactions' then ' and reward_matchday_id is null' else '' end;
    execute format('select coalesce(jsonb_agg(to_jsonb(x) order by to_jsonb(x)::text),''[]''::jsonb) from public.%I x where season_id=$1%s',t,extra)
      into rows using sid;
    result=result||jsonb_build_object(t,rows);
  end loop;
  if exists(select 1 from public.season_players where season_id=sid and status_effective_matchday_number is not null) then
    result=result||jsonb_build_object('participant_boundaries',
      (select jsonb_agg(jsonb_build_object('id',id,'status',status,'effective',status_effective_matchday_number) order by id)
       from public.season_players where season_id=sid));
  end if;
  return encode(sha256(convert_to(result::text,'UTF8')),'hex');
end $$;

create or replace function public.matchday_validate(sid uuid,did uuid,complete boolean) returns void
language plpgsql set search_path=pg_catalog,public as $$
declare d public.matchdays; c public.season_config_versions; total integer; expected integer; v_code text; n integer;
begin
  select * into d from public.matchdays where id=did and season_id=sid;
  if not found then perform public.admin_setup_fail('matchday_not_found',404); end if;
  select * into c from public.season_config_versions where season_id=sid and effective_from_matchday<=d.number
    order by effective_from_matchday desc limit 1;
  if c.id is distinct from d.season_config_version_id or c.division_sizes is null or d.number>c.total_matchdays then
    perform public.admin_setup_fail('config_mismatch'); end if;
  if exists(select 1 from public.season_players where season_id=sid and status<>'active' and status_effective_matchday_number is null) then
    perform public.admin_setup_fail('invalid_roster'); end if;
  select count(*) into total from public.season_players where season_id=sid;
  if total<>(c.division_sizes->>'A')::integer+(c.division_sizes->>'B')::integer then
    perform public.admin_setup_fail('invalid_roster'); end if;
  if exists(select 1 from public.season_players p where p.season_id=sid and (p.status='active' or d.number<p.status_effective_matchday_number) and
    (select count(*) from public.participant_memberships_at(sid,d.number) m where m.season_player_id=p.id
      and m.effective_from_matchday_number<=d.number and coalesce(m.effective_to_matchday_number,d.number)>=d.number)<>1) then
    perform public.admin_setup_fail('invalid_roster'); end if;
  expected=0;
  foreach v_code in array array['A','B'] loop
    select count(*) into n from public.participant_memberships_at(sid,d.number) m join public.divisions v on v.id=m.division_id
      where m.season_id=sid and v.code=v_code and m.effective_from_matchday_number<=d.number
      and coalesce(m.effective_to_matchday_number,d.number)>=d.number;
    if n>(c.division_sizes->>v_code)::integer then perform public.admin_setup_fail('invalid_roster'); end if;
    expected=expected+n*(n-1)/2;
  end loop;
  if (select count(*) from public.matches where matchday_id=did)<>expected or exists (
    select 1 from public.matches x where x.matchday_id=did and (x.status not in ('scheduled','completed')
    or (x.winner_id is null)<>(x.status='scheduled') or not exists (
      select 1 from public.participant_memberships_at(sid,d.number) a join public.participant_memberships_at(sid,d.number) b on a.division_id=b.division_id
      where a.season_player_id=x.player_a_id and b.season_player_id=x.player_b_id and a.division_id=x.division_id
      and a.effective_from_matchday_number<=d.number and coalesce(a.effective_to_matchday_number,d.number)>=d.number
      and b.effective_from_matchday_number<=d.number and coalesce(b.effective_to_matchday_number,d.number)>=d.number))) then
    perform public.admin_setup_fail('invalid_results'); end if;
  if complete and exists(select 1 from public.matches where matchday_id=did and winner_id is null) then
    perform public.admin_setup_fail('results_incomplete'); end if;
end $$;

create or replace function public.matchday_context(op text,r jsonb) returns jsonb
language plpgsql set search_path=pg_catalog,public as $$
declare sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid;
  d public.matchdays; c public.season_config_versions; inputs jsonb; players jsonb; matches jsonb; result jsonb;
begin
  select * into d from public.matchdays where id=did;
  select * into c from public.season_config_versions where id=d.season_config_version_id;
  if (c.rules_json->>'last_b_gets_steal')::boolean and exists (
    select 1 from public.participant_memberships_at(sid,d.number) m join public.divisions v on v.id=m.division_id where v.code='B'
  ) and not exists (
    select 1 from public.shop_items where code='robar_pokemon' and acquisition_mode='purchasable'
  ) then perform public.admin_setup_fail('reward_item_unavailable'); end if;
  if op='correct' then
    select snapshot->'inputs' into inputs from public.matchday_snapshots where matchday_id=did;
  else
    if exists(select 1 from public.season_players p where p.season_id=sid and (p.status='active' or d.number<p.status_effective_matchday_number) and p.current_save_file_id is not null
      and not exists(select 1 from public.pokemon_identity_revisions i where i.save_file_id=p.current_save_file_id)) then
      perform public.admin_setup_fail('ranking_inputs_unavailable'); end if;
    select jsonb_agg(jsonb_build_object('id',p.id,'trainer_id',p.trainer_id,'ranking_key',t.slug,'division',v.code,
      'dead_count',(select count(*) from public.pokemon_observations o where o.save_file_id=p.current_save_file_id and o.source='box' and o.box_number=8)
        +greatest((select count(*) from public.redemptions e where e.season_id=sid and e.trainer_id=p.trainer_id and e.effect_code='revive' and e.status='applied'),
          (select count(*) from public.purchases u join public.shop_items i on i.id=u.shop_item_id where u.season_player_id=p.id and u.status='used' and i.code='revivir_pokemon'))
        +2*st.revived_after_wipe,
      'points_reduction',coalesce((select sum(greatest(amount,0)) from public.penalties pe where pe.season_id=sid and pe.trainer_id=p.trainer_id
        and pe.penalty_type='points_reduction' and (pe.matchday_id is null or pe.matchday_id=did)
        and (pe.trial_case_id is null or exists(select 1 from public.trial_cases tc where tc.id=pe.trial_case_id and tc.status='resolved'
          and tc.accused_trainer_id=p.trainer_id and (tc.season_id is null or tc.season_id=sid)))),0),
      'coins_reduction',coalesce((select sum(greatest(amount,0)) from public.penalties pe where pe.season_id=sid and pe.trainer_id=p.trainer_id
        and pe.penalty_type='coins_reduction' and (pe.matchday_id is null or pe.matchday_id=did)
        and (pe.trial_case_id is null or exists(select 1 from public.trial_cases tc where tc.id=pe.trial_case_id and tc.status='resolved'
          and tc.accused_trainer_id=p.trainer_id and (tc.season_id is null or tc.season_id=sid)))) ,0)) order by p.id) into players
      from public.season_players p join public.trainers t on t.id=p.trainer_id
      join public.season_player_stats st on st.season_player_id=p.id
      join public.participant_memberships_at(sid,d.number) m on m.season_player_id=p.id and m.effective_from_matchday_number<=d.number
        and coalesce(m.effective_to_matchday_number,d.number)>=d.number
      join public.divisions v on v.id=m.division_id where p.season_id=sid;
    select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'player_a_id',x.player_a_id,'player_b_id',x.player_b_id,
      'winner_id',x.winner_id,'division',v.code) order by x.id),'[]'::jsonb) into matches
      from public.matches x join public.divisions v on v.id=x.division_id where x.matchday_id=did;
    inputs=jsonb_build_object('season_id',sid,'day_id',did,'number',d.number,'results_revision',d.results_revision,
      'config',jsonb_build_object('id',c.id,'name',c.name,'effective_from_matchday',c.effective_from_matchday,
        'total_matchdays',c.total_matchdays,'division_sizes',c.division_sizes,'promotion_relegation_count',c.promotion_relegation_count,
        'scoring_json',c.scoring_json,'coin_rewards_json',c.coin_rewards_json,'rules_json',c.rules_json),
      'players',coalesce(players,'[]'::jsonb),'matches',matches);
  end if;
  result=jsonb_build_object('inputs',inputs,'external_facts',public.matchday_external_facts(sid),
    'snapshot_revision',coalesce((select revision from public.matchday_snapshots where matchday_id=did),0),
    'next_config',(select to_jsonb(x) from public.season_config_versions x where x.season_id=sid and x.effective_from_matchday<=d.number+1
      order by x.effective_from_matchday desc limit 1),
    'existing_next_promotions',exists(select 1 from public.shop_promotions p join public.matchdays md on md.id=p.matchday_id
      where p.season_id=sid and md.number=d.number+1),
    'catalog',(select coalesce(jsonb_agg(jsonb_build_object('id',i.id,'code',i.code,'name',i.name,'category',i.category,'base_price',i.base_price,'enabled',i.enabled) order by i.id),'[]'::jsonb)
      from public.shop_items i where i.acquisition_mode='purchasable'),
    'purchase_history',(select coalesce(jsonb_agg(jsonb_build_object('name',i.name,'number',coalesce(md.number,0),'quantity',p.quantity) order by p.id),'[]'::jsonb)
      from public.purchases p join public.shop_items i on i.id=p.shop_item_id left join public.matchdays md
      on md.id=coalesce((p.metadata#>>'{normal_purchase,matchday_id}')::uuid,(p.metadata#>>'{promotional_purchase,matchday_id}')::uuid,p.origin_matchday_id)
      where p.season_id=sid and p.status not in ('cancelled','refunded')),
    'promotion_history',(select coalesce(jsonb_agg(jsonb_build_object('item',i.name,'jornada',md.number) order by p.id),'[]'::jsonb)
      from public.shop_promotions p join public.shop_items i on i.id=p.shop_item_id join public.matchdays md on md.id=p.matchday_id where p.season_id=sid));
  return result;
end $$;

create or replace function public.matchday_commit_close(op text,r jsonb,ctx jsonb,plan jsonb) returns void
language plpgsql set search_path=pg_catalog,public as $$
declare sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid; actor uuid=(r->>'actor_trainer_id')::uuid;
  d public.matchdays; cfg public.season_config_versions; nxtcfg public.season_config_versions;
  old public.matchday_snapshots; v_snapshot jsonb; rev integer; final boolean; nextid uuid; divisionid uuid;
  pid uuid; tid uuid; gift uuid; giftplayer uuid; oldgift public.purchases; row jsonb; divcode text;
  v_amount integer; prior integer; stamp timestamptz=clock_timestamp();
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
  for row in select value from jsonb_array_elements(plan->'standings') loop
    if not exists(select 1 from public.season_players where id=(row->>'trainer_id')::uuid and season_id=sid
      and (status='active' or d.number<status_effective_matchday_number))
      or (row->>'coins_awarded')::integer is distinct from (cfg.coin_rewards_json->>(row->>'position'))::integer
      or (row->>'points_awarded')::integer is distinct from (cfg.scoring_json->>(row->>'position'))::integer then
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
    'final',final,'reason',case when op='correct' then r->'body'->>'reason' else 'close' end);
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

create or replace function public.api_admin_get_setup(p_request jsonb) returns jsonb
language plpgsql set search_path = pg_catalog, public as $$
declare sid uuid=(p_request->>'season_id')::uuid; result jsonb;
begin
  perform public.admin_setup_principal((p_request->>'actor_trainer_id')::uuid);
  -- SHARE holds a coherent multi-query read against every admin mutation.
  perform 1 from public.seasons where id=sid for share;
  if not found then perform public.admin_setup_fail('season_not_found',404); end if;
  select jsonb_build_object('season',jsonb_build_object('id',s.id,'name',s.name,'status',s.status,'started_at',s.started_at),
    'setup_revision',coalesce(a.setup_revision,0),'roster_revision',coalesce(a.roster_revision,0),'config_revision',coalesce(a.config_revision,0),
    'current_matchday_id',s.current_matchday_id,'readiness',public.admin_setup_readiness(sid),
    'participants',(select coalesce(jsonb_agg(jsonb_build_object('id',p.id,'trainer_id',p.trainer_id,'display_name',t.display_name,
      'status',p.status,'status_effective_matchday_number',p.status_effective_matchday_number,'seed_order',p.seed_order,'stats_ready',st.season_player_id is not null) order by p.id),'[]'::jsonb)
      from public.season_players p join public.trainers t on t.id=p.trainer_id
      left join public.season_player_stats st on st.season_player_id=p.id where p.season_id=sid),
    'config_versions',(select coalesce(jsonb_agg(jsonb_build_object('id',c.id,'name',c.name,'version_number',c.version_number,
      'effective_from_matchday',c.effective_from_matchday,'total_matchdays',c.total_matchdays,'division_sizes',c.division_sizes,
      'movement_count',c.promotion_relegation_count,'scoring',c.scoring_json,'coin_rewards',c.coin_rewards_json,'rules',c.rules_json,
      'roster_revision',c.roster_revision,'used',public.admin_setup_config_used(c.id),
      'is_current',coalesce(c.id=(select x.id from public.season_config_versions x where x.season_id=sid
        and x.effective_from_matchday<=coalesce((select number from public.matchdays where id=s.current_matchday_id),1)
        order by x.effective_from_matchday desc limit 1),false)) order by c.effective_from_matchday),'[]'::jsonb)
      from public.season_config_versions c where c.season_id=sid),
    'divisions',(select coalesce(jsonb_agg(jsonb_build_object('id',d.id,'code',d.code,'tier_order',d.tier_order) order by d.tier_order),'[]'::jsonb) from public.divisions d where d.season_id=sid),
    'memberships',(select coalesce(jsonb_agg(jsonb_build_object('season_player_id',m.season_player_id,'division_id',m.division_id,
      'effective_from_matchday',m.effective_from_matchday_number,'effective_to_matchday',m.effective_to_matchday_number,'reason',m.reason,'eligibility_ends_before_matchday_number',m.eligibility_ends_before_matchday_number) order by m.season_player_id),'[]'::jsonb) from public.division_memberships m where m.season_id=sid),
    'first_matchday',(select jsonb_build_object('id',d.id,'number',d.number,'status',d.status,'config_version_id',d.season_config_version_id,
      'match_count',(select count(*) from public.matches where matchday_id=d.id)) from public.matchdays d where d.season_id=sid and number=1)) into result
    from public.seasons s left join public.season_admin_state a on a.season_id=s.id where s.id=sid;
  return result;
end $$;

do $$ declare f regprocedure; begin
  for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and p.proname in ('participant_memberships_at','participant_status_immutable','api_admin_participant_status') loop
    execute format('revoke all on function %s from public,anon,authenticated',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
