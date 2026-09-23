"""Isolated loopback PostgreSQL matchday gates and exact data rollback checks."""
from uuid import uuid4

from app.repositories.errors import PersistenceError
from tools.validate_matchday_fixtures import MatchdayFixtures, require
from tools.validate_supabase_v2_identity_sql import LocalClient, literal


def validate_matchdays(args, sql):
    ids={role:str(uuid4()) for role in ('admin','other','owner')}
    readers={role:LocalClient(args,'authenticated',uid) for role,uid in ids.items()}
    readers['anon']=LocalClient(args,'anon')
    client=LocalClient(args)
    f=MatchdayFixtures(client,readers,ids)
    try: f.run()
    finally: f.cleanup()
    print(f'Matchday PostgreSQL RESULT ok groups={len(f.checks)}',flush=True)
    f=MatchdayFixtures(client,readers,ids)
    try:
        f.setup()
        tables=client.execute("select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'").data
        def snapshot():
            return {t:sorted(client.table(t).select('*').execute().data,key=lambda x:repr(sorted(x.items()))) for t in tables}
        close_points=(
            ('matchday_snapshots','true'),('coin_transactions','true'),('purchases','new.origin_matchday_id is not null'),
            ('matchday_movements','true'),('division_memberships','new.effective_to_matchday_number is not null'),
            ('matchdays',"new.number=2"),('matches',"new.winner_id is null"),('shop_promotions','true'),
            ('seasons','true'),('matchdays',"new.status='closed'"),('activity_events',"new.type='MATCHDAY_ADMIN_CLOSE'"),
            ('admin_operation_receipts',"new.operation_scope like 'matchday_close:%'"))
        correction_points=(
            ('matchday_snapshot_revisions','new.revision=2'),
            ('coin_transactions',"new.transaction_type='compensation'"),
            ('purchases',"new.status='cancelled'"),
            ('matches','new.winner_id is null'),
            ('admin_operation_receipts',"new.operation_scope like 'matchday_correct:%'"))
        for operation,target,condition in (
            [('close',t,c) for t,c in close_points]+[('correct',t,c) for t,c in correction_points]
        ):
            sid,did=f.prepared_close()
            if operation=='correct': f.close(sid,did)
            correction=f.correction(sid,did) if operation=='correct' else None
            before=snapshot()
            scoped=('new.id=' if target=='seasons' else 'new.season_id=')+literal(sid)+'::uuid'
            sql(args,f"create function public.__phase8h_fail() returns trigger language plpgsql as $$ begin if {scoped} and ({condition}) then raise exception 'injected' using errcode='P0001'; end if; return new; end $$; "
                +f'create trigger phase8h_failure after insert or update on public.{target} for each row execute function public.__phase8h_fail();')
            try:
                try:
                    if operation=='correct': f.md('correct',sid,did,correction)
                    else: f.close(sid,did)
                except PersistenceError as exc: require(getattr(exc.__cause__,'code',None)=='P0001','Wrong injection failure '+target)
                else: raise AssertionError('Injection did not fire '+target)
                require(snapshot()==before,'Partial '+operation+' committed after '+target)
            finally:
                sql(args,f'drop trigger phase8h_failure on public.{target}; drop function public.__phase8h_fail();')
            print('PASS exact '+operation+' rollback '+target+' '+condition,flush=True)
    finally: f.cleanup()


if __name__=='__main__':
    import argparse
    from tools.validate_supabase_v2_schema import _psql_text
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--psql',required=True)
    p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',default='55439')
    p.add_argument('--database',default='pokeapp_v2_validation_phase8h')
    p.add_argument('--user',default='postgres')
    p.add_argument('--password',default='')
    p.add_argument('--rebuild',action='store_true',help='Reset ONLY isolated loopback validation DB before focused tests')
    args=p.parse_args()
    LocalClient(args)  # Validates target before any destructive local reset.
    if args.rebuild:
        from tools.validate_supabase_v2_schema import _psql, _build_schema, _prepare_supabase_role_mocks, RESET_SQL
        args.build_source='migrations'
        _prepare_supabase_role_mocks(args)
        _psql(args,RESET_SQL)
        _build_schema(args)
    validate_matchdays(args,_psql_text)
