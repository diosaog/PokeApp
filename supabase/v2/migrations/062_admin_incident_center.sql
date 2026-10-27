-- Phase 28 LOCAL ONLY: admin incident center.
-- Purchase cancellations, refunds and coin corrections are idempotent,
-- audited commands. Nothing is deleted or rewritten: the purchase keeps its
-- row (only its status moves forward) and coins move through new ledger rows.
-- A purchase tied to a save operation (revive, robbery) is never reversed
-- here: a physically applied robbery is not undone by changing a row, it is
-- resolved through its own coordinated reconciliation.
begin;

create table public.admin_incident_commands (
  operation_id uuid primary key,
  season_id uuid not null references public.seasons(id) on delete restrict,
  actor_trainer_id uuid not null references public.trainers(id) on delete restrict,
  kind text not null check (kind in ('purchase_cancel','purchase_refund','coin_adjustment')),
  target_trainer_id uuid not null references public.trainers(id) on delete restrict,
  purchase_id uuid references public.purchases(id) on delete restrict,
  request_hash text not null check (request_hash ~ '^[a-f0-9]{64}$'),
  reason text not null check (length(btrim(reason)) between 5 and 500),
  amount integer not null,
  ledger_id uuid references public.coin_transactions(id) on delete restrict,
  result jsonb not null check (jsonb_typeof(result)='object'),
  created_at timestamptz not null default clock_timestamp(),
  constraint admin_incident_shape check (
    (kind='coin_adjustment' and purchase_id is null and amount<>0 and ledger_id is not null)
    or (kind in ('purchase_cancel','purchase_refund') and purchase_id is not null and amount>=0
        and (amount=0)=(ledger_id is null)))
);
-- One cancellation or refund per purchase, ever: no double return of coins.
create unique index admin_incident_purchase_once
  on public.admin_incident_commands(purchase_id) where purchase_id is not null;
create unique index coin_purchase_reversal_once
  on public.coin_transactions(reference_id)
  where reference_type in ('purchase_cancellation','purchase_refund');
create index admin_incident_commands_season
  on public.admin_incident_commands(season_id, created_at desc);

-- The intervention history is append-only.
create function public.admin_incident_immutable() returns trigger
language plpgsql set search_path=pg_catalog as $$
begin raise exception 'admin_incident_immutable'; end $$;
create trigger admin_incident_no_update before update or delete on public.admin_incident_commands
  for each row execute function public.admin_incident_immutable();
create trigger admin_incident_no_truncate before truncate on public.admin_incident_commands
  for each statement execute function public.admin_incident_immutable();

alter table public.admin_incident_commands enable row level security;
alter table public.admin_incident_commands force row level security;
revoke all on public.admin_incident_commands from public, anon, authenticated, service_role;

create function public.admin_incident_actor(p_actor uuid) returns void
language plpgsql stable security definer set search_path='' as $$
begin
  if not exists(select 1 from public.trainers where id=p_actor and globally_enabled
                and is_admin and auth_user_id is not null) then
    raise exception 'admin_required';
  end if;
end $$;

-- A retry of the same operation returns its stored receipt; the same id with
-- other data is a conflict, never a second effect.
create function public.admin_incident_replay(p_operation uuid,p_actor uuid,p_kind text,
  p_season uuid,p_hash text) returns jsonb
language plpgsql stable security definer set search_path='' as $$
declare c public.admin_incident_commands;
begin
  select * into c from public.admin_incident_commands where operation_id=p_operation;
  if not found then return null; end if;
  if c.actor_trainer_id<>p_actor or c.kind<>p_kind or c.season_id<>p_season
     or c.request_hash<>p_hash then
    raise exception 'idempotency_conflict';
  end if;
  return c.result || jsonb_build_object('replayed', true);
end $$;

create function public.admin_incident_balance(p_season uuid,p_trainer uuid) returns bigint
language sql stable security definer set search_path='' as $$
  select coalesce(sum(amount::bigint),0) from public.coin_transactions
  where season_id=p_season and trainer_id=p_trainer;
