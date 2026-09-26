from dataclasses import replace
import unittest
from unittest.mock import Mock
from uuid import uuid4
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.api.cup_models import CupCreateBody, CupResultsBody
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.errors import InvalidSessionError
from app.repositories.errors import PersistenceError
from app.repositories.supabase.cups import ERRORS, SupabaseCupRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID

SID,CID=str(uuid4()),str(uuid4())


class CupApiTests(unittest.TestCase):
    def setUp(self):
        self.repo=Mock(); self.principals=FakePrincipalRepository(); self.tokens=FakeTokenVerifier()
        self.receipt=dict(operation_id=str(uuid4()),event_id=str(uuid4()),cup_id=CID,season_id=SID,
            operation='start',revision=2,state='active',certificate_id=None,hall_id=None,
            actor_trainer_id=TRAINER_ID,changed_at='2026-09-24T00:00:00Z',replayed=False)
        self.repo.execute.return_value=self.receipt
        self.client=TestClient(create_app(container=ApiContainer(token_verifier=self.tokens,
            principal_repository=self.principals,cup_repository=self.repo)))
        self.addCleanup(self.client.close)
        self.base=f'/v1/admin/seasons/{SID}/cups/{CID}'
        self.headers={'Authorization':'Bearer validated','Idempotency-Key':'cup-key'}

    def post(self,suffix='start',body=None,headers=None):
        return self.client.post(self.base+'/'+suffix,json={'expected_revision':1} if body is None else body,
            headers=self.headers if headers is None else headers)

    def test_bearer_required_and_verified(self):
        self.assertEqual(self.post(headers={'Idempotency-Key':'x'}).status_code,401)
        self.tokens.fail=InvalidSessionError(); self.assertEqual(self.post().status_code,401)
        self.repo.execute.assert_not_called()

    def test_admin_and_global_enable_required(self):
        original=self.principals.trainer
        for kwargs in (dict(globally_enabled=False),dict(is_admin=False)):
            self.principals.trainer=replace(original,**kwargs)
            self.assertEqual(self.post().status_code,403)
        self.repo.execute.assert_not_called()

    def test_admin_outside_roster_and_server_actor(self):
        self.principals.trainer=replace(self.principals.trainer,display_name='Independent admin')
        self.assertEqual(self.post().status_code,200)
        self.assertEqual(self.repo.execute.call_args[0][1]['actor_trainer_id'],TRAINER_ID)

    def test_key_and_revision_are_strict(self):
        for revision in (True,-1,'1',1.5,None):
            self.assertEqual(self.post(body=dict(expected_revision=revision)).status_code,422)
        for key in ('','x'*129,'with space'):
            self.assertEqual(self.post(headers=dict(self.headers,**{'Idempotency-Key':key})).status_code,422)
        self.assertEqual(self.post(headers={'Authorization':'Bearer validated'}).status_code,422)

    def test_actor_plan_champion_and_arbitrary_state_rejected(self):
        for field in ('actor_trainer_id','plan','champion_side_id','standings','state','rules_version','fingerprint'):
            self.assertEqual(self.post(body=dict(expected_revision=1,**{field:'forged'})).status_code,422)

    def test_dq_reason_and_discard_confirmation(self):
        for reason in ('',' ','x'*501,None):
            self.assertEqual(self.post('discard',dict(expected_revision=1,reason=reason,confirmation='DISCARD')).status_code,422)
        self.assertEqual(self.post('discard',dict(expected_revision=1,reason='Cancel',confirmation='discard')).status_code,422)

    def test_cup_receipt_scope_and_privacy(self):
        for field in ('cup_id','season_id','actor_trainer_id'):
            original=self.receipt[field]; self.receipt[field]=str(uuid4())
            self.assertEqual(self.post().status_code,503); self.receipt[field]=original
        self.receipt.update(auth_uid='PRIVATE',private_team='PRIVATE',reason='PRIVATE')
        self.assertNotIn('PRIVATE',self.post().text)
        self.receipt['state']='draft'
        self.assertEqual(self.post().status_code,503)

    def test_finalize_requires_certificate_and_hall(self):
        self.receipt.update(operation='finalize',state='finished')
        self.assertEqual(self.post('finalize').status_code,503)
        self.receipt.update(certificate_id=str(uuid4()),hall_id=str(uuid4()))
        self.assertEqual(self.post('finalize').status_code,200)

    def test_errors_stable_and_backend_sanitized(self):
        for code,status in ERRORS.items():
            self.repo.execute.side_effect=SeasonAdminRejected(code.upper(),status)
            response=self.post(); self.assertEqual(response.status_code,status)
            self.assertEqual(response.json()['detail']['code'],code.upper())
        self.repo.execute.side_effect=PersistenceError('PRIVATE')
        self.assertEqual(self.post().status_code,503); self.assertNotIn('PRIVATE',self.post().text)

    def test_no_generic_patch_or_delete(self):
        self.assertEqual(self.client.patch(self.base,headers=self.headers,json={}).status_code,404)
        self.assertEqual(self.client.delete(self.base,headers=self.headers).status_code,404)

    def test_member_cardinality_duplicates_and_min_swiss(self):
        ids=[str(uuid4()) for _ in range(8)]
        body=dict(name='Cup',format='swiss',sides=[dict(name=str(i),trainer_ids=[ids[i]]) for i in range(4)])
        CupCreateBody.model_validate(body)
        with self.assertRaises(ValidationError): CupCreateBody.model_validate(dict(body,sides=body['sides'][:3]))
        with self.assertRaises(ValidationError): CupCreateBody.model_validate(dict(body,format='doubles'))
        bad=dict(body,sides=[body['sides'][0]]*4)
        with self.assertRaises(ValidationError): CupCreateBody.model_validate(bad)

    def test_bo3_request_bounds_and_canonical_batch(self):
        mid=str(uuid4())
        for a,b in ((0,0),(1,1),(2,2),(2,3),(2,True),(-1,2)):
            with self.assertRaises(ValidationError):
                CupResultsBody.model_validate(dict(expected_revision=1,results=[dict(match_id=mid,score_a=a,score_b=b)]))
        result=dict(match_id=mid,score_a=2,score_b=0)
        with self.assertRaises(ValidationError): CupResultsBody.model_validate(dict(expected_revision=1,results=[result,result]))
        with self.assertRaises(ValidationError):
            CupResultsBody.model_validate(dict(expected_revision=1,results=[dict(result,winner_side_id=str(uuid4()))]))


class CupAdapterTests(unittest.TestCase):
    def test_replay_does_not_plan_or_write(self):
        client=Mock(); client.rpc.return_value.execute.return_value.data={'receipt':{'replayed':True}}
        result=SupabaseCupRepository(client).execute('start',{})
        self.assertTrue(result['replayed']); self.assertEqual(client.rpc.call_count,1)

    def test_failure_never_retries_or_leaks(self):
        client=Mock(); client.rpc.return_value.execute.side_effect=RuntimeError('PRIVATE')
        with self.assertRaisesRegex(PersistenceError,'Cup backend unavailable'):
            SupabaseCupRepository(client).execute('start',{})
        self.assertEqual(client.rpc.call_count,1)

    def test_known_errors_only_with_expected_sqlstate(self):
        for sqlstate in ('PT409','XX000'):
            client=Mock(); exc=Exception('PRIVATE'); exc.message='stale_revision'; exc.code=sqlstate
            client.rpc.return_value.execute.side_effect=exc
            with self.assertRaises(SeasonAdminRejected if sqlstate=='PT409' else PersistenceError):
                SupabaseCupRepository(client).execute('start',{})
