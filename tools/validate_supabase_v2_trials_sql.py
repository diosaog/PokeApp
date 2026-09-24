"""Loopback-only 030 races and exact rollback after each durable write boundary."""
from uuid import uuid4
from app.repositories.errors import PersistenceError
from tools.validate_trials_fixtures import TrialsFixtures, require
from tools.validate_supabase_v2_identity_sql import LocalClient, literal, identifier

SECURITY_AUDIT_SQL = """
select jsonb_build_object(
  'unsafe_functions',(select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and (p.proname like 'trials_%' or p.proname in ('api_trial_mutate','api_trials_read'))
      and (p.prosecdef or p.proconfig is null or has_function_privilege('anon',p.oid,'EXECUTE')
        or has_function_privilege('authenticated',p.oid,'EXECUTE') or not has_function_privilege('service_role',p.oid,'EXECUTE')
        or exists(select 1 from aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a where a.grantee=0 and a.privilege_type='EXECUTE'))),
  'browser_write_grants',(select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
    cross join (values('anon'),('authenticated')) r(role)
    where n.nspname='public' and c.relname in ('trial_cases','trial_votes','penalties','trial_case_revisions','trial_case_counters')
      and (has_table_privilege(r.role,c.oid,'INSERT,UPDATE,DELETE,TRUNCATE') or has_any_column_privilege(r.role,c.oid,'INSERT,UPDATE'))),
  'rls_tables',(select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace
    where n.nspname='public' and c.relname in ('trial_case_counters','trial_case_revisions') and c.relrowsecurity)
)
"""


def validate_trials(args, sql):
    ids={role:str(uuid4()) for role in ('admin','other','owner')}
    readers={r:LocalClient(args,'authenticated',u) for r,u in ids.items()}; readers['anon']=LocalClient(args,'anon')
    client=LocalClient(args); f=TrialsFixtures(client,readers,ids)
    require(client.execute(SECURITY_AUDIT_SQL).data==dict(unsafe_functions=0,browser_write_grants=0,rls_tables=2),'030 grant/RLS catalog audit')
    try: f.run()
    finally: f.cleanup()
    print(f'Trials PostgreSQL RESULT ok groups={len(f.checks)}',flush=True)
    f=TrialsFixtures(client,readers,ids)
    try:
        f.setup(); sid,did=f.season(3); cid=f.case(sid); corrected=f.case(sid)
        f.decision(sid,corrected,[dict(type='coins_reduction',amount=20)])
        sanctions=[dict(type='coins_reduction',amount=30),dict(type='points_reduction',amount='1.25'),
            dict(type='store_ban',duration_matchdays=2),dict(type='pokemon_release',text='Note'),dict(type='other',text='Warning')]
        tables=client.execute("select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'").data
        def snapshot():
            # One consistent database snapshot, without one process per table.
            parts=["select "+literal(t)+" as name, coalesce(jsonb_agg(to_jsonb(x) order by to_jsonb(x)::text),'[]') as rows from public."+identifier(t)+" x" for t in tables]
            return client.execute('select jsonb_object_agg(name,rows) from ('+' union all '.join(parts)+') q').data
        points=[('create','trial_case_counters','true'),('create','trial_cases','true'),('create','trial_case_revisions','true'),
            ('resolve','trial_case_revisions','true'),('resolve','coin_transactions','true'),('resolve','trial_cases','true'),
            ('resolve','activity_events','true'),('resolve','admin_operation_receipts','true'),
            ('correct','trial_case_revisions','true'),('correct','coin_transactions','true'),('correct','admin_operation_receipts','true')]
        points += [('resolve','penalties',"new.penalty_type="+literal(kind)) for kind in ('coins_reduction','other','points_reduction','pokemon_release','store_ban')]
        for op,table,condition in points:
            before=snapshot()
            sql(args,f"create function public.__phase8k1_fail() returns trigger language plpgsql as $$ begin if new.season_id={literal(sid)}::uuid and ({condition}) then raise exception 'injected' using errcode='P0001'; end if; return new; end $$; "
                +f'create trigger phase8k1_failure after insert or update on public.{table} for each row execute function public.__phase8k1_fail();')
            try:
                try:
                    if op=='create': f.case(sid)
                    elif op=='correct': f.decision(sid,corrected,verdict='not_guilty',op='correct')
                    else: f.decision(sid,cid,sanctions)
                except PersistenceError as exc:
                    require(getattr(exc.__cause__,'code',None)=='P0001','Wrong injected failure '+op+'/'+table)
                else: raise AssertionError('Injection did not fire '+op+'/'+table)
                require(snapshot()==before,'Partial trial commit '+op+'/'+table)
            finally: sql(args,f'drop trigger phase8k1_failure on public.{table}; drop function public.__phase8k1_fail();')
            print('PASS exact trial rollback '+op+'/'+table+'/'+condition,flush=True)
    finally: f.cleanup()


if __name__=='__main__':
    import argparse
    from tools.validate_supabase_v2_schema import _psql_text
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--psql',required=True); p.add_argument('--host',default='127.0.0.1')
    p.add_argument('--port',default='55439'); p.add_argument('--database',default='pokeapp_v2_validation_phase8k1')
    p.add_argument('--user',default='postgres'); p.add_argument('--password',default='')
    args=p.parse_args(); LocalClient(args); validate_trials(args,_psql_text)
