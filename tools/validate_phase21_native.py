"""Focused disposable PostgreSQL gate for the Phase21 native read projection.

This gate uses only synthetic rows in the caller's loopback validation database;
it never connects to Supabase and rolls the fixture transaction back.
"""

from __future__ import annotations

import argparse
import os
import subprocess

TRAINER = "11111111-1111-1111-1111-111111111111"
SEASON = "22222222-2222-2222-2222-222222222222"
PLAYER = "55555555-5555-5555-5555-555555555555"
SAVE = "33333333-3333-3333-3333-333333333333"
PARSED = "44444444-4444-4444-4444-444444444444"
SHA = "a" * 64


def sql() -> str:
    payload = (
        '{"save_record_id":"%s","trainer_id":"%s","source_hash":"%s",'
        '"game":"X","generation":6,"trainer":{"name":"Native Fixture",'
        '"tid":1,"sid":2,"gender":0,"language":2},'
        '"observed_progress":{"schema_version":1,"game":"X","generation":6,'
        '"source_hash":"%s","progress":null},"identity_policy_version":2,'
        '"native_progress":{"schema_version":1,"model":"gym_badges",'
        '"badge_flags":[true,false,false,false,false,false,false,false],'
        '"league_access":null,"league_visited":null,"league_fly_unlocked":false,'
        '"hall_of_fame_entered":false,"champion_defeated":false,'
        '"island_stamp_flags":null,"island_challenge_completed":null},'
        '"party":[null,null,null,null,null,null],"boxes":[]}'
    ) % (SAVE, TRAINER, SHA, SHA)
    identity = (
        '{"trusted_registration":{"status":"registered"},"save_identity":'
        '{"game":"X","trainer":{"name":"Native Fixture","tid":1,"sid":2,'
        '"gender":0,"language":2}}}'
    )
    return f"""
begin;
insert into public.trainers(id,display_name,slug) values ('{TRAINER}','Native Fixture','native-fixture');
insert into public.seasons(id,name,status,started_at,created_by_trainer_id) values ('{SEASON}','Native Fixture Season','active',now(),'{TRAINER}');
insert into public.season_players(id,season_id,trainer_id,status) values ('{PLAYER}','{SEASON}','{TRAINER}','active');
insert into public.save_files(id,season_id,trainer_id,storage_bucket,storage_key,original_filename,sha256,parser_status,parser_version,metadata)
values ('{SAVE}','{SEASON}','{TRAINER}','raw-saves','trusted/{TRAINER}/{SEASON}/{SHA}.sav','save.sav','{SHA}','parsed','pokeapp-reader/3;pkhex/24.11.11','{identity}'::jsonb);
insert into public.parsed_saves(id,save_file_id,parser_version,schema_version,status,payload)
values ('{PARSED}','{SAVE}','pokeapp-reader/3;pkhex/24.11.11',1,'parsed','{payload}'::jsonb);
update public.season_players set current_save_file_id='{SAVE}' where id='{PLAYER}';
select case when public.observed_native_progress(sf,ps,sp.trainer_id)->>'model'='gym_badges' then 'PASS native projection' else 'FAIL native projection' end
from public.save_files sf join public.parsed_saves ps on ps.save_file_id=sf.id join public.season_players sp on sp.current_save_file_id=sf.id;
update public.parsed_saves set payload=jsonb_set(payload,'{{native_progress,badge_flags}}','[true]'::jsonb) where id='{PARSED}';
select case when public.observed_native_progress(sf,ps,sp.trainer_id) is null then 'PASS malformed fail closed' else 'FAIL malformed accepted' end
from public.save_files sf join public.parsed_saves ps on ps.save_file_id=sf.id join public.season_players sp on sp.current_save_file_id=sf.id;
rollback;
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--psql", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=55468)
    parser.add_argument("--database", required=True)
    args = parser.parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"} or not args.database.startswith("pokeapp_v2_validation"):
        raise SystemExit("refusing non-disposable database")
    result = subprocess.run(
        [args.psql, "-h", args.host, "-p", str(args.port), "-U", "postgres", "-d", args.database, "-X", "-v", "ON_ERROR_STOP=1", "-qAt", "-f", "-"],
        input=sql(), text=True, encoding="utf-8", capture_output=True, env=os.environ.copy(), check=False,
    )
    if result.returncode:
        raise SystemExit(result.stderr)
    lines = [line for line in result.stdout.splitlines() if line]
    if lines != ["PASS native projection", "PASS malformed fail closed"]:
        raise SystemExit(f"unexpected native gate output: {lines!r}")
    print("Phase21 native PostgreSQL RESULT PASS (2 checks; transaction rolled back)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
