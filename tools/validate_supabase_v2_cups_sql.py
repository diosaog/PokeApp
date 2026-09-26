"""Loopback-only focused Cup flows, ten race families and major rollback boundaries."""
import argparse
from uuid import uuid4
from tools.validate_cup_fixtures import CupFixtures, require
from tools.validate_supabase_v2_identity_sql import LocalClient, literal, identifier
from tools.validate_supabase_v2_schema import _psql_text
from app.repositories.errors import PersistenceError


def validate_cups(args, sql=_psql_text, rollback=True):
    ids={r:str(uuid4()) for r in ('admin','other','owner')}
    readers={r:LocalClient(args,'authenticated',uid) for r,uid in ids.items()}
    readers['anon']=LocalClient(args,'anon'); client=LocalClient(args)
    f=CupFixtures(client,readers,ids)
    try: f.run()
    finally: f.cleanup()
    if rollback:
        f=CupFixtures(client,readers,ids)
        try:
            f.setup(); sid=f.cup_season()
            draft=f.create_cup(sid,'elimination',4,start=False)
            closing=f.create_cup(sid,'elimination',4); c=f.document(sid,closing)
            f.cup('results',sid,closing,f.result_body(c),round_number=1)
            dq=f.create_cup(sid,'elimination',4)
            final=f.create_cup(sid,'elimination',2); f.finish_cup(sid,final,False)
            tables=client.execute("select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'").data
            query='select jsonb_object_agg(name,rows) from ('+' union all '.join(
                'select '+literal(t)+' as name,coalesce(jsonb_agg(to_jsonb(x) order by to_jsonb(x)::text),\'[]\') as rows from public.'+identifier(t)+' x' for t in tables)+') q'
            def snapshot(): return client.execute(query).data
            points=[('start',draft,'cup_matches',None),('close',closing,'cup_standings',1),('close',closing,'cup_rounds',2),
                ('disqualify',dq,'cup_participants',None),('disqualify',dq,'cup_matches',None),
                ('finalize',final,'cup_certificates',None),('finalize',final,'hall_of_fame_entries',None),
                ('finalize',final,'activity_events',None),('finalize',final,'admin_operation_receipts',None)]
            for op,cid,table,number in points:
                before=snapshot(); condition=f'new.cup_id={literal(cid)}::uuid' if table.startswith('cup_') or table=='hall_of_fame_entries' else f'new.season_id={literal(sid)}::uuid'
                if table=='cup_rounds': condition+=f' and new.number={number}'
                sql(args,"create function public.__phase8l_fail() returns trigger language plpgsql as $$ begin if "+condition+" then raise exception 'injected' using errcode='P0001'; end if; return new; end $$; "+
                    f'create trigger phase8l_failure after insert or update on public.{table} for each row execute function public.__phase8l_fail();')
                try:
                    c=f.document(sid,cid); body=dict(expected_revision=c['revision']); kw={}
                    if op=='close': kw['round_number']=1
                    if op=='disqualify': body['reason']='Rollback'; kw['side_id']=c['sides'][0]['id']
                    try: f.cup(op,sid,cid,body,**kw)
                    except PersistenceError as exc: require(getattr(exc.__cause__,'code',None)=='P0001','Wrong rollback failure '+op+'/'+table)
                    else: raise AssertionError('Failure injection did not fire '+op+'/'+table)
                    require(snapshot()==before,'Partial Cup commit '+op+'/'+table)
                finally: sql(args,f'drop trigger phase8l_failure on public.{table}; drop function public.__phase8l_fail();')
                print('PASS exact all-public rollback '+op+'/'+table,flush=True)
        finally: f.cleanup()
    print('Cup PostgreSQL RESULT ok',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--psql',required=True); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',default='55439')
    p.add_argument('--database',default='pokeapp_v2_validation_phase8l'); p.add_argument('--user',default='postgres'); p.add_argument('--password',default='')
    p.add_argument('--skip-rollback',action='store_true')
    args=p.parse_args(); LocalClient(args); validate_cups(args,rollback=not args.skip_rollback)
