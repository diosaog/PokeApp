"""Focused, synthetic trainer evidence and reward acceptance on disposable PG.

No remote connections, real saves, purchases or production repairs. validate()
rolls back every fixture. validate_concurrency() commits synthetic fixture rows
only and therefore requires the dedicated disposable cluster used by main().
"""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
import argparse
import os

import psycopg

from tools.validate_phase21_native import PARSED, PLAYER, SAVE, SEASON, SHA, TRAINER
from tools.validate_phase21_native import sql as native_sql
from tools.validate_phase075_deaths import seed as death_seed


def reward_seed():
    # Existing native fixture, stopped before pointer promotion. Its parsed
    # progress is authentic-shaped but cannot authorize League rewards alone.
    seed = native_sql().split("update public.season_players set current_save_file_id")[0]
    return seed + f"""
insert into public.season_config_versions(season_id,version_number,name,effective_from_matchday,total_matchdays,division_count,rules_json)
 values('{SEASON}',1,'077 reward fixture',1,4,1,'{{"badge_reward_coins":4,"game_completion_reward_coins":12}}');
insert into public.season_player_stats(season_player_id,season_id,trainer_id)
 values('{PLAYER}','{SEASON}','{TRAINER}') on conflict do nothing;
insert into public.trainer_personal_saves(trainer_id,sha256,observation_digest,parser_version,game,payload,uploaded_at)
 select '{TRAINER}',s.sha256,s.sha256,s.parser_version,'X',p.payload,now()
 from public.save_files s join public.parsed_saves p on p.save_file_id=s.id where s.id='{SAVE}';
"""


def identity_sql():
    return f"""
insert into public.pokemon_identity_revisions(season_id,trainer_id,save_file_id,parsed_save_id,
 revision_number,capture_stream_id,capture_sequence,input_signature)
 values('{SEASON}','{TRAINER}','{SAVE}','{PARSED}',1,gen_random_uuid(),1,'{SHA}');
"""


