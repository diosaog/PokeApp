"""Focused ORAS synthetic integration on disposable LOCAL PostgreSQL only.

No authentic gameplay fixture is claimed. Reuses production parser, registration,
read projections and Launcher journal; external Auth/Storage are local substitutes.
"""
# ruff: noqa: E402
import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app.api.main  # noqa: F401 -- initialize the existing API package before its services
from app.application.frontend_reads import FrontendReads
from app.application.save_ingestion import TrustedSaveIngestion
from app.launcher.core import LauncherCore
from app.launcher.runtime import LauncherRuntime
from app.repositories.supabase.frontend_reads import SupabaseFrontendReadRepository
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.adapter import PkhexProcessParser, SaveInspector
from app.save_parser.registration import observation_digest
from tools.validate_phase16d_save_sync import Client, RawRepository
from tools.validate_supabase_v2_identity_sql import SqlError, literal
from tools.validate_supabase_v2_schema import MIGRATIONS, BOOTSTRAP_SQL, SUPABASE_ROLE_MOCK_SQL


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--pg-bin', type=Path, required=True)
    cli.add_argument('--port', type=int, required=True)
    cli.add_argument('--parser', type=Path, required=True)
    cli.add_argument('--fixtures', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    args = cli.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    db = 'pokeapp_v2_validation_phase18_' + uuid4().hex[:12]
    created = []

    def run(program, database, tail, query=None):
        cmd = [str(args.pg_bin / (program + '.exe')), '-h', '127.0.0.1', '-p', str(args.port), '-U', 'postgres']
        if program in ('psql', 'pg_dump'):
            cmd += ['-d', database]
        r = subprocess.run(cmd + tail, input=query, capture_output=True, text=True,
                           encoding='utf-8', env=dict(os.environ, PGCLIENTENCODING='UTF8'))
        if r.returncode:
            raise RuntimeError(r.stderr)
        return r.stdout.strip()

    def sql(query, database=db):
        return run('psql', database, ['-X', '-qAt', '-v', 'ON_ERROR_STOP=1', '-f', '-'], query)

    def scalar(query):
        return json.loads(sql(query))

    def snapshot():
        tables = scalar("select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'")
        parts = [f"select '{t}' name, md5(coalesce(jsonb_agg(to_jsonb(t) order by to_jsonb(t)::text),'[]')::text) hash from public.{t} t" for t in tables]
        return scalar('select jsonb_object_agg(name,hash) from (' + ' union all '.join(parts) + ') q')

    try:
        for name, sources in ((db, MIGRATIONS), (db + '_bootstrap', [BOOTSTRAP_SQL])):
            run('createdb', 'postgres', [name])
            created.append(name)
            sql(SUPABASE_ROLE_MOCK_SQL, name)
            for source in sources:
                sql(source.read_text(encoding='utf-8'), name)
        dumps = ['\n'.join(line for line in run('pg_dump', name, ['--schema-only', '--schema=public', '--schema=v1_shadow']).splitlines()
                           if not line.startswith(('\\restrict ', '\\unrestrict '))) for name in created]
        assert dumps[0] == dumps[1], 'bootstrap parity'
        before = snapshot()
        sid = str(uuid4())
        sql(f"insert into public.seasons(id,name,status,started_at) values('{sid}','Phase18 disposable','active',now())")
        local = SimpleNamespace(psql=str(args.pg_bin / 'psql.exe'), host='127.0.0.1', port=args.port,
                                user='postgres', password='', database=db)
        client = Client(local)
        repo = RawRepository(client, args.output / 'storage')
        parser = PkhexProcessParser(args.parser)
        service = TrustedSaveIngestion(repo, parser)
        reads = FrontendReads(SupabaseFrontendReadRepository(client))
        tids = []
        evidence = {}
        for game, folder in (('OR', 'oras'), ('AS', 'oras'), ('X', 'xy'), ('Y', 'xy')):
            tid, rival = str(uuid4()), str(uuid4())
            tids += [tid, rival]
            sql(f"insert into public.trainers(id,display_name,slug) values('{tid}','Fixture {game}','{tid}'),('{rival}','Other {game}','{rival}'); "
                f"insert into public.season_players(season_id,trainer_id) values('{sid}','{tid}'),('{sid}','{rival}')")
            source = args.fixtures / folder / game / 'main'
            raw = source.read_bytes()
            original_hash = sha256(raw).hexdigest()
            obs = parser.parse(raw)
            digest = observation_digest(obs, parser.version)
            assert obs.game == game and obs.progress is None
            send = lambda: service.receive(sid, tid, original_hash, None, digest, raw)
            with ThreadPoolExecutor(max_workers=2) as pool:
                receipts = list(pool.map(lambda _: send(), range(2)))
            assert receipts[0] == receipts[1]
            accepted = snapshot()
            assert send() == receipts[0] and snapshot() == accepted
            pc = reads.pc(sid, tid)
            public = reads.trainer_collection(sid, tid)
            assert pc.status == public.status == 'ready' and pc.save.game == public.game == game
            assert len(pc.pokemon) == len(public.pokemon) == len(list(obs.occupied()))
            assert all(p.pokemon_entity_id is None for p in pc.pokemon)
            forbidden = {'ivs', 'evs', 'ability', 'nature', 'identity_evidence', 'pokemon_entity_id', 'trainer'}
            assert all(not forbidden.intersection(p.pokemon.model_dump()) for p in public.pokemon)
            assert all(p.pokemon.ivs is not None for p in pc.pokemon)
            if game in ('OR', 'AS'):
                assert public.pokemon[0].pokemon.form == 1
                assert public.pokemon[0].pokemon.types == ['Type #12', 'Type #9']
                assert public.pokemon[0].pokemon.moves[0].name == 'Move #621'
                assert any(p.location == 'Caja 8 · 1' for p in public.pokemon)
                later = (source.parent / 'later').read_bytes()
                latest = service.receive(sid, tid, sha256(later).hexdigest(), receipts[0].save_id,
                                         observation_digest(parser.parse(later), parser.version), later)
                assert latest.is_current and not send().is_current
                assert str(reads.pc(sid, tid).save.id) == latest.save_id
            accepted = snapshot()
            for target, expected, candidate in ((rival, None, raw),
                (tid, str(reads.pc(sid, tid).save.id), (args.fixtures / ('xy' if folder == 'oras' else 'oras') / ('X' if folder == 'oras' else 'OR') / 'main').read_bytes())):
                try:
                    service.receive(sid, target, sha256(candidate).hexdigest(), expected,
                                    observation_digest(parser.parse(candidate), parser.version), candidate)
                except SeasonAdminRejected:
                    pass
                else:
                    raise AssertionError('cross-owner/game accepted')
            assert snapshot() == accepted
            # Failed transaction must leave every public table unchanged.
            request = repo.last.copy()
            request.update(save_id=str(uuid4()), parsed_id=str(uuid4()), sha256='f'*64,
                           expected_save_id=str(reads.pc(sid, tid).save.id), trainer_id=tid)
            request['storage_key'] = f'trusted/{tid}/{sid}/' + 'f'*64 + '.sav'
            request['payload'] = request['payload'] | {'save_record_id':request['save_id'], 'trainer_id':tid, 'source_hash':'f'*64}
            # Last request may be the rejected other owner; take original identity/payload from this game's parse.
            from app.application.save_ingestion import parsed_payload
            request['payload'] = parsed_payload(obs, request['save_id'], tid, 'f'*64)
            request['save_identity'] = {'game':game, 'trainer':obs.trainer.model_dump(mode='json')}
            try:
                sql("do $x$ begin perform public.api_register_save(" + literal(json.dumps(request | {'operation':'register'})) + "::jsonb); perform 1/0; end $x$;")
            except RuntimeError as error:
                assert 'division by zero' in str(error)
            else:
                raise AssertionError('rollback not exercised')
            assert snapshot() == accepted
            core = LauncherCore(args.output / ('local-' + game), SaveInspector(parser))
            core.select(source)
            assert core.manual_sync().status == 'SYNCED' and core.manual_sync().status == 'NO_CHANGE'
            runtime = LauncherRuntime(args.output / ('local-' + game), SaveInspector(parser), start=False)
            try:
                assert runtime.state()['observation']['game'] == game
                assert runtime.state()['cloud_status'] == 'OFFLINE'
            finally:
                runtime.close()
            assert sha256(source.read_bytes()).hexdigest() == original_hash
            evidence[game] = {'synthetic':True, 'import':True, 'replay_concurrency':True, 'privacy':True,
                              'offline_cache':True, 'source_unchanged':True, 'slots':len(pc.pokemon)}
        for role in ('anon', 'authenticated'):
            try:
                Client(local, role).execute("select public.api_register_save('{}')")
            except SqlError as error:
                assert error.code == '42501'
            else:
                raise AssertionError('browser RPC allowed')
        for table in ('pokemon_identity_revisions','pokemon_entities','progress_reward_claims','coin_transactions','team_locks'):
            assert scalar(f'select count(*) from public.{table}') == 0
        sql(f"update public.season_players set current_save_file_id=null where season_id='{sid}'; "
            f"delete from public.parsed_saves where save_file_id in(select id from public.save_files where season_id='{sid}'); "
            f"delete from public.save_files where season_id='{sid}'; delete from public.season_players where season_id='{sid}'; "
            f"delete from public.seasons where id='{sid}'; delete from public.trainers where id in ({','.join(literal(t) for t in tids)})")
        assert snapshot() == before
        report = {'status':'PASS_SYNTHETIC_ONLY','authentic_oras':'NOT_RUN_OWNER_WAIVER',
                  'games':evidence,'tables_restored':len(before),'bootstrap_parity':True,'migration':45,'remote_writes':0}
        (args.output / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report))
    finally:
        for name in reversed(created):
            run('dropdb', 'postgres', [name])


if __name__ == '__main__':
    main()
