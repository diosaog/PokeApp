create schema pokeapp_shop_test;
create function pokeapp_shop_test.assert_true(value boolean, label text) returns void language plpgsql as $$
begin if value is distinct from true then raise exception 'Shop check failed: %', label; end if; end; $$;
create function pokeapp_shop_test.expect_failure(statement text, expected_code text) returns void language plpgsql as $$
begin execute statement; raise exception 'Expected SQLSTATE %', expected_code;
exception when others then if sqlstate <> expected_code then raise; end if; end; $$;
grant usage on schema pokeapp_shop_test to anon, authenticated, service_role;

insert into public.trainers(id,display_name,slug,auth_user_id) values
 ('00000000-0000-4000-8000-000000008d01','Shop Owner','shop_context_owner','00000000-0000-4000-8000-000000008da1'),
 ('00000000-0000-4000-8000-000000008d02','Shop Other','shop_context_other','00000000-0000-4000-8000-000000008da2');
insert into public.seasons(id,name) values
 ('00000000-0000-4000-8000-000000008d10','Shop Context'),
 ('00000000-0000-4000-8000-000000008d11','Other Context');
insert into public.season_config_versions(id,season_id,version_number,name,effective_from_matchday,total_matchdays,division_count)
select ('00000000-0000-4000-8000-000000008d' || x)::uuid, ('00000000-0000-4000-8000-000000008d' || s)::uuid,
 1,'Fixture',1,5,2 from (values ('20','10'),('21','11')) v(x,s);
insert into public.matchdays(id,season_id,number,season_config_version_id)
select ('00000000-0000-4000-8000-000000008d3' || n)::uuid, '00000000-0000-4000-8000-000000008d10',
 n, '00000000-0000-4000-8000-000000008d20' from generate_series(1,5) n;
insert into public.matchdays(id,season_id,number,season_config_version_id) values
 ('00000000-0000-4000-8000-000000008d36','00000000-0000-4000-8000-000000008d11',1,'00000000-0000-4000-8000-000000008d21');
insert into public.trial_cases(id,season_id,accused_trainer_id,title,status) values
 ('00000000-0000-4000-8000-000000008d40','00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d01','Fixture','resolved');
insert into public.penalties(id,season_id,trainer_id,trial_case_id,penalty_type,start_matchday_number,end_matchday_number) values
 ('00000000-0000-4000-8000-000000008d41','00000000-0000-4000-8000-000000008d10','00000000-0000-4000-8000-000000008d01','00000000-0000-4000-8000-000000008d40','store_ban',3,4);
