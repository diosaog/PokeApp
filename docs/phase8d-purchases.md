# Phase 8D: Legacy Purchase Audit And Blocking Contract

Date: 2026-09-22. Current status: 8D.0 DONE local, staging pending; 8D purchase pending.
The subsequent approved 8D.0 + 8D macro resolves the historical audit blocker.
The audit below is preserved as historical evidence, not the current stop state.

## Approved 8D.0 Contract

Migration 020 adds nullable `seasons.current_matchday_id`, with a composite FK
to `(matchdays.id, matchdays.season_id)`, and nullable positive inclusive
`penalties.start_matchday_number/end_matchday_number` with ordered bounds.
No backfill, no row-order heuristics, no changes to 001-019 or existing RLS.
Future season creation initializes the pointer; future close/advance moves it
transactionally. Purchase will not advance it. NULL/cancelled conflict; scheduled,
open and a temporarily closed pointer remain authoritative.

Backend-only SECURITY INVOKER helpers `api_resolve_current_matchday` and
`api_is_store_banned`, their repository port/adapter and pure domain contracts
make the rules reusable outside HTTP. V2 finished cases use status `resolved`
(not the domain/legacy spelling `finished`). Ban code is existing `store_ban`.
Case identity/accused and season are checked; a global case can support a
season-scoped penalty. Either missing boundary preserves active compatibility.
`resolved_at` alone is not expiry. The legacy-window mapper normalizes missing,
invalid/nonpositive bounds without inventing dates; reversed complete windows
are rejected as invalid typed input, not silently imported.

Local validation: 224 unit tests PASS, PostgreSQL 17.11 migrations/bootstrap
paths PASS, including same-season FK, windows, helper permissions and replaying
020. Compileall/diff checks are required before commit. Staging remains pending
until 020 is applied incrementally and its isolated validator passes.

## Historical Audit (Superseded Blocker)
Phase 8C is DONE + Supabase V2 staging validated. This document does not claim a
purchase endpoint, migration 020, purchase test suite or purchase deployment.

## Why The Macro Stopped

The authorized macro requires preserving actual shop eligibility and prohibits
inventing business rules. Legacy ordinary purchases depend on the current
competitive jornada and time-bounded store sanctions. V2 does not yet define an
authoritative equivalent of that current-jornada value or the executable
penalty-window contract. Ignoring the restrictions would allow forbidden
purchases; treating every future/historical sanction as active would deny valid
purchases. Neither is behavior-preserving.

This is not a SQL naming, locking or DTO question. It affects whether an actual
trainer is allowed to spend coins. Per the macro's product-rule stop condition,
no purchase implementation or migration 020 was created.

## Audited Surface

- `app/tienda/sections.py`, `catalog_render.py`, `catalog_data.py`, `discounts.py`,
  `money.py`, `redeem.py`: purchase confirmation, availability, pricing, promotion
  scheduling, balances and the separate use/redemption workflow.
- `app/storage_shop.py`: ordinary insert, promotional atomic claim, spending,
  inventory, purchase status, event and Discord hooks.
- `app/liga/context.py`, `app/juicios/penalties.py`: jornada and sanctions that
  the shop actually consumes.
- `app/domain/shop.py`, `app/domain/services/shop.py`,
  `app/domain/services/activity.py`, `app/domain/trials.py`,
  `app/application/shop.py`, `app/repositories/protocols.py`, legacy/memory shop
  repositories and `app/repositories/mappers.py`: existing contracts and ports.
- SQL 001/003/004/006/007/008/009 and security migrations 010-018: identity,
  lifecycle, catalog, historical price, ledger, sanctions, views and permissions.
- Existing shop-promotion, domain, repository and activity tests; full existing
  suite remains green. No new purchase behavior was tested or asserted as done.

## Actual Legacy Purchase Semantics

