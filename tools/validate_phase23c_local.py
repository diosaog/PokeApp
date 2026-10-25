"""Phase23C: real loopback PG/native/Windows workflow on derived fixture copies.

No production issuer or credentials. The privileged evidence recorder below is
test infrastructure, intentionally not imported by the API. Remote rollout needs
a separately provisioned, restricted verifier and retained artifact transport.
"""

import argparse
import json
import os
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from app.application.item_use_verification import (
    TrustedItemUseVerification,
    VerificationRejected,
)
from app.application.save_ingestion import TrustedSaveIngestion
from app.domain.item_use import ItemUsePrepareRequest
from app.launcher.item_use import EngineeringItemUse
from app.launcher.save_activity import SaveActivityGate, SaveBusy
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import (
    EngineeringCapability,
    LocalWriteEngine,
)
from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError
from app.repositories.errors import ItemUseRejectedError
from app.repositories.supabase.item_use import SupabaseItemUseRepository
from app.repositories.supabase.save_ingestion import SupabaseSaveIngestionRepository
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.registration import observation_digest
from app.save_parser.writer import NativeWriteError, PkhexProcessWriter
from tools.validate_accounts_local import LocalPG
from tools.validate_supabase_v2_identity_sql import LocalClient


def literal(value):
    return "'" + json.dumps(value).replace("'", "''") + "'::jsonb"


class LocalSourceStore(SupabaseSaveIngestionRepository):
    def __init__(self, client):
        super().__init__(client)
        self.blobs = {}

    def store_raw(self, key, data, raw_hash):
        assert sha256(data).hexdigest() == raw_hash
        assert self.blobs.setdefault(key, data) == data


