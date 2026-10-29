-- 070: corrections from the real test of 2026-10-29.
-- 1) Each participant's dead box is an explicit setting, default Box 8 (every
--    existing participant keeps it). Deaths, revive targets and overlap,
--    initial divisions, closings, robbery targets and the League read it
--    instead of a fixed Box 8. Only an administrator changes it, with an
--    audited command; it never moves on its own when a save unlocks boxes.
-- 2) The League shows ONE total per trainer. Closings keep their cumulative
--    deductions; during an active season the read applies the current ones,
--    so a death or sanction counts at once and a closing only adds points.
-- 3) Owner request (2026-10-29): Anto's participation in the active season
--    (Pokémon Y, no Box 8 in that game) counts Box 7.
begin;

-- 1. Dead box per participant -----------------------------------------------
-- On season_players, not season_player_stats: the stats rows are part of the
-- closing fingerprint (matchday_external_facts) that corrections compare.
alter table public.season_players add column dead_box_number smallint not null default 8
  constraint season_players_dead_box_number_check check (dead_box_number between 1 and 32);

create function public.participant_dead_box(sid uuid,tid uuid) returns smallint
language sql stable security invoker set search_path=pg_catalog,public as $$
  select coalesce((select dead_box_number from public.season_players
    where season_id=sid and trainer_id=tid),8::smallint)
$$;

