-- Local transactional fixture only. No remote runner, no retained rows/DDL.
begin;
create function pg_temp.check_true(ok boolean,label text) returns void language plpgsql as $$
begin if not coalesce(ok,false) then raise exception 'GENERAL assertion: %',label; end if; end $$;

do $$
declare fn regprocedure;
begin
  foreach fn in array array['public.league_observed_dead_count(jsonb)'::regprocedure,'public.league_general_read(uuid)'::regprocedure] loop
    perform pg_temp.check_true(not has_function_privilege('anon',fn,'execute'),'anon execute');
    perform pg_temp.check_true(not has_function_privilege('authenticated',fn,'execute'),'browser execute');
    perform pg_temp.check_true(has_function_privilege('service_role',fn,'execute'),'service execute');
    perform pg_temp.check_true((select not prosecdef and proconfig @> array['search_path=pg_catalog, public'] from pg_proc where oid=fn),'invoker/fixed search_path');
  end loop;
end $$;

set local role service_role;
do $$
declare sid uuid=gen_random_uuid(); tid uuid=gen_random_uuid(); other uuid=gen_random_uuid();
  pid uuid=gen_random_uuid(); other_pid uuid=gen_random_uuid(); cid uuid=gen_random_uuid();
  d1 uuid=gen_random_uuid(); d2 uuid=gen_random_uuid(); d3 uuid=gen_random_uuid();
  saved uuid=gen_random_uuid(); parsed uuid=gen_random_uuid(); row jsonb; data jsonb; payload jsonb; original jsonb; bad jsonb;
