"""079 all-vs-all League start by ordinary participants, on the real RPCs.

A synthetic modern single-league season with ZERO matchdays (the production
shape of ChampionsLocke on 2026-11-04) proves that, without any administrator:

* readiness lists the exact per-trainer reasons (save, J1 badges, death
  history) and the season-level structure reasons;
* any active participant prepares J1 once (one «Liga», 10 pairs for 5,
  one audited all_vs_all_v1 snapshot); replays and a second caller get the
  same J1; outsiders, retired and disabled trainers cannot; a two-league
  season still requires the observed A/B assignment;
* a trainer confirms only their OWN observed death history (first baseline or
  the wipe counter they set), never chosen numbers, with revision/source/value
  guards, receipts and an audit event; admin offsets are preserved; other
  cases stay administrative;
* opening stays blocked until every prerequisite holds, then freezes five
  death snapshots; a Team Lock on the prepared J1 queues exactly one
  announcement; closing creates J2 as before.

Disposable loopback PostgreSQL only; validate() always rolls back.
validate_concurrency() commits on its own fresh cluster.

    python -m tools.validate_phase079_all_vs_all --port <free port>
"""

from concurrent.futures import ThreadPoolExecutor
from itertools import combinations
from pathlib import Path
from threading import Barrier
from uuid import uuid4
import argparse
import json
import os

import psycopg
from psycopg.types.json import Jsonb

from tools.validate_player_matchdays import close_request, envelope, participant, rejected


class _Rollback(Exception):
    pass


def connect(pg):
    return psycopg.connect(host="127.0.0.1", port=pg.port, user="supabase_admin", dbname=pg.database)


def value(conn, sql, args=()):
    return conn.execute(sql, args).fetchone()[0]


def call(conn, name, body):
    return value(conn, f"select public.{name}(%s::jsonb)", (Jsonb(body),))


