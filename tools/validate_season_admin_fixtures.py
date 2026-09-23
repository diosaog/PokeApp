"""Same synthetic business/security/race checks on real PostgreSQL and PostgREST."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from app.api.season_admin_models import AdminReceipt, SeasonSetup
from app.repositories.supabase.season_admin import RPCS, SeasonAdminRejected, SupabaseSeasonAdminRepository


def require(condition, message):
    if not condition:
        raise AssertionError(message)


TABLES = ("admin_operation_receipts", "activity_events", "matches", "division_memberships", "matchdays",
    "divisions", "season_config_versions", "season_player_stats", "season_players", "season_admin_state")
AUTHORITATIVE = ("seasons", "season_players", "season_player_stats", "season_config_versions",
    "divisions", "division_memberships", "matchdays", "matches")


class SeasonAdminFixtures:
    def __init__(self, client, readers, auth_ids, run_id=None):
        self.client, self.readers, self.auth_ids = client, readers, auth_ids
        self.run_id = run_id or "phase8g1_validation_"+uuid4().hex
        self.repo = SupabaseSeasonAdminRepository(client)
        self.seasons, self.trainers, self.checks = [], [], []

    def passed(self, label):
        self.checks.append(label)
        print("PASS "+label, flush=True)

    def rows(self, table, **filters):
        q = self.client.table(table).select("*")
        for key, value in filters.items():
            q = q.eq(key, value)
        return q.execute().data

    def insert(self, table, body):
        return self.client.table(table).insert(body).execute().data[0]

    def setup(self):
        require(not self.rows('seasons', status='active'), 'Active season exists; refusing activation fixtures')
        for i in range(7):
            role = ('admin', 'other', 'owner')[i] if i<3 else None
            trainer = self.insert('trainers', dict(display_name=self.run_id+'_'+str(i), slug=self.run_id+'_'+str(i),
                is_admin=i<2, **({'auth_user_id': self.auth_ids[role]} if role else {})))
            self.trainers.append(trainer)
        self.admin, self.admin2, self.owner = self.trainers[:3]

    def request(self, op, sid=None, body=None, resource=None, key=None, actor=None):
        r = dict(actor_trainer_id=actor or self.admin['id'])
        if sid: r['season_id'] = sid
        if body is not None: r['body'] = body
        if resource: r['resource_id'] = resource
        if op!='setup': r['idempotency_key'] = key or uuid4().hex
        return r

    def call(self, op, sid=None, body=None, resource=None, key=None, actor=None):
        r = self.request(op,sid,body,resource,key,actor)
        result = self.repo.execute(op,r)
        if op=='setup': SeasonSetup.model_validate(result)
        else: AdminReceipt.model_validate(result)
        if op=='create' and result['season_id'] not in self.seasons: self.seasons.append(result['season_id'])
        return result

    def reject(self, action, *codes):
        try: action()
        except SeasonAdminRejected as exc:
            require(exc.code in codes, 'Unexpected rejection '+exc.code+' expected '+str(codes))
        else: raise AssertionError('Expected rejection '+str(codes))

    def draft(self):
        return self.call('create',body={'name':self.run_id+'_'+uuid4().hex[:8]})['season_id']

    def state(self,sid):
        return self.call('setup',sid)

    def add(self,sid,tid=None,revision=None,**kw):
        if revision is None: revision=self.state(sid)['roster_revision']
        return self.call('add_participant',sid,dict(trainer_id=tid or self.owner['id'],seed_order=None,expected_roster_revision=revision),**kw)

    def config(self,sid,**changes):
        s=self.state(sid); n=len(s['participants'])
        return dict(name='Initial',effective_from_matchday=1,total_matchdays=4,division_sizes={'A':n//2,'B':n-n//2},
            movement_count=1,scoring={str(i):n-i for i in range(1,n+1)},coin_rewards={str(i):10 for i in range(1,n+1)},
            rules={'team_lock_required':True,'last_b_gets_steal':True},expected_config_revision=s['config_revision'],
            expected_roster_revision=s['roster_revision'],**changes)

    def roster(self):
        sid=self.draft()
        for t in self.trainers[2:6]: self.add(sid,t['id'])
        return sid

    def divisions_body(self,sid,cid):
        s=self.state(sid); ids=sorted(p['id'] for p in s['participants'])
        return dict(config_version_id=cid,assignments={'A':ids[:2],'B':ids[2:]},
            expected_roster_revision=s['roster_revision'],expected_setup_revision=s['setup_revision'])

    def ready(self,prepare=False):
        sid=self.roster()
        c=self.call('create_config',sid,self.config(sid))
        self.call('initial_divisions',sid,self.divisions_body(sid,c['resource_id']))
        if prepare: self.call('prepare',sid,{'expected_setup_revision':self.state(sid)['setup_revision']})
        return sid

    def race(self,*actions):
        barrier=Barrier(len(actions))
        def run(action):
            barrier.wait(timeout=30)
            try: return action()
            except SeasonAdminRejected as exc: return exc.code
        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            results=list(pool.map(run,actions))
        return results

    def one_winner(self,results,*losers):
        require(sum(isinstance(r,dict) for r in results)==1,'Expected exactly one successful mutation')
        require(all(isinstance(r,dict) or r in losers for r in results),'Unexpected race rejection '+str(results))

    def run(self):
        self.setup()
        self.reject(lambda:self.call('create',body={'name':self.run_id},actor=self.owner['id']),'ADMIN_REQUIRED')
        self.passed('RG01/RG02 backend admin identity; non-admin denied; admin not enrolled')
        key=uuid4().hex; body={'name':self.run_id+'_replay'}
        results=self.race(lambda:self.call('create',body=body,key=key),lambda:self.call('create',body=body,key=key))
        require(results[0]['operation_id']==results[1]['operation_id'],'Concurrent create duplicated')
        sid=results[0]['season_id']
        self.reject(lambda:self.call('create',body={'name':body['name']+'changed'},key=key),'IDEMPOTENCY_CONFLICT')
        self.passed('RG03/A/B durable same-actor create replay and semantic conflict')
        race_key=uuid4().hex
        conflict=self.race(lambda:self.call('create',body={'name':self.run_id+'_a'},key=race_key),
            lambda:self.call('create',body={'name':self.run_id+'_b'},key=race_key))
        self.one_winner(conflict,'IDEMPOTENCY_CONFLICT')
        self.call('rename',sid,{'name':self.run_id+'_renamed','expected_revision':0},key='revision:0')
        self.reject(lambda:self.call('rename',sid,{'name':'stale','expected_revision':0}),'STALE_REVISION')
        self.passed('RG16 rename CAS')
        race=self.race(lambda:self.add(sid,revision=0),lambda:self.add(sid,revision=0,actor=self.admin2['id']))
        self.one_winner(race,'STALE_REVISION','PARTICIPANT_EXISTS')
        player=self.rows('season_players',season_id=sid)[0]
        require(len(self.rows('season_player_stats',season_id=sid))==1,'Stats duplicated/missing')
        require(self.rows('season_player_stats',season_id=sid)[0]['badges_count']==0,'Stats not zero')
        require(player['current_save_file_id'] is None and player['metadata']=={},'Inherited state')
        self.reject(lambda:self.add(sid),'PARTICIPANT_EXISTS')
        self.passed('RG04/RG14/C provisioning race, zero stats, no save or economy inheritance')
        self.call('remove_participant',sid,{'reason':'Draft correction','expected_roster_revision':1},player['id'])
        require(not self.rows('season_players',season_id=sid) and not self.rows('season_player_stats',season_id=sid),'Removal incomplete')
        race=self.race(lambda:self.add(sid,self.owner['id'],revision=2),lambda:self.add(sid,self.trainers[3]['id'],revision=2,actor=self.admin2['id']))
        self.one_winner(race,'STALE_REVISION')
        self.passed('D clean removal and different roster edits CAS')
        main=self.roster(); cfg=self.config(main)
        for changed,code in (({'division_sizes':{'A':1,'B':2}},'INVALID_CONFIG'),({'scoring':{'1':1}},'INVALID_REWARDS'),
                             ({'coin_rewards':{'1':-1}},'INVALID_REWARDS'),({'rules':{'other':True}},'INVALID_CONFIG')):
            self.reject(lambda changed=changed:self.call('create_config',main,{**cfg,**changed}),code)
        key=uuid4().hex
        c=self.call('create_config',main,cfg,key=key)
        require(self.call('create_config',main,cfg,key=key)['operation_id']==c['operation_id'],'Config replay changed')
        cid=c['resource_id']
        self.reject(lambda:self.call('create_config',main,self.config(main)),'EFFECTIVE_ROUND_EXISTS')
        self.call('replace_config',main,{**self.config(main),'name':'Corrected','reason':'Validated adjustment'},cid)
        self.reject(lambda:self.call('remove_participant',main,{'reason':'unsafe','expected_roster_revision':4},self.state(main)['participants'][0]['id']),'PARTICIPANT_REFERENCED')
        self.passed('RG05/RG06 config validation, replay, same-round unused correction, referenced removal')
        div=self.divisions_body(main,cid)
        bad={**div,'assignments':{'A':div['assignments']['A'],'B':div['assignments']['A']}}
        self.reject(lambda:self.call('initial_divisions',main,bad),'INVALID_ROSTER')
        bad={**div,'assignments':{'A':div['assignments']['A'][:1],'B':div['assignments']['A'][1:]+div['assignments']['B']}}
        self.reject(lambda:self.call('initial_divisions',main,bad),'DIVISION_CAPACITY_MISMATCH')
        self.call('initial_divisions',main,div)
        self.reject(lambda:self.add(main,self.trainers[6]['id']),'INITIAL_SETUP_LOCKED')
        self.reject(lambda:self.call('activate',main,{'expected_setup_revision':self.state(main)['setup_revision']}),'SETUP_INCOMPLETE')
        self.passed('RG08 exact A/B, complete historical initial memberships; no premature activation')
        b={'expected_setup_revision':self.state(main)['setup_revision']}; key=uuid4().hex
        results=self.race(lambda:self.call('prepare',main,b,key=key),lambda:self.call('prepare',main,b,key=key))
        require(results[0]['operation_id']==results[1]['operation_id'],'Prepare same key duplicated')
        s=self.state(main); day=s['first_matchday']; pairs=self.rows('matches',season_id=main)
        require(day['status']=='scheduled' and day['number']==1 and day['match_count']==2 and len(pairs)==2,'Wrong first matchday')
        require(s['current_matchday_id']==day['id'] and s['readiness']['can_activate'],'Pointer/readiness')
        self.reject(lambda:self.call('replace_config',main,{**self.config(main),'reason':'too late'},cid),'CONFIG_ALREADY_USED')
        try: self.client.table('season_config_versions').update({'name':'forbidden rewrite'}).eq('id',cid).execute()
        except Exception as exc: require(str(getattr(exc,'code',''))=='PT409','Wrong used-config guard')
        else: raise AssertionError('Backend overwrote referenced config')
        inverse={k:v for k,v in pairs[0].items() if k not in ('id','created_at','updated_at')}
        inverse['player_a_id'],inverse['player_b_id']=inverse['player_b_id'],inverse['player_a_id']
        try: self.insert('matches',inverse)
        except Exception as exc: require(str(getattr(exc,'code',''))=='23505','Wrong inverse pair guard')
        else: raise AssertionError('Inverse pair inserted')
        try: self.client.table('admin_operation_receipts').update({'response_json':{}}).eq('id',c['operation_id']).execute()
        except Exception as exc: require(str(getattr(exc,'code',''))=='PT409','Wrong receipt guard')
        else: raise AssertionError('Receipt mutated')
        self.passed('RG07/RG09/RG10/RG11/G correct all-vs-all pairs, server pointer, frozen config, prepare replay')
        uneven=self.roster(); self.add(uneven,self.trainers[6]['id'])
        uneven_config=self.call('create_config',uneven,self.config(uneven))
        self.call('initial_divisions',uneven,self.divisions_body(uneven,uneven_config['resource_id']))
        self.call('prepare',uneven,{'expected_setup_revision':self.state(uneven)['setup_revision']})
        require(self.state(uneven)['first_matchday']['match_count']==4,'2/3 capacities require 1+3 all-vs-all matches')
        self.passed('G28 complete nontrivial all-vs-all in unequal 2/3 divisions')
        self.races(main)
        self.permissions(main)
        for season in self.seasons:
            for table in ('coin_transactions','purchases','redemptions','save_files','trainer_flags','cups','trial_cases'):
                require(not self.rows(table,season_id=season),'Unexpected mutation to '+table)
        self.passed('G36-G40 only first day; zero rewards/purchases/redemptions/saves/flags/cups/trials')

    def races(self,main):
        sid=self.roster(); cfg=self.config(sid)
        results=self.race(lambda:self.call('create_config',sid,cfg),lambda:self.call('create_config',sid,{**cfg,'name':'Other'},actor=self.admin2['id']))
        self.one_winner(results,'STALE_REVISION')
        self.passed('E concurrent config CAS')
        sid=self.ready(); s=self.state(sid); cid=s['config_versions'][0]['id']
        results=self.race(lambda:self.call('replace_config',sid,{**self.config(sid),'reason':'Race correction'},cid),
            lambda:self.call('prepare',sid,{'expected_setup_revision':s['setup_revision']}))
        require(all(isinstance(r,dict) or r in ('CONFIG_ALREADY_USED','STALE_REVISION') for r in results),'Unsafe replace/prepare race')
        require(any(isinstance(r,dict) for r in results),'Both config race operations failed')
        if self.state(sid)['first_matchday'] is None:
            self.call('prepare',sid,{'expected_setup_revision':self.state(sid)['setup_revision']})
        self.reject(lambda:self.call('replace_config',sid,{**self.config(sid),'reason':'After use'},cid),'CONFIG_ALREADY_USED')
        self.passed('F replacement vs first use serialized')
        sid=self.ready(); b={'expected_setup_revision':self.state(sid)['setup_revision']}
        results=self.race(lambda:self.call('prepare',sid,b),lambda:self.call('prepare',sid,b,actor=self.admin2['id']))
        self.one_winner(results,'MATCHDAY_ALREADY_PREPARED')
        require(len(self.rows('matchdays',season_id=sid))==1 and len(self.rows('matches',season_id=sid))==2,'Prepare duplicate day/pairs')
        self.passed('RG15/H two admins, different prepare keys, one matchday')
        sid=self.roster(); cfg=self.config(sid)
        results=self.race(lambda:self.call('create_config',sid,cfg),lambda:self.add(sid,self.trainers[6]['id'],revision=4))
        require(all(isinstance(r,dict) or r=='STALE_REVISION' for r in results),'Config/roster race')
        require(not self.state(sid)['readiness']['can_activate'],'Stale setup can activate')
        sid=self.roster(); c=self.call('create_config',sid,self.config(sid)); div=self.divisions_body(sid,c['resource_id'])
        results=self.race(lambda:self.call('initial_divisions',sid,div),lambda:self.add(sid,self.trainers[6]['id'],revision=4))
        self.one_winner(results,'INITIAL_SETUP_LOCKED','STALE_REVISION')
        self.passed('K roster edits vs config/divisions remain revision consistent')
        remove_sid=self.roster(); remove_cfg=self.config(remove_sid); pid=self.state(remove_sid)['participants'][0]['id']
        results=self.race(lambda:self.call('create_config',remove_sid,remove_cfg),
            lambda:self.call('remove_participant',remove_sid,{'reason':'Race','expected_roster_revision':4},pid))
        self.one_winner(results,'STALE_REVISION','PARTICIPANT_REFERENCED')
        second=self.ready(prepare=True)
        b={'expected_setup_revision':self.state(main)['setup_revision']}
        b2={'expected_setup_revision':self.state(second)['setup_revision']}
        results=self.race(lambda:self.call('activate',main,b,key='activate'),lambda:self.call('activate',second,b2,key='activate'))
        self.one_winner(results,'ACTIVE_SEASON_EXISTS')
        winner=next(r for r in results if isinstance(r,dict)); active=winner['season_id']
        require(len(self.rows('seasons',status='active'))==1,'More than one active season')
        original_b=b if active==main else b2
        results=self.race(lambda:self.call('activate',active,original_b,key='activate'),lambda:self.call('activate',active,original_b,key='activate'))
        require(all(r['operation_id']==winner['operation_id'] for r in results),'Activation replay')
        self.reject(lambda:self.call('activate',active,{'expected_setup_revision':self.state(active)['setup_revision']},actor=self.admin2['id']),'SEASON_NOT_DRAFT')
        require(self.state(active)['season']['status']=='active','Auto-finished winner')
        self.reject(lambda:self.add(active,self.trainers[6]['id']),'SEASON_NOT_DRAFT')
        self.passed('RG12/RG13/I/J activation replay; global one-active constraint; no auto-finish or late join')

    def permissions(self,sid):
        require(all(e['visibility']=='admin' for e in self.rows('activity_events',season_id=sid)),'Public admin audit')
        require(not self.readers['owner'].table('public_activity_events').select('*').eq('season_id',sid).execute().data,'Admin audit leaked')
        for role in ('admin','owner','anon'):
            client=self.readers[role]
            for table in AUTHORITATIVE:
                for method,body in (('insert',{'metadata':{}}),('update',{'metadata':{}}),('delete',None)):
                    q=client.table(table)
                    q=getattr(q,method)() if body is None else getattr(q,method)(body)
                    if method!='insert': q=q.eq('season_id' if table!='seasons' else 'id',sid)
                    try: q.execute()
                    except Exception as exc: require(str(getattr(exc,'code',''))=='42501','Wrong direct-write denial '+str(getattr(exc,'code','')))
                    else: raise AssertionError('Direct '+role+' '+table+' '+method+' allowed')
            for rpc in RPCS.values():
                try: client.rpc(rpc,{'p_request':self.request('setup',sid)}).execute()
                except Exception as exc: require(str(getattr(exc,'code',''))=='42501','Wrong RPC denial')
                else: raise AssertionError('Browser RPC allowed')
        self.passed('RG17/RG18 G41-G45 authenticated/admin/anon INSERT UPDATE DELETE and every RPC denied')

    def cleanup(self):
        # Discover committed create receipts even if a transport failed before returning.
        for t in self.trainers[:2]:
            for r in self.rows('admin_operation_receipts',actor_trainer_id=t['id']):
                if r['season_id'] not in self.seasons: self.seasons.append(r['season_id'])
        for sid in self.seasons:
            self.client.table('seasons').update({'current_matchday_id':None}).eq('id',sid).execute()
            for table in TABLES:
                self.client.table(table).delete().eq('season_id',sid).execute()
            self.client.table('seasons').delete().eq('id',sid).execute()
            require(not self.rows('seasons',id=sid),'Season cleanup')
            for table in TABLES: require(not self.rows(table,season_id=sid),'Cleanup '+table)
        for trainer in self.trainers:
            self.client.table('trainers').delete().eq('id',trainer['id']).execute()
            require(not self.rows('trainers',id=trainer['id']),'Trainer cleanup')
        self.passed('RG22 synthetic cleanup and per-table zero residue')
