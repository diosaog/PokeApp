"""Opt-in 8K.1 staging validation: real JWT/API/PostgREST, scoped fixtures and cleanup."""
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
from app.repositories.supabase.trials import SupabaseTrialRepository
from tools.validate_trials_fixtures import TrialsFixtures
from tools.validate_supabase_v2_season_lifecycle import LifecycleApiTransport
from app.repositories.supabase.season_lifecycle import SupabaseSeasonLifecycleRepository
from app.repositories.supabase.season_admin import SupabaseSeasonAdminRepository, SeasonAdminRejected
from tools.validate_season_lifecycle_fixtures import SeasonLifecycleFixtures
from tools.validate_participant_status_fixtures import ParticipantStatusFixtures
from tools.validate_supabase_v2_participant_status import ParticipantStatusApiTransport
from tools.validate_supabase_v2_matchdays import MatchdayApiTransport
from tools.validate_matchday_fixtures import MatchdayFixtures, require
from tools.validate_season_admin_fixtures import SeasonAdminFixtures
from tools.validate_supabase_v2_season_admin import ApiTransport
from tools.validate_supabase_v2_redemptions import WorkerClient
from tools.validate_supabase_v2_rls import SupabaseHttp
from tools.validate_supabase_v2_team_lock import staging_config
from tools.validate_supabase_v2_purchases import PurchaseValidation
from tools.validate_supabase_v2_promotional_purchases import PromotionalPurchaseValidation


class TrialApiTransport:
    def __init__(self,factory,tokens):
        self.factory,self.tokens,self.worker=factory,tokens,local()

    def execute(self,op,r):
        if not hasattr(self.worker,'client'): self.worker.client=self.factory()
        path='/v1/seasons/'+r['season_id']+'/trials'
        if 'resource_id' in r: path+='/'+r['resource_id']
        if op not in ('create','list','detail'): path+='/'+op
        headers={'Authorization':'Bearer '+self.tokens[r['actor_trainer_id']]}
        if 'idempotency_key' in r: headers['Idempotency-Key']=r['idempotency_key']
        method='GET' if op in ('list','detail') else 'PUT' if op=='proposal' else 'POST'
        response=self.worker.client.request(method,path,headers=headers,json=r.get('body'))
        if response.status_code in (403,404,409,422):
            detail=response.json()['detail']
            if response.status_code==422 and isinstance(detail,list): raise SeasonAdminRejected('INVALID_REQUEST',422)
            raise SeasonAdminRejected(detail['code'],response.status_code)
        require(response.status_code==200,'API trial '+op+' HTTP '+str(response.status_code))
        return response.json()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--allow-staging-writes',action='store_true')
    args=parser.parse_args()
    config=replace(staging_config(args.env_file,args.allow_staging_writes),run_id='phase8k1_validation_'+uuid4().hex)
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
            participant_status_repository=SupabaseParticipantStatusRepository(backend),
            season_lifecycle_repository=SupabaseSeasonLifecycleRepository(backend),trial_repository=SupabaseTrialRepository(backend))
        test=TestClient(create_app(container=container)); apis.append(test); return test
    def wire(fixture):
        mapped={fixture.admin['id']:tokens['admin'],fixture.admin2['id']:tokens['other'],fixture.owner['id']:tokens['owner']}
        if isinstance(fixture,TrialsFixtures):
            mapped[fixture.recorder['id']]=tokens['other']
            fixture.trials=TrialApiTransport(api,mapped)
        fixture.repo=ApiTransport(api,mapped)
        fixture.matchdays=MatchdayApiTransport(api,mapped)
        fixture.status_repo=ParticipantStatusApiTransport(api,mapped)
        fixture.lifecycle=LifecycleApiTransport(api,mapped)
        fixture.validates_request_schema=True
    http=SupabaseHttp(config)
    print('V2 staging='+config.url+'\nrun_id='+config.run_id+'\nsecrets=redacted',flush=True)
    try:
        for role in ('admin','other','owner'):
            password=secrets.token_urlsafe(32); email=config.run_id+'_'+role+'@'+config.email_domain
            users[role]=http.auth_create_user(email,password); tokens[role]=http.auth_sign_in(email,password)
            readers[role]=client(config.anon_key); readers[role].postgrest.auth(tokens[role])
        readers['anon']=client(config.anon_key)
        for label,kind in (('030 trials',TrialsFixtures),('029 lifecycle',SeasonLifecycleFixtures),('028 participant',ParticipantStatusFixtures),
                           ('027 matchday',MatchdayFixtures),('026 setup',SeasonAdminFixtures)):
            class ApiFixtures(kind):
                def setup(self):
                    super().setup(); wire(self)
            f=ApiFixtures(WorkerClient(lambda:client(config.service_role_key)),readers,users,config.run_id+'_'+label[:3])
            try: f.run()
            finally: f.cleanup()
            if label.startswith('030'): count=len(f.checks)
            print(f'PASS {label} groups={len(f.checks)}',flush=True)
        for suffix,kind in (('purchase',PurchaseValidation),('promo',PromotionalPurchaseValidation)):
            regression=kind(replace(config,run_id=config.run_id+'_'+suffix))
            try:
                regression.setup_context()
                if suffix=='promo': regression.validate_promotions()
                else: regression.validate_context(); regression.validate_purchases()
            finally: require(not regression.cleanup(),'Regression cleanup '+suffix)
            print(f'PASS {suffix} regression checks={len(regression.checks)}',flush=True)
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
