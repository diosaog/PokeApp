"""Phase 29 gates on a disposable loopback PostgreSQL: one league or two.

Bootstraps migrations 001-063 on an empty cluster and plays synthetic seasons
end to end through the production RPCs and the Python planners: creation,
enrollment, configuration, initial assignment, calendar, results, closes,
standings, rewards, champion, finish, archive and historical reads, for one
league (several participant counts) and for Liga A + Liga B. Also checks the
structure rules (validation, lock once started, one structure per season),
authority, idempotency and races. Synthetic trainers and saves only; no
remote configuration is loaded.

With --inherited, the inherited two-league competition validators (daily
ranking with promotion/relegation, championship, finalization) run on fresh
databases with the same bootstrap, proving two-league seasons behave as
before. Their residue snapshots read every table as the superuser: since 039
some tables are closed to service_role, and a superuser snapshot is stricter
than the original, never looser. (The inherited initial and results
validators predate 054's physical robbery verification and 039's closed
tables; that drift is unrelated to 063 and documented in the Phase 29 report.)
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from threading import Barrier
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = len(list((ROOT / "supabase/v2/migrations").glob("*.sql")))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from validate_accounts_local import LocalPG  # noqa: E402

from app.application.initial_assignment import plan_initial_assignment  # noqa: E402
from app.application.pokemon_identity import reconcile_parsed_save  # noqa: E402
from app.domain.pokemon_identity import CaptureOrder, PokemonIdentityEvidence  # noqa: E402
from app.repositories.supabase.pokemon_identity import (  # noqa: E402
    SupabasePokemonIdentityRepository,
)
from tools.validate_season_lifecycle_fixtures import (  # noqa: E402
    SeasonLifecycleFixtures,
    require,
)
from tools.validate_supabase_v2_identity_sql import LocalClient, SqlError  # noqa: E402

PARSER = "pokeapp-reader/2;pkhex/24.11.11"
DATABASE = "pokeapp_v2_validation_accounts"
INHERITED = (
    "validate_phase10_5_ranking_sql",
    "validate_phase10_5_championship_sql",
    "validate_phase10_5_final_sql",
)


class League:
    def __init__(self, args):
        self.client = LocalClient(args)
        self.auth = {r: str(uuid4()) for r in ("admin", "other", "owner")}
        readers = {
            r: LocalClient(args, "authenticated", uid) for r, uid in self.auth.items()
        }
        readers["anon"] = LocalClient(args, "anon")
        self.f = SeasonLifecycleFixtures(
            self.client, readers, self.auth, "phase29_" + uuid4().hex
        )

    # -- setup helpers -------------------------------------------------------
    def park(self):
        # Test isolation only: one active season at a time in the fixture DB.
        for old in self.f.seasons:
            if self.f.rows("seasons", id=old)[0]["status"] == "active":
                self.client.table("seasons").update({"status": "draft"}).eq(
                    "id", old
                ).execute()

    def modern(self, n):
        self.park()
        r = self.f.request("create", body={"name": "Liga " + uuid4().hex[:8]})
        sid = (
            self.client.rpc("api_admin_create_season", {"p_request": r})
            .execute()
            .data["season_id"]
        )
        self.f.seasons.append(sid)
        for trainer in self.f.trainers[1 : n + 1]:
            self.f.add(sid, trainer["id"])
        return sid

    def config(self, sid, sizes, *, total=2, movement=0, steal=False, **changes):
        cfg = self.f.config(sid)
        n = len(self.f.state(sid)["participants"])
        cfg.update(
            total_matchdays=total,
            division_sizes=sizes,
            movement_count=movement,
            scoring={str(i): n - i + 1 for i in range(1, n + 1)},
            coin_rewards={str(i): 5 * (n - i + 1) for i in range(1, n + 1)},
            rules={"team_lock_required": True, "last_b_gets_steal": steal},
            **changes,
        )
        return cfg

    def observed(self, sid, player, deaths):
        save_hash = uuid4().hex + uuid4().hex
        mons = [
            {
                "species": "Gastly",
                "identity_evidence": asdict(
                    PokemonIdentityEvidence(
                        1, 5, i + 1, 12345, 6789, 20, 2, "Fixture", 0,
                        ivs=(17, 0, 0, 0, 0, 0),
                    )
                ),
                "legacy_fingerprints": ["p29_" + str(i)],
            }
            for i in range(deaths)
        ]
        payload = dict(
            party=[dict(slot_number=i, pokemon=None) for i in range(1, 7)],
            boxes=[
                dict(
                    box_number=b,
                    slots=[
                        dict(
                            slot_number=i,
                            pokemon=mons[i - 1] if b == 8 and i <= len(mons) else None,
                        )
                        for i in range(1, 31)
                    ],
                )
                for b in range(1, 25)
            ],
            observed_progress=dict(
                schema_version=1,
                game="B2",
                generation=5,
                source_hash=save_hash,
                progress=dict(
                    schema_version=1,
                    primary_region="unova",
                    regions=[
                        dict(region="unova", badge_flags=[True, True] + [False] * 6)
                    ],
                ),
            ),
        )
        saved = self.f.insert(
            "save_files",
            dict(
                season_id=sid,
                trainer_id=player["trainer_id"],
                storage_key=self.f.run_id + "/" + save_hash,
                original_filename="synthetic-no-bytes.sav",
                sha256=save_hash,
                parser_status="parsed",
                parser_version=PARSER,
            ),
        )
        parsed = self.f.insert(
            "parsed_saves",
            dict(
                save_file_id=saved["id"],
                parser_version=PARSER,
                schema_version=1,
                payload=payload,
            ),
        )
        reconcile_parsed_save(
            SupabasePokemonIdentityRepository(self.client),
            season_id=sid,
            trainer_id=player["trainer_id"],
            parsed_save_id=parsed["id"],
            capture_order=CaptureOrder(str(uuid4()), 1),
        )
        self.client.table("season_players").update(
            {"current_save_file_id": saved["id"]}
        ).eq("id", player["id"]).execute()

    def context(self, sid):
        return (
            self.client.rpc(
                "initial_assignment_context",
                {
                    "p_request": {
                        "operation": "read",
                        "request": dict(actor_trainer_id=self.f.admin["id"], season_id=sid),
                    }
                },
            )
            .execute()
            .data
        )

    def envelope(self, sid, key=None):
        ctx = self.context(sid)
        body = {
            "config_version_id": ctx["config_version_id"],
            "input_hash": ctx["input_hash"],
            "expected_setup_revision": ctx["setup_revision"],
            "expected_roster_revision": ctx["roster_revision"],
        }
        return dict(
            request=self.f.request("initial_assignment", sid, body, key=key),
            plan=plan_initial_assignment(ctx, body),
            input_hash=ctx["input_hash"],
        )

    def commit(self, envelope):
        return (
            self.client.rpc(
                "api_admin_finalize_initial_assignment", {"p_request": envelope}
            )
            .execute()
            .data
        )

    def started(self, n, sizes, **kw):
        """A modern season ready to play: config, gameplay leg, observed saves."""
        sid = self.modern(n)
        self.f.call("create_config", sid, self.config(sid, sizes, **kw))
        self.f.call(
            "activate", sid, {"expected_setup_revision": self.f.state(sid)["setup_revision"]}
        )
        players = sorted(self.f.rows("season_players", season_id=sid), key=lambda p: p["id"])
        for i, p in enumerate(players):
            self.observed(sid, p, i)
        return sid, players

    def rejected(self, action, *codes):
        try:
            action()
        except SqlError as exc:
            require(exc.message in codes, f"Unexpected rejection {exc.message} expected {codes}")
        except Exception as exc:  # repository rejections carry an upper-case .code
            code = str(getattr(exc, "code", "")).lower()
            require(code in codes, f"Unexpected rejection {exc!r} expected {codes}")
        else:
            raise AssertionError(f"Expected rejection {codes}")

    # -- play ----------------------------------------------------------------
    def play(self, sid, players, sizes, total, movement, steal=False):
        f = self.f
        single = "B" not in sizes
        n = len(players)
        divisions = f.rows("divisions", season_id=sid)
        require(
            sorted(d["code"] for d in divisions) == (["A"] if single else ["A", "B"]),
            "Wrong league divisions " + str(divisions),
        )
        if single:
            require(divisions[0]["name"] == "Liga", "One league is not named Liga")
        else:
            require(
                sorted(d["name"] for d in divisions) == ["Division A", "Division B"],
                "Two-league names changed",
            )
        by_division = {}
        for m in f.rows("division_memberships", season_id=sid):
            by_division.setdefault(m["division_id"], set()).add(m["season_player_id"])
        require(
            sorted(len(v) for v in by_division.values())
            == sorted(sizes.values()),
            "Initial membership sizes differ from the config",
        )
        pairs = sum(k * (k - 1) // 2 for k in sizes.values())
        did = f.state(sid)["current_matchday_id"]
        movements = 0
        for number in range(1, total + 1):
            matches = f.rows("matches", matchday_id=did)
            require(len(matches) == pairs, f"Day {number}: {len(matches)} matches, expected {pairs}")
            member = {
                m["season_player_id"]: m["division_id"]
                for m in f.rows("division_memberships", season_id=sid)
                if m["effective_from_matchday_number"] <= number
                and (m["effective_to_matchday_number"] or number) >= number
            }
            require(
                all(member[m["player_a_id"]] == member[m["player_b_id"]] == m["division_id"] for m in matches),
                "Pairing crosses leagues",
            )
            f.open(sid, did)
            f.results(sid, did)
            f.close(sid, did)
            snapshot = f.rows("matchday_snapshots", matchday_id=did)[0]["snapshot"]
            standings = sorted(snapshot["standings"], key=lambda s: s["position"])
            require([s["position"] for s in standings] == list(range(1, n + 1)), "Positions not 1..n")
            for s in standings:
                require(
                    s["points_awarded"] == n - s["position"] + 1
                    and s["coins_awarded"] == 5 * (n - s["position"] + 1),
                    "Reward does not follow position",
                )
            last_b = [s for s in standings if s["division_id"] == "B"]
            if single:
                require(
                    [s["division_position"] for s in standings] == list(range(1, n + 1)),
                    "One league split its standings",
                )
                require(not last_b and snapshot["last_b_player_id"] is None, "One league has a last of B")
            else:
                require(
                    snapshot["last_b_player_id"] == (last_b[-1]["trainer_id"] if steal else None),
                    "Last-of-B reward",
                )
            moved = [
                m for m in f.rows("matchday_movements", matchday_id=did)
                if m["movement_type"] != "stay"
            ]
            movements += len(moved)
            if single or number == total:
                require(not moved, "Movement without two leagues or on the final day")
            else:
                require(len(moved) == 2 * movement, "Promotion/relegation count")
            if number < total:
                did = f.state(sid)["current_matchday_id"]
        return movements

    def finish(self, sid, players):
        f = self.f
        title = f.championship(sid)
        require(title["state"] == "ready", "Championship not ready: " + str(title))
        # player_a (lowest id) wins every match: most points overall.
        leader = min(players, key=lambda p: p["id"])
        require(title["champion_trainer_id"] == leader["trainer_id"], "Wrong single champion")
        f.life("finish", sid)
        require(f.rows("seasons", id=sid)[0]["status"] == "finished", "Not finished")
        f.life("archive", sid, {"expected_revision": f.state(sid)["setup_revision"], "label": "Fase 29"})
        hall = f.rows("hall_of_fame_entries", season_id=sid)
        require(len(hall) == 1 and hall[0]["champion_trainer_id"] == leader["trainer_id"], "Hall champion")
        read = self.client.rpc("league_general_read", {"p_season_id": sid}).execute().data
        require(read is not None, "Historical league read")
        return title

    # -- gates ---------------------------------------------------------------
    def run(self):
        f, checks = self.f, []
        f.setup()
        # 1. Structure validation on a modern draft.
        sid = self.modern(4)
        for bad in (
            self.config(sid, {"A": 4}, movement=1),
            self.config(sid, {"A": 4}, steal=True),
            self.config(sid, {"A": 3}),
            self.config(sid, {"A": 4, "B": 0}),
            self.config(sid, {}),
        ):
            self.rejected(lambda bad=bad: f.call("create_config", sid, bad), "invalid_config")
        legacy = f.draft()
        for t in f.trainers[2:6]:
            f.add(legacy, t["id"])
        self.rejected(
            lambda: f.call("create_config", legacy, self.config(legacy, {"A": 4})),
            "invalid_config",
        )
        self.rejected(
            lambda: f.call("create_config", sid, self.config(sid, {"A": 4}), actor=f.trainers[3]["id"]),
            "admin_required",
        )
        checks.append("S1 one league: no movement, no last-of-B reward, exact size, modern seasons only, admin only")

        # 2. One structure per season; free in draft, locked once started.
        cid = f.call("create_config", sid, self.config(sid, {"A": 4}))["resource_id"]
        row = f.rows("season_config_versions", id=cid)[0]
        require(row["division_count"] == 1 and row["division_sizes"] == {"A": 4}, "Stored structure")
        self.rejected(
            lambda: f.call("create_config", sid, self.config(sid, {"A": 2, "B": 2}, effective_from_matchday=2)),
            "competition_structure_mismatch",
        )
        replace = lambda sizes, **kw: f.call(  # noqa: E731
            "replace_config", sid,
            dict(self.config(sid, sizes, **kw), reason="Cambio de estructura en preparación"),
            resource=cid,
        )
        replace({"A": 2, "B": 2}, movement=1)
        require(f.rows("season_config_versions", id=cid)[0]["division_count"] == 2, "Draft change to two")
        replace({"A": 4})
        require(f.rows("season_config_versions", id=cid)[0]["division_count"] == 1, "Draft change back")
        f.call("activate", sid, {"expected_setup_revision": f.state(sid)["setup_revision"]})
        self.rejected(lambda: replace({"A": 2, "B": 2}), "competition_structure_locked")
        self.rejected(
            lambda: f.call("create_config", sid, self.config(sid, {"A": 2, "B": 2}, effective_from_matchday=2)),
            "competition_structure_locked",
        )
        replace({"A": 4}, total=3)
        require(f.rows("season_config_versions", id=cid)[0]["total_matchdays"] == 3, "Same-structure edit")
        checks.append("S2 structure stored in the config; free while draft, one per season, locked once started")

        # 3. Races: two finalizations, one assignment; replay is exact.
        players = sorted(f.rows("season_players", season_id=sid), key=lambda p: p["id"])
        for i, p in enumerate(players):
            self.observed(sid, p, i)
        envelopes = [self.envelope(sid), self.envelope(sid)]
        barrier = Barrier(2)

        def attempt(envelope):
            barrier.wait(timeout=30)
            try:
                return self.commit(envelope)
            except SqlError as exc:
                return exc.message

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, envelopes))
        wins = [i for i, r in enumerate(results) if isinstance(r, dict)]
        require(len(wins) == 1, "Two initial assignments: " + str(results))
        require(
            results[1 - wins[0]] in ("initial_assignment_locked", "stale_revision"),
            "Unexpected race loser " + str(results),
        )
        require(len(f.rows("divisions", season_id=sid)) == 1, "Race created a second league")
        replay = self.commit(envelopes[wins[0]])
        require(replay["replayed"] and replay["operation_id"] == results[wins[0]]["operation_id"], "Initial assignment replay")
        require(len(f.rows("divisions", season_id=sid)) == 1, "Replay duplicated the league")
        self.rejected(lambda: replace({"A": 4}, total=2), "config_already_used", "competition_structure_locked")
        checks.append("S3 concurrent initial assignment: one league, one winner, exact replay")

        # 4. Full one-league season, then counts 2, 3 and 5.
        self.play(sid, players, {"A": 4}, 3, 0)
        title = self.finish(sid, players)
        checks.append(
            f"A1 one league x4: calendar, pairings, standings, rewards, no movement, "
            f"champion {title['resolution_type']}, finish, archive, history"
        )
        for n in (2, 3, 5):
            sid, players = self.started(n, {"A": n}, total=2)
            self.commit(self.envelope(sid))
            self.play(sid, players, {"A": n}, 2, 0)
            self.finish(sid, players)
            checks.append(f"A{n} one league x{n} played to archive")

        # 5. Two leagues keep their exact behaviour, also through the new code.
        sid, players = self.started(6, {"A": 3, "B": 3}, total=3, movement=1, steal=True)
        self.commit(self.envelope(sid))
        moved = self.play(sid, players, {"A": 3, "B": 3}, 3, 1, steal=True)
        require(moved == 4, "Two-league movement over two non-final days")
        self.finish(sid, players)
        checks.append("B1 Liga A + Liga B x6: movement 1 per day, last-of-B rule, champion, archive")
        sid, players = self.started(4, {"A": 2, "B": 2}, total=2)
        self.commit(self.envelope(sid))
        self.play(sid, players, {"A": 2, "B": 2}, 2, 0)
        self.finish(sid, players)
        checks.append("B2 Liga A + Liga B x4 without movement played to archive")
        return checks

    def cleanup(self):
        for sid in self.f.seasons:
            self.client.table("initial_division_snapshots").delete().eq("season_id", sid).execute()
        self.f.cleanup()


def inherited(pg, args):
    from tools.validate_supabase_v2_schema import _psql_text
    import importlib
    import tools.validate_supabase_v2_identity_sql as identity

    base = identity.LocalClient.execute

    def execute(client, sql):
        if client.role == "service_role" and sql.startswith(
            ("select jsonb_agg(tablename", "select jsonb_object_agg(name,rows)")
        ):
            client.role = "postgres"
            try:
                return base(client, sql)
            finally:
                client.role = "service_role"
        return base(client, sql)

    identity.LocalClient.execute = execute

    done = []
    for name in INHERITED:
        database = "pokeapp_v2_validation_" + name.split("_", 3)[-1]
        pg.sql(f"drop database if exists {database}; create database {database};", "postgres")
        pg.storage(database)
        pg.sql((ROOT / "supabase/v2/bootstrap.sql").read_text(encoding="utf-8"), database)
        module = importlib.import_module("tools." + name)
        module.validate(
            SimpleNamespace(
                psql=str(args.bin / "psql.exe"), host="127.0.0.1", port=str(args.port),
                database=database, user="postgres", password="",
            ),
            _psql_text,
        )
        pg.sql(f"drop database {database};", "postgres")
        done.append(name)
    return done


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55529)
    parser.add_argument("--inherited", action="store_true")
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    pg = LocalPG(args.bin, args.port)
    league = None
    try:
        pg.start()
        league = League(
            SimpleNamespace(
                psql=str(args.bin / "psql.exe"), host="127.0.0.1", port=str(args.port),
                database=DATABASE, user="postgres", password="",
            )
        )
        try:
            checks = league.run()
        finally:
            league.cleanup()
        legacy = inherited(pg, args) if args.inherited else []
        version = pg.sql("show server_version;", "postgres").stdout.strip()
    finally:
        with contextlib.suppress(Exception):
            pg.stop()
    for check in checks:
        print("PASS", check)
    for name in legacy:
        print("PASS inherited", name)
    if args.evidence:
        args.evidence.write_text(
            json.dumps(
                {
                    "postgres": version,
                    "migrations": f"001-{MIGRATIONS:03d} bootstrap",
                    "checks": checks,
                    "inherited": legacy,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
