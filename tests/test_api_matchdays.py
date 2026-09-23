from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.matchday_models import ResultsBody, CorrectDayBody
from app.application.matchdays import plan_close
from app.auth.errors import InvalidSessionError
from app.repositories.errors import PersistenceError
from app.repositories.supabase.matchdays import ERRORS, SupabaseMatchdayRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID

SID,DID,MID=[str(uuid4()) for _ in range(3)]


class FakeRepository:
    def __init__(self):
        self.calls=[]; self.failure=None
        self.response=dict(operation_id=str(uuid4()),season_id=SID,matchday_id=DID,event_id=str(uuid4()),
            state='open',revision=1,results_revision=1,snapshot_revision=0,current_matchday_id=DID,replayed=False)

    def execute(self,operation,request):
        self.calls.append((operation,request))
        if self.failure: raise self.failure
        return self.response


class MatchdayApiTests(unittest.TestCase):
    def setUp(self):
        self.repo=FakeRepository(); self.principals=FakePrincipalRepository(); self.tokens=FakeTokenVerifier()
        self.client=TestClient(create_app(container=ApiContainer(token_verifier=self.tokens,
            principal_repository=self.principals,matchday_repository=self.repo)))
        self.addCleanup(self.client.close)
        self.base=f'/v1/admin/seasons/{SID}/matchdays/{DID}'
        self.headers={'Authorization':'Bearer validated','Idempotency-Key':'matchday-key'}

    def post(self,op='open',body=None,headers=None):
        return self.client.post(self.base+'/'+op,json=body if body is not None else {'expected_revision':0},
            headers=self.headers if headers is None else headers)

    def test_missing_bearer(self):
        self.assertEqual(self.post(headers={'Idempotency-Key':'x'}).status_code,401)
        self.assertFalse(self.repo.calls)

    def test_invalid_bearer(self):
        self.tokens.fail=InvalidSessionError()
        self.assertEqual(self.post().status_code,401)

    def test_disabled_admin(self):
        self.principals.trainer=replace(self.principals.trainer,globally_enabled=False)
        self.assertEqual(self.post().status_code,403)

    def test_non_admin_denied(self):
        self.principals.trainer=replace(self.principals.trainer,is_admin=False)
        self.assertEqual(self.post().status_code,403)

    def test_admin_no_name_or_participant_required(self):
        self.principals.trainer=replace(self.principals.trainer,display_name='Different',slug='different')
        self.assertEqual(self.post().status_code,200)
        self.assertEqual(self.repo.calls[0][1]['actor_trainer_id'],TRAINER_ID)

    def test_all_mutation_keys_required(self):
        for op,body in [('open',{'expected_revision':0}),('cancel-editing',{'expected_revision':0,'reason':'x'}),
            ('close',{'expected_results_revision':0}),('correct',{'expected_snapshot_revision':1,'reason':'x',
                'results':[dict(match_id=MID,winner_season_player_id=TRAINER_ID)]})]:
            with self.subTest(op=op):
                self.assertEqual(self.post(op,body,{'Authorization':'Bearer validated'}).status_code,422)

    def test_no_client_authority_or_plan(self):
        for name in ('actor_trainer_id','is_admin','plan','input_hash','standings','reward','current_matchday_id'):
            self.assertEqual(self.post(body={'expected_revision':0,name:TRAINER_ID}).status_code,422)

    def test_strict_revision(self):
        for value in (True,-1,'1',1.2,None):
            self.assertEqual(self.post(body={'expected_revision':value}).status_code,422)

    def test_reason_required(self):
        for reason in ('','   ','x'*501):
            self.assertEqual(self.post('cancel-editing',{'expected_revision':0,'reason':reason}).status_code,422)

    def test_results_route_batch_and_null(self):
        response=self.client.put(self.base+'/results',json={'expected_results_revision':1,
            'results':[dict(match_id=MID,winner_season_player_id=None)]},headers=self.headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.repo.calls[0][0],'results')

    def test_duplicate_matches_rejected(self):
        row=dict(match_id=MID,winner_season_player_id=None)
        with self.assertRaises(ValueError): ResultsBody(expected_results_revision=0,results=[row,row])

    def test_result_order_canonicalized(self):
        ids=sorted([str(uuid4()),str(uuid4())])
        body=ResultsBody(expected_results_revision=0,results=[dict(match_id=i,winner_season_player_id=None) for i in reversed(ids)])
        self.assertEqual([str(r.match_id) for r in body.results],ids)

    def test_correction_requires_winner(self):
        with self.assertRaises(ValueError): CorrectDayBody(expected_snapshot_revision=1,reason='x',results=[dict(match_id=MID,winner_season_player_id=None)])

    def test_correction_strict_revision(self):
        self.assertEqual(self.post('correct',{'expected_snapshot_revision':0,'reason':'x','results':[]}).status_code,422)

    def test_read_state_safe(self):
        self.repo.response.update(matches=[],auth_user_id='secret',private_save_payload={'secret':1})
        response=self.client.get(self.base,headers=self.headers)
        self.assertEqual(response.status_code,200)
        self.assertNotIn('secret',response.text)

    def test_receipt_scope_checked(self):
        self.repo.response['season_id']=str(uuid4())
        self.assertEqual(self.post().status_code,503)

    def test_receipt_filters_secrets(self):
        self.repo.response.update(auth_user_id='private',private_team_snapshot=['secret'])
        self.assertNotIn('secret',self.post().text)

    def test_allowlisted_business_errors(self):
        for error,status in ERRORS.items():
            self.repo.failure=SeasonAdminRejected(error.upper(),status)
            response=self.post()
            self.assertEqual(response.status_code,status)
            self.assertEqual(response.json()['detail']['code'],error.upper())

    def test_backend_error_sanitized(self):
        self.repo.failure=PersistenceError('PRIVATE SQL credential')
        response=self.post()
        self.assertEqual(response.status_code,503)
        self.assertNotIn('PRIVATE',response.text)

    def test_staging_transport_uses_real_route_contract(self):
        from tools.validate_supabase_v2_matchdays import MatchdayApiTransport
        transport=MatchdayApiTransport(lambda:self.client,{TRAINER_ID:'validated'})
        request=dict(actor_trainer_id=TRAINER_ID,season_id=SID,resource_id=DID,idempotency_key='transport',body={'expected_revision':0})
        self.assertEqual(transport.execute('open',request)['state'],'open')
        self.repo.response['matches']=[]
        self.assertEqual(transport.execute('state',request)['matches'],[])
        request['body']={'expected_results_revision':1,'results':[dict(match_id=MID,winner_season_player_id=None)]}
        transport.execute('results',request)
        self.assertEqual(self.repo.calls[-1][0],'results')
        request['body']={'expected_revision':1,'reason':'No results'}
        transport.execute('cancel',request)
        self.assertEqual(self.repo.calls[-1][0],'cancel')

    def test_staging_transport_distinguishes_schema_and_business_errors(self):
        from tools.validate_supabase_v2_matchdays import MatchdayApiTransport
        transport=MatchdayApiTransport(lambda:self.client,{TRAINER_ID:'validated'})
        request=dict(actor_trainer_id=TRAINER_ID,season_id=SID,resource_id=DID,idempotency_key='transport',body={})
        with self.assertRaises(SeasonAdminRejected) as caught: transport.execute('open',request)
        self.assertEqual(caught.exception.code,'INVALID_REQUEST')
        request['body']={'expected_revision':0}
        self.repo.failure=SeasonAdminRejected('STALE_REVISION',409)
        with self.assertRaises(SeasonAdminRejected) as caught: transport.execute('open',request)
        self.assertEqual(caught.exception.code,'STALE_REVISION')


