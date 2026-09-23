from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.errors import InvalidSessionError
from app.repositories.errors import PersistenceError
from app.repositories.supabase.participant_status import ERRORS, SupabaseParticipantStatusRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID

SID,PID,DID=[str(uuid4()) for _ in range(3)]


class FakeStatusRepository:
    def __init__(self):
        self.calls=[]; self.failure=None
        self.response=dict(operation_id=str(uuid4()),event_id=str(uuid4()),season_id=SID,participant_id=PID,
            old_status='active',new_status='retired',reason='Decision',effective_matchday_id=DID,
            effective_matchday_number=2,actor_trainer_id=TRAINER_ID,changed_at='2026-09-23T00:00:00Z',
            roster_revision=5,setup_revision=10,replayed=False)

    def execute(self,op,r):
        self.calls.append((op,r))
        if self.failure: raise self.failure
        return self.response


class ParticipantStatusApiTests(unittest.TestCase):
    def setUp(self):
        self.repo=FakeStatusRepository(); self.principals=FakePrincipalRepository(); self.tokens=FakeTokenVerifier()
        self.client=TestClient(create_app(container=ApiContainer(token_verifier=self.tokens,
            principal_repository=self.principals,participant_status_repository=self.repo)))
        self.addCleanup(self.client.close)
        self.base=f'/v1/admin/seasons/{SID}/participants/{PID}'
        self.headers={'Authorization':'Bearer validated','Idempotency-Key':'status-key'}
        self.body=dict(reason='Decision',expected_roster_revision=4)

    def post(self,op='retire',body=None,headers=None):
        return self.client.post(self.base+'/'+op,json=self.body if body is None else body,
            headers=self.headers if headers is None else headers)

    def test_missing_bearer(self):
        self.assertEqual(self.post(headers={'Idempotency-Key':'x'}).status_code,401)
        self.assertFalse(self.repo.calls)

    def test_invalid_bearer(self):
        self.tokens.fail=InvalidSessionError()
        self.assertEqual(self.post().status_code,401)
        self.assertFalse(self.repo.calls)

    def test_disabled_admin(self):
        self.principals.trainer=replace(self.principals.trainer,globally_enabled=False)
        self.assertEqual(self.post().status_code,403)

    def test_non_admin(self):
        self.principals.trainer=replace(self.principals.trainer,is_admin=False)
        self.assertEqual(self.post().status_code,403)

    def test_admin_need_not_participate_or_have_name(self):
        self.principals.trainer=replace(self.principals.trainer,display_name='Someone',slug='someone')
        self.assertEqual(self.post().status_code,200)
        self.assertEqual(self.repo.calls[0][1]['actor_trainer_id'],TRAINER_ID)

    def test_three_explicit_status_operations(self):
        for op,status in (('retire','retired'),('abandon','abandoned'),('disqualify','disqualified')):
            self.repo.response['new_status']=status
            response=self.post(op)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['new_status'],status)
            self.assertEqual(self.repo.calls[-1][0],op)

    def test_no_generic_patch(self):
        self.assertEqual(self.client.patch(self.base,json={'status':'active'},headers=self.headers).status_code,404)

    def test_no_reactivation_route(self):
        self.assertEqual(self.post('reactivate').status_code,404)

    def test_key_required(self):
        self.assertEqual(self.post(headers={'Authorization':'Bearer validated'}).status_code,422)

    def test_key_validation(self):
        for key in ('','x'*129,'contains space'):
            self.assertEqual(self.post(headers=dict(self.headers,**{'Idempotency-Key':key})).status_code,422)

    def test_reason_validation(self):
        for value in ('','   ','x'*501,None,123):
            self.assertEqual(self.post(body=dict(self.body,reason=value)).status_code,422)

    def test_reason_normalized(self):
        self.assertEqual(self.post(body=dict(self.body,reason='  Decision  ')).status_code,200)
        self.assertEqual(self.repo.calls[-1][1]['body']['reason'],'Decision')

    def test_revision_strict(self):
        for value in (True,-1,'4',4.1,None):
            self.assertEqual(self.post(body=dict(self.body,expected_roster_revision=value)).status_code,422)

    def test_only_two_body_fields(self):
        for field in ('status','new_status','old_status','actor_trainer_id','is_admin','effective_round','changed_at','current_matchday_id'):
            self.assertEqual(self.post(body=dict(self.body,**{field:'injected'})).status_code,422)

    def test_uuid_scopes(self):
        self.base='/v1/admin/seasons/not-uuid/participants/'+PID
        self.assertEqual(self.post().status_code,422)

    def test_receipt_scope_revalidated(self):
        for field in ('season_id','participant_id','actor_trainer_id'):
            original=self.repo.response[field]; self.repo.response[field]=str(uuid4())
            self.assertEqual(self.post().status_code,503)
            self.repo.response[field]=original

    def test_receipt_status_revalidated(self):
        self.repo.response['new_status']='abandoned'
        self.assertEqual(self.post().status_code,503)

    def test_receipt_privacy(self):
        self.repo.response.update(auth_user_id='PRIVATE',parsed_save={'PRIVATE':1},private_team_snapshot=['PRIVATE'])
        self.assertNotIn('PRIVATE',self.post().text)

    def test_replay_receipt(self):
        self.repo.response['replayed']=True
        self.assertTrue(self.post().json()['replayed'])

    def test_business_errors(self):
        for error,status in ERRORS.items():
            self.repo.failure=SeasonAdminRejected(error.upper(),status)
            response=self.post()
            self.assertEqual(response.status_code,status)
            self.assertEqual(response.json()['detail']['code'],error.upper())

    def test_unknown_backend_sanitized(self):
        self.repo.failure=PersistenceError('PRIVATE SQL key')
        response=self.post()
        self.assertEqual(response.status_code,503)
        self.assertNotIn('PRIVATE',response.text)

    def test_malformed_receipt_sanitized(self):
        self.repo.response.pop('effective_matchday_id')
        self.assertEqual(self.post().status_code,503)