def seed(names=("Iker 079", "ByVisan02 079", "Samu 079", "Aaron 079", "Anto 079")):
    sid, admin, outsider, config = (str(uuid4()) for _ in range(4))
    players = [str(uuid4()) for _ in names]
    trainers = [str(uuid4()) for _ in names]
    entities = {pid: [str(uuid4()) for _ in range(6)] for pid in players}
    coins = json.dumps({str(i): 10 for i in range(1, len(names) + 1)})
    scoring = json.dumps({str(i): 0 for i in range(1, len(names) + 1)})
    sql = f"""
insert into public.trainers(id,display_name,slug,is_admin,auth_user_id)
 values('{admin}','079 admin','079-admin-{admin}',true,gen_random_uuid()),
       ('{outsider}','079 outsider','079-out-{outsider}',false,gen_random_uuid());
insert into public.seasons(id,name,status,started_at,created_by_trainer_id,metadata)
 values('{sid}','079 all vs all','active',now(),'{admin}','{{"initial_assignment_rule":"observed_deaths_v1"}}');
insert into public.season_admin_state(season_id,roster_revision) values('{sid}',5);
insert into public.season_config_versions(id,season_id,version_number,name,effective_from_matchday,total_matchdays,
 division_count,division_sizes,promotion_relegation_count,scoring_json,coin_rewards_json,rules_json,roster_revision)
 values('{config}','{sid}',1,'079 fixture',1,2,1,'{{"A":{len(names)}}}',0,'{scoring}','{coins}',
 '{{"team_lock_required":true,"last_b_gets_steal":false,"badge_reward_coins":4,"game_completion_reward_coins":12}}',5);
"""
    for name, pid, tid in zip(names, players, trainers):
        ids = ",".join(f"'{e}'::uuid" for e in entities[pid])
        sql += f"""
insert into public.trainers(id,display_name,slug,is_admin,auth_user_id)
 values('{tid}','{name}','079-p-{tid}',false,gen_random_uuid());
insert into public.season_players(id,season_id,trainer_id,status,dead_box_number)
 values('{pid}','{sid}','{tid}','active',7);
insert into public.season_player_stats(season_player_id,season_id,trainer_id)
 values('{pid}','{sid}','{tid}') on conflict do nothing;
insert into public.pokemon_entities(id,season_id,owner_trainer_id,identity_status,identity_schema_version,candidate_key,initial_evidence)
 select e,'{sid}','{tid}','unambiguous',1,lpad(n::text,64,'0'),jsonb_build_object('fixture',n)
 from unnest(array[{ids}]) with ordinality x(e,n);
"""
    # One trusted Pokémon Y League save per call: native gym badges, Box 7 dead,
    # living Pokémon in Box 1, and a full party of six for Team Locks.
    sql += """
create or replace function pg_temp.observe(pid uuid,dead integer[],badges integer) returns uuid
language plpgsql as $observe$
declare p public.season_players; ids uuid[]; previous public.pokemon_identity_revisions;
 save_id uuid=gen_random_uuid(); parsed_id uuid=gen_random_uuid(); revision_id uuid=gen_random_uuid(); n bigint;
 hash text; payload jsonb; boxes jsonb='[]'; slots jsonb; party jsonb='[]'; box integer; slot integer; idx integer; mon jsonb;
 trainer jsonb=jsonb_build_object('name','Fixture','tid',1,'sid',2,'gender',0,'language',2);
begin
 select * into p from public.season_players where id=pid;
 select array_agg(id order by candidate_key) into ids from public.pokemon_entities where owner_trainer_id=p.trainer_id and season_id=p.season_id;
 select * into previous from public.pokemon_identity_revisions where season_id=p.season_id and trainer_id=p.trainer_id order by revision_number desc limit 1;
 n=coalesce(previous.revision_number,0)+1; hash=encode(sha256(convert_to(pid::text||':'||n::text,'UTF8')),'hex');
 for box in 1..8 loop
  slots='[]';
  for slot in 1..30 loop
   mon='null';
   if slot<=cardinality(ids) and ((box=7 and slot=any(dead)) or (box=1 and not slot=any(dead))) then
    mon=jsonb_build_object('species','Pokémon #25','nickname','Fixture '||slot,'identity_evidence',jsonb_build_object('fixture',slot));
   end if;
   slots=slots||jsonb_build_array(jsonb_build_object('slot_number',slot,'pokemon',mon));
  end loop;
  boxes=boxes||jsonb_build_array(jsonb_build_object('box_number',box,'slots',slots));
 end loop;
 for slot in 1..6 loop
  party=party||jsonb_build_array(jsonb_build_object('slot_number',slot,'pokemon',jsonb_build_object(
   'species','Pokémon #'||(677+slot%2),'nickname','','level',30,'types','[]'::jsonb,'item','',
   'moves',jsonb_build_array(jsonb_build_object('name','Move #1','pp',35)),'is_shiny',false,'gender',case when slot%2=0 then 'F' else 'M' end,
   'form',slot%2,'ability','Ability #1','nature','Nature #1',
   'ivs',jsonb_build_object('hp',31,'atk',31,'defense',31,'spa',31,'spd',31,'spe',31),
   'evs',jsonb_build_object('hp',0,'atk',0,'defense',0,'spa',0,'spd',0,'spe',0))));
 end loop;
 payload=jsonb_build_object('save_record_id',save_id,'source_hash',hash,'trainer_id',p.trainer_id,'game','Y','generation',6,
  'trainer',trainer,'identity_policy_version',2,
  'observed_progress',jsonb_build_object('schema_version',1,'source_hash',hash,'game','Y','generation',6,'progress',null),
  'native_progress',jsonb_build_object('schema_version',1,'model','gym_badges',
    'badge_flags',(select jsonb_agg(i<=badges order by i) from generate_series(1,8) i),
    'league_access',null,'league_visited',false,'league_fly_unlocked',false,'hall_of_fame_entered',false,
    'champion_defeated',null,'island_stamp_flags',null,'island_challenge_completed',null),
  'party',party,'boxes',boxes);
 insert into public.save_files(id,season_id,trainer_id,storage_key,original_filename,sha256,parser_status,parser_version,metadata)
 values(save_id,p.season_id,p.trainer_id,'079-fixture/'||save_id,'main',hash,'parsed','pokeapp-reader/3;pkhex/24.11.11',
  jsonb_build_object('trusted_registration','{}'::jsonb,'save_identity',jsonb_build_object('game','Y','trainer',trainer)));
 insert into public.parsed_saves(id,save_file_id,parser_version,payload)
 values(parsed_id,save_id,'pokeapp-reader/3;pkhex/24.11.11',payload);
 insert into public.pokemon_identity_revisions(id,season_id,trainer_id,save_file_id,parsed_save_id,predecessor_id,
  revision_number,capture_stream_id,capture_sequence,input_signature)
 values(revision_id,p.season_id,p.trainer_id,save_id,parsed_id,previous.id,n,coalesce(previous.capture_stream_id,gen_random_uuid()),n,hash);
 for idx in 1..cardinality(ids) loop
  insert into public.pokemon_observations(revision_id,season_id,trainer_id,save_file_id,pokemon_entity_id,source,box_number,
   slot_number,outcome,evidence,candidate_key,observation_signature)
  values(revision_id,p.season_id,p.trainer_id,save_id,ids[idx],'box',case when idx=any(dead) then 7 else 1 end,idx,
   case when n=1 then 'NEW' else 'MATCHED' end,jsonb_build_object('fixture',idx),lpad(idx::text,64,'0'),lpad(idx::text,64,'0'));
 end loop;
 update public.season_players set current_save_file_id=save_id where id=pid;
 return save_id;
end $observe$;
"""
    return sql, dict(sid=sid, admin=admin, outsider=outsider, config=config,
                     players=players, trainers=trainers, names=list(names))


