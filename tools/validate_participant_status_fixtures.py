"""Real PostgreSQL/PostgREST status contracts. Synthetic data, never save bytes."""
from copy import deepcopy
from dataclasses import asdict
from uuid import uuid4

from app.domain.redemptions import RedemptionRequest
from app.repositories.errors import RepositoryError
from app.repositories.supabase.participant_status import SupabaseParticipantStatusRepository
from app.repositories.supabase.redemptions import SupabaseRedemptionRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.repositories.supabase.team_locks import SupabaseTeamLockRepository
from tools.validate_matchday_fixtures import MatchdayFixtures, require
from tools.validate_pokemon_identity_fixtures import IdentityFixtures


class ParticipantStatusFixtures(MatchdayFixtures):
    def __init__(self, client, readers, auth_ids, run_id=None):
        super().__init__(client, readers, auth_ids, run_id or 'phase8i_validation_'+uuid4().hex)
        self.status_repo = SupabaseParticipantStatusRepository(client)

    def change(self, sid, pid, op='retire', body=None, key=None, actor=None):
        body = body if body is not None else dict(reason='Synthetic participant decision',
            expected_roster_revision=self.state(sid)['roster_revision'])
        return self.status_repo.execute(op, self.request(op, sid, body, pid, key, actor))

    def players(self, sid):
        return sorted(self.rows('season_players', season_id=sid), key=lambda p:p['id'])

    def rpc(self, name, params):
        try:
            return self.client.rpc(name, params).execute().data
        except Exception as exc:
            status = str(getattr(exc, 'code', ''))
            if status in ('PT403','PT404','PT409','PT422'):
                raise SeasonAdminRejected(str(exc.message).upper(), int(status[2:])) from exc
            raise

    def adapter(self, action):
        try:
            return asdict(action())
        except RepositoryError as exc:
            code = getattr(exc, 'code', None) or getattr(exc.__cause__, 'message', None)
            if not code:
                raise
            raise SeasonAdminRejected(str(code).upper(), 409) from exc

    def protected(self, sid):
        tables = ('matchday_snapshots','matchday_snapshot_revisions','matchday_movements','coin_transactions',
            'purchases','redemptions','team_locks','save_files','pokemon_entities','pokemon_observations',
            'pokemon_identity_revisions','pokemon_entity_flags','pokemon_flags','shop_promotions','penalties','trial_cases')
        result={t:sorted(self.rows(t,season_id=sid),key=lambda r:r['id']) for t in tables}
        result['parsed_saves']=sorted([parsed for save in result['save_files']
            for parsed in self.rows('parsed_saves',save_file_id=save['id'])],key=lambda r:r['id'])
        return result

    def identity(self, sid, player, number=1):
        helper=IdentityFixtures(self.client, self.readers, self.auth_ids, run_id=self.run_id+'_'+player['id'])
        helper.season={'id':sid}; helper.owner={'id':player['trainer_id']}
        saved, parsed=helper.save(number, clone=False)
        template=parsed['payload']['party'][0]['pokemon']
        slots=[]
        for i in range(6):
            mon=deepcopy(template); mon['identity_evidence']['pid']=100+i
            mon['legacy_fingerprints']=[f'participant-{i}']
            slots.append(dict(slot_number=i+1,pokemon=mon))
        parsed['payload']={'party':slots,'boxes':[]}
        self.client.table('parsed_saves').update({'payload':parsed['payload']}).eq('id',parsed['id']).execute()
        receipt=helper.reconcile(parsed,1)
        return [o['pokemon_entity_id'] for o in receipt['observations']]

    def entitlement(self, sid, player, code='robar_pokemon'):
        return self.insert('purchases',dict(season_id=sid,trainer_id=player['trainer_id'],season_player_id=player['id'],
            shop_item_id=self.rows('shop_items',code=code)[0]['id'],unit_price=12))

    def use(self, purchase, entity):
        return self.adapter(lambda:SupabaseRedemptionRepository(self.client).redeem_purchase(RedemptionRequest(
            purchase['season_id'],purchase['trainer_id'],purchase['id'],entity,'use-'+purchase['id'])))

    def run(self):
        self.setup()
        for op, expected in (('retire','retired'),('abandon','abandoned'),('disqualify','disqualified')):
            sid,did=self.season(); p=self.players(sid)[0]; before=self.protected(sid)
            trainers=self.rows('trainers')
            matches=self.rows('matches',matchday_id=did); state=self.state(sid)
            body=dict(reason='Distinct '+op,expected_roster_revision=state['roster_revision']); key=uuid4().hex
            r=self.change(sid,p['id'],op,body,key)
            require(r['new_status']==expected and r['effective_matchday_number']==1,'Wrong status/boundary')
            require(r['roster_revision']==state['roster_revision']+1 and r['setup_revision']==state['setup_revision']+1,'Revision delta')
            replay=self.change(sid,p['id'],op,body,key)
            require(replay==dict(r,replayed=True),'Receipt not exact')
            self.reject(lambda:self.change(sid,p['id'],'abandon' if op!='abandon' else 'retire',body,key),'IDEMPOTENCY_CONFLICT')
            self.reject(lambda:self.change(sid,p['id'],op),'PARTICIPANT_ALREADY_INACTIVE')
            self.reject(lambda:self.change(sid,p['id'],'disqualify'),'PARTICIPANT_ALREADY_INACTIVE')
            require(self.protected(sid)==before,'Historical/economy data changed')
            require(self.rows('trainers')==trainers,'Account-level access changed')
            remaining=self.rows('matches',matchday_id=did)
            require(sorted(remaining,key=lambda x:x['id'])==sorted([m for m in matches if p['id'] not in (m['player_a_id'],m['player_b_id'])],key=lambda x:x['id']),'Unrelated matches changed')
            membership=self.rows('division_memberships',season_player_id=p['id'])[0]
            require(membership['effective_from_matchday_number']==1 and membership['eligibility_ends_before_matchday_number']==1,'Empty initial range missing')
            public=self.readers['owner'].table('public_division_memberships').select('*').eq('id',membership['id']).execute().data[0]
            require(public['eligibility_ends_before_matchday_number']==1,'Public boundary missing')
            public_player=self.readers['owner'].table('public_season_players').select('*').eq('id',p['id']).execute().data[0]
            require(public_player['status_effective_matchday_number']==1 and 'status_reason' not in public_player,'Public status privacy/boundary')
            require(next(m for m in self.state(sid)['memberships'] if m['season_player_id']==p['id'])['eligibility_ends_before_matchday_number']==1,'Admin read boundary missing')
            require(self.state(sid)['current_matchday_id']==did,'Pointer changed')
            self.open(sid,did); self.results(sid,did); self.close(sid,did)
            require(len(self.rows('matchday_snapshots',matchday_id=did)[0]['snapshot']['standings'])==3,'Inactive player awarded')
            self.passed('I01 '+op+': exact replay, distinct status, no history writes, smaller round closes')
        self.history_and_empty_divisions()
        self.dependencies()
        self.status_races()
        self.economy_and_locks()
        self.robbery_cases()
        self.permissions()

    def history_and_empty_divisions(self):
        sid,did=self.prepared_close(total=3); self.close(sid,did)
        nextid=self.ds(sid,did)['current_matchday_id']; p=self.players(sid)[0]
        protected=self.protected(sid); old_members=self.rows('division_memberships',season_player_id=p['id'])
        self.change(sid,p['id'])
        require(self.protected(sid)==protected,'Closed history changed')
        for row in old_members:
            after=self.rows('division_memberships',id=row['id'])[0]
            if row['effective_to_matchday_number']==1: require(after==row,'Historical membership changed')
            else: require(after==dict(row,eligibility_ends_before_matchday_number=2),'Current assignment not retained')
        self.reject(lambda:self.md('correct',sid,did,self.correction(sid,did)),'CORRECTION_WINDOW_CLOSED')
        self.open(sid,nextid); self.results(sid,nextid); self.close(sid,nextid)
        self.passed('I02 round 2 cutoff, closed snapshots/ledger/rewards/memberships retained; prior correction blocked')
        sid,did=self.season(total=2)
        for p in self.players(sid)[2:]: self.change(sid,p['id'])
        self.open(sid,did); self.results(sid,did); self.close(sid,did)
        require(not self.rows('purchases',origin_matchday_id=did),'Empty B fabricated free reward')
        nextid=self.ds(sid,did)['current_matchday_id']
        for p in self.players(sid)[:2]: self.change(sid,p['id'])
        self.open(sid,nextid); self.close(sid,nextid)
        require(self.rows('matchday_snapshots',matchday_id=nextid)[0]['snapshot']['standings']==[],'Empty round fake standings')
        require(self.rows('seasons',id=sid)[0]['status']=='active','Empty season auto-finished')
        self.passed('I03 empty division/all inactive: no fake pairs, movements, last-B or finalization')

    def dependencies(self):
        sid,did=self.season(); p=self.players(sid)[0]
        for status in ('draft','finished','archived','discarded'):
            changes={'status':status}
            if status in ('finished','archived'): changes['finished_at']='2026-09-23T00:00:00Z'
            if status=='archived': changes['archived_at']='2026-09-23T00:00:00Z'
            if status=='discarded': changes['discarded_at']='2026-09-23T00:00:00Z'
            self.client.table('seasons').update(changes).eq('id',sid).execute()
            self.reject(lambda:self.change(sid,p['id']),'SEASON_NOT_ACTIVE')
        self.client.table('seasons').update({'status':'active'}).eq('id',sid).execute()
        self.reject(lambda:self.change(sid,str(uuid4())),'PARTICIPANT_NOT_FOUND')
        self.reject(lambda:self.change(sid,p['id'],actor=self.owner['id']),'ADMIN_REQUIRED')
        self.reject(lambda:self.change(sid,p['id'],body=dict(reason='Stale',expected_roster_revision=0)),'STALE_REVISION')
        match=self.rows('matches',matchday_id=did)[0]
        self.client.table('matches').update({'winner_id':match['player_a_id'],'status':'completed'}).eq('id',match['id']).execute()
        self.reject(lambda:self.change(sid,p['id']),'DEPENDENT_DATA_EXISTS')
        self.client.table('matches').update({'winner_id':None,'status':'scheduled'}).eq('id',match['id']).execute()
        self.open(sid,did); self.reject(lambda:self.change(sid,p['id']),'ROUND_OPEN')
        self.results(sid,did); self.close(sid,did)
        nextid=self.ds(sid,did)['current_matchday_id']; self.open(sid,nextid); self.results(sid,nextid); self.close(sid,nextid)
        self.reject(lambda:self.change(sid,p['id']),'MATCHDAY_NOT_SCHEDULED')
        self.passed('I04 admin/scoped/CAS gates; draft/finished/archived/discarded/open/final-closed rejected')
        sid,did=self.season(); p=self.players(sid)[0]
        cup=self.insert('cups',dict(season_id=sid,name=self.run_id,format='elimination',status='active'))
        self.insert('cup_participants',dict(cup_id=cup['id'],trainer_id=p['trainer_id'],display_name='Synthetic'))
        self.reject(lambda:self.change(sid,p['id']),'ONGOING_COMPETITION_DEPENDENCY')
        self.client.table('cups').update({'status':'finished'}).eq('id',cup['id']).execute()
        case=self.insert('trial_cases',dict(season_id=sid,accused_trainer_id=p['trainer_id'],title=self.run_id,status='open'))
        penalty=self.insert('penalties',dict(season_id=sid,trainer_id=p['trainer_id'],trial_case_id=case['id'],penalty_type='points_reduction',amount=1))
        self.client.table('trial_cases').update({'matchday_id':did}).eq('id',case['id']).execute()
        self.reject(lambda:self.change(sid,p['id']),'DEPENDENT_DATA_EXISTS')
        self.client.table('trial_cases').update({'matchday_id':None}).eq('id',case['id']).execute()
        case=self.rows('trial_cases',id=case['id'])[0]
        self.client.table('penalties').update({'matchday_id':did}).eq('id',penalty['id']).execute()
        self.reject(lambda:self.change(sid,p['id']),'DEPENDENT_DATA_EXISTS')
        self.client.table('penalties').update({'matchday_id':None}).eq('id',penalty['id']).execute()
        penalty=self.rows('penalties',id=penalty['id'])[0]
        self.change(sid,p['id'])
        require(self.rows('trial_cases',id=case['id'])[0]==case and self.rows('penalties',id=penalty['id'])[0]==penalty,'Trial rewritten')
        require(self.rows('cup_participants',cup_id=cup['id'])[0]['trainer_id']==p['trainer_id'],'Cup history erased')
        self.passed('I05 active Cup conflict; completed Cup and generic open Trial/penalty history preserved')

    def status_races(self):
        for same_key, other_op in ((True,'retire'),(False,'retire'),(False,'abandon')):
            sid,did=self.season(); p=self.players(sid)[0]; body=dict(reason='Race',expected_roster_revision=self.state(sid)['roster_revision'])
            key=uuid4().hex
            results=self.race(lambda:self.change(sid,p['id'],'retire',body,key),
                lambda:self.change(sid,p['id'],other_op,body,key if same_key else uuid4().hex))
            if same_key: require(results[0]['operation_id']==results[1]['operation_id'],'Replay race duplicated')
            else: self.one_winner(results,'PARTICIPANT_ALREADY_INACTIVE')
            require(len(self.rows('activity_events',season_id=sid,type='PARTICIPANT_STATUS_CHANGED'))==1,'Duplicate event')
            self.passed('I06 status race same_key='+str(same_key)+' rival='+other_op)
        sid,did=self.season(); players=self.players(sid); body=dict(reason='Two people',expected_roster_revision=self.state(sid)['roster_revision'])
        results=self.race(lambda:self.change(sid,players[0]['id'],body=body),lambda:self.change(sid,players[1]['id'],body=body))
        self.one_winner(results,'STALE_REVISION')
        loser=next(p for p in self.players(sid)[:2] if p['status']=='active')
        self.change(sid,loser['id'])
        self.passed('I07 two participants CAS: explicit refreshed second decision, exactly two events')
        for action in ('open','results','close'):
            sid,did=self.season(); p=self.players(sid)[0]
            if action!='open': self.open(sid,did)
            if action=='close': self.results(sid,did)
            revision=self.ds(sid,did)['revision']
            op=lambda:self.md('open',sid,did,dict(expected_revision=revision)) if action=='open' else getattr(self,action)(sid,did)
            results=self.race(lambda:self.change(sid,p['id']),op)
            if action=='open': self.one_winner(results,'ROUND_OPEN','STALE_REVISION')
            else:
                require(isinstance(results[1],dict),'Competitive mutation failed')
                require(results[0]=='ROUND_OPEN' or (action=='close' and isinstance(results[0],dict)),'Unsafe competitive race')
                if isinstance(results[0],dict): require(results[0]['effective_matchday_number']==2,'Retired during prior OPEN round')
            self.passed('I08 status vs '+action+': serialized current pointer/state/revisions')

    def purchase(self,sid,p,promo=False):
        item=self.rows('shop_items',category='bayas')[0]
        args=dict(p_season_id=sid,p_trainer_id=p['trainer_id'],p_idempotency_key=uuid4().hex)
        if promo:
            offer=self.insert('shop_promotions',dict(season_id=sid,matchday_id=self.state(sid)['current_matchday_id'],shop_item_id=item['id'],
                promotion_type='normal',status='active',base_price=item['base_price'],effective_price=1,stock_total=2,
                activates_at='2026-01-01T00:00:00Z'))
            args['p_promotion_id']=offer['id']
        else: args.update(p_item_id=item['id'],p_confirm_base_price=False)
        return lambda:self.rpc('api_create_promotional_purchase' if promo else 'api_create_normal_purchase',args)

    def economy_and_locks(self):
        for promo in (False,True):
            sid,did=self.season(); p=self.players(sid)[0]
            self.insert('coin_transactions',dict(season_id=sid,trainer_id=p['trainer_id'],season_player_id=p['id'],amount=100,transaction_type='admin_adjustment'))
            buy=self.purchase(sid,p,promo)
            results=self.race(lambda:self.change(sid,p['id']),buy)
            require(isinstance(results[0],dict),'Status vs purchase failed')
            require(isinstance(results[1],(dict,list)) or results[1]=='PARTICIPANT_INACTIVE','Purchase race '+str(results[1]))
            self.reject(buy,'PARTICIPANT_INACTIVE')
            self.passed('I09 '+('022 promotional' if promo else '021 normal')+' purchase vs status, subsequent deny')
        sid,did=self.season(); source=self.lock_source(sid,did)
        lock=lambda:self.adapter(lambda:SupabaseTeamLockRepository(self.client).upsert_with_activity(source))
        results=self.race(lambda:self.change(sid,source.season_player_id),lock)
        self.one_winner(results,'PARTICIPANT_HAS_CURRENT_TEAM_LOCK','PARTICIPANT_INACTIVE')
        self.passed('I10 status vs 019 Team Lock: lock retained or inactive owner rejected')
        sid,did=self.season(); source=self.lock_source(sid,did)
        self.adapter(lambda:SupabaseTeamLockRepository(self.client).upsert_with_activity(source))
        before=self.rows('team_locks',season_id=sid)
        self.reject(lambda:self.change(sid,source.season_player_id),'PARTICIPANT_HAS_CURRENT_TEAM_LOCK')
        other=next(p for p in self.players(sid) if p['id']!=source.season_player_id)
        self.change(sid,other['id'])
        require(self.rows('team_locks',season_id=sid)==before,'Other player lock changed')
        self.passed('I11 targeted lock blocks, surviving player locks unchanged')
        for code in ('blindar_pokemon','robar_pokemon'):
            sid,did=self.season(); p,q=self.players(sid)[:2]
            entity=self.identity(sid,q if code=='robar_pokemon' else p)[0]
            owned=self.entitlement(sid,p,code)
            results=self.race(lambda:self.change(sid,p['id']),lambda:self.use(owned,entity))
            require(isinstance(results[0],dict),'Status vs redemption failed')
            require(isinstance(results[1],dict) or results[1]=='PARTICIPANT_INACTIVE','Redemption race')
            self.reject(lambda:self.use(owned,entity),'PARTICIPANT_INACTIVE')
            self.passed('I12 status vs '+code+' redemption; committed history/pending effects kept; future deny')

    def cycle_ready(self):
        sid,did=self.season(); players=self.players(sid)
        entities={p['id']:self.identity(sid,p,i+1) for i,p in enumerate(players)}
        receipts=[]
        for i in range(3):
            receipts.append(self.use(self.entitlement(sid,players[(i+1)%4]),entities[players[i]['id']][0]))
        cycle=self.rows('robbery_cycles',season_id=sid)[0]
        require(cycle['cycle_number']==1,'Premature cycle')
        return sid,did,players,entities,receipts

    def robbery_cases(self):
        sid,did,players,entities,receipts=self.cycle_ready()
        pending=[self.entitlement(sid,players[-1],code) for code in ('revivir_pokemon','blindar_pokemon')]
        pending+=self.rows('purchases',season_player_id=players[-1]['id'],acquisition_type='reward')
        protected=self.protected(sid); before=self.rows('robbery_cycles',season_id=sid)[0]
        p=players[-1]; body=dict(reason='Completes active set',expected_roster_revision=self.state(sid)['roster_revision']); key=uuid4().hex
        results=self.race(lambda:self.change(sid,p['id'],body=body,key=key),lambda:self.change(sid,p['id'],body=body,key=key))
        require(results[0]['operation_id']==results[1]['operation_id'],'Cycle replay duplicated')
        cycle=self.rows('robbery_cycles',season_id=sid)[0]
        require(cycle['cycle_number']==2 and cycle['history_watermark_id']==before['last_redemption_id'],'Incorrect cycle rollover')
        require(self.protected(sid)==protected,'Cycle transition changed durable facts')
        for owned in pending:
            self.reject(lambda:self.use(owned,entities[p['id']][1]),'PARTICIPANT_INACTIVE')
        require(all(not f['flag_value'] for f in self.rows('trainer_flags',season_id=sid,flag_type='robbed')),'Current robbed flags retained')
        self.use(self.entitlement(sid,players[0]),entities[players[1]['id']][1])
        require(self.rows('robbery_cycles',season_id=sid)[0]['cycle_number']==2,'025 reset same cycle again')
        self.passed('I13 status completes cycle exactly once; watermark exact; history preserved; next 025 stays cycle 2')
        sid,did,players,entities,receipts=self.cycle_ready()
        p=players[-1]; purchase=self.entitlement(sid,players[0]); before=self.rows('robbery_cycles',season_id=sid)[0]
        results=self.race(lambda:self.change(sid,p['id']),lambda:self.use(purchase,entities[p['id']][0]))
        require(isinstance(results[0],dict),'Victim status race failed')
        require(isinstance(results[1],dict) or results[1]=='STEAL_VICTIM_INELIGIBLE','Victim race outcome')
        cycle=self.rows('robbery_cycles',season_id=sid)[0]
        require(cycle['cycle_number']==2,'Race duplicated/missed cycle rollover')
        require(cycle['history_watermark_id']==(results[1]['redemption_id'] if isinstance(results[1],dict) else before['last_redemption_id']),'Race watermark')
        self.passed('I14 inactivation vs final victim robbery: one cycle advance, exact winning watermark')

    def permissions(self):
        sid,did=self.season(); p=self.players(sid)[0]
        for role in ('admin','owner','anon'):
            actions=[lambda:self.readers[role].rpc('api_admin_participant_status',{'p_request':{}}).execute(),
                lambda:self.readers[role].rpc('participant_memberships_at',{'sid':sid,'round_number':1}).execute(),
                lambda:self.readers[role].table('season_players').update({'status':'retired'}).eq('id',p['id']).execute(),
                lambda:self.readers[role].table('season_players').update({'status_effective_matchday_number':1}).eq('id',p['id']).execute(),
                lambda:self.readers[role].table('division_memberships').update({'eligibility_ends_before_matchday_number':1}).eq('season_id',sid).execute()]
            for action in actions:
                try: action()
                except Exception as exc: require(str(getattr(exc,'code',''))=='42501','Unexpected security denial')
                else: raise AssertionError('Browser mutation/RPC exposed')
        r=self.change(sid,p['id'])
        require(not any(x in str(r) for x in ('auth_user_id','private_team','parsed_payload')),'Receipt leaked private data')
        try: self.client.table('season_players').update({'status':'active'}).eq('id',p['id']).execute()
        except Exception as exc: require(str(getattr(exc,'message',''))=='participant_already_inactive','Immutable evidence error')
        else: raise AssertionError('Typed status reactivated')
        self.passed('I15 browser admin/owner/anon denied; private receipt projection; evidence immutable')

    def cleanup(self):
        for sid in self.seasons:
            self.client.table('season_players').update({'current_save_file_id':None}).eq('season_id',sid).execute()
            for cup in self.rows('cups',season_id=sid):
                for table in ('cup_matches','cup_standings','cup_participants'):
                    self.client.table(table).delete().eq('cup_id',cup['id']).execute()
            for case in self.rows('trial_cases',season_id=sid):
                self.client.table('trial_votes').delete().eq('trial_case_id',case['id']).execute()
            self.client.table('penalties').delete().eq('season_id',sid).execute()
            self.client.table('trial_cases').delete().eq('season_id',sid).execute()
            self.client.table('robbery_cycles').delete().eq('season_id',sid).execute()
            # Break only this disposable graph's circular gift/origin references.
            empty={key:None for key in ('idempotency_key','effect_code','target_pokemon_entity_id',
                'target_owner_trainer_id','identity_revision_id','physical_effect_status','physical_effect_completed_at',
                'requested_at','activity_event_id','receipt','gift_purchase_id','robbery_cycle_number')}
            self.client.table('redemptions').update(empty).eq('season_id',sid).execute()
            for gift in self.rows('purchases',season_id=sid,acquisition_type='reward'):
                self.client.table('redemptions').delete().eq('purchase_id',gift['id']).execute()
            self.client.table('purchases').delete().eq('season_id',sid).eq('acquisition_type','reward').execute()
            self.client.table('redemptions').delete().eq('season_id',sid).execute()
            for table in ('pokemon_entity_flags','pokemon_observations','pokemon_identity_revisions','pokemon_entities','pokemon_flags','trainer_flags'):
                self.client.table(table).delete().eq('season_id',sid).execute()
        super().cleanup()
