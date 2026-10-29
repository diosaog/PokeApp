-- 071: the Shop is open in the preseason (real test, 2026-10-29).
-- Every purchase in an active season resolved the current matchday, which
-- raises current_matchday_required while the season is active but J1 is not
-- prepared yet (initial assignment pending). Coins already count then (medals
-- pay since 069), so every item was refused with a 409 the web showed as
-- "data changed". The purchase now runs with a NULL matchday in that window,
-- exactly like a purchase after the League finished; balance, price
-- confirmation, promotions, idempotency, the ledger and the audit event are
-- unchanged. A prepared matchday still supplies Store Ban and promotions.
begin;

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
    -- 071: the preseason (active, J1 not prepared yet) already earns coins, so
    -- the shop is open; its receipt keeps a NULL matchday like a finished
    -- League's. A prepared matchday still supplies Store Ban and promotions.
    if v_season.status='active' and v_season.current_matchday_id is not null then
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

revoke all on function public.api_create_normal_purchase_8d(uuid,uuid,uuid,text,boolean) from public,anon,authenticated;
grant execute on function public.api_create_normal_purchase_8d(uuid,uuid,uuid,text,boolean) to service_role;
notify pgrst,'reload schema';
commit;
