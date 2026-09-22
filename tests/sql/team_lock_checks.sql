-- Execute inside a transaction; the validator rolls this test state back.
select pokeapp_team_lock_test.assert_true(
 to_regprocedure('public.api_upsert_team_lock(uuid,uuid,uuid,uuid,uuid,text,uuid,jsonb,jsonb,jsonb)') is not null,
 'RPC exists');
select pokeapp_team_lock_test.assert_true(
 not has_function_privilege('anon','public.api_upsert_team_lock(uuid,uuid,uuid,uuid,uuid,text,uuid,jsonb,jsonb,jsonb)','execute')
 and not has_function_privilege('authenticated','public.api_upsert_team_lock(uuid,uuid,uuid,uuid,uuid,text,uuid,jsonb,jsonb,jsonb)','execute')
 and has_function_privilege('service_role','public.api_upsert_team_lock(uuid,uuid,uuid,uuid,uuid,text,uuid,jsonb,jsonb,jsonb)','execute'),
 'RPC grants are backend-only');
select pokeapp_team_lock_test.assert_true(
 (select not prosecdef and proconfig is not null from pg_proc where oid='public.api_upsert_team_lock(uuid,uuid,uuid,uuid,uuid,text,uuid,jsonb,jsonb,jsonb)'::regprocedure),
 'invoker and fixed search_path');

set role anon;
select pokeapp_team_lock_test.expect_failure('select * from pokeapp_team_lock_test.run()', '42501');
reset role;
set role authenticated;
select pokeapp_team_lock_test.expect_failure('select * from pokeapp_team_lock_test.run()', '42501');
reset role;
set role service_role;
select id from pokeapp_team_lock_test.run();
select id from pokeapp_team_lock_test.run();
reset role;
select pokeapp_team_lock_test.assert_true((select count(*)=1 from public.team_locks), 'one logical lock');
select pokeapp_team_lock_test.assert_true((select count(*)=1 from public.activity_events), 'one event');
select pokeapp_team_lock_test.assert_true(
 (select type='TEAM_LOCKED' and visibility='public' and payload->>'save_sha256'=repeat('a',64)
  and (context->>'matchday_number')::int=1 from public.activity_events), 'event payload');
create temporary table first_lock as select * from public.team_locks;
create temporary table first_event as select * from public.activity_events;

update pokeapp_team_lock_test.request r set
 save_file_id=sf.id, save_sha256=sf.sha256, parsed_save_id=ps.id, parsed_payload=ps.payload,
 public_team_snapshot=(select jsonb_agg(jsonb_build_object('species', mon->>'species')) from jsonb_array_elements(ps.payload->'party') mon),
 private_team_snapshot=ps.payload->'party'
from public.save_files sf join public.parsed_saves ps on ps.save_file_id=sf.id
where sf.id='00000000-0000-4000-8000-000000008c21';
select id from pokeapp_team_lock_test.run();
select pokeapp_team_lock_test.assert_true(
 (select l.id=f.id and l.created_at=f.created_at and l.locked_at>=f.locked_at
 and l.save_sha256=repeat('b',64) and l.save_file_id='00000000-0000-4000-8000-000000008c21'
 and l.private_team_snapshot->0->>'species'='Crobat' from public.team_locks l, first_lock f), 'replacement receipt');
select pokeapp_team_lock_test.assert_true(
 (select to_jsonb(e)=to_jsonb(f) from public.activity_events e, first_event f), 'replacement keeps first event');

update public.parsed_saves set payload=jsonb_set(payload,'{party,0,ivs,hp}','0')
where id='00000000-0000-4000-8000-000000008c31';
select pokeapp_team_lock_test.assert_true(
 (select private_team_snapshot->0->'ivs'->>'hp'='30' from public.team_locks), 'snapshot independence');
select pokeapp_team_lock_test.expect_failure('select * from pokeapp_team_lock_test.run()', 'PT409');
update public.parsed_saves set payload=(select parsed_payload from pokeapp_team_lock_test.request)
where id='00000000-0000-4000-8000-000000008c31';

