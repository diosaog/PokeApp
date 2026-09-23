"""Shared synthetic local/staging robbery contract, including real concurrent RPCs."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from threading import Event
from uuid import uuid4

from app.domain.redemptions import RedemptionRequest
from app.repositories.errors import RedemptionRejectedError
from app.repositories.supabase.redemptions import SupabaseRedemptionRepository
from tools.validate_redemption_fixtures import RedemptionFixtures
from tools.validate_pokemon_identity_fixtures import require


class RobberyFixtures(RedemptionFixtures):
    def setup(self):
        super().setup()
        self.identities = {}
        original_owner = self.owner
        for number, (role, actor) in enumerate(self.actors.items(), 3):
            self.owner = actor
            _, parsed = self.save(number, clone=False)
            payload = deepcopy(self.payload)
            mon = payload['party'][0]['pokemon']
            slots = []
            for i in range(24):
                pokemon = deepcopy(mon)
                pokemon['identity_evidence']['pid'] = 4000 + i
                pokemon['legacy_fingerprints'] = [f'robbery-{i}']
                slots.append(dict(slot_number=i+1,pokemon=pokemon))
            payload['boxes'].append(dict(box_number=1,slots=slots))
            self.client.table('parsed_saves').update({'payload':payload}).eq('id',parsed['id']).execute()
            parsed['payload'] = payload
            revision = self.reconcile(parsed,2 if role=='owner' else 1)
            observations = revision['observations']
            self.identities[role] = dict(parsed=parsed,head=revision['revision']['id'],
                party=[o['pokemon_entity_id'] for o in observations if o['source']=='party'],
                alive=[o['pokemon_entity_id'] for o in observations if o['box_number']==1],
                dead=next(o['pokemon_entity_id'] for o in observations if o['box_number']==8),
                outside=next(o['pokemon_entity_id'] for o in observations if o['box_number']==9))
        self.owner = original_owner
        self.players = {role:self.select('season_players',season_id=self.season['id'],trainer_id=a['id'])[0]
                        for role,a in self.actors.items()}

    def target(self, role, index=0):
        return self.identities[role]['alive'][index]

    def buy(self, role='owner', **extra):
        body=dict(season_id=self.season['id'],trainer_id=self.actors[role]['id'],
            season_player_id=self.players[role]['id'],shop_item_id=self.select('shop_items',code='robar_pokemon')[0]['id'],
            unit_price=12)
        body.update(extra)
        return self.insert('purchases',body)

    def use(self, purchase, target, key='robbery'):
        return self.redeem(purchase,target,key,trainer_id=purchase['trainer_id'])

    def race(self, calls):
        def attempt(call):
            try: return call()
            except RedemptionRejectedError as exc: return exc.code
        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            futures=[pool.submit(attempt,call) for call in calls]
            return [f.result(timeout=90) for f in futures]

    def cycle(self):
        return self.select('robbery_cycles',season_id=self.season['id'])[0]

    def run(self):
        self.setup()
        voucher=self.select('shop_items',code='robbery_shield_voucher')
        require(len(voucher)==1,'canonical voucher duplicate/missing')
        voucher=voucher[0]
        require(voucher['name']=='Comod\u00edn de Blindaje por Robo' and voucher['category']=='comodines', 'canonical display/category')
        require(voucher['base_price']==0 and not voucher['enabled'] and voucher['acquisition_mode']=='reward_only','reward-only representation')
        require(not self.select('public_shop_items',id=voucher['id']),'reward exposed as offer')
        self.denied(lambda:self.buy(shop_item_id=voucher['id']),'paid reward item',('PT409',))
        self.denied(lambda:self.buy(unit_price=0),'free paid purchase',('23514',))
        self.denied(lambda:self.buy(shop_item_id=voucher['id'],unit_price=0,acquisition_type='reward',
                                   origin_redemption_id=str(uuid4())),'forged origin',('PT409',))
        self.passed('V01/V02/V05/V08 canonical single hidden reward; DB rejects invalid acquisition/origin')

        # Exercise the real purchase RPCs with a valid shop context, not an earlier season error.
        config=self.insert('season_config_versions',dict(season_id=self.season['id'],version_number=1,
            name='Fixture',effective_from_matchday=1,total_matchdays=5,division_count=2))
        day=self.insert('matchdays',dict(season_id=self.season['id'],number=1,season_config_version_id=config['id']))
        self.client.table('seasons').update(dict(status='active',started_at='2026-09-23T12:00:00Z',
            current_matchday_id=day['id'])).eq('id',self.season['id']).execute()
        promo=self.insert('shop_promotions',dict(season_id=self.season['id'],matchday_id=day['id'],
            shop_item_id=voucher['id'],promotion_type='normal',status='active',base_price=10,effective_price=5,stock_total=3))
        for rpc, extra in (('api_create_normal_purchase',dict(p_item_id=voucher['id'],p_confirm_base_price=False)),
                           ('api_create_promotional_purchase',dict(p_promotion_id=promo['id']))):
            try:
                self.client.rpc(rpc,dict(p_season_id=self.season['id'],p_trainer_id=self.owner['id'],
                    p_idempotency_key='forbidden',**extra)).execute()
            except Exception as exc: require(getattr(exc,'message',None)=='item_unavailable','reward API rejection')
            else: raise AssertionError('reward bought through '+rpc)
        require(self.select('shop_promotions',id=promo['id'])[0]==promo,'reward promotion stock changed')
        self.passed('V03/V04 direct normal/promotional RPCs reject known voucher UUID')

        purchase=self.buy()
        self.reject(lambda:self.use(purchase,self.target('owner')),'STEAL_SELF_TARGET')
        self.client.table('season_players').update({'status':'retired'}).eq('id',self.players['other']['id']).execute()
        self.reject(lambda:self.use(purchase,self.target('other')),'STEAL_VICTIM_INELIGIBLE')
        self.client.table('season_players').update({'status':'active'}).eq('id',self.players['other']['id']).execute()
        for location in ('dead','outside'):
            self.reject(lambda loc=location:self.use(purchase,self.identities['other'][loc]),'STEAL_TARGET_INELIGIBLE')
        self.client.table('pokemon_entities').update({'identity_status':'ambiguous'}).eq('id',self.target('other')).execute()
        self.reject(lambda:self.use(purchase,self.target('other')),'POKEMON_IDENTITY_AMBIGUOUS')
        self.client.table('pokemon_entities').update({'identity_status':'unambiguous'}).eq('id',self.target('other')).execute()
        self.passed('R02-R05 authoritative cross-player eligibility: self/inactive/dead/outside/ambiguous denied')

        receipts=self.race([lambda:self.use(purchase,self.target('other'))]*4)
        require(all(r==receipts[0] for r in receipts) and not isinstance(receipts[0],str),'four worker replay')
        receipt=receipts[0]
        gift=self.select('purchases',id=receipt.gift_purchase_id)[0]
        require(gift['origin_redemption_id']==receipt.redemption_id and gift['shop_item_id']==voucher['id'], 'gift origin/item')
        require(gift['trainer_id']==self.owner['id'] and gift['season_player_id']==self.player['id'],'legacy gift recipient is robber')
        require((gift['unit_price'],gift['total_price'],gift['quantity'],gift['status'])==(0,0,1,'pending'),'gift price/state')
        require(gift['promotion_id'] is None and gift['acquisition_type']=='reward','gift acquisition')
        require(receipt.physical_effect_status=='pending' and receipt.physical_effect_completed_at is None,'physical steal fabricated')
        require(self.select('pokemon_entities',id=self.target('other'))[0]['owner_trainer_id']==self.actors['other']['id'],'owner moved')
        flags={f['flag_type']:f for f in self.select('pokemon_entity_flags',pokemon_entity_id=self.target('other'))}
        require(set(flags)=={'blindado','robado','robado_from','robado_at'},'exact robbery flags')
        require(flags['blindado']['flag_value'] and flags['robado']['flag_value'],'boolean effects')
        require(flags['robado_from']['flag_trainer_id']==self.actors['other']['id'] and flags['robado_at']['flag_timestamp'],'typed origin/time')
        require(self.select('trainer_flags',season_id=self.season['id'],trainer_id=self.actors['other']['id'],flag_type='robbed')[0]['flag_value'],'victim not marked')
        require(self.cycle()['cycle_number']==1,'premature cycle reset')
        self.passed('R01/R07-R22/V06/V09 four workers: one immutable receipt, gift to robber, exact flags, owner unchanged')
        self.reject(lambda:self.use(purchase,self.target('other',1)),'IDEMPOTENCY_CONFLICT')
        self.reject(lambda:self.use(purchase,self.target('other'),'different'),'PURCHASE_ALREADY_REDEEMED')
        self.reject(lambda:self.use(self.buy(),self.target('other')),'STEAL_TARGET_SHIELDED')
        self.reject(lambda:self.use(self.buy(),self.target('other',1)),'STEAL_VICTIM_ALREADY_ROBBED')
        duplicate={k:v for k,v in gift.items() if k not in ('id','total_price')}
        self.denied(lambda:self.insert('purchases',duplicate),'duplicate gift origin',('PT409','23505'))
        self.passed('R04/R06/R18/R22 immutable replay/conflicts, victim cycle and gift uniqueness')

        self.reject(lambda:self.redeem(gift,self.target('owner',4),trainer_id=self.actors['other']['id']),'PURCHASE_NOT_FOUND')
        self.reject(lambda:self.use(gift,self.target('other',4)),'POKEMON_NOT_OWNED')
        self.reject(lambda:self.use(gift,self.identities['owner']['outside']),'INVALID_POKEMON_TARGET')
        self.client.table('pokemon_entities').update({'identity_status':'ambiguous'}).eq('id',self.target('owner',4)).execute()
        self.reject(lambda:self.use(gift,self.target('owner',4)),'POKEMON_IDENTITY_AMBIGUOUS')
        self.client.table('pokemon_entities').update({'identity_status':'unambiguous'}).eq('id',self.target('owner',4)).execute()
        uses=self.race([lambda:self.use(gift,self.target('owner',4))]*4)
        require(all(r==uses[0] for r in uses) and uses[0].effect_code=='robbery_shield','voucher race')
        require(uses[0].physical_effect_status=='not_required' and uses[0].gift_purchase_id is None,'voucher physical/gift')
        flags=self.select('pokemon_entity_flags',pokemon_entity_id=self.target('owner',4))
        require({f['flag_type'] for f in flags}=={'blindado','blindaje_por_robo'} and all(f['flag_value'] for f in flags),'voucher flags')
        self.passed('V10-V20 voucher owner/identity checks, exact flags, four-worker replay, not_required')

        p=self.buy()
        results=self.race([lambda:self.use(p,self.target('admin'),'one'),lambda:self.use(p,self.target('admin'),'two')])
        require(sum(not isinstance(r,str) for r in results)==1 and 'PURCHASE_ALREADY_REDEEMED' in results,'different-key race')
        self.passed('R23 same purchase different keys: one winner')
        p1,p2=self.buy('other'),self.buy('other')
        results=self.race([lambda:self.use(p1,self.target('owner')),lambda:self.use(p2,self.target('owner'))])
        require(sum(not isinstance(r,str) for r in results)==1 and 'STEAL_TARGET_SHIELDED' in results,'same target race')
        require(self.cycle()['cycle_number']==2 and self.cycle()['history_watermark_id'],'first cycle completion')
        require(all(not f['flag_value'] for f in self.select('trainer_flags',season_id=self.season['id'],flag_type='robbed')),'cycle marks not cleared')
        self.passed('R24/R27 same target race; completing robbery succeeds, watermark advances and flags clear')

        p1,p2=self.buy(),self.buy('admin')
        results=self.race([lambda:self.use(p1,self.target('other',1)),lambda:self.use(p2,self.target('other',2))])
        require(sum(not isinstance(r,str) for r in results)==1 and 'STEAL_VICTIM_ALREADY_ROBBED' in results,'same victim race')
        self.passed('R25 two actors/different entities/same victim: only one cycle entry')
        p1,p2=self.buy(),self.buy('admin')
        results=self.race([lambda:self.use(p1,self.target('admin',1)),lambda:self.use(p2,self.target('owner',1))])
        require(all(not isinstance(r,str) for r in results),'opposite direction deadlock/rejection')
        require(self.cycle()['cycle_number']==3,'opposite-direction cycle reset')
        self.passed('R26 opposite A/B thefts complete without deadlock')
        self.use(self.buy(),self.target('other',3))
        before=self.cycle()
        p1,p2=self.buy(),self.buy('other')
        results=self.race([lambda:self.use(p1,self.target('admin',2)),lambda:self.use(p2,self.target('owner',2))])
        require(all(not isinstance(r,str) for r in results),'boundary race failed')
        require(self.cycle()['cycle_number']==before['cycle_number']+1,'boundary advanced more than once')
        self.passed('R27/RV14 final two operations: one exact cycle advancement')

        # Paused adapter has captured the VICTIM head; advance its real identity chain.
        p=self.buy()
        captured,release=Event(),Event()
        client=self.client
        expected=self.identities['other']['head']
        class PausedClient:
            def table(self,name): return client.table(name)
            def rpc(self,name,args):
                require(args['p_expected_revision_id']==expected,'wrong victim head')
                captured.set()
                require(release.wait(60),'paused robbery timeout')
                return client.rpc(name,args)
        self.owner=self.actors['other']
        _,parsed=self.save(6,clone=False)
        payload=self.identities['other']['parsed']['payload']
        self.client.table('parsed_saves').update({'payload':payload}).eq('id',parsed['id']).execute()
        self.owner=self.actors['owner']
        request=RedemptionRequest(self.season['id'],self.owner['id'],p['id'],self.target('other',4),'stale')
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(SupabaseRedemptionRepository(PausedClient()).redeem_purchase,request)
            try:
                require(captured.wait(60),'capture victim head timeout')
                self.owner=self.actors['other']
                self.reconcile(parsed,2)
            finally:
                self.owner=self.actors['owner']
                release.set()
            self.reject(future.result,'POKEMON_TARGET_STALE')
        require(self.use(purchase,self.target('other'))==receipt,'retry after victim advance changed')
        self.passed('R target head race: stale denied; original successful receipt survives new victim head')

        # A retirement can complete the remaining active set before the next theft.
        self.use(self.buy(),self.target('other',5))
        self.use(self.buy('other'),self.target('owner',3))
        self.client.table('season_players').update({'status':'retired'}).eq('id',self.players['admin']['id']).execute()
        before=self.cycle()['cycle_number']
        self.use(self.buy(),self.target('other',6))
        require(self.cycle()['cycle_number']==before+1,'active-set shrink pre-reset missing')
        self.passed('R cycle honors active-set retirement and advances historical watermark before fresh theft')

        robbery_item=self.select('shop_items',code='robar_pokemon')[0]
        theft_promo=self.insert('shop_promotions',dict(season_id=self.season['id'],shop_item_id=robbery_item['id'],
            promotion_type='normal',status='ended',base_price=12,effective_price=6,stock_total=2,stock_used=1))
        promotional=self.buy('other',promotion_id=theft_promo['id'])
        self.use(promotional,self.identities['owner']['party'][0])
        require(self.select('shop_promotions',id=theft_promo['id'])[0]==theft_promo,'robbery changed paid promo')
        pending=next(g for g in self.select('purchases',season_id=self.season['id'],acquisition_type='reward')
                     if g['trainer_id']==self.actors['owner']['id'] and g['status']=='pending')
        self.reject(lambda:self.use(pending,self.target('owner',4)),'POKEMON_ALREADY_SHIELDED')
        self.denied(lambda:self.client.rpc('api_redeem_purchase',dict(p_season_id=self.season['id'],
            p_trainer_id=self.owner['id'],p_purchase_id=pending['id'],p_pokemon_entity_id=self.identities['owner']['dead'],
            p_idempotency_key='stale-voucher',p_expected_revision_id=str(uuid4()))).execute(),'stale voucher',('PT409',))
        self.use(pending,self.identities['owner']['dead'])
        self.passed('R normal/promo parity and party theft; V13/V15 own Caja 8 voucher, shield and stale denial')

        events=self.select('activity_events',season_id=self.season['id'])
        redemptions=self.select('redemptions',season_id=self.season['id'])
        gifts=self.select('purchases',season_id=self.season['id'],acquisition_type='reward')
        require(len(gifts)==sum(r['effect_code']=='steal' for r in redemptions),'gift count differs from robbery history')
        require(len(events)==len(redemptions) and all(e['visibility']=='owner' for e in events),'private exactly-once events')
        require(not self.select('public_activity_events',self.readers['other'],season_id=self.season['id']),'public event leak')
        foreign_events=self.select('activity_events',self.readers['other'],season_id=self.season['id'])
        require(all(e['trainer_id']==self.actors['other']['id'] for e in foreign_events),'victim reads robber private event')
        require(all(set(e['payload'])==set(asdict(receipt)) for e in events),'private identity evidence leak')
        args=dict(p_season_id=self.season['id'],p_trainer_id=self.owner['id'],p_purchase_id=purchase['id'],
            p_pokemon_entity_id=self.target('other'),p_idempotency_key='robbery',p_expected_revision_id=expected)
        for role in ('owner','other','admin','anon'):
            reader=self.readers[role]
            self.denied(lambda:reader.rpc('api_redeem_purchase',args).execute(),'browser RPC')
            self.denied(lambda:self.select('robbery_cycles',reader,season_id=self.season['id']),'cycle private read')
            for table in ('robbery_cycles','purchases','redemptions','pokemon_entity_flags','trainer_flags','activity_events'):
                self.denied(lambda t=table:reader.table(t).delete().eq('season_id',self.season['id']).execute(),'browser write')
        require(not self.select('coin_transactions',season_id=self.season['id']),'ledger mutated')
        require(self.select('shop_promotions',id=promo['id'])[0]==promo,'promotion stock mutated')
        for identity in self.identities.values():
            require(self.select('parsed_saves',id=identity['parsed']['id'])[0]['payload']==identity['parsed']['payload'],'source save mutated')
        self.passed('RV16-RV19 privacy, browser/admin/anon denials, one gift/event per robbery, no ledger/stock/save mutation')

    def cleanup(self):
        if self.season:
            sid=self.season['id']
            # Unlink only this synthetic graph before deleting the circular origin/receipt FKs.
            self.client.table('robbery_cycles').delete().eq('season_id',sid).execute()
            empty={key:None for key in ('idempotency_key','effect_code','target_pokemon_entity_id',
                'target_owner_trainer_id','identity_revision_id','physical_effect_status','physical_effect_completed_at',
                'requested_at','activity_event_id','receipt','gift_purchase_id','robbery_cycle_number')}
            self.client.table('redemptions').update(empty).eq('season_id',sid).execute()
            for gift in self.select('purchases',season_id=sid,acquisition_type='reward'):
                self.client.table('redemptions').delete().eq('purchase_id',gift['id']).execute()
            item=self.select('shop_items',code='blindar_pokemon')[0]
            self.client.table('purchases').update(dict(acquisition_type='paid',origin_redemption_id=None,
                unit_price=1,shop_item_id=item['id'])).eq('season_id',sid).eq('acquisition_type','reward').execute()
            self.client.table('seasons').update({'current_matchday_id':None}).eq('id',sid).execute()
            self.client.table('purchases').update({'promotion_id':None}).eq('season_id',sid).execute()
            self.client.table('shop_promotions').delete().eq('season_id',sid).execute()
            self.client.table('matchdays').delete().eq('season_id',sid).execute()
            self.client.table('season_config_versions').delete().eq('season_id',sid).execute()
        super().cleanup()
