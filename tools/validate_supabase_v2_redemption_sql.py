"""Loopback-only redemption, atomic rollback and role validation."""
from uuid import uuid4

from app.repositories.errors import PersistenceError
from tools.validate_redemption_fixtures import RedemptionFixtures
from tools.validate_pokemon_identity_fixtures import require
from tools.validate_supabase_v2_identity_sql import LocalClient


def validate_redemptions(args, sql):
    users={role:str(uuid4()) for role in ('owner','other','admin')}
    readers={role:LocalClient(args,'authenticated',uid) for role,uid in users.items()}
    readers['anon']=LocalClient(args,'anon')
    fixture=RedemptionFixtures(LocalClient(args),readers,users,run_id='phase8f_validation_'+uuid4().hex)
    try: fixture.run()
    finally: fixture.cleanup()
    print(f'Redemption PostgreSQL RESULT ok checks={len(fixture.checks)}',flush=True)

    fixture=RedemptionFixtures(LocalClient(args),readers,users,run_id='phase8f_validation_'+uuid4().hex)
    try:
        fixture.setup()
        for table in ('redemptions','pokemon_entity_flags','purchases','activity_events'):
            purchase=fixture.purchase('revivir_pokemon')
            baseline={t:fixture.select(t,season_id=fixture.season['id']) for t in
                      ('redemptions','pokemon_entity_flags','activity_events')}
            operation='update' if table=='purchases' else 'insert or update'
            sql(args,f"""
create function public.__phase8f_fail() returns trigger language plpgsql as $$
begin raise exception 'phase8f forced rollback'; end $$;
create trigger __phase8f_fail before {operation} on public.{table}
for each row when (new.season_id='{fixture.season['id']}'::uuid)
execute function public.__phase8f_fail();
""")
            try:
                try: fixture.redeem(purchase,fixture.dead[0])
                except PersistenceError as exc:
                    require(getattr(exc.__cause__,'code',None)=='P0001','not the forced rollback')
                else: raise AssertionError('forced write failure did not abort')
                require(fixture.select('purchases',id=purchase['id'])[0]['status']=='pending','rollback consumed purchase')
                for t,before in baseline.items():
                    require(fixture.select(t,season_id=fixture.season['id'])==before,'partial write '+t)
                print('PASS rollback at '+table,flush=True)
            finally:
                sql(args,f'drop trigger __phase8f_fail on public.{table}; drop function public.__phase8f_fail();')
    finally: fixture.cleanup()
