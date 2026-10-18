"""Focused Ultra Sun/Ultra Moon integration on disposable LOCAL PostgreSQL only.

Default fixtures are synthetic. --public-fixtures uses the pinned contributor
saves described in tests/fixtures/phase20-public-saves.json. External Auth/Storage
remain local substitutes; neither mode writes to hosted services.
"""

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from hashlib import sha256
from pathlib import Path
from threading import Lock
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
from tools.validate_supabase_v2_schema import (
    BOOTSTRAP_SQL,
    MIGRATIONS,
    SUPABASE_ROLE_MOCK_SQL,
)


class FixtureRawRepository(RawRepository):
    """Model atomic object visibility without serializing database commands."""

    def __init__(self, client, folder):
        super().__init__(client, folder)
        self.object_lock = Lock()

    def store_raw(self, key, data, raw_hash):
        # Plain local files become visible before their writer finishes. Hosted
        # object PUT does not; don't mistake that fixture-only race for replay.
        with self.object_lock:
            super().store_raw(key, data, raw_hash)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--pg-bin", type=Path, required=True)
    cli.add_argument("--port", type=int, required=True)
    cli.add_argument("--parser", type=Path, required=True)
    cli.add_argument("--fixtures", type=Path, required=True)
    cli.add_argument("--public-fixtures", action="store_true")
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    if args.public_fixtures:
        manifest = json.loads(
            (ROOT / "tests/fixtures/phase20-public-saves.json").read_text(
                encoding="utf-8"
            )
        )
        for fixture in manifest["fixtures"]:
            assert (
                sha256((args.fixtures / fixture["file"]).read_bytes()).hexdigest()
                == fixture["sha256"]
            ), fixture["file"]
    db = "pokeapp_v2_validation_phase20_" + uuid4().hex[:12]
    created = []

    def run(program, database, tail, query=None):
        cmd = [
            str(args.pg_bin / (program + ".exe")),
            "-h",
            "127.0.0.1",
            "-p",
            str(args.port),
            "-U",
            "postgres",
        ]
        if program in ("psql", "pg_dump"):
            cmd += ["-d", database]
        r = subprocess.run(
            cmd + tail,
            check=False,
            input=query,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=dict(os.environ, PGCLIENTENCODING="UTF8"),
        )
        if r.returncode:
            raise RuntimeError(r.stderr)
        return r.stdout.strip()

    def sql(query, database=db):
        return run(
            "psql", database, ["-X", "-qAt", "-v", "ON_ERROR_STOP=1", "-f", "-"], query
        )

    def scalar(query):
        return json.loads(sql(query))

    def snapshot():
        tables = scalar(
            "select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'"
        )
        parts = [
            f"select '{t}' name, md5(coalesce(jsonb_agg(to_jsonb(t) order by to_jsonb(t)::text),'[]')::text) hash from public.{t} t"
            for t in tables
        ]
        return scalar(
            "select jsonb_object_agg(name,hash) from ("
            + " union all ".join(parts)
            + ") q"
        )

    try:
        # Full chain parity was already proved on the same application source.
        # Public-fixture follow-up only needs one fresh disposable schema.
        builds = (
            ((db, [BOOTSTRAP_SQL]),)
            if args.public_fixtures
            else ((db, MIGRATIONS), (db + "_bootstrap", [BOOTSTRAP_SQL]))
        )
        for name, sources in builds:
            run("createdb", "postgres", [name])
            created.append(name)
            sql(SUPABASE_ROLE_MOCK_SQL, name)
            for source in sources:
                sql(source.read_text(encoding="utf-8"), name)
        if not args.public_fixtures:
            dumps = [
                "\n".join(
                    line
                    for line in run(
                        "pg_dump",
                        name,
                        ["--schema-only", "--schema=public", "--schema=v1_shadow"],
                    ).splitlines()
                    if not line.startswith(("\\restrict ", "\\unrestrict "))
                )
                for name in created
            ]
            assert dumps[0] == dumps[1], "bootstrap parity"
        before = snapshot()
        sid = str(uuid4())
        sql(
            f"insert into public.seasons(id,name,status,started_at) values('{sid}','Phase20 disposable','active',now())"
        )
        local = SimpleNamespace(
            psql=str(args.pg_bin / "psql.exe"),
            host="127.0.0.1",
            port=args.port,
            user="postgres",
            password="",
            database=db,
        )
        client = Client(local)
        repo = FixtureRawRepository(client, args.output / "storage")
        parser = PkhexProcessParser(args.parser)
        service = TrustedSaveIngestion(repo, parser)
        reads = FrontendReads(SupabaseFrontendReadRepository(client))
        tids = []
        evidence = {}
        cases = (
            (("US", "US/main", None), ("UM", "UM/main", None))
            if args.public_fixtures
            else (
                ("US", "usum/US/main", "usum/US/later"),
                ("UM", "usum/UM/main", "usum/UM/later"),
                ("SN", "sm/SN/main", "sm/SN/later"),
                ("MN", "sm/MN/main", "sm/MN/later"),
                ("OR", "oras/OR/main", "oras/OR/later"),
                ("AS", "oras/AS/main", "oras/AS/later"),
                ("X", "xy/X/main", None),
                ("Y", "xy/Y/main", None),
            )
        )
        for game, relative, later_relative in cases:
            tid, rival = str(uuid4()), str(uuid4())
            tids += [tid, rival]
            sql(
                f"insert into public.trainers(id,display_name,slug) values('{tid}','Fixture {game}','{tid}'),('{rival}','Other {game}','{rival}'); "
                f"insert into public.season_players(season_id,trainer_id) values('{sid}','{tid}'),('{sid}','{rival}')"
            )
            source = args.fixtures / relative
            raw = source.read_bytes()
            original_hash = sha256(raw).hexdigest()
            obs = parser.parse(raw)
            digest = observation_digest(obs, parser.version)
            assert obs.game == game and obs.progress is None
            send = partial(service.receive, sid, tid, original_hash, None, digest, raw)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(send) for _ in range(2)]
                receipts = [future.result() for future in futures]
            assert receipts[0] == receipts[1]
            accepted = snapshot()
            assert send() == receipts[0] and snapshot() == accepted
            pc = reads.pc(sid, tid)
            public = reads.trainer_collection(sid, tid)
            assert (
                pc.status == public.status == "ready"
                and pc.save.game == public.game == game
            )
            assert len(pc.pokemon) == len(public.pokemon) == len(list(obs.occupied()))
            assert all(p.pokemon_entity_id is None for p in pc.pokemon)
            forbidden = {
                "ivs",
                "evs",
                "ability",
                "nature",
                "identity_evidence",
                "pokemon_entity_id",
                "trainer",
            }
            assert all(
                not forbidden.intersection(p.pokemon.model_dump())
                for p in public.pokemon
            )
            assert all(p.pokemon.ivs is not None for p in pc.pokemon)
            if args.public_fixtures:
                expected_count = next(
                    f["occupied_slots"]
                    for f in manifest["fixtures"]
                    if f["game"] == game
                )
                assert len(pc.pokemon) == expected_count
                for slot, (_, native) in zip(
                    public.pokemon, obs.occupied(), strict=True
                ):
                    assert slot.pokemon.form == native.form
                    assert slot.pokemon.species == f"Pokémon #{native.species_id}"
                    assert slot.pokemon.level == native.level
                    assert slot.pokemon.types == list(
                        dict.fromkeys(f"Type #{t}" for t in native.type_ids)
                    )
                    assert [m.name for m in slot.pokemon.moves] == [
                        f"Move #{m.id}" for m in native.moves if m.id
                    ]
            elif game in ("US", "UM"):
                assert len(obs.boxes) == 32
                assert public.pokemon[0].pokemon.form == 1
                assert public.pokemon[0].pokemon.types == ["Type #13", "Type #8"]
                assert public.pokemon[0].pokemon.moves[0].name == "Move #728"
                assert any(p.location == "Caja 32 · 30" for p in public.pokemon)
            elif game in ("SN", "MN"):
                assert len(obs.boxes) == 32
                assert public.pokemon[0].pokemon.form == 1
                assert public.pokemon[0].pokemon.types == ["Type #12", "Type #13"]
                assert public.pokemon[0].pokemon.moves[0].name == "Move #719"
                assert any(p.location == "Caja 32 · 30" for p in public.pokemon)
            elif game in ("OR", "AS"):
                assert public.pokemon[0].pokemon.form == 1
                assert public.pokemon[0].pokemon.types == ["Type #12", "Type #9"]
                assert public.pokemon[0].pokemon.moves[0].name == "Move #621"
                assert any(p.location == "Caja 8 · 1" for p in public.pokemon)
            if later_relative:
                later = (args.fixtures / later_relative).read_bytes()
                latest = service.receive(
                    sid,
                    tid,
                    sha256(later).hexdigest(),
                    receipts[0].save_id,
                    observation_digest(parser.parse(later), parser.version),
                    later,
                )
                assert latest.is_current and not send().is_current
                assert str(reads.pc(sid, tid).save.id) == latest.save_id
            accepted = snapshot()
            if args.public_fixtures:
                other_source = args.fixtures / (
                    cases[1][1] if game == "US" else cases[0][1]
                )
            else:
                other_source = args.fixtures / (
                    "xy/X/main" if game in ("OR", "AS") else "oras/OR/main"
                )
            for target, expected, candidate in (
                (rival, None, raw),
                (tid, str(reads.pc(sid, tid).save.id), other_source.read_bytes()),
            ):
                try:
                    service.receive(
                        sid,
                        target,
                        sha256(candidate).hexdigest(),
                        expected,
                        observation_digest(parser.parse(candidate), parser.version),
                        candidate,
                    )
                except SeasonAdminRejected:
                    pass
                else:
                    raise AssertionError("cross-owner/game accepted")
            assert snapshot() == accepted
            # Failed transaction must leave every public table unchanged.
            request = repo.last.copy()
            request.update(
                save_id=str(uuid4()),
                parsed_id=str(uuid4()),
                sha256="f" * 64,
                expected_save_id=str(reads.pc(sid, tid).save.id),
                trainer_id=tid,
            )
            request["storage_key"] = f"trusted/{tid}/{sid}/" + "f" * 64 + ".sav"
            request["payload"] = request["payload"] | {
                "save_record_id": request["save_id"],
                "trainer_id": tid,
                "source_hash": "f" * 64,
            }
            # Last request may be the rejected other owner; take original identity/payload from this game's parse.
            from app.application.save_ingestion import parsed_payload

            request["payload"] = parsed_payload(obs, request["save_id"], tid, "f" * 64)
            request["save_identity"] = {
                "game": game,
                "trainer": obs.trainer.model_dump(mode="json"),
            }
            # A fresh hash with a stale pointer must fail in SQL itself.
            stale = request | {
                "operation": "register",
                "expected_save_id": str(uuid4()),
            }
            try:
                sql(
                    "select public.api_register_save("
                    + literal(json.dumps(stale))
                    + "::jsonb)"
                )
            except RuntimeError as error:
                assert "save_current_changed" in str(error), str(error)
            else:
                raise AssertionError("stale CAS accepted")
            assert snapshot() == accepted
            try:
                sql(
                    "do $x$ begin perform public.api_register_save("
                    + literal(json.dumps(request | {"operation": "register"}))
                    + "::jsonb); perform 1/0; end $x$;"
                )
            except RuntimeError as error:
                assert "division by zero" in str(error)
            else:
                raise AssertionError("rollback not exercised")
            assert snapshot() == accepted
            core = LauncherCore(args.output / ("local-" + game), SaveInspector(parser))
            core.select(source)
            assert (
                core.manual_sync().status == "SYNCED"
                and core.manual_sync().status == "NO_CHANGE"
            )
            runtime = LauncherRuntime(
                args.output / ("local-" + game), SaveInspector(parser), start=False
            )
            try:
                assert runtime.state()["observation"]["game"] == game
                assert runtime.state()["cloud_status"] == "OFFLINE"
            finally:
                runtime.close()
            assert sha256(source.read_bytes()).hexdigest() == original_hash
            evidence[game] = {
                "synthetic": not args.public_fixtures,
                "import": True,
                "replay_concurrency": True,
                "privacy": True,
                "stale_cas": True,
                "offline_cache": True,
                "source_unchanged": True,
                "slots": len(pc.pokemon),
                "final_slots": len(reads.pc(sid, tid).pokemon),
                "later_receipt_no_rewind": bool(later_relative),
            }
        for role in ("anon", "authenticated"):
            try:
                Client(local, role).execute("select public.api_register_save('{}')")
            except SqlError as error:
                assert error.code == "42501"
            else:
                raise AssertionError("browser RPC allowed")
        for table in (
            "pokemon_identity_revisions",
            "pokemon_entities",
            "progress_reward_claims",
            "coin_transactions",
            "team_locks",
        ):
            assert scalar(f"select count(*) from public.{table}") == 0
        sql(
            f"update public.season_players set current_save_file_id=null where season_id='{sid}'; "
            f"delete from public.parsed_saves where save_file_id in(select id from public.save_files where season_id='{sid}'); "
            f"delete from public.save_files where season_id='{sid}'; delete from public.season_players where season_id='{sid}'; "
            f"delete from public.seasons where id='{sid}'; delete from public.trainers where id in ({','.join(literal(t) for t in tids)})"
        )
        assert snapshot() == before
        if args.public_fixtures:
            for fixture in manifest["fixtures"]:
                assert (
                    sha256((args.fixtures / fixture["file"]).read_bytes()).hexdigest()
                    == fixture["sha256"]
                )
        report = {
            "status": "PASS_PUBLIC_CONTRIBUTOR_SAVES"
            if args.public_fixtures
            else "PASS_SYNTHETIC_ONLY",
            "authentic_usum": "PUBLIC_CONTRIBUTOR_GAMEPLAY_PROVENANCE"
            if args.public_fixtures
            else "SEPARATE_PUBLIC_FIXTURE_GATE",
            "games": evidence,
            "tables_restored": len(before),
            "bootstrap_parity": "RETAINED_UNCHANGED_SOURCE"
            if args.public_fixtures
            else True,
            "migration": 47,
            "remote_writes": 0,
        }
        (args.output / "result.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        print(json.dumps(report))
    finally:
        for name in reversed(created):
            run("dropdb", "postgres", [name])


if __name__ == "__main__":
    main()
