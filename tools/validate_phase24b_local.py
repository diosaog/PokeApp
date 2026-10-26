"""Focused 24B proof: real FastAPI routes, two LauncherRuntimes, private worker.

Reuses the 24A runner/fixtures on disposable PostgreSQL; the inherited base flow
is completed with the already-proven finalizer, then the integrated journey runs
on a fresh season. Native and eight-title matrices are retained, not rerun.
"""

import argparse
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Annotated
from unittest.mock import Mock
from uuid import uuid4

from fastapi import Header
from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.security import require_enabled_principal
from app.application.transfer_integration import TransferIntegration
from app.application.transfer_worker import run_transfer_step
from app.launcher.backend import BackendClient, BackendPrincipal, SessionTokens
from app.launcher.runtime import LauncherRuntime
from app.launcher.write_control import LocalWriteController
from app.launcher.write_engine import EngineeringCapability, LocalWriteEngine
from app.launcher.write_files import WindowsWriteFiles
from app.save_parser.adapter import SaveInspector
from app.save_parser.registration import observation_digest
from tools.validate_phase24_local import run

ORIGIN = "http://127.0.0.1"


def integration(env):
    pg, store, passed, insert = env["pg"], env["store"], env["passed"], env["insert"]
    repo, transport, verifier, rpc = (
        env[k] for k in ("repo", "transport", "verifier", "rpc")
    )
    # Inherited base flow: the 24A finalizer, already proven; not re-tested here.
    assert verifier.finalize(env["aid"])["status"] == "COMMITTED"

    c = env["setup"]("X")
    sid, robber, victim = c["season_id"], c["destination"]["tid"], c["source"]["tid"]
    outsider = str(uuid4())
    insert(
        "trainers",
        {"id": outsider, "display_name": "Outsider", "slug": "outsider-" + outsider},
    )
    insert("season_players", {"season_id": sid, "trainer_id": outsider})
    cohort = TransferIntegration(repo, transport, allowed_trainers=[robber, victim])
    solo = TransferIntegration(repo, transport, allowed_trainers=[robber])

    def principal(authorization: Annotated[str, Header()]):
        return SimpleNamespace(trainer_id=authorization.removeprefix("Bearer "))

    def app(service):
        api = create_app(container=ApiContainer(transfer_integration=service))
        api.dependency_overrides[require_enabled_principal] = principal
        return api

    def auth(tid, key=None):
        headers = {"Authorization": "Bearer " + tid}
        if key:
            headers["Idempotency-Key"] = key
        return headers

    request_path = f"/v1/seasons/{sid}/shop/purchases/{c['purchase']}/transfer"
    body = {"pokemon_entity_id": c["entity"]}

    with TestClient(app(None)) as off:
        assert (
            off.post(
                request_path, json=body, headers=auth(robber, str(uuid4()))
            ).status_code
            == 503
        )
        assert off.get(f"/v1/seasons/{sid}/transfers", headers=auth(robber)).json() == {
            "items": [],
            "transfer_enabled": False,
        }
    with TestClient(app(solo)) as api:
        reply = api.post(request_path, json=body, headers=auth(robber, str(uuid4())))
        assert (
            reply.status_code == 409
            and reply.json()["detail"]["code"] == "TRANSFER_PEER_UNAVAILABLE"
        )
        assert not store.rows("item_use_authorizations", purchase_id=c["purchase"])
    passed(
        "disabled service, outsider-victim reservation refused before any reservation"
    )

    with TestClient(app(cohort)) as api:
        assert (
            api.post(
                request_path, json=body, headers=auth(outsider, str(uuid4()))
            ).status_code
            == 403
        )
        assert (
            api.post(
                request_path, json=body, headers=auth(robber, "not-a-uuid")
            ).status_code
            == 422
        )
        key = str(uuid4())
        first = api.post(request_path, json=body, headers=auth(robber, key))
        assert first.status_code == 200, first.text
        aid = first.json()["authorization_id"]
        assert (
            api.post(request_path, json=body, headers=auth(robber, key)).json()[
                "authorization_id"
            ]
            == aid
        )
        conflict = api.post(request_path, json=body, headers=auth(robber, str(uuid4())))
        assert conflict.status_code == 409
        web = {
            t: api.get(f"/v1/seasons/{sid}/transfers", headers=auth(t)).json()
            for t in (robber, victim, outsider)
        }
        assert web[outsider] == {"items": [], "transfer_enabled": False}
        assert [i["side"] for i in web[robber]["items"]] == ["destination"]
        assert [i["side"] for i in web[victim]["items"]] == ["source"]
        assert all(
            "intent" not in i and "source_sha256" not in i
            for t in (robber, victim)
            for i in web[t]["items"]
        )
        assert web[victim]["items"][0]["purchase_id"] is None
        leg_path = f"/v1/launcher/seasons/{sid}/transfers/{aid}"
        assert api.get(leg_path, headers=auth(outsider)).status_code == 403
        assert (
            api.get(
                f"/v1/launcher/seasons/{sid}/transfers", headers=auth(robber)
            ).json()["items"][0]["intent"]
            is None
        )
        passed(
            "authorized idempotent request, conflict, outsider denial and status-only web reads"
        )

        assert run_transfer_step(rpc, verifier) == [
            {"authorization_id": aid, "action": "plan", "outcome": "DONE"}
        ]
        assert run_transfer_step(rpc, verifier) == []
        launch = {
            t: api.get(f"/v1/launcher/seasons/{sid}/transfers", headers=auth(t)).json()[
                "items"
            ][0]
            for t in (robber, victim)
        }
        assert launch[robber]["intent"]["mutation"]["kind"] == "transfer_insert"
        assert launch[victim]["intent"]["mutation"]["kind"] == "transfer_remove"
        assert "transfer_remove" not in str(
            launch[robber]
        ) and "transfer_insert" not in str(launch[victim])
        passed(
            "private worker plans once; each Launcher receives only its own leg plan"
        )

        def runtime(tid, side, restart=False):
            root = pg.root / ("24b-" + aid + "-" + side)
            root.mkdir(exist_ok=True)
            target = root / "main"
            if not restart:
                target.write_bytes(c[side]["data"])
            r = LauncherRuntime(
                root / "launcher",
                SaveInspector(env["parser"]),
                client=BackendClient(ORIGIN, transport=api._transport),
                token_store=Mock(),
                start=False,
            )
            r.session._tokens = SessionTokens(
                user_id=tid, access_token=tid, expires_at=4102444800
            )
            r.session._principal = BackendPrincipal(
                trainer_id=tid, display_name=side, is_admin=False, globally_enabled=True
            )
            engine = LocalWriteEngine(
                root / "profile",
                env["native"],
                files=WindowsWriteFiles(process_names=list),
                engineering_capability=EngineeringCapability.for_fixture_root(root),
            )
            r.writes = LocalWriteController(
                r.save_activity,
                lambda: str(target),
                engine,
                on_verified=r._invalidate_written_save,
            )
            r.value["cloud"] = {"data": {"season": {"id": sid}}}
            return r, target

        def do(r, name, **extra):
            assert r.command(name, {"authorization_id": aid, **extra}) == {
                "status": "QUEUED"
            }
            r._write_step()
            return r.state()

        confirm = {"closed_emulator_confirmed": True}
        donor, dp = runtime(victim, "source")
        receiver, rp = runtime(robber, "destination")
        assert donor.state()["write"]["transfer_application_enabled"] is True
        assert (
            do(donor, "transfer_prepare", **confirm)["transfer_result"]["status"]
            == "WAITING_OTHER"
        )
        state = do(donor, "transfer_apply", **confirm)
        assert state["write_error"] and dp.read_bytes() == c["source"]["data"]
        assert (
            do(receiver, "transfer_prepare", **confirm)["transfer_result"]["status"]
            == "PENDING_SOURCE"
        )
        state = do(receiver, "transfer_apply", **confirm)
        assert state["write_error"] and rp.read_bytes() == c["destination"]["data"]
        assert (
            donor.save_activity.recovery_required
            and receiver.save_activity.recovery_required
        )
        passed(
            "both Launchers prepare verified backups; early/out-of-order application refused without file change"
        )

        state = do(donor, "transfer_apply", **confirm)
        assert state["transfer_result"]["status"] == "VERIFYING_SOURCE", state
        assert state["transfer_result"]["completed"] is False
        assert (
            dp.read_bytes()
            == (env["args"].fixtures / "X" / "source-result").read_bytes()
        )
        # Private table: service_role cannot read it (42501), so use the cluster owner.
        claim = pg.sql(
            f"select claim_id from public.item_use_transfer_legs where authorization_id='{aid}' and side='source';"
        ).stdout.strip()
        result_path = f"{leg_path}/result?claim_id={claim}"
        tampered = bytearray(dp.read_bytes())
        tampered[0x100] ^= 1
        assert (
            api.put(
                result_path,
                content=bytes(tampered),
                headers=auth(victim) | {"Content-Type": "application/octet-stream"},
            ).status_code
            == 409
        )
        assert (
            api.put(
                result_path,
                content=b"x",
                headers=auth(victim) | {"Content-Type": "text/plain"},
            ).status_code
            == 415
        )
        assert (
            api.put(
                leg_path,
                json={"operation": "begin", "claim_id": str(uuid4())},
                headers=auth(victim),
            ).status_code
            == 409
        )
        assert (
            api.put(
                leg_path,
                json={"operation": "begin", "claim_id": str(claim)},
                headers=auth(outsider),
            ).status_code
            == 403
        )
        assert (
            api.post(
                f"/v1/seasons/{sid}/transfers/{aid}/cancel", headers=auth(robber)
            ).status_code
            == 409
        )
        # Owner rule: a valid robbery needs no consent; the victim cannot veto
        # through the web or the Launcher leg route.
        assert (
            api.post(
                f"/v1/seasons/{sid}/transfers/{aid}/cancel", headers=auth(victim)
            ).status_code
            == 409
        )
        assert (
            api.put(
                leg_path, json={"operation": "cancel"}, headers=auth(victim)
            ).status_code
            == 409
        )
        # Restarted donor Launcher after a lost reply: reconcile, never reapply.
        donor, _ = runtime(victim, "source", restart=True)
        assert donor.save_activity.recovery_required
        assert (
            do(donor, "transfer_apply", **confirm)["transfer_result"]["status"]
            == "VERIFYING_SOURCE"
        )
        assert (
            dp.read_bytes()
            == (env["args"].fixtures / "X" / "source-result").read_bytes()
        )
        assert store.one("purchases", id=c["purchase"])["status"] == "pending"
        passed(
            "first part applied locally is not confirmation; tampered/foreign/wrong-claim uploads and post-apply cancel refused; restart replay idempotent"
        )

        assert run_transfer_step(rpc, verifier) == [
            {"authorization_id": aid, "action": "verify", "outcome": "DONE"}
        ]
        assert (
            api.get(f"/v1/seasons/{sid}/transfers", headers=auth(robber)).json()[
                "items"
            ][0]["status"]
            == "PENDING_DESTINATION"
        )
        state = do(receiver, "transfer_apply", **confirm)
        assert state["transfer_result"]["status"] == "VERIFYING_BOTH", state
        assert (
            rp.read_bytes()
            == (env["args"].fixtures / "X" / "destination-result").read_bytes()
        )
        assert run_transfer_step(rpc, verifier) == [
            {"authorization_id": aid, "action": "verify", "outcome": "DONE"}
        ]
        assert do(receiver, "transfer_refresh")["transfer_result"]["completed"] is False
        assert run_transfer_step(rpc, verifier) == [
            {"authorization_id": aid, "action": "finalize", "outcome": "DONE"}
        ]
        assert run_transfer_step(rpc, verifier) == []
        receipt = verifier.finalize(aid)  # lost final reply: identical terminal receipt
        assert receipt["status"] == "COMMITTED" and receipt == verifier.finalize(aid)
        passed(
            "worker verifies each side independently, finalizes once; replay returns identical receipt"
        )

        for r, tid in ((donor, victim), (receiver, robber)):
            state = do(r, "transfer_refresh")
            assert state["transfer_result"] == {
                "status": "COMMITTED",
                "message": state["transfer_result"]["message"],
                "completed": True,
            }
            assert (
                not r.save_activity.recovery_required
                and state["write"]["status"] != "RECOVERY_REQUIRED"
            )
        donor, _ = runtime(victim, "source", restart=True)
        receiver, _ = runtime(robber, "destination", restart=True)
        for r in (donor, receiver):
            assert not r.save_activity.recovery_required
            assert do(r, "transfer_refresh")["transfer_result"]["completed"] is True
        web = {
            t: api.get(f"/v1/seasons/{sid}/transfers", headers=auth(t)).json()["items"][
                0
            ]
            for t in (robber, victim)
        }
        assert web[robber]["status"] == web[victim]["status"] == "COMMITTED"
        assert (
            api.get(
                f"/v1/launcher/seasons/{sid}/transfers", headers=auth(robber)
            ).json()["items"][0]["intent"]
            is None
        )
        passed(
            "both Launchers and web report COMMITTED; gates released and stay released after restart"
        )

        entity = store.one("pokemon_entities", id=c["entity"])
        assert entity["owner_trainer_id"] == robber
        assert store.one("purchases", id=c["purchase"])["status"] == "used"
        redemptions = store.rows("redemptions", purchase_id=c["purchase"])
        assert len(redemptions) == 1
        assert (
            len(store.rows("purchases", origin_redemption_id=redemptions[0]["id"])) == 1
        )
        for side, tid, path in (("source", victim, dp), ("destination", robber, rp)):
            accepted = web[robber if side == "destination" else victim][
                "accepted_save_id"
            ]
            assert (
                store.one("season_players", season_id=sid, trainer_id=tid)[
                    "current_save_file_id"
                ]
                == accepted
            )
            data = path.read_bytes()
            parsed = env["parser"].parse(data)
            again = env["ingestion"].receive(
                sid,
                tid,
                sha256(data).hexdigest(),
                accepted,
                observation_digest(parsed, env["parser"].version),
                data,
            )
            assert again.save_id == accepted and again.is_current
            head = store.one("pokemon_identity_revisions", save_file_id=accepted)
            matched = store.rows(
                "pokemon_observations",
                revision_id=head["id"],
                pokemon_entity_id=c["entity"],
            )
            assert len(matched) == (side == "destination")
        assert (
            len(
                store.rows(
                    "pokemon_entities",
                    candidate_key=entity["candidate_key"],
                    season_id=sid,
                )
            )
            == 1
        )
        passed(
            "owner, both current saves, PC observations, single consumption/voucher; Launcher re-sync of result bytes is deduplicated, no clone"
        )

        c2 = env["setup"]("X")
        cohort.allowed = frozenset([c2["source"]["tid"], c2["destination"]["tid"]])
        path2 = (
            f"/v1/seasons/{c2['season_id']}/shop/purchases/{c2['purchase']}/transfer"
        )
        aid2 = api.post(
            path2,
            json={"pokemon_entity_id": c2["entity"]},
            headers=auth(c2["destination"]["tid"], str(uuid4())),
        ).json()["authorization_id"]
        run_transfer_step(rpc, verifier)
        aid, c, sid, victim_ = aid2, c2, c2["season_id"], c2["source"]["tid"]
        leg_path = f"/v1/launcher/seasons/{sid}/transfers/{aid}"
        donor2, dp2 = runtime(victim_, "source")
        assert (
            do(donor2, "transfer_prepare", **confirm)["transfer_result"]["status"]
            == "WAITING_OTHER"
        )
        withdrawn = api.post(
            f"/v1/seasons/{sid}/transfers/{aid}/cancel",
            headers=auth(c2["destination"]["tid"]),
        )
        assert (
            withdrawn.status_code == 200 and withdrawn.json()["status"] == "CANCELLED"
        )
        state = do(donor2, "transfer_refresh")
        assert (
            state["transfer_result"]["status"] == "CANCELLED"
            and not donor2.save_activity.recovery_required
        )
        assert dp2.read_bytes() == c2["source"]["data"]
        assert store.one("purchases", id=c2["purchase"])["status"] == "pending"
        assert not store.rows("redemptions", purchase_id=c2["purchase"])
        passed(
            "web withdrawal before application releases the prepared Launcher; original file and purchase untouched"
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("pg-bin", "native-exe", "fixtures", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--games", nargs="+", default=["X"])
    p.add_argument("--skip-parity", action="store_true")
    p.add_argument("--additional", action="store_true")
    p.add_argument("--origin", default="box")  # or party:N (Phase26B)
    run(p.parse_args(), integration)
