select pokeapp_shop_test.scenario('P03 disabled', $$update public.trainers set globally_enabled=false$$, 'trainer_disabled');
select pokeapp_shop_test.scenario('P04 inactive', $$update public.season_players set status='retired'$$, 'participant_inactive');
select pokeapp_shop_test.scenario('P05 draft', $$update public.seasons set status='draft',started_at=null$$, 'season_not_active');
select pokeapp_shop_test.scenario('P06 pointer NULL', $$update public.seasons set current_matchday_id=null$$, 'current_matchday_required');
select pokeapp_shop_test.scenario('P08 first boundary', $$update public.seasons set current_matchday_id='00000000-0000-4000-8000-000000008d33' where id='00000000-0000-4000-8000-000000008d10'$$, 'store_banned');
select pokeapp_shop_test.scenario('P09 last boundary', $$update public.seasons set current_matchday_id='00000000-0000-4000-8000-000000008d34' where id='00000000-0000-4000-8000-000000008d10'$$, 'store_banned');
select pokeapp_shop_test.scenario('P10 before window', 'select 1');
select pokeapp_shop_test.scenario('P11 after window', $$update public.seasons set current_matchday_id='00000000-0000-4000-8000-000000008d35' where id='00000000-0000-4000-8000-000000008d10'$$);
select pokeapp_shop_test.scenario('P12 no window', $$update public.penalties set start_matchday_number=null,end_matchday_number=null$$, 'store_banned');
select pokeapp_shop_test.scenario('P13 unfinished', $$update public.penalties set start_matchday_number=null; update public.trial_cases set status='open'$$);
select pokeapp_shop_test.scenario('P14 unrelated', $$update public.penalties set start_matchday_number=null,penalty_type='coins_reduction'$$);
select pokeapp_shop_test.scenario('P16 disabled item', $$update public.shop_items set enabled=false$$, 'item_unavailable');
select pokeapp_shop_test.scenario('P17 free item', $$update public.shop_items set base_price=0$$, 'item_unavailable');
select pokeapp_shop_test.scenario('P20 sufficient', 'select 1');
select pokeapp_shop_test.scenario('P21 exact', $$update public.coin_transactions set amount=10$$);
select pokeapp_shop_test.scenario('P22 insufficient', $$update public.coin_transactions set amount=9$$, 'insufficient_funds');
select pokeapp_shop_test.scenario('P39 pending non-comodin', $$select pokeapp_shop_test.promo('pending')$$, 'promotion_pending');
select pokeapp_shop_test.scenario('P40 pending comodin', $$select pokeapp_shop_test.promo('pending'); update public.shop_items set category='comodines'$$);
select pokeapp_shop_test.scenario('P41 available', $$select pokeapp_shop_test.promo('active')$$, 'promotion_available', true);
select pokeapp_shop_test.scenario('P43 exhausted', $$select pokeapp_shop_test.promo('exhausted')$$, 'base_price_confirmation_required');
select pokeapp_shop_test.scenario('P43 ended', $$select pokeapp_shop_test.promo('ended')$$, 'base_price_confirmation_required');
select pokeapp_shop_test.scenario('P43 expired time', $$select pokeapp_shop_test.promo('active'); update public.shop_promotions set ends_at=now()-interval '1 second'$$, 'base_price_confirmation_required');
select pokeapp_shop_test.scenario('P44 confirmed', $$select pokeapp_shop_test.promo('exhausted')$$, null, true);
select pokeapp_shop_test.scenario('P45 different day', $$select pokeapp_shop_test.promo('active',3)$$);
select pokeapp_shop_test.scenario('pending activation elapsed', $$select pokeapp_shop_test.promo('pending'); update public.shop_promotions set activates_at=now()-interval '1 second'$$, 'promotion_available');
select pokeapp_shop_test.scenario('future activation', $$select pokeapp_shop_test.promo('active'); update public.shop_promotions set activates_at=now()+interval '1 hour'$$, 'promotion_pending');
select pokeapp_shop_test.scenario('cancelled current', $$update public.matchdays set status='cancelled'$$, 'current_matchday_invalid');

