"""Focused 084 acceptance (Administración › Avisos); always rolls back.

Disposable loopback PostgreSQL only: no production transport, no save bytes.
On the real functions and triggers it checks that:

* accepted saves wait for their analysis in chain order, and a save registered
  before the system's activation is never queued;
* an analysis is recorded once: replays add neither a second analysis nor a
  second notice; the same change of the same save can never be noticed twice;
* the comparison context carries both saves and the server's own operations;
* only an administrator reads or manages notices, every status change is an
  idempotent append-only history row, and a notice can be reopened;
* the evidence of a notice is immutable and browser roles reach nothing.

    python -m tools.validate_phase084_save_audit --port <free port>
"""

from uuid import uuid4

from psycopg.types.json import Jsonb

from app.api.save_audit_models import SaveAuditOverview
from app.domain.save_audit import analyze
from tools.validate_phase079_all_vs_all import as_owner, connect, initialize, observe, value
from tools.validate_player_matchdays import rejected


def validate(pg):
    checks = []

    def ok(condition, label):
        assert condition, label
        checks.append(label)

    def owner_value(sql, args=()):
        conn.execute("reset role")
        try:
            return value(conn, sql, args)
        finally:
            conn.execute("set local role service_role")

    with connect(pg) as conn:
        try:
            v = initialize(conn)
            sid, trainer = v["sid"], v["trainers"][0]
            observe(conn, v, 0, [], 2)
            observe(conn, v, 0, [], 2)
            # A save registered before the system exists is only ever a reference.
            observe(conn, v, 1, [], 2)
            as_owner(
                conn,
                "update public.pokemon_identity_revisions set created_at=created_at-interval '1 day' where trainer_id=%s",
                (v["trainers"][1],),
            )

            def pending():
                return value(conn, "select public.save_audit_pending(%s,%s,%s)", (sid, trainer, 10))

            first_pending = pending()
            ok(
                [row["revision_number"] for row in first_pending] == [1, 2],
                "accepted saves wait for their analysis in chain order",
            )
            ok(
                value(conn, "select public.save_audit_pending(%s,%s,%s)", (sid, v["trainers"][1], 10)) == [],
                "a save older than the system's activation is never analysed",
            )
            first, second = (row["save_file_id"] for row in first_pending)

            context = value(conn, "select public.save_audit_context(%s,%s,%s)", (sid, trainer, second))
            ok(
                context["previous"]["save"]["id"] == first
                and context["current"]["save"]["id"] == second
                and context["current"]["payload"]["game"] == "Y"
                and context["previous"]["payload"]["game"] == "Y"
                and set(context["operations"]) == {"training", "deliveries", "transfers_in", "credited"},
                "the comparison context carries both saves and the server's own operations",
            )

            def record(save, notices, previous=None, status="analyzed"):
                return value(
                    conn,
                    "select public.save_audit_record(%s)",
                    (
                        Jsonb(
                            {
                                "season_id": sid,
                                "trainer_id": trainer,
                                "save_file_id": save,
                                "previous_save_file_id": previous,
                                "game": "Y",
                                "status": status,
                                "detector_version": 1,
                                "inventory_status": "compared" if status == "analyzed" else "baseline",
                                "bag": {"items": {"645": 2}, "pouches": {"645": "Items"}},
                                "friendship": {"1:2": 70},
                                "credited_deliveries": [],
                                "notices": notices,
                            }
                        ),
                    ),
                )

            notice = {
                "group_key": "pokemon:1:2",
                "category": "pokemon",
                "severity": "alta",
                "title": "Los seis IVs han pasado a 31",
                "summary": "Sospecha sin verificar.",
                "origin": "desconocido",
                "pokemon": None,
                "changes": [
                    {
                        "field": "iv_hp",
                        "label": "IV de PS",
                        "kind": "iv",
                        "before": 10,
                        "after": 31,
                        "severity": "alta",
                        "reason": "r",
                    }
                ],
                "operations": [],
                "compared": {
                    "previous": {"save_file_id": first, "sha256": "a" * 64, "uploaded_at": "2026-11-08T09:00:00+00:00", "revision": 1},
                    "current": {"save_file_id": second, "sha256": "b" * 64, "uploaded_at": "2026-11-08T10:00:00+00:00", "revision": 2},
                    "inventory_status": "compared",
                },
            }
            ok(record(first, [], status="baseline")["recorded"] is True, "the first save becomes the baseline")
            ok(
                [row["revision_number"] for row in pending()] == [2],
                "an analysed save is no longer pending",
            )
            ok(record(second, [notice], previous=first)["notices"] == 1, "a suspicious change becomes a notice")
            replay = record(second, [notice], previous=first)
            ok(
                replay == {"save_file_id": second, "recorded": False, "notices": 0}
                and owner_value("select count(*) from public.save_audit_notices where save_file_id=%s", (second,)) == 1,
                "replaying the same analysis adds nothing: no second notice",
            )
            ok(pending() == [], "nothing stays pending once analysed")

            def read(actor):
                return value(conn, "select public.admin_save_audit_read(%s,%s)", (actor, sid))

            overview = read(v["admin"])
            item = overview["notices"][0]
            ok(
                len(overview["notices"]) == 1
                and overview["pending_saves"] == 0
                and value(conn, "select public.admin_save_audit_summary(%s,%s)", (v["admin"], sid))
                == {"season_id": sid, "pending": 1, "pending_high": 1}
                and overview["analyzed_saves"] == 1
                and item["display_name"] == v["names"][0]
                and item["status"] == "pending"
                and item["severity"] == "alta"
                and item["changes"][0]["after"] == 31
                and len(overview["trainers"]) == 5,
                "the administrator reads the notice with its detail",
            )
            for stranger in (v["outsider"], v["trainers"][1]):
                rejected(conn, lambda who=stranger: read(who), "admin_required")
            ok(True, "a trainer without administrator rights is denied")

            # The real detector's output through the real SQL and the API contract.
            def payload(ivs):
                stats = dict(zip(("hp", "atk", "defense", "spa", "spd", "spe"), ivs))
                pokemon = {
                    "species": "Pokémon #25",
                    "nickname": "Nido",
                    "level": 30,
                    "item": "",
                    "moves": [{"name": "Move #33", "pp": 20}],
                    "is_shiny": False,
                    "gender": "M",
                    "form": 0,
                    "ability": "Ability #65",
                    "nature": "Nature #3",
                    "ivs": stats,
                    "evs": dict.fromkeys(stats, 0),
                    "identity_evidence": {
                        "schema_version": 2,
                        "format": 6,
                        "pid": 1000,
                        "encryption_constant": 2000,
                        "ot_name": "Antonio",
                        "ot_tid": 1,
                        "ot_sid": 2,
                        "source_trainer_match": True,
                    },
                }
                return {"game": "Y", "party": [{"slot_number": 1, "pokemon": pokemon}], "boxes": []}

            detected = analyze(
                {"payload": payload((1, 2, 3, 4, 5, 6)), "uploaded_at": "2026-11-08T10:00:00+00:00", "bag": None, "friendship": None},
                {"payload": payload((31,) * 6), "uploaded_at": "2026-11-08T11:00:00+00:00", "bag": None, "friendship": None},
                {},
            )
            observe(conn, v, 0, [], 2)
            third = pending()[-1]["save_file_id"]
            side = {"save_file_id": second, "sha256": "a" * 64, "uploaded_at": "2026-11-08T10:00:00+00:00", "revision": 2}
            for found in detected["notices"]:
                found["compared"] = {"previous": side, "current": side, "inventory_status": "no_baseline"}
            ok(record(third, detected["notices"], previous=second)["notices"] == 1, "the detector's notice is stored")
            contract = SaveAuditOverview.model_validate(read(v["admin"]))
            ok(
                len(contract.notices) == 2 and contract.notices[0].changes[0].after == 31
                and contract.notices[0].title == "Los seis IVs han pasado a 31",
                "the detector's notice crosses the SQL and matches the API contract",
            )

            def update(actor, status, note, operation=None, digest="a" * 64):
                return value(
                    conn,
                    "select public.admin_save_audit_update(%s,%s,%s,%s,%s,%s,%s)",
                    (actor, sid, item["id"], status, note, operation or str(uuid4()), digest),
                )

            rejected(conn, lambda: update(v["trainers"][1], "justified", "No soy admin"), "admin_required")
            rejected(conn, lambda: update(v["admin"], "justified", " "), "notice_note_required")
            operation = str(uuid4())
            done = update(v["admin"], "justified", "El entrenador confirma que lo consiguió jugando", operation)
            ok(
                done["status"] == "justified"
                and done["replayed"] is False
                and [(e["from_status"], e["to_status"]) for e in done["events"]] == [("pending", "justified")],
                "the administrator justifies a notice with an observation",
            )
            again = update(v["admin"], "justified", "El entrenador confirma que lo consiguió jugando", operation)
            ok(again["replayed"] is True and len(again["events"]) == 1, "the same operation is not applied twice")
            rejected(conn, lambda: update(v["admin"], "confirmed", "Otro", operation, "b" * 64), "idempotency_conflict")
            reopened = update(v["admin"], "pending", "Reabierto al revisar de nuevo")
            ok(
                reopened["status"] == "pending"
                and [e["to_status"] for e in reopened["events"]] == ["justified", "pending"]
                and len(read(v["admin"])["notices"]) == 2,
                "a notice can be reopened and its history is kept",
            )

            rejected(
                conn,
                lambda: as_owner(conn, "update public.save_audit_notices set title='x'"),
                "save_audit_immutable",
            )
            rejected(
                conn,
                lambda: as_owner(conn, "delete from public.save_audit_notices"),
                "save_audit_immutable",
            )
            rejected(
                conn,
                lambda: as_owner(conn, "update public.save_audit_notice_events set note='x'"),
                "save_audit_immutable",
            )
            rejected(
                conn,
                lambda: as_owner(conn, "delete from public.save_audit_runs"),
                "save_audit_immutable",
            )
            ok(True, "the evidence, history and analyses are immutable")

            for table in ("save_audit_config", "save_audit_runs", "save_audit_notices", "save_audit_notice_events"):
                forced = value(conn, "select relforcerowsecurity from pg_class where oid=%s::regclass", (f"public.{table}",))
                ok(
                    forced
                    and not any(
                        value(conn, "select has_table_privilege(%s,%s,'select')", (role, f"public.{table}"))
                        for role in ("anon", "authenticated", "service_role")
                    ),
                    f"{table}: forced RLS and no direct access",
                )
            for function in (
                "public.save_audit_pending(uuid,uuid,integer)",
                "public.save_audit_record(jsonb)",
                "public.admin_save_audit_read(uuid,uuid)",
                "public.admin_save_audit_summary(uuid,uuid)",
                "public.admin_save_audit_update(uuid,uuid,uuid,text,text,uuid,text)",
            ):
                ok(
                    not any(
                        value(conn, "select has_function_privilege(%s,%s,'execute')", (role, function))
                        for role in ("anon", "authenticated")
                    ),
                    f"{function}: browser roles cannot call it",
                )
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
    parser.add_argument("--port", type=int, default=55843)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    pg = SupabaseLikePG(args.pg_bin, args.port)
    try:
        pg.start()
        for migration in MIGRATIONS:
            pg.sql(migration.read_text(encoding="utf-8"))
        checks = validate(pg)
        report = {"result": "PASS", "checks": checks, "production_modified": False}
        if args.output:
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
    finally:
        pg.stop(remove=True)


if __name__ == "__main__":
    main()
