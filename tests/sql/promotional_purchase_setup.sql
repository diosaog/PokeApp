-- Extends shop_context_setup.sql + purchase_setup.sql in the local test DB only.
insert into public.trainers(id,display_name,slug,auth_user_id) values
 ('00000000-0000-4000-8000-000000008d03','Promo Third','shop_context_third','00000000-0000-4000-8000-000000008da3');
insert into public.season_players(id,season_id,trainer_id) values
 ('00000000-0000-4000-8000-000000008d52','00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d03');
insert into public.coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type)
 select season_id,trainer_id,id,100,'admin_adjustment' from public.season_players
 where id in ('00000000-0000-4000-8000-000000008d51','00000000-0000-4000-8000-000000008d52');
insert into public.shop_promotions(id,season_id,matchday_id,shop_item_id,promotion_type,status,base_price,effective_price,stock_total,announced_at,activates_at)
 values ('00000000-0000-4000-8000-000000008d70','00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d32',
 '00000000-0000-4000-8000-000000008d60','normal','active',10,8,2,now()-interval '48 hours',now()-interval '24 hours'),
 ('00000000-0000-4000-8000-000000008d71','00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d32',
 '00000000-0000-4000-8000-000000008d61','mega','active',10,5,1,now()-interval '48 hours',now()-interval '24 hours');
create function pokeapp_shop_test.claim(key text default 'promo-first', promo uuid default '00000000-0000-4000-8000-000000008d70',
 trainer uuid default '00000000-0000-4000-8000-000000008d01') returns jsonb language sql as $$
 select public.api_create_promotional_purchase('00000000-0000-4000-8000-000000008d10',trainer,promo,key);
$$;
create function pokeapp_shop_test.promo_state() returns jsonb language sql as $$
 select jsonb_build_array(pokeapp_shop_test.counts(),(select jsonb_agg(to_jsonb(s) order by id) from public.shop_promotions s));
$$;
create function pokeapp_shop_test.promo_scenario(label text, preparation text, rejected text default null) returns void language plpgsql as $$
declare before_state jsonb; receipt jsonb;
begin
 execute preparation;
 before_state := pokeapp_shop_test.promo_state();
 begin
  receipt := pokeapp_shop_test.claim(md5(label));
  if rejected is not null then raise exception 'Expected rejection: %', rejected; end if;
  perform pokeapp_shop_test.assert_true(receipt->>'quantity'='1' and receipt->>'status'='pending'
    and receipt->>'unit_price'='8' and receipt->>'remaining_stock'='1',label);
 exception when others then
  if rejected is null or sqlerrm <> rejected then raise; end if;
  perform pokeapp_shop_test.assert_true(before_state=pokeapp_shop_test.promo_state(),label || ' all effects rolled back');
 end;
 raise sqlstate 'Z0001';
exception when sqlstate 'Z0001' then raise notice 'PASS %',label;
end; $$;