def validate(pg):
    pg.sql(reward_seed() + f"""
set local role service_role;
do $$ begin
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0,'personal native badges without accepted identity cannot pay';
 assert public.league_death_totals('{PLAYER}')->>'blocking_reason'='death_history_source_unavailable','personal PC is not League death proof';
 assert not exists(select 1 from public.progress_reward_claims where season_id='{SEASON}'),'no personal-only reward claims';
 assert public.settle_observed_progress_rewards('{SEASON}',gen_random_uuid())=0,'unknown participant cannot pay';
end $$;
{identity_sql()}
do $$ begin
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0,'accepted identity with absent League pointer cannot pay';
end $$;
update public.season_players set current_save_file_id='{SAVE}' where id='{PLAYER}';
do $$ declare claim public.progress_reward_claims; begin
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0,'pointer hook already settled first badge';
 select * into claim from public.progress_reward_claims where season_id='{SEASON}' and trainer_id='{TRAINER}';
 assert claim.reward_key='badge:1' and claim.amount=4,'one badge pays configured four coins';
 assert claim.source_hash='{SHA}' and claim.identity_revision_id=(select id from public.pokemon_identity_revisions where save_file_id='{SAVE}'),'reward provenance points at exact source identity';
 assert (select amount=4 and reference_id=claim.id and metadata->>'save_file_id'='{SAVE}'
  from public.coin_transactions where id=claim.coin_transaction_id),'claim has exactly matching ledger transaction';
 update public.parsed_saves set payload=jsonb_set(payload,'{{native_progress,badge_flags}}','[true,true,false,false,false,false,false,false]') where id='{PARSED}';
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=1,'second badge pays only its missing ordinal';
 assert (select count(*)=2 and sum(amount)=8 from public.progress_reward_claims where season_id='{SEASON}'),'two claims, eight coins';
 insert into public.coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type,reference_type)
  values('{SEASON}','{TRAINER}','{PLAYER}',-3,'purchase','077-synthetic'),
        ('{SEASON}','{TRAINER}','{PLAYER}',-1,'penalty','077-synthetic');
 assert (select balance='4' from public.public_coin_balances where season_id='{SEASON}' and trainer_id='{TRAINER}'),'wallet is eight earned less valid deductions';
 update public.parsed_saves set payload=jsonb_set(payload,'{{native_progress,badge_flags}}','[true,true,true,false,false,false,false,false]') where id='{PARSED}';
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=1,'later third badge pays one';
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0,'repeated settlement is idempotent';
 assert (select balance='8' from public.public_coin_balances where season_id='{SEASON}' and trainer_id='{TRAINER}'),'balance reconciles all earned and spent entries';
 update public.parsed_saves set payload=jsonb_set(payload,'{{native_progress,badge_flags}}','[true,false,false,false,false,false,false,false]') where id='{PARSED}';
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0,'progress regression cannot replay ordinal rewards';
 update public.parsed_saves set payload=jsonb_set(payload,'{{native_progress,badge_flags}}','[true]') where id='{PARSED}';
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0,'malformed flags fail closed';
 assert not has_function_privilege('anon','public.settle_observed_progress_rewards(uuid,uuid)','execute')
  and not has_function_privilege('authenticated','public.settle_observed_progress_rewards(uuid,uuid)','execute'),'browser roles cannot invoke reward settlement';
 assert (select count(*)=3 from public.progress_reward_claims where season_id='{SEASON}'),'no hidden duplicate claims';
end $$;
rollback;
""")
    # All early zero-return gates are exercised before any eligible reward.
    pg.sql(reward_seed() + identity_sql() + f"""
do $$ begin
 update public.trainers set globally_enabled=false where id='{TRAINER}';
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0,'disabled trainer';
 update public.trainers set globally_enabled=true where id='{TRAINER}';
 update public.season_players set status='retired' where id='{PLAYER}';
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0,'inactive participant';
 update public.season_players set status='active' where id='{PLAYER}';
 update public.seasons set status='draft' where id='{SEASON}';
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0,'draft season';
 update public.seasons set status='active' where id='{SEASON}';
 update public.season_config_versions set effective_from_matchday=2 where season_id='{SEASON}';
 update public.season_players set current_save_file_id='{SAVE}' where id='{PLAYER}';
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0,'future config cannot pay early';
 update public.season_config_versions set effective_from_matchday=1 where season_id='{SEASON}';
 update public.parsed_saves set payload=jsonb_set(payload,'{{source_hash}}',to_jsonb(repeat('b',64))) where id='{PARSED}';
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0,'wrong source hash';
 update public.parsed_saves set payload=jsonb_set(payload,'{{source_hash}}',to_jsonb('{SHA}'::text)) where id='{PARSED}';
 update public.parsed_saves set payload=jsonb_set(payload,'{{trainer_id}}',to_jsonb(gen_random_uuid()::text)) where id='{PARSED}';
 assert public.settle_observed_progress_rewards('{SEASON}','{TRAINER}')=0,'foreign payload trainer';
 assert not exists(select 1 from public.progress_reward_claims where season_id='{SEASON}'),'ineligible cases issued no credit';
end $$;
rollback;
""")
    checks = ["personal vs League scope; configured 1/2/later badge settlement; source provenance; high-water, replay and deductions; all early eligibility gates and browser privileges"]
    for box in (7, 4):
        prefix, v = death_seed()
        if box != 7:
            prefix = prefix.replace("'active',7", f"'active',{box}")
            prefix = prefix.replace("box=7", f"box={box}").replace("then 7 else 1", f"then {box} else 1")
        pg.sql(prefix + f"""
set local role service_role;
select pg_temp.observe(array[1,2,3]);
do $$ declare x jsonb; rows_before bigint; frozen jsonb; begin
 x=public.league_death_totals('{v['pid']}');
 assert x->>'known'='false' and x->>'actual_deaths' is null,'observed occupancy does not invent historical baseline';
 assert (x->>'occupied')::int=3 and (x->>'recorded_deaths')::int=3,'three distinct identity-backed events in participant configured box';
 x=public.league_general_read('{v['sid']}');
 assert x#>>'{{rows,0,total_points}}' is null and x#>>'{{rows,0,historical_deaths}}' is null,'unknown historical evidence leaves NET and deaths unknown';
 perform pg_temp.confirm(3,0,3);
 x=public.league_general_read('{v['sid']}');
 assert (x#>>'{{rows,0,historical_deaths}}')::int=3 and (x#>>'{{rows,0,total_points}}')::numeric=-0.3,'zero victories plus three confirmed ordinary deaths is -0.3 NET';
 perform pg_temp.observe(array[1,2,3]);
 perform pg_temp.observe('{{}}');
 perform pg_temp.observe(array[1,2,3]);
 assert (public.league_death_totals('{v['pid']}')->>'actual_deaths')::int=3,'resync and movement never duplicate or erase death history';
 perform public.league_freeze_death_segment('{v['sid']}','{v['day1']}','{v['tid']}');
 frozen=public.league_death_snapshot('{v['pid']}','{v['day1']}');
 perform pg_temp.observe(array[1,2,3,4]);
 assert public.league_death_snapshot('{v['pid']}','{v['day1']}')=frozen,'later observation leaves frozen evidence unchanged';
 assert not has_table_privilege('authenticated','public.league_death_events','select'),'historical event table stays private';
end $$;
rollback;
""")
        checks.append(f"Box{box}: three deaths observed once, audited baseline, unknown preserved, -0.3 NET, repeated/moved source and frozen snapshot")
    prefix, v = death_seed()
    pg.sql(prefix + f"""
update public.seasons set current_matchday_id=null where id='{v['sid']}';
delete from public.matchdays where season_id='{v['sid']}';
set local role service_role;
select pg_temp.observe(array[1,2,3]);
do $$ declare x jsonb; begin
 x=public.league_general_read('{v['sid']}');
 assert x#>>'{{rows,0,total_points}}' is null,'before J1 missing historical evidence remains unknown';
 perform pg_temp.confirm(3,0,3);
 x=public.league_general_read('{v['sid']}');
 assert (x#>>'{{rows,0,total_points}}')::numeric=-0.3,'before any matchday three confirmed ordinary deaths produce -0.3 NET';
 assert x#>>'{{rows,0,points_provisional}}'='true','preseason NET is explicitly provisional';
 assert (select count(*)=3 from public.league_death_events where season_player_id='{v['pid']}' and phase='preseason'),'preseason events keep their actual phase';
 assert not exists(select 1 from public.matchday_snapshots where season_id='{v['sid']}'),'read and reconciliation do not fabricate an official closing';
end $$;
rollback;
""")
    checks.append("before J1: unknown until audited history, then -0.3 provisional NET with no fabricated matchday or rewards")
    return "PASS: " + "; ".join(checks)


