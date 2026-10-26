"""Phase27A disposable end-to-end proof: server-authoritative robbery.

Disposable PostgreSQL (bootstrap 001-061), the real FastAPI transfer routes, two
Launchers (real safe write engine + AuthenticatedTransferRemote over HTTP) and the
restricted verifier with the real native PKHeX writer/parser. Retained public
fixtures only: no owner save, no network, no production.
"""

import argparse
import json
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

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.security import require_enabled_principal
from app.application.item_use_worker import SignedArtifactReader
from app.application.save_ingestion import TrustedSaveIngestion
from app.application.transfer_integration import TransferIntegration
from app.application.transfer_transport import TransferTransport
from app.application.transfer_verification import TransferVerification
from app.application.transfer_worker import run_transfer_step
from app.launcher.quick_items import quick_item_intent
from app.launcher.save_activity import SaveActivityGate
from app.launcher.transfer import AuthenticatedTransferRemote, LauncherTransfers
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import (
    PRODUCTION_MUTATIONS,
    EngineeringCapability,
    LocalWriteEngine,
)
from app.launcher.write_files import WindowsWriteFiles, WriteSafetyError
from app.repositories.supabase.transfer import TransferRepository
from app.repositories.transfer_verifier_pg import TransferVerifierPG
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.registration import observation_digest
from app.save_parser.writer import PkhexProcessWriter
from tools.validate_accounts_local import LocalPG
from tools.validate_phase23_local import parity
from tools.validate_phase23c_local import LocalSourceStore, LocalVerifierStore
from tools.validate_phase23d_local import Blobs, rejected
from tools.validate_supabase_v2_identity_sql import LocalClient


class ApiError(Exception):
    def __init__(self, status, code):
        super().__init__(f"{status}:{code}")
        self.status, self.code = status, code


class ApiSession:
    """The Launcher's authenticated session, over the real FastAPI routes."""

    def __init__(self, client, tid):
        self.client, self.headers = client, {"Authorization": "Bearer " + tid}

    def _reply(self, response, missing=False):
        if missing and response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise ApiError(response.status_code, response.json()["detail"]["code"])
        return response.json()

    def request(self, method, path, *, body=None, missing=False):
        return self._reply(
            self.client.request(method, path, json=body, headers=self.headers),
            missing,
        )

    def upload(self, path, data):
        headers = self.headers | {"Content-Type": "application/octet-stream"}
        return self._reply(self.client.put(path, content=data, headers=headers))


