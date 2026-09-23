"""Shared 8J real-DB fixtures: explicit lifecycle, frozen safe history and races."""
from dataclasses import replace
from uuid import uuid4

from app.api.season_lifecycle_models import SeasonLifecycleReceipt
from app.domain.normal_purchases import NormalPurchaseRequest
from app.repositories.supabase.normal_purchases import SupabaseNormalPurchaseRepository
from app.repositories.supabase.season_lifecycle import SupabaseSeasonLifecycleRepository
from app.repositories.supabase.team_locks import SupabaseTeamLockRepository
from tools.validate_participant_status_fixtures import ParticipantStatusFixtures, require


class SeasonLifecycleFixtures(ParticipantStatusFixtures):
    def __init__(self, client, readers, auth_ids, run_id=None):
        super().__init__(client, readers, auth_ids, run_id or 'phase8j_validation_'+uuid4().hex)
        self.lifecycle = SupabaseSeasonLifecycleRepository(client)

    def life(self, op, sid, body=None, key=None, actor=None):
        if body is None:
            body=dict(expected_revision=self.state(sid)['setup_revision'])
            if op=='archive': body['label']=None
            if op=='discard': body.update(reason='Unused synthetic draft',confirmation='DISCARD')
        result=self.lifecycle.execute(op,self.request(op,sid,body,key=key,actor=actor))
        SeasonLifecycleReceipt.model_validate(result)
        return result

    def complete(self,total=1):
        sid,did=self.season(total)
        for _ in range(total):
            self.open(sid,did); self.results(sid,did); self.close(sid,did)
            did=self.state(sid)['current_matchday_id']
        return sid,did

    def preserved(self,sid):
        result=self.protected(sid)
        for t in ('season_players','season_player_stats','season_config_versions','divisions','division_memberships','matchdays','matches'):
            result[t]=sorted(self.rows(t,season_id=sid),key=lambda r:str(r.get('id',r.get('season_player_id'))))
        return result

    def run(self):
        self.setup()
        sid=self.draft()
        self.reject(lambda:self.life('finish',sid),'SEASON_NOT_ACTIVE')
        self.reject(lambda:self.life('archive',sid),'SEASON_NOT_FINISHED')
        sid,did=self.season()
        self.reject(lambda:self.life('finish',sid),'COMPETITION_INCOMPLETE')
        self.open(sid,did)
        self.reject(lambda:self.life('finish',sid),'COMPETITION_INCOMPLETE')
        self.results(sid,did); self.close(sid,did)
        self.reject(lambda:self.life('finish',sid),'COMPETITION_INCOMPLETE')
        did=self.state(sid)['current_matchday_id']; self.open(sid,did); self.results(sid,did); self.close(sid,did)
        require(self.rows('seasons',id=sid)[0]['status']=='active','Auto finish at final close')
        self.md('correct',sid,did,self.correction(sid,did))
        self.reject(lambda:self.life('finish',sid,actor=self.owner['id']),'ADMIN_REQUIRED')
        self.reject(lambda:self.life('finish',sid,{'expected_revision':0}),'STALE_REVISION')
        before=self.preserved(sid); body={'expected_revision':self.state(sid)['setup_revision']}; key=uuid4().hex
        race=self.race(lambda:self.life('finish',sid,body,key),lambda:self.life('finish',sid,body,key))
        require(race[0]['operation_id']==race[1]['operation_id'],'Finish replay duplicated')
        require(self.preserved(sid)==before,'Finish rewrote history/economy/saves')
        require(self.rows('seasons',id=sid)[0]['current_matchday_id']==did,'Finish lost pointer')
        require(not self.rows('hall_of_fame_entries',season_id=sid) and not self.rows('season_archive_snapshots',season_id=sid),'Finish auto archive')
        require(self.life('finish',sid,body,key)['replayed'],'Finish retry failed')
        self.reject(lambda:self.life('finish',sid),'SEASON_NOT_ACTIVE')
        self.passed('J01/J02 final completion, manual review, no bonus/archive, pointer and all relational facts retained; finish replay/CAS')
        self.finished_denials(sid,did)
        existing_seasons={s['id'] for s in self.rows('seasons')}
        body={'expected_revision':self.state(sid)['setup_revision'],'label':'Frozen season'}; key=uuid4().hex
        race=self.race(lambda:self.life('archive',sid,body,key),lambda:self.life('archive',sid,body,key))
        require(race[0]['operation_id']==race[1]['operation_id'],'Archive retry duplicate')
        archive=self.rows('season_archive_snapshots',season_id=sid); hall=self.rows('hall_of_fame_entries',season_id=sid)
        require(len(archive)==len(hall)==1,'Archive/Hall not exact once')
        require(hall[0]['team_snapshot']==[] and hall[0]['source_team_lock_id'] is None,'Missing team fabricated')
        standings=self.rows('matchday_snapshots',matchday_id=did)[0]['snapshot']['standings']
        first=min(standings,key=lambda x:x['position'])
        require(hall[0]['champion_trainer_id']==self.rows('season_players',id=first['trainer_id'])[0]['trainer_id'],'Wrong champion')
        require(hall[0]['archive_snapshot_id']==archive[0]['id'] and len(archive[0]['checksum'])==64,'Missing provenance')
        require(self.preserved(sid)==before,'Archive changed relational history')
        require({s['id'] for s in self.rows('seasons')}==existing_seasons,'Auto-created season')
        self.reject(lambda:self.life('archive',sid,dict(body,label='Different'),key),'IDEMPOTENCY_CONFLICT')
        self.reject(lambda:self.life('archive',sid),'SEASON_NOT_FINISHED')
        require(self.life('archive',sid,body,key)['archive_id']==archive[0]['id'],'Regenerated archive')
        for table in ('season_archive_snapshots','hall_of_fame_entries'):
            try: self.client.table(table).update({'created_at':'2026-01-01T00:00:00Z'}).eq('season_id',sid).execute()
            except Exception as exc: require(getattr(exc,'message',None)=='historical_artifact_immutable','Wrong immutable error')
            else: raise AssertionError('History mutable '+table)
        self.passed('J03/J04 archive/Hall atomic exact-once, frozen source, absent team allowed, immutable retry and no next season')
        self.permissions(sid)
        self.sources()
        self.discards()
        self.lifecycle_races()
        self.redemptions_preserved()

    def finished_denials(self,sid,did):
        for op,body in (('open',{'expected_revision':0}),('results',{'expected_results_revision':0,'results':[]}),
            ('close',{'expected_results_revision':0}),('correct',self.correction(sid,did))):
            self.reject(lambda:self.md(op,sid,did,body),'SEASON_NOT_ACTIVE')
        self.reject(lambda:self.change(sid,self.players(sid)[0]['id']),'SEASON_NOT_ACTIVE')
        self.reject(lambda:self.call('rename',sid,{'name':'Changed','expected_revision':0}),'SEASON_NOT_DRAFT')
        self.reject(lambda:self.call('create_config',sid,self.config(sid)),'CONFIG_WINDOW_CLOSED')
        self.reject(lambda:self.call('initial_divisions',sid,self.divisions_body(sid,self.rows('season_config_versions',season_id=sid)[0]['id'])),'SEASON_NOT_DRAFT')
        self.passed('J05 finished competitive/setup/config/status mutations rejected; no reopen')

    def sources(self):
        for fallback in (False,True):
            sid,did=self.season(2 if fallback else 1)
            self.open(sid,did)
            # Attach a real 019 lock for every possible champion before close.
            for player in self.players(sid):
                mutation=self.lock_source(sid,did)
                source=self.rows('save_files',id=mutation.save_file_id)[0]
                self.client.table('save_files').update({'trainer_id':player['trainer_id']}).eq('id',source['id']).execute()
                public=[dict(species='Pikachu',nickname='Historical',ivs={'secret':31},metadata={'secret':'PRIVATE'},
                    moves=[dict(name='Thunderbolt',private='PRIVATE')]) for _ in range(6)]
                mutation=replace(mutation,trainer_id=player['trainer_id'],season_player_id=player['id'],
                    public_team_snapshot=public,private_team_snapshot=[{'species':'Pikachu','nature':'PRIVATE'}]*6)
                self.adapter(lambda:SupabaseTeamLockRepository(self.client).upsert_with_activity(mutation))
            self.results(sid,did); self.close(sid,did)
            if fallback:
                did=self.state(sid)['current_matchday_id']; self.open(sid,did); self.results(sid,did); self.close(sid,did)
            self.life('finish',sid); self.life('archive',sid)
            hall=self.rows('hall_of_fame_entries',season_id=sid)[0]
            require(hall['source_team_lock_id'] is not None and len(hall['team_snapshot'])==6,'Historical team fallback failed')
            package=self.rows('season_archive_snapshots',season_id=sid)[0]
            require('PRIVATE' not in str(package) and 'ivs' not in str(package) and 'private_team' not in str(package),'Archive privacy')
            require('PRIVATE' not in str(self.readers['owner'].table('public_hall_of_fame').select('*').eq('season_id',sid).execute().data),'Public Hall privacy')
            self.passed('J06 champion '+('older historical lock fallback' if fallback else 'final lock')+'; nested public whitelist, no private source')
        sid,did=self.complete(); ledger=self.rows('coin_transactions',season_id=sid)[0]
        self.client.table('coin_transactions').update({'amount':ledger['amount']+1}).eq('id',ledger['id']).execute()
        self.reject(lambda:self.life('finish',sid),'HISTORICAL_SOURCE_INVALID')
        self.client.table('coin_transactions').update({'amount':ledger['amount']}).eq('id',ledger['id']).execute()
        match=self.rows('matches',matchday_id=did)[0]
        changed=match['player_b_id'] if match['winner_id']==match['player_a_id'] else match['player_a_id']
        self.client.table('matches').update({'winner_id':changed}).eq('id',match['id']).execute()
        self.reject(lambda:self.life('finish',sid),'HISTORICAL_SOURCE_INVALID')
        self.client.table('matches').update({'winner_id':match['winner_id']}).eq('id',match['id']).execute()
        self.client.table('matchday_snapshots').delete().eq('matchday_id',did).execute()
        self.reject(lambda:self.life('finish',sid),'HISTORICAL_SOURCE_INVALID')
        self.passed('J07 inconsistent rewards/results and missing authoritative snapshot fail closed')
        sid,did=self.complete()
        cfg=self.config(sid); cfg.update(effective_from_matchday=2,total_matchdays=2)
        self.call('create_config',sid,cfg)
        self.reject(lambda:self.life('finish',sid),'COMPETITION_INCOMPLETE')
        self.passed('J18 future committed configuration cannot be silently skipped at finish')
        sid,did=self.season(1)
        for player in self.players(sid): self.change(sid,player['id'])
        self.open(sid,did); self.close(sid,did); self.life('finish',sid)
        self.reject(lambda:self.life('archive',sid),'HISTORICAL_SOURCE_INVALID')
        require(not self.rows('hall_of_fame_entries',season_id=sid),'Fabricated champion for empty competition')
        self.passed('J19 empty final competition can finish, cannot fabricate required League champion')

    def discards(self):
        sid=self.ready(); before=self.preserved(sid)
        body=dict(reason='Abandoned setup',confirmation='DISCARD',expected_revision=self.state(sid)['setup_revision']); key=uuid4().hex
        race=self.race(lambda:self.life('discard',sid,body,key),lambda:self.life('discard',sid,body,key))
        require(race[0]['operation_id']==race[1]['operation_id'],'Discard duplicated')
        require(self.preserved(sid)==before and self.rows('seasons',id=sid)[0]['status']=='discarded','Destructive discard')
        for view in ('public_seasons','public_season_players','public_season_player_stats','public_season_config_versions','public_divisions','public_division_memberships'):
            for role in ('owner','admin'):
                require(not self.readers[role].table(view).select('*').eq('id' if view=='public_seasons' else 'season_id',sid).execute().data,'Discarded public view '+view)
        for table in ('seasons','season_players','season_player_stats','season_config_versions','divisions','division_memberships'):
            require(not self.readers['owner'].table(table).select('*').eq('id' if table=='seasons' else 'season_id',sid).execute().data,'Direct discarded discovery '+table)
        require(self.state(sid)['season']['status']=='discarded','Admin audit lost')
        self.reject(lambda:self.life('discard',sid,dict(body,reason='changed'),key),'IDEMPOTENCY_CONFLICT')
        self.passed('J08 logical draft discard replay; roster/config retained; parent/child/direct visibility safe, admin audit retained')
        for dependency in ('matchday','ledger','save','cup'):
            sid=self.ready(prepare=dependency=='matchday')
            if dependency=='ledger':
                player=self.players(sid)[0]
                self.insert('coin_transactions',dict(season_id=sid,trainer_id=player['trainer_id'],season_player_id=player['id'],amount=1,transaction_type='admin_adjustment'))
            if dependency=='save': self.lock_source(sid,str(uuid4()))
            if dependency=='cup': self.insert('cups',dict(season_id=sid,name='Existing cup',format='manual'))
            self.reject(lambda:self.life('discard',sid),'DISCARD_NOT_ALLOWED')
        sid,did=self.complete()
        self.reject(lambda:self.life('discard',sid),'DISCARD_NOT_ALLOWED')
        self.life('finish',sid); self.reject(lambda:self.life('discard',sid),'DISCARD_NOT_ALLOWED')
        self.passed('J09 prepared/economic/save/Cup dependencies and active/finished discard rejected')

    def lifecycle_races(self):
        sid,did=self.complete(); body={'expected_revision':self.state(sid)['setup_revision']}
        self.one_winner(self.race(lambda:self.life('finish',sid,body),lambda:self.life('finish',sid,body,actor=self.admin2['id'])),'SEASON_NOT_ACTIVE','STALE_REVISION')
        body={'expected_revision':self.state(sid)['setup_revision'],'label':None}
        self.one_winner(self.race(lambda:self.life('archive',sid,body),lambda:self.life('archive',sid,body,actor=self.admin2['id'])),'SEASON_NOT_FINISHED','STALE_REVISION')
        require(len(self.rows('hall_of_fame_entries',season_id=sid))==1,'Two Hall creators won')
        self.passed('J10 distinct finish/archive keys and Hall creators: single transition/event/artifact')
        sid,did=self.complete(); body={'expected_revision':self.state(sid)['setup_revision']}; correction=self.correction(sid,did)
        outcome=self.race(lambda:self.life('finish',sid,body),lambda:self.md('correct',sid,did,correction))
        require(isinstance(outcome[0],dict) and (isinstance(outcome[1],dict) or outcome[1]=='SEASON_NOT_ACTIVE'),'Finish/correction race')
        outcome=self.race(lambda:self.life('archive',sid),lambda:self.md('correct',sid,did,self.correction(sid,did)))
        require(isinstance(outcome[0],dict) and outcome[1]=='SEASON_NOT_ACTIVE','Late correction after archive')
        self.passed('J11 finish vs correction serialized; archive vs late correction denied')
        sid,did=self.complete(); player=self.players(sid)[0]; item=self.rows('shop_items',category='bayas')[0]
        self.insert('coin_transactions',dict(season_id=sid,trainer_id=player['trainer_id'],season_player_id=player['id'],amount=100,transaction_type='admin_adjustment'))
        buy=NormalPurchaseRequest(sid,player['trainer_id'],item['id'],uuid4().hex)
        outcome=self.race(lambda:self.life('finish',sid),lambda:self.adapter(lambda:SupabaseNormalPurchaseRepository(self.client).create_normal_purchase(buy)))
        require(isinstance(outcome[0],dict) and (isinstance(outcome[1],dict) or outcome[1]=='SEASON_NOT_ACTIVE'),'Finish vs purchase')
        self.passed('J12 finish vs 021 purchase serialized without refunds or new bonus')
        sid,did=self.complete(); mutation=self.lock_source(sid,did); player=self.players(sid)[0]
        outcome=self.race(lambda:self.life('finish',sid),lambda:self.adapter(lambda:SupabaseTeamLockRepository(self.client).upsert_with_activity(mutation)),lambda:self.change(sid,player['id']))
        require(isinstance(outcome[0],dict) and outcome[1] in ('SEASON_NOT_ACTIVE','MATCHDAY_NOT_LOCKABLE') and outcome[2] in ('SEASON_NOT_ACTIVE','MATCHDAY_NOT_SCHEDULED'),'Finish vs lock/status')
        self.passed('J13 finish vs 019 lock and 028 status: no late competitive writes')
        other=self.ready(prepare=True)
        outcome=self.race(lambda:self.life('archive',sid),lambda:self.call('activate',other,{'expected_setup_revision':self.state(other)['setup_revision']}),lambda:self.draft())
        require(isinstance(outcome[0],dict) and isinstance(outcome[1],dict) and isinstance(outcome[2],str),'Archive vs independent activation/create')
        require(len(self.rows('seasons',status='active'))==1,'Multiple active seasons')
        self.passed('J14 archive vs independent next activation/create, no implicit lifecycle coupling')
        sid=self.draft(); body=dict(expected_revision=0,reason='Unused',confirmation='DISCARD')
        outcome=self.race(lambda:self.life('discard',sid,body),lambda:self.call('rename',sid,{'expected_revision':0,'name':'Changed draft'}))
        self.one_winner(outcome,'STALE_REVISION','SEASON_NOT_DRAFT')
        self.passed('J15 discard vs draft setup CAS; only one mutation commits')

    def redemptions_preserved(self):
        sid,did=self.season(1); player=self.players(sid)[0]; entities=self.identity(sid,player)
        pending=self.entitlement(sid,player,'blindar_pokemon')
        victim=self.players(sid)[1]; targets=self.identity(sid,victim)
        robbery=self.entitlement(sid,player,'robar_pokemon')
        second=self.entitlement(sid,player,'blindar_pokemon')
        self.open(sid,did); self.results(sid,did); self.close(sid,did); self.life('finish',sid)
        receipt=self.use(pending,entities[0]); require(receipt['redemption_id'],'Finished redemption blocked')
        self.life('archive',sid)
        require(self.use(second,entities[1])['redemption_id'],'Archived redemption semantics changed')
        require(self.use(robbery,targets[0])['redemption_id'],'Archived robbery semantics changed')
        self.passed('J16 024 shield and 025 robbery remain allowed after finish/archive; no global lifecycle gate')

    def permissions(self,sid):
        for role in ('admin','owner','anon'):
            for rpc in ('api_admin_season_lifecycle','lifecycle_final_source','lifecycle_draft_safe'):
                params={'p_request':{}} if rpc=='api_admin_season_lifecycle' else {'sid':sid}
                try: self.readers[role].rpc(rpc,params).execute()
                except Exception as exc: require(str(getattr(exc,'code',''))=='42501','RPC denial '+rpc)
                else: raise AssertionError('Browser RPC exposed')
            for table in ('season_archive_snapshots','hall_of_fame_entries'):
                for method in ('insert','update','delete'):
                    q=self.readers[role].table(table)
                    q=q.delete() if method=='delete' else getattr(q,method)({'season_id':sid})
                    if method!='insert': q=q.eq('season_id',sid)
                    try: q.execute()
                    except Exception as exc: require(str(getattr(exc,'code',''))=='42501','Artifact write denial')
                    else: raise AssertionError('Browser historical mutation')
        self.passed('J17 RPC and direct archive/Hall INSERT/UPDATE/DELETE denied including browser admin')

    def cleanup(self):
        for sid in self.seasons:
            self.client.table('hall_of_fame_entries').delete().eq('season_id',sid).execute()
            self.client.table('season_archive_snapshots').delete().eq('season_id',sid).execute()
        super().cleanup()
