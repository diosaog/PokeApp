-- Phase 10.5I: exact wallet, shop eligibility and observed progress rewards.
-- Forward only. No old season, ledger or frozen snapshot is recalculated.
begin;

-- The ledger stays the sole wallet truth. A string boundary preserves arbitrary
-- exact integer sums in PostgREST/JavaScript, including negative judicial balances.
drop view public.public_coin_balances;
create view public.public_coin_balances with(security_invoker=false,security_barrier=true) as
select season_id,trainer_id,coalesce(sum(amount::bigint),0)::text balance
from public.coin_transactions group by season_id,trainer_id;
revoke all on public.public_coin_balances from public,anon,authenticated;
grant select on public.public_coin_balances to authenticated,service_role;
alter table public.purchases alter column balance_after type numeric using balance_after::numeric;
alter table public.purchases add constraint purchase_balance_integer_chk
 check(balance_after is null or (balance_after=trunc(balance_after) and balance_after>=0));

-- Preserve the existing public column allowlist. Unannounced pending offers are
-- private until announcement or actual activation; no admin metadata is exposed.
create or replace view public.public_shop_promotions
with(security_invoker=false,security_barrier=true) as
select id,season_id,matchday_id,shop_item_id,promotion_type,
 case when status='ended' or ends_at<=now() then 'ended'
      when status='exhausted' or stock_used>=stock_total then 'exhausted'
      when activates_at>now() or (status='pending' and activates_at is null) then 'pending'
      else 'active' end status,
 base_price,effective_price,stock_total,stock_used,announced_at,activates_at,ends_at,
 exhausted_at,created_at,updated_at
from public.shop_promotions
where status<>'cancelled' and (status<>'pending' or announced_at<=now() or activates_at<=now());


create or replace function public.api_create_normal_purchase_8d(
  p_season_id uuid, p_trainer_id uuid, p_item_id uuid,
  p_idempotency_key text, p_confirm_base_price boolean default false
) returns jsonb
language plpgsql security invoker set search_path = '' as $$
declare
  v_trainer public.trainers%rowtype;
  v_season public.seasons%rowtype;
  v_player public.season_players%rowtype;
  v_day public.matchdays%rowtype;
  v_item public.shop_items%rowtype;
  v_promo public.shop_promotions%rowtype;
  v_purchase public.purchases%rowtype;
  v_balance numeric;
  v_confirmation boolean := false;
  v_ledger uuid := gen_random_uuid();
  v_event uuid := gen_random_uuid();
