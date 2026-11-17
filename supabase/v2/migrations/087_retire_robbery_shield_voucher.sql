-- 087: «Blindaje por Robo» retired (owner rule of 2026-11-17).
--
-- A robbery already leaves the stolen Pokémon ROBADO and BLINDADO, so the
-- voucher the robber used to receive is no longer issued, and every voucher
-- nobody has used yet is cancelled (it disappears from inventories). Used
-- vouchers, the shields they gave and earlier robbery receipts stay as history.
begin;

do $$ declare definition text=pg_get_functiondef('public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid)'::regprocedure);
  issue text=$q$    select id into v_voucher from public.shop_items where code='robbery_shield_voucher'
      and acquisition_mode='reward_only' for share;
    if not found then raise sqlstate 'PT409' using message='steal_cycle_conflict'; end if;
    v_gift:=gen_random_uuid();
$q$;
  gift text=$q$    insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,
      quantity,unit_price,status,acquisition_type,origin_redemption_id)
      values(v_gift,p_season_id,p_trainer_id,v_player.id,v_voucher,1,0,'pending','reward',v_id);
$q$;
begin
  if position(issue in definition)=0 or position(gift in definition)=0 then
    raise exception 'unexpected robbery redemption definition before 087'; end if;
  execute replace(replace(definition,issue,''),gift,'');
end $$;

alter table public.redemptions drop constraint redemption_boundary_chk,
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
        -- 087: a new robbery issues no voucher; earlier ones keep their gift.
        or (effect_code='steal' and physical_effect_status='pending'
          and robbery_cycle_number is not null and robbery_cycle_number>0 and target_owner_trainer_id<>trainer_id)))
  );

update public.purchases p set status='cancelled',metadata=p.metadata||jsonb_build_object(
    'cancelled_reason','robbery_shield_voucher_retired','cancelled_by_migration','087')
  from public.shop_items i
  where i.id=p.shop_item_id and i.code='robbery_shield_voucher' and p.status='pending'
    and not exists(select 1 from public.redemptions r where r.purchase_id=p.id);

do $$ begin
  if exists(select 1 from public.purchases p join public.shop_items i on i.id=p.shop_item_id
      where i.code='robbery_shield_voucher' and p.status='pending')
    or position('robbery_shield_voucher' in
      pg_get_functiondef('public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid)'::regprocedure))=0
    or position('v_voucher,1,0' in
      pg_get_functiondef('public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid)'::regprocedure))>0 then
    raise exception '087: «Blindaje por Robo» could not be retired'; end if;
end $$;

notify pgrst,'reload schema';
commit;