def initialize(conn):
    assert conn.info.host == "127.0.0.1" and not conn.autocommit
    conn.execute("update public.seasons set status='draft' where status='active'")
    sql, v = seed()
    conn.execute(sql)
    conn.execute("set local role service_role")
    return v


def prepare(conn, v, actor):
    return call(conn, "api_league_prepare_first_matchday", dict(actor_trainer_id=actor, season_id=v["sid"]))


def readiness(conn, v, actor):
    return call(conn, "api_league_readiness", dict(actor_trainer_id=actor, season_id=v["sid"]))


def death(conn, v, actor, operation="state", body=None, key=None):
    request = dict(actor_trainer_id=actor, season_id=v["sid"])
    if body is not None:
        request["body"] = body
    if key is not None:
        request["idempotency_key"] = key
    return call(conn, "api_participant_death_history", dict(operation=operation, request=request))


def confirm_body(state, **changes):
    proposed = state["proposed"]
    return dict(dict(expected_revision=state["revision"], source_sha256=state["source_sha256"],
                     actual_deaths=proposed["actual_deaths"], wipe_deaths=proposed["wipe_deaths"],
                     segment_deaths=proposed["segment_deaths"]), **changes)


def reasons(ready, index, v):
    return next(p["reasons"] for p in ready["participants"] if p["season_player_id"] == v["players"][index])


def as_owner(conn, sql, args=()):
    conn.execute("reset role")
    conn.execute(sql, args)
    conn.execute("set local role service_role")


def observe(conn, v, index, dead, badges):
    as_owner(conn, "select pg_temp.observe(%s,%s,%s)", (v["players"][index], dead, badges))


def wipe(conn, v, index, count, key):
    state = call(conn, "api_participant_wipe_revivals",
                 dict(operation="state", request=dict(actor_trainer_id=v["trainers"][index], season_id=v["sid"])))
    return call(conn, "api_participant_wipe_revivals", dict(operation="set", request=dict(
        actor_trainer_id=v["trainers"][index], season_id=v["sid"], idempotency_key=key,
        body=dict(revived_after_wipe=count, expected_revision=state["revision"]))))