begin
  if p_idempotency_key is null or length(p_idempotency_key) not between 1 and 128
     or p_idempotency_key !~ '^[!-~]+$' or p_confirm_base_price is null then
    raise sqlstate 'PT409' using message = 'invalid_purchase_request';
  end if;
  select * into v_trainer from public.trainers where id = p_trainer_id for share;
  if not found or not v_trainer.globally_enabled then
    raise sqlstate 'PT403' using message = 'trainer_disabled';
  end if;
  select * into v_season from public.seasons where id = p_season_id for share;
  if not found then raise sqlstate 'PT404' using message = 'season_not_found'; end if;
  -- Every future mutation of this wallet must acquire this same lock first.
  select * into v_player from public.season_players
    where season_id = p_season_id and trainer_id = p_trainer_id for update;
  if not found or v_player.status <> 'active' then
    raise sqlstate 'PT403' using message = 'participant_inactive';
  end if;
  select * into v_purchase from public.purchases
    where season_id = p_season_id and trainer_id = p_trainer_id and idempotency_key = p_idempotency_key;
  if found then
    if v_purchase.shop_item_id <> p_item_id or
       (v_purchase.base_price_confirmed is not null and v_purchase.base_price_confirmed <> p_confirm_base_price) then
      raise sqlstate 'PT409' using message = 'idempotency_conflict';
    end if;
    -- A retry is a receipt lookup, not a new charge at today's price or balance.
  else
    if v_season.status not in ('active','finished','archived') then
      raise sqlstate 'PT409' using message='season_not_active'; end if;
    -- Only an active competitive window can supply a matchday or Store Ban.
    -- Completed League purchases retain a NULL matchday in their receipt.
    if v_season.status='active' then
      select * into v_day from public.api_resolve_current_matchday(p_season_id);
    end if;
    if v_day.id is not null and public.api_is_store_banned(p_season_id,p_trainer_id,v_day.number) then
      raise sqlstate 'PT403' using message = 'store_banned';
    end if;
    select * into v_item from public.shop_items where id = p_item_id for share;
    if not found then raise sqlstate 'PT404' using message = 'item_not_found'; end if;
    if not v_item.enabled or v_item.base_price <= 0 then
      raise sqlstate 'PT409' using message = 'item_unavailable';
    end if;
    for v_promo in select * from public.shop_promotions
      where season_id = p_season_id and shop_item_id = p_item_id
        and matchday_id is not distinct from v_day.id and status <> 'cancelled'
      order by id for share
    loop
      if exists (select 1 from public.purchases where promotion_id = v_promo.id
                 and season_id = p_season_id and trainer_id = p_trainer_id) then
        continue;
      end if;
      if v_promo.status in ('ended', 'exhausted') or v_promo.stock_used >= v_promo.stock_total
         or v_promo.ends_at <= statement_timestamp() then
        v_confirmation := true;
      elsif v_promo.activates_at > statement_timestamp()
         or (v_promo.status = 'pending' and v_promo.activates_at is null) then
        if v_item.category <> 'comodines' then
          raise sqlstate 'PT409' using message = 'promotion_pending';
        end if;
      else
        raise sqlstate 'PT409' using message = 'promotion_available';
      end if;
    end loop;
    if v_confirmation and not p_confirm_base_price then
      raise sqlstate 'PT409' using message = 'base_price_confirmation_required';
    end if;
    select coalesce(sum(amount::bigint), 0) into v_balance from public.coin_transactions
      where season_id = p_season_id and trainer_id = p_trainer_id;
    if v_balance < v_item.base_price then
      raise sqlstate 'PT409' using message = 'insufficient_funds';
    end if;
    insert into public.purchases (season_id, trainer_id, season_player_id, shop_item_id,
      quantity, unit_price, status, idempotency_key, balance_after, base_price_confirmed, metadata)
    values (p_season_id, p_trainer_id, v_player.id, p_item_id, 1, v_item.base_price, 'pending',
      p_idempotency_key, v_balance - v_item.base_price, case when v_confirmation then true else null end,
      jsonb_build_object('normal_purchase', jsonb_build_object('ledger_id', v_ledger, 'event_id', v_event,
        'matchday_id', v_day.id, 'matchday_number', v_day.number, 'item_name', v_item.name)))
    returning * into v_purchase;
    insert into public.coin_transactions (id, season_id, trainer_id, season_player_id, amount,
      transaction_type, reference_type, reference_id, created_by_trainer_id)
    values (v_ledger, p_season_id, p_trainer_id, v_player.id, -v_item.base_price,
      'purchase', 'purchase', v_purchase.id, p_trainer_id);
    insert into public.activity_events (id, season_id, type, actor_trainer_id, trainer_id,
      visibility, dedupe_key, context, payload)
    values (v_event, p_season_id, 'PURCHASE_COMPLETED', p_trainer_id, p_trainer_id, 'public',
      'purchase_completed:' || v_purchase.id::text,
      jsonb_build_object('matchday_number', v_day.number, 'matchday_id', v_day.id, 'base_price_confirmed', v_confirmation),
      jsonb_build_object('item', v_item.name, 'price', v_item.base_price, 'purchase_id', v_purchase.id,
        'quantity', 1, 'base_price', v_item.base_price, 'promotion_id', null, 'promotion_kind', ''));
  end if;
  return jsonb_build_object('id', v_purchase.id, 'season_id', v_purchase.season_id,
    'trainer_id', v_purchase.trainer_id, 'season_player_id', v_purchase.season_player_id,
    'item_id', v_purchase.shop_item_id, 'quantity', v_purchase.quantity,
    'unit_price', v_purchase.unit_price, 'total_price', v_purchase.total_price,
    'status', 'pending', 'purchased_at', v_purchase.purchased_at, 'balance_after', v_purchase.balance_after,
    'ledger_id', v_purchase.metadata #>> '{normal_purchase,ledger_id}',
    'event_id', v_purchase.metadata #>> '{normal_purchase,event_id}',
    'matchday_id', v_purchase.metadata #>> '{normal_purchase,matchday_id}',
    'matchday_number', (v_purchase.metadata #>> '{normal_purchase,matchday_number}')::integer);
end;
$$;

create or replace function public.api_create_promotional_purchase(
  p_season_id uuid, p_trainer_id uuid, p_promotion_id uuid, p_idempotency_key text
) returns jsonb language plpgsql security invoker set search_path = '' as $$
declare
  v_trainer public.trainers%rowtype;
  v_season public.seasons%rowtype;
  v_player public.season_players%rowtype;
  v_day public.matchdays%rowtype;
  v_item public.shop_items%rowtype;
  v_promo public.shop_promotions%rowtype;
  v_purchase public.purchases%rowtype;
  v_balance numeric;
  v_now timestamptz;
  v_ledger uuid := gen_random_uuid();
  v_event uuid := gen_random_uuid();
  v_history jsonb;
begin
  if p_idempotency_key is null or length(p_idempotency_key) not between 1 and 128
     or p_idempotency_key !~ '^[!-~]+$' or p_promotion_id is null then
    raise sqlstate 'PT409' using message='invalid_purchase_request';
  end if;
  select * into v_trainer from public.trainers where id=p_trainer_id for share;
  if not found or not v_trainer.globally_enabled then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
  select * into v_season from public.seasons where id=p_season_id for share;
  if not found then raise sqlstate 'PT404' using message='season_not_found'; end if;
  -- Same order as 8D: trainer/season -> wallet -> day -> item -> promotion.
  select * into v_player from public.season_players where season_id=p_season_id and trainer_id=p_trainer_id for update;
  if not found or v_player.status <> 'active' then raise sqlstate 'PT403' using message='participant_inactive'; end if;
  select * into v_purchase from public.purchases
    where season_id=p_season_id and trainer_id=p_trainer_id and idempotency_key=p_idempotency_key;
  if found then
    if v_purchase.promotion_id is distinct from p_promotion_id then
      raise sqlstate 'PT409' using message='idempotency_conflict';
    end if;
  else
    if v_season.status not in ('active','finished','archived') then
      raise sqlstate 'PT409' using message='season_not_active'; end if;
    -- Only an active competitive window can supply a matchday or Store Ban.
    -- Completed League purchases retain a NULL matchday in their receipt.
    if v_season.status='active' then
      select * into v_day from public.api_resolve_current_matchday(p_season_id);
    end if;
    if v_day.id is not null and public.api_is_store_banned(p_season_id,p_trainer_id,v_day.number) then
      raise sqlstate 'PT403' using message='store_banned';
    end if;
    -- Unlocked lookup discovers the item; all promotion facts are re-read under lock.
    select * into v_promo from public.shop_promotions where id=p_promotion_id and season_id=p_season_id;
    if not found then raise sqlstate 'PT404' using message='promotion_not_found'; end if;
    select * into v_item from public.shop_items where id=v_promo.shop_item_id for share;
    if not found or not v_item.enabled or v_item.base_price <= 0 then
      raise sqlstate 'PT409' using message='item_unavailable';
    end if;
    select * into v_promo from public.shop_promotions where id=p_promotion_id and season_id=p_season_id for update;
    if not found then raise sqlstate 'PT404' using message='promotion_not_found'; end if;
    if v_promo.shop_item_id <> v_item.id then raise sqlstate 'PT409' using message='promotion_changed'; end if;
    if v_promo.matchday_id is distinct from v_day.id then raise sqlstate 'PT409' using message='promotion_not_current'; end if;
    if exists (select 1 from public.purchases where promotion_id=p_promotion_id and trainer_id=p_trainer_id) then
      raise sqlstate 'PT409' using message='promotion_already_claimed';
    end if;
    -- Time is sampled after waiting for stock, not at request/transaction start.
    v_now := clock_timestamp();
    if v_promo.status in ('ended','cancelled') or v_promo.ends_at <= v_now then
      raise sqlstate 'PT409' using message='promotion_expired';
    end if;
    if v_promo.status='exhausted' or v_promo.stock_used >= v_promo.stock_total then
      raise sqlstate 'PT409' using message='promotion_exhausted';
    end if;
    if v_promo.activates_at > v_now or (v_promo.status='pending' and v_promo.activates_at is null) then
      raise sqlstate 'PT409' using message='promotion_pending';
    end if;
    if v_promo.effective_price <= 0 or v_promo.effective_price > v_promo.base_price then
      raise sqlstate 'PT409' using message='promotion_price_invalid';
    end if;
    select coalesce(sum(amount::bigint),0) into v_balance from public.coin_transactions
      where season_id=p_season_id and trainer_id=p_trainer_id;
    if v_balance < v_promo.effective_price then raise sqlstate 'PT409' using message='insufficient_funds'; end if;
    update public.shop_promotions set stock_used=stock_used+1,
      status=case when stock_used+1=stock_total then 'exhausted' else 'active' end,
      exhausted_at=case when stock_used+1=stock_total then v_now else exhausted_at end
      where id=p_promotion_id returning * into v_promo;
    v_history := jsonb_build_object('ledger_id',v_ledger,'event_id',v_event,'matchday_id',v_day.id,
      'matchday_number',v_day.number,'item_name',v_item.name,'base_price',v_promo.base_price,
      'promotion_kind',v_promo.promotion_type,'remaining_stock',v_promo.stock_total-v_promo.stock_used);
    insert into public.purchases(season_id,trainer_id,season_player_id,shop_item_id,promotion_id,
      quantity,unit_price,status,idempotency_key,balance_after,metadata)
    values(p_season_id,p_trainer_id,v_player.id,v_item.id,p_promotion_id,1,v_promo.effective_price,'pending',
      p_idempotency_key,v_balance-v_promo.effective_price,jsonb_build_object('promotional_purchase',v_history))
    returning * into v_purchase;
    insert into public.coin_transactions(id,season_id,trainer_id,season_player_id,amount,transaction_type,reference_type,reference_id,created_by_trainer_id)
    values(v_ledger,p_season_id,p_trainer_id,v_player.id,-v_promo.effective_price,'purchase','purchase',v_purchase.id,p_trainer_id);
    insert into public.activity_events(id,season_id,type,actor_trainer_id,trainer_id,visibility,dedupe_key,context,payload)
    values(v_event,p_season_id,'PURCHASE_COMPLETED',p_trainer_id,p_trainer_id,'public','purchase_completed:'||v_purchase.id::text,
      jsonb_build_object('matchday_id',v_day.id,'matchday_number',v_day.number),
      jsonb_build_object('purchase_id',v_purchase.id,'item',v_item.name,'quantity',1,'price',v_promo.effective_price,
        'base_price',v_promo.base_price,'promotion_id',p_promotion_id,'promotion_kind',v_promo.promotion_type));
  end if;
  v_history := v_purchase.metadata->'promotional_purchase';
  return jsonb_build_object('id',v_purchase.id,'season_id',v_purchase.season_id,'trainer_id',v_purchase.trainer_id,
    'season_player_id',v_purchase.season_player_id,'item_id',v_purchase.shop_item_id,'quantity',v_purchase.quantity,
    'unit_price',v_purchase.unit_price,'total_price',v_purchase.total_price,'status','pending',
    'purchased_at',v_purchase.purchased_at,'balance_after',v_purchase.balance_after,'promotion_id',v_purchase.promotion_id)
    || (v_history - 'item_name');
end; $$;

create or replace function public.admin_setup_validate_config(sid uuid,b jsonb) returns void
language plpgsql set search_path = pg_catalog, public as $$
declare n integer; a integer; z integer; effective integer; total integer; k text; rewards jsonb; v jsonb;
begin
  select count(*) into n from public.season_players where season_id=sid;
  if n=0 or exists(select 1 from public.season_players where season_id=sid and status<>'active') then
    perform public.admin_setup_fail('invalid_roster');
  end if;
  if jsonb_typeof(b->'division_sizes') is distinct from 'object'
     or not (b->'division_sizes' ?& array['A','B']) or (b->'division_sizes')-'A'-'B'<>'{}'::jsonb then
    perform public.admin_setup_fail('invalid_config');
  end if;
  a=(b->'division_sizes'->>'A')::integer; z=(b->'division_sizes'->>'B')::integer;
  effective=(b->>'effective_from_matchday')::integer; total=(b->>'total_matchdays')::integer;
  if a<=0 or z<=0 or a+z<>n or (b->>'movement_count')::integer not between 0 and least(a,z)
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

revoke all on function public.api_create_normal_purchase_8d(uuid,uuid,uuid,text,boolean) from public,anon,authenticated;
grant execute on function public.api_create_normal_purchase_8d(uuid,uuid,uuid,text,boolean) to service_role;
revoke all on function public.api_create_promotional_purchase(uuid,uuid,uuid,text) from public,anon,authenticated;
grant execute on function public.api_create_promotional_purchase(uuid,uuid,uuid,text) to service_role;
revoke all on function public.admin_setup_validate_config(uuid,jsonb) from public,anon,authenticated;
grant execute on function public.admin_setup_validate_config(uuid,jsonb) to service_role;


-- Both initial readiness and economic rewards consume the same validated facts.
create function public.observed_save_source_valid(saved public.save_files,parsed public.parsed_saves,tid uuid)
returns boolean language plpgsql immutable security invoker set search_path=pg_catalog,public as $$
declare valid boolean; envelope jsonb=parsed.payload->'observed_progress';
begin
    valid=saved.id is not null and saved.deleted_at is null and saved.parser_status='parsed'
      and parsed.id is not null and parsed.status='parsed' and parsed.schema_version=1
      and saved.parser_version in ('pokeapp-reader/2;pkhex/24.11.11','pokeapp-reader/3;pkhex/24.11.11')
      and parsed.parser_version=saved.parser_version
      and (not(parsed.payload ? 'save_record_id') or parsed.payload->>'save_record_id'=saved.id::text)
      and (not(parsed.payload ? 'trainer_id') or parsed.payload->>'trainer_id'=tid::text)
      and (not(parsed.payload ? 'source_hash') or parsed.payload->>'source_hash'=saved.sha256)
      and envelope->'schema_version'='1'::jsonb and envelope->>'source_hash'=saved.sha256;
  return coalesce(valid,false);
end $$;
create function public.observed_save_progress(saved public.save_files,parsed public.parsed_saves,tid uuid)
returns jsonb language plpgsql immutable security invoker set search_path=pg_catalog,public as $$
declare envelope jsonb=parsed.payload->'observed_progress'; progress jsonb=envelope->'progress';
  valid boolean; source_valid boolean=public.observed_save_source_valid(saved,parsed,tid);
  primary_region text; expected_regions jsonb; regions jsonb; flags jsonb; box jsonb;
begin
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

  if not coalesce(valid,false) then return null; end if;
  if progress ? 'champion_defeated' and jsonb_typeof(progress->'champion_defeated') not in ('null','boolean') then
    return null; end if;
  return progress||jsonb_build_object('champion_defeated',case
    when saved.parser_version='pokeapp-reader/3;pkhex/24.11.11' then progress->'champion_defeated' end);
end $$;

create table public.progress_reward_claims (
  id uuid primary key default gen_random_uuid(),
  season_id uuid not null,
  trainer_id uuid not null,
  season_player_id uuid not null,
  reward_key text not null check(reward_key='game_completion' or reward_key ~ '^badge:([1-9]|1[0-6])$'),
  amount integer not null check(amount>=0),
  config_version_id uuid not null,
  identity_revision_id uuid not null,
  source_hash text not null check(source_hash ~ '^[a-f0-9]{64}$'),
  observed_progress jsonb not null check(jsonb_typeof(observed_progress)='object'),
  coin_transaction_id uuid unique references public.coin_transactions(id) on delete restrict,
  created_at timestamptz not null default now(),
  unique(season_id,trainer_id,reward_key),
  foreign key(season_player_id,season_id,trainer_id) references public.season_players(id,season_id,trainer_id),
  foreign key(config_version_id,season_id) references public.season_config_versions(id,season_id),
  foreign key(identity_revision_id,season_id,trainer_id) references public.pokemon_identity_revisions(id,season_id,trainer_id),
  check((amount=0)=(coin_transaction_id is null))
);
create index progress_reward_claims_config_idx on public.progress_reward_claims(config_version_id);
create index progress_reward_claims_revision_idx on public.progress_reward_claims(identity_revision_id);
create index progress_reward_claims_player_idx on public.progress_reward_claims(season_player_id);
alter table public.progress_reward_claims enable row level security;
revoke all on public.progress_reward_claims from public,anon,authenticated,service_role;
grant select,insert,delete on public.progress_reward_claims to service_role;
-- DELETE exists only for disposable fixture cleanup; no application deletion route.
create function public.progress_reward_immutable() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin raise exception 'progress_reward_immutable'; end $$;
create trigger progress_reward_immutable before update on public.progress_reward_claims
for each row execute function public.progress_reward_immutable();
alter table public.coin_transactions drop constraint coin_transactions_type_chk;
alter table public.coin_transactions add constraint coin_transactions_type_chk check(transaction_type in
 ('matchday_reward','purchase','penalty','admin_adjustment','compensation','badge_reward','game_completion_reward'));

create or replace function public.admin_setup_config_used(cid uuid) returns boolean
language sql stable security invoker set search_path=pg_catalog,public as $$
 select exists(select 1 from public.matchdays where season_config_version_id=cid)
   or exists(select 1 from public.matchday_snapshots where config_version_id=cid)
   or exists(select 1 from public.initial_division_snapshots where config_version_id=cid)
   or exists(select 1 from public.progress_reward_claims where config_version_id=cid)
$$;

-- Service-only settlement at trusted observation acceptance, never a participant
-- claim or a GET side effect. The participant row is the existing wallet mutex.
create function public.settle_observed_progress_rewards(sid uuid,tid uuid) returns integer
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare p public.season_players; saved public.save_files; parsed public.parsed_saves;
  ident public.pokemon_identity_revisions; c public.season_config_versions; progress jsonb;
  badge_count integer; reward record; claim uuid; ledger uuid; paid integer=0; day_number integer;
begin
  select * into p from public.season_players where season_id=sid and trainer_id=tid for update;
  if not found or p.status<>'active' or not exists(select 1 from public.trainers where id=tid and globally_enabled)
    or not exists(select 1 from public.seasons where id=sid and status in ('active','finished','archived')) then return 0; end if;
  select * into ident from public.pokemon_identity_revisions where season_id=sid and trainer_id=tid
    order by revision_number desc limit 1;
  if ident.id is null or ident.save_file_id is distinct from p.current_save_file_id then return 0; end if;
  select * into saved from public.save_files where id=ident.save_file_id and season_id=sid and trainer_id=tid for share;
  select * into parsed from public.parsed_saves where id=ident.parsed_save_id and save_file_id=saved.id for share;
  progress=public.observed_save_progress(saved,parsed,tid);
  if progress is null then return 0; end if;
  -- A pre-J1 save uses config 1. Later saves use the current/latest real League
  -- day, including after archive; a future config never takes effect early.
  select coalesce((select number from public.matchdays where id=s.current_matchday_id and season_id=sid),
    (select max(number) from public.matchdays where season_id=sid),1) into day_number
    from public.seasons s where id=sid;
  select * into c from public.season_config_versions where season_id=sid and effective_from_matchday<=day_number
    order by effective_from_matchday desc limit 1;
  if c.id is null then return 0; end if;
  select count(*) into badge_count from jsonb_array_elements(progress->'regions') r,
    lateral jsonb_array_elements(r->'badge_flags') f where f='true'::jsonb;
  -- Ordinal high-water marks: a regression or a different observed region cannot
  -- pay the same N badges twice. HGSS can prove up to sixteen distinct badges.
  for reward in
    select 'badge:'||n key,coalesce((c.rules_json->>'badge_reward_coins')::integer,4) amount,'badge_reward' kind
      from generate_series(1,badge_count) n
    union all
    select 'game_completion',coalesce((c.rules_json->>'game_completion_reward_coins')::integer,12),'game_completion_reward'
      where progress->'champion_defeated'='true'::jsonb
  loop
    if exists(select 1 from public.progress_reward_claims where season_id=sid and trainer_id=tid and reward_key=reward.key) then continue; end if;
    claim=gen_random_uuid(); ledger=null;
    if reward.amount>0 then
      ledger=gen_random_uuid();
      insert into public.coin_transactions(id,season_id,trainer_id,season_player_id,amount,transaction_type,reference_type,reference_id,metadata)
        values(ledger,sid,tid,p.id,reward.amount,reward.kind,'progress_reward',claim,
          jsonb_build_object('reward_key',reward.key,'config_version_id',c.id,'identity_revision_id',ident.id,
            'save_file_id',saved.id,'source_hash',saved.sha256));
    end if;
    insert into public.progress_reward_claims(id,season_id,trainer_id,season_player_id,reward_key,amount,
      config_version_id,identity_revision_id,source_hash,observed_progress,coin_transaction_id)
      values(claim,sid,tid,p.id,reward.key,reward.amount,c.id,ident.id,saved.sha256,progress,ledger);
    paid=paid+1;
  end loop;
  return paid;
end $$;

-- Identity reconciliation and pointer promotion can occur in either order.
-- Both hooks share the existing participant lock and settle only the latest
-- owned revision. No pointer is fabricated or promoted by this migration.
alter function public.commit_pokemon_identity(jsonb) rename to commit_pokemon_identity_v038;
create function public.commit_pokemon_identity(p_request jsonb) returns jsonb
language plpgsql security invoker set search_path=pg_catalog,public as $$
declare result jsonb;
begin
 result=public.commit_pokemon_identity_v038(p_request);
 perform public.settle_observed_progress_rewards((p_request->>'season_id')::uuid,(p_request->>'trainer_id')::uuid);
 return result;
end $$;
create function public.reward_current_save_observation() returns trigger
language plpgsql security invoker set search_path=pg_catalog,public as $$
begin
 perform public.settle_observed_progress_rewards(new.season_id,new.trainer_id);
 return new;
end $$;
create trigger reward_current_save_observation after update of current_save_file_id on public.season_players
for each row when(old.current_save_file_id is distinct from new.current_save_file_id)
execute function public.reward_current_save_observation();

-- A revive preserves its historical death. Until that same entity has been
-- observed alive afterwards, its still-visible Box-8 occurrence is the SAME
-- death, not an extra penalty. Missing/ambiguous evidence cannot prove revival.
create function public.purchased_revive_overlap(sid uuid,tid uuid,save_id uuid) returns bigint
language plpgsql stable security invoker set search_path=pg_catalog,public as $$
declare historical bigint; mapped bigint;
begin
 select count(*) into mapped from public.redemptions r where r.season_id=sid and r.trainer_id=tid
   and r.effect_code='revive' and r.status='applied' and r.target_pokemon_entity_id is not null and r.identity_revision_id is not null;
 select greatest((select count(*) from public.redemptions r where r.season_id=sid and r.trainer_id=tid
     and r.effect_code='revive' and r.status='applied'),
   (select count(*) from public.purchases u join public.shop_items i on i.id=u.shop_item_id
     where u.season_id=sid and u.trainer_id=tid and u.status='used' and i.code='revivir_pokemon')) into historical;
 if exists(select 1 from public.pokemon_observations o where o.save_file_id=save_id and o.source='box' and o.box_number=8)
   and (historical>mapped or exists(select 1 from public.pokemon_observations o
     join public.redemptions r on r.target_pokemon_entity_id=any(o.candidate_entity_ids)
     where o.save_file_id=save_id and o.source='box' and o.box_number=8 and o.pokemon_entity_id is null
       and r.season_id=sid and r.trainer_id=tid and r.effect_code='revive' and r.status='applied')) then
   -- An unlinked legacy counter/ambiguous identity cannot prove which visible
   -- death overlaps. Propagate UNKNOWN rather than invent an additional death.
   return null;
 end if;
 return (select count(*) from public.pokemon_observations current
 join public.pokemon_identity_revisions head on head.id=current.revision_id
 where current.season_id=sid and current.trainer_id=tid and current.save_file_id=save_id
   and current.source='box' and current.box_number=8 and current.pokemon_entity_id is not null
   and exists(select 1 from public.redemptions r join public.pokemon_identity_revisions used on used.id=r.identity_revision_id
     where r.season_id=sid and r.trainer_id=tid and r.effect_code='revive' and r.status='applied'
       and r.target_pokemon_entity_id=current.pokemon_entity_id and used.revision_number<=head.revision_number
       and not exists(select 1 from public.pokemon_observations alive
         join public.pokemon_identity_revisions later on later.id=alive.revision_id
         where alive.season_id=sid and alive.trainer_id=tid and alive.pokemon_entity_id=current.pokemon_entity_id
           and later.revision_number>used.revision_number and later.revision_number<=head.revision_number
           and (alive.source='party' or (alive.source='box' and alive.box_number<>8)))));
end $$;

create or replace function public.initial_assignment_observations(sid uuid) returns jsonb
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
      select count(*)+revive_count-public.purchased_revive_overlap(sid,p.trainer_id,saved.id)+2::bigint*wipe_count into deaths from public.pokemon_observations
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
  if v_effect='steal' and v_observation.source='box' and v_observation.box_number not between 1 and 7 then
    raise sqlstate 'PT409' using message='steal_target_ineligible'; end if;
  if v_observation.source='box' and v_observation.box_number not between 1 and 8 then
    raise sqlstate 'PT409' using message='invalid_pokemon_target'; end if;
  if v_effect='revive' and not (v_observation.source='box' and v_observation.box_number=8) then
    raise sqlstate 'PT409' using message='pokemon_not_revivable'; end if;
  if v_effect='revive' and exists(select 1 from public.redemptions r
    join public.pokemon_identity_revisions used on used.id=r.identity_revision_id
    where r.season_id=p_season_id and r.trainer_id=p_trainer_id and r.effect_code='revive' and r.status='applied'
      and r.target_pokemon_entity_id=v_entity.id and not exists(
        select 1 from public.pokemon_observations alive join public.pokemon_identity_revisions later on later.id=alive.revision_id
        where alive.season_id=p_season_id and alive.trainer_id=p_trainer_id and alive.pokemon_entity_id=v_entity.id
          and later.revision_number>used.revision_number and later.revision_number<=v_head.revision_number
          and (alive.source='party' or (alive.source='box' and alive.box_number<>8)))) then
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
revoke all on function public.observed_save_source_valid(public.save_files,public.parsed_saves,uuid) from public,anon,authenticated;
grant execute on function public.observed_save_source_valid(public.save_files,public.parsed_saves,uuid) to service_role;
revoke all on function public.observed_save_progress(public.save_files,public.parsed_saves,uuid) from public,anon,authenticated;
grant execute on function public.observed_save_progress(public.save_files,public.parsed_saves,uuid) to service_role;
revoke all on function public.progress_reward_immutable() from public,anon,authenticated;
grant execute on function public.progress_reward_immutable() to service_role;
revoke all on function public.settle_observed_progress_rewards(uuid,uuid) from public,anon,authenticated;
grant execute on function public.settle_observed_progress_rewards(uuid,uuid) to service_role;
revoke all on function public.commit_pokemon_identity(jsonb) from public,anon,authenticated;
grant execute on function public.commit_pokemon_identity(jsonb) to service_role;
revoke all on function public.commit_pokemon_identity_v038(jsonb) from public,anon,authenticated;
grant execute on function public.commit_pokemon_identity_v038(jsonb) to service_role;
revoke all on function public.reward_current_save_observation() from public,anon,authenticated;
grant execute on function public.reward_current_save_observation() to service_role;
revoke all on function public.purchased_revive_overlap(uuid,uuid,uuid) from public,anon,authenticated;
grant execute on function public.purchased_revive_overlap(uuid,uuid,uuid) to service_role;
revoke all on function public.initial_assignment_observations(uuid) from public,anon,authenticated;
grant execute on function public.initial_assignment_observations(uuid) to service_role;
revoke all on function public.matchday_context_v034(text,jsonb) from public,anon,authenticated;
grant execute on function public.matchday_context_v034(text,jsonb) to service_role;
revoke all on function public.admin_setup_config_used(uuid) from public,anon,authenticated;
grant execute on function public.admin_setup_config_used(uuid) to service_role;
revoke all on function public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid) from public,anon,authenticated;
grant execute on function public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid) to service_role;

