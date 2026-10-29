-- 072: in-game Shop objects reach the bag through PokeApp Launcher, once.
-- Owner decision 2026-10-29. Until now only the four Pokémon comodines had a
-- use; every other paid object stayed «Sin canje disponible» forever.
--
-- item_deliveries is the single-use record of a paid purchase:
--   bag:        RESERVED (the Launcher is about to write the object, the
--               purchase stays pending) -> DELIVERED (written and natively
--               re-read on the trainer's PC; the purchase becomes used) or
--               RELEASED (nothing was written; the purchase can be used again);
--   permission: USED (Captura Extra: the use is recorded, nothing to write).
-- One live row per purchase (unique while not RELEASED). The API resolves the
-- object, its game item id and the league game from the server-owned contract
-- (app/domain/shop_item_uses.py) before calling these functions.
--
-- api_admin_refund_purchase: audited refund of a pending paid purchase that
-- was never used (e.g. an object that does not exist in the trainer's game):
-- the purchase becomes refunded, a positive purchase_refund ledger row returns
-- exactly what was paid, the owner and the administration each get an event.
begin;

create table public.item_deliveries (
  id uuid primary key default gen_random_uuid(),
  purchase_id uuid not null references public.purchases(id),
  season_id uuid not null,
  trainer_id uuid not null,
  operation_id uuid not null unique,
  kind text not null check (kind in ('bag','permission')),
  item_code text check (item_code is null or item_code ~ '^[a-z0-9_]{1,40}$'),
  game_item_id integer check (game_item_id is null or game_item_id between 1 and 2000),
  game text check (game is null or game in ('X','Y','OR','AS','SN','MN','US','UM')),
  status text not null check (status in ('RESERVED','DELIVERED','RELEASED','USED')),
  source_sha256 text check (source_sha256 is null or source_sha256 ~ '^[a-f0-9]{64}$'),
  output_sha256 text check (output_sha256 is null or output_sha256 ~ '^[a-f0-9]{64}$'),
  reserved_at timestamptz not null default now(),
  finished_at timestamptz,
  foreign key (season_id,trainer_id) references public.season_players(season_id,trainer_id),
  constraint item_delivery_shape_chk check (
    (kind='bag' and item_code is not null and game_item_id is not null and game is not null
      and status in ('RESERVED','DELIVERED','RELEASED'))
    or (kind='permission' and item_code is null and game_item_id is null and game is null
      and status='USED')),
  constraint item_delivery_finished_chk check ((status='RESERVED')=(finished_at is null)),
  constraint item_delivery_proof_chk check (status<>'DELIVERED' or (source_sha256 is not null
    and output_sha256 is not null and source_sha256<>output_sha256))
);
create unique index item_delivery_live_idx on public.item_deliveries(purchase_id)
  where status<>'RELEASED';
create index item_delivery_trainer_idx on public.item_deliveries(season_id,trainer_id,reserved_at desc);
comment on table public.item_deliveries is
  'Backend-only single use of a paid in-game object: bag delivery by the trainer''s Launcher or a recorded permission.';
alter table public.item_deliveries enable row level security;
alter table public.item_deliveries force row level security;
revoke all on public.item_deliveries from public,anon,authenticated,service_role;
grant select,insert,update on public.item_deliveries to service_role;

alter table public.coin_transactions drop constraint coin_transactions_type_chk;
alter table public.coin_transactions add constraint coin_transactions_type_chk check(transaction_type in
 ('matchday_reward','purchase','penalty','admin_adjustment','compensation','badge_reward',
  'game_completion_reward','purchase_refund'));

create function public.item_delivery_receipt(d public.item_deliveries) returns jsonb
language sql stable security invoker set search_path='' as $$
  select jsonb_build_object('delivery_id',d.id,'purchase_id',d.purchase_id,'season_id',d.season_id,
    'trainer_id',d.trainer_id,'operation_id',d.operation_id,'kind',d.kind,'item_code',d.item_code,
    'game_item_id',d.game_item_id,'game',d.game,'status',d.status,'reserved_at',d.reserved_at,
    'finished_at',d.finished_at,
    'purchase_status',(select p.status from public.purchases p where p.id=d.purchase_id))
$$;

-- The common start of a trainer's own use: enabled trainer, active
-- participant, their own paid quantity-one purchase, locked.
create function public.item_use_purchase(p_season_id uuid, p_trainer_id uuid, p_purchase_id uuid)
returns public.purchases language plpgsql security invoker set search_path='' as $$
declare v_player public.season_players; v_purchase public.purchases;
begin
  perform 1 from public.trainers where id=p_trainer_id and globally_enabled for share;
  if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
  select * into v_player from public.season_players where season_id=p_season_id and trainer_id=p_trainer_id;
  if not found or v_player.status<>'active' then
    raise sqlstate 'PT403' using message='participant_inactive'; end if;
  select * into v_purchase from public.purchases where id=p_purchase_id
    and season_id=p_season_id and trainer_id=p_trainer_id for update;
  if not found then raise sqlstate 'PT404' using message='purchase_not_found'; end if;
  return v_purchase;
end $$;

create function public.api_reserve_item_delivery(
  p_season_id uuid, p_trainer_id uuid, p_purchase_id uuid, p_operation_id uuid,
  p_item_code text, p_game_item_id integer, p_game text
) returns jsonb language plpgsql security invoker set search_path='' as $$
declare v_purchase public.purchases; v_code text; v_row public.item_deliveries;
begin
  if p_operation_id is null or p_item_code is null or p_item_code !~ '^[a-z0-9_]{1,40}$'
    or p_game_item_id is null or p_game_item_id not between 1 and 2000
    or p_game is null or p_game not in ('X','Y','OR','AS','SN','MN','US','UM') then
    raise sqlstate 'PT422' using message='invalid_delivery_request'; end if;
  v_purchase := public.item_use_purchase(p_season_id,p_trainer_id,p_purchase_id);
  select * into v_row from public.item_deliveries where operation_id=p_operation_id;
  if found then
    if v_row.purchase_id<>p_purchase_id or v_row.kind<>'bag' or v_row.item_code<>p_item_code
      or v_row.game_item_id<>p_game_item_id or v_row.game<>p_game then
      raise sqlstate 'PT409' using message='idempotency_conflict'; end if;
    return public.item_delivery_receipt(v_row);
  end if;
  if exists(select 1 from public.item_deliveries where purchase_id=p_purchase_id and status<>'RELEASED') then
    raise sqlstate 'PT409' using message='delivery_in_progress'; end if;
  if v_purchase.status<>'pending' or v_purchase.quantity<>1 or v_purchase.acquisition_type<>'paid' then
    raise sqlstate 'PT409' using message='purchase_not_redeemable'; end if;
  select code into v_code from public.shop_items where id=v_purchase.shop_item_id for share;
  if v_code in ('blindar_pokemon','revivir_pokemon','robar_pokemon','robbery_shield_voucher',
    'captura_extra','menta_naturaleza') then
    raise sqlstate 'PT409' using message='delivery_not_supported'; end if;
  insert into public.item_deliveries(purchase_id,season_id,trainer_id,operation_id,kind,
    item_code,game_item_id,game,status)
  values(p_purchase_id,p_season_id,p_trainer_id,p_operation_id,'bag',p_item_code,p_game_item_id,
    p_game,'RESERVED')
  returning * into v_row;
  return public.item_delivery_receipt(v_row);
end $$;

create function public.api_complete_item_delivery(
  p_season_id uuid, p_trainer_id uuid, p_operation_id uuid,
  p_source_sha256 text, p_output_sha256 text
) returns jsonb language plpgsql security invoker set search_path='' as $$
declare v_row public.item_deliveries; v_purchase public.purchases; v_name text;
begin
  if p_operation_id is null or p_source_sha256 is null or p_source_sha256 !~ '^[a-f0-9]{64}$'
    or p_output_sha256 is null or p_output_sha256 !~ '^[a-f0-9]{64}$'
    or p_source_sha256=p_output_sha256 then
    raise sqlstate 'PT422' using message='invalid_delivery_request'; end if;
  select * into v_row from public.item_deliveries where operation_id=p_operation_id
    and season_id=p_season_id and trainer_id=p_trainer_id for update;
  if not found then raise sqlstate 'PT404' using message='delivery_not_found'; end if;
  if v_row.status='DELIVERED' then
    if v_row.source_sha256<>p_source_sha256 or v_row.output_sha256<>p_output_sha256 then
      raise sqlstate 'PT409' using message='idempotency_conflict'; end if;
    return public.item_delivery_receipt(v_row);
  end if;
  if v_row.status<>'RESERVED' then raise sqlstate 'PT409' using message='delivery_not_reserved'; end if;
  v_purchase := public.item_use_purchase(p_season_id,p_trainer_id,v_row.purchase_id);
  if v_purchase.status<>'pending' then raise sqlstate 'PT409' using message='purchase_not_redeemable'; end if;
  update public.item_deliveries set status='DELIVERED',source_sha256=p_source_sha256,
    output_sha256=p_output_sha256,finished_at=now() where id=v_row.id returning * into v_row;
  update public.purchases set status='used' where id=v_purchase.id;
  select name into v_name from public.shop_items where id=v_purchase.shop_item_id;
  insert into public.activity_events(season_id,type,actor_trainer_id,trainer_id,visibility,dedupe_key,payload)
  values(p_season_id,'ITEM_DELIVERED',p_trainer_id,p_trainer_id,'owner','item_delivered:'||v_row.id::text,
    jsonb_build_object('purchase_id',v_purchase.id,'item',v_name,'item_code',v_row.item_code,
      'game_item_id',v_row.game_item_id,'game',v_row.game,'operation_id',v_row.operation_id));
  return public.item_delivery_receipt(v_row);
end $$;

create function public.api_release_item_delivery(
  p_season_id uuid, p_trainer_id uuid, p_operation_id uuid
) returns jsonb language plpgsql security invoker set search_path='' as $$
declare v_row public.item_deliveries;
begin
  if p_operation_id is null then raise sqlstate 'PT422' using message='invalid_delivery_request'; end if;
  perform 1 from public.trainers where id=p_trainer_id and globally_enabled for share;
  if not found then raise sqlstate 'PT403' using message='trainer_disabled'; end if;
  select * into v_row from public.item_deliveries where operation_id=p_operation_id
    and season_id=p_season_id and trainer_id=p_trainer_id for update;
  if not found then raise sqlstate 'PT404' using message='delivery_not_found'; end if;
  if v_row.status='RELEASED' then return public.item_delivery_receipt(v_row); end if;
  if v_row.status<>'RESERVED' then raise sqlstate 'PT409' using message='delivery_already_completed'; end if;
  update public.item_deliveries set status='RELEASED',finished_at=now() where id=v_row.id
    returning * into v_row;
  return public.item_delivery_receipt(v_row);
end $$;

create function public.api_use_permission_item(
  p_season_id uuid, p_trainer_id uuid, p_purchase_id uuid, p_operation_id uuid
) returns jsonb language plpgsql security invoker set search_path='' as $$
declare v_purchase public.purchases; v_code text; v_name text; v_row public.item_deliveries;
begin
  if p_operation_id is null then raise sqlstate 'PT422' using message='invalid_delivery_request'; end if;
  v_purchase := public.item_use_purchase(p_season_id,p_trainer_id,p_purchase_id);
  select * into v_row from public.item_deliveries where operation_id=p_operation_id;
  if found then
    if v_row.purchase_id<>p_purchase_id or v_row.kind<>'permission' then
      raise sqlstate 'PT409' using message='idempotency_conflict'; end if;
    return public.item_delivery_receipt(v_row);
  end if;
  if exists(select 1 from public.item_deliveries where purchase_id=p_purchase_id and status<>'RELEASED') then
    raise sqlstate 'PT409' using message='delivery_in_progress'; end if;
  if v_purchase.status<>'pending' or v_purchase.quantity<>1 or v_purchase.acquisition_type<>'paid' then
    raise sqlstate 'PT409' using message='purchase_not_redeemable'; end if;
  select code,name into v_code,v_name from public.shop_items where id=v_purchase.shop_item_id for share;
  if v_code<>'captura_extra' then raise sqlstate 'PT409' using message='delivery_not_supported'; end if;
  insert into public.item_deliveries(purchase_id,season_id,trainer_id,operation_id,kind,status,finished_at)
  values(p_purchase_id,p_season_id,p_trainer_id,p_operation_id,'permission','USED',now())
  returning * into v_row;
  update public.purchases set status='used' where id=v_purchase.id;
  insert into public.activity_events(season_id,type,actor_trainer_id,trainer_id,visibility,dedupe_key,payload)
  values(p_season_id,'ITEM_USED',p_trainer_id,p_trainer_id,'owner','item_used:'||v_row.id::text,
    jsonb_build_object('purchase_id',v_purchase.id,'item',v_name,'operation_id',v_row.operation_id));
  return public.item_delivery_receipt(v_row);
end $$;

-- Administrator only, idempotent receipt (admin_setup_*), a written reason.
-- Only an untouched paid purchase: never one delivered, used, redeemed,
-- authorized for a physical use or in delivery.
create function public.api_admin_refund_purchase(p_request jsonb) returns jsonb
language plpgsql set search_path=pg_catalog,public as $$
declare cached jsonb; sid uuid=(p_request->>'season_id')::uuid; pid uuid=(p_request->>'resource_id')::uuid;
  b jsonb=p_request->'body'; v public.purchases; v_name text; v_ledger uuid=gen_random_uuid();
  v_reason text; v_actor uuid=(p_request->>'actor_trainer_id')::uuid;
begin
  cached=public.admin_setup_begin('purchase_refund',p_request); if cached is not null then return cached; end if;
  if pid is null or jsonb_typeof(b) is distinct from 'object' or b-array['reason']<>'{}'::jsonb
    or jsonb_typeof(b->'reason') is distinct from 'string'
    or length(btrim(b->>'reason')) not between 3 and 500 then
    perform public.admin_setup_fail('invalid_request',422); end if;
  v_reason=btrim(b->>'reason');
  select * into v from public.purchases where id=pid and season_id=sid for update;
  if not found then perform public.admin_setup_fail('purchase_not_found',404); end if;
  if v.status<>'pending' or v.acquisition_type<>'paid' or coalesce(v.total_price,0)<=0
    or exists(select 1 from public.item_deliveries where purchase_id=pid and status<>'RELEASED')
    or exists(select 1 from public.redemptions where purchase_id=pid)
    or exists(select 1 from public.item_use_authorizations where purchase_id=pid) then
    perform public.admin_setup_fail('purchase_not_refundable'); end if;
  select name into v_name from public.shop_items where id=v.shop_item_id;
  update public.purchases set status='refunded' where id=pid;
  insert into public.coin_transactions(id,season_id,trainer_id,season_player_id,amount,
    transaction_type,reference_type,reference_id,created_by_trainer_id)
  values(v_ledger,sid,v.trainer_id,v.season_player_id,v.total_price,'purchase_refund','purchase',pid,v_actor);
  insert into public.activity_events(season_id,type,actor_trainer_id,trainer_id,visibility,dedupe_key,payload)
  values(sid,'PURCHASE_REFUNDED',v_actor,v.trainer_id,'owner','purchase_refunded:'||pid::text,
    jsonb_build_object('purchase_id',pid,'item',v_name,'amount',v.total_price,'reason',v_reason,
      'ledger_id',v_ledger));
  return public.admin_setup_finish('purchase_refund',p_request,sid,pid,jsonb_build_object(
    'trainer_id',v.trainer_id,'item',v_name,'amount',v.total_price,'ledger_id',v_ledger,'reason',v_reason));
end $$;

do $$ declare f regprocedure; begin
  foreach f in array array[
    'public.item_delivery_receipt(public.item_deliveries)'::regprocedure,
    'public.item_use_purchase(uuid,uuid,uuid)'::regprocedure,
    'public.api_reserve_item_delivery(uuid,uuid,uuid,uuid,text,integer,text)'::regprocedure,
    'public.api_complete_item_delivery(uuid,uuid,uuid,text,text)'::regprocedure,
    'public.api_release_item_delivery(uuid,uuid,uuid)'::regprocedure,
    'public.api_use_permission_item(uuid,uuid,uuid,uuid)'::regprocedure,
    'public.api_admin_refund_purchase(jsonb)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
