"""Loopback-only SQL transport for the production identity adapter/fixture suite."""
import json
import os
import re
import subprocess
from types import SimpleNamespace
from uuid import uuid4

from tools.validate_pokemon_identity_fixtures import IdentityFixtures


def identifier(value):
    if not re.fullmatch(r'[a-z_][a-z_0-9]*', value): raise ValueError('Unsafe SQL identifier')
    return '"' + value + '"'


def literal(value):
    return "'" + str(value).replace("'", "''") + "'"


class SqlError(Exception):
    def __init__(self, code, message=''):
        self.code = code
        self.message = message
        super().__init__('Local SQL rejected: '+code)


class LocalClient:
    def __init__(self, args, role='service_role', user_id=None):
        if args.host not in ('localhost','127.0.0.1','::1') or not args.database.startswith('pokeapp_v2_validation'):
            raise ValueError('Identity SQL fixtures require an isolated loopback validation database')
        self.args, self.role, self.user_id = args, role, user_id

    def table(self, table): return Query(self, table)
    def rpc(self, name, args):
        if 'p_request' in args:
            values = literal(json.dumps(args['p_request']))+'::jsonb'
        else:
            values = ','.join(identifier(key)+' => '+('NULL' if value is None else literal(json.dumps(value) if isinstance(value,(dict,list)) else value))
                              for key,value in args.items())
        call='public.'+identifier(name)+'('+values+')'
        query=("select coalesce(jsonb_agg(to_jsonb(r)),'[]'::jsonb) from "+call+' r') if name=='api_upsert_team_lock' else 'select to_jsonb('+call+')'
        return SimpleNamespace(execute=lambda:self.execute(query))

    def execute(self, sql):
        args = self.args
        claims = json.dumps({'sub':self.user_id,'role':self.role})
        sql = ('begin; set local role '+identifier(self.role)+'; set local request.jwt.claims='+literal(claims)+'; '
               + 'set local request.jwt.claim.sub='+literal(self.user_id or '')+'; '+sql+'; commit;')
        env = dict(os.environ, PGPASSWORD=args.password)
        process = subprocess.run([args.psql,'-h',args.host,'-p',str(args.port),'-U',args.user,'-d',args.database,
            '-X','-qAt','-v','ON_ERROR_STOP=1','-v','VERBOSITY=verbose','-f','-'],
            input=sql,capture_output=True,text=True,encoding='utf-8',env=env)
        if process.returncode:
            code = re.search(r'(?:ERROR|FATAL):\s+([A-Z0-9]{5}):',process.stderr)
            if not code: raise RuntimeError(process.stderr)
            message = process.stderr[code.end():].splitlines()[0].strip()
            raise SqlError(code.group(1), message)
        return SimpleNamespace(data=json.loads(process.stdout))


class Query:
    def __init__(self, client, table):
        self.client, self.table_name = client, identifier(table)
        self.operation, self.filters, self.sort, self.lim, self.offset = 'select', [], '', '', ''
        self.body = None
    def select(self, _columns): return self
    def eq(self, key, value):
        self.filters.append(identifier(key)+'='+literal(value)); return self
    def order(self, key, desc=False):
        self.sort=' order by '+identifier(key)+(' desc' if desc else ''); return self
    def limit(self, limit): self.lim=' limit '+str(int(limit)); return self
    def range(self, start, end):
        self.offset=' offset '+str(int(start)); return self.limit(end-start+1)
    def insert(self, body): self.operation='insert'; self.body=body; return self
    def update(self, body): self.operation='update'; self.body=body; return self
    def delete(self): self.operation='delete'; return self
    def execute(self):
        table = 'public.'+self.table_name
        where = ' where '+' and '.join(self.filters) if self.filters else ''
        if self.operation == 'select':
            query = 'select * from '+table+where+self.sort+self.lim+self.offset
            return self.client.execute("select coalesce(jsonb_agg(to_jsonb(r)),'[]'::jsonb) from ("+query+') r')
        if self.operation == 'delete': query = 'delete from '+table+where
        elif self.operation == 'insert':
            keys = ','.join(identifier(k) for k in self.body)
            query = 'insert into '+table+' ('+keys+') select '+keys+' from jsonb_populate_record(null::'+table+','+literal(json.dumps(self.body))+'::jsonb)'
        else:
            setters = ','.join(identifier(k)+'=r.'+identifier(k) for k in self.body)
            query = 'update '+table+' t set '+setters+' from jsonb_populate_record(null::'+table+','+literal(json.dumps(self.body))+'::jsonb) r'
            query += ' where '+' and '.join('t.'+clause for clause in self.filters)
        return self.client.execute("with r as ("+query+" returning *) select coalesce(jsonb_agg(to_jsonb(r)),'[]'::jsonb) from r")


def validate_identity(args):
    auth_ids = {role:str(uuid4()) for role in ('owner','other','admin')}
    readers = {role:LocalClient(args,'authenticated',uid) for role,uid in auth_ids.items()}
    readers['anon'] = LocalClient(args,'anon')
    fixtures = IdentityFixtures(LocalClient(args),readers,auth_ids)
    try: fixtures.run()
    finally: fixtures.cleanup()
    print(f'Identity PostgreSQL RESULT ok checks={len(fixtures.checks)}',flush=True)
