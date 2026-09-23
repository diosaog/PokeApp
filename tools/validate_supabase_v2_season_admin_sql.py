"""Loopback-only Phase 8G.1 business races and exact-state failure injection."""
from uuid import uuid4

from app.repositories.errors import PersistenceError
from tools.validate_season_admin_fixtures import SeasonAdminFixtures, require
from tools.validate_supabase_v2_identity_sql import LocalClient, literal


def validate_season_admin(args, sql):
    ids={role:str(uuid4()) for role in ('admin','other','owner')}
    readers={role:LocalClient(args,'authenticated',uid) for role,uid in ids.items()}
    readers['anon']=LocalClient(args,'anon')
    client=LocalClient(args)
    refs=client.execute("select jsonb_agg(distinct conrelid::regclass::text) from pg_constraint "
        "where contype='f' and confrelid='public.season_config_versions'::regclass").data
    require(set(refs)=={'matchdays','matchday_snapshots'},'Config used predicate must cover every actual FK')
    fixtures=SeasonAdminFixtures(client,readers,ids)
    try: fixtures.run()
    finally: fixtures.cleanup()
    print(f'Season admin PostgreSQL RESULT ok checks={len(fixtures.checks)}',flush=True)

    # Full fixture data snapshots, including unrelated economy/save/catalog state.
    tables=client.execute("select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'").data
    def snapshot():
        return {t:sorted(client.table(t).select('*').execute().data,key=lambda r:repr(sorted(r.items()))) for t in tables}

    f=SeasonAdminFixtures(client,readers,ids)
    try:
        f.setup()
        for case in ('create','participant','config','memberships','matchday','matches','pointer','activation','receipt'):
            sid=None
            if case in ('create','receipt'):
                action=lambda:f.call('create',body={'name':f.run_id+'_rollback'})
                target='season_admin_state' if case=='create' else 'admin_operation_receipts'
            elif case=='participant':
                sid=f.draft(); target='season_players'; action=lambda:f.add(sid)
            elif case=='config':
                sid=f.roster(); target='season_config_versions'; body=f.config(sid)
                action=lambda:f.call('create_config',sid,body)
            elif case=='memberships':
                sid=f.roster(); c=f.call('create_config',sid,f.config(sid)); body=f.divisions_body(sid,c['resource_id'])
                target='division_memberships'; action=lambda:f.call('initial_divisions',sid,body)
            else:
                sid=f.ready(prepare=case=='activation'); body={'expected_setup_revision':f.state(sid)['setup_revision']}
                target={'matchday':'matchdays','matches':'matches','pointer':'seasons','activation':'seasons'}[case]
                action=lambda:f.call('activate' if case=='activation' else 'prepare',sid,body)
            before=snapshot()
            condition='true' if sid is None else ('new.id=' if target=='seasons' else 'new.season_id=')+literal(sid)+'::uuid'
            if case=='pointer': condition+=' and new.current_matchday_id is not null'
            if case=='activation': condition+=" and new.status='active'"
            if case=='memberships': condition+=' and (select count(*) from public.division_memberships where season_id=new.season_id)=2'
            sql(args,"create function public.__phase8g1_fail() returns trigger language plpgsql as $$ begin if "+condition+
                " then raise exception 'injected' using errcode='P0001'; end if; return new; end $$; "
                +f'create trigger phase8g1_failure after insert or update on public.{target} for each row execute function public.__phase8g1_fail();')
            try:
                try: action()
                except PersistenceError as exc: require(getattr(exc.__cause__,'code',None)=='P0001','Wrong injection failure')
                else: raise AssertionError('Injection did not fire '+case)
                require(snapshot()==before,'Partial commit after '+case)
            finally:
                sql(args,f'drop trigger phase8g1_failure on public.{target}; drop function public.__phase8g1_fail();')
            print('PASS exact rollback '+case,flush=True)
    finally: f.cleanup()


if __name__=='__main__':
    import argparse
    from tools.validate_supabase_v2_schema import _psql_text
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--psql',required=True)
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',default='55439')
    p.add_argument('--database',default='pokeapp_v2_validation_phase8g1')
    p.add_argument('--user',default='postgres')
    p.add_argument('--password',default='')
    validate_season_admin(p.parse_args(),_psql_text)
