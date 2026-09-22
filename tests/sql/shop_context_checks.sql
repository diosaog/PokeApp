select pokeapp_shop_test.expect_failure($q$select * from public.api_resolve_current_matchday('00000000-0000-4000-8000-000000008d10')$q$, 'PT409');
select pokeapp_shop_test.expect_failure($q$update public.seasons set current_matchday_id='00000000-0000-4000-8000-000000008d36' where id='00000000-0000-4000-8000-000000008d10'$q$, '23503');
update public.seasons set current_matchday_id='00000000-0000-4000-8000-000000008d33' where id='00000000-0000-4000-8000-000000008d10';
select pokeapp_shop_test.assert_true((select number=3 from public.api_resolve_current_matchday('00000000-0000-4000-8000-000000008d10')), 'explicit scheduled pointer');
update public.matchdays set status='cancelled' where id='00000000-0000-4000-8000-000000008d33';
select pokeapp_shop_test.expect_failure($q$select * from public.api_resolve_current_matchday('00000000-0000-4000-8000-000000008d10')$q$, 'PT409');
update public.matchdays set status='closed', closed_at=now() where id='00000000-0000-4000-8000-000000008d33';
select pokeapp_shop_test.assert_true((select number=3 from public.api_resolve_current_matchday('00000000-0000-4000-8000-000000008d10')), 'closed pointer not auto advanced');
select pokeapp_shop_test.expect_failure($q$update public.penalties set start_matchday_number=0 where id='00000000-0000-4000-8000-000000008d41'$q$, '23514');
select pokeapp_shop_test.expect_failure($q$update public.penalties set start_matchday_number=5 where id='00000000-0000-4000-8000-000000008d41'$q$, '23514');
do $$ declare n integer; begin
 for n in 2..5 loop
  perform pokeapp_shop_test.assert_true(public.api_is_store_banned('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d01',n)=(n between 3 and 4), 'inclusive window');
 end loop;
end; $$;
update public.penalties set resolved_at=now() where id='00000000-0000-4000-8000-000000008d41';
select pokeapp_shop_test.assert_true(public.api_is_store_banned('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d01',3), 'resolved_at not expiry');
update public.penalties set end_matchday_number=null where id='00000000-0000-4000-8000-000000008d41';
select pokeapp_shop_test.assert_true(public.api_is_store_banned('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d01',99), 'partial window active');
update public.penalties set start_matchday_number=null where id='00000000-0000-4000-8000-000000008d41';
select pokeapp_shop_test.assert_true(public.api_is_store_banned('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d01',99), 'no window active');
select pokeapp_shop_test.assert_true(not public.api_is_store_banned('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d02',3), 'other trainer unaffected');
update public.trial_cases set status='open' where id='00000000-0000-4000-8000-000000008d40';
select pokeapp_shop_test.assert_true(not public.api_is_store_banned('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d01',3), 'unfinished case not active');
update public.trial_cases set status='resolved' where id='00000000-0000-4000-8000-000000008d40';
update public.penalties set penalty_type='coins_reduction' where id='00000000-0000-4000-8000-000000008d41';
select pokeapp_shop_test.assert_true(not public.api_is_store_banned('00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d01',3), 'other penalty not store ban');
select pokeapp_shop_test.assert_true(
 not has_function_privilege('anon','public.api_resolve_current_matchday(uuid)','EXECUTE')
 and not has_function_privilege('authenticated','public.api_is_store_banned(uuid,uuid,integer)','EXECUTE')
 and has_function_privilege('service_role','public.api_is_store_banned(uuid,uuid,integer)','EXECUTE'), 'backend-only helpers');
set local role service_role;
select number from public.api_resolve_current_matchday('00000000-0000-4000-8000-000000008d10');
reset role;
select pokeapp_shop_test.assert_true(
 not has_column_privilege('authenticated','public.seasons','current_matchday_id','UPDATE')
 and not has_column_privilege('authenticated','public.seasons','current_matchday_id','INSERT')
 and has_column_privilege('authenticated','public.seasons','name','UPDATE'), 'new pointer server-only, prior admin columns preserved');
