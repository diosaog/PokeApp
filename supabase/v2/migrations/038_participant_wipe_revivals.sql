-- Phase 10.5G. Owned live wipe-revival counter; no historical recomputation.
begin;

create function public.api_participant_wipe_revivals(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare op text=p_request->>'operation'; r jsonb=p_request->'request'; b jsonb=r->'body';
  actor uuid=(r->>'actor_trainer_id')::uuid; sid uuid=(r->>'season_id')::uuid;
  scope text=public.admin_setup_scope('participant_wipe_revivals',r); k text=r->>'idempotency_key';
  t public.trainers; s public.seasons; p public.season_players; d public.matchdays;
  st public.season_player_stats; cached public.admin_operation_receipts;
  revision bigint=0; requested integer; reason text; result jsonb; before_count integer;
  oid uuid=gen_random_uuid(); eid uuid=gen_random_uuid();
begin
  if op is null or op not in ('state','set') or jsonb_typeof(r) is distinct from 'object'
    or p_request-array['operation','request']<>'{}'::jsonb
    or r-array['actor_trainer_id','season_id','body','idempotency_key']<>'{}'::jsonb then
    perform public.admin_setup_fail('invalid_request',422); end if;
  select * into t from public.trainers where id=actor for share;
  if not found or not t.globally_enabled then perform public.admin_setup_fail('trainer_disabled',403); end if;
  if op='set' then
    if k is null or length(k) not between 1 and 128 or jsonb_typeof(b) is distinct from 'object'
      or b-array['revived_after_wipe','expected_revision']<>'{}'::jsonb
      or jsonb_typeof(b->'revived_after_wipe') is distinct from 'number'
      or (b->>'revived_after_wipe') !~ '^(0|[1-9][0-9]{0,9})$'
      or jsonb_typeof(b->'expected_revision') is distinct from 'number'
      or (b->>'expected_revision') !~ '^(0|[1-9][0-9]{0,15})$' then
      perform public.admin_setup_fail('invalid_request',422); end if;
    if (b->>'revived_after_wipe')::bigint>2147483647
      or (b->>'expected_revision')::bigint>9007199254740991 then
      perform public.admin_setup_fail('invalid_request',422); end if;
    requested=(b->>'revived_after_wipe')::integer;
    perform pg_advisory_xact_lock(hashtextextended(actor::text||scope||':'||k,0));
  elsif coalesce(b,'{}'::jsonb)<>'{}'::jsonb then
    perform public.admin_setup_fail('invalid_request',422);
  end if;
  -- Same ordering as participant results and admin close/status/initialization:
  -- principal, receipt key, season, ordered roster, current day, own stats.
  select * into s from public.seasons where id=sid for no key update;
  if not found or s.status='discarded' then perform public.admin_setup_fail('season_not_found',404); end if;
  perform 1 from public.season_players where season_id=sid order by id for update;
  select * into p from public.season_players where season_id=sid and trainer_id=actor;
  if not found then perform public.admin_setup_fail('participant_not_found',403); end if;
  if op='set' then
    if p.status<>'active' then perform public.admin_setup_fail('participant_inactive',403); end if;
    select * into cached from public.admin_operation_receipts where actor_trainer_id=actor
      and operation_scope=scope and idempotency_key=k;
    if found then
      if cached.request_hash<>encode(sha256(convert_to(r::text,'UTF8')),'hex') then
        perform public.admin_setup_fail('idempotency_conflict'); end if;
      -- Receipt replay never changes live or frozen state, even after final close.
      return cached.response_json||'{"replayed":true}'::jsonb;
    end if;
  end if;
  select * into d from public.matchdays where id=s.current_matchday_id and season_id=sid for update;
  select * into st from public.season_player_stats where season_player_id=p.id
    and season_id=sid and trainer_id=actor for update;
  if not found or jsonb_typeof(st.metadata) is distinct from 'object' then
    perform public.admin_setup_fail('wipe_state_unavailable',503); end if;
  -- Existing metadata is the narrow extension point. Missing means revision zero;
  -- no default column/table rewrite changes any pre-G row or sporting fingerprint.
  if st.metadata ? 'wipe_revision' then
    if jsonb_typeof(st.metadata->'wipe_revision') is distinct from 'number'
      or (st.metadata->>'wipe_revision') !~ '^(0|[1-9][0-9]{0,15})$' then
      perform public.admin_setup_fail('wipe_state_unavailable',503); end if;
    revision=(st.metadata->>'wipe_revision')::bigint;
    if revision>9007199254740991 then perform public.admin_setup_fail('wipe_state_unavailable',503); end if;
  end if;
  reason=case
    when p.status<>'active' then 'participant_inactive'
    when s.status<>'active' then 'season_inactive'
    when s.current_matchday_id is null then
      case when public.initial_assignment_modern(sid)
        and not exists(select 1 from public.matchdays where season_id=sid)
        then null else 'membership_ineligible' end
    when d.id is null then 'membership_ineligible'
    when d.status not in ('scheduled','open') then 'league_closed'
    when not exists(select 1 from public.participant_memberships_at(sid,d.number) m
      where m.season_player_id=p.id) then 'membership_ineligible'
    else null end;
  if op='set' then
    if reason is not null then perform public.admin_setup_fail('wipe_revivals_not_editable'); end if;
    if (b->>'expected_revision')::bigint<>revision then
      perform public.admin_setup_fail('wipe_revision_conflict'); end if;
    before_count=st.revived_after_wipe;
    if requested<>before_count then
      if revision=9007199254740991 then perform public.admin_setup_fail('wipe_state_unavailable',503); end if;
      revision=revision+1;
      update public.season_player_stats set revived_after_wipe=requested,
        metadata=metadata||jsonb_build_object('wipe_revision',revision)
        where season_player_id=p.id returning * into st;
      insert into public.activity_events(id,season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
        values(eid,sid,'WIPE_REVIVALS_UPDATED',actor,'admin','wipe-revivals:'||oid::text,
          jsonb_build_object('operation_id',oid,'season_player_id',p.id,
            'before',jsonb_build_object('revived_after_wipe',before_count,'revision',revision-1),
            'after',jsonb_build_object('revived_after_wipe',requested,'revision',revision)));
    end if;
  end if;
  result=jsonb_build_object('season_id',sid,'revived_after_wipe',st.revived_after_wipe,
    'revision',revision,'editable',reason is null,'blocking_reason',reason,'replayed',false);
  if op='set' then
    -- An unchanged-value command still has a stable receipt but leaves the stats,
    -- revision, audit effects and existing close/correction fingerprints untouched.
    insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
      values(oid,actor,sid,scope,k,encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
  end if;
  return result;
end $$;

revoke all on function public.api_participant_wipe_revivals(jsonb) from public,anon,authenticated;
grant execute on function public.api_participant_wipe_revivals(jsonb) to service_role;
comment on function public.api_participant_wipe_revivals(jsonb) is
  'Enabled JWT owner only through API. Absolute live wipe count, metadata revision, atomic audit/receipt. Never edits frozen history or observes save contents.';

-- The existing canonical death context is promoted to bigint below, without
-- changing purchased-revive semantics or consulting live state for corrections.

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
      'dead_count',(select count(*) from public.pokemon_observations o where o.save_file_id=p.current_save_file_id and o.source='box' and o.box_number=8)
        +greatest((select count(*) from public.redemptions e where e.season_id=sid and e.trainer_id=p.trainer_id and e.effect_code='revive' and e.status='applied'),
          (select count(*) from public.purchases u join public.shop_items i on i.id=u.shop_item_id where u.season_player_id=p.id and u.status='used' and i.code='revivir_pokemon'))
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

revoke all on function public.matchday_context_v034(text,jsonb) from public,anon,authenticated;
grant execute on function public.matchday_context_v034(text,jsonb) to service_role;

notify pgrst,'reload schema';
commit;