| Concern | Evidence and current behavior |
| --- | --- |
| Item identity | Catalog dictionaries keyed by category and visible name; purchase storage uses item text. V2 uses stable `shop_items.id` UUID plus unique `code`. |
| Quantity | One click/confirmation inserts one purchase. No UI quantity or cart. `Purchase.quantity` exists in the DTO, but legacy mapper/repository emits 1. 8D should keep one unit. |
| Catalog | Comodines, bayas, competitivos and crianza. Prices are positive integers in `catalog_data.py`. V2 seed/catalog already represents these items with `enabled`. |
| Normal price | Catalog price, except explicit base-price fallback after a promotional claim fails. The legacy low-level insert accepts a supplied price; V2 must resolve it server-side. |
| Affordability | UI checks available funds again at confirmation. Legacy ordinary insert itself is not an atomic balance/debit operation. This weakness must not be copied. |
| Trainer state | Retired/inactive trainer cannot purchase. Store sanctions independently block confirmation. V2 must also enforce globally enabled identity and active season participation as required by the macro. |
| Season lifecycle | Legacy purchase helper has no V2 lifecycle check; the macro explicitly requires a compatible active V2 season. Do not add a new lifecycle. |
| Purchase state | New purchase is `pending`; use/redemption changes it later. A purchase is not a game effect or a used item. |
| History | Purchase stores the actual paid price and timestamp. Optional legacy promotion/base-price/jornada fields are retained when available. |
| Limits | No normal-stock decrement or normal per-trainer/per-item limit found. Promotion stock and one claim per trainer/promotion are separate. |
| Event | `PURCHASE_COMPLETED`, public visibility; item, actual price, purchase ID, optional promotion/base-price/jornada. Dedupe by purchase ID, not HTTP request. |
| Discord | Normal insert calls async notification after saving. Legacy event/Discord helpers swallow failures. 8D requires atomic activity but no real Discord call. |
| Redemption | Separate workflow validates owner/item and purchase use state, then applies flags/records use. None belongs in 8D. |
| Gifts | Low-level insert also accepts zero-price rewards in other workflows. UI disallows buying price <= 0. Do not expose free/admin rewards through normal purchase. |

Relevant implementation anchors:

- `app/tienda/sections.py:84`: store lock and balance panel.
- `app/tienda/sections.py:210`: confirmation, second balance check, retirement/
  sanction checks, promotion branch and explicit base-price reconfirmation.
- `app/tienda/catalog_render.py:78`: active offer selection and pending delivery.
- `app/tienda/catalog_render.py:204`: disabled delivery/insufficient/zero-price buy.
- `app/storage_shop.py:90`: ordinary purchase insert and separate hooks.
- `app/storage_shop.py:980`: spending aggregation.
- `app/activity/events.py:297`: public PURCHASE_COMPLETED payload/dedupe.

## Coins And V2 Integrity

Legacy `money_breakdown_from_parts` derives available coins from league rewards,
four coins per badge and the claimed 12-coin league-finished bonus, minus all
purchase spending and coin sanctions, clamped to zero. An active store ban makes
the displayed available balance zero. The low-level sum includes purchases
without inventing a refund rule based on their use status.

V2's already-approved source of truth is instead
`SUM(coin_transactions.amount)` scoped to season/trainer. Rewards and monetary
penalties need ledger entries produced by their respective future operations;
the purchase endpoint must not read `.sav`, import V1 totals, subtract a penalty
twice, create rewards, or add a mutable balance.

Existing `purchases.unit_price` and generated `total_price` already freeze the
paid price. Do not add another price column. A server-owned item-name/code
snapshot could use existing purchase metadata. `coin_transactions` has signed
integer amount, type `purchase`, and reference type/UUID for linking the debit.
Zero amounts are forbidden; rejecting zero-priced normal purchases matches UI.

The schema has no purchase request-id/idempotency key or unique debit reference
for this future operation. A minimal additive 020 is appropriate after the
eligibility contract is settled. The proposed implementation remains:

- POST `/v1/seasons/{season_id}/shop/purchases`, only item UUID plus a required
  opaque idempotency key; identity/price/saldo never accepted as authority.
- Thin route -> enabled principal -> application port -> V2 adapter/backend RPC.
- Lock a stable season-player row to serialize spending for the same economy.
- One transaction: eligibility, authoritative price, ledger balance, idempotency,
  purchase, negative debit and public PURCHASE_COMPLETED.
- Same key/item returns the same receipt; another item with that key conflicts.
- Historical resulting balance must come from the transaction/recorded receipt,
  not a later independent balance read.
- Only service_role EXECUTE; no new client write policies.
- No redemption, promotional stock claim, save modification or Discord sending.

These are proposed implementation choices, NOT shipped code.

## Promotions Are A Separate Mutation, Not Irrelevant To Eligibility

Ordinary and promotional persistence paths are distinguishable:
`add_purchase` versus `purchase_shop_discount`. No need to implement stock claim
inside a normal-purchase endpoint. However, blindly ignoring promotions changes
availability and price selection at the UI boundary:

- Promotions are selected for the current jornada by
  `shop_promotions_by_item` (`app/tienda/discounts.py:246`).
- Pending promotion means a 24-hour delivery delay after announcement. Non-
  comodines are temporarily unbuyable; comodines remain available at base price.
