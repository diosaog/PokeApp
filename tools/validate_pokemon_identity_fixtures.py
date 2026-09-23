"""Shared local/staging identity fixtures. Synthetic JSON only, no raw saves."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from dataclasses import asdict
from uuid import uuid4

from app.application.pokemon_identity import reconcile_parsed_save
from app.domain.pokemon_identity import CaptureOrder, PokemonIdentityEvidence
from app.repositories.supabase.pokemon_identity import SupabasePokemonIdentityRepository
from app.repositories.errors import ConflictError

TABLES = ('pokemon_entities','pokemon_observations','pokemon_identity_revisions','pokemon_entity_flags')


def require(condition, message):
    if not condition:
        raise AssertionError(message)


class IdentityFixtures:
    def __init__(self, client, readers, auth_ids, *, run_id=None):
        self.client, self.readers, self.auth_ids = client, readers, auth_ids
        self.run_id = run_id or 'phase8f0_validation_' + uuid4().hex
        self.rows, self.checks = {}, []
        self.season = None
        self.repository = SupabasePokemonIdentityRepository(client)
        self.stream = str(uuid4())

    def passed(self, name):
        self.checks.append(name)
        print('PASS ' + name, flush=True)

    def insert(self, table, body):
        row_id = str(uuid4())
        self.rows.setdefault(table, []).append(row_id)
        return self.client.table(table).insert({'id':row_id, **body}).execute().data[0]

    def select(self, table, client=None, **filters):
        query = (client or self.client).table(table).select('*')
        for key, value in filters.items(): query = query.eq(key, value)
        return query.execute().data

    def denied(self, action, label, codes=('42501',)):
        try:
            response = action()
        except Exception as exc:
            require(str(getattr(exc,'code','')) in codes, label+' unexpected error '+str(getattr(exc,'code',type(exc).__name__)))
            return
        require(response.data == [], label)

    def save(self, number, *, clone=True, unique=True, boxes=False):
        evidence = PokemonIdentityEvidence(1,5,123456789,12345,6789,20,2,'Fixture',0,ivs=(17,0,0,0,0,0))
        pokemon = dict(species='Gastly', identity_evidence=asdict(evidence), legacy_fingerprints=['colliding'])
        mons = [deepcopy(pokemon),deepcopy(pokemon)] if clone else []
        if unique:
            mon = deepcopy(pokemon)
            mon['identity_evidence']['pid'] = 555
            mon['legacy_fingerprints'] = ['unique']
            mon['species'] = 'Gengar' if number > 1 else 'Gastly'
            mon['level'] = 40 + number
            mons.append(mon)
        slots = [{'slot_number':i+1, 'pokemon':p} for i,p in enumerate(mons)]
        payload = dict(party=[] if boxes else slots, boxes=[dict(box_number=2,slots=slots)] if boxes else [])
        save = self.insert('save_files', dict(season_id=self.season['id'],trainer_id=self.owner['id'],
            storage_key=self.run_id + '/' + str(number) + '.sav', original_filename='synthetic-no-bytes.sav',
            sha256=f'{number:064x}', parser_status='parsed', parser_version='identity-fixture-v1',
            uploaded_at=f'2026-01-{number:02}T00:00:00Z'))
        parsed = self.insert('parsed_saves', dict(save_file_id=save['id'],parser_version=save['parser_version'],payload=payload))
        return save, parsed

    def reconcile(self, parsed, sequence):
        return reconcile_parsed_save(self.repository, season_id=self.season['id'], trainer_id=self.owner['id'],
            parsed_save_id=parsed['id'], capture_order=CaptureOrder(self.stream,sequence))

    def run(self):
        actors = {}
        for role in ('owner','other','admin'):
            actors[role] = self.insert('trainers',dict(display_name=self.run_id+'_'+role,slug=self.run_id+'_'+role,
                auth_user_id=self.auth_ids[role],is_admin=role=='admin'))
        self.owner = actors['owner']
        self.season = self.insert('seasons',dict(name=self.run_id,status='draft'))
        for actor in actors.values():
            player = self.insert('season_players',dict(season_id=self.season['id'],trainer_id=actor['id']))
            if actor['id'] == self.owner['id']: self.player = player
        for fingerprint in ('unique','colliding'):
            self.insert('pokemon_flags',dict(season_id=self.season['id'],trainer_id=self.owner['id'],
                season_player_id=self.player['id'], fingerprint=fingerprint,flag_type='shielded'))
        saved, parsed = self.save(1)
        # Concurrent initial allocation, not just replay after a preexisting result.
        with ThreadPoolExecutor(max_workers=4) as pool:
            receipts = list(pool.map(lambda _: self.reconcile(parsed,1), range(4)))
        first = receipts[0]
        require(all(r == first for r in receipts), 'concurrent receipts differ')
        entities = self.select('pokemon_entities',season_id=self.season['id'])
        observations = first['observations']
        require(len(entities)==3 and len({e['id'] for e in entities})==3,'clones collapsed')
        self.passed('RI01 backend entity creation; first clones distinct')
        require(len(observations)==3 and len({o['pokemon_entity_id'] for o in observations})==3,'observation uniqueness')
        self.passed('RI02 observations')
        require(self.reconcile(parsed,1)==first,'same-save replay changed')
        self.passed('RI03 same-save idempotency')
        self.passed('RI11 concurrent initial processing: four workers, one revision')

        for table in TABLES:
            own = self.select(table,self.readers['owner'],season_id=self.season['id'])
            admin = self.select(table,self.readers['admin'],season_id=self.season['id'])
            require(own and admin,'owner/admin read missing '+table)
            require(not self.select(table,self.readers['other'],season_id=self.season['id']),'other private leak '+table)
            self.denied(lambda t=table:self.readers['anon'].table(t).select('*').execute(),'anon read '+table)
            for role in ('owner','admin'):
                self.denied(lambda t=table,r=role:self.readers[r].table(t).insert({'id':str(uuid4())}).execute(),'direct insert '+table)
                self.denied(lambda t=table,r=role:self.readers[r].table(t).delete().eq('season_id',self.season['id']).execute(),'direct delete '+table)
            self.denied(lambda t=table:self.readers['owner'].table(t).update({'id':str(uuid4())}).eq(
                'season_id',self.season['id']).execute(),'direct update '+table)
        self.passed('RI04 owner/admin private reads')
        self.passed('RI05 anon denied')
        self.passed('RI06 other trainer isolated')
        for role in ('anon','owner','admin'):
            self.denied(lambda r=role:self.readers[r].rpc('commit_pokemon_identity',{'p_request':{}}).execute(),'RPC denied')
        self.passed('RI07 browser identity writes and RPC denied')
        self.passed('RI08 service backend writes')

        links = self.select('pokemon_entity_flags',season_id=self.season['id'])
        require(len(links)==1,'unique legacy mapping absent')
        unique_id = links[0]['pokemon_entity_id']
        require(links[0]['flag_value'] is None,'legacy flag value must remain authoritative')
        self.passed('RI09 unique legacy flag linked')
        require(len(self.select('pokemon_flags',season_id=self.season['id']))==2,'legacy flags lost')
        self.passed('RI10 colliding legacy flag intact and unresolved')
        clone_id = next(e['id'] for e in entities if e['id'] != unique_id)
        new_flag = dict(season_id=self.season['id'],trainer_id=self.owner['id'],pokemon_entity_id=clone_id,
                        flag_type='shielded',flag_value=True)
        self.insert('pokemon_entity_flags',new_flag)
        self.denied(lambda:self.client.table('pokemon_entity_flags').insert(new_flag).execute(),'duplicate entity flag',('23505',))
        clone_obs = next(o for o in observations if o['pokemon_entity_id']==clone_id)
        require(self.repository.authoritative_target(season_id=self.season['id'],trainer_id=self.owner['id'],
            observation_id=clone_obs['id'])==clone_id,'initial clone target')
        self.passed('I29 one clone targeted, duplicate entity flag rejected')
        duplicate = {k:v for k,v in observations[0].items() if k not in ('id','created_at')}
        self.denied(lambda:self.client.table('pokemon_observations').insert(duplicate).execute(),'duplicate observation',('23505',))
        self.passed('SQL observation location/entity uniqueness')

        self.client.table('save_files').update({'parser_version':'identity-fixture-v2'}).eq('id',saved['id']).execute()
        reparsed = self.insert('parsed_saves',dict(save_file_id=saved['id'],parser_version='identity-fixture-v2',payload=parsed['payload']))
        require(self.reconcile(reparsed,1)==first,'reparse changed identities')
        self.passed('I34 unchanged reparse reuses receipt')
        _, second = self.save(2,boxes=True)
        receipt = self.reconcile(second,2)
        require(sum(o['outcome']=='AMBIGUOUS' for o in receipt['observations'])==2,'clones auto-bound')
        require(next(o['pokemon_entity_id'] for o in receipt['observations'] if o['outcome']=='MATCHED')==unique_id,'evolution/movement lost identity')
        try:
            self.repository.authoritative_target(season_id=self.season['id'],trainer_id=self.owner['id'],observation_id=clone_obs['id'])
        except ConflictError: pass
        else: raise AssertionError('historical target allowed')
        self.passed('I15/I18/I22/I23 movement/evolution stable; clones ambiguous; stale target denied')
        _, third = self.save(3,unique=False)
        self.reconcile(third,3)
        require(self.select('pokemon_entities',id=unique_id)[0]['identity_status']=='missing','absence not retained')
        _, fourth = self.save(4)
        returned = self.reconcile(fourth,4)
        require(any(o['pokemon_entity_id']==unique_id for o in returned['observations']),'return lost identity')
        self.passed('I19/I20 missing retained, unambiguous return recovered')
        _, stale = self.save(5)
        try: self.reconcile(stale,2)
        except ConflictError as exc:
            require(getattr(exc.__cause__,'code',None)=='PT409','stale rejection must be a database conflict')
        else: raise AssertionError('out-of-order accepted')
        require(len(self.select('pokemon_identity_revisions',season_id=self.season['id']))==4,'stale changed head')
        self.passed('I33 late upload cannot supersede trusted capture chain')

        class CaptureRepository(SupabasePokemonIdentityRepository):
            def commit(self, request): return request
        capture = CaptureRepository(self.client)
        requests = []
        for number in (6,7):
            _, new_parse = self.save(number)
            requests.append(reconcile_parsed_save(capture,season_id=self.season['id'],trainer_id=self.owner['id'],
                parsed_save_id=new_parse['id'],capture_order=CaptureOrder(self.stream,number)))
        def compete(request):
            try: return self.repository.commit(request)
            except ConflictError as exc:
                require(getattr(exc.__cause__,'code',None)=='PT409','CAS rejection must be a database conflict')
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(compete,requests))
        require(sum(r is not None for r in results)==1,'competing heads both committed')
        require(len(self.select('pokemon_identity_revisions',season_id=self.season['id']))==5,'CAS partial writes')
        self.passed('SQL concurrent distinct saves: one CAS winner, no partial loser')

    def cleanup(self):
        # Only fixture-owned IDs/scopes. No global reset, no real save bytes ever created.
        remaining = []
        if self.season:
            for table in ('pokemon_entity_flags','pokemon_observations','pokemon_identity_revisions','pokemon_entities','pokemon_flags'):
                try:
                    self.client.table(table).delete().eq('season_id',self.season['id']).execute()
                    if self.select(table,season_id=self.season['id']): remaining.append(table)
                except Exception: remaining.append(table)
        for table in ('parsed_saves','save_files','season_players','seasons','trainers'):
            for row_id in self.rows.get(table,[]):
                try:
                    self.client.table(table).delete().eq('id',row_id).execute()
                    if self.select(table,id=row_id): remaining.append(table+':'+row_id)
                except Exception: remaining.append(table+':'+row_id)
        require(not remaining,'identity cleanup incomplete: '+','.join(remaining))
        self.passed('RI12 fixture rows cleaned and verified')
