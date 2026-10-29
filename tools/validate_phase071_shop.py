"""071 shop proof on a restored production backup (disposable cluster only).

Reproduces the owner's refusal before 071 (Anto buys «Robar Pokémon» with the
base price confirmed in the active preseason season: 409
current_matchday_required), applies 071, then buys every enabled catalog item
as the same trainer inside rolled-back transactions: the balance drops once by
the price, a pending purchase, its ledger row and its audit event appear, a
retry with the same key returns the same receipt without charging again, a
second key is a second purchase, and buying past the balance is refused with
insufficient_funds. Nothing is committed: the copy keeps production's rows.

Run: python -m tools.validate_phase071_shop --pg-bin <dir> --dump <archive> --dir <private dir> [--output <json>]
"""

import argparse
import json
from pathlib import Path

from tools.phase30_release_audit import MIGRATIONS, SupabaseLikePG

MIGRATION = next(m for m in MIGRATIONS if m.name.startswith("071_"))


def as_api(pg, sql):
    """One rolled-back transaction as the API's own role."""
    run = pg.sql(f"begin; set local role service_role; {sql}; rollback;", "postgres", ok=False)
    error = next((x for x in run.err.splitlines() if "ERROR:" in x), "")
    return run.out.strip(), error.split("ERROR:", 1)[-1].strip()


def restore(pg, dump):
    pg.start(storage_mock=False)
    pg.sql(
        "create role pokeapp_item_verifier nologin nosuperuser nocreatedb nocreaterole noinherit nobypassrls;",
        "supabase_admin",
    )
    pg.sql("drop schema public cascade;", "supabase_admin")
    pg.run(
        "pg_restore",
        ["-h", "127.0.0.1", "-p", str(pg.port), "-U", "supabase_admin", "-d", pg.database,
         "--exit-on-error", str(dump)],
    )  # fmt: skip
    pg.sql("grant usage on schema public to public;", "supabase_admin")