begin
  insert into public.trainers(id,display_name,slug,globally_enabled) values
    (tid,'Zeta','phase10_5b_zeta',false),(other,'Alfa','phase10_5b_alfa',true);
  insert into public.seasons(id,name) values(sid,'phase10_5b');
  insert into public.season_players(id,season_id,trainer_id,status) values
    (pid,sid,tid,'retired'),(other_pid,sid,other,'active');
  data=public.league_general_read(sid);
  perform pg_temp.check_true(jsonb_array_length(data->'rows')=2 and data->'days'='[]'::jsonb,'no days, full roster');
  perform pg_temp.check_true(data#>>'{rows,0,display_name}'='Alfa' and data#>>'{rows,0,total_points}'='0','equal points presentation order');
  perform pg_temp.check_true(data#>>'{rows,1,dead_count_source}'='unknown' and data#>'{rows,1,dead_count}'='null'::jsonb,'unknown is not zero');
  perform pg_temp.check_true(data#>>'{rows,1,status}'='retired','disabled historical trainer retained');
  perform pg_temp.check_true(data#>>'{rows,0,coin_balance}'='0','empty ledger zero');
  insert into public.coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type) values
    (sid,tid,pid,-2147483647,'penalty'),(sid,tid,pid,-2147483647,'penalty'),(sid,other,other_pid,15,'admin_adjustment');
  perform pg_temp.check_true(public.league_general_read(sid)#>>'{rows,1,coin_balance}'='-4294967294','exact debt exceeds int32');
  insert into public.season_config_versions(id,season_id,version_number,name,effective_from_matchday,total_matchdays,division_count)
    values(cid,sid,1,'fixture',1,3,2);
  insert into public.matchdays(id,season_id,number,season_config_version_id) values(d1,sid,1,cid),(d2,sid,2,cid),(d3,sid,3,cid);
  update public.seasons set current_matchday_id=d1 where id=sid;
  perform pg_temp.check_true(jsonb_array_length(public.league_general_read(sid)->'days')=1,'current J1 without future scheduled days');
  update public.matchdays set status='closed',closed_at=now() where id=d1;
  insert into public.matchday_snapshots(season_id,matchday_id,config_version_id,snapshot_schema_version,closed_at,snapshot)
    values(sid,d1,cid,2,now(),jsonb_build_object('schema_version',2,'standings',jsonb_build_array(
      jsonb_build_object('trainer_id',pid,'points_awarded',10,'penalties',jsonb_build_object('points_reduction','1.123456789','dead_points_penalty','0.2')),
      jsonb_build_object('trainer_id',other_pid,'points_awarded',5,'penalties',jsonb_build_object('points_reduction','9007199254741000.123456789')))));
  update public.seasons set current_matchday_id=d2 where id=sid;
  data=public.league_general_read(sid);
  perform pg_temp.check_true(jsonb_array_length(data->'days')=2,'closed J1 plus current J2');
  perform pg_temp.check_true(data#>>'{rows,0,display_name}'='Zeta' and data#>>'{rows,0,total_points}'='8.676543211','numeric points order before text');
  perform pg_temp.check_true(data#>>'{rows,1,total_points}'='-9007199254740995.123456789','exact negative beyond JS safe precision');
  update public.matchdays set status='closed',closed_at=now() where id=d2;
  insert into public.matchday_snapshots(season_id,matchday_id,config_version_id,snapshot_schema_version,closed_at,snapshot)
    values(sid,d2,cid,2,now(),jsonb_build_object('schema_version',2,'standings',jsonb_build_array(
      jsonb_build_object('trainer_id',pid,'points_awarded',7,'penalties',jsonb_build_object('points_reduction','1.123456789','dead_points_penalty','1.4')))));
  data=public.league_general_read(sid);
  perform pg_temp.check_true(data#>>'{rows,0,total_points}'='14.476543211','accumulated awards minus latest penalties once');
  perform pg_temp.check_true(data#>>'{rows,0,points_source_matchday_id}'=d2::text,'last official source');
  perform pg_temp.check_true(jsonb_array_length(data->'days')=2,'final closed, no future tab');

  select jsonb_build_object('boxes',jsonb_build_array(jsonb_build_object('box_number',8,'slots',jsonb_agg(
    jsonb_build_object('slot_number',n,'pokemon',null) order by n)))) into payload from generate_series(1,30) n;
  original=payload;
  insert into public.save_files(id,season_id,trainer_id,storage_key,original_filename,sha256,parser_status,parser_version)
    values(saved,sid,tid,'phase10_5b_private','private.sav',repeat('a',64),'parsed','phase10_5b');
  insert into public.parsed_saves(id,save_file_id,parser_version,payload) values(parsed,saved,'phase10_5b',payload);
  update public.season_players set current_save_file_id=saved where id=pid;
  perform pg_temp.check_true(public.league_general_read(sid)#>>'{rows,0,dead_count_source}'='unknown','unreconciled save');
  insert into public.pokemon_identity_revisions(season_id,trainer_id,save_file_id,parsed_save_id,revision_number,capture_stream_id,capture_sequence,input_signature)
    values(sid,tid,saved,parsed,1,gen_random_uuid(),1,repeat('b',64));
  perform pg_temp.check_true(public.league_general_read(sid)#>>'{rows,0,dead_count}'='0','verified empty box');
  select jsonb_build_object('boxes',jsonb_build_array(jsonb_build_object('box_number',8,'slots',jsonb_agg(
    jsonb_build_object('slot_number',n,'pokemon',case when n<=5 then jsonb_build_object('species','Pikachu','ability','SECRET') end) order by n)))) into payload from generate_series(1,30) n;
  original=payload;
  update public.parsed_saves set payload=original where id=parsed;
  data=public.league_general_read(sid);
  perform pg_temp.check_true(data#>>'{rows,0,dead_count}'='5' and data#>>'{rows,0,dead_count_source}'='observed_current_save','five visible occupants');
  perform pg_temp.check_true(data#>>'{rows,0,total_points}'='14.476543211','save does not rewrite official points');
  perform pg_temp.check_true(data::text not like '%SECRET%' and data::text not like '%storage%' and data::text not like '%pokemon_entity%' and data::text not like '%auth_user%','no private content');

  foreach bad in array array[
    '{}'::jsonb,'{"boxes":null}'::jsonb,'{"boxes":[]}'::jsonb,
    jsonb_set(original,'{boxes,0,slots}','[]'),
    jsonb_set(original,'{boxes,0,slots,29,slot_number}','1'),
    original #- '{boxes,0,slots,0,pokemon}',
    jsonb_set(original,'{boxes,0,slots,0,pokemon}','{}'),
    original||jsonb_build_object('trainer_id',other),
    original||jsonb_build_object('save_record_id',gen_random_uuid()),
    original||jsonb_build_object('source_hash',repeat('f',64))
  ] loop
    update public.parsed_saves set payload=bad where id=parsed;
    perform pg_temp.check_true(public.league_general_read(sid)#>>'{rows,0,dead_count_source}'='unknown','invalid/incomplete/foreign payload');
  end loop;
  update public.parsed_saves set payload=original,parser_version='mismatch' where id=parsed;
  perform pg_temp.check_true(public.league_general_read(sid)#>>'{rows,0,dead_count_source}'='unknown','parser version mismatch');
  update public.parsed_saves set parser_version='phase10_5b' where id=parsed;
  update public.save_files set deleted_at=now() where id=saved;
  perform pg_temp.check_true(public.league_general_read(sid)#>>'{rows,0,dead_count_source}'='unknown','deleted save');
  update public.save_files set deleted_at=null,parser_status='failed' where id=saved;
  perform pg_temp.check_true(public.league_general_read(sid)#>>'{rows,0,dead_count_source}'='unknown','failed parser');

  foreach bad in array array['{"schema_version":1,"standings":[]}'::jsonb,'{"schema_version":2}'::jsonb,'{"schema_version":2,"standings":{}}'::jsonb,
    '{"schema_version":2,"standings":[{}]}'::jsonb] loop
    update public.matchday_snapshots set snapshot=bad where matchday_id=d2;
    begin perform public.league_general_read(sid); raise exception 'expected unsupported history';
    exception when sqlstate 'PT503' then null; end;
  end loop;
  update public.matchday_snapshots set snapshot='{"schema_version":2,"standings":[]}' where matchday_id=d2;
  perform public.league_general_read(sid); -- empty valid standing array is supported
  update public.seasons set status='archived',archived_at=now() where id=sid;
  perform pg_temp.check_true(public.league_general_read(sid) is not null,'archived history readable');
  update public.seasons set status='discarded',discarded_at=now() where id=sid;
  perform pg_temp.check_true(public.league_general_read(sid) is null,'discarded invisible');
  perform pg_temp.check_true(public.league_general_read(gen_random_uuid()) is null,'unknown season');
  raise notice 'GENERAL data, decimals, lifecycle, dead provenance and privacy PASS';
end $$;
rollback;