-- Occupied slots of one complete observed box; anything partial is unknown.
create function public.league_observed_dead_count(payload jsonb,p_box integer) returns integer
language plpgsql immutable security invoker set search_path=pg_catalog,public as $$
declare box jsonb; slot jsonb; seen integer[]='{}'; n integer; occupied integer=0;
begin
  if jsonb_typeof(payload->'boxes') is distinct from 'array' or p_box is null then return null; end if;
  if (select count(*) from jsonb_array_elements(payload->'boxes') b
      where b->'box_number'=to_jsonb(p_box))<>1 then return null; end if;
  select b into box from jsonb_array_elements(payload->'boxes') b where b->'box_number'=to_jsonb(p_box);
  if jsonb_typeof(box->'slots') is distinct from 'array' then return null; end if;
  if jsonb_array_length(box->'slots')<>30 then return null; end if;
  for slot in select * from jsonb_array_elements(box->'slots') loop
    if jsonb_typeof(slot->'slot_number') is distinct from 'number'
       or (slot->>'slot_number') !~ '^([1-9]|[12][0-9]|30)$'
       or not (slot ? 'pokemon') then return null; end if;
    n=(slot->>'slot_number')::integer;
    if n=any(seen) then return null; end if;
    seen=array_append(seen,n);
    if slot->'pokemon'<>'null'::jsonb then
      if jsonb_typeof(slot->'pokemon') is distinct from 'object'
         or jsonb_typeof(slot#>'{pokemon,species}') is distinct from 'string'
         or length(btrim(slot#>>'{pokemon,species}'))=0 then return null; end if;
      occupied=occupied+1;
    end if;
  end loop;
  return occupied;
end $$;

-- The same bodies as 039/061 with the participant's box in place of 8. A
-- robbery still takes only from Boxes 1-7 (or the team), never from the
-- victim's dead box. The engineering-only physical revive (054 item uses,
-- disabled in production) keeps its Box 8 contract unchanged.
create or replace function public.purchased_revive_overlap(sid uuid,tid uuid,save_id uuid) returns bigint
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare historical bigint; mapped bigint; dead smallint=public.participant_dead_box(sid,tid);
begin
 select count(*) into mapped from public.redemptions r where r.season_id=sid and r.trainer_id=tid
   and r.effect_code='revive' and r.status='applied' and r.target_pokemon_entity_id is not null and r.identity_revision_id is not null;
 select greatest((select count(*) from public.redemptions r where r.season_id=sid and r.trainer_id=tid
     and r.effect_code='revive' and r.status='applied'),
   (select count(*) from public.purchases u join public.shop_items i on i.id=u.shop_item_id
     where u.season_id=sid and u.trainer_id=tid and u.status='used' and i.code='revivir_pokemon')) into historical;
 if exists(select 1 from public.pokemon_observations o where o.save_file_id=save_id and o.source='box' and o.box_number=dead)
   and (historical>mapped or exists(select 1 from public.pokemon_observations o
     join public.redemptions r on r.target_pokemon_entity_id=any(o.candidate_entity_ids)
     where o.save_file_id=save_id and o.source='box' and o.box_number=dead and o.pokemon_entity_id is null
       and r.season_id=sid and r.trainer_id=tid and r.effect_code='revive' and r.status='applied')) then
   -- An unlinked legacy counter/ambiguous identity cannot prove which visible
   -- death overlaps. Propagate UNKNOWN rather than invent an additional death.
   return null;
 end if;
 return (select count(*) from public.pokemon_observations current
 join public.pokemon_identity_revisions head on head.id=current.revision_id
 where current.season_id=sid and current.trainer_id=tid and current.save_file_id=save_id
   and current.source='box' and current.box_number=dead and current.pokemon_entity_id is not null
   and exists(select 1 from public.redemptions r join public.pokemon_identity_revisions used on used.id=r.identity_revision_id
     where r.season_id=sid and r.trainer_id=tid and r.effect_code='revive' and r.status='applied'
       and r.target_pokemon_entity_id=current.pokemon_entity_id and used.revision_number<=head.revision_number
       and not exists(select 1 from public.pokemon_observations alive
         join public.pokemon_identity_revisions later on later.id=alive.revision_id
         where alive.season_id=sid and alive.trainer_id=tid and alive.pokemon_entity_id=current.pokemon_entity_id
           and later.revision_number>used.revision_number and later.revision_number<=head.revision_number
           and (alive.source='party' or (alive.source='box' and alive.box_number<>dead)))));
end $$;

create or replace function public.matchday_context_v034(op text,r jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
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
      'dead_count',(select count(*) from public.pokemon_observations o where o.save_file_id=p.current_save_file_id and o.source='box' and o.box_number=p.dead_box_number)
        +greatest((select count(*) from public.redemptions e where e.season_id=sid and e.trainer_id=p.trainer_id and e.effect_code='revive' and e.status='applied'),
          (select count(*) from public.purchases u join public.shop_items i on i.id=u.shop_item_id where u.season_player_id=p.id and u.status='used' and i.code='revivir_pokemon'))
        -public.purchased_revive_overlap(sid,p.trainer_id,p.current_save_file_id)
        +2::bigint*st.revived_after_wipe,
      'points_reduction',coalesce((select sum(greatest(coalesce(points_amount,amount::numeric),0)) from public.penalties pe where pe.season_id=sid and pe.trainer_id=p.trainer_id
        and public.trials_penalty_current(pe) and (pe.effective_from_matchday_number is null or pe.effective_from_matchday_number<=d.number)
        and pe.penalty_type='points_reduction' and (pe.matchday_id is null or pe.matchday_id=did)
        and (pe.trial_case_id is null or exists(select 1 from public.trial_cases tc where tc.id=pe.trial_case_id and tc.status='resolved'
          and tc.accused_trainer_id=p.trainer_id and (tc.season_id is null or tc.season_id=sid)))),0)::text,
      'coins_reduction',coalesce((select sum(greatest(amount,0)) from public.penalties pe where pe.season_id=sid and pe.trainer_id=p.trainer_id
        and public.trials_penalty_current(pe) and pe.penalty_type='coins_reduction' and (pe.matchday_id is null or pe.matchday_id=did)
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

create or replace function public.initial_assignment_observations_v067(sid uuid) returns jsonb
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
    source_valid=public.observed_save_source_valid(saved,parsed,p.trainer_id);
    progress=public.observed_save_progress(saved,parsed,p.trainer_id);
    progress_valid=progress is not null;
    primary_region=progress->>'primary_region'; flags=progress#>'{regions,0,badge_flags}';
    if progress_valid then
      select count(*) into badges from jsonb_array_elements(flags) f where f='true'::jsonb;
    end if;
    -- Absence from a partially parsed box cannot be interpreted as zero deaths.
    valid=source_valid and wipe_count is not null and jsonb_typeof(parsed.payload->'boxes')='array';
    if valid then
      if (select count(*) from jsonb_array_elements(parsed.payload->'boxes') b where b->'box_number'=to_jsonb(p.dead_box_number))<>1 then
        valid=false;
      else
        select b into box from jsonb_array_elements(parsed.payload->'boxes') b where b->'box_number'=to_jsonb(p.dead_box_number);
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
                 where revision_id=ident.id and source='box' and box_number=p.dead_box_number)
              union all
              (select slot_number,evidence from public.pokemon_observations
                 where revision_id=ident.id and source='box' and box_number=p.dead_box_number
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
      select count(*)+revive_count-public.purchased_revive_overlap(sid,p.trainer_id,saved.id)+2::bigint*wipe_count into deaths from public.pokemon_observations
        where save_file_id=saved.id and source='box' and box_number=p.dead_box_number;
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

create or replace function public.api_redeem_purchase(
  p_season_id uuid, p_trainer_id uuid, p_purchase_id uuid, p_pokemon_entity_id uuid,
  p_idempotency_key text, p_expected_revision_id uuid
) returns jsonb language plpgsql security invoker set search_path='' as $$
declare
  v_player public.season_players;
  v_victim public.season_players;
  v_purchase public.purchases;
  v_redemption public.redemptions;
  v_entity public.pokemon_entities;
  v_head public.pokemon_identity_revisions;
  v_observation public.pokemon_observations;
  v_cycle public.robbery_cycles;
  v_active uuid[];
  v_code text;
  v_effect text;
  v_physical text;
  v_gift uuid;
  v_voucher uuid;
  v_id uuid := gen_random_uuid();
  v_event uuid := gen_random_uuid();
  v_now timestamptz := transaction_timestamp();
  v_receipt jsonb;
begin
  if p_idempotency_key is null or length(p_idempotency_key) not between 1 and 128
    or p_idempotency_key !~ '^[!-~]+$' or p_pokemon_entity_id is null then
    raise sqlstate 'PT409' using message='invalid_redemption_request'; end if;
  perform 1 from public.trainers where id=p_trainer_id and globally_enabled for share;
  if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
  -- Serialize the cycle before any wallet lock. NO KEY UPDATE remains compatible
  -- with FK KEY SHARE locks taken by an in-flight identity reconciliation.
  perform 1 from public.seasons where id=p_season_id for no key update;
  if not found then raise sqlstate 'PT404' using message='season_not_found'; end if;
  v_active := array[]::uuid[];
  for v_player in select * from public.season_players where season_id=p_season_id order by id for update loop
    if v_player.status='active' then v_active:=array_append(v_active,v_player.trainer_id); end if;
  end loop;
  select * into v_player from public.season_players where season_id=p_season_id and trainer_id=p_trainer_id;
  if not found or v_player.status<>'active' then
    raise sqlstate 'PT403' using message='participant_inactive'; end if;
  select * into v_purchase from public.purchases where id=p_purchase_id
    and season_id=p_season_id and trainer_id=p_trainer_id for update;
  if not found then raise sqlstate 'PT404' using message='purchase_not_found'; end if;
  select * into v_redemption from public.redemptions where purchase_id=v_purchase.id;
  if found then
    if v_redemption.idempotency_key is distinct from p_idempotency_key then
      raise sqlstate 'PT409' using message='purchase_already_redeemed'; end if;
    if v_redemption.target_pokemon_entity_id is distinct from p_pokemon_entity_id then
      raise sqlstate 'PT409' using message='idempotency_conflict'; end if;
    return v_redemption.receipt;
  end if;
  if v_purchase.status<>'pending' or v_purchase.quantity<>1 then
    raise sqlstate 'PT409' using message='purchase_not_redeemable'; end if;
  select code into v_code from public.shop_items where id=v_purchase.shop_item_id for share;
  v_effect := case v_code when 'blindar_pokemon' then 'shield' when 'revivir_pokemon' then 'revive'
    when 'robbery_shield_voucher' then 'robbery_shield' when 'robar_pokemon' then 'steal' end;
  if v_effect is null then raise sqlstate 'PT409' using message='redemption_not_supported'; end if;
  select * into v_entity from public.pokemon_entities where id=p_pokemon_entity_id
    and season_id=p_season_id for update;
  if not found then raise sqlstate 'PT409' using message='pokemon_not_owned'; end if;
  if v_effect='steal' then
    if v_entity.owner_trainer_id=p_trainer_id then
      raise sqlstate 'PT409' using message='steal_self_target'; end if;
    select * into v_victim from public.season_players
      where season_id=p_season_id and trainer_id=v_entity.owner_trainer_id;
    if not found or not (v_victim.trainer_id=any(v_active)) then
      raise sqlstate 'PT409' using message='steal_victim_ineligible'; end if;
  elsif v_entity.owner_trainer_id<>p_trainer_id then
    raise sqlstate 'PT409' using message='pokemon_not_owned';
  end if;
  select * into v_head from public.pokemon_identity_revisions
    where season_id=p_season_id and trainer_id=v_entity.owner_trainer_id
    order by revision_number desc limit 1 for share;
  if not found or v_entity.identity_status<>'unambiguous' then
    raise sqlstate 'PT409' using message='pokemon_identity_ambiguous'; end if;
  if v_head.id is distinct from p_expected_revision_id then
    raise sqlstate 'PT409' using message='pokemon_target_stale'; end if;
  select * into v_observation from public.pokemon_observations
    where revision_id=v_head.id and pokemon_entity_id=v_entity.id
      and trainer_id=v_entity.owner_trainer_id and season_id=p_season_id
      and outcome in ('NEW','MATCHED') for share;
  if not found then raise sqlstate 'PT409' using message='pokemon_identity_ambiguous'; end if;
  if v_effect='steal' and v_observation.source='box' and (v_observation.box_number not between 1 and 7
      or v_observation.box_number=public.participant_dead_box(p_season_id,v_observation.trainer_id)) then
    raise sqlstate 'PT409' using message='steal_target_ineligible'; end if;
  if v_observation.source='box' and v_observation.box_number not between 1 and greatest(8,public.participant_dead_box(p_season_id,v_observation.trainer_id)) then
    raise sqlstate 'PT409' using message='invalid_pokemon_target'; end if;
  if v_effect='revive' and not (v_observation.source='box' and v_observation.box_number=public.participant_dead_box(p_season_id,v_observation.trainer_id)) then
    raise sqlstate 'PT409' using message='pokemon_not_revivable'; end if;
  if v_effect='revive' and exists(select 1 from public.redemptions r
    join public.pokemon_identity_revisions used on used.id=r.identity_revision_id
    where r.season_id=p_season_id and r.trainer_id=p_trainer_id and r.effect_code='revive' and r.status='applied'
      and r.target_pokemon_entity_id=v_entity.id and not exists(
        select 1 from public.pokemon_observations alive join public.pokemon_identity_revisions later on later.id=alive.revision_id
        where alive.season_id=p_season_id and alive.trainer_id=p_trainer_id and alive.pokemon_entity_id=v_entity.id
          and later.revision_number>used.revision_number and later.revision_number<=v_head.revision_number
          and (alive.source='party' or (alive.source='box' and alive.box_number<>public.participant_dead_box(p_season_id,p_trainer_id))))) then
    raise sqlstate 'PT409' using message='pokemon_revive_pending'; end if;
  if v_effect<>'revive' and exists (
    select 1 from public.pokemon_entity_flags f left join public.pokemon_flags l on l.id=f.legacy_flag_id
    where f.season_id=p_season_id and f.pokemon_entity_id=v_entity.id and f.flag_type='blindado'
      and coalesce(f.flag_value,l.flag_value,false)
  ) then
    if v_effect='steal' then raise sqlstate 'PT409' using message='steal_target_shielded'; end if;
    raise sqlstate 'PT409' using message='pokemon_already_shielded';
  end if;

  if v_effect='steal' then
    insert into public.robbery_cycles(season_id) values(p_season_id) on conflict do nothing;
    select * into v_cycle from public.robbery_cycles where season_id=p_season_id for update;
    -- Legacy also checks completeness BEFORE selection, e.g. after a retirement.
    if not exists (select 1 from unnest(v_active) t(id) where not exists (
      select 1 from public.redemptions r where r.season_id=p_season_id
        and r.robbery_cycle_number=v_cycle.cycle_number and r.target_owner_trainer_id=t.id)) then
      update public.robbery_cycles set cycle_number=cycle_number+1,history_watermark_id=last_redemption_id
        where season_id=p_season_id returning * into v_cycle;
      update public.trainer_flags set flag_value=false,payload='{}' where season_id=p_season_id
        and flag_type='robbed' and trainer_id=any(v_active);
    end if;
    if exists (select 1 from public.redemptions where season_id=p_season_id
      and robbery_cycle_number=v_cycle.cycle_number and target_owner_trainer_id=v_entity.owner_trainer_id) then
      raise sqlstate 'PT409' using message='steal_victim_already_robbed'; end if;
    select id into v_voucher from public.shop_items where code='robbery_shield_voucher'
      and acquisition_mode='reward_only' for share;
    if not found then raise sqlstate 'PT409' using message='steal_cycle_conflict'; end if;
    v_gift:=gen_random_uuid();
  end if;
  v_physical := case when v_effect in ('revive','steal') then 'pending' else 'not_required' end;
  v_receipt := jsonb_build_object('redemption_id',v_id,'purchase_id',v_purchase.id,
    'season_id',p_season_id,'trainer_id',p_trainer_id,'shop_item_id',v_purchase.shop_item_id,
    'effect_code',v_effect,'target_pokemon_entity_id',v_entity.id,'target_owner_trainer_id',v_entity.owner_trainer_id,
    'purchase_status','used','redemption_status','applied','physical_effect_status',v_physical,
    'requested_at',v_now,'redeemed_at',v_now,'physical_effect_completed_at',null,
    'activity_event_id',v_event,'gift_purchase_id',v_gift);
  insert into public.redemptions(id,purchase_id,season_id,trainer_id,season_player_id,shop_item_id,
    redemption_type,status,payload,redeemed_at,idempotency_key,effect_code,target_pokemon_entity_id,
    target_owner_trainer_id,identity_revision_id,physical_effect_status,requested_at,activity_event_id,receipt,
    gift_purchase_id,robbery_cycle_number)
  values(v_id,v_purchase.id,p_season_id,p_trainer_id,v_player.id,v_purchase.shop_item_id,
    v_effect,'applied',jsonb_build_object('item_code',v_code,'effect_code',v_effect,
      'target_pokemon_entity_id',v_entity.id,'target_owner_trainer_id',v_entity.owner_trainer_id),v_now,
    p_idempotency_key,v_effect,v_entity.id,v_entity.owner_trainer_id,v_head.id,v_physical,v_now,v_event,v_receipt,
    v_gift,v_cycle.cycle_number);
  insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_value)
    values(p_season_id,v_entity.owner_trainer_id,v_entity.id,'blindado',true)
    on conflict(season_id,pokemon_entity_id,flag_type) do update
      set flag_value=true,legacy_flag_id=null,flag_timestamp=null,flag_trainer_id=null;
  if v_effect in ('revive','steal') then
    insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_timestamp)
      values(p_season_id,v_entity.owner_trainer_id,v_entity.id,
        case v_effect when 'revive' then 'revivido_at' else 'robado_at' end,v_now)
      on conflict(season_id,pokemon_entity_id,flag_type) do update
        set flag_timestamp=v_now,flag_value=null,legacy_flag_id=null,flag_trainer_id=null;
  end if;
  if v_effect in ('steal','robbery_shield') then
    insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_value)
      values(p_season_id,v_entity.owner_trainer_id,v_entity.id,
        case v_effect when 'steal' then 'robado' else 'blindaje_por_robo' end,true)
      on conflict(season_id,pokemon_entity_id,flag_type) do update
        set flag_value=true,legacy_flag_id=null,flag_timestamp=null,flag_trainer_id=null;
  end if;
  if v_effect='steal' then
    insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_trainer_id)
      values(p_season_id,v_entity.owner_trainer_id,v_entity.id,'robado_from',v_entity.owner_trainer_id)
      on conflict(season_id,pokemon_entity_id,flag_type) do update
        set flag_trainer_id=excluded.flag_trainer_id,flag_value=null,flag_timestamp=null,legacy_flag_id=null;
    insert into public.trainer_flags(season_id,trainer_id,season_player_id,flag_type,flag_value,payload)
      values(p_season_id,v_victim.trainer_id,v_victim.id,'robbed',true,
        jsonb_build_object('robbed_at',v_now,'robbed_by',p_trainer_id,'robbed_source','live',
          'redemption_id',v_id,'cycle_number',v_cycle.cycle_number))
      on conflict(season_id,trainer_id,flag_type) do update set flag_value=true,payload=excluded.payload;
    update public.robbery_cycles set last_redemption_id=v_id where season_id=p_season_id;
    if not exists (select 1 from unnest(v_active) t(id) where not exists (
      select 1 from public.redemptions r where r.season_id=p_season_id
        and r.robbery_cycle_number=v_cycle.cycle_number and r.target_owner_trainer_id=t.id)) then
      update public.robbery_cycles set cycle_number=cycle_number+1,history_watermark_id=v_id where season_id=p_season_id;
      update public.trainer_flags set flag_value=false,payload='{}' where season_id=p_season_id
        and flag_type='robbed' and trainer_id=any(v_active);
    end if;
    insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,
      quantity,unit_price,status,acquisition_type,origin_redemption_id)
      values(v_gift,p_season_id,p_trainer_id,v_player.id,v_voucher,1,0,'pending','reward',v_id);
  end if;
  update public.purchases set status='used' where id=v_purchase.id;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,trainer_id,visibility,dedupe_key,payload)
    values(v_event,p_season_id,'REDEMPTION_USED',p_trainer_id,p_trainer_id,'owner',
      'redemption_used:'||v_id::text,v_receipt);
  return v_receipt;