class LocalVerifierStore:
    """Only loopback test PG + previously server-accepted bytes, never client source."""

    def __init__(self, pg, client, source_store):
        self.pg, self.client, self.source_store = pg, client, source_store

    def rows(self, table, **filters):
        query = self.client.table(table).select("*")
        for k, v in filters.items():
            query = query.eq(k, v)
        return query.execute().data

    def one(self, table, **filters):
        rows = self.rows(table, **filters)
        if len(rows) != 1:
            raise VerificationRejected("MISSING_AUTHORITY")
        return rows[0]

    def load(self, aid, sid, tid):
        a = self.one("item_use_authorizations", id=aid, season_id=sid, trainer_id=tid)
        p = self.one("season_players", season_id=sid, trainer_id=tid)
        purchase = self.one(
            "purchases", id=a["purchase_id"], season_id=sid, trainer_id=tid
        )
        heads = self.rows("pokemon_identity_revisions", season_id=sid, trainer_id=tid)
        head = max(heads, key=lambda r: r["capture_sequence"])
        return {
            "authorization": a,
            "entity": self.one("pokemon_entities", id=a["target_pokemon_entity_id"]),
            "observation": self.one(
                "pokemon_observations",
                revision_id=a["identity_revision_id"],
                pokemon_entity_id=a["target_pokemon_entity_id"],
            ),
            "save": self.one("save_files", id=a["save_file_id"]),
            "current_save_id": p["current_save_file_id"],
            "head_id": head["id"],
            "trainer_enabled": self.one("trainers", id=tid)["globally_enabled"],
            "participant_active": p["status"] == "active",
            "purchase_pending": purchase["status"] == "pending",
            "purchase_effect": "revive"
            if self.one("shop_items", id=purchase["shop_item_id"])["code"]
            == "revivir_pokemon"
            else "unsupported",
        }

    def read_source(self, saved):
        return self.source_store.blobs[saved["storage_key"]]

    def record_verified(self, context, proof, result):
        assert sha256(result).hexdigest() == proof["result_sha256"]
        # Retain exact accepted artifact before recording evidence. Never upsert bytes.
        destination = self.pg.root / (proof["result_sha256"] + ".verified")
        try:
            with destination.open("xb") as out:
                out.write(result)
                out.flush()
                os.fsync(out.fileno())
        except FileExistsError:
            assert destination.read_bytes() == result
        a = context["authorization"]
        # Locks match existing mutation order. CAS against *all* captured authority;
        # no proof is issued if a claim/save/entity changes during native work.
        self.pg.sql(f"""begin;
        select 1 from seasons where id='{a["season_id"]}' for no key update;
        select 1 from season_players where season_id='{a["season_id"]}' and trainer_id='{a["trainer_id"]}' for update;
        select 1 from item_use_authorizations where id='{a["id"]}' for update;
        do $$ begin
          if not exists(select 1 from item_use_authorizations a
            join season_players p on p.season_id=a.season_id and p.trainer_id=a.trainer_id
            join trainers t on t.id=a.trainer_id join purchases buy on buy.id=a.purchase_id
            where a.id='{a["id"]}' and to_jsonb(a)={literal(a)}
              and a.expires_at>clock_timestamp() and p.status='active' and t.globally_enabled
              and p.current_save_file_id=a.save_file_id and buy.status='pending'
              and not exists(select 1 from pokemon_identity_revisions newer
                where newer.season_id=a.season_id and newer.trainer_id=a.trainer_id
                and newer.capture_sequence>(select capture_sequence from pokemon_identity_revisions where id=a.identity_revision_id)))
          or not exists(select 1 from pokemon_entities e where to_jsonb(e)={literal(context["entity"])})
          or not exists(select 1 from pokemon_observations o where to_jsonb(o)={literal(context["observation"])})
          or not exists(select 1 from save_files s where to_jsonb(s)={literal(context["save"])})
          then raise exception 'verification_context_changed'; end if;
          insert into item_use_verifications(authorization_id,claim_id,operation_id,source_sha256,result_sha256,
            target_pokemon_entity_id,identity_revision_id,native_operation_id,plan_sha256)
          select authorization_id,claim_id,operation_id,source_sha256,result_sha256,target_pokemon_entity_id,
            identity_revision_id,native_operation_id,plan_sha256
          from jsonb_populate_record(null::item_use_verifications,{literal(proof)})
          on conflict(authorization_id) do nothing;
          if not exists(select 1 from item_use_verifications v
            where v.authorization_id='{a["id"]}' and (to_jsonb(v)-'verified_at')={literal(proof)})
          then raise exception 'verification_conflict'; end if;
        end $$; commit;""")


