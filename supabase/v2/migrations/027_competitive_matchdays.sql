-- Phase 8H. Backend plans with the existing pure domain; SQL owns atomic commit.
begin;

alter table public.matchdays
  add column revision bigint not null default 0 check (revision>=0),
  add column results_revision bigint not null default 0 check (results_revision>=0);
alter table public.season_player_stats
  add column revived_after_wipe integer not null default 0 check (revived_after_wipe>=0);

create table public.matchday_snapshot_revisions (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null,
  matchday_id uuid not null,
  revision integer not null check (revision>0),
  snapshot jsonb not null check (jsonb_typeof(snapshot)='object'),
  reason text not null,
  created_by_trainer_id uuid not null references public.trainers(id),
  created_at timestamptz not null default clock_timestamp(),
  unique(matchday_id,revision),
  foreign key(matchday_id,season_id) references public.matchdays(id,season_id)
);
alter table public.matchday_snapshot_revisions enable row level security;
revoke all on public.matchday_snapshot_revisions from public,anon,authenticated;
grant all on public.matchday_snapshot_revisions to service_role;
create trigger snapshot_revision_immutable before update on public.matchday_snapshot_revisions
  for each row execute function public.admin_setup_receipt_immutable();

alter table public.coin_transactions
  add column reward_matchday_id uuid,
  add column reward_revision integer,
  add foreign key(reward_matchday_id,season_id) references public.matchdays(id,season_id),
  add foreign key(reward_matchday_id,reward_revision) references public.matchday_snapshot_revisions(matchday_id,revision),
  add constraint reward_ledger_source_chk check (
    (reward_matchday_id is null and reward_revision is null) or
    (reward_matchday_id is not null and reward_revision is not null and reward_revision>0 and transaction_type in ('matchday_reward','compensation'))),
  add constraint uq_matchday_reward_revision unique(reward_matchday_id,season_player_id,reward_revision);
alter table public.purchases
  add column origin_matchday_id uuid,
  add column origin_snapshot_revision integer,
  add foreign key(origin_matchday_id,season_id) references public.matchdays(id,season_id),
  add foreign key(origin_matchday_id,origin_snapshot_revision) references public.matchday_snapshot_revisions(matchday_id,revision),
  add constraint uq_matchday_free_reward unique(origin_matchday_id,origin_snapshot_revision,season_player_id),
  drop constraint purchase_acquisition_chk,
  add constraint purchase_acquisition_chk check (
    (acquisition_type='paid' and unit_price>0 and origin_redemption_id is null
      and origin_matchday_id is null and origin_snapshot_revision is null)
    or (acquisition_type='reward' and unit_price=0 and quantity=1 and promotion_id is null
      and idempotency_key is null and balance_after is null and base_price_confirmed is null
      and ((origin_redemption_id is not null and origin_matchday_id is null and origin_snapshot_revision is null)
        or (origin_redemption_id is null and origin_matchday_id is not null and origin_snapshot_revision is not null and origin_snapshot_revision>0))));
create unique index uq_matchday_movement_player on public.matchday_movements(matchday_id,season_player_id);

