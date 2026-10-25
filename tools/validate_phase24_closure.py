"""Focused 24A finalization proof; disposable PostgreSQL and two real journals.

Native mutation matrices are retained, not rerun. The existing eight-title
fixture journey is extended through the newly implemented SQL/identity boundary.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import psycopg

from app.repositories.errors import PersistenceError
from app.repositories.transfer_verifier_pg import TransferVerifierPG
from tools.validate_phase24_local import run


def closure(env):
    c, aid, pg, rpc, store, verifier = (
        env[k] for k in ("c", "aid", "pg", "rpc", "store", "verifier")
    )
    passed = env["passed"]
    # The helper is module-global in the inherited runner.
    from tools.validate_phase23d_local import rejected

    def private_rows(table, where="true"):
        raw = pg.sql(
            f"select coalesce(jsonb_agg(to_jsonb(t)),'[]'::jsonb) from public.{table} t where {where};"
        ).stdout.strip()
        import json

        return json.loads(raw or "[]")

    request = verifier.finalization_request(aid)
    before_entity = store.one("pokemon_entities", id=c["entity"])
    old_head = store.one("pokemon_identity_revisions", save_file_id=c["source"]["save"])
    old_observations = store.rows("pokemon_observations", revision_id=old_head["id"])
    wrong = deepcopy(request)
    wrong["requests"]["destination"]["sha256"] = "a" * 64
    rejected(lambda: rpc(wrong), PersistenceError)
    assert store.one("purchases", id=c["purchase"])["status"] == "pending"

    if env["game"] == "X":

        def snapshot():
            return {
                name: pg.sql(
                    f"select coalesce(jsonb_agg(to_jsonb(t) order by to_jsonb(t)::text),'[]') from public.{name} t;"
                ).stdout
                for name in (
                    "save_files",
                    "parsed_saves",
                    "season_players",
                    "pokemon_entities",
                    "pokemon_identity_revisions",
                    "pokemon_observations",
                    "pokemon_entity_flags",
                    "purchases",
                    "redemptions",
                    "robbery_cycles",
                    "trainer_flags",
                    "activity_events",
                    "item_use_authorizations",
                    "item_use_transfers",
                    "item_use_transfer_legs",
                    "transfer_provenance",
                    "transfer_commit_permits",
                )
            }

        baseline = snapshot()
        # Failure AFTER025 effects, owner movement and both registrations. Entire
        # transaction rolls back; physical files remain applied and must not revert.
        pg.sql("""create function public.test24_fail() returns trigger language plpgsql as $$
          begin if new.status='APPLIED_VERIFIED' then raise exception 'injected final failure'; end if; return new; end $$;
          create trigger test24_fail before update on public.item_use_authorizations for each row execute function public.test24_fail();""")
        rejected(lambda: rpc(request), PersistenceError)
        assert snapshot() == baseline
        pg.sql(
            "drop trigger test24_fail on public.item_use_authorizations; drop function public.test24_fail();"
        )
        for side in ("source", "destination"):
            b = env["donor"] if side == "source" else env["receiver"]
            assert (
                b.engine.reconcile(env["plans"][side].operation_id).status
                == "APPLIED_VERIFIED"
            )
            rejected(lambda b=b: b.cancel(aid), PersistenceError)
        passed(
            "injected final SQL failure restores all17 tables; physical receipts/backups retained; unilateral cancellation denied"
        )

        def commit(_):
            with psycopg.connect(
                host="127.0.0.1",
                port=pg.port,
                dbname="pokeapp_v2_validation_accounts",
                user="phase24_worker",
                autocommit=True,
            ) as connection:
                return TransferVerifierPG(connection)(request)

        with ThreadPoolExecutor(max_workers=2) as pool:
            replies = list(pool.map(commit, range(2)))
        assert replies[0] == replies[1]
        result = replies[0]
        passed(
            "concurrent finalizers exactly one effect and identical terminal receipt"
        )
    else:
        result = rpc(request)
    assert result["status"] == "COMMITTED"
    # Simulate lost final response: start from status BEFORE re-derivation. This
    # would fail if it tried to reverify the now-obsolete donor context.
    assert verifier.finalize(aid) == result == rpc(request)
    entity = store.one("pokemon_entities", id=c["entity"])
    assert entity["owner_trainer_id"] == c["destination"]["tid"]
    for key in ("id", "initial_evidence", "candidate_key", "created_at"):
        assert entity[key] == before_entity[key]
    assert (
        store.rows("pokemon_observations", revision_id=old_head["id"])
        == old_observations
    )
    assert store.one("purchases", id=c["purchase"])["status"] == "used"
    redemptions = store.rows("redemptions", purchase_id=c["purchase"])
    assert len(redemptions) == 1
    gifts = store.rows("purchases", origin_redemption_id=redemptions[0]["id"])
    assert len(gifts) == 1 and gifts[0]["trainer_id"] == c["destination"]["tid"]
    flags = store.rows("pokemon_entity_flags", pokemon_entity_id=c["entity"])
    assert {f["flag_type"] for f in flags} >= {
        "blindado",
        "robado",
        "robado_from",
        "robado_at",
    }
    assert all(f["trainer_id"] == c["destination"]["tid"] for f in flags)
    assert len(private_rows("transfer_provenance", f"authorization_id='{aid}'")) == 1
    assert not private_rows("transfer_commit_permits")
    for side in ("source", "destination"):
        tid = c[side]["tid"]
        saved = result["receipt"][side]["save_id"]
        assert (
            store.one("season_players", season_id=c["season_id"], trainer_id=tid)[
                "current_save_file_id"
            ]
            == saved
        )
        context = env["sources"].execute(
            "context", {"season_id": c["season_id"], "trainer_id": tid}
        )
        assert (c["entity"] in context["proven_entity_ids"]) == (side == "destination")
        if side == "destination":
            head = store.one("pokemon_identity_revisions", save_file_id=saved)
            target = store.one(
                "pokemon_observations",
                revision_id=head["id"],
                pokemon_entity_id=c["entity"],
            )
            assert (
                target["outcome"] == "MATCHED"
                and target["evidence"]["source_trainer_match"] is False
            )
        b, _ = env["bridge"](c, side, aid, env["plans"][side])
        assert (
            b.state(aid)["completed"] is True
            and not b.controller.gate.recovery_required
        )
    passed(
        env["game"]
        + " atomic owner/save/identity/025 effects, immutable provenance, terminal replay and two restarted Launcher gates"
    )

    if env["game"] == "X":
        # Registration contexts must support ordinary subsequent sync while
        # foreign OT remains literal false; unit tests exercise edited evidence.
        from app.application.save_ingestion import registration_request

        context = env["sources"].execute(
            "context",
            {"season_id": c["season_id"], "trainer_id": c["destination"]["tid"]},
        )
        parsed = env["parser"].parse(env["rp"].read_bytes())
        fresh = registration_request(
            c["season_id"],
            c["destination"]["tid"],
            sha256(env["rp"].read_bytes()).hexdigest(),
            context["current_save_id"],
            parsed,
            env["parser"].version,
            context,
        )
        bindings = fresh["identity_plan"]["bindings"]
        assert (
            sum(
                b["pokemon_entity_id"] == c["entity"] and b["outcome"] == "MATCHED"
                for b in bindings
            )
            == 1
        )
        # Retired donor cannot reacquire the individual by re-uploading original
        # bytes under another hash: collision registry feeds ordinary ingestion.
        donor_context = env["sources"].execute(
            "context", {"season_id": c["season_id"], "trainer_id": c["source"]["tid"]}
        )
        old = env["parser"].parse(c["source"]["data"])
        clone = registration_request(
            c["season_id"],
            c["source"]["tid"],
            sha256(c["source"]["data"]).hexdigest(),
            donor_context["current_save_id"],
            old,
            env["parser"].version,
            donor_context,
        )
        assert clone["identity_plan"]["bindings"][0]["outcome"] == "AMBIGUOUS"
        # Existing identical old-source receipt never rewinds current pointer.
        receipt = env["ingestion"].receipt(
            c["season_id"], c["source"]["tid"], sha256(c["source"]["data"]).hexdigest()
        )
        assert not receipt.is_current
        passed(
            "ordinary sync builder preserves foreign-OT UUID; retired donor clone blocked and old receipt cannot rewind"
        )

        cancelled = env["setup"]("X")
        ca = env["repo"].reserve(cancelled["request"])["authorization_id"]
        plans = verifier.prepare(ca)
        left, left_path = env["bridge"](cancelled, "source", ca, plans["source"])
        right, right_path = env["bridge"](
            cancelled, "destination", ca, plans["destination"]
        )
        left.prepare(ca, closed_emulator_confirmed=True)
        right.prepare(ca, closed_emulator_confirmed=True)
        assert left.cancel(ca)["status"] == "CANCELLED"
        assert right.state(ca)["status"] == "CANCELLED"
        assert (
            not left.controller.gate.recovery_required
            and not right.controller.gate.recovery_required
        )
        assert (
            left_path.read_bytes() == cancelled["source"]["data"]
            and right_path.read_bytes() == cancelled["destination"]["data"]
        )
        env["unconsumed"](cancelled)
        assert left.apply(ca, closed_emulator_confirmed=True)["status"] != "COMMITTED"
        passed(
            "paired pre-apply cancellation, no physical rollback, originals/unused purchase preserved and both gates released"
        )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for name in ("pg-bin", "native-exe", "fixtures", "output"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument(
        "--games", nargs="+", default=["X", "Y", "OR", "AS", "SN", "MN", "US", "UM"]
    )
    p.add_argument("--skip-parity", action="store_true")
    p.add_argument("--additional", action="store_true")
    run(p.parse_args(), closure)
