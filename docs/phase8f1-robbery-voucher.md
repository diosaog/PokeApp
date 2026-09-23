# Phase 8F.1: Canonical Robbery And Voucher

## Status

Implementation from `main` / `2bd0365`, origin/main 0/0, protected guide unchanged.
DONE local + staging. Local verification PASS (318 tests, migrations/bootstrap, real races and rollback);
025 applied as `20260923180416` after implementation push `4cf21bf`.
First concurrent staging run hit a transport ReadError; independent SQL confirmed
zero fixture/Auth residue. A validator-only per-worker HTTP/1.1 session isolates
connections without retrying mutations or altering production transport.
Staging: 17 robbery/voucher groups and 19 shield/revive groups PASS, Auth cleanup
and independent zero-residue SQL PASS. The missing catalog
decision is now explicitly approved, not an unresolved product question.
The completion report records run IDs, remote version, checksums and all final gates.

## Approved Catalog Contract

- Code: `robbery_shield_voucher`.
- Display: Comodin de Blindaje por Robo (canonical SQL stores the accented name).
- Category: `comodines`; acquisition_mode: `reward_only`; price 0; enabled false.
- `enabled` controls SHOP availability, not the use of an already owned purchase.
- CHECK constraints require every reward-only item to be disabled and zero-price;
  the canonical code cannot be switched into purchasable mode.
- Existing normal/promo RPCs already reject disabled/zero-price items under lock.
  They are unchanged; tests call both with a valid shop context and the voucher UUID.
- `public_shop_items` already filters enabled items: no new offer or view rewrite.
- Existing 61 items default to `purchasable`, retaining their data and semantics.
- Migration 025 adds one code-unique canonical item, not a fixture item. No 001-024 edits.

## Legacy Authority

`app/tienda/redeem.py` explicitly calls `add_purchase(current_user,
"Comodin de Blindaje por Robo", 0)` in the robbery branch. The recipient is the
ROBBER, not the victim. It sets victim Pokemon `robado`, `robado_from`, `robado_at`,
`blindado`; the voucher sets `blindado` and `blindaje_por_robo` on an owned Pokemon.
`app/entrenadores/trainer_flags.py` and `app/domain/services/trainers.py` define
history, active-set filtering, pre-check reset and post-robbery cycle completion.
The cycle has no matchday dependency.

## API And Identity

Existing POST `/v1/seasons/{season_id}/shop/purchases/{purchase_id}/redemptions`,
Bearer JWT + Idempotency-Key, body ONLY `pokemon_entity_id`. No victim, item,
effect, price, location, expected-head or acquisition-type authority from clients.
The server reads Entity current owner and captures THAT owner's head; SQL checks
both again under locks. Replay returns the original stored receipt before live
target eligibility checks, but still requires enabled actor/active participation.
Responses allow `shield`, `revive`, `robbery_shield`, `steal`; only steal includes
a non-null gift_purchase_id and a different target_owner_trainer_id.
No evidence, PID or raw parsed payload is exposed.

- Actor: enabled verified trainer, active same-season participant, own pending qty1 purchase.
- Robbery: another active participant, current unambiguous bound Entity, party or
  boxes 1-7; no true blindado (including linked legacy flags); not robbed in cycle.
- Voucher: own current unambiguous Entity, party or boxes 1-8, not already blindado.
- Blindar/Revivir retain 024 rules. No new lifecycle/Store Ban/current-day restriction.
- Robar normal and promotional purchases have identical redemption behavior.
- Stable conflicts add STEAL_SELF_TARGET, STEAL_TARGET_SHIELDED,
  STEAL_TARGET_INELIGIBLE, STEAL_VICTIM_INELIGIBLE, STEAL_VICTIM_ALREADY_ROBBED,
  STEAL_CYCLE_CONFLICT. SQL diagnostics are never returned by the API.

## Atomic Model

`purchases.acquisition_type` distinguishes positive-price paid purchases from
zero-price qty1 rewards with no promotion, wallet snapshot or acquisition key.
`origin_redemption_id` is a unique FK. A trigger checks canonical item, robbery
origin, actor/season/player and exact gift UUID. The receipt gift FK is deferred
within the transaction to allow the circular origin relation. No manual grant endpoint.
The same SQL transaction writes redemption, exact Entity flags, victim trainer
flag/history/cursor, gift purchase, actor purchase used and one owner-private event.
No ledger or stock mutation occurs, including for promotional robbery entitlements.

`robbery_cycles` is backend-only, RLS enabled, no PUBLIC/anon/authenticated grants.
It persists cycle_number, last_redemption_id and history_watermark_id. Immutable
redemptions store the cycle and victim; unique season/cycle/victim prevents duplicates.
`trainer_flags.robbed` is the current projection, not a permanent disqualification.
The active set includes the robber. Completion succeeds, advances the cursor/watermark
and clears active marks atomically. A reduced active set after retirement is checked
before a new robbery, matching legacy. History is not deleted or counted in a new cycle.

`robado_from` is a typed trainer UUID referring to the victim; `robado_at` and
`revivido_at` are timestamps, not boolean flags. Existing legacy flags are not
eagerly rewritten. Explicit new effects replace only their matching linked flag.

## Lock Order

Trainer SHARE -> season NO KEY UPDATE -> ALL existing season_players ordered by
player UUID FOR UPDATE -> actor purchase -> item SHARE -> target Entity UPDATE ->
owner head/observation SHARE -> cycle/flags -> reward item/gift -> purchase/event.
All redemption handlers share this ordering. Season-level serialization is a
conservative choice for this small competition, not a throughput optimization.
The active set is captured from locked participant rows. New membership is observed
by the next transaction; future participant administration must acquire season then
ordered participants, never the reverse. No new membership API is shipped here.
NO KEY UPDATE allows identity's FK KEY SHARE locks while preventing competing
redemptions and conflicting season changes. See the official
[PostgreSQL row-lock matrix](https://www.postgresql.org/docs/17/explicit-locking.html#LOCKING-ROWS).

## Physical Boundary

Purchase used means entitlement consumed; redemption applied means internal facts
committed. Voucher and shield are not_required; revive and theft are pending with
completion timestamp NULL. PokemonEntity owner remains the victim. Future physical
execution must originate from redemption_id; no Companion queue or physical
ownership transition is fabricated. No save write, PKHeX write, Discord or deployment.

## Validation And Cleanup

Shared synthetic fixtures cover catalog/API denial, reward provenance, exact flags,
private events, cycles/retirement, all requested races, paused victim-head advance,
voucher use and paid/promo parity. The original shield/revive suite remains separate.
Local AFTER triggers force seven failures: redemption, Entity flag, trainer flag,
cycle update, gift insert, actor purchase update, event insert. Entire snapshots
must match before/after failure. No fault-injection triggers are applied to staging.
Local SQL transport uses stdin to avoid the Windows command-line size limit for
large synthetic identity requests; production transport is unchanged.
Staging uses `--robbery`, prefix `phase8f1_validation_<uuid>` and existing target guard.
Cleanup unlinks ONLY tracked synthetic circular receipt/origin rows before deletion,
then removes seasons/identities/trainers/Auth users. Canonical voucher is retained.
Independent remote SQL checks counts, catalog, views, Storage and zero fixture residue.

## Scope And Next

No V1, Streamlit, auth, React, Discord, physical bridge or migration cutover change.
No dual write. Next proposal: Phase 8G - season/league administration API contract
audit. It is NOT implemented by 8F.1. Full-project progress only rises from ~56% to
~57% with staging and all other gates closed; parser/frontend/shadow/cutover and
full safe Companion automation remain outstanding.
