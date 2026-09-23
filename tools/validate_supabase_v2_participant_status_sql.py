"""Isolated PostgreSQL status races and exact whole-public-data rollback checks."""
from uuid import uuid4

from app.repositories.errors import PersistenceError
from tools.validate_participant_status_fixtures import ParticipantStatusFixtures, require
from tools.validate_supabase_v2_identity_sql import LocalClient, literal


def validate_participant_status(args, sql):
    ids={role:str(uuid4()) for role in ('admin','other','owner')}
    readers={role:LocalClient(args,'authenticated',uid) for role,uid in ids.items()}
    readers['anon']=LocalClient(args,'anon')
    client=LocalClient(args)
    f=ParticipantStatusFixtures(client,readers,ids)
    try: f.run()
    finally: f.cleanup()
    print(f'Participant status PostgreSQL RESULT ok groups={len(f.checks)}',flush=True)
    f=ParticipantStatusFixtures(client,readers,ids)
    try:
        f.setup()
        tables=client.execute("select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'").data
        def snapshot():
            return {t:sorted(client.table(t).select('*').execute().data,key=lambda x:repr(sorted(x.items()))) for t in tables}
        sid,did,players,entities,receipts=f.cycle_ready()
        player=players[-1]
        f.insert('trainer_flags',dict(season_id=sid,trainer_id=player['trainer_id'],season_player_id=player['id'],flag_type='robbed'))
        points=(('season_players',"new.status='retired'"),('division_memberships','true'),('matches','true'),
            ('trainer_flags','true'),('robbery_cycles','true'),('season_admin_state','true'),
            ('activity_events',"new.type='PARTICIPANT_STATUS_CHANGED'"),('admin_operation_receipts',"new.operation_scope like 'participant_status:%'"))
        for target,condition in points:
            before=snapshot()
            record='old' if target=='matches' else 'new'
            scoped=record+'.season_id='+literal(sid)+'::uuid'
            sql(args,f"create function public.__phase8i_fail() returns trigger language plpgsql as $$ begin if {scoped} and ({condition}) then raise exception 'injected' using errcode='P0001'; end if; return {record}; end $$; "
                +f'create trigger phase8i_failure after insert or update or delete on public.{target} for each row execute function public.__phase8i_fail();')
            try:
                try: f.change(sid,player['id'])
                except PersistenceError as exc: require(getattr(exc.__cause__,'code',None)=='P0001','Wrong injection failure '+target)
                else: raise AssertionError('Injection did not fire '+target)
                require(snapshot()==before,'Partial status mutation committed after '+target)
            finally:
                sql(args,f'drop trigger phase8i_failure on public.{target}; drop function public.__phase8i_fail();')
            print('PASS exact participant status rollback '+target,flush=True)
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
    args=p.parse_args()
    LocalClient(args)
    validate_participant_status(args,_psql_text)