class MatchdayAdapterTests(unittest.TestCase):
    def test_rpc_replay_skips_plan_and_mutation(self):
        calls=[]
        def rpc(name,args):
            calls.append(name)
            return SimpleNamespace(execute=lambda:SimpleNamespace(data={'receipt':{'replayed':True}}))
        repo=SupabaseMatchdayRepository(SimpleNamespace(rpc=rpc))
        self.assertEqual(repo.execute('close',{}),{'replayed':True})
        self.assertEqual(calls,['api_admin_matchday_context'])

    def test_plan_and_input_hash_server_only(self):
        calls=[]
        def rpc(name,args):
            calls.append((name,args))
            data={'context':{},'input_hash':'authoritative'} if 'context' in name else {}
            return SimpleNamespace(execute=lambda:SimpleNamespace(data=data))
        repo=SupabaseMatchdayRepository(SimpleNamespace(rpc=rpc))
        with patch('app.repositories.supabase.matchdays.plan_close',return_value={'safe':True}):
            repo.execute('close',{'body':{'expected_results_revision':2}})
        self.assertEqual(calls[1][1]['p_request']['input_hash'],'authoritative')
        self.assertEqual(calls[1][1]['p_request']['plan'],{'safe':True})

    def test_no_automatic_retry(self):
        calls=[]
        def rpc(name,args):
            calls.append(name)
            error=RuntimeError(); error.code='PT409'; error.message='stale_inputs'
            raise error
        with self.assertRaises(SeasonAdminRejected): SupabaseMatchdayRepository(SimpleNamespace(rpc=rpc)).execute('close',{})
        self.assertEqual(len(calls),1)

    def test_unknown_sql_error_not_exposed(self):
        def rpc(*args):
            error=RuntimeError('secret'); error.code='XX000'; error.message='secret'
            raise error
        with self.assertRaises(PersistenceError) as caught: SupabaseMatchdayRepository(SimpleNamespace(rpc=rpc)).execute('open',{})
        self.assertNotIn('secret',str(caught.exception))


