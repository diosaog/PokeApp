from dataclasses import asdict, replace
import json
from pathlib import Path
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient
import httpx
from postgrest import SyncPostgrestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.auth.errors import InvalidSessionError
from app.domain.redemptions import RedemptionReceipt, RedemptionRequest
from app.repositories.supabase.redemptions import REJECTIONS, SupabaseRedemptionRepository
from test_api_phase8b import TRAINER_ID, FakePrincipalRepository, FakeTokenVerifier


class RedemptionTests(unittest.TestCase):
    def setUp(self):
        self.season, self.purchase, self.entity, self.head = [str(uuid4()) for _ in range(4)]
        self.receipt = RedemptionReceipt(str(uuid4()),self.purchase,self.season,TRAINER_ID,str(uuid4()),
            'shield',self.entity,TRAINER_ID,'used','applied','not_required',
            '2026-09-23T12:00:00+00:00','2026-09-23T12:00:00+00:00',None,str(uuid4()),None)
        self.rpc_status, self.rpc_body = 200, asdict(self.receipt)
        self.requests, self.heads = [], [{'id':self.head}]
        def respond(request):
            self.requests.append(request)
            if request.method == 'GET': return httpx.Response(200,json=self.heads)
            return httpx.Response(self.rpc_status,json=self.rpc_body)
        pg = SyncPostgrestClient('https://example.invalid/rest/v1')
        pg.session = httpx.Client(transport=httpx.MockTransport(respond))
        self.addCleanup(pg.session.close)
        self.principals, self.verifier = FakePrincipalRepository(), FakeTokenVerifier()
        self.container = ApiContainer(token_verifier=self.verifier, principal_repository=self.principals,
            redemption_repository=SupabaseRedemptionRepository(pg))
        self.client = TestClient(create_app(container=self.container))
        self.addCleanup(self.client.close)
        self.path = f'/v1/seasons/{self.season}/shop/purchases/{self.purchase}/redemptions'

    def post(self, body=None, headers=None):
        return self.client.post(self.path,json={'pokemon_entity_id':self.entity} if body is None else body,
            headers={'Authorization':'Bearer dummy','Idempotency-Key':'redeem-1'} if headers is None else headers)

    def test_f01_missing_bearer(self):
        self.assertEqual(self.post(headers={'Idempotency-Key':'x'}).status_code,401)
        self.assertEqual(self.requests,[])

    def test_f02_invalid_bearer(self):
        self.verifier.fail = InvalidSessionError()
        self.assertEqual(self.post().status_code,401)
        self.assertEqual(self.requests,[])

    def test_f03_disabled_admin(self):
        self.principals.trainer = replace(self.principals.trainer,globally_enabled=False)
        self.assertEqual(self.post().status_code,403)
        self.assertEqual(self.requests,[])

    def test_f27_jwt_actor_and_server_head_only(self):
        response = self.post()
        self.assertEqual(response.status_code,200,response.text)
        body = json.loads(self.requests[-1].content)
        self.assertEqual(body,dict(p_season_id=self.season,p_trainer_id=TRAINER_ID,p_purchase_id=self.purchase,
            p_pokemon_entity_id=self.entity,p_idempotency_key='redeem-1',p_expected_revision_id=self.head))
        self.assertEqual(response.json()['redemption_id'],self.receipt.redemption_id)
        self.assertEqual(self.requests[-1].url.path,'/rest/v1/rpc/api_redeem_purchase')

    def test_f28_forbid_forged_authority(self):
        for field in ('effect_type','item_id','trainer_id','target_trainer_id','fingerprint','price','status',
                      'flag_values','physical_effect_status','save_file_id','box','slot','species','nickname',
                      'PID','expected_revision_id','promotion_id','quantity'):
            with self.subTest(field=field):
                self.assertEqual(self.post({'pokemon_entity_id':self.entity,field:'forged'}).status_code,422)
        for body in ({}, {'fingerprint':'legacy'}, {'pokemon_entity_id':''}, {'pokemon_entity_id':'Gengar'}, []):
            self.assertEqual(self.post(body).status_code,422)
        self.assertEqual(self.requests,[])

    def test_malformed_paths_and_header(self):
        for key in ('','has space','a'*129):
            self.assertEqual(self.post(headers={'Authorization':'Bearer dummy','Idempotency-Key':key}).status_code,422)
        self.assertEqual(self.post(headers={'Authorization':'Bearer dummy'}).status_code,422)
        self.path = self.path.replace(self.purchase,'bad-id')
        self.assertEqual(self.post().status_code,422)

    def test_business_errors_sanitized(self):
        for code,status in REJECTIONS.items():
            with self.subTest(code=code):
                self.rpc_status = status
                self.rpc_body = dict(code=f'PT{status}',message=code,details='SECRET SQL',hint='SECRET')
                response = self.post()
                self.assertEqual(response.status_code,status)
                self.assertEqual(response.json()['detail']['code'],code.upper())
                self.assertNotIn('SECRET',response.text)

    def test_unknown_error_sanitized(self):
        for code,msg in (('23505','SECRET'),('PT409','SECRET'),('XX000','pokemon_not_owned')):
            self.rpc_status,self.rpc_body = 500,dict(code=code,message=msg,details='SECRET',hint=None)
            response = self.post()
            self.assertEqual(response.status_code,503)
            self.assertNotIn('SECRET',response.text)

    def test_receipt_scope_and_semantics_fail_closed(self):
        original = asdict(self.receipt)
        for body in (None,[],{},dict(original,trainer_id=str(uuid4())),dict(original,purchase_id=str(uuid4())),
                     dict(original,target_pokemon_entity_id=str(uuid4())),dict(original,effect_code='steal'),
                     dict(original,physical_effect_status='applied'),dict(original,physical_effect_completed_at='now'),
                     dict(original,gift_purchase_id=str(uuid4())),dict(original,purchase_status='pending'),
                     dict(original,requested_at='2026-01-01')):
            with self.subTest(body=body):
                self.rpc_body = body
                self.assertEqual(self.post().status_code,503)

    def test_f16_replay_does_not_require_live_identity(self):
        first = self.post().json()
        self.heads = []
        self.assertEqual(first,self.post().json())
        self.assertIsNone(json.loads(self.requests[-1].content)['p_expected_revision_id'])

    def test_f35_response_drops_private_extra_keys(self):
        self.rpc_body.update(identity_evidence={'pid':'SECRET'},raw_parsed_save='SECRET')
        self.assertNotIn('SECRET',self.post().text)

    def test_f48_revive_pending_not_physical_applied(self):
        self.rpc_body = asdict(replace(self.receipt,effect_code='revive',physical_effect_status='pending'))
        response = self.post()
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['physical_effect_status'],'pending')
        self.assertIsNone(response.json()['physical_effect_completed_at'])

    def test_backend_missing(self):
        with TestClient(create_app(container=replace(self.container,redemption_repository=None))) as client:
            self.assertEqual(client.post(self.path,json={'pokemon_entity_id':self.entity},
                headers={'Authorization':'Bearer dummy','Idempotency-Key':'x'}).status_code,503)

    def test_domain_validation(self):
        for key in ('','bad key','x'*129):
            with self.assertRaises(ValueError):
                RedemptionRequest(self.season,TRAINER_ID,self.purchase,self.entity,key)

    def test_f21_f22_f50_no_physical_or_legacy_dependencies(self):
        for file in ('app/domain/redemptions.py','app/application/redemptions.py',
                     'app/api/routes/redemptions.py','app/repositories/supabase/redemptions.py'):
            source = Path(file).read_text()
            for forbidden in ('streamlit','discord','conex_pkhex','PKHeX','storage_shop','subprocess'):
                self.assertNotIn(forbidden,source)

    def test_sql_dispatch_and_lock_order(self):
        sql = Path('supabase/v2/migrations/024_redemption_effect_boundary.sql').read_text()
        body = sql.split('create function public.api_redeem_purchase',1)[1]
        self.assertLess(body.index('from public.season_players'),body.index('from public.purchases'))
        self.assertLess(body.index('from public.purchases'),body.index('from public.pokemon_entities'))
        for forbidden in ('api_is_store_banned','current_matchday','coin_transactions','shop_promotions','exception when'):
            self.assertNotIn(forbidden,body.lower())
        self.assertIn("security invoker set search_path=''",body)
        self.assertIn("'REDEMPTION_USED'",body)
        self.assertIn('redemption_purchase_unique unique(purchase_id)',sql)
