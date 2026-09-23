select pokeapp_shop_test.promo_scenario('E03 disabled',$$update public.trainers set globally_enabled=false$$,'trainer_disabled');
select pokeapp_shop_test.promo_scenario('E04 inactive',$$update public.season_players set status='retired'$$,'participant_inactive');
select pokeapp_shop_test.promo_scenario('E05 season',$$update public.seasons set status='draft',started_at=null$$,'season_not_active');
select pokeapp_shop_test.promo_scenario('E06 no pointer',$$update public.seasons set current_matchday_id=null$$,'current_matchday_required');
select pokeapp_shop_test.promo_scenario('E07 ban',$$update public.penalties set start_matchday_number=null$$,'store_banned');
select pokeapp_shop_test.promo_scenario('E08 missing',$$delete from public.shop_promotions$$,'promotion_not_found');
select pokeapp_shop_test.promo_scenario('E09 other season',$$update public.shop_promotions set season_id='00000000-0000-4000-8000-000000008d11',matchday_id='00000000-0000-4000-8000-000000008d36'$$,'promotion_not_found');
select pokeapp_shop_test.promo_scenario('E10 wrong current',$$update public.shop_promotions set matchday_id='00000000-0000-4000-8000-000000008d33'$$,'promotion_not_current');
select pokeapp_shop_test.promo_scenario('E11 disabled item',$$update public.shop_items set enabled=false$$,'item_unavailable');
select pokeapp_shop_test.promo_scenario('E12 pending',$$update public.shop_promotions set status='pending',activates_at=now()+interval '1 hour'$$,'promotion_pending');
select pokeapp_shop_test.promo_scenario('E13 comodin pending',$$update public.shop_items set category='comodines'; update public.shop_promotions set status='pending',activates_at=now()+interval '1 hour'$$,'promotion_pending');
select pokeapp_shop_test.promo_scenario('E14 active','select 1');
select pokeapp_shop_test.promo_scenario('E35 expired',$$update public.shop_promotions set ends_at=now()-interval '1 second'$$,'promotion_expired');
select pokeapp_shop_test.promo_scenario('E35 ended',$$update public.shop_promotions set status='ended'$$,'promotion_expired');
select pokeapp_shop_test.promo_scenario('cancelled',$$update public.shop_promotions set status='cancelled'$$,'promotion_expired');
select pokeapp_shop_test.promo_scenario('E36 exhausted',$$update public.shop_promotions set stock_used=stock_total$$,'promotion_exhausted');
select pokeapp_shop_test.promo_scenario('E38 insufficient',$$update public.coin_transactions set amount=7$$,'insufficient_funds');
select pokeapp_shop_test.promo_scenario('E39 exact',$$update public.coin_transactions set amount=8$$);
select pokeapp_shop_test.promo_scenario('invalid free price',$$update public.shop_promotions set effective_price=0$$,'promotion_price_invalid');
select pokeapp_shop_test.promo_scenario('pending null time',$$update public.shop_promotions set status='pending',activates_at=null$$,'promotion_pending');
select pokeapp_shop_test.promo_scenario('elapsed pending',$$update public.shop_promotions set status='pending'$$);
select pokeapp_shop_test.promo_scenario('legacy active null time',$$update public.shop_promotions set activates_at=null$$);

create function pokeapp_shop_test.fail_promo_write() returns trigger language plpgsql as $$
begin raise exception 'injected_failure'; end; $$;
select pokeapp_shop_test.promo_scenario('E40 purchase rollback',$$create trigger fixture_failure before insert on public.purchases for each row execute function pokeapp_shop_test.fail_promo_write()$$,'injected_failure');
select pokeapp_shop_test.promo_scenario('E41 ledger rollback',$$create trigger fixture_failure before insert on public.coin_transactions for each row execute function pokeapp_shop_test.fail_promo_write()$$,'injected_failure');
select pokeapp_shop_test.promo_scenario('E42 event rollback',$$create trigger fixture_failure before insert on public.activity_events for each row execute function pokeapp_shop_test.fail_promo_write()$$,'injected_failure');
select pokeapp_shop_test.promo_scenario('stock update rollback',$$create trigger fixture_failure before update on public.shop_promotions for each row execute function pokeapp_shop_test.fail_promo_write()$$,'injected_failure');

