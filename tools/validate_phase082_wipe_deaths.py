"""Focused 082 acceptance (wipe-revived deaths in official NET); always rolls back.

Disposable loopback PostgreSQL only: no production transport, saves or Discord.

* ``reproduce_defect(pg)`` on 001-081: eleven reported wipe revivals with no
  dead-box observation make NET unknown; four deaths still in the dead box plus
  one wipe revival deduct only 0.5.
* ``validate(pg)`` on 001-082: the same facts give -2.2 and -0.6; an observed
  death later alive with no comodín is charged once with the wipe (-0.2); a
  comodín revival keeps its own 0.1; the values are identical with no
  matchday, a prepared J1, an open J1 (a new death counts at once) and after
  J1 closes; an audited baseline that already contains its wipe deaths is not
  charged twice; missing sources stay unknown; ACLs are unchanged.

    python -m tools.validate_phase082_wipe_deaths --port <free port>
"""

from decimal import Decimal
from uuid import uuid4

from tools.validate_phase079_all_vs_all import (
    as_owner,
    connect,
    initialize,
    observe,
    prepare,
    value,
    wipe,
)
from tools.validate_phase080_enrollment import close_day, open_day, results


def _setup(conn):
    """Iker-like 3 dead; clean 0; Samu-like 11 wipe revivals and nothing in the
    dead box; 4 still dead + 1 wipe; 1 dead then alive again + 1 wipe."""
    v = initialize(conn)
    observe(conn, v, 0, [1, 2, 3], 2)
    observe(conn, v, 1, [], 2)
    observe(conn, v, 2, [], 2)
    wipe(conn, v, 2, 11, "082-eleven")
    observe(conn, v, 3, [1, 2, 3, 4], 2)
    wipe(conn, v, 3, 1, "082-four")
    observe(conn, v, 4, [1], 2)
    observe(conn, v, 4, [], 2)
    wipe(conn, v, 4, 1, "082-overlap")
    return v


def _comodin(conn, v, index, entity):
    """The real redemption RPC with synthetic native receipts (as in 075)."""
    sid, tid, pid = v["sid"], v["trainers"][index], v["players"][index]
    purchase, auth, claim = (str(uuid4()) for _ in range(3))
    head, save = conn.execute(
        "select id,save_file_id from public.pokemon_identity_revisions where season_id=%s and trainer_id=%s"
        " order by revision_number desc limit 1", (sid, tid)).fetchone()
    digest = value(conn, "select sha256 from public.save_files where id=%s", (save,))
    as_owner(conn, "insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,"
             "status,acquisition_type) select %s,%s,%s,%s,id,1,6,'pending','paid' from public.shop_items where code='revivir_pokemon'",
             (purchase, sid, tid, pid))
    as_owner(conn, "insert into public.item_use_authorizations(id,operation_id,idempotency_key,purchase_id,season_id,trainer_id,"
             "target_pokemon_entity_id,save_file_id,save_sha256,identity_revision_id,claim_id,effect_code,status,observed_sha256)"
             " values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'revive','APPLIED_VERIFIED',repeat('f',64))",
             (auth, purchase, purchase, purchase, sid, tid, entity, save, digest, head, claim))
    as_owner(conn, "insert into public.item_use_verifications(authorization_id,claim_id,operation_id,source_sha256,result_sha256,"
             "target_pokemon_entity_id,identity_revision_id,native_operation_id,plan_sha256)"
             " values(%s,%s,%s,%s,repeat('f',64),%s,%s,gen_random_uuid(),repeat('a',64))",
             (auth, claim, purchase, digest, entity, head))
    as_owner(conn, "select public.api_redeem_purchase(%s,%s,%s,%s,%s,%s)", (sid, tid, purchase, entity, purchase, head))


def _reads(conn, v):
    def totals(index):
        return value(conn, "select public.league_death_totals(%s)", (v["players"][index],))

    def row(index):
        rows = value(conn, "select public.league_general_read(%s)", (v["sid"],))["rows"]
        return next(r for r in rows if r["season_player_id"] == v["players"][index])

    def points(index):
        found = row(index)["total_points"]
        return None if found is None else Decimal(found)

    return totals, row, points


def reproduce_defect(pg):
    checks = []
    with connect(pg) as conn:
        try:
            v = _setup(conn)
            totals, _, points = _reads(conn, v)
            assert totals(2)["blocking_reason"] == "death_history_inconsistent" and points(2) is None
            checks.append("081: 11 wipe revivals with an empty dead box make NET unknown")
            assert points(3) == Decimal("-0.5")
            checks.append("081: 4 deaths still in the dead box + 1 wipe revival deduct only 0.5")
        finally:
            conn.rollback()
    return checks


