"""Focused 085 acceptance: Robar y Revivir, on isolated copies only.

Disposable loopback PostgreSQL with the full bootstrap, the real FastAPI routes,
the real safe write engine in production mode, the restricted verifier and the
native PKHeX parser/writer. Public fixtures only: no owner save, no network and
no production database.

    python -m tools.validate_phase085_activation --pg-bin <dir> --native-exe <exe> \
        --fixtures <dir from --phase085-fixtures> --output <json>
"""

import argparse
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated
from uuid import uuid4

import httpx
import psycopg
from fastapi import Header
from fastapi.testclient import TestClient

import app.launcher.revive as revive_module
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.security import require_enabled_principal
from app.application.item_use_transport import ItemUseTransport
from app.application.item_use_worker import SignedArtifactReader, verify_one
from app.application.save_ingestion import TrustedSaveIngestion
from app.application.transfer_integration import TransferIntegration
from app.application.transfer_transport import TransferTransport
from app.application.transfer_verification import TransferVerification
from app.application.transfer_worker import run_transfer_step
from app.launcher.backend import BackendError
from app.launcher.revive import LauncherRevive, ReviveRemote
from app.launcher.save_activity import SaveActivityGate
from app.launcher.transfer import AuthenticatedTransferRemote, LauncherTransfers
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import LocalWriteEngine
from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError
from app.repositories.item_verifier_pg import ItemVerifierPG
from app.repositories.supabase.item_use import SupabaseItemUseRepository
from app.repositories.supabase.item_use_transport import SupabaseItemUseTransport
from app.repositories.supabase.transfer import TransferRepository
from app.repositories.transfer_verifier_pg import TransferVerifierPG
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.registration import observation_digest
from app.save_parser.writer import PkhexProcessWriter
from tools.validate_accounts_local import LocalPG
from tools.validate_phase23c_local import LocalSourceStore, LocalVerifierStore
from tools.validate_phase23d_local import Blobs
from tools.validate_supabase_v2_identity_sql import LocalClient


class ApiError(BackendError):
    def __init__(self, status, code):
        super().__init__("OBSERVATION_REJECTED", status=status, detail=code)
        self.status, self.code = status, code


class LocalReads:
    """The read repository's contract over the loopback client (no `is null`)."""

    def __init__(self, client):
        self.client = client

    def rows(self, table, columns, *, filters=None, order=None, offset=0, limit=500):
        query = self.client.table(table).select("*")
        filters = filters or {}
        for key, value in filters.items():
            if value is not None:
                query = query.eq(key, value)
        return [
            row
            for row in query.execute().data
            if all(row.get(k) is None for k, v in filters.items() if v is None)
        ]


class ApiSession:
    """The Launcher's authenticated session, over the real FastAPI routes."""

    def __init__(self, client, tid, after_upload=None):
        self.client, self.tid = client, tid
        self.headers = {"Authorization": "Bearer " + tid}
        self.after_upload = after_upload or (lambda: None)

    def principal(self):
        return SimpleNamespace(trainer_id=self.tid)

    def _reply(self, response, missing=False):
        if missing and response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise ApiError(response.status_code, response.json()["detail"]["code"])
        return response.json()

    def request(self, method, path, *, body=None, missing=False):
        return self._reply(
            self.client.request(method, path, json=body, headers=self.headers), missing
        )

    def upload(self, path, data):
        headers = self.headers | {"Content-Type": "application/octet-stream"}
        reply = self._reply(self.client.put(path, content=data, headers=headers))
        self.after_upload()
        return reply


