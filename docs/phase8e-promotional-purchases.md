# Phase 8E: Atomic Promotional Purchase

Date: 2026-09-22. Base: `f2d2100`, main, origin/main 0/0.
DONE local + staging: 255 tests, PostgreSQL 17.11 migrations/bootstrap, seven
concurrent scenarios, forced rollback. Remote 022: 27 checks and cleanup PASS;
8D revalidation after 022: 29 checks and cleanup PASS. Implementation: `498b6b8`.
User guide `docs/pokeapp-guia-completa-pestanas-y-producto.md` is untouched/untracked.

## Legacy Evidence And Contract

- `app/tienda/discounts.py`: generation defaults normal stock 2, mega stock 1;
  activation is the stored announcement timestamp + 24 hours, not request time.
- `app/tienda/catalog_render.py`, `sections.py`, `app/storage_shop.py`
  (`purchase_shop_discount`): current jornada scopes offers, previous purchase
  carrying discount identity proves claim regardless of later purchase status.
  An unclaimed active offer consumes shared stock; prior claim allows subsequent
  normal-price purchase. Exhausted/expired require separate base confirmation.
- `app/domain/services/shop.py`: prices are positive (minimum 1), mega and normal
  price generation already exists. 8E does not regenerate or recalculate offers.
- Migration 004 already stores promotion season, matchday, item, type, status,
  base/effective prices, stock_total/stock_used, announced_at/activates_at/ends_at/
  exhausted_at. Purchase already has promotion_id and JSON historical metadata.
- Legacy/domain event is PURCHASE_COMPLETED. Discord delivery is outside the
  transaction and remains entirely out of scope here.

8E consumes persisted stock_total, not a hardcoded stock by kind. Normal/mega
defaults belong to generation. `activates_at` is the authoritative opening time:
future activation rejects even active rows; pending without an activation fails
closed; elapsed pending becomes active on successful claim. Active with NULL
activation preserves the existing immediate-active representation. `ends_at <=
clock_timestamp()` or ended/cancelled means expired. Exhausted status or a full
stock counter rejects. Time is sampled AFTER acquiring the promotion lock.

Pending comodin can still be bought at base price via 8D, never via 8E. No promo
failure silently falls back to base. Stored effective_price must be an integer
greater than zero and no greater than stored base_price. Later catalog price
changes do not rewrite the promotion price or historical purchase.

## API

`POST /v1/seasons/{season_id}/shop/promotions/{promotion_id}/purchases`

- Verified Bearer token, globally enabled principal; trainer derives from auth.
- Required `Idempotency-Key`: 1-128 printable ASCII characters without whitespace.
- Required strict empty JSON object `{}`. No item_id: promotion already determines
  the item. Price, quantity, trainer, stock, day, balance and status are forbidden.
- HTTP 200 typed receipt extends NormalPurchaseReceipt: id, season_id, trainer_id,
  season_player_id, item_id, quantity=1, unit_price, total_price, status=pending,
  purchased_at, balance_after, ledger_id, event_id, matchday_id, matchday_number;
  adds promotion_id, base_price, promotion_kind and remaining_stock.
- remaining_stock and balance_after are HISTORICAL post-purchase snapshots, not
  a live availability/balance query. A retry returns exactly the original receipt.

Code path: existing purchases router -> promotional application use case ->
PromotionalPurchaseRepository protocol -> shared Supabase purchase adapter ->
`api_create_promotional_purchase`. Reuses auth/guard, header validation, error
mapping, response projection and NormalPurchaseReceipt, rather than a parallel
authentication or wallet implementation. One backend RPC; no browser table writes.

## Eligibility And Errors

New claim requires enabled trainer, active season membership, active season,
valid explicit seasons.current_matchday_id (020 resolver, no heuristic), and no
Store Ban using exactly api_is_store_banned. Promotion must belong to this season
and day, reference an enabled purchasable item, be open/not ended, have stock and
valid price, and have no previous purchase for that trainer. Balance is SUM of
coin_transactions.amount for this season/trainer under the existing wallet lock.

