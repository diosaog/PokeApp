"""Phase 30 release step: apply 054-064 to production, once each, in order.

THIS WRITES TO PRODUCTION. Run it only inside the release window the owner has
authorized explicitly, after a fresh verified backup (tools.phase30_backup_rehearsal
capture + rehearse on that same archive).

``--dry-run`` (the default) is read-only: it runs every pre-flight check and
prints the plan. ``--apply`` additionally requires ``--owner-authorized`` and
the rehearsed backup manifest, and then, for each file:

1. re-reads the migration history and refuses if this name is already there;
2. writes an intent file (name + SHA-256) to the private folder, refusing if an
   earlier intent exists without a result (an unknown outcome is reconciled by
   hand, never retried blindly);
3. applies the file through the Management API migrations endpoint, the same
   path 050-053 used (each file is its own transaction);
4. requires exactly one new history record, writes the result file, and stops
   at the first error.

Rollback is fix-forward. Restoring the backup is only for data loss.
Run: python -m tools.phase30_apply_migrations --dir <private dir> [--apply --owner-authorized --backup <manifest>]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tools.phase30_release_audit import DEPLOYED, PENDING
from tools.production_readonly import SUPABASE_REF, _supabase, query, supabase_get

EXPECTED_SHA256 = {
    '068_precompetition_readiness.sql': 'e582c4a973581003b194eb157370521b37f6a002189491f564b7710d7afcad69',
    '067_discord_announcements.sql': '63300555a3b927765a5984ceb7353d2229656b8a529f306e8704ca20a0a462e2',
    "054_item_use_authorizations.sql": "f6e4c775bee8f79f4f8c487b266eef318d611c3f5810eeb7c14249c7aa1f11c9",
    "055_native_identity_evidence_scope.sql": "f1fae278caa2832619713d74b6da03055ede5870ca7b902c85d34427b9e3fc83",
    "056_item_use_verifier_transport.sql": "7b5d9619562e09828dee3313fe514eb99a8ffb71eab3457a4d4b2514fe965e38",
    "057_two_save_transfer_reservations.sql": "ae1061aeae62ce8250877d2dd036e21fa22a4fb461d2892379536658eaa92066",
    "058_transfer_provenance_finalization.sql": "82ae34ee566e02d18c4a0d498a6e51a63dae438e48dbd31c834626a90f576037",
    "059_transfer_integration_reads.sql": "7ad33a22672e226ad03436c9c577512d705d472eb82f67e4b75bc09bffdcaa05",
    "060_transfer_party_origin.sql": "624a59d67e77720bfb862e8efda19f6cbabc530e2169485268206b06160441c4",
    "061_transfer_authoritative_adjudication.sql": "332ff8a2e54e102d744405fcf3b76ff2c5097596eb2dd484e4ebd9fe7bef4482",
    "062_admin_incident_center.sql": "7abd350f7d99247bc82912fce2c53bc636a1745571265332dbd767fce41497ad",
    "063_single_league_structure.sql": "621e43f2c44cc4b232f4a40c787ae84c4a36ad63ab2279778967cffc33576e1c",
    "064_admin_robbery_cancellation.sql": "80407837fce1d205b90757c19e4148419d3fab52e24de6d47952c43afad21b2e",
    "065_personal_saves.sql": "11b02406d1b8eabd688d51bb8c51886cc462c3c5115cdb9b1e685b7b0e417ec9",
    "066_personal_saves_least_privilege.sql": "23529af177f86c7541326e76ee2bbd1b48fbcff8f275f504f970a5ff0a0c81d0",
}
BACKUP_MAX_AGE = timedelta(hours=2)


def history() -> list[str]:
    return [
        r["name"]
        for r in query(
            "select name from supabase_migrations.schema_migrations order by version"
        )
    ]


def preflight(args) -> dict:
    """Read-only: what production looks like and whether the window may open."""
    problems = []
    files = {m.name: hashlib.sha256(m.read_bytes()).hexdigest() for m in PENDING}
    if any(EXPECTED_SHA256.get(name) != digest for name, digest in files.items()):
        problems.append("pending files differ from the rehearsed bytes")
    project = supabase_get("")
    if project["status"] != "ACTIVE_HEALTHY":
        problems.append("project not ACTIVE_HEALTHY")
    names = history()
    # 001-009 were applied before the history table existed.
    missing = sorted(
        m.stem for m in DEPLOYED if int(m.name[:3]) >= 10 and m.stem not in names
    )
    applied = sorted(m.stem for m in PENDING if m.stem in names)
    if missing:
        problems.append(f"history lacks {missing}")
    # Nothing mid-flight: an open matchday or a pending purchase waits for the window.
    busy = query(
        """select (select count(*) from public.seasons where status='active') as active_seasons,
        (select count(*) from public.matchdays where status='open') as open_matchdays,
        (select count(*) from public.purchases where status='pending') as pending_purchases"""
    )[0]
    if busy["open_matchdays"] or busy["pending_purchases"]:
        problems.append(
            "an open matchday or a pending purchase: wait or settle it first"
        )
    backup = None
    if args.backup:
        manifest = json.loads(Path(args.backup).read_text(encoding="utf-8"))
        rehearsal = json.loads(
            (Path(args.backup).parent / "rehearsal.json").read_text(encoding="utf-8")
        )
        age = datetime.now(UTC) - datetime.fromisoformat(manifest["captured_at"])
        backup = {
            "archive": manifest["archive"],
            "sha256": manifest["sha256"],
            "age_minutes": int(age.total_seconds() // 60),
        }
        if age > BACKUP_MAX_AGE:
            problems.append("backup older than 2 hours: capture and rehearse again")
        if (
            rehearsal.get("archive") != manifest["archive"]
            or rehearsal.get("result") != "PASS"
        ):
            problems.append("the rehearsal did not pass on this same archive")
    elif args.apply:
        problems.append("no rehearsed backup manifest given")
    return {
        "project": SUPABASE_REF,
        "history_records": len(names),
        "already_applied": applied,
        "to_apply": [m.name for m in PENDING if m.stem not in names],
        "activity": busy,
        "backup": backup,
        "problems": problems,
    }


def apply(args, plan: dict) -> list[dict]:
    out = Path(args.dir)
    results = []
    for migration in PENDING:
        if migration.name not in plan["to_apply"]:
            continue
        before = history()
        if migration.stem in before:
            raise SystemExit(
                f"{migration.stem} already recorded: reconcile, do not reapply"
            )
        intent = out / f"{migration.name[:3]}-migration-intent.json"
        result = out / f"{migration.name[:3]}-migration-result.json"
        if intent.exists() and not result.exists():
            raise SystemExit(
                f"earlier attempt of {migration.name} has no result: reconcile by hand"
            )
        sql = migration.read_text(encoding="utf-8")
        intent.write_text(json.dumps({"name": migration.stem, "sha256": hashlib.sha256(sql.encode()).hexdigest(),
                                      "at": datetime.now(UTC).isoformat()}), encoding="utf-8")  # fmt: skip
        _supabase(
            "POST",
            f"/v1/projects/{SUPABASE_REF}/database/migrations",
            {"name": migration.stem, "query": sql},
        )
        after = query(
            "select version, name from supabase_migrations.schema_migrations order by version"
        )
        added = [r for r in after if r["name"] == migration.stem]
        if len(added) != 1 or len(after) != len(before) + 1:
            raise SystemExit(
                f"{migration.stem}: history did not gain exactly one record"
            )
        result.write_text(json.dumps(added), encoding="utf-8")
        results.append(added[0])
        print(migration.stem, added[0]["version"], "applied once", flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dir", type=Path, required=True, help="owner-only private folder"
    )
    parser.add_argument("--backup", type=Path, help="manifest of the rehearsed backup")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--owner-authorized", action="store_true")
    args = parser.parse_args()
    plan = preflight(args)
    print(json.dumps(plan, indent=2, default=str))
    if not args.apply:
        return
    if not args.owner_authorized:
        raise SystemExit(
            "--apply needs the owner's explicit authorization (--owner-authorized)"
        )
    if plan["problems"]:
        raise SystemExit("pre-flight problems: " + "; ".join(plan["problems"]))
    apply(args, plan)


if __name__ == "__main__":
    main()