def run(args):
    pg = LocalPG(args.pg_bin, 55474)
    report = {"status": "RUNNING", "games": [], "checks": [], "cluster": str(pg.root)}
    parser, native = (
        PkhexProcessParser(args.native_exe),
        PkhexProcessWriter(args.native_exe),
    )
    try:
        pg.start()
        config = SimpleNamespace(
            psql=str(args.pg_bin / "psql.exe"),
            host="127.0.0.1",
            port=pg.port,
            user="postgres",
            password="",
            database="pokeapp_v2_validation_accounts",
        )
        client = LocalClient(config)
        source_store = LocalSourceStore(client)
        ingestion = TrustedSaveIngestion(source_store, parser)
        store = LocalVerifierStore(pg, client, source_store)
        verifier = TrustedItemUseVerification(store, parser, native)
        repo = SupabaseItemUseRepository(client)

        def insert(table, row):
            return client.table(table).insert(row).execute().data[0]

        def setup(game):
            source = (args.fixtures / game / "source").read_bytes()
            tid = str(uuid4())
            insert(
                "trainers",
                {
                    "id": tid,
                    "display_name": "Revive " + tid[:8],
                    "slug": "revive-" + tid,
                },
            )
            # Separate local scenarios; never more than one active fixture season.
            pg.sql(
                "update seasons set status='draft',started_at=null where status='active';"
            )
            season = insert(
                "seasons",
                {
                    "name": "23C " + tid,
                    "status": "active",
                    "started_at": "2026-10-01T00:00:00Z",
                },
            )
            sid = season["id"]
            player = insert("season_players", {"season_id": sid, "trainer_id": tid})
            observed = parser.parse(source)
            receipt = ingestion.receive(
                sid,
                tid,
                sha256(source).hexdigest(),
                None,
                observation_digest(observed, parser.version),
                source,
            )
            saved = store.one("save_files", id=receipt.save_id)
            head = store.one("pokemon_identity_revisions", save_file_id=saved["id"])
            target = store.one(
                "pokemon_observations",
                revision_id=head["id"],
                source="box",
                box_number=8,
                slot_number=1,
            )
            assert target["outcome"] == "NEW"
            item = store.one("shop_items", code="revivir_pokemon")
            purchase = insert(
                "purchases",
                {
                    "season_id": sid,
                    "trainer_id": tid,
                    "season_player_id": player["id"],
                    "shop_item_id": item["id"],
                    "unit_price": 12,
                },
            )
            auth = repo.prepare(
                ItemUsePrepareRequest(
                    sid,
                    tid,
                    purchase["id"],
                    target["pokemon_entity_id"],
                    saved["id"],
                    saved["sha256"],
                    str(uuid4()),
                    str(uuid4()),
                )
            )
            return auth, source

        def pending(a):
            assert store.one("purchases", id=a["purchase_id"])["status"] == "pending"
            assert not store.rows("redemptions", purchase_id=a["purchase_id"])

        def bridge(a, target, *, fault=None, repository=repo, profile="profile"):
            root = target.parent
            engine = LocalWriteEngine(
                root / profile,
                native,
                files=WindowsWriteFiles(process_names=list),
                engineering_capability=EngineeringCapability.for_fixture_root(root),
                fault_hook=fault,
            )
            controller = LocalWriteController(
                SaveActivityGate(), lambda: str(target), engine
            )
            return EngineeringItemUse(
                controller,
                repository,
                season_id=a["season_id"],
                trainer_id=a["trainer_id"],
            )

        def reject(call, exception):
            try:
                call()
            except exception:
                return
            raise AssertionError("expected rejection")

        for game in args.games if "games" in args.checks else ():
            a, source = setup(game)
            root = pg.root / ("save-" + game)
            root.mkdir()
            path = root / "main"
            path.write_bytes(source)
            intent = verifier.plan(a["id"], a["season_id"], a["trainer_id"])
            assert intent.to_payload() == json.loads(
                (args.fixtures / game / "intent.json").read_text()
            )
            local = bridge(a, path)
            local.bind_revive(
                a, intent, pokemon_entity_id=a["target_pokemon_entity_id"]
            )
            reject(
                lambda local=local, a=a: local.apply(
                    a["id"], closed_emulator_confirmed=False
                ),
                WriteSafetyError,
            )
            assert (
                local.apply(a["id"], closed_emulator_confirmed=True)
                == "LOCAL_VERIFIED_AWAITING_CONFIRMATION"
            )
            pending(a)
            assert path.read_bytes() == (args.fixtures / game / "expected").read_bytes()
            _, record = local._load(a["id"])
            claim = record["claim_id"]
            reject(
                lambda a=a, claim=claim, path=path, source=source: verifier.verify(
                    a["id"], a["season_id"], str(uuid4()), claim, path.read_bytes()
                ),
                VerificationRejected,
            )
            reject(
                lambda a=a, claim=claim, path=path, source=source: verifier.verify(
                    a["id"],
                    a["season_id"],
                    a["trainer_id"],
                    str(uuid4()),
                    path.read_bytes(),
                ),
                VerificationRejected,
            )
            reject(
                lambda a=a, claim=claim, path=path, source=source: verifier.verify(
                    a["id"], a["season_id"], a["trainer_id"], claim, source
                ),
                NativeWriteError,
            )
            assert local.complete(a["id"]) == "BLOCKED_UNCERTAIN"
            pending(a)
            proof = verifier.verify(
                a["id"], a["season_id"], a["trainer_id"], claim, path.read_bytes()
            )
            assert (
                verifier.verify(
                    a["id"], a["season_id"], a["trainer_id"], claim, path.read_bytes()
                )
                == proof
            )
            pending(a)
            incompatible = proof | {"plan_sha256": "f" * 64}
            reject(
                lambda a=a, incompatible=incompatible, path=path: store.record_verified(
                    store.load(a["id"], a["season_id"], a["trainer_id"]),
                    incompatible,
                    path.read_bytes(),
                ),
                RuntimeError,
            )

            class LostAck:
                def complete(self, *parts):
                    repo.complete(*parts)
                    raise OSError("injected response loss")

            interrupted = bridge(a, path, repository=LostAck())
            reject(
                lambda interrupted=interrupted, a=a: interrupted.complete(a["id"]),
                OSError,
            )
            final = bridge(a, path)
            assert final.complete(a["id"]) == "APPLIED_VERIFIED"
            assert final.complete(a["id"]) == "APPLIED_VERIFIED"
            receipt = final.engine.reconcile(intent.operation_id)
            assert receipt.current_matches_receipt
            _, original, _ = final.engine._materials(
                final.engine._load(intent.operation_id)
            )
            assert original == source
            assert len(store.rows("redemptions", purchase_id=a["purchase_id"])) == 1
            assert store.one("purchases", id=a["purchase_id"])["status"] == "used"
            flags = store.rows(
                "pokemon_entity_flags", pokemon_entity_id=a["target_pokemon_entity_id"]
            )
            assert {r["flag_type"] for r in flags} == {"blindado", "revivido_at"}
            assert not store.rows("coin_transactions", season_id=a["season_id"])
            assert not final.controller.gate.recovery_required
            report["games"].append(
                {
                    "game": game,
                    "status": "PASS",
                    "source_sha256": sha256(source).hexdigest(),
                    "result_sha256": proof["result_sha256"],
                    "single_consumption": True,
                    "boundary": "derived native-valid dead-target fixture; isolated local PG and filesystem; no emulator",
                }
            )
            print("PASS PG/NATIVE/LAUNCHER " + game, flush=True)

        # Native Windows interruption gates: existing journal, new revive semantics.
        for stage in (
            (
                "prepared",
                "backup_verified",
                "stage_verified",
                "after_park",
                "after_publish",
                "after_verify",
            )
            if "recovery" in args.checks
            else ()
        ):
            a, source = setup("X")
            root = pg.root / ("fault-" + stage)
            root.mkdir()
            path = root / "main"
            path.write_bytes(source)
            intent = verifier.plan(a["id"], a["season_id"], a["trainer_id"])

            def fault(at, stage=stage):
                if at == stage:
                    raise OSError("injected " + stage)

            local = bridge(a, path, fault=fault)
            local.bind_revive(
                a, intent, pokemon_entity_id=a["target_pokemon_entity_id"]
            )
            try:
                local.apply(a["id"], closed_emulator_confirmed=True)
            except WriteSafetyError:
                pass
            pending(a)
            restarted = bridge(a, path)
            receipt = restarted.engine.reconcile(intent.operation_id)
            assert receipt.status in (
                "REJECTED",
                "RECOVERY_REQUIRED",
                "AWAITING_CONFIRMATION",
                "APPLIED_VERIFIED",
            )
            if path.exists():
                assert path.read_bytes() in (
                    source,
                    (args.fixtures / "X" / "expected").read_bytes(),
                )
            pending(a)
            assert restarted.controller.gate.recovery_required
            report["checks"].append(
                "native interruption "
                + stage
                + ": no unknown consumption; intact source/candidate; restart guarded"
            )
        if "security" in args.checks:
            a, source = setup("X")
            root = pg.root / "security"
            root.mkdir()
            path = root / "main"
            path.write_bytes(source)
            intent = verifier.plan(a["id"], a["season_id"], a["trainer_id"])
            first, second = bridge(a, path), bridge(a, path, profile="second-profile")
            for b in (first, second):
                b.bind_revive(
                    a, intent, pokemon_entity_id=a["target_pokemon_entity_id"]
                )
            assert (
                first.apply(a["id"], closed_emulator_confirmed=True)
                == "LOCAL_VERIFIED_AWAITING_CONFIRMATION"
            )
            reject(
                lambda: second.apply(a["id"], closed_emulator_confirmed=True),
                ItemUseRejectedError,
            )
            pending(a)
            with first.controller.gate.writing(recovery=True):
                reject(lambda: first.controller.gate.reading().__enter__(), SaveBusy)
            _, record = first._load(a["id"])
            claim = record["claim_id"]
            c = store.load(a["id"], a["season_id"], a["trainer_id"])
            # A legitimate proof is bound to actual SQL state, not a captured DTO.
            proof = verifier.verify(
                a["id"], a["season_id"], a["trainer_id"], claim, path.read_bytes()
            )
            reject(
                lambda: store.record_verified(
                    c, proof | {"plan_sha256": "f" * 64}, path.read_bytes()
                ),
                RuntimeError,
            )
            # Untrusted roles still cannot create or edit evidence (existing054).
            for role in ("service_role", "authenticated", "anon"):
                from tools.validate_supabase_v2_identity_sql import SqlError

                reject(
                    lambda r=role: (
                        LocalClient(config, r)
                        .table("item_use_verifications")
                        .insert(proof)
                        .execute()
                    ),
                    SqlError,
                )
            changed = deepcopy(c)
            changed["entity"]["candidate_key"] = "e" * 64
            reject(
                lambda: store.record_verified(changed, proof, path.read_bytes()),
                RuntimeError,
            )
            # Changing the selected file after native success blocks client completion.
            path.write_bytes(source)
            assert first.complete(a["id"]) == "RECOVERY_REQUIRED"
            pending(a)
            assert (
                first.engine._backup_bytes(first.engine._load(intent.operation_id))
                == source
            )
            report["checks"].append(
                "two Launcher profiles, sync exclusion, incompatible proof, issuer grants, CAS and restored-source rejection"
            )

            # Fresh source changed before applying: no candidate can overwrite it.
            a, source = setup("X")
            root = pg.root / "stale"
            root.mkdir()
            path = root / "main"
            path.write_bytes(source)
            intent = verifier.plan(a["id"], a["season_id"], a["trainer_id"])
            first = bridge(a, path)
            first.bind_revive(
                a, intent, pokemon_entity_id=a["target_pokemon_entity_id"]
            )
            changed_bytes = b"\x01" + source[1:]
            path.write_bytes(changed_bytes)
            reject(
                lambda: first.apply(a["id"], closed_emulator_confirmed=True),
                WriteSafetyError,
            )
            pending(a)
            assert path.read_bytes() == changed_bytes
            report["checks"].append(
                "stale selected file rejected and preserved; entitlement pending"
            )
        if "parity" in args.checks:
            from tools.validate_phase23_local import parity

            report["parity"] = parity(pg)
        report["status"] = "PASS"
    finally:
        pg.stop()
        report["database_dropped_cluster_stopped"] = True
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--pg-bin", type=Path, required=True)
    cli.add_argument("--native-exe", type=Path, required=True)
    cli.add_argument("--fixtures", type=Path, required=True)
    cli.add_argument("--output", type=Path, required=True)
    cli.add_argument(
        "--games",
        nargs="+",
        choices=("X", "Y", "OR", "AS", "SN", "MN", "US", "UM"),
        default=["X", "Y", "OR", "AS", "SN", "MN", "US", "UM"],
    )
    cli.add_argument(
        "--checks",
        nargs="+",
        choices=("games", "recovery", "security", "parity"),
        default=["games", "recovery", "security", "parity"],
    )
    run(cli.parse_args())