class ParticipantStatusAdapterTests(unittest.TestCase):
    def test_single_rpc_no_retry(self):
        client=Mock(); client.rpc.return_value.execute.return_value.data={'safe':True}
        repo=SupabaseParticipantStatusRepository(client)
        self.assertEqual(repo.execute('retire',{'season_id':SID}),{'safe':True})
        client.rpc.assert_called_once_with('api_admin_participant_status',{'p_request':{'season_id':SID,'operation':'retire'}})

    def test_unknown_sql_error_not_exposed_or_retried(self):
        client=Mock(); error=Exception('PRIVATE'); error.message='PRIVATE'; error.code='XX000'
        client.rpc.return_value.execute.side_effect=error
        with self.assertRaises(PersistenceError) as caught: SupabaseParticipantStatusRepository(client).execute('retire',{})
        self.assertNotIn('PRIVATE',str(caught.exception))
        self.assertEqual(client.rpc.call_count,1)

    def test_allowlist_requires_matching_sqlstate(self):
        for code,status in ERRORS.items():
            client=Mock(); error=Exception(); error.message=code; error.code='PT'+str(status)
            client.rpc.return_value.execute.side_effect=error
            with self.assertRaises(SeasonAdminRejected) as caught: SupabaseParticipantStatusRepository(client).execute('retire',{})
            self.assertEqual(caught.exception.code,code.upper())
            error.code='XX000'
            with self.assertRaises(PersistenceError) as caught: SupabaseParticipantStatusRepository(client).execute('retire',{})
            self.assertNotIsInstance(caught.exception,SeasonAdminRejected)

    def test_malformed_backend_shape(self):
        for value in (None,[],False,'raw'):
            client=Mock(); client.rpc.return_value.execute.return_value.data=value
            with self.assertRaises(PersistenceError): SupabaseParticipantStatusRepository(client).execute('retire',{})

    def test_additive_migration_contract(self):
        sql=(Path(__file__).resolve().parents[1]/'supabase/v2/migrations/028_participant_status_admin.sql').read_text()
        self.assertNotIn('drop table',sql.lower())
        for fragment in ('participant_memberships_at','eligibility_ends_before_matchday_number',
                         "admin_setup_begin('participant_status'",'history_watermark_id=last_redemption_id',
                         "'participant_has_current_team_lock'","'PARTICIPANT_STATUS_CHANGED'",
                         'from public,anon,authenticated','grant execute'):
            self.assertIn(fragment,sql)
