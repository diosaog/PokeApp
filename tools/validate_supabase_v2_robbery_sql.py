"""Loopback-only robbery concurrency and forced rollback after every boundary."""
from uuid import uuid4

from app.repositories.errors import PersistenceError
from tools.validate_pokemon_identity_fixtures import require
from tools.validate_robbery_fixtures import RobberyFixtures
from tools.validate_supabase_v2_identity_sql import LocalClient


def validate_robbery(args, sql):
    users={role:str(uuid4()) for role in ('owner','other','admin')}
    readers={role:LocalClient(args,'authenticated',uid) for role,uid in users.items()}
    readers['anon']=LocalClient(args,'anon')
    fixture=RobberyFixtures(LocalClient(args),readers,users,run_id='phase8f1_validation_'+uuid4().hex)
    try: fixture.run()
    finally: fixture.cleanup()
    print(f'Robbery PostgreSQL RESULT ok checks={len(fixture.checks)}',flush=True)
    fixture=RobberyFixtures(LocalClient(args),readers,users,run_id='phase8f1_validation_'+uuid4().hex)
    try:
        fixture.setup()
        for table,operation in (('redemptions','insert'),('pokemon_entity_flags','insert'),
                                ('trainer_flags','insert'),('robbery_cycles','update'),
                                ('purchases','insert'),('purchases','update'),('activity_events','insert')):
            purchase=fixture.buy()
            tables=('redemptions','pokemon_entity_flags','trainer_flags','robbery_cycles','purchases','activity_events')
            def snapshot():
                return {t:sorted(fixture.select(t,season_id=fixture.season['id']),key=lambda r:str(r.get('id',r['season_id']))) for t in tables}
            before=snapshot()
            sql(args,f"""
create function public.__phase8f1_fail() returns trigger language plpgsql as $$
begin raise exception 'phase8f1 forced rollback'; end $$;
create trigger __phase8f1_fail after {operation} on public.{table}
for each row when (new.season_id='{fixture.season['id']}'::uuid)
execute function public.__phase8f1_fail();
""")
            try:
                try: fixture.use(purchase,fixture.target('other'))
                except PersistenceError as exc:
                    require(getattr(exc.__cause__,'code',None)=='P0001','not the forced rollback')
                else: raise AssertionError('forced failure did not abort')
                require(snapshot()==before,'partial robbery after '+table+' '+operation)
                print('PASS robbery rollback AFTER '+table+' '+operation,flush=True)
            finally:
                sql(args,f'drop trigger __phase8f1_fail on public.{table}; drop function public.__phase8f1_fail();')
    finally: fixture.cleanup()