do $$ declare first jsonb; second jsonb; before_state jsonb; begin
 first := pokeapp_shop_test.claim('receipt');
 perform pokeapp_shop_test.assert_true(first->>'balance_after'='92' and first->>'base_price'='10' and first->>'promotion_kind'='normal','E15 E21 receipt');
 perform pokeapp_shop_test.assert_true((select amount=-8 and reference_id=(first->>'id')::uuid and transaction_type='purchase' from public.coin_transactions where id=(first->>'ledger_id')::uuid),'E19 debit');
 perform pokeapp_shop_test.assert_true((select type='PURCHASE_COMPLETED' and visibility='public' and payload->>'promotion_id'=first->>'promotion_id'
  and payload->>'price'='8' and payload->>'base_price'='10' and payload->>'promotion_kind'='normal' from public.activity_events where id=(first->>'event_id')::uuid),'E20 event');
 second := pokeapp_shop_test.claim('second','00000000-0000-4000-8000-000000008d70','00000000-0000-4000-8000-000000008d02');
 perform pokeapp_shop_test.assert_true(second->>'remaining_stock'='0','E30 E31 two distinct claims');
 update public.shop_promotions set effective_price=9 where promotion_type='normal';
 update public.shop_items set base_price=20 where code in ('purchase_test_item','purchase_test_other');
 before_state := pokeapp_shop_test.promo_state();
 perform pokeapp_shop_test.assert_true(pokeapp_shop_test.claim('receipt')=first,'E22 original price balance stock snapshot');
 perform pokeapp_shop_test.assert_true(before_state=pokeapp_shop_test.promo_state(),'E23-E26 no repeat effects');
 perform pokeapp_shop_test.expect_failure($q$select pokeapp_shop_test.claim('receipt','00000000-0000-4000-8000-000000008d71')$q$,'PT409');
 perform pokeapp_shop_test.expect_failure($q$select pokeapp_shop_test.claim('third','00000000-0000-4000-8000-000000008d70','00000000-0000-4000-8000-000000008d03')$q$,'PT409');
 perform pokeapp_shop_test.expect_failure($q$select pokeapp_shop_test.claim('different-key')$q$,'PT409');
 -- Constraint is independent of the RPC (including future cancelled/refunded purchases).
 perform pokeapp_shop_test.expect_failure($q$insert into public.purchases(season_id,trainer_id,season_player_id,shop_item_id,promotion_id,unit_price)
  values('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d01','00000000-0000-4000-8000-000000008d50','00000000-0000-4000-8000-000000008d60','00000000-0000-4000-8000-000000008d70',8)$q$,'23505');
 perform pokeapp_shop_test.expect_failure($q$select pokeapp_shop_test.buy('receipt')$q$,'PT409');
 perform pokeapp_shop_test.buy('base-after-claim');
 perform pokeapp_shop_test.expect_failure($q$select pokeapp_shop_test.claim('base-after-claim')$q$,'PT409');
 perform pokeapp_shop_test.claim('mega','00000000-0000-4000-8000-000000008d71');
 perform pokeapp_shop_test.expect_failure($q$select pokeapp_shop_test.claim('mega-other','00000000-0000-4000-8000-000000008d71','00000000-0000-4000-8000-000000008d02')$q$,'PT409');
 perform pokeapp_shop_test.assert_true((select stock_used=stock_total and status='exhausted' and exhausted_at is not null from public.shop_promotions where promotion_type='mega'),'E32 mega exhausted');
 perform pokeapp_shop_test.assert_true((select count(*)=0 from public.save_files) and (select count(*)=0 from public.redemptions),'E50 E51 untouched');
end; $$;
select pokeapp_shop_test.assert_true(not has_function_privilege('authenticated','public.api_create_promotional_purchase(uuid,uuid,uuid,text)','EXECUTE')
 and not has_function_privilege('anon','public.api_create_promotional_purchase(uuid,uuid,uuid,text)','EXECUTE')
 and has_function_privilege('service_role','public.api_create_promotional_purchase(uuid,uuid,uuid,text)','EXECUTE'),'E45 E47 grants');
select pokeapp_shop_test.assert_true(not has_column_privilege('authenticated','public.shop_promotions','stock_used','UPDATE'), 'stock counter server-owned');
