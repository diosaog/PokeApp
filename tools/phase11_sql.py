"""Render atomic owner-only imports into the isolated Phase 11 destination.

Returned SQL contains private source material. Store it only in private evidence
directories and never log an entire failed statement. This module does not execute
SQL, connect to either project, or call competitive V2 functions.
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
import json
import re
from typing import Any
from uuid import UUID


TABLE_COLUMNS = {
    "records": "run_id id source_table source_key payload",
    "identities": "run_id id entity_type source_key target_table target_id",
    "trainers": "run_id id name v2_candidate_id",
    "seasons": (
        "run_id id source_key effective_status status_provenance started_at "
        "current_day day_open configuration"
    ),
    "participants": "run_id id season_id trainer_id division seed_order flags",
    "saves": (
        "run_id id trainer_id source_save_id sha256 filename source_created_at "
        "content parsed"
    ),
    "progress": (
        "run_id id season_id trainer_id save_id badge_count champion_defeated "
        "visible_deaths source_kind"
    ),
    "wallets": (
        "run_id id season_id trainer_id badge_earnings league_earnings "
        "completion_earnings spend sanctions balance known badge_high_water"
    ),
    "purchases": (
        "run_id id season_id trainer_id source_purchase_id item price status "
        "day_number source_created_at"
    ),
    "cups": "run_id id season_id source_key format round max_rounds rules_version source_state",
    "cup_participants": "run_id id cup_id trainer_id seed_order wins losses byes",
    "cup_matches": (
        "run_id id cup_id round position first_trainer_id second_trainer_id winner_id"
    ),
    "exclusions": "run_id id source_key reason payload",
}
RUN_COLUMNS = frozenset(
    "id source_ref capture_hash mapping_version plan_hash captured_at manifest status".split()
)
TABLE_ORDER = tuple(TABLE_COLUMNS)
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_LOCK_KEY = 7_114_200_042


def _json(value: Any) -> str:
    """Exact JSON: never convert Decimal through binary floating point."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Non-finite source number")
        return str(value)
    if isinstance(value, list):
        return "[" + ",".join(_json(item) for item in value) + "]"
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise ValueError("JSON object keys must be strings")
        return "{" + ",".join(_json(key) + ":" + _json(value[key]) for key in sorted(value)) + "}"
    raise ValueError("Unsupported source value type; use exact Decimal numbers")


def _literal(value: str) -> str:
    if "\x00" in value:
        raise ValueError("NUL is not a PostgreSQL text value")
    return "'" + value.replace("'", "''") + "'"


def _json_literal(value: Any) -> str:
    return _literal(_json(value)) + "::jsonb"


def _validate(plan: Mapping[str, Any]) -> None:
    if not isinstance(plan, Mapping) or not {"run", "batches"} <= set(plan):
        raise ValueError("Invalid Phase 11 plan")
    run = plan["run"]
    if not isinstance(run, Mapping) or set(run) != RUN_COLUMNS:
        raise ValueError("Run must contain precisely the schema run columns")
    UUID(run["id"])
    if run["status"] != "prepared":
        raise ValueError("An import plan must start prepared")
    if not all(isinstance(run[key], str) and _HEX.fullmatch(run[key]) for key in ("capture_hash", "plan_hash")):
        raise ValueError("Invalid run fingerprint")
    if not isinstance(run["manifest"], Mapping):
        raise ValueError("Manifest must be an object")
    batches = plan["batches"]
    if not isinstance(batches, list) or not batches:
        raise ValueError("Import must contain at least one explicit batch")
    seen: set[tuple[str, str]] = set()
    for index, batch in enumerate(batches, start=1):
        if not isinstance(batch, Mapping) or set(batch) != {"ordinal", "hash", "tables"}:
            raise ValueError("Invalid batch shape")
        if type(batch["ordinal"]) is not int or batch["ordinal"] != index:
            raise ValueError("Batch ordinals must be the contiguous sequence 1..N")
        if not isinstance(batch["hash"], str) or not _HEX.fullmatch(batch["hash"]):
            raise ValueError("Invalid batch fingerprint")
        tables = batch["tables"]
        if not isinstance(tables, Mapping) or not set(tables) <= set(TABLE_COLUMNS):
            raise ValueError("Unknown isolated destination table")
        for table, rows in tables.items():
            if not isinstance(rows, list):
                raise ValueError("Rows must be a list")
            allowed = set(TABLE_COLUMNS[table].split())
            for row in rows:
                if not isinstance(row, Mapping) or not {"id", "run_id"} <= set(row) <= allowed:
                    raise ValueError("Unexpected destination column")
                if row["run_id"] != run["id"]:
                    raise ValueError("Row belongs to another capture")
                UUID(row["id"])
                identity = (table, row["id"])
                if identity in seen:
                    raise ValueError("Duplicate target identity in plan")
                seen.add(identity)
    # Reject unsupported types before constructing any executable statement.
    _json(plan)


