# Phase 8F Delivery

=== POKEAPP PHASE 8F ===

## Result

**PARTIAL**. Blindar and Revivir are DONE locally and in Supabase V2 staging.
Robar AND Comodin de Blindaje por Robo remain blocked: no canonical V2 gift item
code exists. No hidden catalog entry, fuzzy dispatch or partial robbery was invented.
F40-F42 / RF12 and F52-F70 / RF21-RF27 are explicitly not implemented/passing.
This is a two-effect subset, not the three-effect subset hoped for in the prompt.

## Start And End

- Start: main, `b3cabf3`, origin/main 0/0.
- Start tree: only the protected untracked user guide.
- Implementation: `a36b713 api: add v2 shield and revive redemption boundary`, pushed.
- End code checkpoint: a36b713; subsequent documentation-only closure is recorded
  by `docs: record phase 8f partial staging closure` in Git and the delivery response.
- Target upstream remains origin/main. No amend/force push or deployment.
- Protected guide SHA256 unchanged:
  `6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.

## Official Redemption Contract

- Actor: verified JWT principal, globally enabled, own purchase, active season_player.
- Season: exists; no active lifecycle requirement. Draft/finished/archived/discarded tested.
- Store Ban: purchase-only; does not prevent use of an already owned entitlement.
- Current jornada: not required. Robbery cycle is NOT a matchday concept.
- Normal/promotional parity: same item-code handler; expired promotion does not void use.
- Unsupported items: 409 REDEMPTION_NOT_SUPPORTED, purchase and all effects unchanged.

## API

- Method/path: POST /v1/seasons/{season_id}/shop/purchases/{purchase_id}/redemptions.
- Auth/header: Bearer + Idempotency-Key; actor cannot be overridden, including by admins.
- Body: exactly {"pokemon_entity_id":"<uuid>"}; extra authority/price/location fields rejected.
- Response: typed receipt with redemption/purchase/season/trainer/item IDs, effect,
  target Entity/owner IDs, used/applied/physical states, timestamps, event ID,
  gift_purchase_id NULL. No raw/private evidence.
- Stable errors: 401 auth, 403 actor/participant, 404 scope, 409 business, 422 body,
  503 sanitized backend. SQL error details/secrets never returned.
- Route is implemented/tested locally. Backend RPC is staged; API is not deployed.

## Effect Model

Purchase used = entitlement consumed, NOT save modified.
Redemption applied = internal competitive facts committed atomically.
Physical status = not_required (shield), pending (revive), completion timestamp NULL.
Future Companion handoff key = redemption_id. No queue/polling/completion API yet.

## Identity

Target is authoritative pokemon_entity_id, never fingerprint/name/species/slot/PID.
Repository captures the current revision; RPC rechecks it under the shared player
lock, together with season/current observation/binding/ownership/eligibility.
Ambiguous/missing/unbound targets fail closed. Stale server-observed revision
conflicts. Test pauses a real repository request, advances reconciliation, resumes
the request and verifies rejection without consumption. Evolution/movement preserve
the Entity; current location, not historical slot, governs revive eligibility.

## Effects

| Effect | Internal | Physical |
| --- | --- | --- |
| Blindar | Own party/boxes 1-8, not already blindado; redemption + flag + used + private event | not_required |
| Blindaje Robo | BLOCKED: no stable gift ShopItem/code. No speculative mapping | Not created |
| Revivir | Own current Caja 8; revive history, blindado, timestamp revivido_at, used, private event | pending, completed_at NULL |
| Robar | BLOCKED: cannot omit required gift. No theft/cycle/flags/consumption | No transfer or owner change |

Legacy revive allows an already shielded target; no once-ever rule was invented.
New flags use pokemon_entity_flags; legacy fingerprint rows are not rewritten.
revivido_at uses the added typed flag_timestamp, not a boolean disguised as time.
Ranking history remains durable, with no change to Streamlit ranking/cache behavior.

Robbery audit: active-trainer history after watermark, cycle reset when all relevant
trainers were robbed, watermark advance. That contract must not become a permanent
boolean. Future gift must be quantity 1, price 0, pending, linked uniquely to redemption,
no ledger debit or promotion stock use. Physical ownership stays with victim until a
future transfer lifecycle; none of it is partially shipped here.

## Activity

One REDEMPTION_USED, owner visibility, actor/admin read only. Other trainers and the
public activity view cannot read it. Receipt-shaped payload excludes all identity
evidence and strategic Pokemon details beyond necessary references. Dedupe and
redemption uniqueness prevent duplicate events. Event failure rolls back everything.
No Discord emitter or announcement.

## Idempotency And Concurrency

Lock order: actor trainer/season SHARE -> season_player UPDATE -> purchase UPDATE ->
own Entity UPDATE -> current revision/observation SHARE -> flags. Reconciliation
shares the participant lock. No Python business mutex or retry.
Future cross-player paths must lock all relevant season_players sorted by UUID first.

- Same key/purchase/target: original persisted receipt, including after a new head.
- Same key/different target: IDEMPOTENCY_CONFLICT.
- Different key/same consumed purchase: PURCHASE_ALREADY_REDEEMED.
- Four identical workers: one receipt.
- Different keys, same purchase: one winner.
- Different shield purchases, same Entity: one winner, other purchase untouched.
- Identity advance overtaking request: stale request rejected.

## Atomicity And Migration

024_redemption_effect_boundary.sql is the only new migration. 001-023 unchanged.
One transaction: redemption + flags + purchase pending-to-used + private event.
No debit/refund/stock change. Four local failure injections prove rollback at each
critical write. Robbery gift/cycle atomicity is NOT claimed implemented.

Redemptions add idempotency, effect, target/owner/revision references, separate
physical status/completion time, requested_at, event FK and stored receipt.
Constraints: one redemption per purchase; scoped idempotency; same-season Entity FK;
typed boundary fields with legacy NULL compatibility. Event FK deferred to commit.
Entity flags add timestamp and extend the value-shape check. No data deletion.
Existing duplicate purchase redemptions would fail migration visibly, not be merged.

RPC api_redeem_purchase: SECURITY INVOKER, fixed empty search_path; service_role and
SQL owner EXECUTE only. PUBLIC/anon/authenticated denied.
Browser writes, including admin, denied for purchases, redemptions, Entities,
observations, Entity flags, trainer_flags and activity_events. SELECT/RLS untouched.
Generated bootstrap includes 001-024. reset_dev updated only for disposable local builds.

## Local Validation

- Full suite: **311 PASS**, no skips (295 baseline + 16 API/redemption tests).
- Auth, Team Lock, normal/promotion purchases, identity, repositories/domain/schema: PASS.
- PostgreSQL 17.11 migrations build: PASS, including reset/rebuild/seed idempotence.
- PostgreSQL generated bootstrap build: PASS with same shared fixtures.
- Identity: 19 real SQL checks; redemption: 19 grouped checks in each build.
- Concurrency and four write-failure rollback locations: PASS.
- compileall: PASS; bootstrap equality: PASS; git diff --check: PASS.
- Local PostgreSQL stopped after work. No staging failure triggers or resets.
- Streamlit bare-runtime, Starlette/httpx deprecation and LF/CRLF warnings retained.
- Initial PowerShell log-redirection exit status was misleading; explicit native
  exit propagation confirmed final suite/build exit 0. No assertions weakened.

## Staging

Project: Pokeapp 2.0, https://uwleqeuzsveqlugugzba.supabase.co.
Preflight: latest 023, no new RPC, 36/36 RLS, 37 views, no purchases/redemptions.
Only committed 024 applied via MCP, version **20260923172957**, after implementation push.
RPC prosrc MD5: **66b07f2154ac0d0282f949d74284d9e9**, equals local.
SECURITY INVOKER, empty search_path, intended grants independently verified.

Command:
```powershell
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_redemptions.py --env-file .env.supabase-v2-rls.local --allow-staging-writes
```

Run: phase8f_validation_6f90941346754e9aa1e2cd12902182c7.
Result: **RESULT ok checks=19; Auth cleanup PASS; robbery/voucher NOT SUPPORTED**.
RF01-RF11 and RF13-RF20 covered; RF12 and RF21-RF27 NOT implemented/passing.
Remote identity binding, shielding, revival pending, idempotency, three redemption
races, identity-advance race, privacy and role-denial checks PASS.
First complete invocation passed; no transport failure observed this time.
Previous Windows/httpx transport intermittency is not claimed fixed.

Independent SQL cleanup: zero temporary Auth users/trainers/seasons and zero rows
in affected fixture tables, including other-season scope, redemptions, purchases,
promotions, ledger, events, save metadata, parses, identity tables and all flags.
Auth users/identities/sessions all zero. Retained baseline: 10 trainers, 61 catalog
items, 3 Storage objects; no real trainer/save was used or modified.

Before/after checksums match:

| Surface | MD5 |
| --- | --- |
| Catalog | f1cbe1216934d72dd5a1096d939dbf7a |
| Storage buckets | a1bad2c31b4a666ab2a70cd1519f5a69 |
| 37 views | d4da4cee7449e34f3ab16eeb74819c3d |
| Pre-024 public functions | 345ff0787fb03d61e710635715e284bb |

Inventory stays 36/36 RLS, 37 views. 023 function bodies unchanged.
Advisor retains 24 intentional public definer views, one mutable search_path warning
and three authenticated definer helpers; no new 024 finding. Not Advisor-clean.
See [8F.0 exceptions/remediation links](phase8f0-pokemon-identity.md).

## Progress And Checkpoint

BEFORE: ~55%. AFTER: **~56%**. CHANGE: +1 estimated weighted point.
Reason: official atomic self-service boundary plus two validated internal effects;
not the missing voucher/theft and not full Companion/save automation. Denominator
still includes remaining API, parser boundary, React/Cloudflare, data migration,
shadow/staging/performance/cutover and full Launcher/Companion safe physical actions.

LAST COMPLETED: 8F.0; now the 8F shield/revive subset is validated and staged.
IS REDEMPTION BOUNDARY COMPLETE: **PARTIAL**.
BLOCKER: canonical ShopItem/code for the robbery gift is absent in both reproducible
catalog and real staging. The gift cannot be replaced with a made-up item or omitted.
NEXT: **8F.1 - approve the canonical robbery-voucher catalog contract**.
Only after that decision should voucher/theft, full atomic cycle/gift and their
tests be implemented. This task stops here without starting that next subphase.

=== END REPORT ===