Error envelope remains `detail.code` plus safe generic message. Auth 401;
disabled/inactive participant/STORE_BANNED 403; missing season/promotion (including
foreign-season promotion) 404; malformed UUID/body/header 422. Business 409 includes
PROMOTION_NOT_CURRENT, PROMOTION_PENDING, PROMOTION_EXPIRED, PROMOTION_EXHAUSTED,
PROMOTION_ALREADY_CLAIMED, PROMOTION_PRICE_INVALID, INSUFFICIENT_FUNDS,
IDEMPOTENCY_CONFLICT, ITEM_UNAVAILABLE and current-matchday/season conflicts.
PROMOTION_CHANGED rejects an item identity change during the lock acquisition.
Unknown/malformed backend responses become PURCHASE_UNAVAILABLE 503 without SQL,
PostgREST details, tokens or credentials.

## Transaction And Locks

Shared order with 8D: trainer SHARE -> season SHARE -> season_player wallet UPDATE
-> current matchday SHARE -> item SHARE -> promotion UPDATE (8D uses SHARE for
promotion inspection). An unlocked promotion lookup discovers item identity only;
all facts are re-read under the stock lock and the item relationship rechecked.
No code path acquires stock then wallet. Locks persist until commit/rollback.

After eligibility/funds, one SQL transaction increments stock_used, sets exhausted
and exhausted_at on the last unit, inserts quantity=1/pending purchase, linked
negative `purchase` ledger transaction and public PURCHASE_COMPLETED. Payload has
item, price actually paid, quantity, purchase_id, promotion_id, base_price and
promotion_kind; context carries authoritative matchday UUID/number. Any failure
rolls back the counter, purchase, ledger and event together. No save, redemption,
flag, parser or webhook work occurs.

Partial unique index `uq_purchases_promotion_trainer` on (promotion_id, trainer_id)
WHERE promotion_id IS NOT NULL enforces one historical claim DB-side, without
limiting normal repeat purchases. Shared stock lock serializes different trainers;
wallet lock serializes the same trainer across normal and promotional purchases.
Insufficient funds never consumes stock. Future wallet mutations must reuse this
same lock discipline; do not introduce a second economic write path.

## Idempotency And 8D Compatibility

Reuse 021 persisted columns/index: scope season + trainer + key. Under wallet lock,
replay lookup precedes promotion availability/previous-claim checks. Same promo
returns stored receipt even after stock/price/current day changes; changed promo
or normal-vs-promotional operation is a 409. Disabled/inactive principals remain
denied on replay, as in 8D. Different key, same promo/trainer is already claimed.

021 originally knew only normal purchases: same item/key could otherwise match
a new promotional purchase. 022 preserves its exact SQL body by renaming once
to api_create_normal_purchase_8d. Original RPC name becomes a small wrapper that
rejects a promotional receipt before returning it. This is cross-operation replay
isolation, not a normal purchase redesign. Existing eligibility, normal response
and fallback semantics remain covered by all prior 8D tests. Both SQL functions
and the new RPC retain backend-only EXECUTE, SECURITY INVOKER, empty search_path.

## Migration And Security

- 022 only: partial unique claim index, promotional RPC, normal replay wrapper,
  grants. No changes to migrations 001-021, tables, views or existing RLS policies.
- stock_used is server-managed: authenticated INSERT/UPDATE column grants exclude
  that counter, including browser admin. Other columns retain pre-existing RLS
  restrictions; no promotion creation/edit endpoint is introduced.
- PUBLIC/anon/authenticated cannot EXECUTE the three purchase functions; service
  role can. Existing browser purchase/ledger write restrictions remain intact.
- Bootstrap is generated from ordered 001-022 and ONLY for an empty V2 database.
  Existing staging receives only 022, never bootstrap/reset.

## Validation And Reproduction

All commands run from repository root. Python is the isolated `.venv-api` runtime.
Unit runner redirects legacy SQLite tests to a disposable DB, never real V1.

```powershell
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py
.\.venv-api\Scripts\python.exe -m compileall -q -x '[\\/](\.venv[^\\/]*|\.git|node_modules)[\\/]' .
.\.venv-api\Scripts\python.exe tools/generate_supabase_v2_bootstrap.py
git diff --check
```

255 tests PASS (239 baseline + 16 promotional API/adapter/domain tests); auth,
Team Lock, normal purchase, shop, penalties, repository and schema suites included.
Bootstrap equality is asserted by schema tests. Warnings: Streamlit bare-runtime
MemoryCacheStorageManager and Starlette httpx deprecation; not suppressed/failures.