end $$;

create or replace function public.api_prepare_transfer(p_request jsonb) returns jsonb language plpgsql security definer set search_path='' as $$
declare sid uuid:=(p_request->>'season_id')::uuid; tid uuid:=(p_request->>'trainer_id')::uuid;
 pid uuid:=(p_request->>'purchase_id')::uuid; eid uuid:=(p_request->>'pokemon_entity_id')::uuid;
 op uuid:=(p_request->>'operation_id')::uuid; a public.item_use_authorizations; e public.pokemon_entities;
 donor public.season_players; receiver public.season_players; dhead public.pokemon_identity_revisions; rhead public.pokemon_identity_revisions;
 ds public.save_files; rs public.save_files; obs public.pokemon_observations; cyc bigint;
begin
 if op is null then raise sqlstate 'PT422' using message='invalid_transfer'; end if;
 perform 1 from public.trainers where id=tid and globally_enabled for share;
 if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
 perform 1 from public.seasons where id=sid for no key update;
 perform 1 from public.season_players where season_id=sid order by id for update;
 select * into a from public.item_use_authorizations where purchase_id=pid for update;
 if found then
  if a.trainer_id is distinct from tid or a.season_id is distinct from sid or a.target_pokemon_entity_id is distinct from eid or a.operation_id is distinct from op::text
    or not exists(select 1 from public.item_use_transfers where authorization_id=a.id) then raise sqlstate 'PT409' using message='transfer_conflict'; end if;
  return jsonb_build_object('authorization_id',a.id,'status',public.transfer_state(a.id));
 end if;
 select * into e from public.pokemon_entities where id=eid and season_id=sid and identity_status='unambiguous' for update;
 if not found or e.owner_trainer_id=tid then raise sqlstate 'PT409' using message='transfer_target_invalid'; end if;
 select * into donor from public.season_players where season_id=sid and trainer_id=e.owner_trainer_id and status='active';
 select * into receiver from public.season_players where season_id=sid and trainer_id=tid and status='active';
 if donor.id is null or receiver.id is null or not exists(select 1 from public.trainers where id=e.owner_trainer_id and globally_enabled) then raise sqlstate 'PT409' using message='participant_inactive'; end if;
 perform 1 from public.purchases p join public.shop_items i on i.id=p.shop_item_id where p.id=pid and p.season_id=sid and p.trainer_id=tid and p.status='pending' and p.quantity=1 and i.code='robar_pokemon' for update of p;
 if not found then raise sqlstate 'PT409' using message='purchase_not_redeemable'; end if;
 select * into dhead from public.pokemon_identity_revisions where season_id=sid and trainer_id=donor.trainer_id order by revision_number desc limit 1;
 select * into rhead from public.pokemon_identity_revisions where season_id=sid and trainer_id=tid order by revision_number desc limit 1;
 select * into ds from public.save_files where id=donor.current_save_file_id and trainer_id=donor.trainer_id and season_id=sid and deleted_at is null and parser_status='parsed';
 select * into rs from public.save_files where id=receiver.current_save_file_id and trainer_id=tid and season_id=sid and deleted_at is null and parser_status='parsed';
 if ds.id is null or rs.id is null or dhead.id is null or rhead.id is null or dhead.save_file_id<>ds.id or rhead.save_file_id<>rs.id then raise sqlstate 'PT409' using message='save_context_changed'; end if;
 if ds.metadata->'save_identity'->>'game' is distinct from rs.metadata->'save_identity'->>'game' then raise sqlstate 'PT409' using message='transfer_cross_title_forbidden'; end if;
 select * into obs from public.pokemon_observations where revision_id=dhead.id and pokemon_entity_id=eid and outcome in ('NEW','MATCHED');
 if not found or not (obs.source='box' and obs.box_number between 1 and 7
   and obs.box_number<>public.participant_dead_box(sid,obs.trainer_id) or obs.source='party' and obs.slot_number between 1 and 6) then raise sqlstate 'PT409' using message='transfer_native_scope_unqualified'; end if;
 if exists(select 1 from public.pokemon_entity_flags f left join public.pokemon_flags l on l.id=f.legacy_flag_id where f.season_id=sid and f.pokemon_entity_id=eid and f.flag_type in ('blindado','robado') and coalesce(f.flag_value,l.flag_value,false)) then raise sqlstate 'PT409' using message='steal_target_shielded'; end if;
 select coalesce((select cycle_number from public.robbery_cycles where season_id=sid),1) into cyc;
 -- Match025 pre-check reset semantics, without changing the cursor before use.
 if not exists(select 1 from public.season_players sp join public.trainers t on t.id=sp.trainer_id where sp.season_id=sid and sp.status='active' and t.globally_enabled and not exists(select 1 from public.redemptions r where r.season_id=sid and r.robbery_cycle_number=cyc and r.target_owner_trainer_id=sp.trainer_id)) then cyc:=cyc+1; end if;
 if exists(select 1 from public.redemptions where season_id=sid and robbery_cycle_number=cyc and target_owner_trainer_id=donor.trainer_id) then raise sqlstate 'PT409' using message='steal_victim_already_robbed'; end if;
 -- A decided robbery stops reserving its trainers once their own side is settled.
 if exists(select 1 from public.item_use_authorizations ia where ia.season_id=sid and ia.status<>'APPLIED_VERIFIED'
    and (ia.target_pokemon_entity_id=eid or ia.trainer_id in(tid,donor.trainer_id))
    and not exists(select 1 from public.item_use_transfers x where x.authorization_id=ia.id and (x.terminal='CANCELLED' or x.adjudicated_at is not null)))
  or exists(select 1 from public.item_use_transfer_legs l where l.season_id=sid and l.trainer_id in(tid,donor.trainer_id) and not l.released)
 then raise sqlstate 'PT409' using message='transfer_reserved'; end if;
 insert into public.item_use_authorizations(operation_id,idempotency_key,purchase_id,season_id,trainer_id,target_pokemon_entity_id,save_file_id,save_sha256,identity_revision_id,effect_code)
 values(op::text,op::text,pid,sid,tid,eid,rs.id,rs.sha256,dhead.id,'steal') returning * into a;
 insert into public.item_use_transfers(authorization_id,donor_id) values(a.id,donor.trainer_id);
 insert into public.item_use_transfer_legs(authorization_id,side,season_id,trainer_id,save_file_id,identity_revision_id,source_sha256) values
 (a.id,'source',sid,donor.trainer_id,ds.id,dhead.id,ds.sha256),(a.id,'destination',sid,tid,rs.id,rhead.id,rs.sha256);
 return jsonb_build_object('authorization_id',a.id,'status','REQUESTED');