def domain_context():
    ids=['p1','p2','p3','p4']
    config=dict(id='cfg',name='Config',effective_from_matchday=1,total_matchdays=2,division_sizes={'A':2,'B':2},
        promotion_relegation_count=1,scoring_json={'1':4,'2':3,'3':2,'4':1},coin_rewards_json={'1':10,'2':7,'3':4,'4':0},
        rules_json=dict(team_lock_required=True,last_b_gets_steal=True))
    return dict(inputs=dict(season_id='s',day_id='d',number=1,config=config,
        players=[dict(id=p,trainer_id=p,ranking_key=p,division='A' if i<2 else 'B',dead_count=0,points_reduction=0,coins_reduction=0) for i,p in enumerate(ids)],
        matches=[dict(id='a',player_a_id='p1',player_b_id='p2',winner_id='p2',division='A'),
                 dict(id='b',player_a_id='p3',player_b_id='p4',winner_id='p3',division='B')]),
        existing_next_promotions=True,catalog=[],purchase_history=[],promotion_history=[])


class MatchdayPlannerTests(unittest.TestCase):
    def test_domain_winners_rewards_and_movements(self):
        plan=plan_close(domain_context())
        self.assertEqual([s['trainer_id'] for s in plan['standings']],['p2','p1','p3','p4'])
        self.assertEqual(plan['new_divisions'],{'A':['p2','p3'],'B':['p1','p4']})
        self.assertEqual([s['coins_awarded'] for s in plan['standings']],[10,7,4,0])
        self.assertEqual(plan['last_b_player_id'],'p4')

    def test_final_no_movement_but_last_b_reward(self):
        ctx=domain_context(); ctx['inputs']['number']=2
        plan=plan_close(ctx)
        self.assertEqual(plan['new_divisions'],{'A':['p2','p1'],'B':['p3','p4']})
        self.assertEqual(plan['last_b_player_id'],'p4')
        self.assertEqual(plan['promotions'],[])

    def test_correction_uses_frozen_inputs(self):
        ctx=domain_context(); original=deepcopy(ctx)
        plan=plan_close(ctx,[dict(match_id='b',winner_season_player_id='p4')])
        self.assertEqual(plan['last_b_player_id'],'p3')
        self.assertEqual(ctx,original)

    def test_penalties_not_deducted_from_each_round_reward(self):
        ctx=domain_context(); ctx['inputs']['players'][0].update(dead_count=10,points_reduction=5,coins_reduction=3)
        row=next(s for s in plan_close(ctx)['standings'] if s['trainer_id']=='p1')
        self.assertEqual(row['points_awarded'],3)
        self.assertEqual(row['penalties']['dead_points_penalty'],2)
        self.assertEqual(row['penalties']['points_reduction'],5)

    def test_disabled_last_b_rule(self):
        ctx=domain_context(); ctx['inputs']['config']['rules_json']['last_b_gets_steal']=False
        self.assertIsNone(plan_close(ctx)['last_b_player_id'])

    def test_invalid_winner_rejected(self):
        ctx=domain_context(); ctx['inputs']['matches'][0]['winner_id']='p3'
        with self.assertRaises(ValueError): plan_close(ctx)

    def test_duplicate_ranking_keys_rejected(self):
        ctx=domain_context(); ctx['inputs']['players'][1]['ranking_key']='p1'
        with self.assertRaises(ValueError): plan_close(ctx)

    def test_three_way_tie_uses_adjusted_dead_count_then_stable_key(self):
        ctx=domain_context(); ctx['inputs']['config']['division_sizes']={'A':3,'B':1}
        ctx['inputs']['players'][2]['division']='A'
        ctx['inputs']['players'][0]['dead_count']=5
        ctx['inputs']['matches']=[dict(id='a',player_a_id='p1',player_b_id='p2',winner_id='p1',division='A'),
            dict(id='b',player_a_id='p2',player_b_id='p3',winner_id='p2',division='A'),
            dict(id='c',player_a_id='p1',player_b_id='p3',winner_id='p3',division='A')]
        self.assertEqual([s['trainer_id'] for s in plan_close(ctx)['standings']],['p2','p3','p1','p4'])