-- Narrow owner-only eligibility projection; no save or flag payload reaches the
-- browser. Redemption rechecks identity, ownership, revision and flags atomically.
create function public.inventory_shield_targets(sid uuid,tid uuid) returns jsonb
language sql stable security invoker set search_path=pg_catalog,public as $$
 select coalesce(jsonb_agg(o.pokemon_entity_id order by o.pokemon_entity_id),'[]'::jsonb)
 from public.season_players p
 join public.trainers t on t.id=p.trainer_id and t.globally_enabled
 join public.pokemon_identity_revisions r on r.season_id=p.season_id and r.trainer_id=p.trainer_id
   and r.save_file_id=p.current_save_file_id
 join public.pokemon_observations o on o.revision_id=r.id and o.outcome in ('NEW','MATCHED')
 join public.pokemon_entities e on e.id=o.pokemon_entity_id and e.owner_trainer_id=tid and e.identity_status='unambiguous'
 where p.season_id=sid and p.trainer_id=tid and p.status='active'
   and (o.source='party' or (o.source='box' and o.box_number between 1 and 8))
   and not exists(select 1 from public.pokemon_identity_revisions newer where newer.season_id=sid
     and newer.trainer_id=tid and newer.revision_number>r.revision_number)
   and not exists(select 1 from public.pokemon_entity_flags f left join public.pokemon_flags legacy on legacy.id=f.legacy_flag_id
     where f.season_id=sid and f.pokemon_entity_id=e.id and f.flag_type='blindado' and coalesce(f.flag_value,legacy.flag_value,false))
$$;
revoke all on function public.inventory_shield_targets(uuid,uuid) from public,anon,authenticated;
grant execute on function public.inventory_shield_targets(uuid,uuid) to service_role;

notify pgrst,'reload schema';
commit;