end $$;


-- 2. One League total ------------------------------------------------------
-- The official total is the earned position points minus the LAST closing's
-- cumulative deductions (public_sanctioned_points). During an active season
-- the read uses the current deductions from the same inputs the next closing
-- uses (matchday_context: round(0.2 per adjusted death,1) plus resolved points
-- sanctions). That closing then only adds its position points: nothing is
-- subtracted twice. official_points keeps the closed figure; finished seasons
-- show it as is. Read only: nothing is written, paid or penalized here.
create or replace function public.league_general_read(p_season_id uuid) returns jsonb
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare result jsonb; next_number integer; next_id uuid; live boolean; rows jsonb;
begin
  result=public.league_general_read_v068(p_season_id);
  if result is null then return result; end if;
  live=result#>>'{season,status}'='active';
  select id,number into next_id,next_number from public.matchdays
    where season_id=p_season_id and status<>'closed' order by number limit 1;
  if next_number is null then
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
        where sp.season_id=p_season_id and sp.season_player_id=p.id),0) as earned,
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
      then g.earned-g.reduction-round(0.2*g.deaths,1) end as current) f
  ) z;
  -- Every official row keeps its place; a mismatch keeps the 068 read as is.
  if jsonb_array_length(coalesce(rows,'[]'::jsonb))<>jsonb_array_length(result->'rows') then return result; end if;
  return jsonb_set(result,'{rows}',coalesce(rows,'[]'::jsonb));
