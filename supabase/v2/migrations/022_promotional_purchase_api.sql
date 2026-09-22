-- Atomic promotional claims; no rewrites of migrations 001-021.
begin;

create unique index if not exists uq_purchases_promotion_trainer
  on public.purchases (promotion_id, trainer_id) where promotion_id is not null;

-- The consumed counter is now an economic mutation, not a browser-admin field.
do $$ declare writable_columns text; begin
  select string_agg(quote_ident(attname), ', ' order by attnum) into writable_columns
    from pg_attribute where attrelid='public.shop_promotions'::regclass
      and attnum > 0 and not attisdropped and attname <> 'stock_used';
  revoke insert, update on public.shop_promotions from authenticated;
  execute format('grant insert (%s), update (%s) on public.shop_promotions to authenticated', writable_columns, writable_columns);
end; $$;

-- Keep the exact 8D implementation, adding only cross-operation replay isolation.
-- Rename once instead of copying/editing its SQL body in this migration.
do $$ begin
  if to_regprocedure('public.api_create_normal_purchase_8d(uuid,uuid,uuid,text,boolean)') is null then
    alter function public.api_create_normal_purchase(uuid,uuid,uuid,text,boolean)
      rename to api_create_normal_purchase_8d;
  end if;
end; $$;
create or replace function public.api_create_normal_purchase(
  p_season_id uuid, p_trainer_id uuid, p_item_id uuid,
  p_idempotency_key text, p_confirm_base_price boolean default false
) returns jsonb language plpgsql security invoker set search_path = '' as $$
declare receipt jsonb;
begin
  receipt := public.api_create_normal_purchase_8d(p_season_id,p_trainer_id,p_item_id,p_idempotency_key,p_confirm_base_price);
  if exists (select 1 from public.purchases where id=(receipt->>'id')::uuid and promotion_id is not null) then
    raise sqlstate 'PT409' using message='idempotency_conflict';
  end if;
  return receipt;
end; $$;

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
  v_balance bigint;
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
    if v_season.status <> 'active' then raise sqlstate 'PT409' using message='season_not_active'; end if;
    select * into v_day from public.api_resolve_current_matchday(p_season_id);
    if public.api_is_store_banned(p_season_id,p_trainer_id,v_day.number) then
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
    select coalesce(sum(amount),0) into v_balance from public.coin_transactions
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

revoke all on function public.api_create_normal_purchase_8d(uuid,uuid,uuid,text,boolean) from public,anon,authenticated;
revoke all on function public.api_create_normal_purchase(uuid,uuid,uuid,text,boolean) from public,anon,authenticated;
revoke all on function public.api_create_promotional_purchase(uuid,uuid,uuid,text) from public,anon,authenticated;
grant execute on function public.api_create_normal_purchase_8d(uuid,uuid,uuid,text,boolean) to service_role;
grant execute on function public.api_create_normal_purchase(uuid,uuid,uuid,text,boolean) to service_role;
grant execute on function public.api_create_promotional_purchase(uuid,uuid,uuid,text) to service_role;
comment on function public.api_create_promotional_purchase(uuid,uuid,uuid,text) is
  'Atomic claim/stock/purchase/debit/event. Wallet before stock; one claim per trainer, no redemption or base fallback.';
commit;
