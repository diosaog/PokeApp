"""Focused 8L flows shared by real PostgreSQL and real JWT/API/PostgREST."""
from copy import deepcopy
from uuid import uuid4
from app.api.cup_models import CupCreateBody, CupDetail, CupReceipt
from app.repositories.supabase.cups import SupabaseCupRepository
from tools.validate_season_lifecycle_fixtures import SeasonLifecycleFixtures, require


class CupFixtures(SeasonLifecycleFixtures):
    def __init__(self,client,readers,auth_ids,run_id=None):
        super().__init__(client,readers,auth_ids,run_id or 'phase8l_validation_'+uuid4().hex)
        self.cups=SupabaseCupRepository(client)

    def cup_season(self):
        sid=self.roster()
        for t in (self.trainers[1],self.trainers[6]): self.add(sid,t['id'])
        b=self.config(sid); b.update(total_matchdays=1,rules=dict(team_lock_required=False,last_b_gets_steal=False))
        cfg=self.call('create_config',sid,b)['resource_id']
        s=self.state(sid); ids=sorted(p['id'] for p in s['participants'])
        self.call('initial_divisions',sid,dict(config_version_id=cfg,assignments={'A':ids[:3],'B':ids[3:]},
            expected_roster_revision=s['roster_revision'],expected_setup_revision=s['setup_revision']))
        self.call('prepare',sid,dict(expected_setup_revision=self.state(sid)['setup_revision']))
        self.call('activate',sid,dict(expected_setup_revision=self.state(sid)['setup_revision']))
        return sid

    def document(self,sid,cid,actor=None):
        result=self.cups.read(dict(season_id=sid,resource_id=cid,actor_trainer_id=actor or self.admin['id']))['cup']
        CupDetail.model_validate(result)
        return result

    def cup(self,op,sid,cid=None,body=None,key=None,actor=None,**resource):
        if body is None: body=dict(expected_revision=self.document(sid,cid)['revision'])
        r=self.request('cup_'+op,sid,body,cid,key,actor); r.update(resource)
        result=self.cups.execute(op,r); CupReceipt.model_validate(result)
        return result

    def create_cup(self,sid,fmt='swiss',n=4,start=True,rounds=3):
        players=sorted(self.players(sid),key=lambda p:p['id'])
        size=2 if fmt=='doubles' else 1
        body=dict(name=self.run_id+' Cup',format=fmt,swiss_rounds=rounds,
            sides=[dict(name='Side '+str(i+1),trainer_ids=[p['trainer_id'] for p in players[i*size:(i+1)*size]]) for i in range(n)])
        body=CupCreateBody.model_validate(body).model_dump(mode='json')
        cid=self.cup('create',sid,body=body)['cup_id']
        if start: self.cup('start',sid,cid)
        return cid

    @staticmethod
    def result_body(c,number=None,reverse=False,correction=False):
        r=c['rounds'][-1] if number is None else next(r for r in c['rounds'] if r['number']==number)
        results=[]
        for m in r['matches']:
            if m['status']!=('completed' if correction else 'scheduled'): continue
            result=dict(match_id=m['id'],winner_side_id=None,score_a=None,score_b=None)
            if r['phase']=='swiss': result['winner_side_id']=m['b'] if reverse else m['a']
            else: result.update(score_a=1 if reverse else 2,score_b=2 if reverse else 1)
            results.append(result)
        return dict(expected_revision=c['revision'],results=results)

    def play_round(self,sid,cid):
        c=self.document(sid,cid); r=c['rounds'][-1]; body=self.result_body(c)
        if body['results']: self.cup('results',sid,cid,body,round_number=r['number'])
        self.cup('close',sid,cid,round_number=r['number'])

    def finish_cup(self,sid,cid,certify=True):
        for _ in range(22):
            c=self.document(sid,cid); r=c['rounds'][-1]
            if r['phase']=='final' and r['status']=='closed': break
            self.play_round(sid,cid)
        else: raise AssertionError('Cup did not terminate')
        return self.cup('finalize',sid,cid) if certify else c

    def league_history(self,sid):
        tables=('season_players','season_player_stats','season_config_versions','divisions','division_memberships','matchdays','matches',
            'matchday_snapshots','matchday_snapshot_revisions','matchday_movements','coin_transactions','team_locks','season_archive_snapshots')
        result={t:sorted(self.rows(t,season_id=sid),key=lambda r:str(r.get('id',r.get('season_player_id')))) for t in tables}
        result['league_hall']=self.rows('hall_of_fame_entries',season_id=sid,competition_type='league')
        result['season']=self.rows('seasons',id=sid)
        return result

    def run(self):
        self.setup(); sid=self.cup_season()
        # League inactivity does not erase a same-season Cup identity.
        inactive=self.players(sid)[0]
        self.change(sid,inactive['id'])
        original_players=self.rows('season_players',season_id=sid)
        self.draft_checks(sid)
        cid=self.create_cup(sid,n=5,start=False)
        self.reject(lambda:self.cup('start',sid,cid,actor=self.owner['id']),'ADMIN_REQUIRED')
        body=dict(expected_revision=self.document(sid,cid)['revision']); key=uuid4().hex
        started=self.cup('start',sid,cid,body,key)
        initial=self.document(sid,cid)
        replay=self.cup('start',sid,cid,body,key)
        require(replay['operation_id']==started['operation_id'] and replay['replayed'],'Start receipt')
        require(self.document(sid,cid)==initial,'Replay reshuffled')
        self.reject(lambda:self.cup('start',sid,cid,dict(expected_revision=body['expected_revision']+1),key),'IDEMPOTENCY_CONFLICT')
        self.reject(lambda:self.cup('close',sid,cid,round_number=1),'RESULTS_INCOMPLETE')
        self.finish_cup(sid,cid)
        swiss=self.document(sid,cid)
        byes=[m['winner'] for r in swiss['rounds'] if r['phase']=='swiss' for m in r['matches'] if m['status']=='bye']
        require(len(byes)==len(set(byes))==3,'Swiss repeated avoidable bye')
        require([r['phase'] for r in swiss['rounds']]==['swiss']*3+['semifinal','final'],'Wrong Swiss phases')
        require(self.rows('season_players',season_id=sid)==original_players,'Cup changed League participation')
        for table,filters,change in (
            ('cups',{'id':cid},{'name':'forged'}),
            ('cup_certificates',{'cup_id':cid},{'checksum':'0'*64}),
            ('cup_side_members',{'cup_id':cid},{'display_name':'forged'})):
            q=self.client.table(table).update(change)
            for key,value in filters.items(): q=q.eq(key,value)
            try: q.execute()
            except Exception as exc: require(getattr(exc,'message',None)=='historical_artifact_immutable','Wrong certificate protection')
            else: raise AssertionError('Certified source mutable '+table)
        self.passed('L01 admin authority, inactive League entrant, immutable start replay, Swiss odd byes/Top4/final certification')

        elim=self.create_cup(sid,'elimination',5); self.finish_cup(sid,elim)
        doubles=self.create_cup(sid,'doubles',3); self.finish_cup(sid,doubles)
        hall=self.rows('hall_of_fame_entries',season_id=sid)
        require(len(hall)==3 and len({h['cup_id'] for h in hall})==3,'Multiple Cups collapsed in Hall')
        double_hall=next(h for h in hall if h['cup_id']==doubles)
        require(double_hall['champion_trainer_id'] is None and double_hall['champion_side_id'],'Doubles reduced to one trainer')
        members=self.rows('cup_side_members',cup_id=doubles,side_id=double_hall['champion_side_id'])
        require(len(members)==2 and all(h['team_snapshot']==[] for h in hall),'Hall members or invented Pokemon team')
        self.passed('L02 elimination five/real Bo3/byes and doubles RR/Top2/Bo3/both members; three independent Hall entries')

        correction=self.create_cup(sid,'elimination',4); self.play_round(sid,correction)
        c=self.document(sid,correction); old_ids=[m['id'] for m in c['rounds'][-1]['matches']]
        body=self.result_body(c,1,True,True); body['reason']='Recorded backwards'
        self.cup('correct',sid,correction,body,round_number=1)
        c=self.document(sid,correction)
        require([m['id'] for m in c['rounds'][-1]['matches']]!=old_ids,'Unplayed final not rebuilt')
        self.cup('results',sid,correction,self.result_body(c),round_number=2)
        c=self.document(sid,correction); body=self.result_body(c,1,False,True); body['reason']='Too late'
        self.reject(lambda:self.cup('correct',sid,correction,body,round_number=1),'PLAYED_RESULT_DEPENDENCY')
        self.cup('close',sid,correction,round_number=2)
        body=dict(expected_revision=self.document(sid,correction)['revision']); key=uuid4().hex
        first=self.cup('finalize',sid,correction,body,key); second=self.cup('finalize',sid,correction,body,key)
        require(first['certificate_id']==second['certificate_id'] and second['replayed'],'Certificate not exact once')
        self.reject(lambda:self.cup('discard',sid,correction,dict(expected_revision=first['revision'],reason='No',confirmation='DISCARD')),'CUP_TERMINAL')
        require(len(self.rows('cup_history',cup_id=correction))==first['revision'],'Missing revision history')
        self.passed('L03 reasoned correction rebuild, played dependency denial, certification replay/terminal guard and append-only history')

        for fmt,n in (('swiss',4),('doubles',3)):
            dq=self.create_cup(sid,fmt,n); c=self.document(sid,dq); side=c['sides'][-1]
            before=deepcopy(side['members'])
            self.cup('disqualify',sid,dq,dict(expected_revision=c['revision'],reason='Fixture DQ'),side_id=side['id'])
            self.finish_cup(sid,dq)
            c=self.document(sid,dq)
            require(c['sides'][-1]['members']==before and c['champion_side_id']!=side['id'],'DQ identity/champion')
            require(any(m['status']=='forfeit' and m['score_a'] is None for r in c['rounds'] for m in r['matches']),'Missing scoreless forfeit')
        cancelled=self.create_cup(sid); self.play_round(sid,cancelled); c=self.document(sid,cancelled)
        self.cup('discard',sid,cancelled,dict(expected_revision=c['revision'],reason='Fixture cancel',confirmation='DISCARD'))
        require(self.document(sid,cancelled)['rounds']==c['rounds'],'Cancellation lost history')
        self.reject(lambda:self.document(sid,cancelled,self.owner['id']),'CUP_NOT_FOUND')
        require(not self.rows('cup_certificates',cup_id=cancelled),'Cancelled Cup certified')
        self.passed('L04 singles/team DQ, scoreless continuation and cancellation preserving played history')

        did=self.state(sid)['current_matchday_id']; self.open(sid,did); self.results(sid,did); self.close(sid,did)
        self.life('finish',sid)
        finished=self.create_cup(sid,'elimination',2); self.finish_cup(sid,finished)
        self.life('archive',sid); baseline=self.league_history(sid)
        late=self.create_cup(sid,'elimination',2); self.finish_cup(sid,late)
        require(self.league_history(sid)==baseline,'Post-League Cup rewrote historical data')
        require(self.rows('season_archive_snapshots',season_id=sid)[0]['snapshot']['cup_hall_status']=='pending_cup_api','Archive marker rewritten')
        self.passed('L05 FINISHED and ARCHIVED Cups with exact League snapshots/rewards/movements/Hall/archive preservation')
        self.permissions(sid,cid)
        self.races(sid)

    def draft_checks(self,sid):
        cid=self.create_cup(sid,'elimination',4,start=False)
        c=self.document(sid,cid); players=sorted(self.players(sid),key=lambda p:p['id'])
        body=dict(name='Revised draft',format='doubles',swiss_rounds=1,expected_revision=c['revision'],
            sides=[dict(name='Team '+str(i),trainer_ids=[p['trainer_id'] for p in players[i*2:(i+1)*2]]) for i in range(3)])
        self.cup('setup',sid,cid,body)
        c=self.document(sid,cid)
        require(c['format']=='doubles' and all(len(s['members'])==2 for s in c['sides']),'Draft setup not replaced')
        self.reject(lambda:self.cup('setup',sid,cid,body),'STALE_REVISION')
        self.cup('disqualify',sid,cid,dict(expected_revision=c['revision'],reason='Draft DQ'),side_id=c['sides'][0]['id'])
        self.cup('start',sid,cid)
        self.reject(lambda:self.cup('setup',sid,cid,dict(body,expected_revision=self.document(sid,cid)['revision'])),'CUP_NOT_DRAFT')
        self.cup('discard',sid,cid,dict(expected_revision=self.document(sid,cid)['revision'],reason='Draft validation done',confirmation='DISCARD'))
        draft=self.draft(); create={k:v for k,v in body.items() if k!='expected_revision'}
        self.reject(lambda:self.cup('create',draft,body=create),'SEASON_NOT_ELIGIBLE')
        self.life('discard',draft)
        self.reject(lambda:self.cup('create',draft,body=create),'SEASON_NOT_ELIGIBLE')
        legacy=self.insert('cups',dict(season_id=sid,name='Ambiguous import',format='manual',status='finished',metadata={'champion':'untrusted'}))
        self.reject(lambda:self.cup('finalize',sid,legacy['id'],dict(expected_revision=0)),'LEGACY_CUP_UNSUPPORTED')
        require(not self.rows('cup_certificates',cup_id=legacy['id']),'Legacy Cup falsely certified')
        self.passed('L00 draft replace/CAS/DQ/freeze; draft/discarded season denials; ambiguous import remains uncertified')

    def permissions(self,sid,cid):
        for role,reader in self.readers.items():
            for table in ('cups','cup_participants','cup_matches','cup_standings','cup_side_members','cup_rounds','cup_certificates','cup_history'):
                try:
                    reader.table(table).update({'status':'active'} if table in ('cups','cup_participants','cup_matches','cup_rounds') else
                        {'revision':0} if table in ('cup_certificates','cup_history') else {'display_name':'bad'} if table=='cup_side_members' else {'wins':100}).eq('id' if table=='cups' else 'cup_id',cid).execute()
                except Exception as exc: require(str(getattr(exc,'code','')) in ('42501','PGRST204'),'Unexpected write denial '+table+' '+str(getattr(exc,'code','')))
                else: raise AssertionError('Browser write '+role+'/'+table)
            for rpc in ('api_cup_context','api_admin_cup','api_cup_read'):
                params={'p_request':dict(actor_trainer_id=self.admin['id'],season_id=sid)}
                if rpc=='api_admin_cup': params.update(p_fingerprint='x',p_plan={})
                try: reader.rpc(rpc,params).execute()
                except Exception as exc: require(str(getattr(exc,'code','')) in ('42501','PGRST202'),'Wrong RPC denial')
                else: raise AssertionError('Browser RPC '+role+'/'+rpc)
            if role=='anon':
                continue  # Existing public projections require an authenticated reader.
            public=reader.table('public_hall_of_fame').select('*').eq('season_id',sid).execute().data
            require(any(h['cup_id']==cid and h['cup_sides'] for h in public),'Public unified Hall missing Cup')
            require('actor_trainer_id' not in str(public) and 'reason' not in str(public),'Private audit leak')
        self.passed('L06 browser table/RPC denials including admin; safe unified Hall with Cup identity and both members')

    def races(self,sid):
        losers=('STALE_REVISION','STALE_INPUTS')
        def compete(label,a,b):
            result=self.race(a,b); self.one_winner(result,*losers); self.passed('race '+label)
        cid=self.create_cup(sid,'elimination',4,start=False); rev=self.document(sid,cid)['revision']
        compete('two starts',lambda:self.cup('start',sid,cid,dict(expected_revision=rev)),lambda:self.cup('start',sid,cid,dict(expected_revision=rev)))
        c=self.document(sid,cid); body=self.result_body(c)
        compete('results/results',lambda:self.cup('results',sid,cid,body,round_number=1),lambda:self.cup('results',sid,cid,body,round_number=1))
        c=self.document(sid,cid); rev=c['revision']; body=self.result_body(c,1,True,True); body['reason']='Race'
        compete('correction/close',lambda:self.cup('correct',sid,cid,body,round_number=1),lambda:self.cup('close',sid,cid,dict(expected_revision=rev),round_number=1))
        c=self.document(sid,cid)
        if c['rounds'][0]['status']=='open': self.cup('close',sid,cid,round_number=1)
        self.finish_cup(sid,cid,False); c=self.document(sid,cid); rev=c['revision']
        body=self.result_body(c,2,True,True); body['reason']='Race'
        compete('correction/finalize',lambda:self.cup('correct',sid,cid,body,round_number=2),lambda:self.cup('finalize',sid,cid,dict(expected_revision=rev)))
        cid=self.create_cup(sid,'elimination',2); c=self.document(sid,cid); body=self.result_body(c); rev=c['revision']
        # Close may arrive before results: either a coherent close or incomplete,
        # never a close built from a partial result batch.
        raced=self.race(lambda:self.cup('results',sid,cid,body,round_number=1),lambda:self.cup('close',sid,cid,dict(expected_revision=rev),round_number=1))
        self.one_winner(raced,*losers,'RESULTS_INCOMPLETE'); self.passed('race results/close')
        c=self.document(sid,cid); rev=c['revision']
        compete('two closes',lambda:self.cup('close',sid,cid,dict(expected_revision=rev),round_number=1),lambda:self.cup('close',sid,cid,dict(expected_revision=rev),round_number=1))
        rev=self.document(sid,cid)['revision']
        compete('discard/finalize',lambda:self.cup('discard',sid,cid,dict(expected_revision=rev,reason='Race',confirmation='DISCARD')),lambda:self.cup('finalize',sid,cid,dict(expected_revision=rev)))
        cid=self.create_cup(sid,'elimination',2); c=self.document(sid,cid); body=self.result_body(c); rev=c['revision']; side=c['sides'][0]['id']
        compete('DQ/results',lambda:self.cup('disqualify',sid,cid,dict(expected_revision=rev,reason='Race'),side_id=side),lambda:self.cup('results',sid,cid,body,round_number=1))
        cid=self.create_cup(sid,'elimination',2); self.finish_cup(sid,cid,False); rev=self.document(sid,cid)['revision']
        compete('two finalizes',lambda:self.cup('finalize',sid,cid,dict(expected_revision=rev)),lambda:self.cup('finalize',sid,cid,dict(expected_revision=rev)))
        other=self.cup_season(); did=self.state(other)['current_matchday_id']
        self.open(other,did); self.results(other,did); self.close(other,did)
        cid=self.create_cup(other,'elimination',2); self.finish_cup(other,cid,False)
        rev=self.document(other,cid)['revision']; before=self.league_history(other); before.pop('season')
        result=self.race(lambda:self.cup('finalize',other,cid,dict(expected_revision=rev)),lambda:self.life('finish',other))
        require(isinstance(result[1],dict) and (isinstance(result[0],dict) or result[0]=='STALE_INPUTS'),'Cup/League finish race')
        after=self.league_history(other); after.pop('season')
        require(before==after,'Concurrent finalization rewrote League history')
        read=self.document(other,cid,self.owner['id'])
        require((read['status']=='finished')==(read['certificate_id'] is not None),'Torn read certificate')
        self.passed('race Cup finalization/League finish and consistent certificate read')

    def cleanup(self):
        for sid in self.seasons:
            self.client.table('hall_of_fame_entries').delete().eq('season_id',sid).execute()
            for c in self.rows('cups',season_id=sid):
                for t in ('cup_certificates','cup_history','cup_matches','cup_standings','cup_rounds','cup_side_members'):
                    self.client.table(t).delete().eq('cup_id',c['id']).execute()
        super().cleanup()
