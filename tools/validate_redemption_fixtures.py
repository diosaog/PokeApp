"""Synthetic shared PostgreSQL/staging checks. No raw saves or physical operations."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from threading import Event
from uuid import uuid4

from app.domain.redemptions import RedemptionRequest
from app.repositories.errors import RedemptionRejectedError
from app.repositories.supabase.redemptions import SupabaseRedemptionRepository
from tools.validate_pokemon_identity_fixtures import IdentityFixtures, require


class RedemptionFixtures(IdentityFixtures):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.redemptions = SupabaseRedemptionRepository(self.client)

    def purchase(self, code='blindar_pokemon', **extra):
        item = self.select('shop_items',code=code)[0]
        return self.insert('purchases',dict(season_id=self.season['id'],trainer_id=self.owner['id'],
            season_player_id=self.player['id'],shop_item_id=item['id'],unit_price=12,**extra))

    def redeem(self, purchase, target, key='redeem', **extra):
        return self.redemptions.redeem_purchase(RedemptionRequest(self.season['id'],
            extra.get('trainer_id',self.owner['id']),purchase['id'],target,key))

    def reject(self, action, code):
        try: action()
        except RedemptionRejectedError as exc:
            require(exc.code == code, 'unexpected business rejection '+exc.code+' expected '+code)
        else: raise AssertionError('expected rejection '+code)

    def setup(self):
        self.actors = {}
        for role in ('owner','other','admin'):
            self.actors[role] = self.insert('trainers',dict(display_name=self.run_id+'_'+role,
                slug=self.run_id+'_'+role,auth_user_id=self.auth_ids[role],is_admin=role=='admin'))
        self.owner = self.actors['owner']
        self.season = self.insert('seasons',dict(name=self.run_id,status='draft'))
        for actor in self.actors.values():
            player = self.insert('season_players',dict(season_id=self.season['id'],trainer_id=actor['id']))
            if actor['id']==self.owner['id']: self.player=player
        saved, parsed = self.save(1,clone=False)
        mon = parsed['payload']['party'][0]['pokemon']
        def slots(start,count):
            result=[]
            for i in range(count):
                p=deepcopy(mon)
                p['identity_evidence']['pid']=start+i
                p['legacy_fingerprints']=[f'unique-{start+i}']
                result.append(dict(slot_number=i+1,pokemon=p))
            return result
        self.payload=dict(party=slots(1000,6),boxes=[dict(box_number=8,slots=slots(2000,6)),
                                                  dict(box_number=9,slots=slots(3000,1))])
        self.client.table('parsed_saves').update({'payload':self.payload}).eq('id',parsed['id']).execute()
        parsed['payload']=self.payload
        receipt=self.reconcile(parsed,1)
        self.head=receipt['revision']['id']
        self.party=[o['pokemon_entity_id'] for o in receipt['observations'] if o['source']=='party']
        self.dead=[o['pokemon_entity_id'] for o in receipt['observations'] if o['box_number']==8]
        self.outside=next(o['pokemon_entity_id'] for o in receipt['observations'] if o['box_number']==9)

    def run(self):
        self.setup()
        first=self.purchase()
        receipt=self.redeem(first,self.party[0])
        require(receipt.physical_effect_status=='not_required','shield physical state')
        require(self.select('purchases',id=first['id'])[0]['status']=='used','purchase not consumed')
        require(self.select('pokemon_entity_flags',pokemon_entity_id=self.party[0],flag_type='blindado')[0]['flag_value'],'shield missing')
        self.passed('RF01/RF11 normal shield; F05/F07 draft season and NULL jornada accepted')
        require(self.redeem(first,self.party[0])==receipt,'idempotent receipt changed')
        self.passed('RF04 historical idempotent replay')
        self.reject(lambda:self.redeem(first,self.party[1]),'IDEMPOTENCY_CONFLICT')
        self.reject(lambda:self.redeem(first,self.party[0],'other-key'),'PURCHASE_ALREADY_REDEEMED')
        self.reject(lambda:self.redeem(self.purchase(),self.party[0]),'POKEMON_ALREADY_SHIELDED')
        require(len(self.select('redemptions',purchase_id=first['id']))==1,'duplicate redemption')
        self.passed('RF03/RF05 one redemption; semantic conflict; already shielded rollback')

        promo=self.insert('shop_promotions',dict(season_id=self.season['id'],shop_item_id=first['shop_item_id'],
            promotion_type='normal',status='ended',base_price=12,effective_price=6,stock_total=2,stock_used=1))
        promotional=self.purchase(promotion_id=promo['id'])
        self.redeem(promotional,self.party[1])
        require(self.select('shop_promotions',id=promo['id'])[0]==promo,'promotion changed')
        self.passed('RF02 promotional parity; expired promotion does not invalidate owned entitlement')
        self.insert('trainer_flags',dict(season_id=self.season['id'],trainer_id=self.owner['id'],
            season_player_id=self.player['id'],flag_type='store_banned'))
        revive=self.purchase('revivir_pokemon')
        revived=self.redeem(revive,self.dead[0])
        require(revived.physical_effect_status=='pending' and revived.physical_effect_completed_at is None,'physical revive fabricated')
        flags=self.select('pokemon_entity_flags',pokemon_entity_id=self.dead[0])
        timestamp=next(f for f in flags if f['flag_type']=='revivido_at')
        require(timestamp['flag_timestamp'] and timestamp['flag_value'] is None,'revivido_at must be timestamp')
        require(next(f for f in flags if f['flag_type']=='blindado')['flag_value'],'revive shield missing')
        self.passed('RF08/RF13 Store Ban does not block revive; Caja 8, timestamp, pending physical')
        self.reject(lambda:self.redeem(self.purchase('revivir_pokemon'),self.party[2]),'POKEMON_NOT_REVIVABLE')
        self.reject(lambda:self.redeem(self.purchase(),self.outside),'INVALID_POKEMON_TARGET')
        self.passed('F34/F44 current location eligibility, including configured eight-box limit')

        for state in ('retired','abandoned','disqualified'):
            self.client.table('season_players').update({'status':state}).eq('id',self.player['id']).execute()
            self.reject(lambda:self.redeem(first,self.party[0]),'PARTICIPANT_INACTIVE')
        self.client.table('season_players').update({'status':'active'}).eq('id',self.player['id']).execute()
        self.client.table('trainers').update({'globally_enabled':False}).eq('id',self.owner['id']).execute()
        self.reject(lambda:self.redeem(first,self.party[0]),'TRAINER_DISABLED')
        self.client.table('trainers').update({'globally_enabled':True}).eq('id',self.owner['id']).execute()
        self.passed('RF07 inactive participant/disabled actor rejected, even on replay')
        for role in ('other','admin'):
            self.reject(lambda r=role:self.redeem(first,self.party[0],trainer_id=self.actors[r]['id']),'PURCHASE_NOT_FOUND')
        self.reject(lambda:self.redeem({'id':str(uuid4())},self.party[0]),'PURCHASE_NOT_FOUND')
        for status in ('used','cancelled','refunded'):
            self.reject(lambda s=status:self.redeem(self.purchase(status=s),self.party[2]),'PURCHASE_NOT_REDEEMABLE')
        self.reject(lambda:self.redeem(self.purchase(quantity=2),self.party[2]),'PURCHASE_NOT_REDEEMABLE')
        for code in ('captura_extra','robar_pokemon','fosil','baya_aranja'):
            p=self.purchase(code)
            self.reject(lambda:self.redeem(p,self.party[2]),'REDEMPTION_NOT_SUPPORTED')
            require(self.select('purchases',id=p['id'])[0]['status']=='pending','unsupported consumed')
        self.passed('F08/F10/F13/F15 scoped purchase, unsupported robbery/catalog and invalid states unchanged')

        other_season=self.insert('seasons',dict(name=self.run_id+'_other',status='draft'))
        other_player=self.insert('season_players',dict(season_id=other_season['id'],trainer_id=self.owner['id']))
        foreign_purchase=self.insert('purchases',dict(season_id=other_season['id'],trainer_id=self.owner['id'],
            season_player_id=other_player['id'],shop_item_id=first['shop_item_id'],unit_price=12))
        self.reject(lambda:self.redeem(foreign_purchase,self.party[2]),'PURCHASE_NOT_FOUND')
        foreign_entity=self.insert('pokemon_entities',dict(season_id=other_season['id'],owner_trainer_id=self.owner['id'],
            identity_status='unambiguous',identity_schema_version=1,candidate_key='0'*64,initial_evidence={}))
        self.reject(lambda:self.redeem(self.purchase(),foreign_entity['id']),'POKEMON_NOT_OWNED')
        invalid=dict(self.select('redemptions',purchase_id=first['id'])[0],id=str(uuid4()),
                     purchase_id=self.purchase()['id'],target_pokemon_entity_id=foreign_entity['id'])
        self.denied(lambda:self.client.table('redemptions').insert(invalid).execute(),'target season FK',('23503',))
        duplicate=dict(self.select('redemptions',purchase_id=first['id'])[0],id=str(uuid4()))
        self.denied(lambda:self.client.table('redemptions').insert(duplicate).execute(),'unique purchase',('23505',))
        self.client.table('pokemon_entities').delete().eq('id',foreign_entity['id']).execute()
        self.client.table('purchases').delete().eq('id',foreign_purchase['id']).execute()
        self.passed('F09/F31 wrong-season purchase/entity denied')

        p=self.purchase()
        for state in ('ambiguous','missing'):
            self.client.table('pokemon_entities').update({'identity_status':state}).eq('id',self.party[2]).execute()
            self.reject(lambda:self.redeem(p,self.party[2]),'POKEMON_IDENTITY_AMBIGUOUS')
        self.client.table('pokemon_entities').update({'identity_status':'unambiguous'}).eq('id',self.party[2]).execute()
        obs=self.select('pokemon_observations',pokemon_entity_id=self.party[2])[0]
        self.client.table('pokemon_observations').update(dict(pokemon_entity_id=None,outcome='AMBIGUOUS',
            candidate_entity_ids=[self.party[2]])).eq('id',obs['id']).execute()
        self.reject(lambda:self.redeem(p,self.party[2]),'POKEMON_IDENTITY_AMBIGUOUS')
        self.client.table('pokemon_observations').update(dict(pokemon_entity_id=self.party[2],outcome='NEW',
            candidate_entity_ids=[])).eq('id',obs['id']).execute()
        self.reject(lambda:self.redeem(p,str(uuid4())),'POKEMON_NOT_OWNED')
        self.client.table('pokemon_entities').update({'owner_trainer_id':self.actors['other']['id']}).eq('id',self.party[2]).execute()
        self.reject(lambda:self.redeem(p,self.party[2]),'POKEMON_NOT_OWNED')
        self.client.table('pokemon_entities').update({'owner_trainer_id':self.owner['id']}).eq('id',self.party[2]).execute()
        self.passed('RF09 ambiguity/missing/foreign ownership denied without consumption')

        p=self.purchase()
        with ThreadPoolExecutor(max_workers=4) as pool:
            receipts=list(pool.map(lambda _:self.redeem(p,self.party[2]),range(4)))
        require(all(r==receipts[0] for r in receipts),'same-key race receipts differ')
        self.passed('RF06 four same-key workers produce one receipt')
        p=self.purchase()
        def attempt(purchase,target,key):
            try: return self.redeem(purchase,target,key)
            except RedemptionRejectedError as exc: return exc.code
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(attempt,p,self.party[3],k) for k in ('one','two')]
            results=[f.result() for f in futures]
        require(sum(not isinstance(r,str) for r in results)==1 and 'PURCHASE_ALREADY_REDEEMED' in results,'different-key race')
        p1,p2=self.purchase(),self.purchase()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(attempt,p,self.party[4],'shield') for p in (p1,p2)]
            results=[f.result() for f in futures]
        require(sum(not isinstance(r,str) for r in results)==1 and 'POKEMON_ALREADY_SHIELDED' in results,'same-target race')
        self.passed('F18/F39 different-key same-purchase and two-purchase same-shield races')

        p=self.purchase()
        stale=dict(p_season_id=self.season['id'],p_trainer_id=self.owner['id'],p_purchase_id=p['id'],
            p_pokemon_entity_id=self.party[5],p_idempotency_key='stale',p_expected_revision_id=self.head)
        _,parsed=self.save(2,clone=False)
        moved=deepcopy(self.payload)
        moved['boxes'][0]['slots'].append(dict(slot_number=7,pokemon=moved['party'].pop()['pokemon']))
        moved['boxes'][0]['slots'][-1]['pokemon']['species']='Gengar'
        self.client.table('parsed_saves').update({'payload':moved}).eq('id',parsed['id']).execute()
        captured,release=Event(),Event()
        client=self.client
        class PausedClient:
            def table(self, name): return client.table(name)
            def rpc(self, name, args):
                require(args['p_expected_revision_id']==stale['p_expected_revision_id'],'head was not captured before race')
                captured.set()
                require(release.wait(60),'race release timed out')
                return client.rpc(name,args)
        paused=SupabaseRedemptionRepository(PausedClient())
        request=RedemptionRequest(self.season['id'],self.owner['id'],p['id'],self.party[5],'stale')
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(paused.redeem_purchase,request)
            try:
                require(captured.wait(60),'race capture timed out')
                self.reconcile(parsed,2)
            finally: release.set()
            self.reject(future.result,'POKEMON_TARGET_STALE')
        require(self.select('purchases',id=p['id'])[0]['status']=='pending','stale consumed')
        receipt2=self.redeem(self.purchase('revivir_pokemon'),self.party[5])
        require(receipt2.target_pokemon_entity_id==self.party[5],'movement/evolution identity changed')
        require(self.redeem(first,self.party[0])==receipt,'historical retry after new head changed')
        self.passed('RF10/F30/F33/F34 stale head rejected; moved/evolved Entity revived by CURRENT location')
        for state,column in (('finished','finished_at'),('archived','archived_at'),('discarded','discarded_at')):
            self.client.table('seasons').update({'status':state,column:'2026-09-23T12:00:00Z'}).eq('id',self.season['id']).execute()
            self.redeem(self.purchase('revivir_pokemon'),self.dead[1])
        self.passed('F05 fresh redemption allowed in finished/archived/discarded seasons with active participant')

        events=self.select('activity_events',season_id=self.season['id'])
        redemptions=self.select('redemptions',season_id=self.season['id'])
        require(len(events)==len(redemptions),'event/redemption count differs')
        for role in ('owner','admin'):
            require(len(self.select('activity_events',self.readers[role],season_id=self.season['id']))==len(events),'private events unavailable')
        require(not self.select('activity_events',self.readers['other'],season_id=self.season['id']),'private event leaked')
        require(not self.select('public_activity_events',self.readers['other'],season_id=self.season['id']),'public view leaked event')
        for event in events:
            require(event['visibility']=='owner' and event['type']=='REDEMPTION_USED','event contract')
            require(set(event['payload'])==set(asdict(receipt)),'unexpected event fields/private evidence')
        self.passed('RF16/F71-F75/F77 private deduped events; no identity evidence')
        for role in ('owner','admin','anon'):
            self.denied(lambda r=role:self.readers[r].rpc('api_redeem_purchase',stale).execute(),'direct RPC')
            for table in ('purchases','redemptions','pokemon_entities','pokemon_observations',
                          'pokemon_entity_flags','trainer_flags','activity_events'):
                self.denied(lambda t=table,r=role:self.readers[r].table(t).insert({'id':str(uuid4())}).execute(),'direct insert')
                self.denied(lambda t=table,r=role:self.readers[r].table(t).update({'id':str(uuid4())}).eq('season_id',self.season['id']).execute(),'direct update')
                self.denied(lambda t=table,r=role:self.readers[r].table(t).delete().eq('season_id',self.season['id']).execute(),'direct delete')
        self.passed('RF17/RF18/RF19 RPC and direct writes denied, including browser admin')
        require(not self.select('coin_transactions',season_id=self.season['id']),'ledger mutated')
        require(self.select('shop_promotions',id=promo['id'])[0]==promo,'stock changed')
        require(self.select('parsed_saves',id=parsed['id'])[0]['payload']==moved,'parsed source modified')
        self.passed('RF14/RF15 no ledger/stock/save payload mutations; synthetic metadata only')

    def cleanup(self):
        remaining=[]
        if self.season:
            for table in ('redemptions','activity_events','purchases','shop_promotions','trainer_flags'):
                try:
                    self.client.table(table).delete().eq('season_id',self.season['id']).execute()
                    if self.select(table,season_id=self.season['id']): remaining.append(table)
                except Exception: remaining.append(table)
        # Foreign-season test rows may still exist if a check failed mid-case.
        for table in ('pokemon_entities','purchases'):
            for row_id in self.rows.get(table,[]):
                try: self.client.table(table).delete().eq('id',row_id).execute()
                except Exception: remaining.append(table)
        super().cleanup()
        require(not remaining,'redemption cleanup incomplete: '+','.join(remaining))
        self.passed('RF20 redemption fixture cleanup')
