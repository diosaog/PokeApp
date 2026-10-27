"""Phase 28 incident center gates on a disposable loopback PostgreSQL.

Bootstraps migrations 001-062 on an empty cluster and exercises purchase
cancellation/refund and coin corrections with synthetic data only: authority,
idempotency, concurrency, single reversal, atomic failure, append-only audit
and grants. No remote configuration is loaded.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_accounts_local import LocalPG

HASH = "c" * 64


class Fixture:
    def __init__(self, pg):
        self.pg = pg
        self.admin, self.player, self.rival = (str(uuid4()) for _ in range(3))
        self.season = str(uuid4())
        pg.sql(f"""
        insert into trainers(id,display_name,slug,auth_user_id,is_admin) values
          ('{self.admin}','Admin','admin-28',gen_random_uuid(),true),
          ('{self.player}','Player','player-28',gen_random_uuid(),false),
          ('{self.rival}','Rival','rival-28',gen_random_uuid(),false);
        insert into seasons(id,name,created_by_trainer_id,status,started_at)
          values('{self.season}','Phase 28','{self.admin}','active',now());
        insert into season_players(season_id,trainer_id) values
          ('{self.season}','{self.player}'),('{self.season}','{self.rival}');
        insert into coin_transactions(season_id,trainer_id,season_player_id,amount,
          transaction_type,reference_type)
        select season_id,trainer_id,id,100,'admin_adjustment','fixture'
          from season_players where season_id='{self.season}';
        """)

    def scalar(self, query):
        return self.pg.sql(query).stdout.strip()

    def purchase(self, status="pending", trainer=None):
        """A paid purchase and its ledger debit, as the purchase API leaves it."""
        trainer = trainer or self.player
        pid = str(uuid4())
        self.pg.sql(f"""
        insert into purchases(id,season_id,trainer_id,season_player_id,shop_item_id,
          unit_price,status,idempotency_key)
        select '{pid}',sp.season_id,sp.trainer_id,sp.id,i.id,i.base_price,'{status}','{pid}'
          from season_players sp, shop_items i
          where sp.season_id='{self.season}' and sp.trainer_id='{trainer}'
            and i.acquisition_mode='purchasable' and i.base_price>0
          order by i.code limit 1;
        insert into coin_transactions(season_id,trainer_id,season_player_id,amount,
          transaction_type,reference_type,reference_id)
        select season_id,trainer_id,season_player_id,-total_price,'purchase','purchase',id
          from purchases where id='{pid}';
        """)
        return pid

    def resolve(
        self,
        pid,
        kind="purchase_cancel",
        op=None,
        digest=HASH,
        actor=None,
        reason="Compra duplicada por error",
        ok=True,
    ):
        op = op or str(uuid4())
        result = self.pg.sql(
            f"select admin_purchase_resolve('{actor or self.admin}','{self.season}',"
            f"'{pid}','{kind}','{op}','{digest}',$r${reason}$r$);",
            ok=ok,
        )
        return (json.loads(result.stdout) if ok else result), op

    def adjust(self, amount, op=None, actor=None, trainer=None, ok=True):
        op = op or str(uuid4())
        result = self.pg.sql(
            f"select admin_coin_adjust('{actor or self.admin}','{self.season}',"
            f"'{trainer or self.player}',{amount},'{op}','{HASH}','Corrección de prueba');",
            ok=ok,
        )
        return json.loads(result.stdout) if ok else result

    def balance(self, trainer=None):
        return int(
            self.scalar(
                f"select coalesce(sum(amount),0) from coin_transactions where "
                f"season_id='{self.season}' and trainer_id='{trainer or self.player}';"
            )
        )


def refused(result, code):
    assert result.returncode and code in result.stderr, result.stderr[-600:]


def gates(pg):
    f = Fixture(pg)
    checks = []
    start = f.balance()
    price = None

    # 1. Cancel a pending purchase: status forward, coins back once, audited.
    pid = f.purchase()
    price = int(f.scalar(f"select total_price from purchases where id='{pid}';"))
    assert f.balance() == start - price
    receipt, op = f.resolve(pid)
    assert receipt["status"] == "cancelled" and receipt["amount"] == price
    assert receipt["balance_after"] == start and f.balance() == start
    assert f.scalar(f"select status from purchases where id='{pid}';") == "cancelled"
    assert (
        f.scalar(
            f"select count(*) from coin_transactions where reference_id='{pid}' "
            f"and reference_type='purchase_cancellation' and transaction_type='compensation';"
        )
        == "1"
    )
    checks.append("cancel returns the exact price once and keeps the purchase row")

    # 2. Retry with the same operation: same receipt, no second effect.
    again, _ = f.resolve(pid, op=op)
    assert again["replayed"] is True and again["ledger_id"] == receipt["ledger_id"]
    assert f.balance() == start
    refused(f.resolve(pid, op=op, digest="d" * 64, ok=False)[0], "idempotency_conflict")
    refused(f.resolve(pid, ok=False)[0], "purchase_not_cancellable")
    refused(
        f.resolve(pid, kind="purchase_refund", ok=False)[0], "purchase_not_refundable"
    )
    checks.append("same operation replays; other data conflicts; no double return")

    # 3. Six administrators race on one purchase: exactly one reversal.
    race = f.purchase()
    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(lambda _: f.resolve(race, ok=False)[0], range(6)))
    assert sum(r.returncode == 0 for r in results) == 1, [r.stderr for r in results]
    assert (
        f.scalar(
            f"select count(*) from coin_transactions where reference_id='{race}' and amount>0;"
        )
        == "1"
    )
    assert f.balance() == start
    checks.append("concurrent cancellations: one effect, others refused")

    # 4. Refund of a used purchase; a used purchase cannot be "cancelled".
    used = f.purchase(status="used")
    refused(f.resolve(used, ok=False)[0], "purchase_not_cancellable")
    refund, _ = f.resolve(used, kind="purchase_refund")
    assert refund["status"] == "refunded" and f.balance() == start
    checks.append("refund only for used purchases, history kept")

    # 5. A purchase tied to a save operation is never reversed here.
    linked = f.purchase()
    pg.sql(f"""
    set session_replication_role = replica;
    insert into item_use_authorizations(operation_id,idempotency_key,purchase_id,season_id,
      trainer_id,target_pokemon_entity_id,save_file_id,save_sha256,identity_revision_id,
      effect_code)
    values('{uuid4()}','{uuid4()}','{linked}','{f.season}','{f.player}',gen_random_uuid(),
      gen_random_uuid(),'{"0" * 64}',gen_random_uuid(),'steal');
    set session_replication_role = origin;
    """)
    refused(f.resolve(linked, ok=False)[0], "purchase_linked_to_save_operation")
    assert f.scalar(f"select status from purchases where id='{linked}';") == "pending"
    checks.append("robbery/revive purchases are not reversed by a status change")

    # 6. A failure half way leaves nothing behind (single transaction).
    torn = f.purchase()
    pg.sql(f"""
    insert into coin_transactions(season_id,trainer_id,season_player_id,amount,
      transaction_type,reference_type,reference_id)
    select season_id,trainer_id,season_player_id,1,'compensation','purchase_refund',id
      from purchases where id='{torn}';
    """)
    before = f.balance()
    refused(f.resolve(torn, ok=False)[0], "coin_purchase_reversal_once")
    assert f.scalar(f"select status from purchases where id='{torn}';") == "pending"
    assert f.balance() == before
    assert (
        f.scalar(
            f"select count(*) from admin_incident_commands where purchase_id='{torn}';"
        )
        == "0"
    )
    checks.append("mid-operation failure rolls back status, coins and audit")

    # 7. Coin corrections: exact, never below zero, authority checked.
    corrected = f.adjust(25)
    assert corrected["amount"] == 25 and f.balance() == before + 25
    refused(f.adjust(-(before + 26), ok=False), "insufficient_funds")
    refused(f.adjust(0, ok=False), "invalid_incident_request")
    refused(f.adjust(5, actor=f.player, ok=False), "admin_required")
    pg.sql(f"update trainers set globally_enabled=false where id='{f.admin}';")
    refused(f.adjust(5, ok=False), "admin_required")
    pg.sql(f"update trainers set globally_enabled=true where id='{f.admin}';")
    refused(
        f.resolve(f.purchase(), reason="no", ok=False)[0], "incident_reason_required"
    )
    checks.append("corrections are bounded, admin only, reason required")

    # 8. The read shows what can be done to each purchase and the history.
    view = json.loads(
        f.scalar(f"select admin_incident_read('{f.admin}','{f.season}');")
    )
    rows = {p["id"]: p for p in view["purchases"]}
    assert rows[pid]["cancellable"] is False and rows[pid]["status"] == "cancelled"
    assert (
        rows[linked]["linked_operation"] is True
        and rows[linked]["cancellable"] is False
    )
    assert rows[torn]["cancellable"] is True
    assert {h["kind"] for h in view["history"]} == {
        "purchase_cancel",
        "purchase_refund",
        "coin_adjustment",
    }
    assert any(w["trainer_id"] == f.player for w in view["wallets"])
    refused(
        pg.sql(f"select admin_incident_read('{f.player}','{f.season}');", ok=False),
        "admin_required",
    )
    checks.append("incident read: wallets, purchases with allowed actions, history")

    # 9. Archived seasons are frozen.
    pending = f.purchase()
    pg.sql(
        f"update seasons set status='archived',finished_at=now(),archived_at=now() where id='{f.season}';"
    )
    refused(f.resolve(pending, ok=False)[0], "historical_artifact_immutable")
    refused(f.adjust(5, ok=False), "historical_artifact_immutable")
    pg.sql(f"update seasons set status='active' where id='{f.season}';")
    checks.append("archived seasons cannot be corrected")

    # 10. Append-only audit and closed grants.
    refused(
        pg.sql("update admin_incident_commands set reason='x';", ok=False),
        "admin_incident_immutable",
    )
    refused(
        pg.sql("delete from admin_incident_commands;", ok=False),
        "admin_incident_immutable",
    )
    for role in ("anon", "authenticated"):
        for query in (
            f"select admin_coin_adjust('{f.admin}','{f.season}','{f.player}',5,'{uuid4()}','{HASH}','Intento externo');",
            f"select admin_incident_read('{f.admin}','{f.season}');",
            "select * from admin_incident_commands;",
        ):
            denied = pg.sql(f"set role {role};" + query, ok=False)
            assert denied.returncode and "permission denied" in denied.stderr, (
                denied.stderr
            )
    denied = pg.sql(
        "set role service_role; select * from admin_incident_commands;", ok=False
    )
    assert denied.returncode and "permission denied" in denied.stderr
    allowed = pg.sql(
        f"set role service_role; select admin_incident_read('{f.admin}','{f.season}') is not null;"
    )
    assert allowed.stdout.strip().endswith("t")
    checks.append("append-only audit; only the backend role can run the commands")
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55482)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    pg = LocalPG(args.bin, args.port)
    try:
        pg.start()
        checks = gates(pg)
        version = pg.sql("show server_version;", "postgres").stdout.strip()
    finally:
        # A failed stop must not hide the gate failure that got us here.
        with contextlib.suppress(Exception):
            pg.stop()
    for check in checks:
        print("PASS", check)
    if args.evidence:
        args.evidence.write_text(
            json.dumps(
                {
                    "postgres": version,
                    "migrations": "001-062 bootstrap",
                    "checks": checks,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
