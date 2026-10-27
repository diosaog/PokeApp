-- Phase 29: an administrator can cancel a robbery that is still reversible.
-- Reversible means nothing was decided and nothing physical started: the
-- transfer is not terminal, not adjudicated, and neither save began applying
-- (the same rule as a participant's own cancel). The cancellation releases
-- both trainers exactly as that cancel does, and returns the robbery item's
-- price once: the item was never consumed, and its purchase can never start
-- another robbery (one authorization per purchase). Anything decided or
-- physical is never undone by changing rows: it stays visible as needing
-- reconciliation through its own coordinated flow.
begin;

alter table public.admin_incident_commands
  add column authorization_id uuid references public.item_use_authorizations(id) on delete restrict,
  drop constraint admin_incident_commands_kind_check,
  add constraint admin_incident_commands_kind_check check (kind in
    ('purchase_cancel','purchase_refund','coin_adjustment','robbery_cancel')),
  drop constraint admin_incident_shape,
  add constraint admin_incident_shape check (
    (kind='coin_adjustment' and purchase_id is null and authorization_id is null
      and amount<>0 and ledger_id is not null)
    or (kind in ('purchase_cancel','purchase_refund') and purchase_id is not null
      and authorization_id is null and amount>=0 and (amount=0)=(ledger_id is null))
    or (kind='robbery_cancel' and purchase_id is not null and authorization_id is not null
      and amount>=0 and (amount=0)=(ledger_id is null)));
-- One administrative cancellation per robbery; with the purchase index, the
-- item's coins can never come back twice by either path.
create unique index admin_incident_robbery_once
  on public.admin_incident_commands(authorization_id) where authorization_id is not null;

-- Why a robbery cannot be cancelled here (null: it can).
create function public.admin_robbery_blocker(p_authorization uuid) returns text
language sql stable security definer set search_path='' as $$
  select case
    when x.terminal='CANCELLED' then 'robbery_already_cancelled'
    when x.terminal is not null or x.adjudicated_at is not null
      or exists(select 1 from public.item_use_transfer_legs l
        where l.authorization_id=x.authorization_id and l.apply_started)
      then 'robbery_reconciliation_required'
    when (select count(*) from public.item_use_transfer_legs l
        where l.authorization_id=x.authorization_id)<>2
      or a.status not in ('PREPARED','PENDING_APPLICATION')
      or p.status<>'pending' then 'robbery_reconciliation_required'
  end
  from public.item_use_transfers x
  join public.item_use_authorizations a on a.id=x.authorization_id
  join public.purchases p on p.id=a.purchase_id
  where x.authorization_id=p_authorization;
$$;

create function public.admin_robbery_cancel(p_actor uuid,p_season uuid,p_authorization uuid,
  p_operation uuid,p_hash text,p_reason text) returns jsonb
language plpgsql security definer set search_path='' as $$
declare
  s public.seasons; a public.item_use_authorizations; x public.item_use_transfers;
  p public.purchases; sp public.season_players; prior jsonb; blocker text;
  ledger uuid; credit integer; result jsonb;
begin
  perform public.admin_incident_actor(p_actor);
  if p_operation is null or p_authorization is null or p_hash is null
     or p_hash !~ '^[a-f0-9]{64}$' then
    raise exception 'invalid_incident_request';
  end if;
  if p_reason is null or length(btrim(p_reason)) not between 5 and 500 then
    raise exception 'incident_reason_required';
  end if;
  select * into a from public.item_use_authorizations
    where id=p_authorization and season_id=p_season and effect_code='steal';
  if not found then raise exception 'robbery_not_found'; end if;
  -- Same lock order as the robbery verifier and the participant legs.
  perform 1 from public.trainers
    where id in (a.trainer_id,(select donor_id from public.item_use_transfers
      where authorization_id=a.id)) order by id for share;
  select * into s from public.seasons where id=p_season for no key update;
  perform 1 from public.season_players where season_id=p_season order by id for update;
  select * into x from public.item_use_transfers where authorization_id=a.id for update;
  if not found then raise exception 'robbery_not_found'; end if;
  perform 1 from public.item_use_transfer_legs where authorization_id=a.id order by side for update;
  select * into p from public.purchases where id=a.purchase_id for update;
  prior := public.admin_incident_replay(p_operation,p_actor,'robbery_cancel',p_season,p_hash);
  if prior is not null then return prior; end if;
  if s.status='archived' then raise exception 'historical_artifact_immutable'; end if;
  select * into a from public.item_use_authorizations where id=a.id;
  blocker := public.admin_robbery_blocker(a.id);
  if blocker is not null then raise exception '%', blocker; end if;
  update public.item_use_transfers set terminal='CANCELLED' where authorization_id=a.id;
  update public.item_use_transfer_legs set released=true where authorization_id=a.id;
  update public.item_use_authorizations set status='FAILED_RECOVERABLE',error_code='TRANSFER_CANCELLED',
    receipt=coalesce(receipt,'{}'::jsonb)||jsonb_build_object('admin_cancellation',jsonb_build_object(
      'operation_id',p_operation,'actor_trainer_id',p_actor,'at',clock_timestamp()))
    where id=a.id;
  update public.purchases set status='cancelled',
    metadata=metadata || jsonb_build_object('admin_incident', jsonb_build_object(
      'operation_id',p_operation,'kind','robbery_cancel','actor_trainer_id',p_actor,
      'previous_status',p.status,'authorization_id',a.id,'at',clock_timestamp()))
    where id=p.id;
  select * into sp from public.season_players where season_id=p_season and trainer_id=p.trainer_id;
  credit := p.total_price;
  if credit>0 then
    ledger := gen_random_uuid();
    insert into public.coin_transactions(id,season_id,trainer_id,season_player_id,amount,
      transaction_type,reference_type,reference_id,metadata,created_by_trainer_id)
    values(ledger,p_season,p.trainer_id,sp.id,credit,'compensation','purchase_cancellation',
      p.id,jsonb_build_object('operation_id',p_operation,'reason',btrim(p_reason),
        'authorization_id',a.id),p_actor);
  end if;
  result := jsonb_build_object('operation_id',p_operation,'kind','robbery_cancel','season_id',p_season,
    'trainer_id',p.trainer_id,'purchase_id',p.id,'authorization_id',a.id,'status','cancelled',
    'amount',credit,'ledger_id',ledger,
    'balance_after',public.admin_incident_balance(p_season,p.trainer_id),'replayed',false);
  insert into public.admin_incident_commands(operation_id,season_id,actor_trainer_id,kind,
    target_trainer_id,purchase_id,authorization_id,request_hash,reason,amount,ledger_id,result)
  values(p_operation,p_season,p_actor,'robbery_cancel',p.trainer_id,p.id,a.id,p_hash,
    btrim(p_reason),credit,ledger,result);
  return result;
end $$;

-- The overview now says, per robbery, whether it can be cancelled here or
-- needs reconciliation, and what the robber gets back.
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

revoke all on function public.admin_robbery_blocker(uuid),
  public.admin_robbery_cancel(uuid,uuid,uuid,uuid,text,text)
  from public, anon, authenticated, service_role;
grant execute on function public.admin_robbery_cancel(uuid,uuid,uuid,uuid,text,text)
  to service_role;
commit;