def run(args):
    pg = LocalPG(args.pg_bin, 55478)
    report = {
        "status": "RUNNING",
        "checks": [],
        "scenarios": [],
        "cluster": str(pg.root),
    }
    worker = None

    def passed(label):
        report["checks"].append(label)
        print("PASS", label, flush=True)

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
        pg.sql(
            "create role phase27_worker login nosuperuser nocreatedb nocreaterole nobypassrls; grant pokeapp_item_verifier to phase27_worker;"
        )
        worker = psycopg.connect(
            host="127.0.0.1",
            port=pg.port,
            dbname="pokeapp_v2_validation_accounts",
            user="phase27_worker",
            autocommit=True,
        )
        rpc = TransferVerifierPG(worker)
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
        assert not PRODUCTION_MUTATIONS

        def insert(table, row):
            return client.table(table).insert(row).execute().data[0]

        def drain():
            outcomes = []
            for _ in range(12):
                step = run_transfer_step(rpc, verifier)
                if not step:
                    return outcomes
                outcomes += step
                assert all(o["outcome"] == "DONE" for o in step), step
            raise AssertionError("worker did not settle")

        def played(data):
            """The victim/robber played on: a real native change (bag item)."""
            intent = quick_item_intent(native, data, "rare_candy", 1)
            return native.prepare(data, intent).output

        def world(game, *, robber_game=None, origin="box"):
            pg.sql(
                "update seasons set status='draft',started_at=null where status='active';"
            )
            sid = insert(
                "seasons",
                {
                    "name": "27A " + str(uuid4()),
                    "status": "active",
                    "started_at": "2026-10-01T00:00:00Z",
                },
            )["id"]
            c = {"season_id": sid, "game": game}
            for side, fixture in (
                ("source", game),
                ("destination", robber_game or game),
            ):
                tid = str(uuid4())
                insert(
                    "trainers",
                    {
                        "id": tid,
                        "display_name": "Disposable " + tid[:8],
                        "slug": "t27-" + tid,
                    },
                )
                player = insert("season_players", {"season_id": sid, "trainer_id": tid})
                data = (args.fixtures / fixture / side).read_bytes()
                receipt = ingestion.receive(
                    sid,
                    tid,
                    sha256(data).hexdigest(),
                    None,
                    observation_digest(parser.parse(data), parser.version),
                    data,
                )
                c[side] = {
                    "tid": tid,
                    "player": player,
                    "data": data,
                    "save": receipt.save_id,
                }
            head = store.one(
                "pokemon_identity_revisions", save_file_id=c["source"]["save"]
            )
            observations = store.rows("pokemon_observations", revision_id=head["id"])
            if origin == "party":
                party = [o for o in observations if o["source"] == "party"]
                eligible = [
                    o
                    for o in party
                    if o["outcome"] in ("NEW", "MATCHED")
                    and o["evidence"]["source_trainer_match"]
                ]
                if len(party) < 2 or not eligible:
                    return None
                chosen = eligible[-1]
            else:
                chosen = next(
                    o
                    for o in observations
                    if o["source"] == "box"
                    and o["box_number"] == 1
                    and o["slot_number"] == 1
                )
            item = store.one("shop_items", code="robar_pokemon")
            purchase = insert(
                "purchases",
                {
                    "season_id": sid,
                    "trainer_id": c["destination"]["tid"],
                    "season_player_id": c["destination"]["player"]["id"],
                    "shop_item_id": item["id"],
                    "unit_price": item["base_price"],
                },
            )
            c.update(
                purchase=purchase["id"],
                entity=chosen["pokemon_entity_id"],
                origin=chosen,
            )
            service = TransferIntegration(
                repo,
                transport,
                allowed_trainers=[c["source"]["tid"], c["destination"]["tid"]],
            )

            def principal(authorization: Annotated[str, Header()]):
                return SimpleNamespace(trainer_id=authorization.removeprefix("Bearer "))

            api = create_app(container=ApiContainer(transfer_integration=service))
            api.dependency_overrides[require_enabled_principal] = principal
            c["http"] = TestClient(api)
            return c

        def reserve(c, key=None):
            """Robber's request through the API. With an explicit key, the raw reply."""
            reply = c["http"].post(
                f"/v1/seasons/{c['season_id']}/shop/purchases/{c['purchase']}/transfer",
                json={"pokemon_entity_id": c["entity"]},
                headers={
                    "Authorization": "Bearer " + c["destination"]["tid"],
                    "Idempotency-Key": key or str(uuid4()),
                },
            )
            if key is not None:
                return reply
            assert reply.status_code == 200, reply.text
            return reply.json()

        def launcher(c, side, *, running=(), fault=None, data=None):
            root = pg.root / f"{c['season_id']}-{side}"
            root.mkdir(exist_ok=True)
            target = root / "main"
            if data is not None:
                target.write_bytes(data)
            elif not target.exists():
                target.write_bytes(c[side]["data"])
            engine = LocalWriteEngine(
                root / "profile",
                native,
                files=WindowsWriteFiles(process_names=lambda: list(running)),
                engineering_capability=EngineeringCapability.for_fixture_root(root),
                fault_hook=fault,
            )
            controller = LocalWriteController(
                SaveActivityGate(), lambda: str(target), engine
            )
            remote = AuthenticatedTransferRemote(
                ApiSession(c["http"], c[side]["tid"]), c["season_id"], c[side]["tid"]
            )
            return LauncherTransfers(controller, remote), target

        def listing(c, side):
            return ApiSession(c["http"], c[side]["tid"]).request(
                "GET", f"/v1/launcher/seasons/{c['season_id']}/transfers"
            )["items"]

        def leg(c, side, aid):
            return next(i for i in listing(c, side) if i["authorization_id"] == aid)

        def decided(c, aid):
            purchase = store.one("purchases", id=c["purchase"])
            assert purchase["status"] != "pending", purchase["status"]
            assert len(store.rows("redemptions", purchase_id=c["purchase"])) == 1
            entity = store.one("pokemon_entities", id=c["entity"])
            assert entity["owner_trainer_id"] == c["destination"]["tid"]
            flags = {
                f["flag_type"]
                for f in store.rows(
                    "pokemon_entity_flags", pokemon_entity_id=c["entity"]
                )
                if f["flag_value"]
            }
            assert {"robado", "blindado"} <= flags, flags
            return entity

        def undecided(c):
            assert store.one("purchases", id=c["purchase"])["status"] == "pending"
            assert not store.rows("redemptions", purchase_id=c["purchase"])
            assert (
                store.one("pokemon_entities", id=c["entity"])["owner_trainer_id"]
                == c["source"]["tid"]
            )

        def current_revision(c, side):
            player = store.one(
                "season_players", season_id=c["season_id"], trainer_id=c[side]["tid"]
            )
            return store.one(
                "pokemon_identity_revisions",
                save_file_id=player["current_save_file_id"],
            )

        def holds(c, side):
            return [
                o["outcome"]
                for o in store.rows(
                    "pokemon_observations", revision_id=current_revision(c, side)["id"]
                )
                if o["pokemon_entity_id"] == c["entity"]
            ]

        def team_lock(c, side):
            """Fire ONLY the 27A guard (FKs disabled in a rolled-back transaction)."""
            player = store.one(
                "season_players", season_id=c["season_id"], trainer_id=c[side]["tid"]
            )
            save = store.one("save_files", id=player["current_save_file_id"])
            return pg.sql(
                "begin; alter table public.team_locks disable trigger all;"
                " alter table public.team_locks enable trigger team_lock_robbery_guard;"
                " insert into public.team_locks(season_id,matchday_id,trainer_id,season_player_id,"
                "save_file_id,save_sha256,public_team_snapshot) values("
                f"'{c['season_id']}','{uuid4()}','{c[side]['tid']}','{player['id']}',"
                f"'{save['id']}','{save['sha256']}','[]'); rollback;",
                ok=False,
            )

        def reconciled(c, aid):
            assert leg(c, "source", aid)["status"] == "RECONCILED"
            assert holds(c, "source") == [] and holds(c, "destination") == ["MATCHED"]
            entity = decided(c, aid)
            assert (
                entity["initial_evidence"] == c["origin"]["evidence"]
            )  # OT/identity kept
            assert (
                store.one("item_use_authorizations", id=aid)["status"]
                == "APPLIED_VERIFIED"
            )

        # ---------- A: both online and cooperative (cases 1, 11, 8, 13, 14) ----------
        c = world("X")
        with ThreadPoolExecutor(max_workers=2) as pool:
            key = str(uuid4())
            replies = list(pool.map(lambda _: reserve(c, key), range(2)))
        assert all(r.status_code == 200 for r in replies), [r.text for r in replies]
        aid = replies[0].json()["authorization_id"]
        assert replies[1].json()["authorization_id"] == aid
        assert replies[0].json()["status"] == "REQUESTED"
        try:
            ApiSession(c["http"], c["source"]["tid"]).request(
                "POST", f"/v1/seasons/{c['season_id']}/transfers/{aid}/cancel"
            )
            raise AssertionError("victim cancelled")
        except ApiError as error:
            assert error.code == "TRANSFER_VICTIM_CANNOT_CANCEL"
        undecided(c)
        passed("A: one authority for concurrent identical requests; victim cannot veto")
        run_transfer_step(rpc, verifier)  # plan only
        assert leg(c, "source", aid)["status"] == "ELIGIBILITY_VERIFIED"
        undecided(c)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: verifier.adjudicate(aid), range(2)))
        decided(c, aid)
        assert leg(c, "source", aid)["status"] == "COMPETITIVELY_ADJUDICATED"
        assert leg(c, "source", aid)["obligation"] == "DONOR_PHYSICAL_PENDING"
        assert leg(c, "destination", aid)["obligation"] == "RECIPIENT_PHYSICAL_PENDING"
        assert holds(c, "destination") == []  # adjudicated, not yet physically usable
        passed("A: adjudication once under concurrent verifiers; nothing physical yet")
        for side in ("source", "destination"):
            try:
                ApiSession(c["http"], c[side]["tid"]).request(
                    "POST", f"/v1/seasons/{c['season_id']}/transfers/{aid}/cancel"
                )
                raise AssertionError("cancel after decision")
            except ApiError as error:
                assert error.code in (
                    "TRANSFER_ADJUDICATED",
                    "TRANSFER_VICTIM_CANNOT_CANCEL",
                )
        assert (
            team_lock(c, "source").returncode
            and "transfer_removal_pending" in team_lock(c, "source").stderr
        )
        passed("A: nobody can cancel a decided robbery; victim cannot lock a team")
        victim, vpath = launcher(c, "source", running=("lime3ds.exe",))
        rejected(
            lambda: victim.fulfil(aid, closed_emulator_confirmed=True), WriteSafetyError
        )
        assert vpath.read_bytes() == c["source"]["data"]
        passed(
            "A: emulator open blocks the mandatory removal before any change (case 8)"
        )
        victim, vpath = launcher(c, "source")
        assert victim.obligations()[0]["authorization_id"] == aid
        victim.fulfil(aid, closed_emulator_confirmed=True)
        drain()
        assert leg(c, "source", aid)["obligation"] == "DONOR_VERIFIED"
        assert holds(c, "source") == []
        assert team_lock(c, "source").returncode == 0
        assert verifier.settle(aid, "source")["obligation"] == "VERIFIED"  # lost reply
        assert verifier.verify(aid, "source")["verified"] is True
        passed(
            "A: victim removal verified and registered; retries are no-ops (case 14)"
        )
        robber, _ = launcher(c, "destination")
        robber.fulfil(aid, closed_emulator_confirmed=True)
        drain()
        reconciled(c, aid)
        assert robber.refresh(aid)["completed"] is True
        report["scenarios"].append({"name": "A", "game": "X", "status": "RECONCILED"})
        passed("A: robber received canonical bytes; RECONCILED with identity kept")

        # ---------- B: victim offline for days, plays first (cases 2-6, 10, 12) ----------
        c = world("X")
        aid = reserve(c)["authorization_id"]
        drain()  # plan + adjudicate with NO Launcher online
        decided(c, aid)
        robber, _ = launcher(c, "destination")
        robber.fulfil(aid, closed_emulator_confirmed=True)
        drain()
        assert leg(c, "destination", aid)["obligation"] == "RECIPIENT_VERIFIED"
        assert leg(c, "source", aid)["status"] == "COMPETITIVELY_ADJUDICATED"
        # The victim's accepted save still physically lists it (pending removal);
        # competitively it already belongs to the robber.
        assert holds(c, "destination") == ["MATCHED"] and holds(c, "source") == ["NEW"]
        passed(
            "B: decision and robber delivery complete while the victim never connects"
        )
        progressed = played(c["source"]["data"])
        rejected(
            lambda: ingestion.receive(
                c["season_id"],
                c["source"]["tid"],
                sha256(progressed).hexdigest(),
                c["source"]["save"],
                observation_digest(parser.parse(progressed), parser.version),
                progressed,
            ),
            Exception,
        )
        assert team_lock(c, "source").returncode
        passed(
            "B: ordinary victim sync and team lock refused until the removal (case 10)"
        )
        victim, vpath = launcher(
            c, "source", data=progressed
        )  # days later, after playing
        assert (
            victim.fulfil(aid, closed_emulator_confirmed=True)["status"] == "REPLANNING"
        )
        assert vpath.read_bytes() == progressed  # nothing modified while re-planning
        drain()
        replanned = leg(c, "source", aid)
        assert replanned["source_sha256"] == sha256(progressed).hexdigest()
        assert replanned["pair_id"] != aid
        victim.fulfil(aid, closed_emulator_confirmed=True)
        drain()
        reconciled(c, aid)
        final = parser.parse(vpath.read_bytes())
        assert final.trainer == parser.parse(progressed).trainer
        report["scenarios"].append({"name": "B", "game": "X", "status": "RECONCILED"})
        passed(
            "B: played save re-planned on current bytes; progress kept; RECONCILED (cases 3-6)"
        )

        # ---------- C: victim no longer holds it; robber offline first (cases 7, 12) ----------
        c = world("Y")
        aid = reserve(c)["authorization_id"]
        drain()
        decided(c, aid)
        without = native.prepare(
            c["source"]["data"],
            native.plan_transfer(
                c["source"]["data"],
                c["destination"]["data"],
                pair_id=str(uuid4()),
                location="box",
                box_index=0,
                slot_index=0,
                target_pid=c["origin"]["evidence"]["pid"],
                target_ec=c["origin"]["evidence"]["encryption_constant"],
            )["source"],
        ).output  # released elsewhere, outside PokeApp
        victim, vpath = launcher(c, "source", data=without)
        victim.fulfil(aid, closed_emulator_confirmed=True)
        drain()
        assert leg(c, "source", aid)["obligation"] == "DONOR_ABSENT_VERIFIED"
        assert vpath.read_bytes() == without
        robber, _ = launcher(c, "destination")
        robber.fulfil(aid, closed_emulator_confirmed=True)
        drain()
        reconciled(c, aid)
        report["scenarios"].append({"name": "C", "game": "Y", "status": "RECONCILED"})
        passed(
            "C: victim save without the Pokémon accepted as verified absence; no clone"
        )

        # ---------- D: restart during removal (case 9) ----------
        c = world("X")
        aid = reserve(c)["authorization_id"]
        drain()

        def crash(stage):
            if stage == "before_park":
                raise WriteSafetyError("INJECTED_CRASH")

        victim, vpath = launcher(c, "source", fault=crash)
        result = victim.fulfil(aid, closed_emulator_confirmed=True)
        assert result["status"] == "RECOVERY_REQUIRED", result
        assert vpath.read_bytes() == c["source"]["data"]
        victim, vpath = launcher(c, "source")  # restarted Launcher
        assert (
            victim.fulfil(aid, closed_emulator_confirmed=True)["status"] == "REPLANNING"
        )
        drain()
        replanned = leg(c, "source", aid)
        assert replanned["pair_id"] != aid and replanned["intent"] is not None, (
            replanned
        )
        retried = victim.fulfil(aid, closed_emulator_confirmed=True)
        steps = drain()
        assert leg(c, "source", aid)["obligation"] == "DONOR_VERIFIED", (
            retried,
            steps,
            leg(c, "source", aid),
        )
        robber, _ = launcher(c, "destination")
        robber.fulfil(aid, closed_emulator_confirmed=True)
        drain()
        reconciled(c, aid)
        report["scenarios"].append({"name": "D", "game": "X", "status": "RECONCILED"})
        passed(
            "D: interrupted removal kept the original; restart re-planned once; RECONCILED"
        )

        # ---------- E: concurrent operations and cross-title (case 13, decision B) ----------
        c = world("X", robber_game="Y")
        reply = reserve(c, str(uuid4()))
        assert (
            reply.status_code == 409
            and reply.json()["detail"]["code"] == "TRANSFER_CROSS_TITLE_FORBIDDEN"
        ), reply.text
        undecided(c)
        c = world("X")
        aid = reserve(c)["authorization_id"]
        copy = store.one("purchases", id=c["purchase"])
        second = insert(
            "purchases",
            {
                k: copy[k]
                for k in (
                    "season_id",
                    "trainer_id",
                    "season_player_id",
                    "shop_item_id",
                    "unit_price",
                )
            },
        )
        reply = c["http"].post(
            f"/v1/seasons/{c['season_id']}/shop/purchases/{second['id']}/transfer",
            json={"pokemon_entity_id": c["entity"]},
            headers={
                "Authorization": "Bearer " + c["destination"]["tid"],
                "Idempotency-Key": str(uuid4()),
            },
        )
        assert (
            reply.status_code == 409
            and reply.json()["detail"]["code"] == "TRANSFER_RESERVED"
        ), reply.text
        passed(
            "E: cross-title refused at reservation; a second concurrent robbery refused"
        )

        # ---------- G: manipulated material (foreign file, tampered result) ----------
        c = world("X")
        aid = reserve(c)["authorization_id"]
        drain()
        foreign = c["destination"]["data"]  # another trainer's save offered as "mine"
        victim, vpath = launcher(c, "source", data=foreign)
        assert (
            victim.fulfil(aid, closed_emulator_confirmed=True)["status"] == "REPLANNING"
        )
        drain()
        assert vpath.read_bytes() == foreign
        assert leg(c, "source", aid)["obligation"] == "DONOR_BLOCKED_UNCERTAIN"
        assert leg(c, "source", aid)["status"] == "BLOCKED_UNCERTAIN"
        decided(c, aid)  # an incident never hands the Pokémon back
        robber, _ = launcher(c, "destination")
        robber.fulfil(aid, closed_emulator_confirmed=True)
        artifact = rpc(
            {"operation": "artifact", "authorization_id": aid, "side": "destination"}
        )
        exact = blobs.objects[artifact["result_key"]]
        blobs.objects[artifact["result_key"]] = c["destination"]["data"]
        steps = run_transfer_step(rpc, verifier)
        assert [s["outcome"] for s in steps] == ["REJECTED"], steps
        assert (
            rpc(
                {
                    "operation": "artifact",
                    "authorization_id": aid,
                    "side": "destination",
                }
            )["proof"]
            is None
        )
        blobs.objects[artifact["result_key"]] = exact
        drain()
        assert leg(c, "destination", aid)["obligation"] == "RECIPIENT_VERIFIED"
        assert holds(c, "destination") == ["MATCHED"]
        report["scenarios"].append(
            {
                "name": "G",
                "game": "X",
                "status": "BLOCKED_UNCERTAIN (victim side, by design)",
            }
        )
        passed(
            "G: foreign file blocks only the victim side; tampered result issues no proof"
        )

        # ---------- F: party origin (owner decision A) ----------
        for game in args.party_games:
            c = world(game, origin="party")
            if c is None:
                report["scenarios"].append(
                    {"name": "F", "game": game, "status": "NO_ELIGIBLE_PARTY_FIXTURE"}
                )
                continue
            aid = reserve(c)["authorization_id"]
            drain()
            victim, _ = launcher(c, "source")
            victim.fulfil(aid, closed_emulator_confirmed=True)
            robber, _ = launcher(c, "destination")
            robber.fulfil(aid, closed_emulator_confirmed=True)
            drain()
            reconciled(c, aid)
            report["scenarios"].append(
                {"name": "F", "game": game, "origin": "party", "status": "RECONCILED"}
            )
            passed(f"F: team (party) robbery on {game} RECONCILED")
            break

        # ---------- Restricted issuer and grants ----------
        for role in ("anon", "authenticated", "service_role"):
            for call in (
                'select public.transfer_verifier(\'{"operation":"queue"}\');',
                f"select public.transfer_leg_view('{aid}','source');",
                f"select public.transfer_obligation('{aid}','source');",
                "select * from item_use_transfer_legs;",
            ):
                assert pg.sql(f"set role {role}; {call}", ok=False).returncode, (
                    role,
                    call,
                )
        assert not pg.sql(
            "select proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.prosecdef and p.prorettype<>'trigger'::regtype and has_function_privilege('phase27_worker',p.oid,'EXECUTE') and proname not in('item_verifier_job','transfer_verifier');"
        ).stdout.strip()
        passed("restricted issuer: only the verifier role decides, proves and settles")
        if not args.skip_parity:
            report["parity"] = parity(pg)
            passed("upgrade 001-060 + 061 equals bootstrap; existing data unchanged")
        report["status"] = "PASS"
    finally:
        if worker:
            worker.close()
        pg.stop()
        report["cleanup"] = "owned databases dropped; cluster stopped"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--pg-bin", type=Path, required=True)
    p.add_argument("--native-exe", type=Path, required=True)
    p.add_argument("--fixtures", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--skip-parity", action="store_true")
    p.add_argument(
        "--party-games",
        nargs="+",
        default=["X", "Y", "OR", "AS", "SN", "MN", "US", "UM"],
    )
    run(p.parse_args())
