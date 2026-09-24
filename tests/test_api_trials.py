from dataclasses import replace
from decimal import Decimal
import unittest
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.trial_models import ResolveTrialBody
from app.auth.errors import InvalidSessionError
from app.repositories.errors import PersistenceError
from app.repositories.supabase.trials import ERRORS, SupabaseTrialRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID

SID,CID,ACC=[str(uuid4()) for _ in range(3)]


class FakeTrials:
    def __init__(self): self.calls=[]; self.failure=None; self.override={}

    def execute(self,op,r):
        self.calls.append((op,r))
        if self.failure: raise self.failure
        verdict=r.get('body',{}).get('verdict')
        response=dict(operation_id=str(uuid4()),event_id=str(uuid4()),season_id=SID,case_id=CID,
            case_number=1,case_revision=1,operation=op,status='open' if op in ('create','proposal') else 'cancelled' if op=='cancel' else 'resolved' if verdict=='guilty' else 'dismissed',
            verdict=verdict,decision_revision_id=str(uuid4()) if verdict else None,actor_trainer_id=TRAINER_ID,
            changed_at='2026-09-24T00:00:00Z',replayed=False)
        if op in ('list','detail'):
            response=dict(id=CID,season_id=SID,case_number=1,revision=1,title='Safe',description='Summary',status='open',verdict=None,
                is_public=True,created_at='2026-09-24T00:00:00Z',updated_at='2026-09-24T00:00:00Z',resolved_at=None,sanctions=[],detail=None)
            if op=='list': response=dict(season_id=SID,cases=[response])
        return dict(response,**self.override)


