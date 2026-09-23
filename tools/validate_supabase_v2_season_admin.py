"""Opt-in real JWT + FastAPI + PostgREST staging checks; synthetic V2 only."""
import argparse
from dataclasses import replace
from pathlib import Path
import secrets
import sys
from threading import local
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.supabase_repository import SupabaseTrainerAuthRepository
from app.auth.supabase_adapter import SupabaseAuthClient
from app.repositories.supabase.season_admin import SeasonAdminRejected, SupabaseSeasonAdminRepository
from tools.validate_season_admin_fixtures import SeasonAdminFixtures, require
from tools.validate_supabase_v2_redemptions import WorkerClient
from tools.validate_supabase_v2_rls import SupabaseHttp
from tools.validate_supabase_v2_team_lock import staging_config
from tools.validate_supabase_v2_team_lock import TeamLockValidation
from tools.validate_supabase_v2_purchases import PurchaseValidation
from tools.validate_robbery_fixtures import RobberyFixtures


class ApiTransport:
    def __init__(self, factory, tokens):
        self.factory,self.tokens,self.worker=factory,tokens,local()

    def execute(self,op,r):
        if not hasattr(self.worker,'client'): self.worker.client=self.factory()
        sid=r.get('season_id'); resource=r.get('resource_id')
        base='/v1/admin/seasons/'+str(sid)
        paths={
            'setup':('GET',base+'/setup'),'create':('POST','/v1/admin/seasons'),
            'rename':('PUT',base+'/name'),'add_participant':('POST',base+'/participants'),
            'remove_participant':('POST',base+'/participants/'+str(resource)+'/remove-from-draft'),
            'create_config':('POST',base+'/config-versions'),
            'replace_config':('POST',base+'/config-versions/'+str(resource)+'/replace-unused'),
            'initial_divisions':('PUT',base+'/initial-divisions'),
            'prepare':('POST',base+'/matchdays/prepare-current'),'activate':('POST',base+'/activate'),
        }
        method,path=paths[op]
        headers={'Authorization':'Bearer '+self.tokens[r['actor_trainer_id']]}
        if 'idempotency_key' in r: headers['Idempotency-Key']=r['idempotency_key']
        response=self.worker.client.request(method,path,headers=headers,json=r.get('body'))
        if response.status_code in (403,404,409,422):
            raise SeasonAdminRejected(response.json()['detail']['code'],response.status_code)
        require(response.status_code==200,'API operation '+op+' HTTP '+str(response.status_code))
        return response.json()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--env-file',type=Path,required=True)
    p.add_argument('--allow-staging-writes',action='store_true')
    args=p.parse_args()
    config=replace(staging_config(args.env_file,args.allow_staging_writes),run_id='phase8g1_validation_'+uuid4().hex)
    from fastapi.testclient import TestClient
    from supabase import create_client
    from supabase.lib.client_options import SyncClientOptions
    import httpx
    transports=[]; apis=[]
    def client(key):
        transport=httpx.Client(http2=False,timeout=60); transports.append(transport)
        return create_client(config.url,key,options=SyncClientOptions(httpx_client=transport))
    def api():
        backend=client(config.service_role_key)
        app=create_app(container=ApiContainer(token_verifier=SupabaseAuthClient(client(config.anon_key)),
            principal_repository=SupabaseTrainerAuthRepository(backend),season_admin_repository=SupabaseSeasonAdminRepository(backend)))
        c=TestClient(app); apis.append(c); return c
    http=SupabaseHttp(config); users={}; tokens={}; readers={}; fixture=None; failure=None; fixture_cleaned=False
    print('V2 staging='+config.url+'\nrun_id='+config.run_id+'\nsecrets=redacted',flush=True)
    try:
        for role in ('admin','other','owner'):
            email=config.run_id+'_'+role+'@'+config.email_domain; password=secrets.token_urlsafe(32)
            users[role]=http.auth_create_user(email,password)
            tokens[role]=http.auth_sign_in(email,password)
            readers[role]=client(config.anon_key); readers[role].postgrest.auth(tokens[role])
        readers['anon']=client(config.anon_key)
        class ApiFixtures(SeasonAdminFixtures):
            def setup(self):
                super().setup()
                self.repo=ApiTransport(api,{self.admin['id']:tokens['admin'],self.admin2['id']:tokens['other'],self.owner['id']:tokens['owner']})
        fixture=ApiFixtures(WorkerClient(lambda:client(config.service_role_key)),readers,users,config.run_id)
        fixture.run()
        fixture.cleanup(); fixture_cleaned=True
        # Reuse the established regression suites, but keep this task's prefix.
        for suffix,kind in (('teamlock',TeamLockValidation),('purchase',PurchaseValidation)):
            regression=kind(replace(config,run_id=config.run_id+'_'+suffix))
            try:
                if suffix=='teamlock': regression.validate(regression.setup())
                else:
                    regression.setup_context(); regression.validate_context(); regression.validate_purchases()
            finally:
                require(not regression.cleanup(),'Regression cleanup '+suffix)
            print('PASS RG'+('19' if suffix=='teamlock' else '20')+' '+suffix+f' regression checks={len(regression.checks)}',flush=True)
        robbery=RobberyFixtures(WorkerClient(lambda:client(config.service_role_key)),readers,users,run_id=config.run_id+'_redemption')
        try: robbery.run()
        finally: robbery.cleanup()
        print(f'PASS RG21 redemption/robbery regression groups={len(robbery.checks)}',flush=True)
    except Exception as exc:
        failure=str(exc) if isinstance(exc,AssertionError) else type(exc).__name__
        if exc.__cause__: failure+=' cause='+type(exc.__cause__).__name__+' code='+str(getattr(exc.__cause__,'code',None))
    finally:
        if fixture and not fixture_cleaned:
            try: fixture.cleanup()
            except Exception as exc: failure='Fixture cleanup failed '+type(exc).__name__
        for uid in users.values():
            try:
                http.auth_delete_user(uid)
                require(http.request('GET',http.auth_url+'/admin/users/'+uid,auth='service',raise_on_error=False).status==404,'Auth cleanup')
            except Exception: failure='Auth cleanup failed'
        for c in apis: c.close()
        for c in transports: c.close()
    if failure:
        print('RESULT failed: '+failure,flush=True); return 1
    print(f'RESULT ok groups={len(fixture.checks)}; real JWT/API/PostgREST; Auth cleanup PASS',flush=True)
    return 0


if __name__=='__main__': raise SystemExit(main())