create or replace function public.check_purchase_acquisition() returns trigger
language plpgsql security invoker set search_path='' as $$
declare v_item public.shop_items; v_origin public.redemptions;
begin
  select * into v_item from public.shop_items where id=new.shop_item_id for share;
  if new.acquisition_type='paid' and v_item.acquisition_mode<>'purchasable' then
    raise sqlstate 'PT409' using message='item_unavailable'; end if;
  if new.acquisition_type='reward' and new.origin_matchday_id is not null then
    if v_item.code<>'robar_pokemon' or v_item.acquisition_mode<>'purchasable' or not exists (
      select 1 from public.matchday_snapshot_revisions r join public.season_players p
      on p.id=(r.snapshot->>'last_b_player_id')::uuid
      where r.matchday_id=new.origin_matchday_id and r.revision=new.origin_snapshot_revision
      and r.season_id=new.season_id and p.id=new.season_player_id and p.trainer_id=new.trainer_id
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

create function public.matchday_protect_snapshot() returns trigger
language plpgsql set search_path=pg_catalog,public as $$
begin
  if tg_op='UPDATE' and not exists(select 1 from public.matchday_snapshot_revisions where matchday_id=old.matchday_id) then
    return new; -- Historical pre-027 imports retain their existing contract.
  end if;
  if tg_op='UPDATE' and (new.matchday_id<>old.matchday_id or new.season_id<>old.season_id
     or new.config_version_id<>old.config_version_id or new.revision<>old.revision+1) then
    perform public.admin_setup_fail('stale_revision'); end if;
  if not exists(select 1 from public.matchday_snapshot_revisions r where r.matchday_id=new.matchday_id
      and r.revision=new.revision and r.season_id=new.season_id and r.snapshot=new.snapshot) then
    perform public.admin_setup_fail('invalid_results'); end if;
  return new;
end $$;
-- Apply the guard only to authoritative 8H snapshots, not older fixture imports.
create trigger authoritative_snapshot_guard before update on public.matchday_snapshots
  for each row execute function public.matchday_protect_snapshot();
revoke insert,update,delete on public.matchday_snapshots,public.matchday_movements,public.coin_transactions,
  public.matchday_snapshot_revisions from public,anon,authenticated;
do $$ declare t text; cols text; begin
  foreach t in array array['matchdays','matches','matchday_snapshots','matchday_movements',
    'coin_transactions','purchases','season_player_stats','matchday_snapshot_revisions'] loop
    select string_agg(quote_ident(attname),',') into cols from pg_attribute
      where attrelid=('public.'||t)::regclass and attnum>0 and not attisdropped;
    execute format('revoke insert (%s), update (%s) on public.%I from public,anon,authenticated',cols,cols,t);
  end loop;
end $$;

create function public.matchday_external_facts(sid uuid) returns text
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
  return encode(sha256(convert_to(result::text,'UTF8')),'hex');
end $$;

create function public.matchday_validate(sid uuid,did uuid,complete boolean) returns void
language plpgsql set search_path=pg_catalog,public as $$
declare d public.matchdays; c public.season_config_versions; total integer; expected integer; v_code text; n integer;
begin
  select * into d from public.matchdays where id=did and season_id=sid;
  if not found then perform public.admin_setup_fail('matchday_not_found',404); end if;
  select * into c from public.season_config_versions where season_id=sid and effective_from_matchday<=d.number
    order by effective_from_matchday desc limit 1;
  if c.id is distinct from d.season_config_version_id or c.division_sizes is null or d.number>c.total_matchdays then
    perform public.admin_setup_fail('config_mismatch'); end if;
  if exists(select 1 from public.season_players where season_id=sid and status<>'active') then
    perform public.admin_setup_fail('invalid_roster'); end if;
  select count(*) into total from public.season_players where season_id=sid;
  if total<>(c.division_sizes->>'A')::integer+(c.division_sizes->>'B')::integer then
    perform public.admin_setup_fail('invalid_roster'); end if;
  if exists(select 1 from public.season_players p where p.season_id=sid and
    (select count(*) from public.division_memberships m where m.season_player_id=p.id
      and m.effective_from_matchday_number<=d.number and coalesce(m.effective_to_matchday_number,d.number)>=d.number)<>1) then
    perform public.admin_setup_fail('invalid_roster'); end if;
  expected=0;
  foreach v_code in array array['A','B'] loop
    select count(*) into n from public.division_memberships m join public.divisions v on v.id=m.division_id
      where m.season_id=sid and v.code=v_code and m.effective_from_matchday_number<=d.number
      and coalesce(m.effective_to_matchday_number,d.number)>=d.number;
    if n<>(c.division_sizes->>v_code)::integer then perform public.admin_setup_fail('invalid_roster'); end if;
    expected=expected+n*(n-1)/2;
  end loop;
  if (select count(*) from public.matches where matchday_id=did)<>expected or exists (
    select 1 from public.matches x where x.matchday_id=did and (x.status not in ('scheduled','completed')
    or (x.winner_id is null)<>(x.status='scheduled') or not exists (
      select 1 from public.division_memberships a join public.division_memberships b on a.division_id=b.division_id
      where a.season_player_id=x.player_a_id and b.season_player_id=x.player_b_id and a.division_id=x.division_id
      and a.effective_from_matchday_number<=d.number and coalesce(a.effective_to_matchday_number,d.number)>=d.number
      and b.effective_from_matchday_number<=d.number and coalesce(b.effective_to_matchday_number,d.number)>=d.number))) then
    perform public.admin_setup_fail('invalid_results'); end if;
  if complete and exists(select 1 from public.matches where matchday_id=did and winner_id is null) then
    perform public.admin_setup_fail('results_incomplete'); end if;
end $$;

create function public.matchday_lock(op text,r jsonb) returns jsonb
language plpgsql set search_path=pg_catalog,public as $$
declare cached jsonb; sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid;
  d public.matchdays; s public.seasons; snap public.matchday_snapshots; nextday public.matchdays; change jsonb;
begin
  cached=public.admin_setup_begin('matchday_'||op,r);
  if cached is not null then return cached; end if;
  select * into s from public.seasons where id=sid;
  if s.status<>'active' then perform public.admin_setup_fail('season_not_active'); end if;
  select * into d from public.matchdays where id=did and season_id=sid for update;
  if not found then perform public.admin_setup_fail('matchday_not_found',404); end if;
  perform 1 from public.matches where matchday_id=did order by id for update;
  perform 1 from public.season_config_versions where season_id=sid order by id for share;
  if op in ('close','correct') then
    perform 1 from public.shop_items order by id for share;
    perform 1 from public.shop_promotions where season_id=sid order by id for update;
  end if;
  if op='correct' then
    select * into snap from public.matchday_snapshots where matchday_id=did;
    if d.status<>'closed' or snap.id is null or not (snap.snapshot ? 'external_facts')
      or exists(select 1 from public.matchday_snapshots x join public.matchdays md on md.id=x.matchday_id
        where x.season_id=sid and md.number>d.number)
      or snap.snapshot->>'external_facts' is distinct from public.matchday_external_facts(sid) then
      perform public.admin_setup_fail('correction_window_closed'); end if;
    if snap.revision<>(r->'body'->>'expected_snapshot_revision')::integer then
      perform public.admin_setup_fail('stale_revision'); end if;
    if jsonb_typeof(r->'body'->'results') is distinct from 'array' or jsonb_array_length(r->'body'->'results')=0
      or (select count(distinct value->>'match_id') from jsonb_array_elements(r->'body'->'results'))<>jsonb_array_length(r->'body'->'results') then
      perform public.admin_setup_fail('invalid_results'); end if;
    for change in select value from jsonb_array_elements(r->'body'->'results') loop
      if not exists(select 1 from public.matches m where m.id=(change->>'match_id')::uuid and m.matchday_id=did
        and (change->>'winner_season_player_id')::uuid in (m.player_a_id,m.player_b_id)) then
        perform public.admin_setup_fail('invalid_results'); end if;
    end loop;
    -- No cross-competition cascade: even a pre-existing cup may depend on standings.
    if exists(select 1 from public.cups where season_id=sid)
      or exists(select 1 from public.redemptions where season_id=sid and physical_effect_status='pending') then
      perform public.admin_setup_fail('correction_window_closed'); end if;
    if s.current_matchday_id<>did then
      select * into nextday from public.matchdays where id=s.current_matchday_id for update;
      if nextday.number<>d.number+1 or nextday.status<>'scheduled'
        or exists(select 1 from public.matches where matchday_id=nextday.id and winner_id is not null)
        or exists(select 1 from public.team_locks where matchday_id=nextday.id)
        or exists(select 1 from public.matchday_movements where matchday_id=nextday.id)
        or exists(select 1 from public.penalties where matchday_id=nextday.id) then
        perform public.admin_setup_fail('correction_window_closed'); end if;
    end if;
    if exists(select 1 from public.purchases p where p.origin_matchday_id=did and
      (p.status not in ('pending','cancelled') or exists(select 1 from public.redemptions where purchase_id=p.id))) then
      perform public.admin_setup_fail('correction_window_closed'); end if;
  else
    if s.current_matchday_id is distinct from did then perform public.admin_setup_fail('matchday_not_current'); end if;
    if op='open' then
      if d.status<>'scheduled' then perform public.admin_setup_fail('matchday_not_scheduled'); end if;
    elsif d.status<>'open' then perform public.admin_setup_fail(case when d.status='closed' then 'already_closed' else 'matchday_not_open' end); end if;
    if (r->'body' ? 'expected_revision' and (r->'body'->>'expected_revision')::bigint<>d.revision)
      or (r->'body' ? 'expected_results_revision' and (r->'body'->>'expected_results_revision')::bigint<>d.results_revision) then
      perform public.admin_setup_fail('stale_revision'); end if;
    perform public.matchday_validate(sid,did,op='close');
  end if;
  return null;
end $$;

create function public.matchday_context(op text,r jsonb) returns jsonb
language plpgsql set search_path=pg_catalog,public as $$
declare sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid;
  d public.matchdays; c public.season_config_versions; inputs jsonb; players jsonb; matches jsonb; result jsonb;
begin
  select * into d from public.matchdays where id=did;
  select * into c from public.season_config_versions where id=d.season_config_version_id;
  if (c.rules_json->>'last_b_gets_steal')::boolean and not exists (
    select 1 from public.shop_items where code='robar_pokemon' and acquisition_mode='purchasable'
  ) then perform public.admin_setup_fail('reward_item_unavailable'); end if;
  if op='correct' then
    select snapshot->'inputs' into inputs from public.matchday_snapshots where matchday_id=did;
  else
    if exists(select 1 from public.season_players p where p.season_id=sid and p.current_save_file_id is not null
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
      join public.division_memberships m on m.season_player_id=p.id and m.effective_from_matchday_number<=d.number
        and coalesce(m.effective_to_matchday_number,d.number)>=d.number
      join public.divisions v on v.id=m.division_id where p.season_id=sid;
    select coalesce(jsonb_agg(jsonb_build_object('id',x.id,'player_a_id',x.player_a_id,'player_b_id',x.player_b_id,
      'winner_id',x.winner_id,'division',v.code) order by x.id),'[]'::jsonb) into matches
      from public.matches x join public.divisions v on v.id=x.division_id where x.matchday_id=did;
    inputs=jsonb_build_object('season_id',sid,'day_id',did,'number',d.number,'results_revision',d.results_revision,
      'config',jsonb_build_object('id',c.id,'name',c.name,'effective_from_matchday',c.effective_from_matchday,
        'total_matchdays',c.total_matchdays,'division_sizes',c.division_sizes,'promotion_relegation_count',c.promotion_relegation_count,
        'scoring_json',c.scoring_json,'coin_rewards_json',c.coin_rewards_json,'rules_json',c.rules_json),
      'players',players,'matches',matches);
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

create function public.api_admin_matchday_context(p_request jsonb) returns jsonb
language plpgsql set search_path=pg_catalog,public as $$
declare op text=p_request->>'operation'; r jsonb=p_request->'request'; cached jsonb; ctx jsonb;
begin
  if op not in ('close','correct') then perform public.admin_setup_fail('invalid_request',422); end if;
  cached=public.matchday_lock(op,r);
  if cached is not null then return jsonb_build_object('receipt',cached); end if;
  ctx=public.matchday_context(op,r);
  return jsonb_build_object('context',ctx,'input_hash',encode(sha256(convert_to(ctx::text,'UTF8')),'hex'));
end $$;

create function public.matchday_results(did uuid,changes jsonb,correcting boolean default false) returns void
language plpgsql set search_path=pg_catalog,public as $$
declare x jsonb; m public.matches; wid uuid;
begin
  if jsonb_typeof(changes) is distinct from 'array' or jsonb_array_length(changes)=0
    or (select count(distinct value->>'match_id') from jsonb_array_elements(changes))<>jsonb_array_length(changes) then
    perform public.admin_setup_fail('invalid_results'); end if;
  for x in select value from jsonb_array_elements(changes) loop
    select * into m from public.matches where id=(x->>'match_id')::uuid and matchday_id=did;
    wid=(x->>'winner_season_player_id')::uuid;
    if not found or (correcting and wid is null) or (wid is not null and wid not in (m.player_a_id,m.player_b_id)) then
      perform public.admin_setup_fail('invalid_results'); end if;
    update public.matches set winner_id=wid,status=case when wid is null then 'scheduled' else 'completed' end where id=m.id;
  end loop;
end $$;

create function public.matchday_commit_close(op text,r jsonb,ctx jsonb,plan jsonb) returns void
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
    (select count(*) from public.season_players where season_id=sid)
    or (select count(distinct value->>'trainer_id') from jsonb_array_elements(plan->'standings'))<>jsonb_array_length(plan->'standings') then
    perform public.admin_setup_fail('invalid_results'); end if;
  for row in select value from jsonb_array_elements(plan->'standings') loop
    if not exists(select 1 from public.season_players where id=(row->>'trainer_id')::uuid and season_id=sid)
      or (row->>'coins_awarded')::integer is distinct from (cfg.coin_rewards_json->>(row->>'position'))::integer
      or (row->>'points_awarded')::integer is distinct from (cfg.scoring_json->>(row->>'position'))::integer then
      perform public.admin_setup_fail('invalid_results'); end if;
  end loop;
  giftplayer=(plan->>'last_b_player_id')::uuid;
  if (cfg.rules_json->>'last_b_gets_steal')::boolean then
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
      and effective_from_matchday_number<=d.number and coalesce(effective_to_matchday_number,d.number)>=d.number;
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

create function public.api_admin_matchday(p_request jsonb) returns jsonb
language plpgsql set search_path=pg_catalog,public as $$
declare op text=p_request->>'operation'; r jsonb=p_request->'request'; cached jsonb; ctx jsonb; result jsonb;
  sid uuid=(r->>'season_id')::uuid; did uuid=(r->>'resource_id')::uuid; d public.matchdays; oid uuid=gen_random_uuid(); eid uuid=gen_random_uuid();
begin
  if op='state' then
    perform public.admin_setup_principal((r->>'actor_trainer_id')::uuid);
    perform 1 from public.seasons where id=sid for share;
  else
    if op not in ('open','results','cancel','close','correct') then perform public.admin_setup_fail('invalid_request',422); end if;
    cached=public.matchday_lock(op,r); if cached is not null then return cached; end if;
  end if;
  select * into d from public.matchdays where id=did and season_id=sid;
  if not found then perform public.admin_setup_fail('matchday_not_found',404); end if;
  if op='open' then
    update public.matchdays set status='open',opened_at=clock_timestamp(),revision=revision+1,results_revision=results_revision+1 where id=did;
  elsif op='results' then
    perform public.matchday_results(did,r->'body'->'results');
    update public.matchdays set revision=revision+1,results_revision=results_revision+1 where id=did;
  elsif op='cancel' then
    if exists(select 1 from public.matches where matchday_id=did and winner_id is not null)
      or exists(select 1 from public.matchday_snapshots where matchday_id=did)
      or exists(select 1 from public.matchday_movements where matchday_id=did) then
      perform public.admin_setup_fail('dependent_data_exists'); end if;
    update public.matchdays set status='scheduled',opened_at=null,revision=revision+1,results_revision=results_revision+1 where id=did;
  elsif op in ('close','correct') then
    ctx=public.matchday_context(op,r);
    if p_request->>'input_hash' is distinct from encode(sha256(convert_to(ctx::text,'UTF8')),'hex') then
      perform public.admin_setup_fail('stale_inputs'); end if;
    perform public.matchday_commit_close(op,r,ctx,p_request->'plan');
  end if;
  select jsonb_build_object('season_id',sid,'matchday_id',did,'state',x.status,'revision',x.revision,'results_revision',x.results_revision,
    'snapshot_revision',coalesce((select revision from public.matchday_snapshots where matchday_id=did),0),
    'current_matchday_id',s.current_matchday_id) into result from public.matchdays x join public.seasons s on s.id=x.season_id where x.id=did;
  if op='state' then
    return result||jsonb_build_object('matches',(select coalesce(jsonb_agg(jsonb_build_object('id',id,'player_a_id',player_a_id,
      'player_b_id',player_b_id,'winner_id',winner_id) order by id),'[]'::jsonb) from public.matches where matchday_id=did));
  end if;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,visibility,dedupe_key,payload)
    values(eid,sid,'MATCHDAY_ADMIN_'||upper(op),(r->>'actor_trainer_id')::uuid,'admin','matchday-admin:'||oid::text,
      result||jsonb_build_object('reason',r->'body'->>'reason','operation_id',oid));
  result=result||jsonb_build_object('operation_id',oid,'event_id',eid,'replayed',false);
  insert into public.admin_operation_receipts(id,actor_trainer_id,season_id,operation_scope,idempotency_key,request_hash,response_json)
    values(oid,(r->>'actor_trainer_id')::uuid,sid,public.admin_setup_scope('matchday_'||op,r),r->>'idempotency_key',
      encode(sha256(convert_to(r::text,'UTF8')),'hex'),result);
  return result;
end $$;

do $$ declare f regprocedure; begin
  for f in select p.oid::regprocedure from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and (p.proname like 'matchday_%' or p.proname like 'api_admin_matchday%') loop
    execute format('revoke all on function %s from public,anon,authenticated',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