def validate(pg):
    checks = []
    with connect(pg) as conn:
        try:
            v = initialize(conn)
            t, p = v["trainers"], v["players"]
            assert not any(value(conn, "select is_admin from public.trainers where id=%s", (x,)) for x in t)

            ready = readiness(conn, v, t[0])
            assert ready["state"] == "unprepared" and ready["structure"] == "all_vs_all", ready
            assert ready["next_number"] == 1 and ready["can_prepare"] and not ready["can_open"]
            assert ready["can_operate"] and not readiness(conn, v, v["outsider"])["can_operate"]
            assert all(x["reasons"] == ["save_missing", "death_history_baseline_required"] for x in ready["participants"])
            inputs = value(conn, "select public.initial_assignment_inputs(%s)", (v["sid"],))
            assert inputs["state"] == "not_required" and inputs["blocking_reasons"] == ["initial_assignment_not_required"]
            checks.append("zero matchdays: readiness unprepared, every trainer save_missing+baseline; A/B review not_required")

            rejected(conn, lambda: prepare(conn, v, v["outsider"]), "participant_required")
            for change, code in (("update public.season_players set status='retired' where id=%s", "participant_inactive"),
                                 ("update public.trainers set globally_enabled=false where id=(select trainer_id from public.season_players where id=%s)", "trainer_disabled")):
                try:
                    with conn.transaction():
                        as_owner(conn, change, (p[4],))
                        rejected(conn, lambda: prepare(conn, v, t[4]), code)
                        assert "invalid_roster" in readiness(conn, v, t[0])["reasons"]
                        raise _Rollback()
                except _Rollback:
                    pass
            try:
                with conn.transaction():
                    as_owner(conn, "update public.season_config_versions set division_sizes='{\"A\":3,\"B\":2}',division_count=2 where id=%s", (v["config"],))
                    rejected(conn, lambda: prepare(conn, v, t[0]), "initial_assignment_required")
                    two = readiness(conn, v, t[0])
                    assert two["structure"] == "divisions" and two["reasons"] == ["initial_assignment_required"], two
                    raise _Rollback()
            except _Rollback:
                pass
            checks.append("outsider/retired/disabled refused; two-league season keeps the observed A/B assignment")

            created = prepare(conn, v, t[1])
            assert created["created"] is True and created["number"] == 1 and created["status"] == "scheduled"
            day = created["matchday_id"]
            again = prepare(conn, v, t[2])
            assert again == dict(created, created=False), again
            assert value(conn, "select count(*) from public.matchdays where season_id=%s", (v["sid"],)) == 1
            assert value(conn, "select current_matchday_id::text from public.seasons where id=%s", (v["sid"],)) == day
            assert conn.execute("select code,name from public.divisions where season_id=%s", (v["sid"],)).fetchall() == [("A", "Liga")]
            assert value(conn, "select count(*) from public.division_memberships where season_id=%s and effective_from_matchday_number=1", (v["sid"],)) == 5
            pairs = conn.execute("select player_a_id::text,player_b_id::text from public.matches where matchday_id=%s", (day,)).fetchall()
            assert len(pairs) == 10 and {frozenset(x) for x in pairs} == {frozenset(x) for x in combinations(p, 2)}
            snap = conn.execute("select rule,actor_trainer_id::text,assignments from public.initial_division_snapshots where season_id=%s", (v["sid"],)).fetchone()
            assert snap[0] == "all_vs_all_v1" and snap[1] == t[1] and sorted(snap[2]["A"]) == sorted(p) and snap[2]["B"] == []
            assert value(conn, "select count(*) from public.activity_events where season_id=%s and type='LEAGUE_FIRST_MATCHDAY_PREPARED' and actor_trainer_id=%s", (v["sid"], t[1])) == 1
            assert value(conn, "select public.initial_assignment_inputs(%s)", (v["sid"],))["state"] == "not_required"
            checks.append("participant prepared J1 once: 1 Liga, 5 members, 10 unique pairs, audited all_vs_all_v1; replay/2nd caller same J1")

            ready = readiness(conn, v, t[0])
            assert ready["state"] == "scheduled" and ready["matchday"]["id"] == day and not ready["can_open"]
            # Saves: Iker 3 dead / 2 badges, ByVisan02 0 / 1 badge, Aaron 0 / 3, Anto 0 / 8; Samu none.
            observe(conn, v, 0, [1, 2, 3], 2)
            observe(conn, v, 1, [], 1)
            observe(conn, v, 3, [], 3)
            observe(conn, v, 4, [], 8)
            ready = readiness(conn, v, t[0])
            assert reasons(ready, 0, v) == ["death_history_baseline_required"]
            assert reasons(ready, 1, v) == ["badges_missing", "death_history_baseline_required"]
            assert reasons(ready, 2, v) == ["save_missing", "death_history_baseline_required"]
            own = next(x for x in ready["participants"] if x["season_player_id"] == p[0])
            assert own["self_confirmable"] and not next(x for x in ready["participants"] if x["season_player_id"] == p[2])["self_confirmable"]
            checks.append("readiness per trainer: save_missing, badges_missing, death_history_baseline_required")

            rejected(conn, lambda: call(conn, "api_admin_matchday", dict(operation="open", request=envelope(
                t[0], v, day, "079-open-early", dict(expected_revision=ready["matchday"]["revision"])))),
                "initial_assignment_not_ready", "death_history_baseline_required")
            checks.append("opening refused while a prerequisite is missing (no partial freeze)")
            assert value(conn, "select count(*) from public.matchday_death_snapshots where matchday_id=%s", (day,)) == 0

            state = death(conn, v, t[0])
            assert state["can_confirm"] and state["proposed"] == dict(actual_deaths=3, wipe_deaths=0, segment_deaths=3), state
            body = confirm_body(state)
            rejected(conn, lambda: death(conn, v, t[0], "confirm", dict(body, actual_deaths=2), "079-d-0"), "death_history_changed")
            rejected(conn, lambda: death(conn, v, t[0], "confirm", dict(body, expected_revision=state["revision"] + 1), "079-d-1"),
                     "death_history_revision_conflict")
            rejected(conn, lambda: death(conn, v, t[0], "confirm", dict(body, source_sha256="0" * 64), "079-d-2"), "death_history_source_changed")
            rejected(conn, lambda: death(conn, v, v["outsider"], "confirm", body, "079-d-3"), "participant_required")
            rejected(conn, lambda: call(conn, "api_participant_death_history", dict(operation="confirm", request=dict(
                actor_trainer_id=t[1], season_id=v["sid"], resource_id=p[0], idempotency_key="079-d-4", body=body))), "invalid_request")
            done = death(conn, v, t[0], "confirm", body, "079-d-5")
            assert done["known"] and done["actual_deaths"] == 3 and done["wipe_deaths"] == 0 and done["segment_deaths"] == 3
            assert death(conn, v, t[0], "confirm", body, "079-d-5")["replayed"] is True
            rejected(conn, lambda: death(conn, v, t[0], "confirm", body, "079-d-6"), "death_history_already_confirmed", "death_history_revision_conflict")
            row = conn.execute("select actor_trainer_id::text,confirmed_counts from public.league_death_resolutions where season_player_id=%s", (p[0],)).fetchone()
            assert row[0] == t[0] and row[1]["self_confirmed"] is True
            assert value(conn, "select count(*) from public.activity_events where type='DEATH_HISTORY_RECONCILED' and payload->>'season_player_id'=%s and (payload->>'self_confirmed')::boolean", (p[0],)) == 1
            assert value(conn, "select public.league_death_totals(%s)->>'death_penalty_tenths'", (p[0],)) == "3"
            checks.append("own observed baseline 3/0/3 confirmed once (shown values, revision, source, owner-only; receipt replay; audited)")

            # The wipe counter the trainer sets is acknowledged the same way.
            wipe(conn, v, 0, 1, "079-w-1")
            assert reasons(readiness(conn, v, t[0]), 0, v) == ["death_history_wipe_reconciliation_required"]
            state = death(conn, v, t[0])
            assert state["proposed"] == dict(actual_deaths=3, wipe_deaths=1, segment_deaths=3), state
            assert death(conn, v, t[0], "confirm", confirm_body(state), "079-d-7")["wipe_deaths"] == 1
            assert value(conn, "select public.league_death_totals(%s)->>'death_penalty_tenths'", (p[0],)) == "4"
            # More wipe revivals than observed deaths is not self-service.
            for index in (3, 4):
                death(conn, v, t[index], "confirm", confirm_body(death(conn, v, t[index])), f"079-d-base-{index}")
            wipe(conn, v, 3, 2, "079-w-2")
            state = death(conn, v, t[3])
            assert not state["can_confirm"] and state["confirm_blocker"] == "death_history_admin_required", state
            rejected(conn, lambda: death(conn, v, t[3], "confirm", dict(expected_revision=state["revision"], source_sha256=state["source_sha256"],
                     actual_deaths=0, wipe_deaths=2, segment_deaths=0), "079-d-8"), "death_history_admin_required")
            # Back to a counter the deaths can explain: the trainer acknowledges it again.
            wipe(conn, v, 3, 0, "079-w-3")
            state = death(conn, v, t[3])
            assert state["can_confirm"] and state["proposed"] == dict(actual_deaths=0, wipe_deaths=0, segment_deaths=0), state
            assert death(conn, v, t[3], "confirm", confirm_body(state), "079-d-8b")["known"] is True
            checks.append("own wipe counter acknowledged (3/1/3 = 0.4); wipes>deaths stays administrative")

            # An administrator's pre-tracking offset survives a later self-acknowledgement.
            admin_state = call(conn, "api_admin_death_history", dict(operation="state", request=dict(
                actor_trainer_id=v["admin"], season_id=v["sid"], resource_id=p[1])))
            call(conn, "api_admin_death_history", dict(operation="reconcile", request=dict(
                actor_trainer_id=v["admin"], season_id=v["sid"], resource_id=p[1], idempotency_key="079-admin-1",
                body=dict(actual_deaths=2, wipe_deaths=0, segment_deaths=2, expected_revision=admin_state["revision"],
                          source_sha256=admin_state["source_sha256"], reason="Pre-tracking deaths reviewed",
                          evidence="Owner-confirmed history", revived_entity_ids=[], invalidated_event_ids=[]))))
            wipe(conn, v, 1, 1, "079-w-4")
            state = death(conn, v, t[1])
            assert state["proposed"] == dict(actual_deaths=2, wipe_deaths=1, segment_deaths=2), state
            death(conn, v, t[1], "confirm", confirm_body(state), "079-d-9")
            assert value(conn, "select actual_offset from public.league_death_history where season_player_id=%s", (p[1],)) == 2
            checks.append("admin pre-tracking offset (2) preserved by the trainer's acknowledgement")

            observe(conn, v, 1, [], 2)
            observe(conn, v, 2, [], 2)
            death(conn, v, t[2], "confirm", confirm_body(death(conn, v, t[2])), "079-d-10")
            ready = readiness(conn, v, t[2])
            assert ready["can_open"] and all(not x["reasons"] for x in ready["participants"]), ready

            # Team Lock on the prepared J1: one announcement per lock, replacement edits it.
            source = conn.execute("select f.id::text,f.sha256,ps.id::text,ps.payload from public.season_players sp join public.save_files f on f.id=sp.current_save_file_id"
                                  " join public.parsed_saves ps on ps.save_file_id=f.id where sp.id=%s", (p[0],)).fetchone()
            team = [dict(species=s["pokemon"]["species"]) for s in source[3]["party"]]
            lock = lambda: conn.execute("select id::text,matchday_id::text from public.api_upsert_team_lock(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                                        (v["sid"], day, t[0], p[0], source[0], source[1], source[2], Jsonb(source[3]), Jsonb(team), Jsonb(team))).fetchone()
            first = lock()
            assert first[1] == day and value(conn, "select timing_status from public.public_team_locks where id=%s", (first[0],)) == "on_time"
            team[0] = dict(species="Pokémon #1")
            assert lock()[0] == first[0]
            assert value(conn, "select count(*) from public.discord_announcements where event_key=%s", ("team_locked:" + first[0],)) == 1
            assert value(conn, "select revision from public.discord_announcements where event_key=%s", ("team_locked:" + first[0],)) == 2
            checks.append("Team Lock on the prepared J1 (on time); one Discord row; replacement only edits it")

            opened = call(conn, "api_admin_matchday", dict(operation="open", request=envelope(
                t[3], v, day, "079-open", dict(expected_revision=ready["matchday"]["revision"]))))
            assert opened["state"] == "open"
            assert value(conn, "select count(*) from public.matchday_death_snapshots where matchday_id=%s", (day,)) == 5
            assert value(conn, "select segment_deaths from public.matchday_death_snapshots where matchday_id=%s and season_player_id=%s", (day, p[0])) == 3
            assert readiness(conn, v, t[0])["state"] == "open"
            state = death(conn, v, t[4])
            assert state["known"] and not state["can_confirm"] and state["confirm_blocker"] == "death_history_confirmed"
            checks.append("participant opened J1 once every prerequisite held: 5 frozen death snapshots (Iker segment 3)")

            matches = conn.execute("select id::text,player_a_id::text from public.matches where matchday_id=%s order by id", (day,)).fetchall()
            participant(conn, "results", envelope(t[2], v, day, "079-results", dict(
                expected_results_revision=opened["results_revision"],
                results=[dict(match_id=m, winner_season_player_id=a) for m, a in matches])))
            close, _ = close_request(conn, t[4], v, day, "079-close")
            try:
                closed = call(conn, "api_admin_matchday", close)
            except psycopg.Error:
                raise
            assert closed["state"] == "closed"
            ready = readiness(conn, v, t[0])
            assert ready["state"] == "scheduled" and ready["matchday"]["number"] == 2, ready
            assert value(conn, "select count(*) from public.matches m join public.matchdays d on d.id=m.matchday_id where d.season_id=%s and d.number=2", (v["sid"],)) == 10
            assert prepare(conn, v, t[0])["created"] is False
            assert all(x["reasons"] == [] for x in ready["participants"]), ready
            checks.append("participant closed J1; J2 created as before with 10 pairs; J2 readiness has no J1 badge gate")
        finally:
            conn.rollback()
    return "PASS: " + "; ".join(checks)


def validate_restored(pg):
    """The restored active season itself (rehearsal on a production backup).

    Everything runs as ordinary participants in ONE transaction that is always
    rolled back: readiness, preparing J1, a second caller, each trainer
    confirming their own observed history, and the opening refusing while a
    prerequisite is still missing. Nothing of it persists in the copy.
    """
    with connect(pg) as conn:
        try:
            conn.execute("set local role service_role")
            row = conn.execute("select id::text from public.seasons where status='active'").fetchone()
            if row is None:
                return "SKIP: the restored copy has no active season"
            v = dict(sid=row[0])
            assert value(conn, "select public.league_all_vs_all(%s)", (v["sid"],)), "active season is not all-vs-all"
            roster = conn.execute(
                "select sp.id::text,sp.trainer_id::text,t.display_name,t.is_admin,sp.current_save_file_id is not null"
                " from public.season_players sp join public.trainers t on t.id=sp.trainer_id"
                " where sp.season_id=%s order by t.display_name", (v["sid"],)).fetchall()
            n = len(roster)
            ordinary = [r for r in roster if not r[3]]
            actor = next(r for r in ordinary if r[4])
            assert value(conn, "select count(*) from public.matchdays where season_id=%s", (v["sid"],)) == 0
            ready = readiness(conn, v, actor[1])
            assert ready["state"] == "unprepared" and ready["can_prepare"] and ready["can_operate"], ready
            before = {p["display_name"]: p["reasons"] for p in ready["participants"]}
            created = prepare(conn, v, actor[1])
            assert created["created"] and created["number"] == 1
            assert prepare(conn, v, ordinary[-1][1])["matchday_id"] == created["matchday_id"]
            assert value(conn, "select count(*) from public.matches where matchday_id=%s", (created["matchday_id"],)) == n * (n - 1) // 2
            confirmed = {}
            for sp, trainer, name, _, _ in roster:
                state = death(conn, v, trainer)
                if state["can_confirm"]:
                    death(conn, v, trainer, "confirm", confirm_body(state), f"079-rehearsal-{sp}")
                    p = state["proposed"]
                    confirmed[name] = f"{p['actual_deaths']}/{p['wipe_deaths']}/{p['segment_deaths']}"
            after = readiness(conn, v, actor[1])
            left = {p["display_name"]: p["reasons"] for p in after["participants"] if p["reasons"]}
            refused = None
            if not after["can_open"]:
                try:
                    with conn.transaction():
                        call(conn, "api_admin_matchday", dict(operation="open", request=envelope(
                            actor[1], v, created["matchday_id"], "079-rehearsal-open",
                            dict(expected_revision=after["matchday"]["revision"]))))
                except psycopg.Error as exc:
                    refused = exc.diag.message_primary
                assert refused, "an unready J1 opened"
                assert value(conn, "select count(*) from public.matchday_death_snapshots where matchday_id=%s", (created["matchday_id"],)) == 0
            return ("PASS (rolled back): %d participants, J1 prepared by a non-admin with %d pairs; before %s;"
                    " self-confirmed %s; still missing %s; opening refused with %s"
                    % (n, n * (n - 1) // 2, json.dumps(before, ensure_ascii=True), json.dumps(confirmed, ensure_ascii=True),
                       json.dumps(left, ensure_ascii=True), refused))
        finally:
            conn.rollback()


def validate_concurrency(pg):
    """Call only on a dedicated disposable cluster: commits synthetic rows."""
    with connect(pg) as conn:
        v = initialize(conn)
        conn.commit()
    barrier = Barrier(3)

    def prepare_as(actor):
        with connect(pg) as conn:
            conn.execute("set role service_role")
            barrier.wait(timeout=15)
            result = prepare(conn, v, actor)
            conn.commit()
            return result

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(prepare_as, v["trainers"][:3]))
    assert sorted(r["created"] for r in results) == [False, False, True], results
    assert len({r["matchday_id"] for r in results}) == 1
    with connect(pg) as conn:
        assert value(conn, "select count(*) from public.matchdays where season_id=%s", (v["sid"],)) == 1
        assert value(conn, "select count(*) from public.matches m join public.matchdays d on d.id=m.matchday_id where d.season_id=%s", (v["sid"],)) == 10
        assert value(conn, "select count(*) from public.initial_division_snapshots where season_id=%s", (v["sid"],)) == 1
    return "PASS: 3 concurrent participant preparations: one J1, one creator, 10 pairs, one snapshot"


def main():
    from tools.phase30_release_audit import SupabaseLikePG

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path,
                        default=Path(os.environ["LOCALAPPDATA"]) / "Temp/phase10-5l-pg17/pgsql/bin")
    parser.add_argument("--port", type=int, default=55621)
    args = parser.parse_args()
    for check in (validate, validate_concurrency):
        pg = SupabaseLikePG(args.pg_bin, args.port)
        try:
            pg.start()
            for migration in sorted((Path(__file__).resolve().parents[1] / "supabase/v2/migrations").glob("*.sql")):
                if int(migration.name[:3]) <= 79:
                    pg.sql(migration.read_text(encoding="utf-8"))
            print(check(pg))
        finally:
            pg.stop(remove=True)


if __name__ == "__main__":
    main()
