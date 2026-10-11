"""Deterministic mapping of surviving V1 facts into the private Shadow schema.

This module only reads private captures and produces a private plan. It never
connects to a database, authenticates a player, or issues competitive rewards.
The deliberately bounded mapping rejects newly discovered domains for review.
"""

from __future__ import annotations

import argparse
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from app.save_parser.models import ObservedSave
from tools.phase11_sql import _json as canonical_json


SOURCE_REF = "fdtytpeyfzyssfrsulxd"
MAPPING_VERSION = "phase11-surviving-v1/1"
NAMESPACE = UUID("ad7da12c-0f68-57bc-bc41-4c675d2664f9")
SOURCE_TABLES = {
    "public.settings", "public.saves", "public.purchases", "public.redemptions",
    "public.pokemon_flags", "public.shop_discounts", "public.team_locks",
    "auth.users", "auth.identities", "auth.sessions", "auth.refresh_tokens",
    "storage.buckets", "storage.objects",
}
EMPTY_DOMAINS = {
    "public.redemptions", "public.pokemon_flags", "public.shop_discounts",
    "public.team_locks", "auth.users", "auth.identities", "auth.sessions",
    "auth.refresh_tokens",
}


def digest(value: Any) -> str:
    return sha256(canonical_json(value).encode("utf-8")).hexdigest()


def identity(kind: str, key: str) -> str:
    return str(uuid5(NAMESPACE, f"{SOURCE_REF}:{kind}:{key}"))


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON source key")
        value[key] = item
    return value


