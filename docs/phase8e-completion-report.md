# PokeApp Phase 8E Completion Report

=== POKEAPP PHASE 8E ===

## Result

DONE. Local + real Supabase V2 staging validated on 2026-09-22.

## Start And End

START: main, HEAD `f2d2100`, origin/main 0/0; only the user-owned untracked guide.
END implementation: `498b6b8 api: add atomic promotional purchase and stock validation`.
Closure is the subsequent documentation-only commit
`docs: close phase 8e staging validation` (exact final hash in delivered Git report).
No force push or amend; only the user-owned guide remains untracked.

## Legacy Promotion Contract

Normal generation defaults to stock 2; mega to stock 1. Claim consumes persisted
stock_total/stock_used. One purchase with promotion_id is one historical claim per
trainer, independent of later purchase status. Ordinary repeat purchases remain
unlimited by this index. Legacy +24h scheduling is represented by activates_at;
no request-time timestamp invented. Pending comodin only permits the separate
normal-price route. Pending non-comodin rejects. Expiration uses ends_at and
ended/cancelled status. Positive effective_price is server-owned; no free offers.
PURCHASE_COMPLETED remains the event type. Price, base price, day, balance_after,
ledger/event IDs, promotion kind and remaining stock snapshots persist for replay.

Evidence: discounts.py, sections.py, catalog_render.py, storage_shop.py,
domain/services/shop.py, schema 004/006/008/010-021. Full details and file paths:
[Phase 8E contract](phase8e-promotional-purchases.md).

## API

METHOD: POST.
PATH: `/v1/seasons/{season_id}/shop/promotions/{promotion_id}/purchases`.
AUTH: verified Bearer, enabled principal, self-service trainer from JWT mapping.
HEADER: required Idempotency-Key (1-128 printable ASCII, no whitespace).
BODY: strictly `{}`; item_id and economic/context fields forbidden.
RESPONSE: existing normal receipt plus promotion_id, base_price, promotion_kind,
remaining_stock; quantity=1, pending, real paid price and historical balance.
Errors: 401 auth, 403 restrictions, 404 scoped missing, 409 business state,
422 invalid request, 503 sanitized unavailable backend. No automatic base charge.

## Eligibility

Current jornada: only seasons.current_matchday_id plus matchdays.number via 020.
Store Ban: exact existing helper, inclusive windows, resolved case, no bypass.
Item: promotion-owned relationship, enabled and purchasable.
Promotion: same season/day, valid state/time/price, stock remaining.
Claim: no prior trainer/promotion claim (DB unique), except same-key replay.
Funds: authoritative SUM ledger under season_player lock.

## Concurrency

Wallet lock: season_players FOR UPDATE shared with normal purchase.
Promotion lock: shop_promotions FOR UPDATE, facts rechecked after lock wait.
Lock order: trainer/season -> wallet -> day -> item -> promotion.
Last stock: one winner only. Different trainer claims serialize on promotion.
Same trainer: one claim, other key conflicts; same key replays identical receipt.
Combined wallet/stock: no oversell, negative balance or duplicate claim/debit/event.
Local six-connection races: stock2, mega1, same-trainer, same-key, wallet,
mixed normal/promotional and combined. Remote API races use independent clients
and a barrier, against real database transactions and Auth tokens.

## Idempotency

Scope: season/trainer/key, persisted columns/index from 021.
Same request: original receipt, not current price/balance/stock.
Different promotion or normal/promotional operation: IDEMPOTENCY_CONFLICT.
Lost successful response: retry lookup before already-claimed/availability checks.
Normal core SQL preserved byte-for-byte under `_8d`; minimal original-name wrapper
only rejects cross-operation replay. 8D endpoint and product behavior not redesigned.

## Atomicity

Stock increment/exhaustion + unique claim via pending purchase + negative purchase
ledger debit + public PURCHASE_COMPLETED occur in one RPC transaction.
Local forced stock/purchase/ledger/event failures roll back every effect.
No redemption, used status, flag, save/parser effect, Companion job or Discord send.

## Migration

022: additive partial unique purchase index and atomic backend-only RPC; column
grants reserve stock_used for backend, including against browser admin writes.
Normal replay guard preserves original core. All three RPCs service_role-only,
SECURITY INVOKER and empty search_path. No browser write policy added.
001-021: unchanged. No remote bootstrap/reset. Bootstrap generated 001-022 only.

## Local Validation

- API/promotional/domain/adapter: 16 added tests PASS.
- Normal purchase, Team Lock, auth, shop, penalties, repositories/schema: PASS.
- Full suite: 255 tests PASS, zero failures/skips (baseline 239).
- `.venv-api\Scripts\python.exe tools/run_unit_tests.py`: PASS.
- `.venv-api\Scripts\python.exe -m compileall -q -x '[\\/](\.venv[^\\/]*|\.git|node_modules)[\\/]' .`: PASS.
- `.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql <portable-pg17-psql> --host 127.0.0.1 --port 55439 --database pokeapp_v2_validation_phase8c --allow-destructive-reset`: PASS.
- Same PostgreSQL command with `--build-source bootstrap`: PASS.
- Stock/wallet concurrency, forced rollback, RLS/grants and old fixtures: PASS.
- Bootstrap equality assertion against ordered migrations: PASS.
- `git diff --check`: PASS. No migrations 001-021 diff.
- Warnings retained: Streamlit bare runtime/session cache, Starlette httpx
  deprecation, Git LF/CRLF normalization notices. None is a failure.

## Staging

Target: only `uwleqeuzsveqlugugzba` (Pokeapp 2.0).
022 applied by MCP as `20260922174842_022_promotional_purchase_api`.
27/27 RE checks PASS; 29/29 8D context/purchase regression checks PASS afterward.
Both validators: CLEANUP PASS. All Auth/trainer/season/day/player/item/promotion/
purchase/ledger/event test rows removed and absence independently checked.

Remote stock2, mega1, one-claim, idempotency/conflicts, insufficient/exact funds,
pending/expired/wrong-day, Store Ban, last-stock/wallet/mixed/same-key races,
direct owner/admin write denials, private reads, public balances, anon denial and
no redemption/save effects: PASS. No intrusive remote failure triggers.

SQL definitions match local. Promotion RPC MD5 `fde0f5a7019b33b2f144113d7219f31f`;
wrapper `2a80fdc553c7ccb18c3b8406a114cb80`; preserved original 8D core
`af6c9b572b498cbf5d60d1096d4231b1`. 32 tables / 32 RLS / 37 views preserved.
API exercised locally against real staging; NOT deployed or wired into Streamlit.

## Git And Boundaries

COMMITS: `498b6b8` implementation/tests/local docs; subsequent closure docs commit.
PUSH: normal origin/main; implementation pushed before remote apply.
USER GUIDE untouched YES: SHA256
`6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.
V1/legacy runtime/parser/PKHeX/Discord/React/Companion unchanged. No dual-write,
production deployment, real-user purchase or new mechanic.

## Checkpoint

LAST COMPLETED: Phase 8E, local + staging.
NEXT: Phase 8F redemption/effect boundary. Not started.
BLOCKERS: none for 8E.
FUTURE NOTES: all new wallet mutators must reuse the same lock order; promotion
generation/admin UI, production auth/rate-limit deployment and runtime migration
remain separate scopes. Historical receipt stock is not live availability.
RECOMMENDED NEXT ACTION: design the redemption/effect boundary before implementing
save/flag mutations. Do not infer the entire API or Cloudflare migration is done.

=== END REPORT ===
