"""Synthetic V2 staging redemption validator; no raw saves, no deployment."""
import argparse
from dataclasses import replace
from pathlib import Path
import secrets
import sys
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.validate_supabase_v2_team_lock import staging_config
from tools.validate_supabase_v2_rls import SupabaseHttp
from tools.validate_redemption_fixtures import RedemptionFixtures


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--allow-staging-writes',action='store_true')
    args=parser.parse_args()
    config=replace(staging_config(args.env_file,args.allow_staging_writes),run_id='phase8f_validation_'+uuid4().hex)
    from supabase import create_client
    http=SupabaseHttp(config)
    users,readers,fixture,failure={},{},None,None
    print('V2 staging='+config.url+'\nrun_id='+config.run_id+'\nsecrets=redacted',flush=True)
    try:
        for role in ('owner','other','admin'):
            email,password=config.run_id+'_'+role+'@'+config.email_domain,secrets.token_urlsafe(32)
            users[role]=http.auth_create_user(email,password)
            token=http.auth_sign_in(email,password)
            readers[role]=create_client(config.url,config.anon_key)
            readers[role].postgrest.auth(token)
        readers['anon']=create_client(config.url,config.anon_key)
        fixture=RedemptionFixtures(create_client(config.url,config.service_role_key),readers,users,run_id=config.run_id)
        fixture.run()
    except Exception as exc:
        failure=str(exc) if isinstance(exc,AssertionError) else type(exc).__name__
        cause=exc.__cause__
        if cause is not None:
            failure+=' cause='+type(cause).__name__+' code='+str(getattr(cause,'code',None))
    finally:
        if fixture:
            try: fixture.cleanup()
            except Exception: failure='fixture cleanup failed'
        for uid in users.values():
            try:
                http.auth_delete_user(uid)
                if http.request('GET',http.auth_url+'/admin/users/'+uid,auth='service',raise_on_error=False).status!=404:
                    failure='Auth cleanup verification failed'
            except Exception: failure='Auth cleanup failed'
    if failure:
        print('RESULT failed: '+failure,flush=True)
        return 1
    print(f'RESULT ok checks={len(fixture.checks)}; Auth cleanup PASS; robbery/voucher NOT SUPPORTED',flush=True)
    return 0


if __name__=='__main__': raise SystemExit(main())
