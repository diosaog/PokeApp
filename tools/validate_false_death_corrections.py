"""Isolated SQL acceptance for explicit false-death event corrections (077).

Synthetic complete parsed observations only. No production credentials, native
saves or real purchases. validate() rolls back every fixture; concurrency is
restricted to a dedicated empty disposable loopback cluster.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from threading import Barrier
import argparse
import json
import os

import psycopg

from tools.validate_phase075_deaths import seed


def fixture():
    prefix, v = seed()
    full = ",".join(f"'{e}'::uuid" for e in v["entities"])
    v["entities"] = v["entities"][:5]
    prefix = prefix.replace(full, ",".join(f"'{e}'::uuid" for e in v["entities"]))
    original = """   if slot<=cardinality(ids) and ((box=7 and slot=any(dead)) or (box=1 and not slot=any(dead))) then
    mon=jsonb_build_object('species','Pikachu','nickname','Fixture '||slot,'identity_evidence',jsonb_build_object('fixture',slot));
   end if;"""
    corrected = """   idx=null;
   if box=7 then idx=dead[slot];
   elsif box=1 then
    select candidate.entity_number into idx from generate_series(1,cardinality(ids)) candidate(entity_number)
     where not candidate.entity_number=any(dead)
       and (case when candidate.entity_number=1 and n>1 then 8 else candidate.entity_number end)=slot;
   end if;
   if idx is not null then
    mon=jsonb_build_object('species',case when idx=1 then 'Pokemon #443' else 'Pikachu' end,
      'nickname',case when idx=1 then 'Gible false-placement fixture' else 'Fixture '||idx end,
      'identity_evidence',jsonb_build_object('fixture',idx));
   end if;"""
    assert original in prefix
    prefix = prefix.replace(original, corrected)
    old = "case when idx=any(dead) then 7 else 1 end,idx,"
    assert old in prefix
    prefix = prefix.replace(old, "case when idx=any(dead) then 7 else 1 end,case when idx=any(dead) then array_position(dead,idx) when idx=1 and n>1 then 8 else idx end,")
    # Copied active production seasons are changed only inside this fixture's
    # isolated transaction; validate() always rolls the entire transaction back.
    prefix = prefix.replace("begin;", "begin;\nupdate public.seasons set status='draft' where status='active';", 1)
    prefix += f"""
update public.seasons set current_matchday_id=null where id='{v['sid']}';
delete from public.matchdays where season_id='{v['sid']}';
set local role service_role;
select pg_temp.observe(array[1]);
select pg_temp.confirm(1,0,1);
select pg_temp.observe(array[2,3,4,5]);
create or replace function pg_temp.correction(ids uuid[] default null) returns jsonb
language plpgsql as $request$
declare state jsonb=public.league_death_admin_state('{v['pid']}'); event uuid;
begin
 select id into event from public.league_death_events where season_player_id='{v['pid']}' and pokemon_entity_id='{v['entities'][0]}';
 return jsonb_build_object('operation','reconcile','request',jsonb_build_object(
   'actor_trainer_id','{v['tid']}','season_id','{v['sid']}','resource_id','{v['pid']}',
   'idempotency_key',gen_random_uuid()::text,'body',jsonb_build_object(
     'actual_deaths',4,'wipe_deaths',0,'segment_deaths',4,
     'expected_revision',state->'revision','source_sha256',state->'source_sha256',
     'reason','Explicit owner-confirmed false Box7 placement',
     'evidence','Same Gible identity: first Box7/1, later Box1/8; owner confirms it never died',
     'invalidated_event_ids',to_jsonb(coalesce(ids,array[event])))));
