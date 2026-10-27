"""Phase 30 gate: a Cup inside a one-league season, on disposable PostgreSQL.

Phase 29 proved one-league seasons and left the Cup engine (031/032, no
division dependency) untouched, but never played both together. Here one
league of four trainers runs a Swiss Cup and a doubles Cup while the league is
in progress, certifies both, and is then played to archive. A twin one-league
season without Cups is played the same way as the control: standings, points,
coins and champion must be identical, the Cup Hall entries separate from the
league's, and the archived history must read both. Synthetic data only.

Run: python -m tools.validate_phase30_cup_single_league --bin <pg bin> [--evidence <json>]
"""

from __future__ import annotations

import argparse
import contextlib
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from tools.validate_cup_fixtures import CupFixtures
from tools.validate_phase29_league import DATABASE, MIGRATIONS, League, LocalPG
from tools.validate_season_lifecycle_fixtures import require
from tools.validate_supabase_v2_identity_sql import LocalClient


def certified(cup):
    return (
        cup["status"] == "finished"
        and bool(cup["certificate_id"])
        and bool(cup["champion_side_id"])
    )


class CupLeague(League):
    def __init__(self, args):
        self.client = LocalClient(args)
        self.auth = {r: str(uuid4()) for r in ("admin", "other", "owner")}
        readers = {
            r: LocalClient(args, "authenticated", uid) for r, uid in self.auth.items()
        }
        readers["anon"] = LocalClient(args, "anon")
        self.f = CupFixtures(self.client, readers, self.auth, "phase30_" + uuid4().hex)

    def finish(self, sid, players):
        """League.finish, but the Hall also holds this season's Cup entries."""
        f = self.f
        title = f.championship(sid)
        require(title["state"] == "ready", "Championship not ready: " + str(title))
        leader = min(players, key=lambda p: p["id"])
        require(
            title["champion_trainer_id"] == leader["trainer_id"],
            "Wrong single champion",
        )
        f.life("finish", sid)
        f.life(
            "archive",
            sid,
            {"expected_revision": f.state(sid)["setup_revision"], "label": "Fase 30"},
        )
        league = [
            h
            for h in f.rows("hall_of_fame_entries", season_id=sid)
            if h["competition_type"] == "league"
        ]
        require(
            len(league) == 1
            and league[0]["champion_trainer_id"] == leader["trainer_id"],
            "League Hall champion",
        )
        return title

    def league_outcome(self, sid):
        """What the league awarded, per matchday, without ids that differ per season."""
        days = sorted(
            self.f.rows("matchdays", season_id=sid), key=lambda d: d["number"]
        )
        outcome = []
        for day in days:
            snapshot = self.f.rows("matchday_snapshots", matchday_id=day["id"])[0][
                "snapshot"
            ]
            outcome.append(
                [
                    (
                        s["position"],
                        s["division_position"],
                        s["points_awarded"],
                        s["coins_awarded"],
                    )
                    for s in sorted(snapshot["standings"], key=lambda s: s["position"])
                ]
            )
        coins = sorted(
            r["amount"] for r in self.f.rows("coin_transactions", season_id=sid)
        )
        return outcome, coins

    def run(self):
        f, checks = self.f, []
        f.setup()
        n, sizes = 4, {"A": 4}

        # Control: the same one-league season without any Cup.
        control, players = self.started(n, sizes, total=2)
        self.commit(self.envelope(control))
        self.play(control, players, sizes, 2, 0)
        control_title = self.finish(control, players)
        control_outcome = self.league_outcome(control)

        sid, players = self.started(n, sizes, total=2)
        self.commit(self.envelope(sid))
        require(
            [d["code"] for d in f.rows("divisions", season_id=sid)] == ["A"],
            "Not one league",
        )
        roster = sorted(p["trainer_id"] for p in players)
        participation = sorted(
            f.rows("season_players", season_id=sid), key=lambda p: p["id"]
        )
        swiss = f.create_cup(sid, "swiss", n=4, rounds=2)
        doubles = f.create_cup(sid, "doubles", n=2)
        for cid in (swiss, doubles):
            c = f.document(sid, cid)
            members = sorted(m["trainer_id"] for s in c["sides"] for m in s["members"])
            require(members == roster, "Cup entrants are not the one-league roster")
        f.finish_cup(sid, swiss)
        f.finish_cup(sid, doubles)
        for cid in (swiss, doubles):
            require(certified(f.document(sid, cid)), "Cup not certified")
        require(
            sorted(f.rows("season_players", season_id=sid), key=lambda p: p["id"])
            == participation,
            "Cups changed league participation",
        )
        phases = [r["phase"] for r in f.document(sid, swiss)["rounds"]]
        require(
            phases == ["swiss", "swiss", "semifinal", "final"],
            "Swiss phases " + str(phases),
        )
        checks.append(
            "C1 one league x4: Swiss Cup (2 rounds + Top 4) and doubles Cup certified during the league, participation untouched"
        )

        self.play(sid, players, sizes, 2, 0)
        title = self.finish(sid, players)
        outcome = self.league_outcome(sid)
        require(outcome == control_outcome, "Cups changed league standings or rewards")
        require(
            title["resolution_type"] == control_title["resolution_type"],
            "Championship differs from the Cup-free control",
        )
        checks.append(
            "C2 league played to archive with Cups: standings, points, coins and champion identical to a Cup-free twin"
        )

        hall = f.rows("hall_of_fame_entries", season_id=sid)
        kinds = sorted(h["competition_type"] for h in hall)
        require(kinds == ["cup", "doubles_cup", "league"], "Hall entries " + str(kinds))
        require(
            {h["cup_id"] for h in hall if h["competition_type"] != "league"}
            == {swiss, doubles},
            "Cup Hall entries do not match the certified Cups",
        )
        league_hall = next(h for h in hall if h["competition_type"] == "league")
        require(league_hall["cup_id"] is None, "League Hall entry points at a Cup")
        archived = f.rows("season_archive_snapshots", season_id=sid)[0]["snapshot"]
        require(
            archived["cup_hall_status"] == "independent_cup_certification",
            "Archive Cup marker",
        )
        read = (
            self.client.rpc("league_general_read", {"p_season_id": sid}).execute().data
        )
        require(read is not None, "Archived league read")
        for cid in (swiss, doubles):
            require(certified(f.document(sid, cid)), "Archived Cup unreadable")
        checks.append(
            "C3 Hall: one league champion and two separate Cup entries; archive and history read both"
        )

        late = f.create_cup(sid, "elimination", 2)
        baseline = f.league_history(sid)
        f.finish_cup(sid, late)
        require(
            f.league_history(sid) == baseline, "Post-archive Cup rewrote league history"
        )
        checks.append(
            "C4 Cup after archive in a one-league season leaves league history byte-identical"
        )
        return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bin", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55531)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    pg = LocalPG(args.bin, args.port)
    try:
        pg.start()
        league = CupLeague(
            SimpleNamespace(
                psql=str(args.bin / "psql.exe"),
                host="127.0.0.1",
                port=str(args.port),
                database=DATABASE,
                user="postgres",
                password="",
            )
        )
        try:
            checks = league.run()
        finally:
            league.cleanup()
        version = pg.sql("show server_version;", "postgres").stdout.strip()
    finally:
        with contextlib.suppress(Exception):
            pg.stop()
    for check in checks:
        print("PASS", check)
    if args.evidence:
        args.evidence.write_text(
            json.dumps(
                {
                    "postgres": version,
                    "migrations": f"001-{MIGRATIONS:03d} bootstrap",
                    "checks": checks,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
