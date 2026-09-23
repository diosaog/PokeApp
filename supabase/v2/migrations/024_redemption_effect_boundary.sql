-- Backend-only entitlement consumption. No physical save operation.
begin;

alter table public.redemptions
  add column idempotency_key text,
  add column effect_code text,
  add column target_pokemon_entity_id uuid,
  add column target_owner_trainer_id uuid references public.trainers(id),
  add column identity_revision_id uuid references public.pokemon_identity_revisions(id),
  add column physical_effect_status text,
  add column physical_effect_completed_at timestamptz,
  add column requested_at timestamptz,
  add column activity_event_id uuid references public.activity_events(id) deferrable initially deferred,
  add column receipt jsonb,
  add constraint redemption_entity_season_fk foreign key(target_pokemon_entity_id,season_id)
    references public.pokemon_entities(id,season_id),
  add constraint redemption_purchase_unique unique(purchase_id),
  add constraint redemption_boundary_chk check (
    (idempotency_key is null and effect_code is null and target_pokemon_entity_id is null
      and target_owner_trainer_id is null and identity_revision_id is null
      and physical_effect_status is null and physical_effect_completed_at is null
      and requested_at is null and activity_event_id is null and receipt is null)
    or
    (idempotency_key is not null and length(idempotency_key) between 1 and 128
      and idempotency_key ~ '^[!-~]+$' and effect_code is not null
      and target_pokemon_entity_id is not null and target_owner_trainer_id is not null
      and identity_revision_id is not null and requested_at is not null
      and activity_event_id is not null and receipt is not null and jsonb_typeof(receipt)='object'
      and physical_effect_status is not null and physical_effect_completed_at is null
      and ((effect_code='shield' and physical_effect_status='not_required')
        or (effect_code='revive' and physical_effect_status='pending')))
  );
create unique index redemption_idempotency_idx
  on public.redemptions(season_id,trainer_id,purchase_id,idempotency_key)
  where idempotency_key is not null;

-- Preserve timestamp semantics: revivido_at is NOT a new boolean flag.
alter table public.pokemon_entity_flags add column flag_timestamp timestamptz;
alter table public.pokemon_entity_flags drop constraint pokemon_entity_flags_check;
alter table public.pokemon_entity_flags add constraint pokemon_entity_flag_value_chk check (
  (legacy_flag_id is not null and flag_value is null and flag_timestamp is null)
  or (legacy_flag_id is null and flag_value is not null and flag_timestamp is null)
  or (legacy_flag_id is null and flag_value is null and flag_timestamp is not null and flag_type='revivido_at')
);

-- Previously some admin browser writes were allowed. All effect surfaces are backend-only now.
revoke insert,update,delete,truncate on public.purchases,public.redemptions,
  public.pokemon_entities,public.pokemon_observations,public.pokemon_entity_flags,
  public.trainer_flags,public.activity_events from public,anon,authenticated;