Local real PostgreSQL command (temporary cluster only):

```powershell
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_schema.py --psql "$env:TEMP\pokeapp_pg17_phase8c_20260922\portable\pgsql\bin\psql.exe" --host 127.0.0.1 --port 55439 --database pokeapp_v2_validation_phase8c --allow-destructive-reset
# Repeat with --build-source bootstrap.
```

Both modes PASS. Safety guard remains loopback + pokeapp_v2_validation* DB.
SQL fixtures cover E03-E21 eligibility/receipt, E22-E32 idempotency/claims/stock,
E35-E42 time/funds/forced rollback, roles/private projections, no effects, and
cross-operation keys. API tests cover E01/E02/E03, error mappings, strict inputs,
receipt validation/secrets. E28 redundant item conflict is inapplicable because
item_id is forbidden. Existing 8D checks cover E52; no rules reimplemented there.
Seven six-connection scenarios cover stock2, mega1, same trainer, same key, wallet,
mixed-normal and combined wallet/stock (E33/E34/E43/E44). Failure triggers for
purchase/ledger/event/stock exist only in rolled-back LOCAL test transactions.

Remote opt-in (only approved uwleqeuzsveqlugugzba V2 staging; refuses an existing
active season; no real trainer used):

```powershell
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_promotional_purchases.py --env-file .env.supabase-v2-rls.local --allow-staging-writes
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_purchases.py --env-file .env.supabase-v2-rls.local --allow-staging-writes --suite purchase
```

New validator covers RE01-RE22 plus RE23 normal-after-claim, RE24 mixed normal/promo
wallet race, RE25 same-trainer and same-key races, RE26 combined stock/wallet,
RE27 no redemption/save effects. Real Auth JWTs + local in-process FastAPI use real
PostgREST/SQL; this is not a deployed API or load test. Per-run fixture prefix is
phase8e_validation_UUID; cleanup removes only recorded fixture IDs/owned season
rows and temporary Auth users, then verifies removal. No remote failure triggers.

## Limits And Next

No runtime cutover, V1 changes, dual-write, frontend/React/Cloudflare/Companion,
promotion scheduling/admin UI, Discord or redemption implementation. Service
credentials remain server-only and outside Git. Runtime remains legacy Streamlit.
Next: Phase 8F redemption/effect boundary design and scoped
implementation, NOT part of this task.

## Real Staging Evidence

Applied only 022 by MCP to `https://uwleqeuzsveqlugugzba.supabase.co` on 2026-09-22;
remote migration version `20260922174842`, name `022_promotional_purchase_api`.
Before apply: no active season or duplicate promotion/trainer claim groups.
Implementation/local-validation commit `498b6b8` was pushed before remote changes.

- 8E run `phase8e_validation_08f577dd23d6452ba0871c9b70fbf4d7`:
  `RESULT ok checks=27`, `CLEANUP PASS`.
- 8D rerun `phase8d_validation_c1e993b6594a4672b8de48ff328fed52`:
  `RESULT ok checks=29`, `CLEANUP PASS`.
- RPC prosrc MD5 matches local: promotional
  `fde0f5a7019b33b2f144113d7219f31f`; normal wrapper
  `2a80fdc553c7ccb18c3b8406a114cb80`.
- Original 8D core MD5 before/after rename identical:
  `af6c9b572b498cbf5d60d1096d4231b1`.
- 32 public tables / 32 RLS tables / 37 views unchanged. New RPC/wrapper are
  SECURITY INVOKER, fixed empty search_path, anon/authenticated EXECUTE=false,
  service EXECUTE=true; authenticated stock_used INSERT/UPDATE=false.
- Partial unique claim index independently inspected. HTTP assertions verified
  browser-admin as well as owner denials, private owner/admin reads, other-trainer
  isolation, public balance/event accuracy and anon denial.
- Cleanup was also queried independently via MCP: zero run-prefixed users,
  trainers, seasons/items and zero residual promotion/purchase/ledger/event rows.
  No V1 changes, remote bootstrap/reset, injected remote failure triggers or API
  deployment occurred.

Full closure report: [phase8e-completion-report.md](phase8e-completion-report.md).
