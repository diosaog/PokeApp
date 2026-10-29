"""Focused rollback-only checks for 072, on a disposable Supabase-shaped cluster.

Synthetic rows only. Proves: a paid in-game object is reserved once, written
by the Launcher and completed once (the purchase becomes used and the owner
gets an event), a second reservation or another device is refused, a release
returns the purchase untouched, idempotent replays return the same receipt
and a different request with the same operation is refused; Captura Extra
records its use once; Pokémon comodines and unavailable objects are never
delivered; an administrator refunds an untouched paid purchase exactly once
(ledger +price, owner and admin events, receipt replay), never one in
delivery, used or by a non-admin; nothing new for browsers.
"""

from tools.validate_phase21_native import PLAYER, SEASON, TRAINER
from tools.validate_phase21_native import sql as native_sql

ADMIN = "66666666-6666-6666-6666-666666666666"
OTHER = "77777777-7777-7777-7777-777777777777"
OTHER_PLAYER = "88888888-8888-8888-8888-888888888888"
P_CAP = "c0000000-0000-4000-8000-000000000001"  # Chapa Plateada
P_BERRY = "c0000000-0000-4000-8000-000000000002"  # Baya Zidra
P_CAPTURE = "c0000000-0000-4000-8000-000000000003"  # Captura Extra
P_SHIELD = "c0000000-0000-4000-8000-000000000004"  # Blindar Pokemon
P_REFUND = "c0000000-0000-4000-8000-000000000005"  # Menta de Naturaleza
OP1 = "d0000000-0000-4000-8000-000000000001"
OP2 = "d0000000-0000-4000-8000-000000000002"
OP3 = "d0000000-0000-4000-8000-000000000003"
OP4 = "d0000000-0000-4000-8000-000000000004"
A, B = "a" * 64, "b" * 64


def _purchase(pid, code, price):
    return (
        f"insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,status)"
        f" select '{pid}','{SEASON}','{TRAINER}','{PLAYER}',id,1,{price},'pending' from public.shop_items where code='{code}';"
    )


