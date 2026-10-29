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
-- Returning the coins of an unusable purchase (e.g. a Chapa Plateada bought
-- for Pokémon Y) reuses the audited incident center (062: «Cancelar compra»
-- gives back exactly its price once, with a reason). 072 only teaches it that
-- a purchase being delivered is tied to a save operation: it is never
-- cancelled while its object may be on its way to the bag.
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

-- 062's audited command, unchanged except that a purchase in delivery is
-- tied to a save operation (the same refusal as a revive or a robbery).
create or replace function public.admin_purchase_resolve(p_actor uuid,p_season uuid,p_purchase uuid,
  p_kind text,p_operation uuid,p_hash text,p_reason text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare
  s public.seasons; p public.purchases; sp public.season_players;
  prior jsonb; ledger uuid; credit integer; result jsonb; next_status text;
begin
  perform public.admin_incident_actor(p_actor);
  if p_kind not in ('purchase_cancel','purchase_refund') or p_operation is null
     or p_hash is null or p_hash !~ '^[a-f0-9]{64}$' then
    raise exception 'invalid_incident_request';
  end if;
  if p_reason is null or length(btrim(p_reason)) not between 5 and 500 then
    raise exception 'incident_reason_required';
  end if;
  select * into s from public.seasons where id=p_season for share;
  if not found then raise exception 'season_not_found'; end if;
  select * into p from public.purchases where id=p_purchase and season_id=p_season;
  if not found then raise exception 'purchase_not_found'; end if;
  -- Same wallet lock every purchase and reward takes first: one writer.
  select * into sp from public.season_players
    where season_id=p_season and trainer_id=p.trainer_id for update;
  prior := public.admin_incident_replay(p_operation,p_actor,p_kind,p_season,p_hash);
  if prior is not null then return prior; end if;
  if s.status='archived' then raise exception 'historical_artifact_immutable'; end if;
  select * into p from public.purchases where id=p_purchase for update;
  if exists(select 1 from public.item_use_authorizations a where a.purchase_id=p.id)
     or exists(select 1 from public.item_deliveries d where d.purchase_id=p.id and d.status='RESERVED') then
    raise exception 'purchase_linked_to_save_operation';
  end if;
  if p_kind='purchase_cancel' then
    if p.status<>'pending' or exists(select 1 from public.redemptions r
        where r.purchase_id=p.id and r.status='applied') then
      raise exception 'purchase_not_cancellable';
    end if;
    next_status := 'cancelled';
  else
    if p.status<>'used' then raise exception 'purchase_not_refundable'; end if;
    next_status := 'refunded';
  end if;
  credit := p.total_price;
  update public.purchases set status=next_status,
    metadata=metadata || jsonb_build_object('admin_incident', jsonb_build_object(
      'operation_id',p_operation,'kind',p_kind,'actor_trainer_id',p_actor,
      'previous_status',p.status,'at',clock_timestamp()))
    where id=p.id;
  if credit>0 then
    ledger := gen_random_uuid();
    insert into public.coin_transactions(id,season_id,trainer_id,season_player_id,amount,
      transaction_type,reference_type,reference_id,metadata,created_by_trainer_id)
    values(ledger,p_season,p.trainer_id,sp.id,credit,'compensation',
      case p_kind when 'purchase_cancel' then 'purchase_cancellation' else 'purchase_refund' end,
      p.id,jsonb_build_object('operation_id',p_operation,'reason',btrim(p_reason)),p_actor);
  end if;
  result := jsonb_build_object('operation_id',p_operation,'kind',p_kind,'season_id',p_season,
    'trainer_id',p.trainer_id,'purchase_id',p.id,'status',next_status,'amount',credit,
    'ledger_id',ledger,'balance_after',public.admin_incident_balance(p_season,p.trainer_id),
    'replayed',false);
  insert into public.admin_incident_commands(operation_id,season_id,actor_trainer_id,kind,
    target_trainer_id,purchase_id,request_hash,reason,amount,ledger_id,result)
  values(p_operation,p_season,p_actor,p_kind,p.trainer_id,p.id,p_hash,btrim(p_reason),
    credit,ledger,result);
  return result;
end $$;

-- 064's overview, unchanged except that a purchase in delivery shows as tied
-- to a save operation and is not offered for cancellation.
create or replace function public.admin_incident_read(p_actor uuid,p_season uuid) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare s public.seasons;
begin
  perform public.admin_incident_actor(p_actor);
  select * into s from public.seasons where id=p_season;
  if not found then raise exception 'season_not_found'; end if;
  return jsonb_build_object(
    'season_id',s.id,'season_status',s.status,
    'wallets',coalesce((select jsonb_agg(w order by w->>'display_name') from (
      select jsonb_build_object('trainer_id',sp.trainer_id,'display_name',t.display_name,
        'status',sp.status,'balance',public.admin_incident_balance(s.id,sp.trainer_id)) w
      from public.season_players sp join public.trainers t on t.id=sp.trainer_id
      where sp.season_id=s.id) q),'[]'::jsonb),
    'purchases',coalesce((select jsonb_agg(x order by x->>'purchased_at' desc) from (
      select jsonb_build_object('id',p.id,'trainer_id',p.trainer_id,'display_name',t.display_name,
        'item_name',i.name,'item_code',i.code,'total_price',p.total_price,'status',p.status,
        'acquisition_type',p.acquisition_type,'purchased_at',p.purchased_at,
        'linked_operation',exists(select 1 from public.item_use_authorizations a where a.purchase_id=p.id)
          or exists(select 1 from public.item_deliveries d where d.purchase_id=p.id and d.status='RESERVED'),
        'cancellable',p.status='pending' and s.status<>'archived'
          and not exists(select 1 from public.item_use_authorizations a where a.purchase_id=p.id)
          and not exists(select 1 from public.item_deliveries d where d.purchase_id=p.id and d.status='RESERVED')
          and not exists(select 1 from public.redemptions r where r.purchase_id=p.id and r.status='applied'),
        'refundable',p.status='used' and s.status<>'archived'
          and not exists(select 1 from public.item_use_authorizations a where a.purchase_id=p.id)) x
      from public.purchases p join public.trainers t on t.id=p.trainer_id
        join public.shop_items i on i.id=p.shop_item_id
      where p.season_id=s.id order by p.purchased_at desc limit 300) q),'[]'::jsonb),
    'robberies',coalesce((select jsonb_agg(r order by r->>'created_at' desc) from (
      select jsonb_build_object('authorization_id',x.authorization_id,'purchase_id',a.purchase_id,
        'requester',(select display_name from public.trainers where id=a.trainer_id),
        'donor',(select display_name from public.trainers where id=x.donor_id),
        'state',public.transfer_state(x.authorization_id),
        'source_obligation',public.transfer_obligation(x.authorization_id,'source'),
        'destination_obligation',public.transfer_obligation(x.authorization_id,'destination'),
        'price',(select total_price from public.purchases where id=a.purchase_id),
        'cancellable',s.status<>'archived' and public.admin_robbery_blocker(x.authorization_id) is null,
        'reconciliation_required',x.terminal is null and coalesce(
          public.admin_robbery_blocker(x.authorization_id)='robbery_reconciliation_required',false),
        'cancelled_by_admin',exists(select 1 from public.admin_incident_commands c
          where c.authorization_id=x.authorization_id),
        'created_at',x.created_at) r
      from public.item_use_transfers x join public.item_use_authorizations a on a.id=x.authorization_id
      where a.season_id=s.id order by x.created_at desc limit 200) q),'[]'::jsonb),
    'history',coalesce((select jsonb_agg(h order by h->>'created_at' desc) from (
      select jsonb_build_object('operation_id',c.operation_id,'kind',c.kind,
        'actor',(select display_name from public.trainers where id=c.actor_trainer_id),
        'target',(select display_name from public.trainers where id=c.target_trainer_id),
        'purchase_id',c.purchase_id,'amount',c.amount,'reason',c.reason,
        'status',c.result->>'status','created_at',c.created_at) h
      from public.admin_incident_commands c where c.season_id=s.id
      order by c.created_at desc limit 200) q),'[]'::jsonb));
end $$;

do $$ declare f regprocedure; begin
  foreach f in array array[
    'public.item_delivery_receipt(public.item_deliveries)'::regprocedure,
    'public.item_use_purchase(uuid,uuid,uuid)'::regprocedure,
    'public.api_reserve_item_delivery(uuid,uuid,uuid,uuid,text,integer,text)'::regprocedure,
    'public.api_complete_item_delivery(uuid,uuid,uuid,text,text)'::regprocedure,
    'public.api_release_item_delivery(uuid,uuid,uuid)'::regprocedure,
    'public.api_use_permission_item(uuid,uuid,uuid,uuid)'::regprocedure
  ] loop
    execute format('revoke all on function %s from public,anon,authenticated,service_role',f);
    execute format('grant execute on function %s to service_role',f);
  end loop;
end $$;
notify pgrst,'reload schema';
commit;
