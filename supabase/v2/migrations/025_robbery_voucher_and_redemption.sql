-- Canonical reward and atomic robbery. No physical transfer or save writes.
begin;

alter table public.shop_items add column acquisition_mode text not null default 'purchasable',
  add constraint shop_item_acquisition_chk check (
    acquisition_mode='purchasable' or
    (acquisition_mode='reward_only' and base_price=0 and not enabled)),
  add constraint shop_item_voucher_chk check (code<>'robbery_shield_voucher'
    or (acquisition_mode='reward_only' and category='comodines'));
-- enabled is SHOP availability, not the ability to redeem an owned entitlement.
-- Both existing purchase RPCs reject disabled/zero-price items under their item lock.
insert into public.shop_items(code,name,category,base_price,enabled,acquisition_mode)
values('robbery_shield_voucher',U&'Comod\00EDn de Blindaje por Robo','comodines',0,false,'reward_only')
on conflict(code) do nothing;

alter table public.purchases
  add column acquisition_type text not null default 'paid',
  add column origin_redemption_id uuid unique references public.redemptions(id),
  add constraint purchase_acquisition_chk check (
    (acquisition_type='paid' and unit_price>0 and origin_redemption_id is null)
    or (acquisition_type='reward' and unit_price=0 and quantity=1 and promotion_id is null
      and origin_redemption_id is not null and idempotency_key is null and balance_after is null
      and base_price_confirmed is null));

alter table public.redemptions
  add column gift_purchase_id uuid references public.purchases(id) deferrable initially deferred,
  add column robbery_cycle_number bigint,
  drop constraint redemption_boundary_chk,
  add constraint redemption_boundary_chk check (
    (idempotency_key is null and effect_code is null and target_pokemon_entity_id is null
      and target_owner_trainer_id is null and identity_revision_id is null
      and physical_effect_status is null and physical_effect_completed_at is null
      and requested_at is null and activity_event_id is null and receipt is null
      and gift_purchase_id is null and robbery_cycle_number is null)
    or
    (idempotency_key is not null and length(idempotency_key) between 1 and 128
      and idempotency_key ~ '^[!-~]+$' and effect_code is not null
      and target_pokemon_entity_id is not null and target_owner_trainer_id is not null
      and identity_revision_id is not null and requested_at is not null
      and activity_event_id is not null and receipt is not null and jsonb_typeof(receipt)='object'
      and physical_effect_status is not null and physical_effect_completed_at is null
      and ((effect_code in ('shield','robbery_shield') and physical_effect_status='not_required'
          and gift_purchase_id is null and robbery_cycle_number is null and target_owner_trainer_id=trainer_id)
        or (effect_code='revive' and physical_effect_status='pending' and gift_purchase_id is null
          and robbery_cycle_number is null and target_owner_trainer_id=trainer_id)
        or (effect_code='steal' and physical_effect_status='pending' and gift_purchase_id is not null
          and robbery_cycle_number is not null and robbery_cycle_number>0 and target_owner_trainer_id<>trainer_id)))
  );
create unique index robbery_victim_cycle_idx
  on public.redemptions(season_id,robbery_cycle_number,target_owner_trainer_id)
  where effect_code='steal';

create table public.robbery_cycles (
  season_id uuid primary key references public.seasons(id),
  cycle_number bigint not null default 1 check(cycle_number>0),
  last_redemption_id uuid references public.redemptions(id),
  history_watermark_id uuid references public.redemptions(id)
);
alter table public.robbery_cycles enable row level security;
revoke all on public.robbery_cycles from public,anon,authenticated;
grant all on public.robbery_cycles to service_role;
comment on table public.robbery_cycles is
  'Backend-only cycle cursor; redemptions retain immutable victim history. No browser access.';

alter table public.pokemon_entity_flags
  add column flag_trainer_id uuid references public.trainers(id),
  drop constraint pokemon_entity_flag_value_chk,
  add constraint pokemon_entity_flag_value_chk check (
    (legacy_flag_id is not null and flag_value is null and flag_timestamp is null and flag_trainer_id is null)
    or (legacy_flag_id is null and flag_value is not null and flag_timestamp is null and flag_trainer_id is null)
    or (legacy_flag_id is null and flag_value is null and flag_timestamp is not null
      and flag_trainer_id is null and flag_type in ('revivido_at','robado_at'))
    or (legacy_flag_id is null and flag_value is null and flag_timestamp is null
      and flag_trainer_id is not null and flag_type='robado_from')
  );

-- Protect the reward path even for backend direct inserts, not only the HTTP API.
create function public.check_purchase_acquisition() returns trigger
language plpgsql security invoker set search_path='' as $$
declare v_item public.shop_items; v_origin public.redemptions;
begin
  select * into v_item from public.shop_items where id=new.shop_item_id for share;
  if new.acquisition_type='paid' and v_item.acquisition_mode<>'purchasable' then
    raise sqlstate 'PT409' using message='item_unavailable'; end if;
  if new.acquisition_type='reward' then
    select * into v_origin from public.redemptions where id=new.origin_redemption_id;
    if not found or v_item.code<>'robbery_shield_voucher' or v_item.acquisition_mode<>'reward_only'
      or v_origin.effect_code is distinct from 'steal' or v_origin.status<>'applied'
      or v_origin.season_id<>new.season_id or v_origin.trainer_id<>new.trainer_id
      or v_origin.season_player_id<>new.season_player_id or v_origin.gift_purchase_id is distinct from new.id then
      raise sqlstate 'PT409' using message='invalid_reward_origin'; end if;
  end if;
  return new;
end $$;
create trigger purchase_acquisition_guard before insert or update on public.purchases
for each row execute function public.check_purchase_acquisition();
revoke all on function public.check_purchase_acquisition() from public,anon,authenticated;
grant execute on function public.check_purchase_acquisition() to service_role;

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
revoke all on function public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid) from public,anon,authenticated;
grant execute on function public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid) to service_role;
commit;
