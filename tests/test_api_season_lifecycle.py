from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.errors import InvalidSessionError
from app.repositories.errors import PersistenceError
from app.repositories.supabase.season_lifecycle import ERRORS, SupabaseSeasonLifecycleRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID

SID,DID=str(uuid4()),str(uuid4())


class FakeLifecycle:
    def __init__(self):
        self.calls=[]; self.failure=None
        self.response=dict(operation_id=str(uuid4()),event_id=str(uuid4()),season_id=SID,operation='finish',
            state='finished',actor_trainer_id=TRAINER_ID,changed_at='2026-09-24T00:00:00Z',setup_revision=10,
            current_matchday_id=DID,archive_id=None,hall_id=None,replayed=False)

    def execute(self,op,r):
        self.calls.append((op,r))
        if self.failure: raise self.failure
        return self.response


class LifecycleApiTests(unittest.TestCase):
    def setUp(self):
        self.repo=FakeLifecycle(); self.principals=FakePrincipalRepository(); self.tokens=FakeTokenVerifier()
        self.client=TestClient(create_app(container=ApiContainer(token_verifier=self.tokens,
            principal_repository=self.principals,season_lifecycle_repository=self.repo)))
        self.addCleanup(self.client.close)
        self.base=f'/v1/admin/seasons/{SID}'
        self.headers={'Authorization':'Bearer validated','Idempotency-Key':'lifecycle-key'}

    def post(self,op='finish',body=None,headers=None):
        return self.client.post(self.base+'/'+op,json={'expected_revision':9} if body is None else body,
            headers=self.headers if headers is None else headers)

    def test_missing_bearer(self):
        self.assertEqual(self.post(headers={'Idempotency-Key':'x'}).status_code,401); self.assertFalse(self.repo.calls)

    def test_invalid_bearer(self):
        self.tokens.fail=InvalidSessionError(); self.assertEqual(self.post().status_code,401); self.assertFalse(self.repo.calls)

    def test_disabled_admin(self):
        self.principals.trainer=replace(self.principals.trainer,globally_enabled=False)
        self.assertEqual(self.post().status_code,403); self.assertFalse(self.repo.calls)

    def test_non_admin(self):
        self.principals.trainer=replace(self.principals.trainer,is_admin=False)
        self.assertEqual(self.post().status_code,403); self.assertFalse(self.repo.calls)

    def test_admin_not_participant(self):
        self.principals.trainer=replace(self.principals.trainer,display_name='Independent admin')
        self.assertEqual(self.post().status_code,200)
        self.assertEqual(self.repo.calls[0][1]['actor_trainer_id'],TRAINER_ID)

    def test_three_explicit_commands(self):
        for op,state in (('finish','finished'),('archive','archived'),('discard','discarded')):
            body={'expected_revision':9}
            self.repo.response.update(operation=op,state=state,archive_id=None,hall_id=None)
            if op=='archive': self.repo.response.update(archive_id=str(uuid4()),hall_id=str(uuid4()))
            if op=='discard': body.update(reason='Unused',confirmation='DISCARD')
            self.assertEqual(self.post(op,body).status_code,200)
            self.assertEqual(self.repo.calls[-1][0],op)

    def test_key_required_and_validated(self):
        self.assertEqual(self.post(headers={'Authorization':'Bearer validated'}).status_code,422)
        for key in ('','x'*129,'with space'):
            self.assertEqual(self.post(headers=dict(self.headers,**{'Idempotency-Key':key})).status_code,422)

    def test_revision_strict(self):
        for value in (True,-1,'9',9.5,None): self.assertEqual(self.post(body={'expected_revision':value}).status_code,422)

    def test_extra_authority_and_status_rejected(self):
        for key in ('status','actor_trainer_id','is_admin','finished_at','current_matchday_id','champion','archive','reward'):
            self.assertEqual(self.post(body={'expected_revision':9,key:'injected'}).status_code,422)

    def test_discard_confirmation_exact(self):
        for value in ('discard','DESCARTAR',None,True):
            self.assertEqual(self.post('discard',dict(expected_revision=9,reason='Unused',confirmation=value)).status_code,422)

    def test_reason_required_trimmed_bounded(self):
        for value in ('','  ',None,123,'x'*501):
            self.assertEqual(self.post('discard',dict(expected_revision=9,reason=value,confirmation='DISCARD')).status_code,422)

    def test_archive_label_bounded(self):
        for value in ('','  ',123,'x'*121):
            self.assertEqual(self.post('archive',dict(expected_revision=9,label=value)).status_code,422)

    def test_archive_label_normalization(self):
        self.repo.response.update(operation='archive',state='archived',archive_id=str(uuid4()),hall_id=str(uuid4()))
        self.assertEqual(self.post('archive',dict(expected_revision=9,label='  Season  ')).status_code,200)
        self.assertEqual(self.repo.calls[-1][1]['body']['label'],'Season')

    def test_scope_uuid(self):
        self.base='/v1/admin/seasons/not-uuid'; self.assertEqual(self.post().status_code,422)

    def test_receipt_scope_revalidation(self):
        for field in ('season_id','actor_trainer_id'):
            original=self.repo.response[field]; self.repo.response[field]=str(uuid4())
            self.assertEqual(self.post().status_code,503); self.repo.response[field]=original

    def test_receipt_state_revalidation(self):
        self.repo.response['state']='archived'; self.assertEqual(self.post().status_code,503)

    def test_archive_requires_both_artifact_ids(self):
        self.repo.response.update(state='archived',operation='archive')
        self.assertEqual(self.post('archive').status_code,503)

    def test_receipt_privacy(self):
        self.repo.response.update(auth_uid='PRIVATE',private_team_snapshot='PRIVATE',raw_save='PRIVATE')
        self.assertNotIn('PRIVATE',self.post().text)

    def test_replay(self):
        self.repo.response['replayed']=True; self.assertTrue(self.post().json()['replayed'])

    def test_known_business_rejections(self):
        for code,status in ERRORS.items():
            self.repo.failure=SeasonAdminRejected(code.upper(),status)
            response=self.post(); self.assertEqual(response.status_code,status)
            self.assertEqual(response.json()['detail']['code'],code.upper())

    def test_unknown_error_sanitized(self):
        self.repo.failure=PersistenceError('PRIVATE'); response=self.post()
        self.assertEqual(response.status_code,503); self.assertNotIn('PRIVATE',response.text)

    def test_no_reopen_or_generic_patch(self):
        self.assertEqual(self.post('reopen').status_code,404)
        self.assertEqual(self.client.patch(self.base,headers=self.headers,json={'status':'active'}).status_code,404)


