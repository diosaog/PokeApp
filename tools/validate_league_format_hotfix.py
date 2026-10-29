"""Synthetic loopback API/SQL acceptance for the five-player format form.

No production connection. Uses actual 001-073 RPCs, with only authentication
stubbed; the four configured matchdays are closed and replayed independently.
"""

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.application.matchdays import plan_close
from app.application.initial_assignment import plan_initial_assignment
from app.repositories.supabase.season_admin import SupabaseSeasonAdminRepository
from tools.phase30_release_audit import MIGRATIONS, SupabaseLikePG
from tools.validate_phase073_league import validate as validate_073
from tools import validate_phase21_native as native
from tools.validate_supabase_v2_identity_sql import LocalClient, SqlError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID


def validate(pg):
    # Keep the existing single-day prizes, death/wipe deductions and history gate.
    print(validate_073(pg), flush=True)
    pg.sql("alter database pokeapp rename to pokeapp_v2_validation_format;",
           user="supabase_admin", database="postgres")
    pg.database = "pokeapp_v2_validation_format"
    local = LocalClient(SimpleNamespace(
        host="127.0.0.1", port=pg.port, database=pg.database,
        psql=str(pg.bin / "psql.exe"), user="supabase_admin", password=""))
    local.table("trainers").insert(dict(id=TRAINER_ID, display_name="Format fixture",
        slug="format-admin", is_admin=True)).execute()
    app = create_app(container=ApiContainer(
        token_verifier=FakeTokenVerifier(), principal_repository=FakePrincipalRepository(),
        season_admin_repository=SupabaseSeasonAdminRepository(local)))
    with TestClient(app) as api:
        def call(path, body=None, status=200):
            headers = {"Authorization": "Bearer synthetic", "Idempotency-Key": uuid4().hex}
            response = (api.get(path, headers=headers) if body is None
                        else api.post(path, json=body, headers=headers))
            assert response.status_code == status, response.text
            return response.json()

        sid = call("/v1/admin/seasons", {"name": "Isolated five-player format"})["season_id"]
        base = f"/v1/admin/seasons/{sid}"
        for i in range(5):
            tid = str(uuid4())
            local.table("trainers").insert(dict(id=tid, display_name=f"Fixture {i}", slug=f"format-{i}")).execute()
            state = call(base + "/setup")
            call(base + "/participants", dict(trainer_id=tid, expected_roster_revision=state["roster_revision"]))

        points = {str(i): v for i, v in enumerate([10, 8, 6, 4, 2], 1)}
        coins = {str(i): v for i, v in enumerate([50, 40, 30, 20, 0], 1)}
        cid = None

        def save(days, sizes=None, bad=False):
            nonlocal cid
            state = call(base + "/setup")
            sizes = sizes or {"A": 5}
            single = days == 1 and "B" not in sizes
            scoring = {str(i): 0 for i in range(1, 6)} if single else points
            rewards = {str(i): 17 for i in range(1, 6)} if single else coins
            body = dict(name="Reglas de la Liga", effective_from_matchday=1, total_matchdays=days,
                division_sizes=sizes, movement_count=0, scoring=scoring, coin_rewards=rewards,
                rules=dict(team_lock_required=False, last_b_gets_steal="B" in sizes),
                expected_config_revision=state["config_revision"], expected_roster_revision=state["roster_revision"])
            if cid:
                body["reason"] = "Synthetic format switch"
            if bad:
                body["scoring"] = {k: v for k, v in points.items() if k != "5"}
                result = call(base + f"/config-versions/{cid}/replace-unused", body, 409)
                assert result["detail"]["code"] == "INVALID_REWARDS", result
                assert call(base + "/setup") == state, "rejected write changed setup"
                return
            path = base + "/config-versions" + (f"/{cid}/replace-unused" if cid else "")
            receipt = call(path, body)
            cid = receipt["resource_id"]
            stored = call(base + "/setup")["config_versions"][0]
            for key in ("total_matchdays", "scoring", "coin_rewards"):
                assert stored[key] == body[key], (key, stored)
            assert {k: v for k, v in stored["division_sizes"].items() if v is not None} == sizes
            row = local.table("season_config_versions").select("*").eq("id", cid).execute().data[0]
            assert row["scoring_json"] == scoring and row["coin_rewards_json"] == rewards

        save(1)
        save(4, bad=True)
        for days in (4, 1, 2, 1, 3, 4):
            save(days)
        save(4, {"A": 3, "B": 2})
        save(1, {"A": 3, "B": 2})  # two divisions retain positional rewards
        save(4)
        print("PASS API -> SQL: create/read/replace 1/2/3/4 days, five values, A and A/B, invalid four-value write is atomic", flush=True)

        # Apply the exact configuration saved through the HTTP API to four days.
        state = call(base + "/setup")
        call(base + "/activate", dict(expected_setup_revision=state["setup_revision"]))
        for player in state["participants"]:
            saved, parsed = str(uuid4()), str(uuid4())
            seed = "insert into public.save_files" + native.sql().split("insert into public.save_files", 1)[1].split("select case when", 1)[0]
            for old, new in ((native.TRAINER, player["trainer_id"]), (native.SEASON, sid),
                             (native.PLAYER, player["id"]), (native.SAVE, saved), (native.PARSED, parsed)):
                seed = seed.replace(old, new)
            boxes = [dict(box_number=b, slots=[dict(slot_number=s, pokemon=None) for s in range(1, 31)]) for b in range(1, 9)]
            seed = seed.replace('"boxes":[]', '"boxes":' + json.dumps(boxes))
            seed = seed.replace('[true,false,false,false,false,false,false,false]', '[true,true,false,false,false,false,false,false]')
            pg.sql(seed)
            local.table("pokemon_identity_revisions").insert(dict(season_id=sid, trainer_id=player["trainer_id"],
                save_file_id=saved, parsed_save_id=parsed, revision_number=1, capture_stream_id=str(uuid4()),
                capture_sequence=1, input_signature=native.SHA)).execute()
        request = dict(actor_trainer_id=TRAINER_ID, season_id=sid, idempotency_key="format-initial")
        context = local.rpc("initial_assignment_context", {"p_request": dict(operation="read", request=request)}).execute().data
        body = {key: context[key] for key in ("config_version_id", "input_hash")}
        body.update(expected_setup_revision=context["setup_revision"], expected_roster_revision=context["roster_revision"])
        request["body"] = body
        local.rpc("api_admin_finalize_initial_assignment", {"p_request": dict(request=request,
            input_hash=context["input_hash"], plan=plan_initial_assignment(context, body))}).execute()
        for number in range(1, 5):
            day = local.table("matchdays").select("*").eq("season_id", sid).eq("number", number).execute().data[0]["id"]
            pg.sql(f"update public.matchdays set status='open',opened_at=now() where id='{day}';"
                   f"update public.matches set status='completed',winner_id=least(player_a_id,player_b_id) where matchday_id='{day}';")
            request = dict(actor_trainer_id=TRAINER_ID, season_id=sid, resource_id=day,
                idempotency_key=f"format-close-{number}", body=dict(expected_results_revision=0))
            context = local.rpc("api_admin_matchday_context", {"p_request": dict(operation="close", request=request)}).execute().data
            cfg = context["context"]["inputs"]["config"]
            assert cfg["scoring_mode"] == "position_v1" and cfg["death_penalty_per_mon"] == "0.1"
            plan = plan_close(context["context"])
            envelope = dict(operation="close", request=request, input_hash=context["input_hash"], plan=plan)
            local.rpc("api_admin_matchday", {"p_request": envelope}).execute()
            replay = local.rpc("api_admin_matchday", {"p_request": envelope}).execute().data
            assert replay["replayed"] is True
            snapshot = local.table("matchday_snapshots").select("*").eq("matchday_id", day).execute().data[0]["snapshot"]
            assert len(snapshot["standings"]) == 5
            for row in snapshot["standings"]:
                assert row["points_awarded"] == points[str(row["position"])]
                assert row["coins_awarded"] == coins[str(row["position"])]
            ledger = local.table("coin_transactions").select("*").eq("reward_matchday_id", day).execute().data
            assert sum(row["amount"] for row in ledger) == 140
            assert len(ledger) == len({row["trainer_id"] for row in ledger}), "duplicate payout"
        assert len(local.table("matchdays").select("*").eq("season_id", sid).execute().data) == 4
        assert not local.table("purchases").select("*").eq("season_id", sid).execute().data, "single-day prizes leaked"
        print("PASS four actual closings + four replays: configured points/coins each day, no duplicate payouts or single-day prizes", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55583)
    args = parser.parse_args()
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        for migration in MIGRATIONS:
            pg.sql(migration.read_text(encoding="utf-8"))
        try:
            validate(pg)
        except SqlError as exc:
            raise AssertionError(f"Local fixture: {exc.code} {exc.message}") from exc
    finally:
        pg.stop()


if __name__ == "__main__":
    main()