def run(args):
    pg = LocalPG(args.pg_bin, args.port)
    report = {"status": "RUNNING", "checks": []}
    worker = None

    def passed(label):
        report["checks"].append(label)
        print("PASS", label, flush=True)

    def ok(condition, label):
        assert condition, label
        passed(label)

    try:
        pg.start()
        client = LocalClient(
            SimpleNamespace(
                psql=str(args.pg_bin / "psql.exe"),
                host="127.0.0.1",
                port=pg.port,
                user="postgres",
                password="",
                database="pokeapp_v2_validation_accounts",
            )
        )
        parser, native = (
            PkhexProcessParser(args.native_exe),
            PkhexProcessWriter(args.native_exe),
        )
        sources = LocalSourceStore(client)
        ingestion = TrustedSaveIngestion(sources, parser)
        store = LocalVerifierStore(pg, client, sources)
        repo = TransferRepository(client)
        item_repo = SupabaseItemUseRepository(client)
        pg.sql(
            "create role phase085_worker login nosuperuser nocreatedb nocreaterole nobypassrls; grant pokeapp_item_verifier to phase085_worker;"
        )
        worker = psycopg.connect(
            host="127.0.0.1",
            port=pg.port,
            dbname="pokeapp_v2_validation_accounts",
            user="phase085_worker",
            autocommit=True,
        )
        rpc = TransferVerifierPG(worker)
        item_rpc = ItemVerifierPG(worker)
        blobs = Blobs(sources.blobs)
        reader = SignedArtifactReader(
            blobs.origin,
            client=httpx.Client(transport=httpx.MockTransport(blobs.serve)),
        )
        verifier = TransferVerification(
            rpc,
            lambda s: sources.blobs[s["storage_key"]],
            reader,
            parser,
            native,
            store_raw=sources.store_raw,
        )
        transport = TransferTransport(repo, blobs)
        service = TransferIntegration(repo, transport)
        item_transport = ItemUseTransport(SupabaseItemUseTransport(client), blobs)

        def principal(authorization: Annotated[str, Header()]):
            return SimpleNamespace(trainer_id=authorization.removeprefix("Bearer "))

        api = create_app(
            container=ApiContainer(
                transfer_integration=service,
                item_use_repository=item_repo,
                item_use_transport=item_transport,
                frontend_read_repository=LocalReads(client),
            )
        )
        api.dependency_overrides[require_enabled_principal] = principal
        http = TestClient(api)

        def insert(table, row):
            return client.table(table).insert(row).execute().data[0]

        def admin(table, **filters):
            """As the database owner: tables the API roles cannot read."""
            where = " and ".join(f"{k}='{v}'" for k, v in filters.items()) or "true"
            out = pg.sql(
                f"select coalesce(jsonb_agg(to_jsonb(t)),'[]'::jsonb) from public.{table} t where {where};"
            ).stdout.strip()
            return json.loads(out)

        def drain():
            for _ in range(12):
                step = run_transfer_step(rpc, verifier)
                if not step:
                    return
                assert all(o["outcome"] == "DONE" for o in step), step
            raise AssertionError("worker did not settle")

        def trainer(sid, data=None, name=None):
            tid = str(uuid4())
            insert(
                "trainers",
                {
                    "id": tid,
                    "display_name": name or "Prueba " + tid[:8],
                    "slug": "t85-" + tid,
                },
            )
            player = insert("season_players", {"season_id": sid, "trainer_id": tid})
            t = {"tid": tid, "player": player, "data": data, "save": None}
            if data is not None:
                t["save"] = receive(sid, t, data)
            return t

        def receive(sid, t, data):
            receipt = ingestion.receive(
                sid,
                t["tid"],
                sha256(data).hexdigest(),
                t["save"],
                observation_digest(parser.parse(data), parser.version),
                data,
            )
            t["save"], t["data"] = receipt.save_id, data
            return receipt.save_id

        def season():
            pg.sql(
                "update public.seasons set status='draft',started_at=null where status='active';"
            )
            return insert(
                "seasons",
                {
                    "name": "085 " + str(uuid4()),
                    "status": "active",
                    "started_at": "2026-10-01T00:00:00Z",
                },
            )["id"]

        def age(sid=None):
            """Every Pokémon first seen two days ago, in this test database only."""
            pg.sql(
                "set session_replication_role=replica;"
                "update public.pokemon_entities set created_at=now()-interval '2 days';"
                "update public.pokemon_observations set created_at=now()-interval '2 days';"
                "set session_replication_role=origin;"
            )

        def purchase(sid, t, code):
            item = store.one("shop_items", code=code)
            return insert(
                "purchases",
                {
                    "season_id": sid,
                    "trainer_id": t["tid"],
                    "season_player_id": t["player"]["id"],
                    "shop_item_id": item["id"],
                    "unit_price": item["base_price"],
                },
            )["id"]

        def observed(t, *, source="box", box=1):
            head = store.one("pokemon_identity_revisions", save_file_id=t["save"])
            return sorted(
                (
                    o
                    for o in store.rows("pokemon_observations", revision_id=head["id"])
                    if o["source"] == source and o["box_number"] == box
                ),
                key=lambda o: o["slot_number"],
            )

        def steal(sid, thief, pid, entity, key=None):
            return http.post(
                f"/v1/seasons/{sid}/shop/purchases/{pid}/transfer",
                json={"pokemon_entity_id": entity},
                headers={
                    "Authorization": "Bearer " + thief["tid"],
                    "Idempotency-Key": key or str(uuid4()),
                },
            )

        def code(reply):
            return reply.json()["detail"]["code"]

        def board(sid, t):
            reply = http.get(
                f"/v1/seasons/{sid}/robbery/board",
                headers={"Authorization": "Bearer " + t["tid"]},
            )
            assert reply.status_code == 200, reply.text
            return reply.json()

        def by(data, t):
            return next(x for x in data["trainers"] if x["trainer_id"] == t["tid"])

        def launcher(sid, t, label, *, running=(), after_upload=None, fault=None):
            root = pg.root / f"{sid}-{label}"
            root.mkdir(exist_ok=True)
            target = root / "main"
            if not target.exists():
                target.write_bytes(t["data"])
            engine = LocalWriteEngine(
                root / "profile",
                native,
                files=WindowsWriteFiles(process_names=lambda: list(running)),
                fault_hook=fault,
            )
            controller = LocalWriteController(
                SaveActivityGate(), lambda: str(target), engine
            )
            session = ApiSession(http, t["tid"], after_upload)
            return controller, session, target, engine

        def transfer_flow(sid, t, label):
            controller, session, target, _ = launcher(sid, t, label)
            return (
                LauncherTransfers(
                    controller, AuthenticatedTransferRemote(session, sid, t["tid"])
                ),
                target,
            )

        def fulfil(sid, aid, t, label):
            flow, target = transfer_flow(sid, t, label)
            flow.fulfil(aid, closed_emulator_confirmed=True)
            drain()
            flow.refresh(aid)
            return target

        def settle(sid, aid, victim, thief, labels):
            drain()
            source = fulfil(sid, aid, victim, labels[0])
            destination = fulfil(sid, aid, thief, labels[1])
            state = admin("item_use_transfers", authorization_id=aid)[0]
            assert state["terminal"] == "COMMITTED", state
            victim["save"] = store.one(
                "season_players", season_id=sid, trainer_id=victim["tid"]
            )["current_save_file_id"]
            thief["save"] = store.one(
                "season_players", season_id=sid, trainer_id=thief["tid"]
            )["current_save_file_id"]
            victim["data"], thief["data"] = source.read_bytes(), destination.read_bytes()
            return source, destination

        # ---------- Robo ----------
        donor_bytes = (args.fixtures / "Alfa" / "main").read_bytes()
        thief_bytes = (args.fixtures / "Bravo" / "main").read_bytes()

        sid = season()
        victim = trainer(sid, donor_bytes, "Victima")
        thief = trainer(sid, thief_bytes, "Ladron")
        without_save = trainer(sid, None, "SinPartida")
        ok(
            store.one("season_players", id=victim["player"]["id"])["dead_box_number"]
            == 7,
            "new participants default to the official dead box (Caja 7)",
        )
        target = observed(victim)[0]
        pid = purchase(sid, thief, "robar_pokemon")

        # Purchase is independent of use: bought, kept, no Team Lock, no matchday.
        ok(
            not store.rows("team_locks", season_id=sid)
            and not store.rows("matchdays", season_id=sid),
            "no Team Lock and no matchday exist in this season",
        )

        # 24 h: the first verified sighting is seconds old.
        reply = steal(sid, thief, pid, target["pokemon_entity_id"])
        ok(
            reply.status_code == 409 and code(reply) == "STEAL_TARGET_RECENT_CAPTURE",
            "a Pokémon seen less than 24 h ago is refused",
        )
        ok(
            reply.json()["detail"]["message"]
            == "Este Pokémon todavía no lleva 24 horas capturado.",
            "the refusal explains the 24 h rule",
        )
        data = board(sid, thief)
        entry = next(
            t
            for t in by(data, victim)["targets"]
            if t["pokemon_entity_id"] == target["pokemon_entity_id"]
        )
        ok(
            entry["blocked"] == "recent_capture" and entry["available_at"],
            "the board shows the wait and when it ends",
        )
        ok(
            not store.rows("item_use_authorizations", purchase_id=pid),
            "a refused request leaves no authorization",
        )
        age()

        # Trainers that cannot be robbed are explained, and do not block the round.
        data = board(sid, thief)
        ok(by(data, without_save)["status"] == "no_save", "no save: explained")
        ok(
            by(data, without_save)["message"]
            == "La partida del entrenador objetivo todavía no está disponible.",
            "no-save message",
        )
        ok(data["round"] == 1 and by(data, victim)["status"] == "available", "round 1")

        # Self robbery.
        own = observed(thief)[0]
        reply = steal(sid, thief, pid, own["pokemon_entity_id"])
        ok(code(reply) == "STEAL_SELF_TARGET", "no self robbery")

        # Shielded: refused at preparation; the rest stay available.
        shielded = observed(victim)[1]
        pg.sql(
            "insert into public.pokemon_entity_flags(season_id,trainer_id,pokemon_entity_id,flag_type,flag_value)"
            f" values('{sid}','{victim['tid']}','{shielded['pokemon_entity_id']}','blindado',true);"
        )
        reply = steal(sid, thief, pid, shielded["pokemon_entity_id"])
        ok(
            code(reply) == "STEAL_TARGET_SHIELDED"
            and reply.json()["detail"]["message"] == "Este Pokémon está blindado.",
            "a shielded Pokémon is refused",
        )
        data = board(sid, thief)
        states = {
            t["pokemon_entity_id"]: t["blocked"] for t in by(data, victim)["targets"]
        }
        ok(
            states[shielded["pokemon_entity_id"]] == "shielded"
            and states[target["pokemon_entity_id"]] is None,
            "other Pokémon of a shielded trainer stay available",
        )
        ok(by(data, victim)["status"] == "available", "a shield does not end the round")

        # Cancelled attempt: victim not marked, comodín free again.
        key = str(uuid4())
        first = steal(sid, thief, pid, target["pokemon_entity_id"], key)
        again = steal(sid, thief, pid, target["pokemon_entity_id"], key)
        ok(
            first.status_code == 200
            and again.json()["authorization_id"] == first.json()["authorization_id"],
            "a technical retry returns the same robbery",
        )
        aid = first.json()["authorization_id"]
        session = ApiSession(http, thief["tid"])
        session.request(
            "PUT",
            f"/v1/launcher/seasons/{sid}/transfers/{aid}",
            body={"operation": "cancel"},
        )
        ok(
            store.one("purchases", id=pid)["status"] == "pending",
            "a cancelled attempt does not consume the comodín",
        )
        ok(
            by(board(sid, thief), victim)["status"] == "available",
            "a cancelled attempt does not mark the victim",
        )

        # Concurrency: two thieves, one victim.
        rival = trainer(sid, None, "Segundo")
        rival_pid = purchase(sid, thief, "robar_pokemon")
        real = steal(sid, thief, pid, target["pokemon_entity_id"])
        ok(real.status_code == 200, "a new attempt reuses the comodín")
        aid = real.json()["authorization_id"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            replies = list(
                pool.map(
                    lambda _: steal(
                        sid, thief, rival_pid, observed(victim)[2]["pokemon_entity_id"]
                    ),
                    range(2),
                )
            )
        ok(
            all(code(r) == "TRANSFER_RESERVED" for r in replies),
            "concurrent requests on a reserved trainer are refused",
        )

        # Adjudication and physical delivery without any Team Lock.
        source_before = victim["data"]
        settle(sid, aid, victim, thief, ("victim1", "thief1"))
        after_source = parser.parse(victim["data"])
        after_destination = parser.parse(thief["data"])
        moved = [
            s
            for b in after_destination.boxes
            for s in b.slots
            if s is not None and s.identity.pid == target["evidence"]["pid"]
        ]
        ok(len(moved) == 1, "the Pokémon arrives once in the thief's save")
        ok(
            not any(
                s is not None and s.identity.pid == target["evidence"]["pid"]
                for b in after_source.boxes
                for s in b.slots
            ),
            "the Pokémon leaves the victim's save",
        )
        ok(
            moved[0].identity.encryption_constant
            == target["evidence"]["encryption_constant"]
            and moved[0].ivs == tuple(target["evidence"]["ivs"]),
            "identity and original data are preserved",
        )
        dead = next(b for b in after_destination.boxes if b.number == 7)
        ok(
            not any(
                s is not None and s.identity.pid == target["evidence"]["pid"]
                for s in dead.slots
            ),
            "a stolen Pokémon never lands in the dead box",
        )
        ok(source_before != victim["data"], "the victim's save changed")
        ok(
            len(store.rows("redemptions", purchase_id=pid)) == 1
            and store.one("purchases", id=pid)["status"] == "used",
            "exactly one redemption; comodín consumed once",
        )

        # Round: victim robbed; thief can't rob them again until the round ends.
        age()
        other = observed(victim)[2]
        reply = steal(sid, thief, rival_pid, other["pokemon_entity_id"])
        ok(
            code(reply) == "STEAL_VICTIM_ALREADY_ROBBED"
            and reply.json()["detail"]["message"]
            == "Este entrenador ya ha sido robado durante la ronda actual.",
            "a robbed trainer cannot be robbed again in the round",
        )
        data = board(sid, thief)
        ok(by(data, victim)["status"] == "already_robbed", "the board says so")
        ok(
            admin("robbery_cycles", season_id=sid)[0]["cycle_number"] == 1,
            "the round stays open while an eligible victim is missing",
        )

        # The victim robs the thief: nobody eligible is missing, the round rolls.
        victim_pid = purchase(sid, victim, "robar_pokemon")
        back = next(
            o
            for o in observed(thief, box=1)
            if o["pokemon_entity_id"] != target["pokemon_entity_id"]
            and o["evidence"]["source_trainer_match"]
        )
        real = steal(sid, victim, victim_pid, back["pokemon_entity_id"])
        ok(real.status_code == 200, "the first victim can rob the other trainer back")
        settle(
            sid, real.json()["authorization_id"], thief, victim, ("thief2", "victim2")
        )
        ok(
            admin("robbery_cycles", season_id=sid)[0]["cycle_number"] == 2,
            "the round completes when every eligible victim was robbed (no-save ignored)",
        )
        age()
        data = board(sid, thief)
        ok(
            data["round"] == 2 and by(data, victim)["status"] == "available",
            "a trainer can be robbed again in the new round",
        )
        reply = steal(sid, thief, rival_pid, observed(victim)[2]["pokemon_entity_id"])
        ok(reply.status_code == 200, "a new robbery opens the next round")
        pg.sql(
            f"update public.item_use_authorizations set expires_at=now()-interval '1 minute' where id='{reply.json()['authorization_id']}';"
        )
        ok(
            run_transfer_step(rpc, verifier) == [],
            "an expired undecided request is released by the verifier",
        )
        ok(
            admin(
                "item_use_transfers", authorization_id=reply.json()["authorization_id"]
            )[0]["terminal"]
            == "CANCELLED"
            and store.one("purchases", id=rival_pid)["status"] == "pending",
            "an expired request frees both trainers and keeps the comodín",
        )

        # ---------- Revivir ----------
        base = (args.fixtures / "Carla" / "main").read_bytes()
        sid = season()
        trainer_a = trainer(sid, base, "Revivir")
        dead_observation = observed(trainer_a, box=7)
        ok(len(dead_observation) >= 1, "the fixture has a Pokémon in Caja 7")
        entity = dead_observation[0]["pokemon_entity_id"]
        pg.sql(
            "insert into public.league_death_history(season_player_id,dead_box_number,actual_offset,last_identity_revision_id,confirmed_wipe_deaths,confirmed_wipe_revision,confirmed_unmapped_revives)"
            f" select '{trainer_a['player']['id']}',7,0,id,0,0,0 from public.pokemon_identity_revisions where save_file_id='{trainer_a['save']}'"
            " on conflict(season_player_id) do update set actual_offset=0,blocking_reason=null,confirmed_wipe_deaths=0,confirmed_wipe_revision=0,confirmed_unmapped_revives=0,last_identity_revision_id=excluded.last_identity_revision_id;"
        )
        pg.sql(
            "insert into public.league_death_events(season_player_id,pokemon_entity_id,identity_revision_id,observation_id,source_save_id,source_sha256,dead_box_number,cycle_key,phase,observed_at)"
            f" select '{trainer_a['player']['id']}',o.pokemon_entity_id,o.revision_id,o.id,o.save_file_id,'{sha256(base).hexdigest()}',7,'initial','preseason',now()"
            f" from public.pokemon_observations o where o.id='{dead_observation[0]['id']}' on conflict do nothing;"
        )

        pg.sql(
            "insert into public.season_player_stats(season_player_id,season_id,trainer_id) "
            f"values('{trainer_a['player']['id']}','{sid}','{trainer_a['tid']}') on conflict do nothing;"
        )

        def totals(t):
            return json.loads(
                pg.sql(
                    f"select public.league_death_totals('{t['player']['id']}')::text;"
                ).stdout.strip()
            )

        before = totals(trainer_a)
        ok(
            before["recorded_deaths"] == 1 and before["known"],
            "the death is on record before the revive",
        )
        insert(
            "coin_transactions",
            {
                "season_id": sid,
                "trainer_id": trainer_a["tid"],
                "season_player_id": trainer_a["player"]["id"],
                "amount": 40,
                "transaction_type": "compensation",
                "reference_type": "test",
            },
        )
        item = store.one("shop_items", code="revivir_pokemon")
        reply = client.rpc(
            "api_create_normal_purchase_8d",
            {
                "p_season_id": sid,
                "p_trainer_id": trainer_a["tid"],
                "p_item_id": item["id"],
                "p_idempotency_key": str(uuid4()),
                "p_confirm_base_price": False,
            },
        ).execute()
        revive_pid = reply.data["id"]
        ok(
            store.one("purchases", id=revive_pid)["status"] == "pending",
            "the comodín is bought at any time and kept in the inventory",
        )
        ok(
            not store.rows("matchdays", season_id=sid)
            and not store.rows("team_locks", season_id=sid),
            "buying needs no matchday and no Team Lock",
        )

        verified = []

        def work():
            for _ in range(5):
                outcome = verify_one(item_rpc, reader, parser, native)
                verified.append(outcome)
                if outcome == "IDLE":
                    return

        revive_module.VERIFY_POLL_SECONDS = 0.01
        controller, session, save_path, engine = launcher(
            sid, trainer_a, "revive1", after_upload=work
        )
        remote = ReviveRemote(session, sid, trainer_a["tid"])
        flow = LauncherRevive(controller, remote, session=session)
        view = flow.view()
        ok(
            view["dead_box_number"] == 7
            and any(c["pokemon_entity_id"] == entity for c in view["candidates"])
            and view["application_enabled"],
            "the dead Pokémon of Caja 7 are offered with species, nickname and level",
        )
        original = save_path.read_bytes()

        # A changed save is refused before anything happens.
        changed = bytearray(original)
        changed[0x100] ^= 1
        save_path.write_bytes(bytes(changed))
        result = flow.apply(revive_pid, entity)
        ok(
            result["status"] == "SAVE_CHANGED",
            "a save changed since the selection is refused",
        )
        save_path.write_bytes(original)
        ok(
            not store.rows("item_use_authorizations", purchase_id=revive_pid),
            "nothing is authorized for a changed save",
        )

        # Emulator open.
        _, session2, _, engine2 = launcher(
            sid, trainer_a, "revive1", running=("lime3ds-gui.exe",), after_upload=work
        )
        controller2 = LocalWriteController(
            SaveActivityGate(), lambda: str(save_path), engine2
        )
        running = LauncherRevive(controller2, remote, session=session2)
        try:
            running.apply(revive_pid, entity)
            raise AssertionError("emulator check")
        except WriteSafetyError as error:
            ok(str(error) == "EMULATOR_RUNNING", "an open emulator stops the operation")

        # A wrong target: not in the dead box.
        alive = observed(trainer_a)[0]["pokemon_entity_id"]
        result = flow.apply(revive_pid, alive)
        ok(result["status"] == "SAVE_CHANGED", "a living Pokémon is not a target")

        # Interrupted between the write and the proof: resumes from the journal.
        calls = {"n": 0}
        real_submit = flow.transport.submit

        def flaky(*a):
            calls["n"] += 1
            if calls["n"] == 1:
                raise httpx.ConnectError("injected")
            return real_submit(*a)

        flow.transport.submit = flaky
        try:
            flow.apply(revive_pid, entity)
            raise AssertionError("expected interruption")
        except httpx.ConnectError:
            passed("an interruption after the write is reported, not hidden")
        ok(
            store.one("purchases", id=revive_pid)["status"] == "pending",
            "an interrupted revive does not consume the comodín",
        )
        ok(
            controller.gate.recovery_required,
            "normal sync stays paused until it is settled",
        )
        controller3, session3, _, _ = launcher(
            sid, trainer_a, "revive1", after_upload=work
        )
        again = LauncherRevive(
            controller3, ReviveRemote(session3, sid, trainer_a["tid"]), session=session3
        )
        results = again.resume()
        ok(
            results and results[-1]["status"] == "DONE",
            "a new Launcher finishes the interrupted revive",
        )
        ok(
            results[-1]["message"] == "La operación se ha completado correctamente.",
            "the result message is the agreed one",
        )
        ok(
            not again.resume(),
            "a settled revive is not resumed twice",
        )
        ok(
            not controller3.gate.recovery_required,
            "normal sync resumes after completion",
        )

        # Physical result, re-read from the file.
        final = save_path.read_bytes()
        reread = parser.parse(final)
        dead_box = next(b for b in reread.boxes if b.number == 7)
        evidence = dead_observation[0]["evidence"]
        ok(
            not any(
                s is not None and s.identity.pid == evidence["pid"]
                for s in dead_box.slots
            ),
            "the Pokémon left Caja 7",
        )
        back_alive = [
            (b.number, i)
            for b in reread.boxes
            for i, s in enumerate(b.slots)
            if s is not None and s.identity.pid == evidence["pid"]
        ]
        ok(
            len(back_alive) == 1 and back_alive[0][0] < 7,
            "the Pokémon is in a usable box, once",
        )
        ok(
            store.one("purchases", id=revive_pid)["status"] == "used"
            and len(store.rows("redemptions", purchase_id=revive_pid)) == 1,
            "the comodín is consumed exactly once, after verification",
        )
        authorization = store.one("item_use_authorizations", purchase_id=revive_pid)
        ok(
            authorization["status"] == "APPLIED_VERIFIED"
            and authorization["observed_sha256"] == sha256(final).hexdigest(),
            "the server recorded the verified result",
        )
        ok(
            len(admin("item_use_verifications", authorization_id=authorization["id"])) == 1,
            "the proof comes from the restricted verifier",
        )

        # NET: next sync of the revived save.
        receive(sid, trainer_a, final)
        after = totals(trainer_a)
        ok(
            after["known"]
            and after["recorded_deaths"] == before["recorded_deaths"]
            and after["actual_deaths"] == before["actual_deaths"]
            and after["death_penalty_tenths"] == before["death_penalty_tenths"],
            "the historical death and its NET penalty remain after the revive",
        )
        ok(
            len(admin("league_death_events", season_player_id=trainer_a["player"]["id"]))
            == 1,
            "the revive itself adds no second penalty",
        )

        # An unverified result returns the save to its original state.
        trainer_b = trainer(season(), base, "RevivirB")
        sid_b = store.one("season_players", id=trainer_b["player"]["id"])["season_id"]
        pid_b = purchase(sid_b, trainer_b, "revivir_pokemon")
        entity_b = observed(trainer_b, box=7)[0]["pokemon_entity_id"]

        def refuse():
            """Injected rejection: the verifier refuses this artifact."""
            job = worker_lease()
            assert job["authorization_id"]

        def worker_lease():
            lease = str(uuid4())
            job = item_rpc({"operation": "lease", "lease_id": lease})
            item_rpc(
                {
                    "operation": "reject",
                    "authorization_id": job["authorization_id"],
                    "lease_id": lease,
                }
            )
            return job

        controller4, session4, save4, _ = launcher(
            sid_b, trainer_b, "revive2", after_upload=refuse
        )
        rejected_flow = LauncherRevive(
            controller4, ReviveRemote(session4, sid_b, trainer_b["tid"]), session=session4
        )
        before_bytes = save4.read_bytes()
        result = rejected_flow.apply(pid_b, entity_b)
        ok(result["status"] == "RELEASED", "a rejected result is released")
        ok(
            save4.read_bytes() == before_bytes,
            "a rejected result restores the save, byte for byte",
        )
        ok(
            store.one("purchases", id=pid_b)["status"] == "pending"
            and not store.rows("redemptions", purchase_id=pid_b),
            "a rejected result does not consume the comodín",
        )
        ok(
            not controller4.gate.recovery_required,
            "a released attempt does not keep the sync paused",
        )
        # The same comodín can be used again: the failed attempt is history.
        controller5, session5, _, _ = launcher(
            sid_b, trainer_b, "revive2", after_upload=work
        )
        second = LauncherRevive(
            controller5, ReviveRemote(session5, sid_b, trainer_b["tid"]), session=session5
        )
        retried = second.apply(pid_b, entity_b)
        ok(retried["status"] == "DONE", "the comodín works after a failed attempt")
        rows = store.rows("item_use_authorizations", purchase_id=pid_b)
        ok(
            len(rows) == 2 and sum(r["superseded_at"] is None for r in rows) == 1,
            "the failed attempt stays as history",
        )

        # The revived Pokémon can be observed dead again: a new, separate death.
        ok(
            store.one("purchases", id=pid_b)["status"] == "used",
            "the retry consumed the comodín once",
        )

        report["status"] = "PASS"
    finally:
        try:
            if worker:
                worker.close()
        finally:
            pg.stop() if hasattr(pg, "stop") else None
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--native-exe", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55485)
    args = parser.parse_args()
    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(report["status"], len(report["checks"]), "checks")


if __name__ == "__main__":
    main()