class LifecycleAdapterTests(unittest.TestCase):
    def test_finished_denial_fixtures_reach_business_guards(self):
        from app.api.matchday_models import OpenDayBody, ResultsBody, CloseDayBody, CorrectDayBody
        from tools.validate_season_lifecycle_fixtures import SeasonLifecycleFixtures
        fixture=SeasonLifecycleFixtures.__new__(SeasonLifecycleFixtures)
        fixture.rows=Mock(return_value=[dict(id=DID,winner_id=TRAINER_ID)])
        fixture.correction=Mock(return_value=dict(expected_snapshot_revision=1,reason='Review',
            results=[dict(match_id=DID,winner_season_player_id=TRAINER_ID)]))
        bodies={'open':OpenDayBody,'results':ResultsBody,'close':CloseDayBody,'correct':CorrectDayBody}
        seen=[]
        def md(op,sid,did,body):
            bodies[op].model_validate(body)
            seen.append(op)
            raise SeasonAdminRejected('SEASON_NOT_ACTIVE',409)
        fixture.md=md
        fixture.players=Mock(return_value=[dict(id=TRAINER_ID)])
        fixture.change=Mock(side_effect=SeasonAdminRejected('SEASON_NOT_ACTIVE',409))
        fixture.config=Mock(return_value={}); fixture.divisions_body=Mock(return_value={})
        def call(op,*args):
            raise SeasonAdminRejected('CONFIG_WINDOW_CLOSED' if op=='create_config' else 'SEASON_NOT_DRAFT',409)
        fixture.call=call; fixture.passed=Mock()
        fixture.finished_denials(SID,DID)
        self.assertEqual(seen,['open','results','close','correct'])
        fixture.passed.assert_called_once()

    def test_single_rpc(self):
        c=Mock(); c.rpc.return_value.execute.return_value.data={'safe':True}
        self.assertEqual(SupabaseSeasonLifecycleRepository(c).execute('finish',{'season_id':SID}),{'safe':True})
        c.rpc.assert_called_once_with('api_admin_season_lifecycle',{'p_request':{'season_id':SID,'operation':'finish'}})

    def test_rejection_allowlist_requires_sqlstate(self):
        for code,status in ERRORS.items():
            c=Mock(); error=Exception(); error.message=code; error.code='PT'+str(status)
            c.rpc.return_value.execute.side_effect=error
            with self.assertRaises(SeasonAdminRejected): SupabaseSeasonLifecycleRepository(c).execute('finish',{})
            error.code='XX000'
            with self.assertRaises(PersistenceError) as caught: SupabaseSeasonLifecycleRepository(c).execute('finish',{})
            self.assertNotIsInstance(caught.exception,SeasonAdminRejected)

    def test_unknown_no_retry(self):
        c=Mock(); c.rpc.return_value.execute.side_effect=Exception('PRIVATE')
        with self.assertRaises(PersistenceError) as caught: SupabaseSeasonLifecycleRepository(c).execute('archive',{})
        self.assertNotIn('PRIVATE',str(caught.exception)); self.assertEqual(c.rpc.call_count,1)

    def test_malformed_reply(self):
        for value in ([],None,False,'raw'):
            c=Mock(); c.rpc.return_value.execute.return_value.data=value
            with self.assertRaises(PersistenceError): SupabaseSeasonLifecycleRepository(c).execute('archive',{})

    def test_additive_sql_scope(self):
        sql=(Path(__file__).resolve().parents[1]/'supabase/v2/migrations/029_season_finalization_archive_hall.sql').read_text()
        self.assertNotIn('drop table',sql.lower())
        self.assertNotIn('delete from',sql.lower())
        for fragment in ('lifecycle_final_source','lifecycle_public_team',"admin_setup_begin('lifecycle'",'historical_artifact_immutable',
            'source_snapshot_revision_id','lifecycle_discarded_visibility','from public,anon,authenticated'):
            self.assertIn(fragment,sql)