class TrialApiTests(unittest.TestCase):
    def setUp(self):
        self.repo=FakeTrials(); self.principals=FakePrincipalRepository(); self.tokens=FakeTokenVerifier()
        self.principals.trainer=replace(self.principals.trainer,is_admin=False)
        self.client=TestClient(create_app(container=ApiContainer(token_verifier=self.tokens,
            principal_repository=self.principals,trial_repository=self.repo)))
        self.addCleanup(self.client.close)
        self.base=f'/v1/seasons/{SID}/trials'; self.headers={'Authorization':'Bearer validated','Idempotency-Key':'trial-key'}

    def create(self,**changes):
        return dict(title='Case',description='Public summary',accused_trainer_id=ACC,**changes)

    def decision(self,**changes):
        return dict(expected_case_revision=1,verdict='guilty',decision_summary='Agreed in Discord',sanctions=[],**changes)

    def send(self,op='resolve',body=None,headers=None):
        return self.client.request('PUT' if op=='proposal' else 'POST',self.base+('' if op=='create' else '/'+CID+'/'+op),
            json=self.decision() if body is None else body,headers=self.headers if headers is None else headers)

    def test_non_admin_records_without_votes(self):
        self.assertEqual(self.send().status_code,200)
        self.assertEqual(self.repo.calls[-1][1]['actor_trainer_id'],TRAINER_ID)

    def test_missing_bearer(self):
        self.assertEqual(self.send(headers={'Idempotency-Key':'x'}).status_code,401); self.assertFalse(self.repo.calls)

    def test_invalid_bearer(self):
        self.tokens.fail=InvalidSessionError(); self.assertEqual(self.send().status_code,401); self.assertFalse(self.repo.calls)

    def test_disabled_participant(self):
        self.principals.trainer=replace(self.principals.trainer,globally_enabled=False)
        self.assertEqual(self.send().status_code,403); self.assertFalse(self.repo.calls)

    def test_all_five_commands(self):
        for op,body in (('create',self.create()),('proposal',dict(title='Changed',description='Safe',expected_case_revision=1)),
            ('resolve',self.decision()),('cancel',dict(expected_case_revision=1,reason='Withdraw')),
            ('correct',self.decision(reason='Recording error'))):
            self.assertEqual(self.send(op,body).status_code,200)
            self.assertEqual(self.repo.calls[-1][0],op)

    def test_key_required_all_commands(self):
        for op,body in (('create',self.create()),('resolve',self.decision()),('cancel',dict(expected_case_revision=1,reason='Withdraw')),
            ('correct',self.decision(reason='Error')),('proposal',dict(title='Edit',description='Safe',expected_case_revision=1))):
            self.assertEqual(self.send(op,body,{'Authorization':'Bearer validated'}).status_code,422)

    def test_key_bounds(self):
        for key in ('','x'*129,'with space'):
            self.assertEqual(self.send(headers=dict(self.headers,**{'Idempotency-Key':key})).status_code,422)

    def test_revision_strict(self):
        for value in (True,-1,'1',1.5,None):
            self.assertEqual(self.send(body=dict(self.decision(),expected_case_revision=value)).status_code,422)

    def test_explicit_verdict_required(self):
        body=self.decision(); body.pop('verdict')
        self.assertEqual(self.send(body=body).status_code,422)
        for value in ('resolved','no_culpable',None,True):
            self.assertEqual(self.send(body=dict(self.decision(),verdict=value)).status_code,422)

    def test_guilty_warning_distinct_from_not_guilty(self):
        guilty=self.send().json(); innocent=self.send(body=dict(self.decision(),verdict='not_guilty')).json()
        self.assertEqual(guilty['verdict'],'guilty'); self.assertEqual(innocent['verdict'],'not_guilty')

    def test_not_guilty_rejects_each_mechanical_effect(self):
        for sanction in (dict(type='store_ban',duration_matchdays=1),dict(type='coins_reduction',amount=1),dict(type='points_reduction',amount='1.25')):
            self.assertEqual(self.send(body=dict(self.decision(),verdict='not_guilty',sanctions=[sanction])).status_code,422)

    def test_sanctions_explicit_required(self):
        body=self.decision(); body.pop('sanctions'); self.assertEqual(self.send(body=body).status_code,422)

    def test_authority_and_effect_fields_forbidden(self):
        for key in ('actor_id','actor_trainer_id','is_admin','created_by','jury','votes','ledger_id','applied','effective_matchday_id'):
            self.assertEqual(self.send(body=dict(self.decision(),**{key:'injected'})).status_code,422)

    def test_proposal_cannot_change_identity_or_verdict(self):
        body=dict(title='Edited',description='Safe',expected_case_revision=1)
        for key in ('accused_trainer_id','creator_id','season_id','verdict','sanctions'):
            self.assertEqual(self.send('proposal',dict(body,**{key:ACC})).status_code,422)

    def test_coins_positive_strict_integer(self):
        for value in (0,-1,True,'2',2.1,2147483648):
            self.assertEqual(self.send(body=dict(self.decision(),sanctions=[dict(type='coins_reduction',amount=value)])).status_code,422)

    def test_points_finite_precision_positive(self):
        for value in ('NaN','Infinity','0','-1','1.001',True,'10000000000'):
            self.assertEqual(self.send(body=dict(self.decision(),sanctions=[dict(type='points_reduction',amount=value)])).status_code,422)

    def test_points_and_sanctions_semantic_canonicalization(self):
        bodies=[]
        for value in ('1.50',1.5):
            self.assertEqual(self.send(body=dict(self.decision(),sanctions=[dict(type='points_reduction',amount=value),dict(type='coins_reduction',amount=3)])).status_code,200)
            bodies.append(self.repo.calls[-1][1]['body'])
        self.assertEqual(*bodies)
        model=ResolveTrialBody.model_validate(dict(self.decision(),sanctions=[dict(type='points_reduction',amount='10.00')]))
        self.assertEqual(model.model_dump(mode='json')['sanctions'][0]['amount'],'10')

    def test_duration_strict_and_server_derived(self):
        for value in (0,-1,True,'2',2.5,1001):
            self.assertEqual(self.send(body=dict(self.decision(),sanctions=[dict(type='store_ban',duration_matchdays=value)])).status_code,422)
        for key in ('start_matchday_number','end_matchday_number','matchday_id'):
            self.assertEqual(self.send(body=dict(self.decision(),sanctions=[dict(type='store_ban',duration_matchdays=1,**{key:1})])).status_code,422)

    def test_only_known_effects_one_per_type(self):
        for effects in ([dict(type='execute',text='command')],[dict(type='coins_reduction',amount=1)]*2):
            self.assertEqual(self.send(body=dict(self.decision(),sanctions=effects)).status_code,422)

    def test_notes_text_only(self):
        for kind in ('pokemon_release','other'):
            effect=dict(type=kind,text='Discussed externally')
            self.assertEqual(self.send(body=dict(self.decision(),sanctions=[effect])).status_code,200)
            for key in ('pokemon_id','save_id','command','physical_effect'):
                self.assertEqual(self.send(body=dict(self.decision(),sanctions=[dict(effect,**{key:ACC})])).status_code,422)

    def test_correction_reason_required(self):
        self.assertEqual(self.send('correct').status_code,422)
        for reason in ('',' ',123,'x'*501):
            self.assertEqual(self.send('correct',self.decision(reason=reason)).status_code,422)

    def test_response_receipt_scope_revalidation(self):
        for key in ('season_id','case_id','actor_trainer_id'):
            self.repo.override={key:str(uuid4())}; self.assertEqual(self.send().status_code,503)

    def test_receipt_verdict_head_state_revalidation(self):
        for changes in ({'status':'open'},{'verdict':'not_guilty'},{'decision_revision_id':None},{'operation':'cancel'}):
            self.repo.override=changes; self.assertEqual(self.send().status_code,503)

    def test_response_whitelist(self):
        self.repo.override={'private_payload':'PRIVATE','auth_uid':'PRIVATE'}
        self.assertNotIn('PRIVATE',self.send().text)

    def test_list_and_detail_safe_read(self):
        for path in ('','/'+CID):
            r=self.client.get(self.base+path,headers=self.headers); self.assertEqual(r.status_code,200)
            self.assertNotIn('evidence',r.text)

    def test_read_scope_revalidation(self):
        self.repo.override={'season_id':str(uuid4())}
        self.assertEqual(self.client.get(self.base,headers=self.headers).status_code,503)
        self.repo.override={'id':str(uuid4())}
        self.assertEqual(self.client.get(self.base+'/'+CID,headers=self.headers).status_code,503)

    def test_replay_preserved(self):
        self.repo.override={'replayed':True}; self.assertTrue(self.send().json()['replayed'])

    def test_stable_business_errors(self):
        for code,status in ERRORS.items():
            self.repo.failure=SeasonAdminRejected(code.upper(),status); r=self.send()
            self.assertEqual(r.status_code,status); self.assertEqual(r.json()['detail']['code'],code.upper())

    def test_unknown_errors_sanitized(self):
        self.repo.failure=PersistenceError('PRIVATE'); r=self.send()
        self.assertEqual(r.status_code,503); self.assertNotIn('PRIVATE',r.text)

    def test_no_jury_vote_delete_patch(self):
        for op in ('vote','jury','delete','set-points','set-balance'): self.assertEqual(self.send(op).status_code,404)
        for method in ('PATCH','DELETE'):
            self.assertIn(self.client.request(method,self.base+'/'+CID,headers=self.headers).status_code,(404,405))