$$;

create function public.admin_purchase_resolve(p_actor uuid,p_season uuid,p_purchase uuid,
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
  if exists(select 1 from public.item_use_authorizations a where a.purchase_id=p.id) then
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

create function public.admin_coin_adjust(p_actor uuid,p_season uuid,p_trainer uuid,
  p_amount integer,p_operation uuid,p_hash text,p_reason text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare s public.seasons; sp public.season_players; prior jsonb; ledger uuid; result jsonb;
begin
  perform public.admin_incident_actor(p_actor);
  if p_operation is null or p_hash is null or p_hash !~ '^[a-f0-9]{64}$'
     or p_amount is null or p_amount=0 or abs(p_amount)>100000 then
    raise exception 'invalid_incident_request';
  end if;
  if p_reason is null or length(btrim(p_reason)) not between 5 and 500 then
    raise exception 'incident_reason_required';
  end if;
  select * into s from public.seasons where id=p_season for share;
  if not found then raise exception 'season_not_found'; end if;
  select * into sp from public.season_players
    where season_id=p_season and trainer_id=p_trainer for update;
  if not found then raise exception 'participant_not_found'; end if;
  prior := public.admin_incident_replay(p_operation,p_actor,'coin_adjustment',p_season,p_hash);
  if prior is not null then return prior; end if;
  if s.status='archived' then raise exception 'historical_artifact_immutable'; end if;
  -- A correction never leaves a wallet below zero.
  if public.admin_incident_balance(p_season,p_trainer)+p_amount<0 then
    raise exception 'insufficient_funds';
  end if;
  ledger := gen_random_uuid();
  insert into public.coin_transactions(id,season_id,trainer_id,season_player_id,amount,
    transaction_type,reference_type,reference_id,metadata,created_by_trainer_id)
  values(ledger,p_season,p_trainer,sp.id,p_amount,'admin_adjustment','admin_adjustment',
    p_operation,jsonb_build_object('operation_id',p_operation,'reason',btrim(p_reason)),p_actor);
  result := jsonb_build_object('operation_id',p_operation,'kind','coin_adjustment',
    'season_id',p_season,'trainer_id',p_trainer,'purchase_id',null,'status','applied',
    'amount',p_amount,'ledger_id',ledger,
    'balance_after',public.admin_incident_balance(p_season,p_trainer),'replayed',false);
  insert into public.admin_incident_commands(operation_id,season_id,actor_trainer_id,kind,
    target_trainer_id,purchase_id,request_hash,reason,amount,ledger_id,result)
  values(p_operation,p_season,p_actor,'coin_adjustment',p_trainer,null,p_hash,btrim(p_reason),
    p_amount,ledger,result);
  return result;
end $$;

-- What an administrator needs to decide: wallets, purchases with what can be
-- done to each, robbery cases (read only: resolved by their own flow), and
-- the intervention history.
create function public.admin_incident_read(p_actor uuid,p_season uuid) returns jsonb
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
        'linked_operation',exists(select 1 from public.item_use_authorizations a where a.purchase_id=p.id),
        'cancellable',p.status='pending' and s.status<>'archived'
          and not exists(select 1 from public.item_use_authorizations a where a.purchase_id=p.id)
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

revoke all on function public.admin_incident_actor(uuid),
  public.admin_incident_replay(uuid,uuid,text,uuid,text),
  public.admin_incident_balance(uuid,uuid),
  public.admin_purchase_resolve(uuid,uuid,uuid,text,uuid,text,text),
  public.admin_coin_adjust(uuid,uuid,uuid,integer,uuid,text,text),
  public.admin_incident_read(uuid,uuid),
  public.admin_incident_immutable()
  from public, anon, authenticated;
grant execute on function public.admin_purchase_resolve(uuid,uuid,uuid,text,uuid,text,text),
  public.admin_coin_adjust(uuid,uuid,uuid,integer,uuid,text,text),
  public.admin_incident_read(uuid,uuid)
  to service_role;
commit;