create function public.api_redeem_purchase(
  p_season_id uuid, p_trainer_id uuid, p_purchase_id uuid, p_pokemon_entity_id uuid,
  p_idempotency_key text, p_expected_revision_id uuid
) returns jsonb language plpgsql security invoker set search_path='' as $$
declare
  v_player public.season_players;
  v_purchase public.purchases;
  v_redemption public.redemptions;
  v_entity public.pokemon_entities;
  v_head public.pokemon_identity_revisions;
  v_observation public.pokemon_observations;
  v_code text;
  v_effect text;
  v_physical text;
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
  perform 1 from public.seasons where id=p_season_id for share;
  if not found then raise sqlstate 'PT404' using message='season_not_found'; end if;
  -- Shared ordering with identity and purchase RPCs: participant, purchase, entity, flags.
  select * into v_player from public.season_players
    where season_id=p_season_id and trainer_id=p_trainer_id for update;
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
  v_effect := case v_code when 'blindar_pokemon' then 'shield' when 'revivir_pokemon' then 'revive' end;
  -- No authoritative gift item exists in 001-023. Never invent a code or a partial theft.
  if v_effect is null then raise sqlstate 'PT409' using message='redemption_not_supported'; end if;
  select * into v_entity from public.pokemon_entities where id=p_pokemon_entity_id
    and season_id=p_season_id and owner_trainer_id=p_trainer_id for update;
  if not found then raise sqlstate 'PT409' using message='pokemon_not_owned'; end if;
  select * into v_head from public.pokemon_identity_revisions
    where season_id=p_season_id and trainer_id=p_trainer_id order by revision_number desc limit 1 for share;
  if not found or v_entity.identity_status<>'unambiguous' then
    raise sqlstate 'PT409' using message='pokemon_identity_ambiguous'; end if;
  if v_head.id is distinct from p_expected_revision_id then
    raise sqlstate 'PT409' using message='pokemon_target_stale'; end if;
  select * into v_observation from public.pokemon_observations
    where revision_id=v_head.id and pokemon_entity_id=v_entity.id
      and trainer_id=p_trainer_id and season_id=p_season_id and outcome in ('NEW','MATCHED') for share;
  if not found then raise sqlstate 'PT409' using message='pokemon_identity_ambiguous'; end if;
  if v_observation.source='box' and v_observation.box_number not between 1 and 8 then
    raise sqlstate 'PT409' using message='invalid_pokemon_target'; end if;
  if v_effect='revive' and not (v_observation.source='box' and v_observation.box_number=8) then
    raise sqlstate 'PT409' using message='pokemon_not_revivable'; end if;
  if v_effect='shield' and exists (
    select 1 from public.pokemon_entity_flags f left join public.pokemon_flags l on l.id=f.legacy_flag_id
    where f.season_id=p_season_id and f.pokemon_entity_id=v_entity.id and f.flag_type='blindado'
      and coalesce(f.flag_value,l.flag_value,false)
  ) then raise sqlstate 'PT409' using message='pokemon_already_shielded'; end if;

  v_physical := case v_effect when 'revive' then 'pending' else 'not_required' end;
  v_receipt := jsonb_build_object('redemption_id',v_id,'purchase_id',v_purchase.id,
    'season_id',p_season_id,'trainer_id',p_trainer_id,'shop_item_id',v_purchase.shop_item_id,
    'effect_code',v_effect,'target_pokemon_entity_id',v_entity.id,'target_owner_trainer_id',v_entity.owner_trainer_id,
    'purchase_status','used','redemption_status','applied','physical_effect_status',v_physical,
    'requested_at',v_now,'redeemed_at',v_now,'physical_effect_completed_at',null,
    'activity_event_id',v_event,'gift_purchase_id',null);
  insert into public.redemptions(id,purchase_id,season_id,trainer_id,season_player_id,shop_item_id,
    redemption_type,status,payload,redeemed_at,idempotency_key,effect_code,target_pokemon_entity_id,
    target_owner_trainer_id,identity_revision_id,physical_effect_status,requested_at,activity_event_id,receipt)
  values(v_id,v_purchase.id,p_season_id,p_trainer_id,v_player.id,v_purchase.shop_item_id,
    v_effect,'applied',jsonb_build_object('item_code',v_code,'effect_code',v_effect,
      'target_pokemon_entity_id',v_entity.id,'target_owner_trainer_id',v_entity.owner_trainer_id),v_now,
    p_idempotency_key,v_effect,v_entity.id,v_entity.owner_trainer_id,v_head.id,v_physical,v_now,v_event,v_receipt);
  insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_value)
    values(p_season_id,p_trainer_id,v_entity.id,'blindado',true)
    on conflict(season_id,pokemon_entity_id,flag_type) do update
      set flag_value=true,legacy_flag_id=null,flag_timestamp=null;
  if v_effect='revive' then
    insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_timestamp)
      values(p_season_id,p_trainer_id,v_entity.id,'revivido_at',v_now)
      on conflict(season_id,pokemon_entity_id,flag_type) do update
        set flag_timestamp=v_now,flag_value=null,legacy_flag_id=null;
  end if;
  update public.purchases set status='used' where id=v_purchase.id;
  insert into public.activity_events(id,season_id,type,actor_trainer_id,trainer_id,visibility,dedupe_key,payload)
    values(v_event,p_season_id,'REDEMPTION_USED',p_trainer_id,p_trainer_id,'owner',
      'redemption_used:'||v_id::text,v_receipt);
  return v_receipt;
end $$;
revoke all on function public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid) from public,anon,authenticated;
grant execute on function public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid) to service_role;
comment on column public.redemptions.physical_effect_status is
  'used/applied consumes the entitlement and applies internal effects, NOT a physical save write. Companion must start from redemption_id.';
commit;