end $$;

-- 3. Changing a participant's dead box ---------------------------------------
-- Administrator only, draft or active season, idempotent receipt and an admin
-- activity event with before/after. Closed matchdays keep their snapshots.
create function public.api_admin_set_dead_box(p_request jsonb) returns jsonb
language plpgsql set search_path=pg_catalog,public as $$
declare cached jsonb; sid uuid=(p_request->>'season_id')::uuid; pid uuid=(p_request->>'resource_id')::uuid;
  b jsonb=p_request->'body'; p public.season_players; s public.seasons;
begin
  cached=public.admin_setup_begin('dead_box',p_request); if cached is not null then return cached; end if;
  if pid is null or jsonb_typeof(b) is distinct from 'object' or b-array['dead_box_number']<>'{}'::jsonb
    or jsonb_typeof(b->'dead_box_number') is distinct from 'number'
    or (b->>'dead_box_number') !~ '^([1-9]|[12][0-9]|3[0-2])$' then
    perform public.admin_setup_fail('invalid_request',422); end if;
  select * into s from public.seasons where id=sid;
  if s.status not in ('draft','active') then perform public.admin_setup_fail('season_not_editable'); end if;
  select * into p from public.season_players where id=pid and season_id=sid;
  if not found then perform public.admin_setup_fail('participant_not_found',404); end if;
  update public.season_players set dead_box_number=(b->>'dead_box_number')::smallint where id=pid;
  return public.admin_setup_finish('dead_box',p_request,sid,pid,jsonb_build_object('trainer_id',p.trainer_id,
    'before',p.dead_box_number,'after',(b->>'dead_box_number')::integer));
end $$;

-- 4. Owner request: the active season's Anto participation counts Box 7 ------
update public.season_players p set dead_box_number=7
  from public.seasons s, public.trainers t
  where s.id=p.season_id and s.status='active' and t.id=p.trainer_id and lower(t.display_name)='anto';

do $$ declare f regprocedure; begin
  foreach f in array array[
    'public.participant_dead_box(uuid,uuid)'::regprocedure,
    'public.league_observed_dead_count(jsonb,integer)'::regprocedure,
    'public.league_general_read(uuid)'::regprocedure,
    'public.api_admin_set_dead_box(jsonb)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