def loads(value: str) -> Any:
    return json.loads(value, parse_float=Decimal, object_pairs_hook=_pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def read(path: Path) -> Any:
    return loads(path.read_text(encoding="utf-8-sig"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def integer(value: Any, *, minimum: int = 0) -> int:
    require(type(value) is int and value >= minimum, "Invalid integer source fact")
    return value


def money(value: Any) -> Decimal:
    require(type(value) in (int, Decimal), "Money must be an exact numeric source fact")
    result = Decimal(value)
    require(result.is_finite() and result >= 0, "Invalid monetary source fact")
    return result


def validate_plan(plan: dict) -> None:
    from tools.phase11_sql import _validate

    _validate(plan)
    for batch in plan["batches"]:
        require(batch["hash"] == digest({"ordinal": batch["ordinal"], "tables": batch["tables"]}),
                "Batch content fingerprint mismatch")
    unsigned = {"run": {k: v for k, v in plan["run"].items() if k != "plan_hash"},
                "batches": plan["batches"]}
    require(plan["run"]["plan_hash"] == digest(unsigned), "Plan content fingerprint mismatch")


def build_plan(capture_path: Path, parsed_path: Path, save_directory: Path,
               candidates_path: Path | None = None) -> dict:
    project = read(capture_path.with_name("project.json"))
    require(project.get("id") == SOURCE_REF, "Capture bundle belongs to another source project")
    capture_list = read(capture_path)
    require(isinstance(capture_list, list) and len(capture_list) == 1, "Expected one atomic V1 capture")
    capture = capture_list[0]
    tables = {t["name"]: t for t in capture["tables"]}
    require(len(tables) == len(capture["tables"]) and set(tables) == SOURCE_TABLES,
            "Source catalog differs from the verified surviving V1 profile")
    for table in tables.values():
        require(table["count"] == len(table["rows"]), "Source count differs from captured rows")
    for name in EMPTY_DOMAINS:
        require(not tables[name]["rows"], "New surviving domain requires an explicit mapping")
    settings = {}
    for row in tables["public.settings"]["rows"]:
        require(row["key"] not in settings, "Duplicate V1 setting")
        settings[row["key"]] = (None if row["key"].startswith(("pin:", "discord_notify:"))
                                else loads(row["value"]) if isinstance(row["value"], str) else row["value"])
    permitted = {"league_state", "copa_swiss_state", "trainer_flags"}
    for key in settings:
        require(key in permitted or key.startswith(("pin:", "discord_notify:", "badges_count:",
                                                    "current_save:", "trainer_snapshot:")),
                "Unmapped surviving V1 setting")
    league = settings["league_state"]
    require(set(league) == {"tramo", "active", "divisions", "matches", "results", "movements", "round_snapshots"},
            "League source shape changed")
    require(all(not league[k] for k in ("matches", "results", "movements", "round_snapshots")),
            "Surviving League history requires mapping; do not reconstruct it")
    require(set(league["divisions"]) == {"A", "B"} and type(league["active"]) is bool,
            "Invalid League divisions/day state")
    names = league["divisions"]["A"] + league["divisions"]["B"]
    require(names and all(isinstance(n, str) and n.strip() == n and n for n in names)
            and len(set(names)) == len(names), "Ambiguous source trainer identities")
    for key in settings:
        if key.startswith(("badges_count:", "current_save:", "trainer_snapshot:", "pin:")):
            require(key.split(":", 1)[1] in names, "Setting belongs to a trainer outside the captured roster")
    flags = settings.get("trainer_flags", {})
    require(set(flags) <= set(names), "Flags reference an unknown trainer")
    # Hash the full private capture, but never export credential rows or their individual hashes.
    capture_hash = digest([{ "name": name, "rows": tables[name]["rows"]} for name in sorted(tables)])
    run_id = identity("run", f"{MAPPING_VERSION}:{capture_hash}")
    rows: dict[str, list] = {name: [] for name in (
        "records", "exclusions", "trainers", "seasons", "participants", "saves", "progress",
        "wallets", "purchases", "cups", "cup_participants", "cup_matches", "identities")}

    def add(table: str, key: str, **values) -> str:
        target = identity(table, key)
        rows[table].append({"run_id": run_id, "id": target, **values})
        if table not in {"identities", "records", "exclusions"}:
            rows["identities"].append({"run_id": run_id, "id": identity("identities", f"{table}:{key}"),
                                       "entity_type": table, "source_key": key,
                                       "target_table": table, "target_id": target})
        return target

    for table in sorted(tables):
        for record in tables[table]["rows"]:
            key = str(record.get("key", record.get("id")))
            require(key != "None", "Source record lacks a stable identity")
            if table == "public.settings" and key.startswith(("pin:", "discord_notify:")):
                add("exclusions", f"{table}:{key}", source_key=f"{table}:{key}",
                    reason="Credential is not migrated" if key.startswith("pin:") else "Notification cache is not domain history",
                    payload={})
                continue
            add("records", f"{table}:{key}", source_table=table, source_key=key, payload=record)
    candidates = {}
    if candidates_path is not None:
        for row in read(candidates_path):
            name = row["display_name"]
            require(name not in candidates, "Ambiguous V2 candidate name")
            candidates[name] = str(UUID(row["id"]))
    trainers = {name: add("trainers", name, name=name, v2_candidate_id=candidates.get(name)) for name in names}
    season = add("seasons", "league_state", source_key="league_state", effective_status="active",
                 status_provenance="Absent season_lifecycle_v1: tracked legacy runtime default; not a stored historical status or verified deployment revision",
                 started_at=None, current_day=integer(league["tramo"], minimum=1), day_open=league["active"],
                 configuration={"stored_configuration": None,
                                "observed_division_sizes": {d: len(league["divisions"][d]) for d in ("A", "B")}})
    for division in ("A", "B"):
        for index, name in enumerate(league["divisions"][division]):
            add("participants", name, season_id=season, trainer_id=trainers[name], division=division,
                seed_order=index, flags=flags.get(name, {}))

    source_saves = tables["public.saves"]["rows"]
    require(len(source_saves) == 1, "This verified profile requires exactly one surviving save")
    source_save = source_saves[0]
    owner = source_save["user"]
    require(owner in trainers, "Save owner is outside source roster")
    filename = source_save["filename"]
    require(Path(filename).name == filename and "/" not in filename and "\\" not in filename,
            "Unsafe source save filename")
    content = (save_directory / filename).read_bytes()
    require(sha256(content).hexdigest() == source_save["sha256"], "Source save bytes differ from captured metadata")
    parsed = read(parsed_path)
    observed = ObservedSave.model_validate_json(canonical_json(parsed))
    summary = read(parsed_path.with_name("parsed-save-summary.json"))
    require(summary["source_copy_hash"] == source_save["sha256"] and summary["progress"] == parsed["progress"]
            and summary["game"] == parsed["game"] and summary["physical_save_write"] is False,
            "Parsed evidence is not bound to this captured source save")
    require(observed.progress is not None, "Verified source progress unexpectedly absent")
    badges = sum(sum(region.badge_flags) for region in observed.progress.regions)
    dead_boxes = [box for box in observed.boxes if box.number == 8]
    require(len(dead_boxes) == 1, "Dead Box 8 is unobserved; cannot infer zero deaths")
    dead = sum(p is not None for p in dead_boxes[0].slots)
    require(summary["visible_dead_count"] == dead, "Parsed death evidence differs from capture summary")
    require(settings.get(f"current_save:{owner}") == source_save["id"]
            and settings.get(f"badges_count:{owner}") == badges, "Legacy progress/current-save mapping conflict")
    save_id = add("saves", str(source_save["id"]), trainer_id=trainers[owner], source_save_id=str(source_save["id"]),
                  sha256=source_save["sha256"], filename=filename, source_created_at=source_save["created_at"],
                  content="\\x" + content.hex(), parsed=parsed)
    for name in names:
        known = name == owner
        add("progress", name, season_id=season, trainer_id=trainers[name], save_id=save_id if known else None,
            badge_count=badges if known else None,
            champion_defeated=observed.progress.champion_defeated if known else None,
            visible_deaths=dead if known else None,
            source_kind="captured_v1_save_reparse_private_not_competitive" if known else "unobserved")
        if not known:
            require(f"badges_count:{name}" not in settings and f"current_save:{name}" not in settings
                    and f"trainer_snapshot:{name}" not in settings, "Additional legacy progress needs explicit evidence")
    spent = {name: Decimal(0) for name in names}
    for purchase in tables["public.purchases"]["rows"]:
        name = purchase["user"]
        require(name in trainers and purchase["status"] == "pending" and purchase["redeemed_at"] is None
                and purchase["discount_id"] is None, "Unsupported surviving purchase semantics")
        price = money(purchase["price"])
        spent[name] += price
        add("purchases", str(purchase["id"]), season_id=season, trainer_id=trainers[name],
            source_purchase_id=str(purchase["id"]), item=purchase["item"], price=price, status=purchase["status"],
            day_number=integer(purchase["jornada"], minimum=1), source_created_at=purchase["created_at"])
    for name in names:
        known = name == owner
        earnings = Decimal(badges * 4) if known else None
        add("wallets", name, season_id=season, trainer_id=trainers[name], badge_earnings=earnings,
            league_earnings=Decimal(0), completion_earnings=Decimal(0), spend=spent[name], sanctions=Decimal(0),
            balance=max(Decimal(0), earnings - spent[name]) if known else None,
            known=known, badge_high_water=badges if known else None)

    cup = settings["copa_swiss_state"]
    require(not any(cup.get(k) for k in ("history", "results", "qualified", "eliminated", "topcut")),
            "Surviving Cup history requires an explicit mapping")
    players = cup["players"]
    require(len(players) == len(set(players)) and set(players) <= set(names), "Invalid Cup roster")
    require(cup["current"].get("bye") is None, "Unmapped Cup bye")
    cup_id = add("cups", "copa_swiss_state", season_id=season, source_key="copa_swiss_state",
                 format="legacy_swiss", round=integer(cup["round"], minimum=1),
                 max_rounds=integer(cup["max_rounds"], minimum=1), rules_version=None, source_state=cup)
    for index, name in enumerate(players):
        values = {k: integer(cup[k][name]) for k in ("wins", "losses", "byes")}
        require(not any(values.values()), "Cup standings differ from verified empty history")
        add("cup_participants", name, cup_id=cup_id, trainer_id=trainers[name], seed_order=index, **values)
    paired = []
    for index, pair in enumerate(cup["current"]["pairs"]):
        require(len(pair) == 2 and pair[0] != pair[1] and set(pair) <= set(players), "Invalid pending Cup pair")
        paired.extend(pair)
        add("cup_matches", f"1:{index}", cup_id=cup_id, round=cup["round"], position=index,
            first_trainer_id=trainers[pair[0]], second_trainer_id=trainers[pair[1]], winner_id=None)
    require(len(paired) == len(set(paired)) and set(paired) == set(players), "Cup pending pairs do not cover its roster")
    groups = [("records", "exclusions", "trainers", "seasons"), ("participants",), ("saves", "progress"),
              ("wallets", "purchases"), ("cups", "cup_participants", "cup_matches"), ("identities",)]
    batches = []
    for ordinal, group in enumerate(groups, start=1):
        batch = {"ordinal": ordinal, "tables": {t: rows[t] for t in group}}
        batches.append({**batch, "hash": digest(batch)})
    run = {"id": run_id, "source_ref": SOURCE_REF, "capture_hash": capture_hash,
           "mapping_version": MAPPING_VERSION, "captured_at": capture["captured_at"], "status": "prepared",
           "manifest": {"source_snapshot": capture["snapshot"],
                        "source_counts": {t: tables[t]["count"] for t in sorted(tables)},
                        "destination_counts": {t: len(r) for t, r in rows.items()},
                        "parser_version": summary["parser_version"],
                        "parsed_observed_at": summary["observed_at"],
                        "semantics": "Private surviving facts only; no modern identity merge, progress acceptance, rewards, history reconstruction or cutover",
                        "wallet_basis": "Tracked legacy formula, 4 per badge; all purchases spent including pending; no surviving League awards, sanctions or completion claim; clamp zero",
                        "unknown_dates": "Source text retained without invented timezone; season start unknown"}}
    plan = {"run": run, "batches": batches}
    run["plan_hash"] = digest(plan)
    validate_plan(plan)
    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--parsed", type=Path, required=True)
    parser.add_argument("--saves", type=Path, required=True)
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--output", type=Path, required=True, help="Private path: plan includes raw save and source facts")
    args = parser.parse_args()
    plan = build_plan(args.capture, args.parsed, args.saves, args.candidates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(canonical_json(plan), encoding="utf-8")
    print(json.dumps({"run_id": plan["run"]["id"], "batches": len(plan["batches"]),
                      "counts": plan["run"]["manifest"]["destination_counts"]}))


if __name__ == "__main__":
    main()
