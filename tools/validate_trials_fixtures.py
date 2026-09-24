"""Shared 8K.1 real PostgreSQL/PostgREST cases; only scoped synthetic data."""
from decimal import Decimal
from uuid import uuid4

from app.api.trial_models import (CreateTrialBody, UpdateTrialBody, ResolveTrialBody,
    CorrectTrialBody, CancelTrialBody, TrialReceipt, TrialList, TrialView)
from app.domain.normal_purchases import NormalPurchaseRequest
from app.domain.promotional_purchases import PromotionalPurchaseRequest
from app.repositories.supabase.normal_purchases import SupabaseNormalPurchaseRepository
from app.repositories.supabase.trials import SupabaseTrialRepository
from tools.validate_season_lifecycle_fixtures import SeasonLifecycleFixtures, require

BODIES=dict(create=CreateTrialBody,proposal=UpdateTrialBody,resolve=ResolveTrialBody,correct=CorrectTrialBody,cancel=CancelTrialBody)


class TrialsFixtures(SeasonLifecycleFixtures):
    def __init__(self, client, readers, auth_ids, run_id=None):
        super().__init__(client,readers,auth_ids,run_id or 'phase8k1_validation_'+uuid4().hex)
        self.trials=SupabaseTrialRepository(client)

    def setup(self):
        super().setup()
        # The second JWT belongs to an ordinary participant, never a judge/admin.
        self.client.table('trainers').update({'auth_user_id':None}).eq('id',self.admin2['id']).execute()
        self.recorder=self.trainers[3]
        self.client.table('trainers').update({'auth_user_id':self.auth_ids['other']}).eq('id',self.recorder['id']).execute()

    def trial(self,op,sid,cid=None,body=None,key=None,actor=None):
        r=dict(actor_trainer_id=actor or self.owner['id'],season_id=sid)
        if cid: r['resource_id']=cid
        if body is not None:
            r.update(body=BODIES[op].model_validate(body).model_dump(mode='json'),idempotency_key=key or uuid4().hex)
        result=self.trials.execute(op,r)
        (TrialList if op=='list' else TrialView if op=='detail' else TrialReceipt).model_validate(result)
        return result

    def create_body(self,accused=None,**kw):
        return dict(title='Manual Discord case',description='Safe public summary',is_public=True,
            evidence='PRIVATE evidence',accused_trainer_id=accused or self.trainers[4]['id'],**kw)

    def case(self,sid,**kw):
        return self.trial('create',sid,body=self.create_body(),**kw)['case_id']

    def decision(self,sid,cid,sanctions=None,verdict='guilty',op='resolve',**kw):
        body=dict(expected_case_revision=self.rows('trial_cases',id=cid)[0]['revision'],verdict=verdict,
            decision_summary='PRIVATE agreed manually in Discord',sanctions=sanctions or [])
        if op=='correct': body['reason']='PRIVATE recording error'
        return self.trial(op,sid,cid,body,**kw)

    def banned(self,sid,tid=None):
        d=self.rows('matchdays',id=self.state(sid)['current_matchday_id'])[0]
        return self.rpc('api_is_store_banned',dict(p_season_id=sid,p_trainer_id=tid or self.trainers[4]['id'],p_matchday_number=d['number']))

    def finish_day(self,sid,did):
        self.open(sid,did); self.results(sid,did); self.close(sid,did)
        return self.state(sid)['current_matchday_id']

    def coin_rows(self,cid): return self.rows('coin_transactions',trial_case_id=cid)

    def run(self):
        self.setup(); self.basics(); self.effects(); self.timing(); self.concurrent(); self.permissions_trials()

    def basics(self):
        sid,did=self.season(3); body=self.create_body(); key=uuid4().hex
        r=self.race(lambda:self.trial('create',sid,body=body,key=key),lambda:self.trial('create',sid,body=body,key=key))
        require(r[0]['case_id']==r[1]['case_id'] and r[0]['operation_id']==r[1]['operation_id'],'Create replay duplicated')
        cid=r[0]['case_id']; require(r[0]['case_number']==1,'First number')
        self.reject(lambda:self.trial('create',sid,body=dict(body,title='changed'),key=key),'IDEMPOTENCY_CONFLICT')
        r=self.race(lambda:self.case(sid),lambda:self.case(sid,actor=self.recorder['id']))
        require(len(set(r))==2 and sorted(c['case_number'] for c in self.rows('trial_cases',season_id=sid))==[1,2,3],'Number race')
        proposal=dict(title='Edited',description='Safe',is_public=True,evidence='PRIVATE',expected_case_revision=1)
        self.reject(lambda:self.trial('proposal',sid,cid,proposal,actor=self.recorder['id']),'CREATOR_REQUIRED')
        proposal_key=uuid4().hex
        edited=self.trial('proposal',sid,cid,proposal,proposal_key)
        require(self.trial('proposal',sid,cid,proposal,proposal_key)==dict(edited,replayed=True),'Proposal replay')
        self.reject(lambda:self.trial('proposal',sid,cid,proposal),'STALE_REVISION')
        self.decision(sid,cid,actor=self.recorder['id'])
        require(self.rows('trial_cases',id=cid)[0]['verdict']=='guilty' and not self.rows('penalties',trial_case_id=cid),'Warning-only guilt lost')
        self.reject(lambda:self.trial('proposal',sid,cid,dict(proposal,expected_case_revision=3)),'TRIAL_NOT_OPEN')
        c2=r[0]; self.decision(sid,c2,verdict='not_guilty')
        require(self.rows('trial_cases',id=c2)[0]['verdict']=='not_guilty','Explicit acquittal')
        c3=r[1]; cancel_body=dict(expected_case_revision=1,reason='Withdrawn'); cancel_key=uuid4().hex
        cancelled=self.trial('cancel',sid,c3,cancel_body,cancel_key,actor=self.recorder['id'])
        require(self.trial('cancel',sid,c3,cancel_body,cancel_key,actor=self.recorder['id'])==dict(cancelled,replayed=True),'Cancel replay')
        require(self.rows('trial_cases',id=c3)[0]['status']=='cancelled','Logical cancellation')
        c4=self.case(sid); require(self.rows('trial_cases',id=c4)[0]['case_number']==4,'Reused number')
        accused_case=self.trial('create',sid,body=self.create_body(accused=self.owner['id']),actor=self.recorder['id'])['case_id']
        self.decision(sid,accused_case)  # accused records, with no application votes
        require(not self.rows('trial_votes',trial_case_id=accused_case),'Invented votes')
        self.reject(lambda:self.trial('create',sid,body=body,actor=self.admin['id']),'PARTICIPANT_INACTIVE')
        self.passed('K01 numbering/concurrent create/replay; creator-only edit/cancel; explicit guilty-warning/acquittal; equal non-admin/creator/accused recorders; no jury')

    def effects(self):
        sid,did=self.season(3); cid=self.case(sid); tid=self.trainers[4]['id']
        sanctions=[dict(type='coins_reduction',amount=50),dict(type='points_reduction',amount='1.25'),
            dict(type='store_ban',duration_matchdays=2),dict(type='pokemon_release',text='PRIVATE manual release'),dict(type='other',text='PRIVATE warning')]
        body=dict(expected_case_revision=1,verdict='guilty',decision_summary='Agreed',sanctions=sanctions); key=uuid4().hex
        r=self.trial('resolve',sid,cid,body,key,actor=self.recorder['id'])
        require(self.trial('resolve',sid,cid,body,key,actor=self.recorder['id'])==dict(r,replayed=True),'Stable resolve receipt')
        require([c['amount'] for c in self.coin_rows(cid)]==[-50],'Debt/full exact-once debit')
        require(self.banned(sid) and len(self.rows('penalties',trial_case_id=cid))==5,'Missing typed effect')
        for table in ('pokemon_entities','pokemon_flags','pokemon_entity_flags','save_files','redemptions','team_locks'):
            require(not self.rows(table,season_id=sid),'Text note mutated '+table)
        did2=self.finish_day(sid,did)
        first=self.rows('matchday_snapshots',matchday_id=did)[0]
        pid=self.rows('season_players',season_id=sid,trainer_id=tid)[0]['id']
        p=next(x for x in first['snapshot']['standings'] if x['trainer_id']==pid)
        require(Decimal(str(p['penalties']['points_reduction']))==Decimal('1.25'),'Decimal capture')
        require(self.banned(sid),'Two-round ban ended early')
        self.finish_day(sid,did2)
        require(not self.banned(sid),'Two-round ban did not end exactly')
        projection=self.rows('public_sanctioned_points',season_id=sid,season_player_id=pid)[0]
        require(Decimal(str(projection['earned_points']))-Decimal(str(projection['sanctioned_points']))==Decimal('1.25'),'Multiplied cumulative deduction')
        require(sum(c['amount'] for c in self.rows('coin_transactions',season_id=sid) if c['trial_revision_id'] is None)==42,'Sanction changed rewards')
        originals=self.rows('trial_case_revisions',case_id=cid); ledger=self.coin_rows(cid); penalties=self.rows('penalties',trial_case_id=cid)
        corrected_body=dict(expected_case_revision=2,verdict='guilty',decision_summary='Corrected agreed amount',reason='Recording error',
            sanctions=[dict(type='coins_reduction',amount=20),dict(type='points_reduction',amount='.50')]); correction_key=uuid4().hex
        r=self.trial('correct',sid,cid,corrected_body,correction_key)
        require(self.trial('correct',sid,cid,corrected_body,correction_key)==dict(r,replayed=True),'Correction replay')
        self.reject(lambda:self.trial('correct',sid,cid,dict(corrected_body,reason='Different'),correction_key),'IDEMPOTENCY_CONFLICT')
        require(sum(c['amount'] for c in self.coin_rows(cid))==-20 and all(x in self.coin_rows(cid) for x in ledger),'Compensation difference')
        require(self.rows('matchday_snapshots',matchday_id=did)[0]==first,'Correction rewrote closed capture')
        did3=self.state(sid)['current_matchday_id']; self.finish_day(sid,did3)
        projection=self.rows('public_sanctioned_points',season_id=sid,season_player_id=pid)[0]
        require(Decimal(str(projection['points_reduction']))==Decimal('.50'),'Future corrected net amount')
        # Pending cases do not block finish/archive.
        pending=self.case(sid); self.life('finish',sid); self.life('archive',sid)
        frozen={t:self.rows(t,season_id=sid) for t in ('matchday_snapshots','matchday_snapshot_revisions','hall_of_fame_entries','season_archive_snapshots','matchday_movements')}
        self.decision(sid,cid,verdict='not_guilty',op='correct')
        require(sum(c['amount'] for c in self.coin_rows(cid))==0,'Undo did not return full debit')
        for row in originals: require(row in self.rows('trial_case_revisions',case_id=cid),'Decision rewritten')
        for row in penalties: require(row in self.rows('penalties',trial_case_id=cid),'Penalty rewritten')
        require(all(self.rows(t,season_id=sid)==v for t,v in frozen.items()),'Archived history rewritten')
        require(self.rows('public_sanctioned_points',season_id=sid,season_player_id=pid)[0]==projection,'Archived projection changed')
        for effect in (dict(type='points_reduction',amount=1),dict(type='coins_reduction',amount=1),dict(type='store_ban',duration_matchdays=1)):
            self.reject(lambda:self.decision(sid,cid,[effect],op='correct'),'SEASON_NOT_ACTIVE')
            self.reject(lambda:self.decision(sid,pending,[effect]),'SEASON_NOT_ACTIVE')
        self.decision(sid,pending,[dict(type='other',text='Administrative warning')])
        self.passed('K02 five typed effects; full debt/exact replay; cumulative exact decimal captures/rewards; append-only difference/undo after archive, frozen history unchanged')

    def timing(self):
        for opened in (False,True):
            sid,did=self.season(1); cid=self.case(sid)
            if opened: self.open(sid,did)
            self.reject(lambda:self.decision(sid,cid,[dict(type='store_ban',duration_matchdays=2),dict(type='coins_reduction',amount=1)]),'STORE_BAN_ROUNDS_UNAVAILABLE')
            require(not self.coin_rows(cid) and self.rows('trial_cases',id=cid)[0]['revision']==1,'Illegal ban partial commit')
            self.decision(sid,cid,[dict(type='store_ban',duration_matchdays=1)])
            require(self.banned(sid),'Ban not immediate')
            if not opened: self.open(sid,did)
            self.results(sid,did); self.close(sid,did)
            require(not self.banned(sid),'Final CLOSED pointer ban did not expire')
            c2=self.case(sid)
            self.reject(lambda:self.decision(sid,c2,[dict(type='points_reduction',amount=1),dict(type='coins_reduction',amount=1)]),'NO_FUTURE_POINTS_CAPTURE')
            require(not self.coin_rows(c2),'Mixed invalid verdict partially applied')
        sid,did=self.season(3); cid=self.case(sid)
        self.decision(sid,cid,[dict(type='store_ban',duration_matchdays=3)])
        config=self.config(sid); config.update(effective_from_matchday=2,total_matchdays=2)
        self.reject(lambda:self.call('create_config',sid,config),'INVALID_CONFIG')
        self.finish_day(sid,did); self.decision(sid,cid,[dict(type='store_ban',duration_matchdays=1)],op='correct')
        require(not self.banned(sid),'Reduced duration restarted instead of compensating original range')
        self.passed('K03 scheduled/open one-round ban exact final boundary, insufficient rounds and no future points atomic rejection; reduced ban keeps original anchor')

    def concurrent(self):
        sid,did=self.season(2)
        for conflict in ('proposal','cancel','resolve'):
            cid=self.case(sid); decision=dict(expected_case_revision=1,verdict='guilty',decision_summary='Agreed',sanctions=[])
            body=dict(expected_case_revision=1,reason='Withdraw') if conflict=='cancel' else decision if conflict=='resolve' else dict(title='Edited',description='Safe',is_public=True,evidence='',expected_case_revision=1)
            self.one_winner(self.race(lambda:self.trial('resolve',sid,cid,decision),lambda:self.trial(conflict,sid,cid,body)),'STALE_REVISION')
        cid=self.case(sid); body=dict(expected_case_revision=1,verdict='guilty',decision_summary='Agreed',sanctions=[dict(type='coins_reduction',amount=10)]); key=uuid4().hex
        r=self.race(lambda:self.trial('resolve',sid,cid,body,key),lambda:self.trial('resolve',sid,cid,body,key))
        require(r[0]['operation_id']==r[1]['operation_id'] and len(self.coin_rows(cid))==1,'Resolve race duplicate')
        body.update(expected_case_revision=2,reason='Review',verdict='not_guilty',sanctions=[])
        self.one_winner(self.race(lambda:self.trial('correct',sid,cid,body),lambda:self.trial('correct',sid,cid,body)),'STALE_REVISION')
        cases=[self.case(sid),self.case(sid)]
        r=self.race(*(lambda cid=cid:self.decision(sid,cid,[dict(type='coins_reduction',amount=5)]) for cid in cases))
        require(all(isinstance(x,dict) for x in r) and sum(x['amount'] for cid in cases for x in self.coin_rows(cid))==-10,'Independent trials lost debit')
        self.passed('K04 proposal/resolve, cancel/resolve, different resolve keys, same-key resolve replay, corrections and independent cases serialized')
        self.purchase_races()
        sid,did=self.season(2); cid=self.case(sid)
        r=self.race(lambda:self.decision(sid,cid,[dict(type='points_reduction',amount='.25')]),lambda:self.open(sid,did))
        require(all(isinstance(x,dict) for x in r),'Resolve/open race')
        self.results(sid,did); cid=self.case(sid)
        r=self.race(lambda:self.decision(sid,cid,[dict(type='points_reduction',amount='.50')]),lambda:self.close(sid,did))
        require(isinstance(r[0],dict) and (isinstance(r[1],dict) or r[1]=='STALE_INPUTS'),'Points/close race')
        if self.ds(sid,did)['state']=='open': self.close(sid,did)
        day=self.state(sid)['current_matchday_id']; self.finish_day(sid,day)
        projection=self.rows('public_sanctioned_points',season_id=sid)
        pid=self.rows('season_players',season_id=sid,trainer_id=self.trainers[4]['id'])[0]['id']
        require(Decimal(str(next(x for x in projection if x['season_player_id']==pid)['points_reduction']))==Decimal('.75'),'Concurrent decimal effects lost/doubled')
        cid=self.case(sid)
        r=self.race(lambda:self.decision(sid,cid,[dict(type='coins_reduction',amount=3)]),lambda:self.life('finish',sid))
        require(isinstance(r[1],dict) and (isinstance(r[0],dict) or r[0]=='SEASON_NOT_ACTIVE'),'Finish race')
        if isinstance(r[0],dict): self.decision(sid,cid,verdict='not_guilty',op='correct')
        sid,did=self.season(); cid=self.case(sid); player=self.rows('season_players',season_id=sid,trainer_id=self.owner['id'])[0]
        r=self.race(lambda:self.decision(sid,cid,[dict(type='coins_reduction',amount=3)]),lambda:self.change(sid,player['id']))
        require(isinstance(r[1],dict) and (isinstance(r[0],dict) or r[0]=='PARTICIPANT_INACTIVE'),'Participant status race')
        self.passed('K05 resolve/open, points/close (stale context rejected), finish and actor retirement; compensatory correction after finish')

    def purchase_races(self):
        for mode in ('coins','promo','ban','correction'):
            sid,did=self.season(); tid=self.owner['id']; player=self.rows('season_players',season_id=sid,trainer_id=tid)[0]
            cid=self.trial('create',sid,body=self.create_body(accused=tid))['case_id']
            item=self.rows('shop_items',category='bayas')[0]
            self.insert('coin_transactions',dict(season_id=sid,trainer_id=tid,season_player_id=player['id'],amount=20,transaction_type='admin_adjustment'))
            request=NormalPurchaseRequest(sid,tid,item['id'],uuid4().hex)
            buy=lambda:self.adapter(lambda:SupabaseNormalPurchaseRepository(self.client).create_normal_purchase(request))
            if mode=='promo':
                promo=self.insert('shop_promotions',dict(season_id=sid,matchday_id=did,shop_item_id=item['id'],promotion_type='normal',status='active',base_price=item['base_price'],effective_price=max(0,item['base_price']-1),stock_total=2))
                request=PromotionalPurchaseRequest(sid,tid,promo['id'],uuid4().hex)
                buy=lambda:self.adapter(lambda:SupabaseNormalPurchaseRepository(self.client).create_promotional_purchase(request))
            effect=[dict(type='store_ban',duration_matchdays=1)] if mode=='ban' else [dict(type='coins_reduction',amount=50)]
            if mode=='correction':
                self.decision(sid,cid,effect)
                act=lambda:self.decision(sid,cid,verdict='not_guilty',op='correct')
            else: act=lambda:self.decision(sid,cid,effect)
            r=self.race(act,buy)
            require(isinstance(r[0],dict) and (isinstance(r[1],dict) or r[1] in ('INSUFFICIENT_FUNDS','STORE_BANNED')),'Purchase race '+mode+' '+str(r))
            expected=0 if mode in ('ban','correction') else -50
            require(sum(x['amount'] for x in self.coin_rows(cid))==expected,'Race lost coin effect')
            require(len(self.rows('purchases',season_id=sid))==(1 if isinstance(r[1],dict) else 0),'Purchase partial commit')
        self.passed('K06 coins/normal, coins/promo, ban/purchase, correction/purchase: serial wallet/shop decisions with no refund or double debit')

    def permissions_trials(self):
        sid,did=self.season(); cid=self.case(sid); self.decision(sid,cid,[dict(type='other',text='PRIVATE note')])
        public=self.trial('detail',sid,cid,actor=self.recorder['id'])
        require(public['detail'] is None and 'PRIVATE' not in str(public),'API private details leaked')
        private=self.trial('detail',sid,cid); require('PRIVATE' in str(private['detail']),'Creator detail unavailable')
        c2=self.trial('create',sid,body=dict(self.create_body(),is_public=False))['case_id']
        self.reject(lambda:self.trial('detail',sid,c2,actor=self.recorder['id']),'TRIAL_NOT_FOUND')
        self.decision(sid,c2,[dict(type='coins_reduction',amount=1)])
        self.client.table('trainers').update({'globally_enabled':False}).eq('id',self.owner['id']).execute()
        try:
            self.reject(lambda:self.trial('list',sid),'TRAINER_DISABLED')
            self.reject(lambda:self.case(sid),'TRAINER_DISABLED')
        finally: self.client.table('trainers').update({'globally_enabled':True}).eq('id',self.owner['id']).execute()
        legacy=self.insert('trial_cases',dict(season_id=sid,created_by_trainer_id=self.owner['id'],accused_trainer_id=self.trainers[4]['id'],title='Ambiguous imported case',status='resolved'))
        self.reject(lambda:self.decision(sid,legacy['id'],op='correct'),'TRIAL_SOURCE_UNSUPPORTED')
        require(self.trial('detail',sid,legacy['id'])['verdict'] is None,'Fabricated historical verdict')
        orphan=self.insert('trial_cases',dict(season_id=sid,title='PRIVATE unassigned historical case',payload={'is_public':False}))
        self.reject(lambda:self.trial('detail',sid,orphan['id'],actor=self.recorder['id']),'TRIAL_NOT_FOUND')
        require(not self.readers['other'].table('public_penalties').select('*').eq('trial_case_id',c2).execute().data,'Private sanction public')
        require(not self.readers['other'].table('trial_case_revisions').select('*').eq('case_id',cid).execute().data,'History RLS leak')
        for role in ('owner','other','admin','anon'):
            client=self.readers[role]
            for table,changes in (('trial_cases',{'title':'Bypass'}),('penalties',{'amount':99}),('trial_votes',{'vote':'guilty'})):
                for action in ('update','insert','delete'):
                    query=getattr(client.table(table),action)(changes) if action!='delete' else client.table(table).delete()
                    if action!='insert': query=query.eq('id',cid)
                    try: query.execute()
                    except Exception as exc: require(str(getattr(exc,'code',''))=='42501','Wrong direct-write denial '+table)
                    else: raise AssertionError('Direct browser write '+table+'/'+action)
            try: client.rpc('api_trial_mutate',{'p_request':{}}).execute()
            except Exception as exc: require(str(getattr(exc,'code',''))=='42501','RPC grant bypass')
            else: raise AssertionError('Browser executed service RPC')
        for table,filters,changes in (('trial_case_revisions',{'case_id':cid},{'decision_summary':'rewrite'}),('penalties',{'trial_case_id':cid},{'amount':99})):
            query=self.client.table(table).update(changes)
            for k,v in filters.items(): query=query.eq(k,v)
            try: query.execute()
            except Exception as exc: require(getattr(exc,'message','')=='historical_artifact_immutable','Wrong immutable rejection')
            else: raise AssertionError('Mutable history')
        try: self.client.table('coin_transactions').update({'amount':99}).eq('trial_case_id',c2).execute()
        except Exception as exc: require(getattr(exc,'message','')=='historical_artifact_immutable','Wrong immutable ledger rejection')
        else: raise AssertionError('Mutable sanction ledger')
        self.passed('K07 JWT/RLS public shape vs private evidence/history; table+column browser judicial DML and RPC denied, immutable decisions/effects')

    def cleanup(self):
        for sid in self.seasons:
            # FK order, only this run's IDs. No trigger disabling or global delete.
            self.client.table('coin_transactions').delete().eq('season_id',sid).execute()
            self.client.table('penalties').delete().eq('season_id',sid).execute()
            self.client.table('trial_case_revisions').delete().eq('season_id',sid).execute()
            self.client.table('trial_case_counters').delete().eq('season_id',sid).execute()
            for table in ('trial_case_revisions','trial_case_counters'):
                require(not self.rows(table,season_id=sid),'Trial fixture residue '+table)
        super().cleanup()