def _begin() -> str:
    return (
        "BEGIN;\n"
        "SET LOCAL search_path = pg_catalog;\n"
        "SET LOCAL standard_conforming_strings = on;\n"
        f"SELECT pg_catalog.pg_advisory_xact_lock({_LOCK_KEY});\n"
    )


def _assert(condition: str, label: str) -> str:
    # The diagnostic never embeds a source row. Avoid DO dollar quoting: legacy
    # strings can legitimately contain any dollar-quote delimiter.
    return f"SELECT 1 / CASE WHEN ({condition}) THEN 1 ELSE 0 END AS phase11_{label};\n"


def _expected_batches(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "ordinal": batch["ordinal"],
            "batch_hash": batch["hash"],
            "row_counts": {table: len(rows) for table, rows in batch["tables"].items()},
        }
        for batch in plan["batches"]
    ]


def _assert_state(
    plan: Mapping[str, Any], *, complete: bool = False, staged: bool = False
) -> str:
    """Compare all durable rows against exactly the receipted plan prefix."""
    run_id = _literal(plan["run"]["id"]) + "::uuid"
    ctes = [
        "expected_run AS (SELECT * FROM pg_catalog.jsonb_populate_record(NULL::v1_shadow.runs, "
        + _json_literal(plan["run"])
        + "))",
        "expected_batches AS (SELECT * FROM pg_catalog.jsonb_to_recordset("
        + _json_literal(_expected_batches(plan))
        + ") AS b(ordinal integer, batch_hash text, row_counts jsonb))",
    ]
    conditions = [
        "(SELECT count(*) FROM v1_shadow.runs) = 1",
        "EXISTS (SELECT 1 FROM v1_shadow.runs a CROSS JOIN expected_run e "
        "WHERE (pg_catalog.to_jsonb(a) - 'status') = (pg_catalog.to_jsonb(e) - 'status') "
        "AND a.status IN ('prepared', 'reconciled'))",
        "NOT EXISTS (SELECT 1 FROM v1_shadow.batches a WHERE a.run_id <> " + run_id + ")",
        "NOT EXISTS (SELECT 1 FROM v1_shadow.batches a LEFT JOIN expected_batches e "
        "ON a.ordinal = e.ordinal WHERE e.ordinal IS NULL OR a.batch_hash <> e.batch_hash "
        "OR a.row_counts <> e.row_counts OR a.completed_at IS NULL)",
        "(SELECT count(*) = coalesce(max(ordinal), 0) AND coalesce(min(ordinal), 1) = 1 "
        "FROM v1_shadow.batches)",
        "NOT EXISTS (SELECT 1 FROM v1_shadow.runs WHERE status = 'reconciled' "
        f"AND (SELECT count(*) FROM v1_shadow.batches) <> {len(plan['batches'])})",
    ]
    if complete:
        conditions.append(f"(SELECT count(*) FROM v1_shadow.batches) = {len(plan['batches'])}")
    for table in TABLE_ORDER:
        if staged:
            # Reuse the transaction-local plan. The save's bytea JSON can exceed
            # a megabyte; repeating it in precheck/insert/postcheck exceeds the
            # management transport limit without adding any verification value.
            source = (
                "FROM pg_temp.phase11_expected_plan p "
                "CROSS JOIN LATERAL pg_catalog.jsonb_array_elements(p.payload -> 'batches') b(value) "
                f"CROSS JOIN LATERAL pg_catalog.jsonb_populate_recordset(NULL::v1_shadow.{table}, "
                f"coalesce(b.value -> 'tables' -> '{table}', '[]'::jsonb)) e "
                "WHERE EXISTS (SELECT 1 FROM v1_shadow.batches receipt "
                "WHERE receipt.ordinal = (b.value ->> 'ordinal')::integer))"
            )
        else:
            payload = [
                {"ordinal": batch["ordinal"], "rows": batch["tables"][table]}
                for batch in plan["batches"]
                if batch["tables"].get(table)
            ]
            source = (
                "FROM pg_catalog.jsonb_to_recordset("
                + _json_literal(payload)
                + ") AS b(ordinal integer, rows jsonb) "
                f"CROSS JOIN LATERAL pg_catalog.jsonb_populate_recordset(NULL::v1_shadow.{table}, b.rows) e "
                "WHERE EXISTS (SELECT 1 FROM v1_shadow.batches receipt WHERE receipt.ordinal = b.ordinal))"
            )
        ctes.append(f"expected_{table} AS (SELECT pg_catalog.to_jsonb(e) AS row_value " + source)
        # No other run, orphan row, omitted table, duplicate, or unexpected column
        # is ignored. JSON conversion normalizes numeric and timestamp input forms.
        conditions.append(
            "NOT EXISTS ((SELECT pg_catalog.to_jsonb(a) AS row_value "
            f"FROM v1_shadow.{table} a EXCEPT ALL SELECT row_value FROM expected_{table}) "
            f"UNION ALL (SELECT row_value FROM expected_{table} EXCEPT ALL "
            f"SELECT pg_catalog.to_jsonb(a) FROM v1_shadow.{table} a))"
        )
    return "WITH " + ",\n".join(ctes) + "\n" + _assert("\nAND ".join(conditions), "state_matches")


