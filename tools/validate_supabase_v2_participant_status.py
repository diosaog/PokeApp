"""Opt-in Phase 8I real JWT/API/PostgREST fixtures on the pinned V2 staging project."""
import argparse
from dataclasses import replace
from pathlib import Path
import secrets
import sys
from threading import local
import traceback
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.supabase_repository import SupabaseTrainerAuthRepository
from app.auth.supabase_adapter import SupabaseAuthClient
from app.repositories.supabase.matchdays import SupabaseMatchdayRepository
from app.repositories.supabase.participant_status import SupabaseParticipantStatusRepository
from tools.validate_participant_status_fixtures import ParticipantStatusFixtures
from tools.validate_supabase_v2_matchdays import MatchdayApiTransport
from app.repositories.supabase.season_admin import SupabaseSeasonAdminRepository, SeasonAdminRejected
from tools.validate_matchday_fixtures import MatchdayFixtures, require
from tools.validate_season_admin_fixtures import SeasonAdminFixtures
from tools.validate_supabase_v2_season_admin import ApiTransport
from tools.validate_supabase_v2_redemptions import WorkerClient
from tools.validate_supabase_v2_rls import SupabaseHttp
from tools.validate_supabase_v2_team_lock import staging_config, TeamLockValidation
from tools.validate_supabase_v2_purchases import PurchaseValidation
from tools.validate_robbery_fixtures import RobberyFixtures


class ParticipantStatusApiTransport:
    def __init__(self,factory,tokens):
        self.factory,self.tokens,self.worker=factory,tokens,local()

    def execute(self,op,r):
        if not hasattr(self.worker,'client'): self.worker.client=self.factory()
        path='/v1/admin/seasons/'+r['season_id']+'/participants/'+r['resource_id']+'/'+op
        headers={'Authorization':'Bearer '+self.tokens[r['actor_trainer_id']], 'Idempotency-Key':r['idempotency_key']}
        response=self.worker.client.post(path,headers=headers,json=r['body'])
        if response.status_code in (403,404,409,422):
            detail=response.json()['detail']
            if response.status_code==422 and isinstance(detail,list): raise SeasonAdminRejected('INVALID_REQUEST',422)
            raise SeasonAdminRejected(detail['code'],response.status_code)
        require(response.status_code==200,'API '+op+' HTTP '+str(response.status_code))
        return response.json()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--allow-staging-writes',action='store_true')
    args=parser.parse_args()
    config=replace(staging_config(args.env_file,args.allow_staging_writes),run_id='phase8i_validation_'+uuid4().hex)
    from fastapi.testclient import TestClient
    from supabase import create_client
    from supabase.lib.client_options import SyncClientOptions
    import httpx
    transports=[]; apis=[]; users={}; tokens={}; readers={}; failure=None; count=0
    def client(key):
        transport=httpx.Client(http2=False,timeout=60); transports.append(transport)
        return create_client(config.url,key,options=SyncClientOptions(httpx_client=transport))
    def api():
        backend=client(config.service_role_key)
        container=ApiContainer(token_verifier=SupabaseAuthClient(client(config.anon_key)),
            principal_repository=SupabaseTrainerAuthRepository(backend),
            season_admin_repository=SupabaseSeasonAdminRepository(backend),matchday_repository=SupabaseMatchdayRepository(backend),
            participant_status_repository=SupabaseParticipantStatusRepository(backend))
        test=TestClient(create_app(container=container)); apis.append(test); return test
    http=SupabaseHttp(config)
    print('V2 staging='+config.url+'\nrun_id='+config.run_id+'\nsecrets=redacted',flush=True)
    try:
        for role in ('admin','other','owner'):
            email=config.run_id+'_'+role+'@'+config.email_domain; password=secrets.token_urlsafe(32)
            users[role]=http.auth_create_user(email,password)
            tokens[role]=http.auth_sign_in(email,password)
            readers[role]=client(config.anon_key); readers[role].postgrest.auth(tokens[role])
        readers['anon']=client(config.anon_key)
        class ApiFixtures(ParticipantStatusFixtures):
            def setup(self):
                super().setup()
                mapped={self.admin['id']:tokens['admin'],self.admin2['id']:tokens['other'],self.owner['id']:tokens['owner']}
                self.repo=ApiTransport(api,mapped)
                self.matchdays=MatchdayApiTransport(api,mapped)
                self.status_repo=ParticipantStatusApiTransport(api,mapped)
        fixture=ApiFixtures(WorkerClient(lambda:client(config.service_role_key)),readers,users,config.run_id)
        try: fixture.run()
        finally: fixture.cleanup()
        count=len(fixture.checks)
        class MatchdayRegression(MatchdayFixtures):
            def setup(self):
                super().setup()
                mapped={self.admin['id']:tokens['admin'],self.admin2['id']:tokens['other'],self.owner['id']:tokens['owner']}
                self.repo=ApiTransport(api,mapped)
                self.matchdays=MatchdayApiTransport(api,mapped)
        matchdays=MatchdayRegression(WorkerClient(lambda:client(config.service_role_key)),readers,users,config.run_id+'_matchdays')
        try: matchdays.run()
        finally: matchdays.cleanup()
        print(f'PASS 027 matchday regression groups={len(matchdays.checks)}',flush=True)
        class SetupRegression(SeasonAdminFixtures):
            def setup(self):
                super().setup(); self.validates_request_schema=True
                self.repo=ApiTransport(api,{self.admin['id']:tokens['admin'],self.admin2['id']:tokens['other'],self.owner['id']:tokens['owner']})
        setup=SetupRegression(WorkerClient(lambda:client(config.service_role_key)),readers,users,config.run_id+'_setup')
        try: setup.run()
        finally: setup.cleanup()
        print(f'PASS 026 setup regression groups={len(setup.checks)}',flush=True)
        for suffix,kind in (('teamlock',TeamLockValidation),('purchase',PurchaseValidation)):
            regression=kind(replace(config,run_id=config.run_id+'_'+suffix))
            try:
                if suffix=='teamlock': regression.validate(regression.setup())
                else:
                    regression.setup_context(); regression.validate_context(); regression.validate_purchases()
            finally: require(not regression.cleanup(),'Regression cleanup '+suffix)
            print(f'PASS {suffix} regression checks={len(regression.checks)}',flush=True)
        robbery=RobberyFixtures(WorkerClient(lambda:client(config.service_role_key)),readers,users,run_id=config.run_id+'_redemption')
        try: robbery.run()
        finally: robbery.cleanup()
        print(f'PASS redemption/robbery regression groups={len(robbery.checks)}',flush=True)
    except Exception as exc:
        failure=str(exc) if isinstance(exc,AssertionError) else type(exc).__name__
        frames=traceback.extract_tb(exc.__traceback__)
        if frames: failure+=' at '+Path(frames[-1].filename).name+':'+str(frames[-1].lineno)
    finally:
        for uid in users.values():
            try:
                http.auth_delete_user(uid)
                require(http.request('GET',http.auth_url+'/admin/users/'+uid,auth='service',raise_on_error=False).status==404,'Auth cleanup')
            except Exception: failure='Auth cleanup failed'
        for c in apis: c.close()
        for c in transports: c.close()
    if failure:
        print('RESULT failed: '+failure,flush=True); return 1
    print(f'RESULT ok groups={count}; real JWT/API/PostgREST; regressions PASS; Auth cleanup PASS',flush=True)
    return 0


if __name__=='__main__': raise SystemExit(main())
