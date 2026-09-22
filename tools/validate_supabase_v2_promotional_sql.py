"""Promotion SQL fixtures; called only after the local schema validator guards."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def validate_promotional_purchase(args, execute_sql, root: Path):
    fixtures = root / "tests/sql"
    setup = "\n".join((fixtures / name).read_text(encoding="utf-8") for name in (
        "shop_context_setup.sql", "purchase_setup.sql", "promotional_purchase_setup.sql"))
    cleanup = (fixtures / "purchase_cleanup.sql").read_text(encoding="utf-8") + "\ndelete from public.trainers where id='00000000-0000-4000-8000-000000008d03';"
    checks = (fixtures / "promotional_purchase_checks.sql").read_text(encoding="utf-8")
    execute_sql(args, "begin;\n" + setup + checks + "\nrollback;")
    owner = "00000000-0000-4000-8000-000000008d01"
    promo = "00000000-0000-4000-8000-000000008d70"
    mega = "00000000-0000-4000-8000-000000008d71"
    for mode in ("stock2", "mega1", "same-trainer", "same-key", "wallet", "mixed-normal", "combined"):
        print("== Promotional concurrency: " + mode + " ==", flush=True)
        prepare = ""
        if mode in ("wallet", "combined"):
            prepare = "update public.coin_transactions set amount=8;"
        elif mode == "mixed-normal":
            prepare = "update public.coin_transactions set amount=10; update public.shop_promotions set status='pending',activates_at=now()+interval '1 hour' where promotion_type='mega';"
        execute_sql(args, "begin;\n" + setup + prepare + """
create table pokeapp_shop_test.race_results (result jsonb not null);
grant insert,select on pokeapp_shop_test.race_results to service_role;
commit;
""")
        try:
            def run(n):
                trainer = owner
                selected = promo
                if mode in ("stock2", "mega1", "combined"):
                    trainer = f"00000000-0000-4000-8000-000000008d0{n % 3 + 1}"
                if mode == "mega1" or (mode == "wallet" and n % 2):
                    selected = mega
                key = "same-key" if mode == "same-key" else f"race-{n}"
                expression = f"pokeapp_shop_test.claim('{key}','{selected}','{trainer}')"
                if mode == "mixed-normal" and n % 2:
                    expression = f"pokeapp_shop_test.buy('{key}',false,'00000000-0000-4000-8000-000000008d61')"
                execute_sql(args, f"""begin; set local role service_role; set local lock_timeout='10s';
do $$ declare receipt jsonb; begin
 receipt := {expression};
 insert into pokeapp_shop_test.race_results values(receipt);
 perform pg_sleep(0.15);
exception when sqlstate 'PT409' then
 if sqlerrm not in ('promotion_exhausted','promotion_already_claimed','insufficient_funds') then raise; end if;
 insert into pokeapp_shop_test.race_results values(jsonb_build_object('error',sqlerrm));
end; $$; commit;""")

            with ThreadPoolExecutor(max_workers=6) as pool:
                list(pool.map(run, range(6)))
            expected = 2 if mode in ("stock2", "combined") else 1
            successes = 6 if mode == "same-key" else expected
            execute_sql(args, f"""
select pokeapp_shop_test.assert_true((select count(*)={successes} from pokeapp_shop_test.race_results where result ? 'id'), 'race success count');
select pokeapp_shop_test.assert_true((select count(*)={expected} from public.purchases), 'race purchases');
select pokeapp_shop_test.assert_true((select count(*)={expected} from public.coin_transactions where transaction_type='purchase'), 'race debits');
select pokeapp_shop_test.assert_true((select count(*)={expected} from public.activity_events), 'race events');
select pokeapp_shop_test.assert_true(not exists(select 1 from public.coin_transactions group by season_id,trainer_id having sum(amount)<0), 'race nonnegative wallets');
select pokeapp_shop_test.assert_true(not exists(select 1 from public.shop_promotions s where stock_used>stock_total or stock_used<>(select count(*) from public.purchases p where p.promotion_id=s.id)), 'race stock equals claims');
select pokeapp_shop_test.assert_true(not exists(select 1 from public.purchases where promotion_id is not null group by promotion_id,trainer_id having count(*)>1), 'race claim uniqueness');
""")
        finally:
            execute_sql(args, "begin;\n" + cleanup + "\ncommit;")