def render_prepare(plan: Mapping[str, Any]) -> str:
    """Create only this immutable run, or validate its existing exact receipt."""
    _validate(plan)
    sql = _begin()
    sql += _assert(
        "NOT EXISTS (SELECT 1 FROM v1_shadow.runs WHERE id <> "
        + _literal(plan["run"]["id"])
        + "::uuid)",
        "single_capture",
    )
    sql += (
        "INSERT INTO v1_shadow.runs SELECT * FROM pg_catalog.jsonb_populate_record("
        "NULL::v1_shadow.runs, "
        + _json_literal(plan["run"])
        + ") ON CONFLICT (id) DO NOTHING;\n"
    )
    sql += _assert_state(plan)
    return sql + "COMMIT;\n"


def render_batch(
    plan: Mapping[str, Any], ordinal: int, fail_after_table: str | None = None
) -> str:
    """Atomically import one batch and its journal receipt; exact replay is safe."""
    _validate(plan)
    if type(ordinal) is not int or not 1 <= ordinal <= len(plan["batches"]):
        raise ValueError("Unknown batch ordinal")
    batch = plan["batches"][ordinal - 1]
    if fail_after_table is not None and fail_after_table not in batch["tables"]:
        raise ValueError("Failure injection must name a table in this batch")
    sql = _begin()
    sql += (
        "CREATE TEMP TABLE phase11_expected_plan (payload jsonb NOT NULL) ON COMMIT DROP;\n"
        "INSERT INTO pg_temp.phase11_expected_plan (payload) VALUES ("
        + _json_literal(plan)
        + ");\n"
    )
    sql += _assert_state(plan, staged=True)
    sql += _assert(
        f"(SELECT count(*) FROM v1_shadow.batches WHERE ordinal < {ordinal}) = {ordinal - 1}",
        "batch_predecessors",
    )
    for table in TABLE_ORDER:
        if table not in batch["tables"]:
            continue
        sql += (
            f"INSERT INTO v1_shadow.{table} SELECT * FROM pg_catalog.jsonb_populate_recordset("
            f"NULL::v1_shadow.{table}, (SELECT payload -> 'batches' -> {ordinal - 1} "
            f"-> 'tables' -> '{table}' FROM pg_temp.phase11_expected_plan)) "
            "ON CONFLICT (run_id, id) DO NOTHING;\n"
        )
        if table == fail_after_table:
            sql += "SELECT 1 / 0 AS phase11_forced_failure;\n"
    sql += (
        "INSERT INTO v1_shadow.batches (run_id, ordinal, batch_hash, completed_at, row_counts) VALUES ("
        + _literal(plan["run"]["id"])
        + f"::uuid, {ordinal}, "
        + _literal(batch["hash"])
        + ", pg_catalog.clock_timestamp(), "
        + _json_literal({table: len(rows) for table, rows in batch["tables"].items()})
        + ") ON CONFLICT (run_id, ordinal) DO NOTHING;\n"
    )
    sql += _assert_state(plan, staged=True)
    return sql + "COMMIT;\n"


def render_verify(plan: Mapping[str, Any], finalize: bool = False) -> str:
    """Read-only reconciliation, or final certification of every exact row."""
    _validate(plan)
    sql = _begin() + _assert_state(plan, complete=finalize)
    if finalize:
        sql += (
            "UPDATE v1_shadow.runs SET status = 'reconciled' WHERE id = "
            + _literal(plan["run"]["id"])
            + "::uuid AND status = 'prepared';\n"
        )
    return sql + "COMMIT;\n"
