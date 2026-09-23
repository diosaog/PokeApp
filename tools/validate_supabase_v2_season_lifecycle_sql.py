"""Loopback-only 8J races and full public state rollback injection."""
from uuid import uuid4
from app.repositories.errors import PersistenceError
from tools.validate_season_lifecycle_fixtures import SeasonLifecycleFixtures, require
from tools.validate_supabase_v2_identity_sql import LocalClient, literal


def validate_season_lifecycle(args, sql):
    ids={role:str(uuid4()) for role in ('admin','other','owner')}
    readers={role:LocalClient(args,'authenticated',uid) for role,uid in ids.items()}
    readers['anon']=LocalClient(args,'anon'); client=LocalClient(args)
    f=SeasonLifecycleFixtures(client,readers,ids)
    try: f.run()
    finally: f.cleanup()
    print(f'Season lifecycle PostgreSQL RESULT ok groups={len(f.checks)}',flush=True)
    f=SeasonLifecycleFixtures(client,readers,ids)
    try:
        f.setup()
        finish,_=f.complete(); archive,_=f.complete(); f.life('finish',archive)
        # Re-establish only the synthetic completed season's ACTIVE review state.
        client.table('seasons').update({'status':'active'}).eq('id',finish).execute()
        discard=f.draft()
        tables=client.execute("select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'").data
        def snapshot():
            return {t:sorted(client.table(t).select('*').execute().data,key=lambda x:repr(sorted(x.items()))) for t in tables}
        points=(('finish',finish,'seasons'),('finish',finish,'activity_events'),
            ('archive',archive,'seasons'),('archive',archive,'season_archive_snapshots'),
            ('archive',archive,'hall_of_fame_entries'),('archive',archive,'activity_events'),
            ('discard',discard,'seasons'),('finish',finish,'admin_operation_receipts'),
            ('archive',archive,'admin_operation_receipts'),('discard',discard,'admin_operation_receipts'))
        for op,sid,table in points:
            before=snapshot(); column='id' if table=='seasons' else 'season_id'
            sql(args,f"create function public.__phase8j_fail() returns trigger language plpgsql as $$ begin if new.{column}={literal(sid)}::uuid then raise exception 'injected' using errcode='P0001'; end if; return new; end $$; "
                +f'create trigger phase8j_failure after insert or update on public.{table} for each row execute function public.__phase8j_fail();')
            try:
                try: f.life(op,sid)
                except PersistenceError as exc: require(getattr(exc.__cause__,'code',None)=='P0001','Wrong injection failure '+op+'/'+table)
                else: raise AssertionError('Injection did not fire '+op+'/'+table)
                require(snapshot()==before,'Partial lifecycle committed '+op+'/'+table)
            finally: sql(args,f'drop trigger phase8j_failure on public.{table}; drop function public.__phase8j_fail();')
            print('PASS exact lifecycle rollback '+op+'/'+table,flush=True)
    finally: f.cleanup()


if __name__=='__main__':
    import argparse
    from tools.validate_supabase_v2_schema import _psql_text
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--psql',required=True); p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',default='55439'); p.add_argument('--database',default='pokeapp_v2_validation_phase8h')
    p.add_argument('--user',default='postgres'); p.add_argument('--password',default='')
    args=p.parse_args(); LocalClient(args); validate_season_lifecycle(args,_psql_text)