def validate(pg):
    report = {"checks": []}

    def check(label, condition, detail=None):
        report["checks"].append({"check": label, "pass": bool(condition), "detail": detail})
        print("PASS" if condition else "FAIL", label, detail if not condition else "", flush=True)

    season, current = pg.lines(
        "select id||'|'||coalesce(current_matchday_id::text,'none') from public.seasons where status='active'",
        "supabase_admin",
    )[0].split("|")
    trainer = pg.lines(
        f"select p.trainer_id from public.season_players p join public.trainers t on t.id=p.trainer_id"
        f" where p.season_id='{season}' and lower(t.display_name)='anto'",
        "supabase_admin",
    )[0]
    balance = int(pg.lines(
        f"select coalesce(sum(amount),0) from public.coin_transactions where season_id='{season}' and trainer_id='{trainer}'",
        "supabase_admin",
    )[0])  # fmt: skip
    items = [
        line.split("|")
        for line in pg.lines(
            "select id||'|'||code||'|'||base_price from public.shop_items"
            " where enabled and base_price>0 and acquisition_mode='purchasable' order by base_price,code",
            "supabase_admin",
        )
    ]
    robar = next(i for i in items if i[1] == "robar_pokemon")
    report.update(season=season, current_matchday=current, balance=balance, catalog=len(items))
    check("the active season is in its preseason (no current matchday)", current == "none", current)

    def buy(item, key, confirm=True):
        return f"select public.api_create_normal_purchase('{season}','{trainer}','{item}','{key}',{str(confirm).lower()})"

    out, error = as_api(pg, buy(robar[0], "owner-capture"))
    check("before 071: the owner's purchase is refused exactly as captured (409 current_matchday_required)",
          error == "current_matchday_required" and not out, error)  # fmt: skip

    run = pg.sql(MIGRATION.read_text(encoding="utf-8"), "postgres", ok=False)
    check(f"{MIGRATION.name} applies as non-superuser postgres", not run.returncode, run.err[-400:])

    # The owner's purchase, now: one charge of the confirmed price, receipt,
    # ledger and audit event, all in one transaction (rolled back here).
    out, error = as_api(pg, f"""
      create temp table r as {buy(robar[0], 'owner-capture')} as receipt;
      select (receipt->>'balance_after')::int||'|'||(receipt->>'unit_price')
        ||'|'||(select count(*) from public.purchases where id=(receipt->>'id')::uuid and status='pending')
        ||'|'||(select count(*) from public.coin_transactions where reference_id=(receipt->>'id')::uuid and amount=-(receipt->>'unit_price')::int)
        ||'|'||(select count(*) from public.activity_events where id=(receipt->>'event_id')::uuid and type='PURCHASE_COMPLETED')
        ||'|'||coalesce(receipt->>'matchday_id','null')
        ||'|'||(select sum(amount) from public.coin_transactions where season_id='{season}' and trainer_id='{trainer}')
      from r""")  # fmt: skip
    parts = out.split("|") if out else []
    check(f"after 071: «Robar Pokémon» bought once, {balance} -> {balance - int(robar[2])} PK₽, ledger and event recorded",
          not error and parts[:6] == [str(balance - int(robar[2])), robar[2], "1", "1", "1", "null"]
          and parts[6] == str(balance - int(robar[2])), out or error)  # fmt: skip

    # Retry and double click: the same key is the same purchase, charged once.
    out, error = as_api(pg, f"""
      create temp table a as {buy(robar[0], 'double-click')} as receipt;
      create temp table b as {buy(robar[0], 'double-click')} as receipt;
      select (a.receipt->>'id'=b.receipt->>'id')::text||'|'||(select count(*) from public.purchases
        where season_id='{season}' and trainer_id='{trainer}' and idempotency_key='double-click')
        ||'|'||(select sum(amount) from public.coin_transactions where season_id='{season}' and trainer_id='{trainer}')
      from a,b""")  # fmt: skip
    check("a retry or double click with the same key returns the same receipt and charges once",
          out == f"true|1|{balance - int(robar[2])}", out or error)  # fmt: skip
    out, error = as_api(pg, f"{buy(robar[0], 'double-click')}; {buy(items[0][0], 'double-click')}")
    check("the same key for another item is refused as idempotency_conflict", error == "idempotency_conflict", error)

    # Every enabled catalog item the balance covers can be bought.
    bought, refused = [], []
    for item_id, code, price in items:
        out, error = as_api(pg, f"select ({buy(item_id, 'catalog-' + code)})->>'balance_after'")
        if int(price) <= balance:
            (bought if out == str(balance - int(price)) else refused).append(code)
        else:
            (bought if error == "insufficient_funds" else refused).append(code + "(funds)")
    check(f"every enabled item is purchasable within the balance ({len(items)} items)", not refused,
          {"ok": bought, "refused": refused})  # fmt: skip

    # Past the balance: refused with the real reason, nothing charged.
    affordable = [i for i in items if int(i[2]) <= balance]
    statements = "; ".join(buy(i[0], f"spend-{n}") for n, i in enumerate(affordable * (balance // max(1, int(affordable[0][2])) + 1)))
    out, error = as_api(pg, statements)
    check("buying past the balance stops at insufficient_funds (never negative)", error == "insufficient_funds", error)
    for code in ("blindar_pokemon", "revivir_pokemon"):
        item = next((i for i in items if i[1] == code), None)
        if item and int(item[2]) <= balance:
            out, error = as_api(pg, f"select ({buy(item[0], code)})->>'status'")
            check(f"«{code}» is purchasable", out == "pending", out or error)
    left = pg.lines(
        f"select count(*) from public.purchases where season_id='{season}' and trainer_id='{trainer}'"
        " and idempotency_key in ('owner-capture','double-click')",
        "supabase_admin",
    )
    check("nothing committed: the copy keeps production's purchases", left == ["0"], left)
    report["result"] = "PASS" if all(c["pass"] for c in report["checks"]) else "FAIL"
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--dump", type=Path, required=True)
    parser.add_argument("--dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55560)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    pg = SupabaseLikePG(args.pg_bin, args.port, args.dir)
    try:
        restore(pg, args.dump)
        report = validate(pg)
    finally:
        pg.stop(remove=True)
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    raise SystemExit(0 if report["result"] == "PASS" else 1)


if __name__ == "__main__":
    main()