def validate(pg):
    checks = []

    def ok(condition, label):
        assert condition, label
        checks.append(label)

    with connect(pg) as conn:
        try:
            v = _setup(conn)
            totals, row, points = _reads(conn, v)
            samu = totals(2)
            ok(samu["known"] and samu["actual_deaths"] == 11 and samu["wipe_deaths"] == 11
               and samu["death_penalty_tenths"] == 22 and points(2) == Decimal("-2.2"),
               "11 wipe revivals with no dead-box event: 11 deaths at 0.2 each, NET -2.2")
            ok(points(0) == Decimal("-0.3") and totals(0)["actual_deaths"] == 3,
               "3 ordinary deaths still in the dead box: NET -0.3")
            ok(points(1) == 0 and totals(1)["known"], "no deaths and no wins: known NET 0, never unknown")
            ok(points(3) == Decimal("-0.6") and totals(3)["actual_deaths"] == 5,
               "4 ordinary deaths + 1 separate wipe revival: NET -0.6")
            ok(points(4) == Decimal("-0.2") and totals(4)["actual_deaths"] == 1,
               "a dead-box death later alive with no comodín is the wipe's own death: charged once (-0.2)")
            before = {i: points(i) for i in range(5)}

            day = prepare(conn, v, v["trainers"][0])["matchday_id"]
            ok({i: points(i) for i in range(5)} == before, "a prepared J1 changes no accumulated NET")
            open_day(conn, v, day)
            ok({i: points(i) for i in range(5)} == before, "an open J1 changes no accumulated NET")
            observe(conn, v, 0, [1, 2, 3, 4], 2)
            ok(points(0) == Decimal("-0.4"), "a new death during an open matchday counts at once")
            before[0] = Decimal("-0.4")
            results(conn, v, day)
            close_day(conn, v, day)
            closed = {i: points(i) for i in range(5)}
            ok(all(closed[i] == Decimal(row(i)["normal_wins"]) + before[i] for i in range(5)),
               "after J1 closes, NET = wins - the same accumulated death penalties")

            as_owner(conn, "update public.league_death_history set actual_offset=11,confirmed_wipe_deaths=11,"
                     "confirmed_at=now() where season_player_id=%s", (v["players"][2],))
            ok(totals(2)["death_penalty_tenths"] == 22,
               "an audited baseline that already contains its wipe deaths is not charged twice")
            as_owner(conn, "update public.season_players set current_save_file_id=null where id=%s", (v["players"][1],))
            ok(not totals(1)["known"] and points(1) is None, "a missing official source stays unknown, never zero")
            ok(not value(conn, "select has_function_privilege('authenticated','public.league_death_totals(uuid)','execute')"),
               "league_death_totals keeps its service-only ACL")
        finally:
            conn.rollback()

    # A comodín revival explains its own revival: that death keeps its 0.1 and
    # a later wipe revival is a different death with its own 0.2.
    with connect(pg) as conn:
        try:
            v = initialize(conn)
            totals, _, points = _reads(conn, v)
            for index in range(1, 5):
                observe(conn, v, index, [], 2)
            observe(conn, v, 0, [1], 2)
            entity = value(conn, "select pokemon_entity_id from public.league_death_events where season_player_id=%s",
                           (v["players"][0],))
            _comodin(conn, v, 0, entity)
            observe(conn, v, 0, [], 2)
            wipe(conn, v, 0, 1, "082-comodin")
            ok(points(0) == Decimal("-0.3") and totals(0)["actual_deaths"] == 2,
               "a comodín-revived death keeps its 0.1 and a later wipe revival adds its own 0.2")
        finally:
            conn.rollback()
    return checks


def main():
    import argparse
    import json
    import os
    from pathlib import Path

    from tools.phase30_release_audit import MIGRATIONS, SupabaseLikePG

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, default=Path(os.environ["LOCALAPPDATA"]) / "Temp/phase10-5l-pg17/pgsql/bin")
    parser.add_argument("--port", type=int, default=55642)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        for migration in MIGRATIONS:
            if int(migration.name[:3]) <= 81:
                pg.sql(migration.read_text(encoding="utf-8"))
        defect = reproduce_defect(pg)
        for migration in MIGRATIONS:
            if int(migration.name[:3]) > 81:
                pg.sql(migration.read_text(encoding="utf-8"))
        checks = validate(pg)
        report = {"result": "PASS", "defect_reproduced_on_081": defect, "checks": checks,
                  "production_modified": False}
        if args.output:
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        pg.stop(remove=True)


if __name__ == "__main__":
    main()
