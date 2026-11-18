"""088 Revivir ya no blinda (owner rule of 2026-11-18), on the real RPCs.

Disposable loopback PostgreSQL only: no production transport or saves.

* ``reproduce(conn)`` on 001-087 (committed): a Pokémon revived with the
  comodín is left BLINDADO; one that was shielded with Blindar, died and was
  revived is BLINDADO too.
* ``validate(pg)`` after 088: the revive-only shield is gone, the Blindar one
  stays, both stay REVIVIDO; a new revive leaves the Pokémon REVIVIDO only;
  once alive again the revived Pokémon is not refused as shielded by the
  robbery rotation; Blindar still shields; ACLs unchanged.
* ``rehearsal_rows(pg)`` / ``verify_rehearsal(pg, before)`` (backup
  rehearsal on a production restore): 088 changes no flag row except
  revive-only BLINDADO rows, which go from true to false and nothing else.

    python -m tools.validate_phase088_revive_shield --pg-bin <bin> --port <free port>
"""

from uuid import uuid4

from tools.validate_phase079_all_vs_all import (
    as_owner,
    connect,
    initialize,
    observe,
    seed,
    value,
)
from tools.validate_phase082_wipe_deaths import _comodin as revive

SIGNATURE = "public.api_redeem_purchase(uuid,uuid,uuid,uuid,text,uuid)"


def _entities(conn, v, index):
    return [str(row[0]) for row in conn.execute(
        "select id from public.pokemon_entities where season_id=%s and owner_trainer_id=%s order by candidate_key",
        (v["sid"], v["trainers"][index])).fetchall()]


def _shield(conn, v, index, entity):
    """Blindar through the real redemption RPC (no physical step)."""
    sid, tid, pid = v["sid"], v["trainers"][index], v["players"][index]
    purchase = str(uuid4())
    head = value(conn, "select id from public.pokemon_identity_revisions where season_id=%s and trainer_id=%s"
                       " order by revision_number desc limit 1", (sid, tid))
    as_owner(conn, "insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,"
             "status,acquisition_type) select %s,%s,%s,%s,id,1,6,'pending','paid' from public.shop_items where code='blindar_pokemon'",
             (purchase, sid, tid, pid))
    as_owner(conn, "select public.api_redeem_purchase(%s,%s,%s,%s,%s,%s)", (sid, tid, purchase, entity, purchase, head))


def flags(conn, v, entity):
    rows = conn.execute("select flag_type,flag_value,flag_timestamp is not null from public.pokemon_entity_flags"
                        " where season_id=%s and pokemon_entity_id=%s", (v["sid"], entity)).fetchall()
    return {kind: (stamp if kind.endswith("_at") else bool(flag)) for kind, flag, stamp in rows}


def reproduce(conn):
    """On 001-087, committed: the two revived Pokémon both end up BLINDADO."""
    v = initialize(conn)
    observe(conn, v, 0, [1], 2)
    e = _entities(conn, v, 0)
    _shield(conn, v, 0, e[3])            # Blindar while alive...
    observe(conn, v, 0, [1, 4], 2)       # ...then it dies
    revive(conn, v, 0, e[0])             # revive-only
    revive(conn, v, 0, e[3])             # shielded with Blindar, then revived
    observe(conn, v, 1, [1], 2)
    other = _entities(conn, v, 1)
    _shield(conn, v, 1, other[2])        # another trainer's Blindar
    before = {name: flags(conn, v, entity) for name, entity in
              (("revive_only", e[0]), ("blindar_then_revive", e[3]), ("other_blindar", other[2]))}
    assert before["revive_only"].get("blindado") is True and before["revive_only"].get("revivido_at"), before
    assert before["blindar_then_revive"].get("blindado") is True, before
    acl = value(conn, "select proacl::text from pg_proc where oid=%s::regprocedure", (SIGNATURE,))
    conn.commit()
    return v, {"revive_only": e[0], "blindar_then_revive": e[3], "other_blindar": other[2]}, before, acl