def validate(pg):
    seed = native_sql().split("select case when public.observed_native_progress")[0]
    seed = seed.replace(
        "begin;",
        "begin; update public.seasons set status='draft' where status='active';",
    )
    purchases = "\n".join(
        _purchase(pid, code, price)
        for pid, code, price in (
            (P_CAP, "chapa_plateada", 6),
            (P_BERRY, "baya_zidra", 3),
            (P_CAPTURE, "captura_extra", 5),
            (P_SHIELD, "blindar_pokemon", 12),
            (P_REFUND, "menta_naturaleza", 6),
        )
    )
    checks = f"""
insert into public.trainers(id,display_name,slug,auth_user_id,is_admin) values
  ('{ADMIN}','Admin Fixture','admin-fixture',gen_random_uuid(),true),
  ('{OTHER}','Other Fixture','other-fixture',gen_random_uuid(),false);
insert into public.season_players(id,season_id,trainer_id,status) values ('{OTHER_PLAYER}','{SEASON}','{OTHER}','active');
insert into public.season_admin_state(season_id) values ('{SEASON}');
insert into public.coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type)
  values ('{SEASON}','{TRAINER}','{PLAYER}',50,'admin_adjustment');
{purchases}
do $$ declare r jsonb; request jsonb; balance bigint;
begin
  -- 1. Reserve: the purchase stays pending until the Launcher proves the write.
  r=public.api_reserve_item_delivery('{SEASON}','{TRAINER}','{P_CAP}','{OP1}','bottle_cap',795,'SN');
  assert r->>'status'='RESERVED' and r->>'purchase_status'='pending' and r->>'game_item_id'='795', format('reserve %s',r);
  assert public.api_reserve_item_delivery('{SEASON}','{TRAINER}','{P_CAP}','{OP1}','bottle_cap',795,'SN')->>'delivery_id'=r->>'delivery_id', 'replay';
  begin
    perform public.api_reserve_item_delivery('{SEASON}','{TRAINER}','{P_CAP}','{OP2}','bottle_cap',795,'SN');
    raise exception 'second reservation accepted';
  exception when sqlstate 'PT409' then assert sqlerrm='delivery_in_progress', sqlerrm; end;
  begin
    perform public.api_reserve_item_delivery('{SEASON}','{TRAINER}','{P_CAP}','{OP1}','bottle_cap',795,'US');
    raise exception 'changed request accepted';
  exception when sqlstate 'PT409' then assert sqlerrm='idempotency_conflict', sqlerrm; end;
  begin
    perform public.api_reserve_item_delivery('{SEASON}','{OTHER}','{P_CAP}','{OP2}','bottle_cap',795,'SN');
    raise exception 'another trainer reserved';
  exception when sqlstate 'PT404' then null; end;
  begin
    perform public.api_admin_refund_purchase(jsonb_build_object('actor_trainer_id','{ADMIN}','season_id','{SEASON}',
      'resource_id','{P_CAP}','idempotency_key','072-reserved','body',jsonb_build_object('reason','En entrega')));
    raise exception 'refunded a purchase in delivery';
  exception when sqlstate 'PT409' then assert sqlerrm='purchase_not_refundable', sqlerrm; end;

  -- 2. Complete: once, with the write's proof; replay returns the receipt.
  r=public.api_complete_item_delivery('{SEASON}','{TRAINER}','{OP1}','{A}','{B}');
  assert r->>'status'='DELIVERED' and r->>'purchase_status'='used', format('complete %s',r);
  assert public.api_complete_item_delivery('{SEASON}','{TRAINER}','{OP1}','{A}','{B}')->>'status'='DELIVERED', 'complete replay';
  begin
    perform public.api_complete_item_delivery('{SEASON}','{TRAINER}','{OP1}','{B}','{A}');
    raise exception 'other proof accepted';
  exception when sqlstate 'PT409' then assert sqlerrm='idempotency_conflict', sqlerrm; end;
  begin
    perform public.api_release_item_delivery('{SEASON}','{TRAINER}','{OP1}');
    raise exception 'delivered released';
  exception when sqlstate 'PT409' then assert sqlerrm='delivery_already_completed', sqlerrm; end;
  begin
    perform public.api_reserve_item_delivery('{SEASON}','{TRAINER}','{P_CAP}','{OP2}','bottle_cap',795,'SN');
    raise exception 'used purchase reserved again';
  exception when sqlstate 'PT409' then null; end;
  assert (select count(*) from public.activity_events where type='ITEM_DELIVERED' and trainer_id='{TRAINER}'
    and visibility='owner')=1, 'one owner event';

  -- 3. Release: nothing written, the purchase is usable again.
  r=public.api_reserve_item_delivery('{SEASON}','{TRAINER}','{P_BERRY}','{OP2}','sitrus_berry',158,'SN');
  r=public.api_release_item_delivery('{SEASON}','{TRAINER}','{OP2}');
  assert r->>'status'='RELEASED' and r->>'purchase_status'='pending', format('release %s',r);
  assert public.api_release_item_delivery('{SEASON}','{TRAINER}','{OP2}')->>'status'='RELEASED', 'release replay';
  begin
    perform public.api_complete_item_delivery('{SEASON}','{TRAINER}','{OP2}','{A}','{B}');
    raise exception 'released completed';
  exception when sqlstate 'PT409' then assert sqlerrm='delivery_not_reserved', sqlerrm; end;
  r=public.api_reserve_item_delivery('{SEASON}','{TRAINER}','{P_BERRY}','{OP3}','sitrus_berry',158,'SN');
  assert r->>'status'='RESERVED', 'a released purchase is reserved again';

  -- 4. Captura Extra: its use is recorded once; comodines and mints are not objects.
  r=public.api_use_permission_item('{SEASON}','{TRAINER}','{P_CAPTURE}','{OP4}');
  assert r->>'status'='USED' and r->>'purchase_status'='used', format('permission %s',r);
  assert public.api_use_permission_item('{SEASON}','{TRAINER}','{P_CAPTURE}','{OP4}')->>'status'='USED', 'permission replay';
  begin
    perform public.api_reserve_item_delivery('{SEASON}','{TRAINER}','{P_SHIELD}',gen_random_uuid(),'metal_coat',233,'SN');
    raise exception 'comodin delivered';
  exception when sqlstate 'PT409' then assert sqlerrm='delivery_not_supported', sqlerrm; end;
  begin
    perform public.api_reserve_item_delivery('{SEASON}','{TRAINER}','{P_REFUND}',gen_random_uuid(),'leaf_stone',85,'SN');
    raise exception 'mint delivered';
  exception when sqlstate 'PT409' then assert sqlerrm='delivery_not_supported', sqlerrm; end;
  begin
    perform public.api_use_permission_item('{SEASON}','{TRAINER}','{P_SHIELD}',gen_random_uuid());
    raise exception 'comodin used as permission';
  exception when sqlstate 'PT409' then assert sqlerrm='delivery_not_supported', sqlerrm; end;
  begin
    perform public.api_reserve_item_delivery('{SEASON}','{TRAINER}','{P_REFUND}',gen_random_uuid(),'BAD',85,'SN');
    raise exception 'invalid code accepted';
  exception when sqlstate 'PT422' then null; end;

  -- 5. Refund: administrator only, once, exactly the price, audited.
  balance=(select sum(amount) from public.coin_transactions where season_id='{SEASON}' and trainer_id='{TRAINER}');
  request=jsonb_build_object('actor_trainer_id','{ADMIN}','season_id','{SEASON}','resource_id','{P_REFUND}',
    'idempotency_key','072-refund','body',jsonb_build_object('reason','No existe en los juegos Gen 6/7'));
  begin
    perform public.api_admin_refund_purchase(jsonb_set(request,'{{actor_trainer_id}}','"{OTHER}"'));
    raise exception 'non-admin refund';
  exception when sqlstate 'PT403' then null; end;
  begin
    perform public.api_admin_refund_purchase(jsonb_set(jsonb_set(request,'{{body,reason}}','"x"'),'{{idempotency_key}}','"072-short"'));
    raise exception 'empty reason accepted';
  exception when sqlstate 'PT422' then null; end;
  r=public.api_admin_refund_purchase(request);
  assert r->>'replayed'='false' and r->>'resource_id'='{P_REFUND}', format('refund %s',r);
  assert public.api_admin_refund_purchase(request)->>'replayed'='true', 'refund replay';
  assert (select status from public.purchases where id='{P_REFUND}')='refunded', 'refunded';
  assert (select sum(amount) from public.coin_transactions where season_id='{SEASON}' and trainer_id='{TRAINER}')=balance+6,
    'exactly the price back, once';
  assert (select count(*) from public.coin_transactions where reference_id='{P_REFUND}' and transaction_type='purchase_refund')=1,
    'one refund row';
  assert (select count(*) from public.activity_events where type='PURCHASE_REFUNDED' and trainer_id='{TRAINER}'
    and visibility='owner')=1, 'owner event';
  assert (select count(*) from public.activity_events where type='SEASON_ADMIN_PURCHASE_REFUND'
    and visibility='admin')=1, 'admin event';
  begin
    perform public.api_admin_refund_purchase(jsonb_set(request,'{{idempotency_key}}','"072-again"'));
    raise exception 'refunded twice';
  exception when sqlstate 'PT409' then assert sqlerrm='purchase_not_refundable', sqlerrm; end;
  begin
    perform public.api_admin_refund_purchase(jsonb_set(jsonb_set(request,'{{resource_id}}','"{P_CAP}"'),'{{idempotency_key}}','"072-used"'));
    raise exception 'refunded a delivered purchase';
  exception when sqlstate 'PT409' then assert sqlerrm='purchase_not_refundable', sqlerrm; end;

  -- 6. Private: nothing new for browsers.
  assert not has_table_privilege('authenticated','public.item_deliveries','SELECT'), 'no browser read';
  assert not has_table_privilege('anon','public.item_deliveries','SELECT'), 'no anon read';
  assert not has_function_privilege('authenticated','public.api_reserve_item_delivery(uuid,uuid,uuid,uuid,text,integer,text)','EXECUTE'), 'private reserve';
  assert not has_function_privilege('authenticated','public.api_admin_refund_purchase(jsonb)','EXECUTE'), 'private refund';
  assert has_function_privilege('service_role','public.api_complete_item_delivery(uuid,uuid,uuid,text,text)','EXECUTE'), 'API complete';
  assert (select relforcerowsecurity from pg_class where oid='public.item_deliveries'::regclass), 'forced RLS';
end $$;
-- The API's own role runs every command with its grants.
set local role service_role;
do $$ declare r jsonb; begin
  r=public.api_complete_item_delivery('{SEASON}','{TRAINER}','{OP3}','{A}','{B}');
  assert r->>'status'='DELIVERED', format('service_role complete %s',r);
  assert (select count(*) from public.item_deliveries where trainer_id='{TRAINER}')=4, 'service_role reads its rows';
end $$;
reset role;
rollback;
"""
    pg.sql(seed + checks, user="supabase_admin")
    return (
        "PASS: reserve once (replay, second/changed/other trainer refused), complete once "
        "with proof (purchase used, one owner event, release refused), release returns "
        "the purchase (reserve again), Captura Extra used once, comodines and mints never "
        "delivered, admin-only audited refund of exactly the price once (never in delivery "
        "or used), no browser privilege, service_role runs the commands"
    )