set role authenticated;
set request.jwt.claim.sub='00000000-0000-4000-8000-000000008ca1';
select pokeapp_team_lock_test.assert_true((select count(*)=1 from public.current_team_locks), 'owner private read');
reset role;
-- Direct writes have no policy: assert zero affected rows rather than assuming an exception.
set role authenticated;
do $$ declare n int; begin
 update public.team_locks set is_late=true;
 get diagnostics n=row_count;
 perform pokeapp_team_lock_test.assert_true(n=0,'authenticated direct update denied');
end; $$;
set request.jwt.claim.sub='00000000-0000-4000-8000-000000008ca2';
select pokeapp_team_lock_test.assert_true((select count(*)=0 from public.current_team_locks), 'other trainer private denied');
select pokeapp_team_lock_test.assert_true((select count(*)=1 from public.public_team_locks), 'other trainer public read');
select pokeapp_team_lock_test.expect_failure('select private_team_snapshot from public.public_team_locks','42703');
reset role;
update public.trainers set is_admin=true where id='00000000-0000-4000-8000-000000008c04';
set role authenticated;
select pokeapp_team_lock_test.assert_true((select count(*)=1 from public.current_team_locks), 'admin private read');
reset role;
set role anon;
select pokeapp_team_lock_test.expect_failure('select * from public.public_team_locks','42501');
reset role;

update public.matchdays set status='closed', closed_at=now() where id='00000000-0000-4000-8000-000000008c12';
select pokeapp_team_lock_test.expect_failure('select * from pokeapp_team_lock_test.run()', 'PT409');
update public.matchdays set status='open', closed_at=null where id='00000000-0000-4000-8000-000000008c12';
update public.season_players set status='retired' where id='00000000-0000-4000-8000-000000008c02';
select pokeapp_team_lock_test.expect_failure('select * from pokeapp_team_lock_test.run()', 'PT403');
update public.season_players set status='active' where id='00000000-0000-4000-8000-000000008c02';
update public.trainers set globally_enabled=false where id='00000000-0000-4000-8000-000000008c01';
select pokeapp_team_lock_test.expect_failure('select * from pokeapp_team_lock_test.run()', 'PT403');
update public.trainers set globally_enabled=true where id='00000000-0000-4000-8000-000000008c01';
update pokeapp_team_lock_test.request set save_sha256=repeat('f',64);
select pokeapp_team_lock_test.expect_failure('select * from pokeapp_team_lock_test.run()', 'PT409');
update pokeapp_team_lock_test.request set save_sha256=repeat('b',64);
update pokeapp_team_lock_test.request set trainer_id='00000000-0000-4000-8000-000000008c04';
select pokeapp_team_lock_test.expect_failure('select * from pokeapp_team_lock_test.run()', 'PT404');
update pokeapp_team_lock_test.request set trainer_id='00000000-0000-4000-8000-000000008c01';

-- Force the event insert to fail AFTER the Team Lock write.
create function pokeapp_team_lock_test.fail_event() returns trigger language plpgsql as $$ begin
 raise sqlstate 'XX999' using message='intentional fixture event failure';
end; $$;
create trigger team_lock_test_fail_event before insert on public.activity_events
 for each row execute function pokeapp_team_lock_test.fail_event();
create temporary table before_failed_replacement as select * from public.team_locks;
select pokeapp_team_lock_test.expect_failure('select * from pokeapp_team_lock_test.run()', 'XX999');
select pokeapp_team_lock_test.assert_true(
 (select to_jsonb(l)=to_jsonb(b) from public.team_locks l,before_failed_replacement b), 'replacement rollback');
delete from public.activity_events;
delete from public.team_locks;
select pokeapp_team_lock_test.expect_failure('select * from pokeapp_team_lock_test.run()', 'XX999');
select pokeapp_team_lock_test.assert_true((select count(*)=0 from public.team_locks), 'insert rollback');
select pokeapp_team_lock_test.assert_true((select count(*)=0 from public.activity_events), 'no orphan event');