def validate(pg, v, entities, acl):
    checks = []
    with connect(pg) as conn:
        try:
            definition = value(conn, "select pg_get_functiondef(%s::regprocedure)", (SIGNATURE,))
            assert "if v_effect<>'revive' then" in definition, "guard missing"
            assert value(conn, "select proacl::text from pg_proc where oid=%s::regprocedure", (SIGNATURE,)) == acl
            checks.append("api_redeem_purchase shields on Blindar/Robar only; ACL unchanged")

            after = {name: flags(conn, v, entity) for name, entity in entities.items()}
            assert after["revive_only"].get("blindado") is False, after
            assert after["revive_only"].get("revivido_at") is True, after
            assert after["blindar_then_revive"].get("blindado") is True, after
            assert after["blindar_then_revive"].get("revivido_at") is True, after
            assert after["other_blindar"].get("blindado") is True, after
            checks.append("revive-only shield removed; Blindar shields (revived or not) kept; REVIVIDO kept")

            # pg_temp.observe lives in the session that seeded: define it again.
            fixture = seed()[0]
            conn.execute(fixture[fixture.index("create or replace function pg_temp.observe"):])
            conn.execute("set local role service_role")
            observe(conn, v, 0, [1, 2, 4], 2)
            e = _entities(conn, v, 0)
            revive(conn, v, 0, e[1])
            new = flags(conn, v, e[1])
            assert new.get("revivido_at") is True and not new.get("blindado"), new
            checks.append("a revive after 088 leaves the Pokémon REVIVIDO only")

            observe(conn, v, 0, [4], 2)  # both revived Pokémon alive again in Box 1
            blocked = dict(conn.execute(
                "select pokemon_entity_id::text,blocked from public.robbery_candidates(%s,%s)",
                (v["sid"], v["trainers"][0])).fetchall())
            for entity in (e[0], e[1]):
                assert entity in blocked and blocked[entity] != "shielded", blocked
            checks.append("the robbery rotation no longer refuses a revived Pokémon as shielded")

            _shield(conn, v, 0, e[0])
            assert flags(conn, v, e[0]).get("blindado") is True
            checks.append("a revived Pokémon can still be protected with Blindar")
        finally:
            conn.rollback()
    return checks


REVIVE_ONLY = """exists(select 1 from public.redemptions r where r.season_id=f.season_id
      and r.target_pokemon_entity_id=f.pokemon_entity_id and r.effect_code='revive' and r.status='applied')
    and not exists(select 1 from public.redemptions r where r.season_id=f.season_id
      and r.target_pokemon_entity_id=f.pokemon_entity_id
      and r.effect_code in ('shield','robbery_shield','steal') and r.status='applied')"""


def rehearsal_rows(pg):
    """Every flag row before 088: id, the row without flag_value, flag_value."""
    return pg.lines("select f.id::text||'|'||md5((to_jsonb(f)-'flag_value')::text)||'|'||coalesce(f.flag_value::text,'-')"
                    " from public.pokemon_entity_flags f order by f.id", "supabase_admin")


def verify_rehearsal(pg, before):
    after = rehearsal_rows(pg)
    expected = set(pg.lines(f"select f.id::text from public.pokemon_entity_flags f where f.flag_type='blindado'"
                            f" and {REVIVE_ONLY}", "supabase_admin"))
    old = {line.split("|")[0]: line.split("|")[1:] for line in before}
    new = {line.split("|")[0]: line.split("|")[1:] for line in after}
    problems = []
    if set(old) != set(new):
        problems.append("flag rows added or removed")
    changed = sorted(i for i in set(old) & set(new) if old[i] != new[i])
    for flag_id in changed:
        if flag_id not in expected or old[flag_id] != [old[flag_id][0], "true"] or new[flag_id] != [old[flag_id][0], "false"]:
            problems.append(f"unexpected change {flag_id}")
    still = pg.lines(f"select count(*) from public.pokemon_entity_flags f where f.flag_type='blindado'"
                     f" and f.flag_value is true and {REVIVE_ONLY}", "supabase_admin")
    if still != ["0"]:
        problems.append(f"revive-only shields left: {still}")
    return {"unshielded_revived": len(changed), "problems": problems}


def main():
    import argparse
    import json
    import os
    from pathlib import Path

    from tools.phase30_release_audit import MIGRATIONS, SupabaseLikePG

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pg-bin", type=Path, default=Path(os.environ["LOCALAPPDATA"]) / "PokeAppDev/pg17/pgsql/bin")
    parser.add_argument("--port", type=int, default=55688)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        for migration in MIGRATIONS:
            if int(migration.name[:3]) <= 87:
                pg.sql(migration.read_text(encoding="utf-8"))
        with connect(pg) as conn:
            v, entities, before, acl = reproduce(conn)
        run = pg.sql((MIGRATIONS[-1]).read_text(encoding="utf-8"), "postgres", ok=False)
        assert MIGRATIONS[-1].name.startswith("088_") and not run.returncode, run.err[-600:]
        checks = validate(pg, v, entities, acl)
        report = {"result": "PASS", "defect_reproduced_on_087": before, "checks": checks,
                  "production_modified": False}
        if args.output:
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        pg.stop(remove=True)


if __name__ == "__main__":
    main()
