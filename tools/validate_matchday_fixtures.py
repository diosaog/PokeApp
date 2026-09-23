"""Shared real-database Phase 8H fixtures. Only task-prefixed synthetic seasons."""
from dataclasses import asdict
from uuid import uuid4

from app.domain.normal_purchases import NormalPurchaseRequest
from app.domain.team_locks import TeamLockMutation
from app.repositories.errors import PersistenceError
from app.repositories.supabase.matchdays import SupabaseMatchdayRepository
from app.repositories.supabase.normal_purchases import SupabaseNormalPurchaseRepository
from app.repositories.supabase.team_locks import SupabaseTeamLockRepository
from tools.validate_season_admin_fixtures import SeasonAdminFixtures, require


class MatchdayFixtures(SeasonAdminFixtures):
    def __init__(self, client, readers, auth_ids, run_id=None):
        super().__init__(client, readers, auth_ids, run_id or 'phase8h_validation_'+uuid4().hex)
        self.matchdays = SupabaseMatchdayRepository(client)

    def md(self, op, sid, did, body=None, key=None, actor=None):
        request = dict(actor_trainer_id=actor or self.admin['id'],season_id=sid,resource_id=did)
        if body is not None: request['body']=body
        if op!='state': request['idempotency_key']=key or uuid4().hex
        return self.matchdays.execute(op,request)

    def ds(self,sid,did): return self.md('state',sid,did)

    def season(self,total=2):
        # Test isolation only, never a product finish endpoint or a real season.
        for sid in self.seasons:
            self.client.table('seasons').update({'status':'draft'}).eq('id',sid).execute()
        sid=self.roster(); cfg=self.config(sid)
        cfg.update(total_matchdays=total,coin_rewards={'1':10,'2':7,'3':4,'4':0})
        c=self.call('create_config',sid,cfg)
        self.call('initial_divisions',sid,self.divisions_body(sid,c['resource_id']))
        self.call('prepare',sid,{'expected_setup_revision':self.state(sid)['setup_revision']})
        self.call('activate',sid,{'expected_setup_revision':self.state(sid)['setup_revision']})
        return sid,self.state(sid)['current_matchday_id']

    def open(self,sid,did,**kw):
        return self.md('open',sid,did,{'expected_revision':self.ds(sid,did)['revision']},**kw)

    def results(self,sid,did,reverse=False,**kw):
        state=self.ds(sid,did)
        body={'expected_results_revision':state['results_revision'],'results':[
            {'match_id':m['id'],'winner_season_player_id':m['player_b_id' if reverse else 'player_a_id']}
            for m in state['matches']]}
        return self.md('results',sid,did,body,**kw)

    def close(self,sid,did,**kw):
        return self.md('close',sid,did,{'expected_results_revision':self.ds(sid,did)['results_revision']},**kw)

    def correction(self,sid,did):
        state=self.ds(sid,did)
        return dict(expected_snapshot_revision=state['snapshot_revision'],reason='Synthetic corrected winners',results=[
            dict(match_id=m['id'],winner_season_player_id=m['player_b_id'] if m['winner_id']==m['player_a_id'] else m['player_a_id'])
            for m in state['matches']])

    def prepared_close(self,total=2):
        sid,did=self.season(total)
        self.open(sid,did); self.results(sid,did)
        return sid,did

    def run(self):
        self.setup()
        sid,did=self.season()
        self.reject(lambda:self.open(sid,did,actor=self.owner['id']),'ADMIN_REQUIRED')
        state=self.ds(sid,did); body={'expected_revision':state['revision']}
        race=self.race(lambda:self.md('open',sid,did,body),lambda:self.md('open',sid,did,body,actor=self.admin2['id']))
        self.one_winner(race,'MATCHDAY_NOT_SCHEDULED','STALE_REVISION')
        require(not self.rows('coin_transactions',season_id=sid),'Open awarded coins')
        self.passed('H01 admin not participant; non-admin denied; concurrent open single transition')
        state=self.ds(sid,did)
        self.md('cancel',sid,did,{'expected_revision':state['revision'],'reason':'No results'})
        require(self.ds(sid,did)['state']=='scheduled' and len(self.ds(sid,did)['matches'])==2,'Cancel destroyed canonical pairs')
        self.open(sid,did)
        self.passed('H02 cancel same day scheduled, pointer/pairs retained; reopen revision advances')
        self.reject(lambda:self.close(sid,did),'RESULTS_INCOMPLETE')
        state=self.ds(sid,did); match=state['matches'][0]
        invalid={'expected_results_revision':state['results_revision'],'results':[dict(match_id=match['id'],winner_season_player_id=str(uuid4()))]}
        self.reject(lambda:self.md('results',sid,did,invalid),'INVALID_RESULTS')
        self.results(sid,did)
        state=self.ds(sid,did)
        self.reject(lambda:self.md('cancel',sid,did,{'expected_revision':state['revision'],'reason':'Unsafe'}),'DEPENDENT_DATA_EXISTS')
        changes={'expected_results_revision':state['results_revision'],'results':[dict(match_id=m['id'],winner_season_player_id=None) for m in state['matches']]}
        self.md('results',sid,did,changes)
        require(all(m['winner_id'] is None for m in self.ds(sid,did)['matches']),'Remove winners')
        self.results(sid,did)
        state=self.ds(sid,did); body={'expected_results_revision':state['results_revision'],'results':[dict(match_id=match['id'],winner_season_player_id=match['player_a_id'])]}
        race=self.race(lambda:self.md('results',sid,did,body),lambda:self.md('results',sid,did,body,actor=self.admin2['id']))
        self.one_winner(race,'STALE_REVISION')
        self.passed('H03 batch edits/removals, invalid winner, incomplete close and results CAS')
        body={'expected_results_revision':self.ds(sid,did)['results_revision']}; key=uuid4().hex
        race=self.race(lambda:self.md('close',sid,did,body,key=key),lambda:self.md('close',sid,did,body,key=key))
        require(race[0]['operation_id']==race[1]['operation_id'],'Close replay duplicated')
        nextid=self.ds(sid,did)['current_matchday_id']
        require(nextid!=did and self.ds(sid,nextid)['state']=='scheduled','Next round not prepared')
        require(len(self.rows('matchdays',season_id=sid))==2 and len(self.rows('matches',season_id=sid))==4,'Extra/missing rounds/pairs')
        require(len(self.rows('coin_transactions',season_id=sid))==3,'Zero ledger or duplicated reward')
        require(sum(x['amount'] for x in self.rows('coin_transactions',season_id=sid))==21,'Wrong rewards')
        require(len(self.rows('matchday_movements',season_id=sid))==4,'Movement exactly once')
        gifts=self.rows('purchases',origin_matchday_id=did)
        require(len(gifts)==1 and gifts[0]['unit_price']==0 and gifts[0]['status']=='pending','Free reward')
        require(self.rows('shop_items',id=gifts[0]['shop_item_id'])[0]['code']=='robar_pokemon','Wrong canonical reward')
        promos=self.rows('shop_promotions',season_id=sid)
        require(promos and all(p['status']=='pending' and p['matchday_id']==nextid and p['stock_used']==0 for p in promos),'Next promotions')
        self.passed('H04 close replay atomic snapshot/rewards/free Robar/movements/memberships/next pairs/pointer/promotions')
        original=self.rows('matchday_snapshot_revisions',matchday_id=did)[0]
        for table in ('coin_transactions','purchases','matchday_movements'):
            duplicate=dict(self.rows(table,season_id=sid)[0],id=str(uuid4()))
            if table=='purchases': duplicate.pop('total_price')
            try: self.client.table(table).insert(duplicate).execute()
            except Exception as exc: require(str(getattr(exc,'code',''))=='23505','Missing source dedupe '+table)
            else: raise AssertionError('Duplicated authoritative source '+table)
        try: self.client.table('matchday_snapshot_revisions').update({'reason':'rewrite'}).eq('id',original['id']).execute()
        except Exception as exc: require(str(getattr(exc,'code',''))=='PT409','History immutable error')
        else: raise AssertionError('Historical revision was rewritten')
        self.passed('H18 database source uniqueness and immutable snapshot history')
        corrected=self.correction(sid,did); key=uuid4().hex
        corrected_result=self.md('correct',sid,did,corrected,key=key)
        require(self.md('correct',sid,did,corrected,key=key)['operation_id']==corrected_result['operation_id'],'Correction replay')
        revisions=self.rows('matchday_snapshot_revisions',matchday_id=did)
        require(len(revisions)==2 and next(r for r in revisions if r['revision']==1)==original,'Lost snapshot history')
        require(self.rows('matchday_snapshots',matchday_id=did)[0]['revision']==2,'Missing current snapshot revision')
        ledger=self.rows('coin_transactions',season_id=sid)
        require(len(ledger)==7 and sum(r['amount'] for r in ledger)==21,'Compensation not exact/deduped')
        gifts=self.rows('purchases',origin_matchday_id=did)
        require(len(gifts)==2 and sorted(g['status'] for g in gifts)==['cancelled','pending'],'Reward compensation')
        require(len(self.rows('matchdays',season_id=sid))==2 and len(self.rows('matches',season_id=sid))==4,'Correction duplicated next')
        require(self.rows('shop_promotions',season_id=sid)==promos,'Correction rerolled shop promotions')
        self.passed('H05 immutable correction revision; append-only coin compensation; cancel/reissue pending reward; replay')
        self.open(sid,nextid)
        self.reject(lambda:self.md('correct',sid,did,self.correction(sid,did)),'CORRECTION_WINDOW_CLOSED')
        self.results(sid,nextid); self.close(sid,nextid)
        require(self.ds(sid,nextid)['current_matchday_id']==nextid and len(self.rows('matchdays',season_id=sid))==2,'Fictional final next day')
        require(self.rows('seasons',id=sid)[0]['status']=='active','Final close finished season')
        require(not self.rows('matchday_movements',matchday_id=nextid),'Final movements')
        require(len(self.rows('purchases',origin_matchday_id=nextid))==1,'Final last-B gift missing')
        require(all(p['status']=='ended' for p in self.rows('shop_promotions',season_id=sid)),'Final promos not expired')
        self.md('correct',sid,nextid,self.correction(sid,nextid))
        require(self.ds(sid,nextid)['current_matchday_id']==nextid,'Final correction pointer')
        self.passed('H06 later open blocks correction; final close/correction leaves ACTIVE with final pointer; no movement/next/finish')
        self.races()
        self.cross_flow_races()
        self.unsafe_corrections()
        self.permissions_8h(sid)

    def races(self):
        sid,did=self.prepared_close(); body={'expected_results_revision':self.ds(sid,did)['results_revision']}
        result=self.race(lambda:self.md('close',sid,did,body),lambda:self.md('close',sid,did,body,actor=self.admin2['id']))
        self.one_winner(result,'MATCHDAY_NOT_CURRENT','ALREADY_CLOSED','STALE_REVISION','STALE_INPUTS')
        self.passed('H07 different close keys/admins: rewards/gift/movement/next/pointer exactly once')
        sid,did=self.prepared_close(); state=self.ds(sid,did)
        result=self.race(lambda:self.md('close',sid,did,{'expected_results_revision':state['results_revision']}),
            lambda:self.md('results',sid,did,{'expected_results_revision':state['results_revision'],
                'results':[dict(match_id=m['id'],winner_season_player_id=m['player_b_id']) for m in state['matches']]}))
        self.one_winner(result,'MATCHDAY_NOT_CURRENT','ALREADY_CLOSED','STALE_REVISION','STALE_INPUTS')
        if self.ds(sid,did)['state']=='open': self.close(sid,did)
        self.passed('H08 result edit vs close serialized, stale loser has no effects')
        corrected=self.correction(sid,did)
        result=self.race(lambda:self.md('correct',sid,did,corrected),lambda:self.md('correct',sid,did,corrected,actor=self.admin2['id']))
        self.one_winner(result,'STALE_REVISION','STALE_INPUTS')
        self.passed('H09 corrections same base CAS, one new revision and compensations')
        nextid=self.ds(sid,did)['current_matchday_id']; corrected=self.correction(sid,did)
        result=self.race(lambda:self.md('correct',sid,did,corrected),lambda:self.open(sid,nextid,actor=self.admin2['id']))
        require(any(isinstance(r,dict) for r in result),'No race progress')
        require(all(isinstance(r,dict) or r in ('CORRECTION_WINDOW_CLOSED','STALE_INPUTS') for r in result),'Unsafe correction/open outcome')
        corrected=self.correction(sid,did)
        result=self.race(lambda:self.md('correct',sid,did,corrected),lambda:self.results(sid,nextid))
        require(result[0]=='CORRECTION_WINDOW_CLOSED' and isinstance(result[1],dict),'Correction crossed next result entry')
        self.reject(lambda:self.md('correct',sid,did,self.correction(sid,did)),'CORRECTION_WINDOW_CLOSED')
        self.passed('H10 correction vs next open/results: safe ordered correction or fail closed')
        sid,did=self.prepared_close(); body={'expected_results_revision':self.ds(sid,did)['results_revision']}
        result=self.race(lambda:self.md('close',sid,did,body),lambda:self.add(sid,self.trainers[6]['id']))
        self.one_winner(result,'SEASON_NOT_DRAFT')
        self.passed('H11 close vs draft roster mutation preserves competitive roster')

    def unsafe_corrections(self):
        sid,did=self.prepared_close(); self.close(sid,did)
        gift=self.rows('purchases',origin_matchday_id=did)[0]
        self.client.table('purchases').update({'status':'used'}).eq('id',gift['id']).execute()
        self.reject(lambda:self.md('correct',sid,did,self.correction(sid,did)),'CORRECTION_WINDOW_CLOSED')
        self.passed('H12 used free reward blocks correction')
        sid,did=self.prepared_close(); self.close(sid,did)
        p=self.rows('season_players',season_id=sid)[0]
        self.insert('coin_transactions',dict(season_id=sid,trainer_id=p['trainer_id'],season_player_id=p['id'],amount=-1,transaction_type='purchase'))
        self.reject(lambda:self.md('correct',sid,did,self.correction(sid,did)),'CORRECTION_WINDOW_CLOSED')
        self.passed('H13 changed external economy blocks correction, timestamps not trusted')
        sid,did=self.prepared_close()
        self.insert('cups',dict(season_id=sid,name=self.run_id+'_cup',format='manual'))
        self.close(sid,did)
        self.reject(lambda:self.md('correct',sid,did,self.correction(sid,did)),'CORRECTION_WINDOW_CLOSED')
        self.passed('H19 pre-existing season cup blocks correction without a cascade')

    def lock_source(self,sid,did):
        player=self.rows('season_players',season_id=sid)[0]
        sf=self.insert('save_files',dict(season_id=sid,trainer_id=player['trainer_id'],storage_key=self.run_id+'/'+uuid4().hex+'.sav',
            original_filename='synthetic.sav',sha256=uuid4().hex*2,parser_status='parsed',parser_version='phase8h'))
        party=[{'species':'Pikachu'} for _ in range(6)]
        parsed=self.insert('parsed_saves',dict(save_file_id=sf['id'],parser_version='phase8h',payload={'party':party}))
        return TeamLockMutation(season_id=sid,matchday_id=did,trainer_id=player['trainer_id'],season_player_id=player['id'],
            save_file_id=sf['id'],save_sha256=sf['sha256'],parsed_save_id=parsed['id'],parsed_payload=parsed['payload'],
            public_team_snapshot=party,private_team_snapshot=party)

    def cross_flow_races(self):
        def call_adapter(action):
            try: return asdict(action())
            except PersistenceError as exc:
                code=getattr(exc,'code',None) or getattr(exc.__cause__,'message',None)
                if not code: raise
                return str(code).upper()
        sid,did=self.prepared_close()
        player=self.rows('season_players',season_id=sid)[0]
        self.insert('coin_transactions',dict(season_id=sid,trainer_id=player['trainer_id'],season_player_id=player['id'],amount=100,transaction_type='admin_adjustment'))
        item=self.rows('shop_items',category='bayas')[0]
        purchase=NormalPurchaseRequest(sid,player['trainer_id'],item['id'],uuid4().hex)
        buy=lambda:call_adapter(lambda:SupabaseNormalPurchaseRepository(self.client).create_normal_purchase(purchase))
        result=self.race(lambda:self.close(sid,did),buy)
        require(isinstance(result[1],dict),'Concurrent purchase failed')
        require(isinstance(result[0],dict) or result[0]=='STALE_INPUTS','Unexpected close/purchase outcome')
        if self.ds(sid,did)['state']=='open': self.close(sid,did)
        require(result[1]['matchday_id'] in (did,self.ds(sid,did)['current_matchday_id']),'Purchase has fictional pointer')
        require(len(self.rows('purchases',idempotency_key=purchase.idempotency_key))==1,'Duplicated purchase')
        self.passed('H15 real 021 purchase vs close: stable wallet/pointer or explicit stale-input rejection')
        sid,did=self.prepared_close(); mutation=self.lock_source(sid,did)
        lock=lambda:call_adapter(lambda:SupabaseTeamLockRepository(self.client).upsert_with_activity(mutation))
        result=self.race(lambda:self.close(sid,did),lock)
        require(isinstance(result[0],dict) or result[0]=='STALE_INPUTS','Close/lock outcome')
        require(isinstance(result[1],dict) or result[1]=='MATCHDAY_NOT_LOCKABLE','Team Lock/close outcome')
        if self.ds(sid,did)['state']=='open': self.close(sid,did)
        require(len(self.rows('team_locks',season_id=sid))<=1,'Duplicate Team Lock')
        self.passed('H16 real 019 Team Lock vs close: no deadlock, no lost lock, closed round immutable')
        nextid=self.ds(sid,did)['current_matchday_id']; future_lock=self.lock_source(sid,nextid)
        SupabaseTeamLockRepository(self.client).upsert_with_activity(future_lock)
        self.reject(lambda:self.md('correct',sid,did,self.correction(sid,did)),'CORRECTION_WINDOW_CLOSED')
        self.open(sid,nextid)
        before=self.rows('team_locks',matchday_id=nextid)
        self.md('cancel',sid,nextid,dict(expected_revision=self.ds(sid,nextid)['revision'],reason='Preserve lock'))
        require(self.rows('team_locks',matchday_id=nextid)==before,'Cancel destroyed lock')
        self.passed('H17 downstream lock blocks correction; cancel preserves its exact snapshot')

    def permissions_8h(self,sid):
        for role in ('admin','owner','anon'):
            for rpc in ('api_admin_matchday','api_admin_matchday_context'):
                try: self.readers[role].rpc(rpc,{'p_request':{}}).execute()
                except Exception as exc: require(str(getattr(exc,'code',''))=='42501','RPC denial code')
                else: raise AssertionError('Privileged RPC exposed')
            for table in ('matchdays','matches','matchday_snapshots','matchday_movements','coin_transactions','matchday_snapshot_revisions'):
                for method in ('insert','update','delete'):
                    q=self.readers[role].table(table)
                    q=q.delete() if method=='delete' else getattr(q,method)({'season_id':sid})
                    if method!='insert': q=q.eq('season_id',sid)
                    try: q.execute()
                    except Exception as exc: require(str(getattr(exc,'code',''))=='42501','Table denial '+table)
                    else: raise AssertionError('Browser direct write exposed')
        self.passed('H14 admin/owner/anon browser writes and privileged RPCs denied')

    def cleanup(self):
        for sid in self.seasons:
            for table in ('cups','team_locks','coin_transactions','redemptions','purchases','shop_promotions',
                          'matchday_movements','matchday_snapshots','matchday_snapshot_revisions'):
                self.client.table(table).delete().eq('season_id',sid).execute()
            for save in self.rows('save_files',season_id=sid):
                self.client.table('parsed_saves').delete().eq('save_file_id',save['id']).execute()
            self.client.table('save_files').delete().eq('season_id',sid).execute()
        super().cleanup()