- An active unclaimed offer selects promotional price/stock automatically.
- An already-claimed offer falls back to normal price. Exhausted/expired claim
  asks for explicit normal-price confirmation; it does not silently charge more.
- Normal offer stock is 2, mega stock 1; each trainer claims an offer once.
  Ordinary repeat purchases do not share that limit.

8D may read promotions to reject/reroute an eligible promotional purchase and
preserve delivery restrictions, while leaving its atomic stock claim for the
next slice. But that read needs the authoritative current-jornada contract.
The public promotion view currently omits pending/future offers; backend
eligibility cannot rely on that sanitized view alone.

## Missing Temporal And Sanction Contract

1. Legacy current jornada comes from session `league_tramo`, then persisted
   `settings.league_state.tramo`, default 1 (`app/liga/context.py:13`). Store
   sanctions specifically use the persisted value. V2 `seasons` has no current
   matchday pointer. `matchdays` supports scheduled/open/closed/cancelled and a
   unique season/number, but does not enforce one open matchday or define a
   rule to derive the current one. Neither a V2 repository nor a documented
   current-matchday resolver supplies it. The Team Lock API accepts an explicit
   jornada and does not establish this missing store-wide concept.
2. Legacy store bans apply only from finished cases, inclusively between
   `start_tramo` and `end_tramo`; missing windows remain active for compatibility
   (`app/juicios/penalties.py:67`, `:92`). The domain mapper converts those to
   `Penalty.start_matchday/end_matchday` (`app/repositories/mappers.py:638`). V2
   `penalties` has one optional `matchday_id`, generic payload and `resolved_at`,
   but no agreed payload/window encoding or rule for when that timestamp means
   an economic restriction ends. The SQL comment defers effects to application
   logic; no V2 implementation resolves this yet.

Concrete ambiguity: a ban for jornadas 3-4 must block during 3-4, not 2 or 5.
Choosing the highest scheduled number can activate/expire it early. Taking any
unresolved penalty forever can keep it active after 4. Looking only for one
`open` row can leave the store undefined before opening/between rounds. These
are different product outcomes, not equivalent implementations.

## Decision Needed And Recommendation

Next subphase only: **Phase 8D.0 - authoritative current-jornada and store-ban
contract**, preserving existing rules. No implementation in this audit.

Resolve together:

- What authoritative server-owned value identifies the current competitive
  jornada for purchases, including before the first opening/between rounds?
  Recommendation: explicitly model/validate this value rather than taking an
  arbitrary min/max row; align it with the future close-jornada operation.
- How does V2 encode and end store bans while retaining finished-case gating,
  inclusive jornada windows and the documented no-window compatibility case?
  Recommendation: define this mapping explicitly before choosing columns or
  payload fields. Do not interpret `resolved_at` as a revocation by guesswork.

After approval: implement 020 and the API with tests for future/current/expired
bans, pending commodity/non-commodity offers, price authority, no double-spend,
idempotency and rollback. Then run the authorized local-to-staging gates.

## Macro Result At This Stop

- START: `main`, `931db66`, origin divergence 0/0, only protected user guide.
- 8C remote: PASS; 019 applied by MCP as `20260922162954_019_team_lock_api`.
- 8C security: anon/auth RPC denied; service API works; direct writes blocked;
  owner/admin private reads and other/public projection verified.
- TL01-TL13: PASS. TL14: local real PostgreSQL PASS, remote injection not run.
- Staging cleanup: PASS, independent zero-fixture count including Auth users.
- Local full suite: 208 PASS, 0 failed/skipped; compileall/diff-check PASS.
- 8D legacy audit: completed; implementation BLOCKED on the contract above.
- 8D endpoint/RPC/020/local SQL/remote purchase/concurrency: NOT IMPLEMENTED /
  NOT RUN. No 8D fixtures or cleanup pending. No purchase success claim.
- Bootstrap and migrations 001-019: unchanged in the repository.
- V1, Streamlit, parser, Discord, real trainer data and the protected guide:
  untouched. No deployment or dual-write.
- Commits pushed: `7e43d41 test: add real staging team lock validation`,
  `abed73d docs: record phase 8c staging validation`; this audit is a separate
  documentation checkpoint. Obtain its final hash from Git.
- Last completed: Phase 8C + staging validation. Next: Phase 8D.0 contract only.
- Remaining critical Phase 8 work: normal purchase, promoted stock claim,
  redemption, close-jornada/rewards, season/admin/trials/Hall operations.

Operational note: staging validation deliberately uses an isolated active test
season. The existing one-active-season index is preserved; do not disable it or
change a real season if a future rerun finds an active season already present.
