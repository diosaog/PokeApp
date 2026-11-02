"""Rollback-only, synthetic historical-death acceptance for migration 075.

The caller supplies an isolated Supabase-shaped PostgreSQL cluster. No remote
configuration, owner save or production purchase is used by this validator.
"""

import json
from pathlib import Path
import sys
from uuid import uuid4


def seed():
    sid, tid, pid, config, division, day1, day2, day3 = (str(uuid4()) for _ in range(8))
    entities = [str(uuid4()) for _ in range(9)]
    entity_sql = ",".join(f"'{e}'::uuid" for e in entities)
    sql = f"""
begin;
insert into public.trainers(id,display_name,slug,is_admin,auth_user_id)
 values('{tid}','075 death fixture','075-death-{tid}',true,gen_random_uuid());
insert into public.seasons(id,name,status,started_at,created_by_trainer_id)
 values('{sid}','075 death history','active',now(),'{tid}');
insert into public.season_players(id,season_id,trainer_id,status,dead_box_number)
 values('{pid}','{sid}','{tid}','active',7);
insert into public.season_player_stats(season_player_id,season_id,trainer_id)
 values('{pid}','{sid}','{tid}') on conflict do nothing;
insert into public.season_admin_state(season_id) values('{sid}');
insert into public.season_config_versions(id,season_id,version_number,name,effective_from_matchday,total_matchdays,
 division_count,division_sizes,scoring_json,coin_rewards_json,rules_json)
 values('{config}','{sid}',1,'075 fixture',1,4,1,'{{"A":1}}','{{"1":0}}','{{"1":4}}',
 '{{"team_lock_required":false,"last_b_gets_steal":false}}');
insert into public.divisions(id,season_id,code,name,tier_order) values('{division}','{sid}','A','A',1);
insert into public.division_memberships(season_id,season_player_id,division_id,effective_from_matchday_number)
 values('{sid}','{pid}','{division}',1);
insert into public.matchdays(id,season_id,number,season_config_version_id)
 values('{day1}','{sid}',1,'{config}'),('{day2}','{sid}',2,'{config}'),('{day3}','{sid}',3,'{config}');
update public.seasons set current_matchday_id='{day1}' where id='{sid}';
insert into public.pokemon_entities(id,season_id,owner_trainer_id,identity_status,identity_schema_version,candidate_key,initial_evidence)
 select e,'{sid}','{tid}','unambiguous',1,lpad(n::text,64,'0'),jsonb_build_object('fixture',n)
 from unnest(array[{entity_sql}]) with ordinality x(e,n);
create or replace function pg_temp.observe(dead integer[], incomplete boolean default false) returns uuid
language plpgsql as $observe$
declare ids uuid[]=array[{entity_sql}]; previous public.pokemon_identity_revisions;
 save_id uuid=gen_random_uuid(); parsed_id uuid=gen_random_uuid(); revision_id uuid=gen_random_uuid(); n bigint;
 hash text; payload jsonb; boxes jsonb='[]'; slots jsonb; box integer; slot integer; idx integer; mon jsonb;
begin
 select * into previous from public.pokemon_identity_revisions where season_id='{sid}' and trainer_id='{tid}' order by revision_number desc limit 1;
 n=coalesce(previous.revision_number,0)+1;hash=encode(sha256(convert_to('{sid}'||n::text,'UTF8')),'hex');
 for box in 1..8 loop
  slots='[]';
  for slot in 1..30 loop
   mon='null';
   if slot<=cardinality(ids) and ((box=7 and slot=any(dead)) or (box=1 and not slot=any(dead))) then
    mon=jsonb_build_object('species','Pikachu','nickname','Fixture '||slot,'identity_evidence',jsonb_build_object('fixture',slot));
   end if;
   if not (incomplete and box=7 and slot=30) then
    slots=slots||jsonb_build_array(jsonb_build_object('slot_number',slot,'pokemon',mon));
   end if;
  end loop;
  boxes=boxes||jsonb_build_array(jsonb_build_object('box_number',box,'slots',slots));
 end loop;
 payload=jsonb_build_object('source_hash',hash,'trainer_id','{tid}','game','X','generation',6,
  'observed_progress',jsonb_build_object('schema_version',1,'source_hash',hash,'game','X','generation',6,'progress',null),
  'party','[]'::jsonb,'boxes',boxes);
 insert into public.save_files(id,season_id,trainer_id,storage_key,original_filename,sha256,parser_status,parser_version)
 values(save_id,'{sid}','{tid}','075-fixture/'||save_id,'isolated.main',hash,'parsed','pokeapp-reader/3;pkhex/24.11.11');
 insert into public.parsed_saves(id,save_file_id,parser_version,payload)
 values(parsed_id,save_id,'pokeapp-reader/3;pkhex/24.11.11',payload);
 insert into public.pokemon_identity_revisions(id,season_id,trainer_id,save_file_id,parsed_save_id,predecessor_id,
  revision_number,capture_stream_id,capture_sequence,input_signature)
 values(revision_id,'{sid}','{tid}',save_id,parsed_id,previous.id,n,coalesce(previous.capture_stream_id,gen_random_uuid()),n,hash);
 for idx in 1..cardinality(ids) loop
  insert into public.pokemon_observations(revision_id,season_id,trainer_id,save_file_id,pokemon_entity_id,source,box_number,
   slot_number,outcome,evidence,candidate_key,observation_signature)
  values(revision_id,'{sid}','{tid}',save_id,ids[idx],'box',case when idx=any(dead) then 7 else 1 end,idx,
   case when n=1 then 'NEW' else 'MATCHED' end,jsonb_build_object('fixture',idx),lpad(idx::text,64,'0'),lpad(idx::text,64,'0'));
 end loop;
 update public.season_players set current_save_file_id=save_id where id='{pid}';
 return save_id;
end $observe$;
create or replace function pg_temp.confirm(actual integer,wipes integer,segment integer,revived uuid[] default '{{}}') returns jsonb
language plpgsql as $confirm$
declare state jsonb=public.league_death_admin_state('{pid}'); req jsonb; result jsonb;
begin
 req=jsonb_build_object('operation','reconcile','request',jsonb_build_object('actor_trainer_id','{tid}',
  'season_id','{sid}','resource_id','{pid}','idempotency_key',gen_random_uuid()::text,
  'body',jsonb_build_object('actual_deaths',actual,'wipe_deaths',wipes,'segment_deaths',segment,
   'expected_revision',state->'revision','source_sha256',state->'source_sha256',
   'reason','Isolated explicit fixture confirmation','evidence','Synthetic complete source and human-reviewed event history',
   'revived_entity_ids',to_jsonb(revived))));
 result=public.api_admin_death_history(req);
 assert public.api_admin_death_history(req)->>'replayed'='true','exact receipt replay';
 return result;
end $confirm$;
-- A historical native verification receipt is synthetic fixture input here;
-- native writing itself belongs to the existing independent acceptance gates.
-- The private verifier remains inaccessible to service_role in production.
create or replace function pg_temp.normal_revive(ent uuid) returns void
language plpgsql security definer set search_path=pg_catalog,public as $revive$
declare purchase uuid=gen_random_uuid(); auth uuid=gen_random_uuid(); claim uuid=gen_random_uuid(); head public.pokemon_identity_revisions; hash text;
begin
 select * into head from public.pokemon_identity_revisions where season_id='{sid}' and trainer_id='{tid}' order by revision_number desc limit 1;
 select sha256 into hash from public.save_files where id=head.save_file_id;
 insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,status,acquisition_type)
  select purchase,'{sid}','{tid}','{pid}',id,1,6,'pending','paid' from public.shop_items where code='revivir_pokemon';
 insert into public.item_use_authorizations(id,operation_id,idempotency_key,purchase_id,season_id,trainer_id,target_pokemon_entity_id,
  save_file_id,save_sha256,identity_revision_id,claim_id,effect_code,status,observed_sha256)
 values(auth,purchase::text,purchase::text,purchase,'{sid}','{tid}',ent,head.save_file_id,hash,head.id,claim,'revive','APPLIED_VERIFIED',repeat('f',64));
 insert into public.item_use_verifications(authorization_id,claim_id,operation_id,source_sha256,result_sha256,target_pokemon_entity_id,
  identity_revision_id,native_operation_id,plan_sha256)
 values(auth,claim,purchase::text,hash,repeat('f',64),ent,head.id,gen_random_uuid(),repeat('a',64));
 perform public.api_redeem_purchase('{sid}','{tid}',purchase,ent,purchase::text,head.id);
end $revive$;
"""
    return sql, dict(sid=sid, tid=tid, pid=pid, config=config, day1=day1, day2=day2, day3=day3, entities=entities)