end $request$;
do $$ declare general jsonb; begin
 general=public.league_general_read('{v['sid']}');
 assert (general#>>'{{rows,0,dead_count}}')::int=4,'production reproduction has four current occupants';
 assert (general#>>'{{rows,0,historical_deaths}}')::int=5,'production reproduction has five distinct raw events';
 assert (general#>>'{{rows,0,total_points}}')::numeric=-0.5,'production reproduction is exactly -0.5';
 assert (select count(distinct pokemon_entity_id)=5 from public.league_death_events where season_player_id='{v['pid']}'),'no duplicate entity caused the extra tenth';
 assert exists(select 1 from public.pokemon_observations where pokemon_entity_id='{v['entities'][0]}'
   and revision_id=(public.league_death_totals('{v['pid']}')->>'identity_revision_id')::uuid
   and source='box' and box_number=1 and slot_number=8 and outcome='MATCHED'),'same Gible moved to Box1/8';
end $$;
"""
    return prefix, v


def validate_red(pg):
    prefix, v = fixture()
    pg.sql(prefix + f"""
do $$ begin
 begin
  perform pg_temp.confirm(4,0,4);
  raise exception 'RED reproduction unexpectedly allowed 075 to correct a false raw event';
 exception when sqlstate 'PT409' then
  assert sqlerrm='death_history_inconsistent',sqlerrm;
 end;
 begin
  perform public.api_admin_death_history(pg_temp.correction());
  raise exception 'RED reproduction unexpectedly supports an event correction before077';
 exception when sqlstate 'PT422' then
  assert sqlerrm='death_history_evidence_required',sqlerrm;
 end;
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=5,'both denied operations preserve the original raw-history floor';
end $$;
rollback;
""")
    return "RED: exact four-box/five-history/-0.5 fixture;075 blocks actual4 with409 death_history_inconsistent; explicit event correction unsupported422"


def validate(pg):
    prefix, v = fixture()
    pg.sql(prefix + f"""
do $$ declare request jsonb=pg_temp.correction(); result jsonb; general jsonb; original_event uuid;
 raw_before text; saves_before text; parsed_before text; observations_before text; coins_before text; snapshots_before text;
begin
 select id into original_event from public.league_death_events where season_player_id='{v['pid']}' and pokemon_entity_id='{v['entities'][0]}';
 request=jsonb_set(request,'{{request,body,invalidated_event_ids}}',to_jsonb(array[upper(original_event::text)]));
 select md5(jsonb_agg(to_jsonb(e) order by e.id)::text) into raw_before from public.league_death_events e where season_player_id='{v['pid']}';
 select md5(jsonb_agg(to_jsonb(s) order by s.id)::text) into saves_before from public.save_files s where season_id='{v['sid']}';
 select md5(jsonb_agg(to_jsonb(p) order by p.id)::text) into parsed_before from public.parsed_saves p join public.save_files s on s.id=p.save_file_id where s.season_id='{v['sid']}';
 select md5(jsonb_agg(to_jsonb(o) order by o.id)::text) into observations_before from public.pokemon_observations o where season_id='{v['sid']}';
 select coalesce(md5(jsonb_agg(to_jsonb(c) order by c.id)::text),'-') into coins_before from public.coin_transactions c where season_id='{v['sid']}';
 select coalesce(md5(jsonb_agg(to_jsonb(s) order by s.id)::text),'-') into snapshots_before from public.matchday_death_snapshots s where season_id='{v['sid']}';
 result=public.api_admin_death_history(request);
 assert result->>'known'='true' and (result->>'actual_deaths')::int=4 and (result->>'segment_deaths')::int=4,'explicit correction removes just the false count';
 assert (result->>'raw_recorded_deaths')::int=5 and (result->>'recorded_deaths')::int=4,'five immutable raw rows, four counted events';
 assert result->'invalidated_event_ids'=to_jsonb(array[original_event]),'exact invalidated event retained in admin provenance';
 assert (public.api_admin_death_history(request)->>'replayed')::boolean,'same confirmation replays';
 assert public.api_admin_death_history(request)->>'resolution_id'=result->>'resolution_id','same resolution replay';
 assert (select count(*)=2 from public.league_death_resolutions where season_player_id='{v['pid']}'),'one original baseline plus one correction';
 assert (select count(*)=4 from public.league_effective_death_events('{v['pid']}')),'effective helper excludes only explicitly invalidated event';
 assert not exists(select 1 from jsonb_array_elements(result->'observed_dead_entities') e
  where e->>'pokemon_entity_id'='{v['entities'][0]}' and (e->>'has_recorded_death')::boolean),'Gible false event is not a counted death';
 general=public.league_general_read('{v['sid']}');
 assert (general#>>'{{rows,0,total_points}}')::numeric=-0.4 and (general#>>'{{rows,0,dead_count}}')::int=4,'after explicit correction exactly four ordinary deaths cost -0.4';
 assert raw_before=(select md5(jsonb_agg(to_jsonb(e) order by e.id)::text) from public.league_death_events e where season_player_id='{v['pid']}'),'raw source events byte-equivalent';
 assert saves_before=(select md5(jsonb_agg(to_jsonb(s) order by s.id)::text) from public.save_files s where season_id='{v['sid']}'),'save records untouched';
 assert parsed_before=(select md5(jsonb_agg(to_jsonb(p) order by p.id)::text) from public.parsed_saves p join public.save_files s on s.id=p.save_file_id where s.season_id='{v['sid']}'),'parsed saves untouched';
 assert observations_before=(select md5(jsonb_agg(to_jsonb(o) order by o.id)::text) from public.pokemon_observations o where season_id='{v['sid']}'),'identity observations untouched';
 assert coins_before=(select coalesce(md5(jsonb_agg(to_jsonb(c) order by c.id)::text),'-') from public.coin_transactions c where season_id='{v['sid']}'),'coin ledger untouched';
 assert snapshots_before=(select coalesce(md5(jsonb_agg(to_jsonb(s) order by s.id)::text),'-') from public.matchday_death_snapshots s where season_id='{v['sid']}'),'existing snapshots untouched';
 -- A false raw event cannot masquerade as a genuine death eligible for a
 -- later revival. That would overwrite the fresh correction boundary.
 begin
  perform pg_temp.confirm(4,0,4,array['{v['entities'][0]}'::uuid]);
  raise exception 'invalidated raw event was accepted as a real revival';
 exception when sqlstate 'PT409' then assert sqlerrm='death_history_inconsistent',sqlerrm; end;
 -- Subsequent normal confirmations must keep the correction, even when the
 -- optional new field is omitted as it was by every old client.
 perform pg_temp.confirm(4,0,4);
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=4,'legacy-shaped reconciliation never resurrects a false event';
 insert into public.matchdays(id,season_id,number,season_config_version_id) values('{v['day1']}','{v['sid']}',1,'{v['config']}');
 update public.seasons set current_matchday_id='{v['day1']}' where id='{v['sid']}';
 perform public.league_freeze_death_segment('{v['sid']}','{v['day1']}','{v['tid']}');
 assert (select cardinality(event_ids)=4 and not original_event=any(event_ids) from public.matchday_death_snapshots
   where matchday_id='{v['day1']}' and season_player_id='{v['pid']}'),'future official snapshot contains counted events only';
 snapshots_before=public.league_death_snapshot('{v['pid']}','{v['day1']}')::text;
 perform pg_temp.observe(array[1,2,3,4,5]);
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=5,'future genuine Gible death counts again after correction';
 assert (select count(*)=6 from public.league_death_events where season_player_id='{v['pid']}'),'five old rows plus one genuine new event';
 assert (select count(*)=1 from public.league_effective_death_events('{v['pid']}') where pokemon_entity_id='{v['entities'][0]}' and cycle_key like 'correction:%'),'fresh correction boundary counted once';
 perform pg_temp.observe(array[1,2,3,4,5]);
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=5,'resync cannot double-count future death';
 assert public.league_death_snapshot('{v['pid']}','{v['day1']}')::text=snapshots_before,'later genuine death preserves frozen snapshot';
end $$;
rollback;
""")
    # Separate rollback groups make every failure check independent of the
    # successful audit and preserve original production-shaped reproduction.
    prefix, v = fixture()
    pg.sql(prefix + f"""
do $$ declare r jsonb; state jsonb; original uuid; dead uuid; before_count bigint; key text;
begin
 select id into original from public.league_death_events where season_player_id='{v['pid']}' and pokemon_entity_id='{v['entities'][0]}';
 select id into dead from public.league_death_events where season_player_id='{v['pid']}' and pokemon_entity_id='{v['entities'][1]}';
 before_count=(select count(*) from public.league_death_resolutions where season_player_id='{v['pid']}');
 foreach key in array array['currently_dead','foreign','wrong_total','stale_revision','wrong_source','duplicate_id','wipe','revive_rearm'] loop
  r=pg_temp.correction();
  if key='currently_dead' then r=jsonb_set(r,'{{request,body,invalidated_event_ids}}',to_jsonb(array[dead]));
  elsif key='foreign' then r=jsonb_set(r,'{{request,body,invalidated_event_ids}}',to_jsonb(array[gen_random_uuid()]));
  elsif key='wrong_total' then r=jsonb_set(r,'{{request,body,actual_deaths}}','3');
  elsif key='stale_revision' then r=jsonb_set(r,'{{request,body,expected_revision}}','0');
  elsif key='wrong_source' then r=jsonb_set(r,'{{request,body,source_sha256}}',to_jsonb(repeat('a',64)));
  elsif key='duplicate_id' then r=jsonb_set(r,'{{request,body,invalidated_event_ids}}',to_jsonb(array[original::text,upper(original::text)]));
  elsif key='wipe' then
   update public.season_player_stats set revived_after_wipe=1,metadata='{{"wipe_revision":1}}' where season_player_id='{v['pid']}';
  elsif key='revive_rearm' then
   update public.league_death_history set revived_entities=jsonb_build_object('{v['entities'][0]}',jsonb_build_object('token','audit:real-revive','after_revision_number',2)) where season_player_id='{v['pid']}';
  end if;
  begin
   perform public.api_admin_death_history(r);
   raise exception 'ineligible correction accepted: %',key;
  exception when sqlstate 'PT409' or sqlstate 'PT422' then null;
  end;
  update public.season_player_stats set revived_after_wipe=0,metadata='{{}}' where season_player_id='{v['pid']}';
  update public.league_death_history set revived_entities='{{}}' where season_player_id='{v['pid']}';
  assert (select count(*) from public.league_death_resolutions where season_player_id='{v['pid']}')=before_count,'failed corrections leave no resolution';
 end loop;
 assert not has_function_privilege('anon','public.league_effective_death_events(uuid)','execute')
  and not has_function_privilege('authenticated','public.league_effective_death_events(uuid)','execute'),'effective event evidence stays backend-only';
 assert not has_function_privilege('anon','public.api_admin_death_history(jsonb)','execute')
  and not has_function_privilege('authenticated','public.api_admin_death_history(jsonb)','execute'),'browser roles cannot mutate history';
 -- Freeze the old five-event boundary, then attempt the same specific
 -- correction. An approved new live adjustment cannot rewrite that boundary.
 insert into public.matchdays(id,season_id,number,season_config_version_id) values('{v['day1']}','{v['sid']}',1,'{v['config']}');
 update public.seasons set current_matchday_id='{v['day1']}' where id='{v['sid']}';
 perform public.league_freeze_death_segment('{v['sid']}','{v['day1']}','{v['tid']}');
 begin
  r=jsonb_set(jsonb_set(pg_temp.correction(),'{{request,body,segment_deaths}}','5'),'{{request,body,actual_deaths}}','5');
  perform public.api_admin_death_history(r);
  raise exception 'frozen false event was silently changed';
 exception when sqlstate 'PT409' then assert sqlerrm='death_history_event_frozen',sqlerrm; end;
 assert (public.league_death_snapshot('{v['pid']}','{v['day1']}')->>'actual_deaths')::int=5,'old frozen count unchanged';
end $$;
rollback;
""")
    prefix, v = fixture()
    # The mechanism applies to multiple explicitly reviewed false placements,
    # rather than being a trainer/name-specific subtraction of one tenth.
    prefix = prefix.replace("observe(array[1]);", "observe(array[1,2]);")
    prefix = prefix.replace("confirm(1,0,1);", "confirm(2,0,2);")
    prefix = prefix.replace("observe(array[2,3,4,5]);", "observe(array[3,4,5]);")
    prefix = prefix[:prefix.index("do $$ declare general jsonb;")]
    pg.sql(prefix + f"""
do $$ declare request jsonb; ids uuid[]; result jsonb; begin
 select array_agg(id order by id) into ids from public.league_death_events
  where season_player_id='{v['pid']}' and pokemon_entity_id in ('{v['entities'][0]}','{v['entities'][1]}');
 request=pg_temp.correction(ids);
 request=jsonb_set(jsonb_set(request,'{{request,body,actual_deaths}}','3'),'{{request,body,segment_deaths}}','3');
 result=public.api_admin_death_history(request);
 assert (result->>'actual_deaths')::int=3 and jsonb_array_length(result->'invalidated_event_ids')=2,'two reviewed false events removed exactly';
 assert (select count(*)=5 from public.league_death_events where season_player_id='{v['pid']}'),'all original raw events retained';
 perform pg_temp.observe(array[1,3,4,5]);
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=4,'first corrected entity can genuinely die';
 perform pg_temp.observe(array[1,2,3,4,5]);
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=5,'second corrected entity has its independent fresh cycle';
end $$;
rollback;
""")
    return "GREEN: explicit false event4/-0.4;immutable originals/provenance;source/revive/frozen/permission guards;future real death and snapshots correct"


def validate_concurrency(pg):
    assert pg.lines("select count(*) from public.seasons") == ["0"], "concurrency requires a dedicated empty synthetic cluster"
    prefix, v = fixture()
    result = pg.sql(prefix + "select pg_temp.correction();\ncommit;")
    request = json.loads(next(line for line in reversed(result.out.splitlines()) if line.startswith('{"request"') or line.startswith('{"operation"')))
    barrier = Barrier(2)

    def execute():
        with psycopg.connect(host="127.0.0.1", port=pg.port, user="supabase_admin", dbname=pg.database) as connection:
            connection.execute("set local role service_role")
            barrier.wait(timeout=15)
            return connection.execute("select public.api_admin_death_history(%s::jsonb)", (json.dumps(request),)).fetchone()[0]

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: execute(), range(2)))
    assert sorted(r["replayed"] for r in responses) == [False, True]
    assert responses[0]["resolution_id"] == responses[1]["resolution_id"]
    assert pg.lines(f"select count(*) from public.league_death_resolutions where season_player_id='{v['pid']}'") == ["2"]
    assert pg.lines(f"select count(*) from public.league_death_events where season_player_id='{v['pid']}'") == ["5"]
    return "concurrent same confirmation:one correction/one replay,one shared resolution,five immutable raw events"


def main():
    from tools.phase30_release_audit import SupabaseLikePG

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, default=Path(os.environ["LOCALAPPDATA"]) / "Temp/phase10-5l-pg17/pgsql/bin")
    parser.add_argument("--port", type=int, default=55601)
    parser.add_argument("--evidence", type=Path, default=Path(os.environ["LOCALAPPDATA"]) / "PokeApp-migration-evidence/trainer-079-readonly")
    parser.add_argument("--regressions", action="store_true", help="Also run the affected075/076 SQL acceptance groups")
    args = parser.parse_args()
    args.evidence.mkdir(exist_ok=True)
    pg = SupabaseLikePG(args.pg_bin, args.port, parent=args.evidence)
    report = {"status": "RUNNING", "production_mutations": False, "port": args.port}
    migration = Path(__file__).resolve().parents[1] / "supabase/v2/migrations/077_false_death_event_corrections.sql"
    try:
        pg.start()
        for file in sorted(migration.parent.glob("*.sql")):
            if int(file.name[:3]) <= 76:
                pg.sql(file.read_text(encoding="utf-8"))
        report["red"] = validate_red(pg)
        pg.sql(migration.read_text(encoding="utf-8"))
        report["green"] = validate(pg)
        if args.regressions:
            from tools import validate_phase075_deaths as deaths
            from tools import validate_phase075_league as league
            from tools import validate_phase075_guards as guards
            from tools import validate_phase076_championship as championship
            report["regressions"] = {
                "075_deaths": deaths.validate(pg),
                "075_four_matchdays": league.validate(pg),
                "075_two_divisions": league.validate_two_divisions(pg),
                "075_legacy": league.validate_legacy(pg),
                "075_guards": guards.validate(pg),
                "076_championship": championship.validate(pg),
            }
        report["concurrency"] = validate_concurrency(pg)
        report.update(status="PASS", migration_sha256=sha256(migration.read_bytes()).hexdigest())
        print(json.dumps(report))
    finally:
        pg.stop(remove=False)
        report.update(retained_cluster=str(pg.root), stopped=True, completed_at=datetime.now(UTC).isoformat())
        (args.evidence / "false-death-sql-tests.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