def validate_concurrency(pg):
    # A dedicated synthetic fixture is committed so two real transactions can
    # contend for the same participant wallet mutex. No remote URL is accepted.
    pg.sql(reward_seed() + f"""
update public.parsed_saves set payload=jsonb_set(payload,'{{native_progress,badge_flags}}','[true,true,false,false,false,false,false,false]') where id='{PARSED}';
-- The source pointer alone cannot settle without the identity. Add the raw
-- synthetic revision afterwards, then exercise the normal service procedure.
update public.season_players set current_save_file_id='{SAVE}' where id='{PLAYER}';
{identity_sql()}
commit;
""")
    barrier = Barrier(2)
    def settle():
        with psycopg.connect(host="127.0.0.1", port=pg.port, user="supabase_admin", dbname=pg.database) as conn:
            conn.execute("set local role service_role")
            barrier.wait(timeout=15)
            return conn.execute("select public.settle_observed_progress_rewards(%s,%s)", (SEASON, TRAINER)).fetchone()[0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: settle(), range(2)))
    assert sorted(results) == [0, 2], results
    pg.sql(f"""do $$ begin
 assert (select count(*)=2 and sum(amount)=8 from public.progress_reward_claims where season_id='{SEASON}'),'concurrent rewards exactly once';
 assert (select count(*)=2 and sum(amount)=8 from public.coin_transactions where season_id='{SEASON}'),'one coin transaction per ordinal';
end $$;""")
    return "PASS: two simultaneous reconciliations serialize -> two badge claims/two ledger entries/eight coins, never duplicated"


def main():
    from tools.phase30_release_audit import SupabaseLikePG
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, default=Path(os.environ["LOCALAPPDATA"])/"Temp/phase10-5l-pg17/pgsql/bin")
    parser.add_argument("--port", type=int, default=55598)
    parser.add_argument("--upto", type=int, default=76)
    args = parser.parse_args()
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        migrations = sorted((Path(__file__).resolve().parents[1]/"supabase/v2/migrations").glob("*.sql"))
        for migration in migrations:
            if int(migration.name[:3]) <= args.upto:
                pg.sql(migration.read_text(encoding="utf-8"))
        print(validate(pg))
        print(validate_concurrency(pg))
    finally:
        pg.stop(remove=True)


if __name__ == "__main__":
    main()
