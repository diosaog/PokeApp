-- Disposable fixtures only. Run on an empty local validation database.
create schema pokeapp_team_lock_test;
grant usage on schema pokeapp_team_lock_test to anon, authenticated, service_role;

insert into public.trainers (id, display_name, slug, auth_user_id) values
 ('00000000-0000-4000-8000-000000008c01', 'Team Lock A', 'team_lock_fixture_a', '00000000-0000-4000-8000-000000008ca1'),
 ('00000000-0000-4000-8000-000000008c04', 'Team Lock B', 'team_lock_fixture_b', '00000000-0000-4000-8000-000000008ca2');
insert into public.seasons (id, name, status, started_at) values
 ('00000000-0000-4000-8000-000000008c10', 'Team Lock Fixture', 'active', now());
insert into public.season_players (id, season_id, trainer_id) values
 ('00000000-0000-4000-8000-000000008c02', '00000000-0000-4000-8000-000000008c10', '00000000-0000-4000-8000-000000008c01'),
 ('00000000-0000-4000-8000-000000008c03', '00000000-0000-4000-8000-000000008c10', '00000000-0000-4000-8000-000000008c04');
insert into public.season_config_versions (
 id, season_id, version_number, name, effective_from_matchday, total_matchdays, division_count
) values ('00000000-0000-4000-8000-000000008c11', '00000000-0000-4000-8000-000000008c10', 1, 'Fixture', 1, 4, 2);
insert into public.matchdays (id, season_id, number, season_config_version_id) values
 ('00000000-0000-4000-8000-000000008c12', '00000000-0000-4000-8000-000000008c10', 1, '00000000-0000-4000-8000-000000008c11');
insert into public.save_files (id, season_id, trainer_id, storage_key, original_filename, sha256, parser_status, parser_version) values
 ('00000000-0000-4000-8000-000000008c20', '00000000-0000-4000-8000-000000008c10', '00000000-0000-4000-8000-000000008c01', 'fixture/a', 'a.sav', repeat('a',64), 'parsed', 'fixture'),
 ('00000000-0000-4000-8000-000000008c21', '00000000-0000-4000-8000-000000008c10', '00000000-0000-4000-8000-000000008c01', 'fixture/b', 'b.sav', repeat('b',64), 'parsed', 'fixture');
insert into public.parsed_saves (id, save_file_id, parser_version, payload)
select '00000000-0000-4000-8000-000000008c30', '00000000-0000-4000-8000-000000008c20', 'fixture',
 jsonb_build_object('party', jsonb_agg(jsonb_build_object('species','Milotic','ability','Competitive','ivs',jsonb_build_object('hp',31))))
from generate_series(1,6);
insert into public.parsed_saves (id, save_file_id, parser_version, payload)
select '00000000-0000-4000-8000-000000008c31', '00000000-0000-4000-8000-000000008c21', 'fixture',
 jsonb_build_object('party', jsonb_agg(jsonb_build_object('species','Crobat','ability','Inner Focus','ivs',jsonb_build_object('hp',30))))
from generate_series(1,6);

create table pokeapp_team_lock_test.request as
select sf.season_id, '00000000-0000-4000-8000-000000008c12'::uuid as matchday_id, sf.trainer_id,
 '00000000-0000-4000-8000-000000008c02'::uuid as season_player_id,
 sf.id as save_file_id, sf.sha256 as save_sha256, ps.id as parsed_save_id, ps.payload as parsed_payload,
 (select jsonb_agg(jsonb_build_object('species', mon->>'species')) from jsonb_array_elements(ps.payload->'party') mon) as public_team_snapshot,
 ps.payload->'party' as private_team_snapshot
from public.save_files sf join public.parsed_saves ps on ps.save_file_id=sf.id
where sf.id='00000000-0000-4000-8000-000000008c20';
grant select on pokeapp_team_lock_test.request to anon, authenticated, service_role;

create function pokeapp_team_lock_test.run() returns setof public.team_locks
language sql security invoker set search_path = '' as $$
 select result.* from pokeapp_team_lock_test.request r,
 lateral public.api_upsert_team_lock(
   r.season_id, r.matchday_id, r.trainer_id, r.season_player_id, r.save_file_id, r.save_sha256,
   r.parsed_save_id, r.parsed_payload, r.public_team_snapshot, r.private_team_snapshot
 ) result;
$$;

create function pokeapp_team_lock_test.assert_true(value boolean, label text) returns void
language plpgsql as $$ begin
 if value is distinct from true then raise exception 'Team Lock check failed: %', label; end if;
end; $$;

create function pokeapp_team_lock_test.expect_failure(statement text, expected_code text) returns void
language plpgsql security invoker as $$ begin
 execute statement;
 raise exception 'Expected SQLSTATE % was not raised', expected_code;
exception when others then
 if sqlstate <> expected_code then raise; end if;
end; $$;