def validate(pg):
    prefix, v = seed()
    sql = prefix + f"""
set local role service_role;
select pg_temp.observe(array[1,2,3]);
do $$ declare x jsonb; purchase uuid; ent uuid; head uuid; before_count bigint;
begin
 x=public.league_death_totals('{v['pid']}');
 assert x->>'known'='false' and x->>'actual_deaths' is null,'unknown first history is never zero';
 assert x->>'blocking_reason'='death_history_baseline_required','explicit baseline required';
 begin
  perform public.league_freeze_death_segment('{v['sid']}','{v['day1']}','{v['tid']}');
  raise exception 'unknown progression frozen as zero';
 exception when sqlstate 'PT409' then assert sqlerrm='death_history_baseline_required',sqlerrm; end;
 assert not exists(select 1 from public.matchday_death_snapshots where matchday_id='{v['day1']}'),'failed freeze leaves no partial snapshot';
 x=pg_temp.confirm(3,0,3);
 assert x->>'known'='true' and (x->>'actual_deaths')::int=3 and (x->>'death_penalty_tenths')::int=3,'three ordinary deaths are three and -0.3';
 assert (select count(*) from public.league_death_events where season_player_id='{v['pid']}')=3,'one event per first dead identity';
 foreach ent in array array['{v['entities'][0]}'::uuid,'{v['entities'][1]}'::uuid,'{v['entities'][2]}'::uuid] loop
  perform pg_temp.normal_revive(ent);
 end loop;
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=3,'applied normal revives do not add deaths';
 perform pg_temp.observe('{{}}');
 x=public.league_death_totals('{v['pid']}');
 assert (x->>'actual_deaths')::int=3 and (x->>'death_penalty_tenths')::int=3,'three revived deaths retain -0.3 after box emptied';
 perform pg_temp.observe(array[1]);
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=4,'new death after authorized normal revival is a new event';
 perform pg_temp.observe(array[1]);
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=4,'same dead identity across saves deduplicates';
 perform pg_temp.observe('{{}}'); perform pg_temp.observe(array[1]);
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=4,'moving out and back without another revive is not a death';
 perform pg_temp.observe('{{}}');
 begin
  perform pg_temp.confirm(0,0,0);
  raise exception 'recorded deaths erased by lower baseline';
 exception when sqlstate 'PT409' then assert sqlerrm='death_history_inconsistent',sqlerrm; end;
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=4,'baseline cannot erase actual recorded deaths';
 before_count=(select count(*) from public.league_death_resolutions where season_player_id='{v['pid']}');
 begin
  perform public.api_admin_death_history(jsonb_build_object('operation','reconcile','request',jsonb_build_object(
    'actor_trainer_id','{v['tid']}','season_id','{v['sid']}','resource_id','{v['pid']}',
    'idempotency_key','bad-cas','body',jsonb_build_object('actual_deaths',4,'wipe_deaths',0,'segment_deaths',4,
    'expected_revision',0,'source_sha256',repeat('a',64),'reason','test','evidence','test'))));
  raise exception 'stale revision accepted';
 exception when sqlstate 'PT409' then assert sqlerrm='death_history_revision_conflict',sqlerrm; end;
 assert (select count(*) from public.league_death_resolutions where season_player_id='{v['pid']}')=before_count,'failed reconciliation leaves no partial record';
end $$;
rollback;
"""
    pg.sql(sql)
    first = "ordinary + three actual comodin revivals, repeated death, movement/replay and CAS rollback"

    prefix, v = seed()
    ids = ",".join(f"'{e}'::uuid" for e in v["entities"][:5])
    pg.sql(prefix + f"""
set local role service_role;
select pg_temp.observe(array[1,2,3,4,5]);
update public.season_player_stats set revived_after_wipe=5,metadata='{{"wipe_revision":1}}' where season_player_id='{v['pid']}';
select pg_temp.confirm(5,5,5);
do $$ declare x jsonb; frozen jsonb;
begin
 x=public.league_death_totals('{v['pid']}');
 assert (x->>'actual_deaths')::int=5 and (x->>'death_penalty_tenths')::int=10,'five wipe deaths are five actual and -1.0, no ordinary duplicate';
 perform public.league_freeze_death_segment('{v['sid']}','{v['day1']}','{v['tid']}');
 frozen=public.league_death_snapshot('{v['pid']}','{v['day1']}');
 update public.matchdays set status='open',opened_at=clock_timestamp() where id='{v['day1']}';
 perform pg_temp.observe('{{}}');
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=5,'wipe revival cannot erase recorded deaths';
 perform pg_temp.confirm(5,5,5,array[{ids}]);
 perform pg_temp.observe(array[1]);
 x=public.league_death_totals('{v['pid']}');
 assert (x->>'actual_deaths')::int=6 and (x->>'death_penalty_tenths')::int=11,'audited wipe revival rearms one new ordinary death';
 assert public.league_death_snapshot('{v['pid']}','{v['day1']}')=frozen,'later revival and battle-phase death leave frozen segment unchanged';
 update public.matchdays set status='scheduled' where id='{v['day1']}';
 perform public.league_freeze_death_segment('{v['sid']}','{v['day1']}','{v['tid']}');
 assert public.league_death_snapshot('{v['pid']}','{v['day1']}')=frozen,'cancel/reopen reuses first immutable snapshot';
 begin
  update public.matchday_death_snapshots set segment_deaths=0 where matchday_id='{v['day1']}';
  raise exception 'snapshot mutated';
 exception when insufficient_privilege then null; when sqlstate 'PT409' then null; end;
 update public.season_player_stats set revived_after_wipe=4,metadata='{{"wipe_revision":2}}' where season_player_id='{v['pid']}';
 assert public.league_death_totals('{v['pid']}')->>'blocking_reason'='death_history_wipe_reconciliation_required','counter corrections require explicit reconciliation';
 perform pg_temp.observe(array[1,2]);
 perform pg_temp.confirm(7,4,5);
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=7,'a new death during cancelled battle editing stays outside the frozen progression segment';
 assert public.league_death_snapshot('{v['pid']}','{v['day1']}')=frozen,'counter correction never mutates historical snapshot';
end $$;
rollback;
""")
    second = "wipe five=5/-1.0, audited rearm, immutable open snapshot, reopen and revised-counter uncertainty"

    prefix, v = seed()
    pg.sql(prefix + f"""
set local role service_role;
select pg_temp.observe(array[1]); select pg_temp.confirm(1,0,1);
select public.league_freeze_death_segment('{v['sid']}','{v['day1']}','{v['tid']}');
update public.matchdays set status='open',opened_at=clock_timestamp() where id='{v['day1']}';
update public.matchdays set status='closed',closed_at=clock_timestamp() where id='{v['day1']}';
update public.seasons set current_matchday_id='{v['day2']}' where id='{v['sid']}';
select pg_temp.observe(array[1,2,3,4,5,6,7]);
select public.league_freeze_death_segment('{v['sid']}','{v['day2']}','{v['tid']}');
do $$ declare x jsonb;
begin
 assert (public.league_death_snapshot('{v['pid']}','{v['day1']}')->>'segment_deaths')::int=1,'J1 deaths=1';
 assert (public.league_death_snapshot('{v['pid']}','{v['day2']}')->>'segment_deaths')::int=6,'J2 deaths=6';
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=7,'GENERAL historical deaths=7';
 update public.matchdays set status='open',opened_at=clock_timestamp() where id='{v['day2']}';
 perform pg_temp.observe(array[1,2,3,4,5,6,7,8]);
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=8,'battle-phase death is counted cumulatively';
 update public.matchdays set status='closed',closed_at=clock_timestamp() where id='{v['day2']}';
 update public.seasons set current_matchday_id='{v['day3']}' where id='{v['sid']}';
 perform pg_temp.observe(array[1,2,3,4,5,6,7,8,9]);
 perform public.league_freeze_death_segment('{v['sid']}','{v['day3']}','{v['tid']}');
 assert (public.league_death_snapshot('{v['pid']}','{v['day3']}')->>'segment_deaths')::int=1,'previous battle-phase death is not moved to next progression';
 perform pg_temp.observe('{{}}',true);
 x=public.league_death_totals('{v['pid']}');
 assert x->>'known'='false' and x->>'actual_deaths' is null,'incomplete box never becomes zero';
 assert (select count(*) from public.league_death_events where season_player_id='{v['pid']}')=9,'incomplete resync cannot erase events';
 assert (public.league_death_snapshot('{v['pid']}','{v['day1']}')->>'segment_deaths')::int=1,'old J1 remains stable';
 update public.season_players set dead_box_number=8 where id='{v['pid']}';
 assert public.league_death_totals('{v['pid']}')->>'blocking_reason'='death_history_dead_box_changed','changing boxes requires audited reconciliation';
 assert (select count(*) from public.league_death_events where season_player_id='{v['pid']}')=9,'changing boxes never erases deaths';
 update public.season_player_stats set metadata='{{"wipe_revision":"corrupt"}}' where season_player_id='{v['pid']}';
 assert public.league_death_totals('{v['pid']}')->>'blocking_reason'='death_history_wipe_state_unavailable','corrupt counter metadata is explicit unknown rather than a fabricated zero';
 assert not has_table_privilege('anon','public.league_death_events','select') and not has_table_privilege('authenticated','public.matchday_death_snapshots','select'),'private ledger has no direct browser reads';
end $$;
rollback;
""")
    third = "J1=1/J2=6/GENERAL=7, participant Box7, phase boundaries, partial-source unknown and private tables"
    # Exercise the actual registration transport and Python-generated identity
    # plans, rather than only the lower-level synthetic pointer fixture above.
    from app.application.save_ingestion import registration_request
    from app.save_parser.models import ObservedSave
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
    from test_phase074_training import observation, VERSION

    prefix, v = seed()
    alive = observation()
    dead_raw = alive.model_dump(mode="json")
    dead_raw["boxes"][6]["slots"][0] = dead_raw["party"][0]
    dead_raw["party"][0] = None
    dead = ObservedSave.model_validate_json(json.dumps(dead_raw))
    initial = registration_request(v["sid"], v["tid"], "a" * 64, None, alive, VERSION, {"head": None, "entities": []})
    binding = initial["identity_plan"]["bindings"][0]
    context = {"head": {"id": str(uuid4()), "capture_stream_id": initial["identity_plan"]["capture_stream_id"], "capture_sequence": 1},
               "entities": [{"id": binding["pokemon_entity_id"], "identity_status": "unambiguous", "initial_evidence": binding["evidence"]}]}
    next_save = registration_request(v["sid"], v["tid"], "b" * 64, initial["save_id"], dead, VERSION, context)
    literal = lambda obj: "'" + json.dumps(obj).replace("'", "''") + "'::jsonb"
    pg.sql(prefix + f"""
delete from public.pokemon_entities where season_id='{v['sid']}';
set local role service_role;
select public.api_register_save({literal(initial)}||jsonb_build_object('operation','register'));
select pg_temp.confirm(0,0,0);
do $$ declare request jsonb={literal(next_save)}; head uuid; result jsonb; before_count bigint;
begin
 select id into head from public.pokemon_identity_revisions where season_id='{v['sid']}' and trainer_id='{v['tid']}' order by revision_number desc limit 1;
 request=jsonb_set(request,'{{identity_plan,expected_predecessor_id}}',to_jsonb(head));
 result=public.api_register_save(request||jsonb_build_object('operation','register'));
 assert result->>'is_current'='true','actual registration advances pointer after identity completion';
 result=public.league_death_totals('{v['pid']}');
 assert result->>'known'='true' and (result->>'actual_deaths')::int=1,'actual API registration automatically records complete death evidence';
 assert result->>'source_save_id'='{next_save['save_id']}','ledger source is the exact accepted save';
 assert (select count(*) from public.league_death_events where season_player_id='{v['pid']}')=1,'real registry emits one event';
 result=public.api_register_save({literal(initial)}||jsonb_build_object('operation','register'));
 assert result->>'is_current'='false','historical save replay cannot rewind current pointer';
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=1,'historical source replay neither erases nor duplicates deaths';
end $$;
rollback;
""")
    fourth = "real Python identity plans + api_register_save ordering, automatic death capture and historical save replay"
    return [first, second, third, fourth]
