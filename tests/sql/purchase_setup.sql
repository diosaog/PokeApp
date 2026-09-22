-- Extends shop_context_setup.sql in the guarded disposable local database only.
update public.seasons set status='active', started_at=now(), current_matchday_id='00000000-0000-4000-8000-000000008d32'
 where id='00000000-0000-4000-8000-000000008d10';
insert into public.season_players(id,season_id,trainer_id) values
 ('00000000-0000-4000-8000-000000008d50','00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d01'),
 ('00000000-0000-4000-8000-000000008d51','00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d02');
insert into public.shop_items(id,code,name,category,base_price) values
 ('00000000-0000-4000-8000-000000008d60','purchase_test_item','Fixture Item','bayas',10),
 ('00000000-0000-4000-8000-000000008d61','purchase_test_other','Fixture Other','comodines',10);
insert into public.coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type)
 values ('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d01','00000000-0000-4000-8000-000000008d50',100,'admin_adjustment');
create function pokeapp_shop_test.buy(key text default 'first', confirmed boolean default false,
 item uuid default '00000000-0000-4000-8000-000000008d60') returns jsonb language sql as $$
 select public.api_create_normal_purchase('00000000-0000-4000-8000-000000008d10',
 '00000000-0000-4000-8000-000000008d01',item,key,confirmed);
$$;
create function pokeapp_shop_test.counts() returns jsonb language sql as $$
 select jsonb_build_array((select count(*) from public.purchases),
 (select count(*) from public.coin_transactions),(select count(*) from public.activity_events));
$$;
create function pokeapp_shop_test.scenario(label text, preparation text, rejected text default null,
 confirmed boolean default false) returns void language plpgsql as $$
declare before_counts jsonb; receipt jsonb;
begin
 execute preparation;
 before_counts := pokeapp_shop_test.counts();
 begin
  receipt := pokeapp_shop_test.buy(md5(label),confirmed);
  if rejected is not null then raise exception 'Expected rejection: %', rejected; end if;
  perform pokeapp_shop_test.assert_true(receipt->>'status'='pending' and receipt->>'quantity'='1'
    and receipt->>'unit_price'='10' and (receipt->>'balance_after')::bigint >= 0, label);
 exception when others then
  if rejected is null or sqlerrm <> rejected then raise; end if;
  perform pokeapp_shop_test.assert_true(before_counts=pokeapp_shop_test.counts(), label || ' no partial effects');
 end;
 -- Each scenario is independent; this subtransaction undoes setup and successful purchases.
 raise sqlstate 'Z0001';
exception when sqlstate 'Z0001' then raise notice 'PASS %', label;
end;
$$;
create function pokeapp_shop_test.promo(status text, day integer default 2) returns void language sql as $$
 insert into public.shop_promotions(id,season_id,matchday_id,shop_item_id,promotion_type,status,base_price,effective_price,stock_total)
 values ('00000000-0000-4000-8000-000000008d70','00000000-0000-4000-8000-000000008d10',
 ('00000000-0000-4000-8000-000000008d3'||day)::uuid,'00000000-0000-4000-8000-000000008d60','normal',status,10,5,2);
$$;
