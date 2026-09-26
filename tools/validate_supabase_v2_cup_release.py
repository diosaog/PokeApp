"""Final 8L local gate: reproducible 001-031/bootstrap and relevant 026-030 regressions.

Only disposable loopback databases are accepted. Never use on staging.
"""
import argparse
from copy import copy
from pathlib import Path
import re
import subprocess
import tempfile
from uuid import uuid4
from tools.validate_supabase_v2_identity_sql import LocalClient
from tools.validate_supabase_v2_schema import (MIGRATIONS, RESET_SQL, _psql, _psql_text,
    _prepare_supabase_role_mocks, _apply_bootstrap, _render_validation_sql, RLS_VALIDATION_SQL)
from tools.validate_supabase_v2_cups_sql import validate_cups
from tools.validate_season_admin_fixtures import SeasonAdminFixtures, require
from tools.validate_matchday_fixtures import MatchdayFixtures
from tools.validate_participant_status_fixtures import ParticipantStatusFixtures
from tools.validate_season_lifecycle_fixtures import SeasonLifecycleFixtures
from tools.validate_trials_fixtures import TrialsFixtures

INHERITED = """
grant insert,update,delete,truncate on public.cups,public.cup_participants,public.cup_matches,public.cup_standings,public.hall_of_fame_entries to authenticated;
grant update(metadata),insert(metadata) on public.cups,public.cup_participants,public.cup_matches,public.cup_standings,public.hall_of_fame_entries to authenticated;
grant update(name),insert(name) on public.public_cups to authenticated;
"""

CATALOG = """
do $$ declare bad integer; begin
 select count(*) into bad from information_schema.role_table_grants where table_schema='public'
   and grantee in ('PUBLIC','anon','authenticated') and privilege_type in ('INSERT','UPDATE','DELETE','TRUNCATE')
   and table_name in ('cups','cup_participants','cup_side_members','cup_matches','cup_standings','cup_rounds','cup_history','cup_certificates',
      'public_cups','public_cup_participants','public_cup_matches','public_cup_standings','public_hall_of_fame');
 if bad<>0 then raise exception 'Browser table Cup writes: %',bad; end if;
 select count(*) into bad from information_schema.role_column_grants where table_schema='public'
   and grantee in ('PUBLIC','anon','authenticated') and privilege_type in ('INSERT','UPDATE')
   and table_name in ('cups','cup_participants','cup_side_members','cup_matches','cup_standings','cup_rounds','cup_history','cup_certificates',
      'public_cups','public_cup_participants','public_cup_matches','public_cup_standings','public_hall_of_fame');
 if bad<>0 then raise exception 'Browser column Cup writes: %',bad; end if;
 select count(*) into bad from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public'
   and (p.proname like 'cup_%' or p.proname like 'api_cup_%' or p.proname='api_admin_cup')
   and (p.prosecdef or p.proconfig is null or has_function_privilege('anon',p.oid,'EXECUTE') or has_function_privilege('authenticated',p.oid,'EXECUTE'));
 if bad<>0 then raise exception 'Unsafe Cup RPC/helper: %',bad; end if;
 select count(*) into bad from pg_class where relnamespace='public'::regnamespace and relname in ('cup_side_members','cup_rounds','cup_history','cup_certificates') and relrowsecurity;
 if bad<>4 then raise exception 'Cup RLS table count: %',bad; end if;
 if not exists(select 1 from pg_class where oid='public.public_hall_of_fame'::regclass and reloptions @> array['security_invoker=false','security_barrier=true']) then
   raise exception 'Hall security options changed'; end if;
end $$;
"""


def build(args,bootstrap=False):
    _psql(args,RESET_SQL)
    if bootstrap:
        _apply_bootstrap(args)
    else:
        for migration in MIGRATIONS:
            if migration.name.startswith('031_'): _psql_text(args,INHERITED)
            _psql(args,migration)
    _psql_text(args,CATALOG)


def dump(args,label):
    command=[str(Path(args.psql).with_name('pg_dump.exe')),'-h',args.host,'-p',str(args.port),'-U',args.user,
        '-d',args.database,'--schema-only','--schema=public']
    import os
    result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',check=True,env=dict(os.environ,PGPASSWORD=args.password))
    normalized='\n'.join(line for line in result.stdout.splitlines() if not re.match(r'^\\(?:un)?restrict ',line))+'\n'
    path=Path(tempfile.gettempdir())/('phase8l-'+label+'-schema.sql'); path.write_text(normalized,encoding='utf-8')
    return normalized


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--psql',required=True); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',default='55439')
    p.add_argument('--database',default='pokeapp_v2_validation_phase8l'); p.add_argument('--user',default='postgres'); p.add_argument('--password',default='')
    p.add_argument('--allow-destructive-reset',action='store_true'); p.add_argument('--skip-regressions',action='store_true')
    args=p.parse_args(); LocalClient(args)
    if not args.allow_destructive_reset: raise SystemExit('Explicit local reset flag required')
    other=copy(args); other.database=args.database+'_bootstrap'; LocalClient(other)
    import os
    # CREATE DATABASE cannot run inside the SQL client's transaction.
    exists=subprocess.run([args.psql,'-h',args.host,'-p',str(args.port),'-U',args.user,'-d','postgres','-qAt','-c',
        "select 1 from pg_database where datname='"+other.database.replace("'","''")+"'"],capture_output=True,text=True,check=True,
        env=dict(os.environ,PGPASSWORD=args.password)).stdout.strip()
    if not exists:
        subprocess.run([str(Path(args.psql).with_name('createdb.exe')),'-h',args.host,'-p',str(args.port),'-U',args.user,other.database],check=True,
            env=dict(os.environ,PGPASSWORD=args.password))
    _prepare_supabase_role_mocks(args)
    for label,target,bootstrap in (('migrations',args,False),('bootstrap',other,True)):
        for iteration in range(2):
            build(target,bootstrap); print(f'PASS {label} rebuild {iteration+1}',flush=True)
        _psql_text(target,_render_validation_sql()); _psql_text(target,RLS_VALIDATION_SQL)
    a,b=dump(args,'migrations'),dump(other,'bootstrap')
    require(a==b,'Schema/grants/ownership mismatch')
    print('PASS exact schema/grants/ownership parity lines='+str(len(a.splitlines())),flush=True)
    if not args.skip_regressions:
        ids={r:str(uuid4()) for r in ('admin','other','owner')}
        readers={r:LocalClient(args,'authenticated',uid) for r,uid in ids.items()}; readers['anon']=LocalClient(args,'anon')
        for kind in (SeasonAdminFixtures,MatchdayFixtures,ParticipantStatusFixtures,SeasonLifecycleFixtures,TrialsFixtures):
            f=kind(LocalClient(args),readers,ids)
            try: f.run()
            finally: f.cleanup()
            print('PASS regression '+kind.__name__+' groups='+str(len(f.checks)),flush=True)
    validate_cups(args)
    _psql_text(args,CATALOG)
    require(dump(args,'migrations')==b,'Validation left a schema change')
    print('Cup release RESULT ok; final local gate complete',flush=True)


if __name__=='__main__': main()