class TrialAdapterTests(unittest.TestCase):
    def test_one_transaction_no_chained_effect_rpcs(self):
        client=Mock(); client.rpc.return_value.execute.return_value.data={'ok':True}
        SupabaseTrialRepository(client).execute('resolve',{'body':{'verdict':'guilty'}})
        client.rpc.assert_called_once_with('api_trial_mutate',{'p_request':{'body':{'verdict':'guilty'},'operation':'resolve'}})

    def test_read_rpc(self):
        for op in ('list','detail'):
            client=Mock(); client.rpc.return_value.execute.return_value.data={}
            SupabaseTrialRepository(client).execute(op,{})
            self.assertEqual(client.rpc.call_args.args[0],'api_trials_read')

    def test_rejection_requires_matching_sqlstate(self):
        for message,status in ERRORS.items():
            client=Mock(); error=Exception(); error.message=message; error.code='PT'+str(status)
            client.rpc.return_value.execute.side_effect=error
            with self.assertRaises(SeasonAdminRejected): SupabaseTrialRepository(client).execute('resolve',{})
            error.code='XX000'
            with self.assertRaises(PersistenceError) as caught: SupabaseTrialRepository(client).execute('resolve',{})
            self.assertNotIsInstance(caught.exception,SeasonAdminRejected)

    def test_unknown_error_never_retried(self):
        client=Mock(); client.rpc.return_value.execute.side_effect=Exception('PRIVATE')
        with self.assertRaises(PersistenceError): SupabaseTrialRepository(client).execute('correct',{})
        self.assertEqual(client.rpc.call_count,1)

    def test_legacy_no_culpable_explicit_import_without_invented_guilt(self):
        from app.repositories.mappers import trial_case_from_legacy
        from app.domain.trials import TrialVerdict
        base=dict(id='historical',case_no=1,title='Imported',creator='one',accused='two',status='finalizado')
        self.assertEqual(trial_case_from_legacy(dict(base,verdict='no_culpable')).verdict,TrialVerdict.NOT_GUILTY)
        self.assertEqual(trial_case_from_legacy(dict(base,verdict='unknown')).verdict,TrialVerdict.PENDING)


if __name__=='__main__': unittest.main()
