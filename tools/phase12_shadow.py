"""Private, offline, read-only comparison of the fixed Phase 11 facts with V2.

No database client, migration renderer, legacy runtime loader or reward service
is invoked. Inputs are private atomic SELECT exports and the retained V1 capture.
Outputs contain classifications, never raw saves, credentials or source hashes.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from app.api.read_models import ShopRead, TrainerRead
from app.application.progress import progress_read
from app.domain.cup import Cup, CupFormat, CupMatch
from app.domain.seasons import SeasonLifecycle
from app.domain.services.cup_engine import CupRejected, validate as validate_modern_cup
from app.domain.shop import PurchaseStatus
from app.save_parser.models import ObservedSave, progress_evidence
from tools.phase11_import import SOURCE_REF, canonical_json, identity, loads, read


CLASSES = ("MATCH", "EXPECTED_DIFFERENCE", "UNKNOWN", "NOT_APPLICABLE", "BLOCKER")
TABLES = (
    "runs",
    "batches",
    "records",
    "identities",
    "trainers",
    "seasons",
    "participants",
    "saves",
    "progress",
    "wallets",
    "purchases",
    "cups",
    "cup_participants",
    "cup_matches",
    "exclusions",
)
DOMAINS = ("identities", "league", "save", "progress", "economy", "purchases", "cup")


def capture_sql() -> str:
    """One atomic private SELECT; fixed identifiers, no caller-supplied SQL."""
    return (
        "select jsonb_build_object("
        + ",".join(
            f"'{t}',(select coalesce(jsonb_agg(to_jsonb(x) order by to_jsonb(x)::text),"
            f"'[]'::jsonb) from v1_shadow.{t} x)"
            for t in TABLES
        )
        + ") as shadow"
    )


def _same(a, b):
    # bool is not an integer observation. Canonical JSON retains that distinction.
    return canonical_json(a) == canonical_json(b)


def _instant(value):
    timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        raise ValueError("Missing capture timezone")
    return timestamp.astimezone(timezone.utc)


def compare(
    shadow: dict,
    source: dict,
    parsed: dict,
    parser_summary: dict,
    source_bytes: bytes,
    candidates: list[dict],
) -> dict:
    """Classify source truth and exercise current pure V2 readers/validators.

    Migration mismatches and V2 interpretation failures have distinct origins.
    The comparator never repairs either input. Per-fact IDs and output order are
    stable, independent of database row order and execution wall-clock time.
    """
    findings = []

    def emit(domain, key, classification, reason, origin=None):
        findings.append(
            dict(
                id=f"{domain}/{key}",
                domain=domain,
                classification=classification,
                reason=reason,
                origin=origin,
            )
        )

    def check(domain, key, condition, reason):
        emit(
            domain,
            key,
            "MATCH" if condition else "BLOCKER",
            reason,
            None if condition else "PHASE 11 MIGRATION DEFECT",
        )
        return condition

    def interpret(domain, key, operation, reason, classification="MATCH"):
        try:
            if operation() is not True:
                raise ValueError("Interpretation differs")
        except (KeyError, TypeError, ValueError, AttributeError):
            emit(domain, key, "BLOCKER", reason, "V2 INTERPRETATION DEFECT")
        else:
            emit(domain, key, classification, reason)

    def finish():
        ordered = sorted(findings, key=lambda f: f["id"])
        counts = Counter(f["classification"] for f in ordered)
        return dict(
            schema_version=1,
            comparator_version="phase12-fixed-shadow/1",
            run_id=shadow.get("runs", [{}])[0].get("id")
            if shadow.get("runs")
            else None,
            counts={c: counts[c] for c in CLASSES},
            domains_compared=sorted(set(f["domain"] for f in ordered) & set(DOMAINS)),
            status="BLOCKED" if counts["BLOCKER"] else "PASS",
            comparison_scope="Fixed private legacy facts; no competitive promotion or relational mutation",
            findings=ordered,
        )

    try:
        if not check(
            "reference",
            "tables",
            set(shadow) == set(TABLES),
            "Only the fifteen approved private tables are accepted",
        ):
            return finish()
        if not check(
            "reference",
            "run",
            len(shadow["runs"]) == 1,
            "Exactly one captured migration reference",
        ):
            return finish()
        run = shadow["runs"][0]
        if not check(
            "reference",
            "certified",
            run["status"] == "reconciled"
            and run["source_ref"] == SOURCE_REF
            and run["mapping_version"] == "phase11-surviving-v1/1",
            "Only the reconciled, approved source mapping can be compared",
        ):
            return finish()
        batches = sorted(shadow["batches"], key=lambda b: b["ordinal"])
        if not check(
            "reference",
            "receipts",
            [b["ordinal"] for b in batches] == list(range(1, 7))
            and all(b["run_id"] == run["id"] and b["completed_at"] for b in batches),
            "Six completed atomic units, without replay",
        ):
            return finish()
        check(
            "reference",
            "capture_time",
            _instant(run["captured_at"]) == _instant(source["captured_at"]),
            "Capture timestamps compare as precise instants, not timezone display strings",
        )
        for table in TABLES[2:]:
            values = shadow[table]
            if not check(
                "reference",
                f"scope-{table}",
                len({r["id"] for r in values}) == len(values)
                and all(r["run_id"] == run["id"] for r in values),
                "Private rows have unique IDs and belong to this run",
            ):
                return finish()
        tables = {t["name"]: t["rows"] for t in source["tables"]}
        settings = {
            r["key"]: loads(r["value"]) if isinstance(r["value"], str) else r["value"]
            for r in tables["public.settings"]
            if not r["key"].startswith(("pin:", "discord_notify:"))
        }
        records = {
            (r["source_table"], r["source_key"]): r["payload"]
            for r in shadow["records"]
        }
        expected_records = {
            (t, str(r.get("key", r.get("id")))): r
            for t, rows in tables.items()
            for r in rows
            if not (
                t == "public.settings"
                and r["key"].startswith(("pin:", "discord_notify:"))
            )
        }

        def record_values(mapping):
            return [[t, k, mapping[(t, k)]] for t, k in sorted(mapping)]

        check(
            "reference",
            "retained_records",
            _same(record_values(records), record_values(expected_records)),
            "Retained noncredential source records match the fixed capture",
        )
        excluded = {
            "public.settings:" + r["key"]
            for r in tables["public.settings"]
            if r["key"].startswith(("pin:", "discord_notify:"))
        }
        check(
            "reference",
            "exclusions",
            {r["source_key"] for r in shadow["exclusions"]} == excluded
            and all(r["payload"] == {} for r in shadow["exclusions"]),
            "Credential/cache exclusions contain no copied values",
        )
        emit(
            "identities",
            "no_auth_merge",
            "EXPECTED_DIFFERENCE",
            "Legacy names map to isolated UUIDs; candidate V2 IDs neither establish ownership nor copy credentials",
        )

        identities = shadow["identities"]
        targets = {(t, r["id"]) for t in DOMAINS_TO_TABLES for r in shadow[t]}
        check(
            "identities",
            "complete_map",
            len(identities) == len(targets)
            and {(r["target_table"], r["target_id"]) for r in identities} == targets
            and all(
                r["entity_type"] == r["target_table"]
                and r["id"]
                == identity("identities", f"{r['entity_type']}:{r['source_key']}")
                and r["target_id"] == identity(r["entity_type"], r["source_key"])
                for r in identities
            ),
            "Each surviving typed entity has one deterministic, auditable mapping",
        )
        league = settings["league_state"]
        names = league["divisions"]["A"] + league["divisions"]["B"]
        trainers = {r["name"]: r for r in shadow["trainers"]}
        if not check(
            "identities",
            "roster",
            set(trainers) == set(names)
            and len(trainers) == len(names) == len(shadow["trainers"]),
            "Exact surviving trainer roster",
        ):
            return finish()
        candidate_ids = {r["display_name"]: r["id"] for r in candidates}
        for name in sorted(names):
            trainer = trainers[name]
            check(
                "identities",
                name,
                trainer["id"] == identity("trainers", name)
                and trainer["v2_candidate_id"] == candidate_ids.get(name),
                "Deterministic private trainer and annotation-only candidate",
            )
            interpret(
                "identities",
                name + "-v2",
                lambda t=trainer: (
                    TrainerRead(id=t["id"], display_name=t["name"]).model_dump(
                        mode="json"
                    )
                    == {"id": t["id"], "display_name": t["name"]}
                ),
                "Current V2 trainer projection accepts the isolated identity and name",
            )
        season = shadow["seasons"][0]
        sid = season["id"]
        check(
            "league",
            "context",
            len(shadow["seasons"]) == 1
            and sid == identity("seasons", "league_state")
            and _same(season["current_day"], league["tramo"])
            and _same(season["day_open"], league["active"])
            and season["effective_status"] == "active"
            and bool(season["status_provenance"]),
            "J1 and its editing state remain distinct from inferred legacy lifecycle",
        )
        interpret(
            "league",
            "v2_context",
            lambda: (
                SeasonLifecycle(season["effective_status"]) == SeasonLifecycle.ACTIVE
            ),
            "V2 recognizes the lifecycle value; missing dates prevent any claim of public activation",
        )
        emit(
            "league",
            "lifecycle",
            "EXPECTED_DIFFERENCE",
            "Legacy active=false governs day editing; missing lifecycle uses documented runtime fallback outside public active-season constraints",
        )
        check(
            "league",
            "unknown_timing_retained",
            season["started_at"] is None
            and season["configuration"].get("stored_configuration") is None,
            "No historical date/configuration version invented",
        )
        emit(
            "league",
            "historical_timing",
            "UNKNOWN",
            "Season start and effective historical rule timing were not recorded",
        )
        members = {r["trainer_id"]: r for r in shadow["participants"]}
        check(
            "league",
            "membership_count",
            len(members) == len(names) == len(shadow["participants"]),
            "One membership per surviving trainer",
        )
        check(
            "league",
            "capacities",
            season["configuration"]["observed_division_sizes"]
            == {d: len(league["divisions"][d]) for d in ("A", "B")},
            "Observed A/B capacities are retained, never recomputed from current progress",
        )
        for division in ("A", "B"):
            for index, name in enumerate(league["divisions"][division]):
                member = members[trainers[name]["id"]]
                check(
                    "league",
                    "member-" + name,
                    member["id"] == identity("participants", name)
                    and member["season_id"] == sid
                    and member["division"] == division
                    and member["seed_order"] == index
                    and _same(
                        member["flags"], settings.get("trainer_flags", {}).get(name, {})
                    ),
                    "Division, relative order and legacy flags match; no modern robbery effect implied",
                )

        save = shadow["saves"][0]
        original = tables["public.saves"][0]
        owner = original["user"]
        body = (
            bytes.fromhex(save["content"][2:])
            if save["content"].startswith("\\x")
            else b""
        )
        if not check(
            "save",
            "continuity",
            len(shadow["saves"]) == len(tables["public.saves"]) == 1
            and body == source_bytes
            and sha256(body).hexdigest() == save["sha256"] == original["sha256"]
            and save["id"] == identity("saves", str(original["id"]))
            and save["source_save_id"] == str(original["id"])
            and save["filename"] == original["filename"]
            and save["source_created_at"] == original["created_at"]
            and save["trainer_id"] == trainers[owner]["id"]
            and settings[f"current_save:{owner}"] == original["id"]
            and _same(save["parsed"], parsed),
            "Source bytes, hash, owner, pointer, timestamp text and neutral parse all match",
        ):
            return finish()
        observation = ObservedSave.model_validate_json(canonical_json(save["parsed"]))
        envelope = progress_evidence(observation, save["sha256"])
        check(
            "save",
            "parser_binding",
            parser_summary["source_copy_hash"] == save["sha256"]
            and _same(parser_summary["progress"], envelope["progress"]),
            "Retained parser evidence is bound to the same immutable source bytes",
        )
        emit(
            "save",
            "upload_timezone",
            "UNKNOWN",
            "Legacy timestamp text has no proven timezone; no modern upload time is invented",
        )
        emit(
            "save",
            "authority",
            "EXPECTED_DIFFERENCE",
            "Private original bytes and neutral DTO are not modern current-save acceptance, identity allocation or Team Lock",
        )

        progress = {r["trainer_id"]: r for r in shadow["progress"]}
        check(
            "progress",
            "coverage",
            len(progress) == len(names) == len(shadow["progress"]),
            "Every participant has explicit observed or unknown progress",
        )
        for name in sorted(names):
            row = progress[trainers[name]["id"]]
            known = name == owner
            expected_count = (
                sum(sum(r.badge_flags) for r in observation.progress.regions)
                if known
                else None
            )
            expected_dead = (
                sum(
                    p is not None
                    for b in observation.boxes
                    if b.number == 8
                    for p in b.slots
                )
                if known
                else None
            )
            valid = (
                row["id"] == identity("progress", name)
                and row["season_id"] == sid
                and row["save_id"] == (save["id"] if known else None)
            )
            valid = (
                valid
                and _same(row["badge_count"], expected_count)
                and _same(row["visible_deaths"], expected_dead)
            )
            valid = valid and _same(
                row["champion_defeated"],
                observation.progress.champion_defeated if known else None,
            )
            valid = valid and row["source_kind"] == (
                "captured_v1_save_reparse_private_not_competitive"
                if known
                else "unobserved"
            )
            if not check(
                "progress",
                name + "-source",
                valid,
                "Progress and deaths retain their observed/unknown provenance",
            ):
                continue

            def projected_matches():
                projected = progress_read(
                    dict(
                        progress=envelope["progress"] if known else None,
                        game=observation.game if known else None,
                        observed_at=parser_summary["observed_at"] if known else None,
                    )
                )
                return (
                    projected.badges_count == row["badge_count"]
                    and projected.champion_defeated is row["champion_defeated"]
                    and projected.state == ("observed" if known else "unknown")
                )

            interpret(
                "progress",
                name,
                projected_matches,
                "Current V2 progress reader preserves count and independent Champion state",
                "MATCH" if known else "UNKNOWN",
            )
        emit(
            "progress",
            "adjusted_deaths",
            "UNKNOWN",
            "Visible Box-8 facts do not prove missing historical wipe/revive contributions or frozen penalties",
        )

        purchases = {r["source_purchase_id"]: r for r in shadow["purchases"]}
        spend = {name: Decimal(0) for name in names}
        check(
            "purchases",
            "coverage",
            len(purchases)
            == len(tables["public.purchases"])
            == len(shadow["purchases"]),
            "All surviving purchases accounted for once",
        )
        for original_purchase in tables["public.purchases"]:
            p = purchases[str(original_purchase["id"])]
            name = original_purchase["user"]
            spend[name] += Decimal(original_purchase["price"])
            check(
                "purchases",
                p["source_purchase_id"],
                p["id"] == identity("purchases", str(original_purchase["id"]))
                and p["trainer_id"] == trainers[name]["id"]
                and p["season_id"] == sid
                and Decimal(p["price"]) == Decimal(original_purchase["price"])
                and p["item"] == original_purchase["item"]
                and p["status"] == original_purchase["status"]
                and p["day_number"] == original_purchase["jornada"]
                and p["source_created_at"] == original_purchase["created_at"],
                "Original ownership, exact price, pending state, day and timestamp text retained",
            )
            interpret(
                "purchases",
                p["source_purchase_id"] + "-pending",
                lambda p=p: PurchaseStatus(p["status"]) == PurchaseStatus.PENDING,
                "Current purchase status distinguishes a pending purchase from a redeemed effect",
            )
        emit(
            "purchases",
            "already_spent",
            "EXPECTED_DIFFERENCE",
            "Legacy pending purchases already reduce the snapshot; no modern purchase command or second debit executes",
        )
        emit(
            "purchases",
            "timestamps",
            "UNKNOWN",
            "Purchase timestamp timezones and unrecorded SKU/timing history remain unproven",
        )
        wallets = {r["trainer_id"]: r for r in shadow["wallets"]}
        check(
            "economy",
            "coverage",
            len(wallets) == len(names) == len(shadow["wallets"]),
            "One explicit private wallet state per trainer",
        )
        for name in sorted(names):
            wallet = wallets[trainers[name]["id"]]
            known = name == owner
            earned = Decimal(settings[f"badges_count:{owner}"]) * 4 if known else None
            expected_balance = max(Decimal(0), earned - spend[name]) if known else None
            valid = (
                wallet["id"] == identity("wallets", name)
                and wallet["season_id"] == sid
                and wallet["known"] is known
            )
            valid = (
                valid
                and wallet["badge_earnings"] == earned
                and wallet["spend"] == spend[name]
            )
            valid = valid and all(
                wallet[k] == 0
                for k in ("league_earnings", "completion_earnings", "sanctions")
            )
            valid = (
                valid
                and wallet["balance"] == expected_balance
                and wallet["badge_high_water"] == (int(earned / 4) if known else None)
            )
            if not check(
                "economy",
                name + "-source",
                valid,
                "Exact surviving legacy formula, including pending spend; unknown balance is never zero",
            ):
                continue
            balance = (
                str(int(expected_balance))
                if known and expected_balance == expected_balance.to_integral_value()
                else None
            )
            if known and balance is None:
                emit(
                    "economy",
                    name,
                    "BLOCKER",
                    "Known legacy amount is not an integer supported by the current V2 wallet contract",
                    "V2 INTERPRETATION DEFECT",
                )
                continue
            interpret(
                "economy",
                name,
                lambda b=balance: (
                    ShopRead(
                        items=[], promotions=[], balance=b, season_status="active"
                    ).balance
                    == b
                ),
                "V2 wallet read DTO preserves the known integer string or unknown null; no ledger synthesized",
                "MATCH" if known else "UNKNOWN",
            )
        emit(
            "economy",
            "ledger",
            "EXPECTED_DIFFERENCE",
            "Legacy derived opening snapshot is not modern ledger history or authority for badge/completion settlement",
        )

        source_cup = settings["copa_swiss_state"]
        cup = shadow["cups"][0]
        check(
            "cup",
            "context",
            len(shadow["cups"]) == 1
            and cup["id"] == identity("cups", "copa_swiss_state")
            and cup["season_id"] == sid
            and cup["format"] == "legacy_swiss"
            and cup["rules_version"] is None
            and cup["round"] == source_cup["round"]
            and cup["max_rounds"] == source_cup["max_rounds"]
            and _same(cup["source_state"], source_cup),
            "Original legacy Cup state retained without a modern certificate",
        )
        cup_members = sorted(shadow["cup_participants"], key=lambda r: r["seed_order"])
        check(
            "cup",
            "members",
            [r["trainer_id"] for r in cup_members]
            == [trainers[n]["id"] for n in source_cup["players"]]
            and all(
                r["id"] == identity("cup_participants", n)
                and r["cup_id"] == cup["id"]
                and all(r[k] == source_cup[k][n] for k in ("wins", "losses", "byes"))
                for r, n in zip(cup_members, source_cup["players"], strict=True)
            ),
            "Cup membership/order and explicit zero standings are separate from missing League results",
        )
        matches = sorted(shadow["cup_matches"], key=lambda r: r["position"])
        check(
            "cup",
            "pairs",
            [(r["first_trainer_id"], r["second_trainer_id"]) for r in matches]
            == [
                (trainers[a]["id"], trainers[b]["id"])
                for a, b in source_cup["current"]["pairs"]
            ]
            and all(
                r["cup_id"] == cup["id"]
                and r["round"] == source_cup["round"]
                and r["winner_id"] is None
                and r["position"] == i
                and r["id"] == identity("cup_matches", f"1:{i}")
                for i, r in enumerate(matches)
            ),
            "Pending pairings remain in their original order with no inferred winner",
        )
        represented = Cup(
            id=cup["id"],
            season_id=sid,
            format=CupFormat.SWISS,
            name="Legacy source Cup",
            player_ids=tuple(r["trainer_id"] for r in cup_members),
            current_round=cup["round"],
            max_rounds=cup["max_rounds"],
            configured=source_cup.get("configured", False),
        )
        interpreted_matches = [
            CupMatch(
                id=m["id"],
                cup_id=cup["id"],
                round_number=m["round"],
                participant_a_id=m["first_trainer_id"],
                participant_b_id=m["second_trainer_id"],
                winner_id=m["winner_id"],
            )
            for m in matches
        ]
        interpret(
            "cup",
            "v2_representation",
            lambda: (
                not represented.champion_id
                and represented.player_ids
                == tuple(r["trainer_id"] for r in cup_members)
                and represented.current_round == cup["round"]
                and represented.max_rounds == cup["max_rounds"]
                and all(
                    not m.winner_id
                    and m.participant_a_id == r["first_trainer_id"]
                    and m.participant_b_id == r["second_trainer_id"]
                    and m.round_number == r["round"]
                    for m, r in zip(interpreted_matches, matches, strict=True)
                )
            ),
            "Existing V2 legacy Cup value objects retain participants, pairs and absent winners",
        )
        try:
            validate_modern_cup({"rules_version": cup["rules_version"]})
        except CupRejected as error:
            rejection = str(error) == "UNSUPPORTED_RULES"
        else:
            rejection = False
        interpret(
            "cup",
            "certification_boundary",
            lambda: rejection,
            "Modern V2 certification rejects legacy null rules rather than inventing a champion",
            "EXPECTED_DIFFERENCE",
        )

        absent = {
            "results": not league["matches"] and not league["results"],
            "official_rankings": not league["round_snapshots"]
            and not league["movements"],
            "team_locks": not tables["public.team_locks"],
            "redemptions": not tables["public.redemptions"],
            "promotions": not tables["public.shop_discounts"],
            "sanctions": not any(k.startswith(("trial", "sanction")) for k in settings),
            "championship": not source_cup["results"]
            and not source_cup["history"]
            and not league["results"],
            "hall_archive": not any(
                k.startswith(("hall", "season_archive")) for k in settings
            ),
        }
        for domain, empty in absent.items():
            emit(
                domain,
                "absent",
                "NOT_APPLICABLE" if empty else "BLOCKER",
                "No surviving authoritative facts; no reconstruction or fabricated comparison",
                None if empty else "PHASE 11 MIGRATION DEFECT",
            )
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
        emit(
            "reference",
            "invalid_input",
            "BLOCKER",
            "Malformed or contradictory fixed reference; inspect private input without rewriting it",
            "REFERENCE VALIDATION FAILURE",
        )
    return finish()


DOMAINS_TO_TABLES = (
    "trainers",
    "seasons",
    "participants",
    "saves",
    "progress",
    "wallets",
    "purchases",
    "cups",
    "cup_participants",
    "cup_matches",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--shadow", type=Path, required=True, help="Private atomic SELECT export"
    )
    parser.add_argument(
        "--source", type=Path, required=True, help="Retained Phase11 v1 directory"
    )
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = read(args.source / "raw-capture.json")[0]
    saved = next(t for t in source["tables"] if t["name"] == "public.saves")["rows"][0]
    filename = saved["filename"]
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise ValueError("Unsafe captured source filename")
    result = compare(
        read(args.shadow)[0]["shadow"],
        source,
        read(args.source / "parsed-save-private.json"),
        read(args.source / "parsed-save-summary.json"),
        (args.source / "storage-copy" / filename).read_bytes(),
        read(args.candidates),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(result) + "\n", encoding="utf-8")
    print(canonical_json({"status": result["status"], "counts": result["counts"]}))
    return 1 if result["status"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
