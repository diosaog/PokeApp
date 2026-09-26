"""Opt-in Phase 8L staging: real Auth JWT -> FastAPI -> production PostgREST."""
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
from app.repositories.supabase.cups import SupabaseCupRepository
from app.repositories.supabase.trials import SupabaseTrialRepository
from app.repositories.supabase.matchdays import SupabaseMatchdayRepository
from app.repositories.supabase.participant_status import SupabaseParticipantStatusRepository
from app.repositories.supabase.season_lifecycle import SupabaseSeasonLifecycleRepository
from app.repositories.supabase.season_admin import SupabaseSeasonAdminRepository, SeasonAdminRejected
from tools.validate_cup_fixtures import CupFixtures, require
from tools.validate_supabase_v2_season_admin import ApiTransport
from tools.validate_supabase_v2_matchdays import MatchdayApiTransport
from tools.validate_supabase_v2_participant_status import ParticipantStatusApiTransport
from tools.validate_supabase_v2_season_lifecycle import LifecycleApiTransport
from tools.validate_supabase_v2_redemptions import WorkerClient
from tools.validate_supabase_v2_rls import SupabaseHttp
from tools.validate_supabase_v2_team_lock import staging_config
from tools.validate_trials_fixtures import TrialsFixtures
from tools.validate_supabase_v2_trials import TrialApiTransport


class CupApiTransport:
    def __init__(self,factory,tokens):
        self.factory,self.tokens,self.worker=factory,tokens,local()

    def send(self,method,path,r):
        if not hasattr(self.worker,'client'): self.worker.client=self.factory()
        headers={'Authorization':'Bearer '+self.tokens[r['actor_trainer_id']]}
        if 'idempotency_key' in r: headers['Idempotency-Key']=r['idempotency_key']
        response=self.worker.client.request(method,path,headers=headers,json=r.get('body'))
        if response.status_code in (403,404,409,422):
            detail=response.json()['detail']
            if response.status_code==422 and isinstance(detail,list): raise SeasonAdminRejected('INVALID_REQUEST',422)
            raise SeasonAdminRejected(detail['code'],response.status_code)
        require(response.status_code==200,'API Cup '+method+' HTTP '+str(response.status_code))
        return response.json()

    def execute(self,op,r):
        path='/v1/admin/seasons/'+r['season_id']+'/cups'
        if 'resource_id' in r: path+='/'+r['resource_id']
        if 'round_number' in r: path+='/rounds/'+str(r['round_number'])
        if 'side_id' in r: path+='/participants/'+r['side_id']
        if op!='create': path+='/'+op
        return self.send('PUT' if op in ('setup','results') else 'POST',path,r)

    def read(self,r):
        path='/v1/seasons/'+r['season_id']+'/cups'
        if 'resource_id' in r: path+='/'+r['resource_id']
        data=self.send('GET',path,r)
        return {'cup' if 'resource_id' in r else 'cups':data}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--allow-staging-writes',action='store_true')
    args=parser.parse_args()
    config=replace(staging_config(args.env_file,args.allow_staging_writes),run_id='phase8l_validation_'+uuid4().hex)
    from fastapi.testclient import TestClient
    from supabase import create_client
    from supabase.lib.client_options import SyncClientOptions
    import httpx
    transports=[]; apis=[]; users={}; tokens={}; readers={}; failure=None
    def client(key):
        transport=httpx.Client(http2=False,timeout=60); transports.append(transport)
        return create_client(config.url,key,options=SyncClientOptions(httpx_client=transport))
    def api():
        backend=client(config.service_role_key)
        container=ApiContainer(token_verifier=SupabaseAuthClient(client(config.anon_key)),
            principal_repository=SupabaseTrainerAuthRepository(backend),season_admin_repository=SupabaseSeasonAdminRepository(backend),
            matchday_repository=SupabaseMatchdayRepository(backend),participant_status_repository=SupabaseParticipantStatusRepository(backend),
            season_lifecycle_repository=SupabaseSeasonLifecycleRepository(backend),cup_repository=SupabaseCupRepository(backend),
            trial_repository=SupabaseTrialRepository(backend))
        test=TestClient(create_app(container=container)); apis.append(test); return test
    class ApiFixtures(CupFixtures):
        def setup(self):
            super().setup()
            mapped={self.admin['id']:tokens['admin'],self.admin2['id']:tokens['other'],self.owner['id']:tokens['owner']}
            self.cups=CupApiTransport(api,mapped); self.repo=ApiTransport(api,mapped)
            self.matchdays=MatchdayApiTransport(api,mapped); self.status_repo=ParticipantStatusApiTransport(api,mapped)
            self.lifecycle=LifecycleApiTransport(api,mapped); self.validates_request_schema=True
    class JudicialRegression(TrialsFixtures):
        def setup(self):
            super().setup()
            mapped={self.admin['id']:tokens['admin'],self.recorder['id']:tokens['other'],self.owner['id']:tokens['owner']}
            self.trials=TrialApiTransport(api,mapped); self.repo=ApiTransport(api,mapped)
            self.matchdays=MatchdayApiTransport(api,mapped); self.status_repo=ParticipantStatusApiTransport(api,mapped)
            self.lifecycle=LifecycleApiTransport(api,mapped); self.validates_request_schema=True
    http=SupabaseHttp(config)
    print('V2 staging='+config.url+'\nrun_id='+config.run_id+'\nsecrets=redacted',flush=True)
    try:
        for role in ('admin','other','owner'):
            password=secrets.token_urlsafe(32); email=config.run_id+'_'+role+'@'+config.email_domain
            users[role]=http.auth_create_user(email,password); tokens[role]=http.auth_sign_in(email,password)
            readers[role]=client(config.anon_key); readers[role].postgrest.auth(tokens[role])
        readers['anon']=client(config.anon_key)
        f=ApiFixtures(WorkerClient(lambda:client(config.service_role_key)),readers,users,config.run_id)
        try: f.run()
        finally: f.cleanup()
        print('PASS focused Cup and integrated 026/027/028/029 flows groups='+str(len(f.checks)),flush=True)
        regression=JudicialRegression(WorkerClient(lambda:client(config.service_role_key)),readers,users,config.run_id+'_030')
        try:
            regression.setup(); regression.effects()
        finally: regression.cleanup()
        print('PASS focused 030 sanction/replay/correction/League archive regression',flush=True)
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
    print('RESULT ok; real JWT/API/PostgREST; cleanup/Auth PASS',flush=True)
    return 0


if __name__=='__main__': raise SystemExit(main())
