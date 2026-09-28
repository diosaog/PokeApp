"""Opt-in hosted HTTPS validation; real PIN/JWT/PostgREST and isolated browser.

Requires Supabase CLI authentication for fresh read-only full-state evidence.
Never reapplies migrations, alters grants, uploads saves or uses real data as fixtures.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import subprocess
import traceback
from uuid import uuid4

import httpx
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions

from app.auth.credentials import build_internal_auth_credential
from app.application.pokemon_identity import reconcile_parsed_save
from app.domain.common import to_jsonable
from app.domain.pokemon import PrivatePokemon, PokemonMove
from app.domain.pokemon_identity import PokemonIdentityEvidence, CaptureOrder
from app.repositories.supabase.pokemon_identity import SupabasePokemonIdentityRepository
from tools.validate_cup_fixtures import CupFixtures, require
from tools.validate_supabase_v2_cups import CupApiTransport
from tools.validate_supabase_v2_matchdays import MatchdayApiTransport
from tools.validate_supabase_v2_rls import SupabaseHttp
from tools.validate_supabase_v2_season_admin import ApiTransport
from tools.validate_supabase_v2_team_lock import staging_config

ROOT = Path(__file__).resolve().parents[1]
REF = 'uwleqeuzsveqlugugzba'
API = 'https://pokeapp-api-production.up.railway.app'
WEB = 'https://pokeapp-web.pokeapp-v2.workers.dev'
HISTORY = 'select version,name,md5(to_jsonb(m)::text) as record_hash from supabase_migrations.schema_migrations m order by version'
TABLES = """select table_schema as s,table_name as t from information_schema.tables
where table_type='BASE TABLE' and (table_schema='public' or
(table_schema='auth' and table_name in ('users','identities','sessions','refresh_tokens')) or
(table_schema='storage' and table_name in ('buckets','objects'))) order by table_schema,table_name"""


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


def cli(args):
    result = subprocess.run(['npx.cmd' if os.name == 'nt' else 'npx', '--no-install', 'supabase', *args],
                            cwd=ROOT, capture_output=True, text=True, encoding='utf-8', timeout=180)
    require(result.returncode == 0, 'Supabase CLI failed; output suppressed')
    return json.loads(result.stdout)


def query(out, name, sql):
    path = out/(name+'.sql')
    path.write_text(sql, encoding='utf-8')
    rows = cli(['db', 'query', '--linked', '--project-ref', REF, '--file', str(path), '-o', 'json'])['rows']
    write(out/(name+'.json'), rows)
    return rows


def snapshot(out, name, owner_auth_user=None):
    tables = query(out, name+'-tables', TABLES)
    selects = []
    for table in tables:
        qualified = '.'.join('"'+table[k].replace('"', '""')+'"' for k in ('s', 't'))
        label = table['s']+'.'+table['t']
        clause = ''
        if owner_auth_user and table['s'] == 'auth':
            from uuid import UUID
            uid = str(UUID(owner_auth_user))
            column = 'id' if table['t'] == 'users' else 'user_id'
            clause = f" where {column}::text is distinct from '{uid}'"
        selects.append("select '"+label+"' as name,count(*) as rows,encode(sha256(convert_to("
                       "coalesce(jsonb_agg(to_jsonb(t) order by to_jsonb(t)::text)::text,'[]'),'UTF8')),"
                       "'hex') as sha256 from "+qualified+' t'+clause)
    return query(out, name, '\nunion all\n'.join(selects)+'\norder by name')


def advisors(out, name):
    data = cli(['db', 'advisors', '--linked', '--project-ref', REF, '--type', 'all',
                '--level', 'info', '--fail-on', 'none', '-o', 'json'])
    write(out/(name+'.json'), data)
    return data


def significant(data):
    # Preserve object/finding identity, not only aggregate counts.
    return {json.dumps({k: r.get(k) for k in ('name', 'level', 'metadata', 'cache_key')}, sort_keys=True)
            for r in data if r.get('level') in ('ERROR', 'WARN')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--allow-staging-writes', action='store_true')
    parser.add_argument('--owner-auth-user', help='Explicit persistent owner staging Auth exception; never cleaned')
    args = parser.parse_args()
    out = args.output.resolve()
    require(not out.exists(), 'Use a new evidence directory')
    out.mkdir(parents=True)
    cfg = replace(staging_config(args.env_file, args.allow_staging_writes), run_id='phase10_hosted_'+uuid4().hex)
    pepper = os.environ.get('POKEAPP_AUTH_PIN_PEPPER', '')
    require(bool(pepper), 'Supply deployed PIN pepper privately in environment')
    projects = cli(['projects', 'list', '-o', 'json'])
    require(any(p['id'] == REF and p['linked'] for p in projects), 'Wrong linked V2 project')
    history = query(out, 'history-before', HISTORY)
    require(history[-2]['version'] == '20260928110301' and history[-1]['version'] == '20260928111840', 'Unexpected migration history')
    before = snapshot(out, 'baseline-before', args.owner_auth_user)
    require(next(x for x in before if x['name'] == 'auth.users')['rows'] == 0, 'Unexpected non-owner Auth identities; investigate before fixtures')
    if args.owner_auth_user:
        from uuid import UUID
        uid = str(UUID(args.owner_auth_user))
        owner = query(out, 'owner-exception', "select id,slug,globally_enabled,auth_user_id from public.trainers where auth_user_id='"+uid+"'::uuid")
        require(len(owner) == 1 and owner[0]['slug'] == 'anto' and owner[0]['globally_enabled'], 'Owner exception identity mismatch')
    advisor_before = advisors(out, 'advisors-before')
    report = dict(run_id=cfg.run_id, started_at=datetime.now(timezone.utc).isoformat(),
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  api=API, web=WEB, project_ref=REF, checks=[], status='RUNNING', users=[], trainers=[], seasons=[])
    report['owner_exception'] = {'marker': 'OWNER_TEMP_STAGING_AUTH', 'auth_user_id': args.owner_auth_user,
                                'excluded_from_comparison': 'Only this owner Auth row/identities/sessions/refresh tokens; all public rows fully compared'} if args.owner_auth_user else None

    def save():
        write(out/'result.json', report)

    def passed(name):
        report['checks'].append(name)
        save()
        print('PASS '+name, flush=True)

    transport = httpx.Client(timeout=60, http2=False)
    client = create_client(cfg.url, cfg.service_role_key, options=SyncClientOptions(httpx_client=transport))
    api = httpx.Client(base_url=API, timeout=60, follow_redirects=False, headers={'Origin': WEB})
    fixtures = CupFixtures(client, {}, dict(admin=None, other=None, owner=None), cfg.run_id)
    http = SupabaseHttp(cfg)
    tokens = {}
    pins = {}
    failure = None
    save()

    def request(method, path, body=None, actor=None, status=200, key=None):
        headers = {}
        if actor:
            headers['Authorization'] = 'Bearer '+tokens[actor]
        if key:
            headers['Idempotency-Key'] = key
        r = api.request(method, path, json=body, headers=headers)
        require(r.status_code == status, f'{method} {path}: HTTP {r.status_code}, expected {status}')
        if path.startswith('/v1/'):
            require(r.headers.get('cache-control') == 'no-store', 'Private response cache policy')
            require(r.headers.get('access-control-allow-origin') == WEB, 'Actual response CORS')
        return r.json()

    try:
        require(api.get('/health').status_code == 200, 'Hosted health')
        for origin, expected in ((WEB, 200), ('https://untrusted.invalid', 400)):
            r = api.options('/v1/me', headers={'Origin': origin, 'Access-Control-Request-Method': 'GET',
                                              'Access-Control-Request-Headers': 'Authorization'})
            require(r.status_code == expected, 'CORS preflight')
            require(r.headers.get('access-control-allow-origin') == (WEB if expected == 200 else None), 'CORS allowlist')
        request('GET', '/v1/me', status=401)
        passed('Hosted HTTPS, liveness, anonymous denial, exact allowed/rejected CORS and no-store')
        fixtures.setup()
        report['trainers'] = [t['id'] for t in fixtures.trainers]
        save()
        for trainer in fixtures.trainers[:4]:
            tid = trainer['id']
            pins[tid] = str(secrets.randbelow(10000)).zfill(4)
            credential = build_internal_auth_credential(tid, pins[tid], pepper)
            uid = http.auth_create_user(credential.email, credential.password)
            report['users'].append(uid)
            save()
            client.table('trainers').update({'auth_user_id': uid}).eq('id', tid).execute()
            login = request('POST', '/v1/auth/pin-login', {'trainer_identifier': trainer['slug'], 'pin': pins[tid]})
            require(login['trainer_id'] == tid, 'PIN actor mapping')
            refreshed = request('POST', '/v1/auth/refresh', {'refresh_token': login['session']['refresh_token']})
            tokens[tid] = refreshed['session']['access_token']
            require(request('GET', '/v1/me', actor=tid)['trainer_id'] == tid, 'JWT actor mapping')
        passed('Four real PIN logins, refresh sessions and verified JWT trainer mapping')
        admin, owner = fixtures.admin['id'], fixtures.owner['id']
        wrong = str((int(pins[admin])+1) % 10000).zfill(4)
        request('POST', '/v1/auth/pin-login', {'trainer_identifier': fixtures.admin['slug'], 'pin': wrong}, status=401)
        disabled = fixtures.trainers[3]
        client.table('trainers').update({'globally_enabled': False}).eq('id', disabled['id']).execute()
        request('GET', '/v1/read/seasons', actor=disabled['id'], status=403)
        request('POST', '/v1/auth/pin-login', {'trainer_identifier': disabled['slug'], 'pin': pins[disabled['id']]}, status=401)
        client.table('trainers').update({'globally_enabled': True}).eq('id', disabled['id']).execute()
        # Point one disposable trainer at another disposable Auth identity; its
        # own correct PIN must not authenticate through the mismatched mapping.
        mapped = fixtures.rows('trainers', id=disabled['id'])[0]['auth_user_id']
        alternate = fixtures.rows('trainers', id=fixtures.admin2['id'])[0]['auth_user_id']
        client.table('trainers').update({'auth_user_id': None}).eq('id', fixtures.admin2['id']).execute()
        client.table('trainers').update({'auth_user_id': alternate}).eq('id', disabled['id']).execute()
        request('POST', '/v1/auth/pin-login', {'trainer_identifier': disabled['slug'], 'pin': pins[disabled['id']]}, status=401)
        client.table('trainers').update({'auth_user_id': mapped}).eq('id', disabled['id']).execute()
        client.table('trainers').update({'auth_user_id': alternate}).eq('id', fixtures.admin2['id']).execute()
        passed('Wrong PIN, disabled trainer and mismatched Auth mapping all denied through public API')
        fixtures.repo = ApiTransport(lambda: api, tokens)
        fixtures.matchdays = MatchdayApiTransport(lambda: api, tokens)
        fixtures.cups = CupApiTransport(lambda: api, tokens)
        fixtures.validates_request_schema = True
        request('POST', '/v1/admin/seasons', {'name': cfg.run_id}, actor=owner, status=403, key=uuid4().hex)
        sid = fixtures.draft()
        report['seasons'] = fixtures.seasons
        save()
        # Renaming is a draft-only command; exercise its CAS before activation.
        key = uuid4().hex
        setup = fixtures.state(sid)
        body = dict(name=cfg.run_id+' renamed', expected_revision=setup['setup_revision'])
        first = fixtures.call('rename', sid, body, key=key)
        replay = fixtures.call('rename', sid, body, key=key)
        require(first['operation_id'] == replay['operation_id'], 'Hosted idempotency replay')
        request('PUT', f'/v1/admin/seasons/{sid}/name', body, actor=admin, key=uuid4().hex, status=409)
        passed('Real admin authority, durable idempotency replay and stale revision conflict')
        for trainer in fixtures.trainers[:4]:
            fixtures.add(sid, trainer['id'])
        config = fixtures.config(sid)
        config.update(total_matchdays=2, rules={'team_lock_required': True, 'last_b_gets_steal': False})
        cid = fixtures.call('create_config', sid, config)['resource_id']
        fixtures.call('initial_divisions', sid, fixtures.divisions_body(sid, cid))
        for op in ('prepare', 'activate'):
            fixtures.call(op, sid, {'expected_setup_revision': fixtures.state(sid)['setup_revision']})
        day = fixtures.state(sid)['current_matchday_id']
        fixtures.open(sid, day)
        for i, trainer in enumerate(fixtures.trainers[:4]):
            tid = trainer['id']
            player = fixtures.rows('season_players', season_id=sid, trainer_id=tid)[0]
            source_hash = hashlib.sha256(tid.encode()).hexdigest()
            record = fixtures.insert('save_files', dict(season_id=sid, trainer_id=tid,
                storage_key=cfg.run_id+'/'+str(i)+'.sav', original_filename='synthetic.sav',
                sha256=source_hash, parser_status='parsed', parser_version='phase10-fixture-v1'))
            pokemon = to_jsonable(PrivatePokemon(species='Milotic', nickname='Synthetic '+str(i), level=50,
                                  ability='Escama Especial', moves=(PokemonMove('Surf'),)))
            payload = dict(party=[dict(slot_number=s, pokemon={**pokemon, 'legacy_fingerprints': [],
                'identity_evidence': asdict(PokemonIdentityEvidence(1, 5, i*100+s, 12345, 6789, 20, 2,
                                                                   'Synthetic', 0, ivs=(0,)*6))}) for s in range(1, 7)], boxes=[])
            parsed = fixtures.insert('parsed_saves', dict(save_file_id=record['id'], parser_version='phase10-fixture-v1', payload=payload))
            # Synthetic trusted capture order in the fixture only. The production
            # parser/Launcher still does not invent an upload or current pointer.
            reconcile_parsed_save(SupabasePokemonIdentityRepository(client), season_id=sid, trainer_id=tid,
                                  parsed_save_id=parsed['id'], capture_order=CaptureOrder(str(uuid4()), 1))
            client.table('season_players').update({'current_save_file_id': record['id']}).eq('id', player['id']).execute()
            fixtures.insert('coin_transactions', dict(season_id=sid, trainer_id=tid, season_player_id=player['id'],
                            amount=1000, transaction_type='admin_adjustment', metadata={'validation_run': cfg.run_id}))
            request('PUT', f'/v1/seasons/{sid}/matchdays/{day}/team-lock', {'save_file_id': record['id']}, actor=tid)
        fixtures.results(sid, day)
        fixtures.close(sid, day)
        day2 = fixtures.state(sid)['current_matchday_id']
        fixtures.open(sid, day2)
        passed('Hosted admin setup/activation, four Team Locks, day results/close and official history')
        for endpoint in ('overview', 'pc', 'shop', 'inventory'):
            request('GET', f'/v1/read/seasons/{sid}/{endpoint}', actor=admin)
        own_pc = request('GET', f'/v1/read/seasons/{sid}/pc', actor=owner)
        require(all(p['pokemon']['nickname'] == 'Synthetic 2' for p in own_pc['pokemon']) and len(own_pc['pokemon']) == 6, 'Private PC owner scope')
        passed('Typed overview/shop/inventory and real private PC owner isolation')
        doubles = fixtures.create_cup(sid, fmt='doubles', n=2)
        fixtures.finish_cup(sid, doubles)
        cup = fixtures.create_cup(sid, fmt='elimination', n=4)
        hall = request('GET', '/v1/read/hall', actor=admin)
        entry = next(x for x in hall['items'] if x['cup_id'] == doubles)
        winner = next(s for s in entry['cup_sides'] if s['id'] == entry['champion_side_id'])
        require(entry['champion_trainer_id'] is None and len(winner['members']) == 2, 'Doubles Hall')
        trial = request('POST', f'/v1/seasons/{sid}/trials', dict(title='Hosted Discord agreement',
            description='Synthetic hosted validation', is_public=True, evidence='Synthetic evidence',
            accused_trainer_id=owner), actor=admin, key=uuid4().hex)
        passed('Hosted doubles Bo3/certification/Hall and manual judicial proposal')
        data = dict(web=WEB, api=API, trainer=fixtures.admin['slug'], pin=pins[admin], season=sid,
                    cup=cup, doubles=doubles, trial=trial['case_id'], output=str(out))
        result = subprocess.run(['node', 'scripts/validate-hosted.mjs'], cwd=ROOT/'web',
                                input=json.dumps(data), capture_output=True, text=True, encoding='utf-8', timeout=600)
        log = result.stdout+'\n'+result.stderr
        for pin in pins.values():
            log = log.replace(pin, '[REDACTED]')
        (out/'browser.log').write_text(log, encoding='utf-8')
        require(result.returncode == 0, 'Hosted browser validation failed; inspect sanitized browser.log')
        passed('Real Cloudflare browser: login, all screens, PC dialog, Team Lock, purchase, Cup result, judicial decision and logout')
        detail = request('GET', f'/v1/seasons/{sid}/trials/{trial["case_id"]}', actor=admin)
        require(detail['verdict'] == 'guilty', 'Browser judicial mutation persisted')
        require(len(fixtures.rows('purchases', season_id=sid, trainer_id=admin)) == 1, 'Browser purchase persisted once')
        passed('Independent server readback confirms browser mutations')
    except Exception as exc:
        last = traceback.extract_tb(exc.__traceback__)[-1]
        failure = type(exc).__name__+' at '+Path(last.filename).name+':'+str(last.lineno)
        if isinstance(exc, AssertionError):
            failure += ': '+str(exc)
        elif hasattr(exc, 'code'):
            failure += ': '+str(exc.code)
        report['failure'] = failure
        print('FAIL '+failure, flush=True)
    finally:
        try:
            for sid in fixtures.seasons:
                for table in ('coin_transactions', 'penalties', 'trial_case_revisions', 'trial_case_counters'):
                    client.table(table).delete().eq('season_id', sid).execute()
            fixtures.cleanup()
            for uid in report['users']:
                http.auth_delete_user(uid)
                require(http.request('GET', http.auth_url+'/admin/users/'+uid, auth='service', raise_on_error=False).status == 404, 'Auth cleanup')
            report['fixture_cleanup'] = 'PASS'
        except Exception as exc:
            report['cleanup_failure'] = type(exc).__name__
            failure = failure or 'Fixture cleanup failed'
        api.close()
        transport.close()
        save()
        after = snapshot(out, 'baseline-after', args.owner_auth_user)
        after_history = query(out, 'history-after', HISTORY)
        after_advisor = advisors(out, 'advisors-after')
        report['baseline_tables'] = len(before)
        report['zero_residue'] = before == after
        report['migration_history_unchanged'] = history == after_history
        report['new_advisor_error_warn'] = sorted(significant(after_advisor)-significant(advisor_before))
        clean = report['zero_residue'] and report['migration_history_unchanged'] and not report['new_advisor_error_warn']
        report['status'] = 'PASS' if not failure and clean else 'FAIL'
        report['finished_at'] = datetime.now(timezone.utc).isoformat()
        save()
    print('RESULT '+report['status']+'; full-state cleanup='+str(report['zero_residue']), flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