-- Failure injection is restricted to disposable PostgreSQL, never staging.
create function pokeapp_shop_test.fail_write() returns trigger language plpgsql as $$
begin raise exception 'injected_failure'; end; $$;
select pokeapp_shop_test.scenario('P28 purchase rollback', $$create trigger fixture_failure before insert on public.purchases for each row execute function pokeapp_shop_test.fail_write()$$, 'injected_failure');
select pokeapp_shop_test.scenario('P29 ledger rollback', $$create trigger fixture_failure before insert on public.coin_transactions for each row execute function pokeapp_shop_test.fail_write()$$, 'injected_failure');
select pokeapp_shop_test.scenario('P30 event rollback', $$create trigger fixture_failure before insert on public.activity_events for each row execute function pokeapp_shop_test.fail_write()$$, 'injected_failure');

do $$ declare first jsonb; retried jsonb; second jsonb; begin
 first := pokeapp_shop_test.buy('receipt');
 perform pokeapp_shop_test.assert_true(first->>'balance_after'='90', 'P20 balance after');
 perform pokeapp_shop_test.assert_true((select amount=-10 and reference_id=(first->>'id')::uuid and transaction_type='purchase'
   from public.coin_transactions where id=(first->>'ledger_id')::uuid), 'P26 exact negative debit');
 perform pokeapp_shop_test.assert_true((select type='PURCHASE_COMPLETED' and visibility='public' and payload->>'item'='Fixture Item'
   from public.activity_events where id=(first->>'event_id')::uuid), 'P27 public event');
 second := pokeapp_shop_test.buy('second');
 perform pokeapp_shop_test.assert_true(second->>'balance_after'='80' and second->>'id'<>first->>'id', 'P34 distinct keys');
 update public.shop_items set base_price=30 where code in ('purchase_test_item','purchase_test_other');
 retried := pokeapp_shop_test.buy('receipt',true);
 perform pokeapp_shop_test.assert_true(first=retried, 'P24 P25 P31 P49 historical price balance and irrelevant confirmation');
 perform pokeapp_shop_test.assert_true((select count(*)=2 from public.purchases), 'P31 no duplicates');
 perform pokeapp_shop_test.expect_failure($q$select pokeapp_shop_test.buy('receipt',false,'00000000-0000-4000-8000-000000008d61')$q$,'PT409');
 perform pokeapp_shop_test.expect_failure($q$select pokeapp_shop_test.buy('missing',false,'00000000-0000-4000-8000-000000008d99')$q$,'PT404');
 update public.shop_items set base_price=10 where code in ('purchase_test_item','purchase_test_other');
 perform pokeapp_shop_test.promo('exhausted');
 first := pokeapp_shop_test.buy('confirmed',true);
 perform pokeapp_shop_test.expect_failure($q$select pokeapp_shop_test.buy('confirmed',false)$q$,'PT409');
 update public.shop_promotions set status='active';
 update public.purchases set promotion_id='00000000-0000-4000-8000-000000008d70' where id=(first->>'id')::uuid;
 perform pokeapp_shop_test.buy('claimed');
 perform pokeapp_shop_test.assert_true((select count(*)=4 from public.purchases), 'P42 already claimed base');
 perform pokeapp_shop_test.assert_true((select count(*)=0 from public.redemptions)
    and (select count(*)=0 from public.save_files), 'P37 P38 no redemption or save effect');
end; $$;
select pokeapp_shop_test.assert_true(not has_function_privilege('anon','public.api_create_normal_purchase(uuid,uuid,uuid,text,boolean)','EXECUTE')
 and not has_function_privilege('authenticated','public.api_create_normal_purchase(uuid,uuid,uuid,text,boolean)','EXECUTE')
 and has_function_privilege('service_role','public.api_create_normal_purchase(uuid,uuid,uuid,text,boolean)','EXECUTE'), 'P46 RPC service-only');
set local role service_role;
select pokeapp_shop_test.buy('service');
reset role;
set local role authenticated;
select set_config('request.jwt.claim.sub','00000000-0000-4000-8000-000000008da1',true);
select pokeapp_shop_test.expect_failure($q$select pokeapp_shop_test.buy('forbidden')$q$,'42501');
select pokeapp_shop_test.expect_failure($q$insert into public.purchases(season_id,trainer_id,season_player_id,shop_item_id,unit_price)
values('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d01','00000000-0000-4000-8000-000000008d50','00000000-0000-4000-8000-000000008d60',1)$q$,'42501');
reset role;
