# Phase 8F: Redemption / Effect Boundary

## Current Implementation: 2026-09-23

Resume checkpoint: `main`, `b3cabf3`, origin/main 0/0; protected guide untouched.
**PARTIAL: shield + revive DONE local + V2 staging; robbery AND its voucher are
blocked by the absent canonical V2 gift item.** Implementation: `a36b713`, pushed
before any staging change. [Delivery report](phase8f-completion-report.md).
8F.0 is DONE. Individual identity is no longer the blocker. The earlier audit is
preserved below as historical evidence, not current implementation status.

### Official Contract

`POST /v1/seasons/{season_id}/shop/purchases/{purchase_id}/redemptions` uses the
verified Bearer principal, `Idempotency-Key` (1-128 printable ASCII characters),
and exactly `{"pokemon_entity_id":"<uuid>"}`. Extra fields are forbidden.
The actor is JWT -> trainers.auth_user_id, never a body parameter. Even admins
consume only their own purchases. Global enablement and an active same-season
participant are required, including replay. The secondary legacy UI bypass is
not preserved. Streamlit itself is not changed.

The season must exist; no active lifecycle restriction is invented. Draft,
finished, archived and discarded seasons with an active participant are tested.
Store Ban blocks buying, NOT consuming existing entitlements. No current matchday
is required. Redemption does not debit/refund, change the ledger or promotional
stock. Normal/promotional purchases share one handler, even after a promotion ends.
Only pending quantity-one purchases can be consumed. Unsupported items return
`REDEMPTION_NOT_SUPPORTED` without consuming anything.

Server-owned dispatch is exact SQL `shop_items.code` -> effect, not display names:

| Legacy contract | Stable V2 code | Internal effect | Physical effect | Status |
| --- | --- | --- | --- | --- |
| Blindar Pokemon | blindar_pokemon | shield redemption, used purchase, blindado | not_required | Implemented |
| Comodin de Blindaje por Robo | NONE in canonical 001-023 catalog | would require blindado + blindaje_por_robo | not_required | Blocked, no invented code |
| Revivir Pokemon | revivir_pokemon | revive history, used purchase, blindado + revivido_at | pending | Implemented |
| Robar Pokemon | robar_pokemon, but missing gift item | must also include cycle/history and zero-price voucher | pending transfer | Blocked, no partial theft |

Shield accepts own current party or box 1-8, including Caja 8, and rejects an
existing true blindado (including a safely linked legacy flag). Revive requires
own CURRENT Caja 8 observation. The legacy revive branch has no already-shielded
or once-ever revival prohibition; none is invented. It records a timestamp and
sets blindado even if already shielded. Redemption history is the durable future
ranking input; existing league/ranking/cache behavior is untouched.

**Purchase `used` means the entitlement was consumed**, not that PKHeX changed
anything. Redemption `applied` means internal competitive consequences committed.
Revive has `physical_effect_status=pending`, completion timestamp NULL. Shield
has `not_required`. No physical applied/failed transition, queue, poller or job
table is shipped. A future Companion operation MUST originate at `redemption_id`,
resolve the same individual in an authorized current save, then backup/write/
validate/confirm separately. Species/nickname/slot are not operation identity.

### Atomicity, Identity And Permissions

The repository reads the current owner/season identity revision and passes its ID
to backend-only `api_redeem_purchase`. This version is server-observed, not accepted
from the browser. SQL rechecks Entity UUID, season, current ownership, unambiguous
status, newest revision and an authoritative current observation inside the lock.
Ambiguous/missing/unbound targets conflict without writes. A revision advancing
after the server read gives `POKEMON_TARGET_STALE`, even if the target survives.

Lock order follows existing mutation RPCs: actor trainer/season SHARE, then
season_player UPDATE, purchase UPDATE, own Entity UPDATE, current revision and
observation SHARE, then flag writes. Identity reconciliation uses the same player
lock. Only own-target effects are enabled. Future robbery must lock ALL affected
season_players sorted by UUID before purchases/entities/flags; no cross-player
implementation or cycle simplification is included in this subset.

Replay is checked after actor/participant/purchase scope but before mutable item
or target validation. Same purchase/key/target returns the stored original receipt
after moves/evolution/new heads. Same key/different target conflicts; another key
for the consumed purchase conflicts. SQL enforces unique(purchase_id), independently
of keys. Four simultaneous identical requests yield one receipt; two different keys
yield one winner; two different shield purchases targeting one Entity yield one
shield and one unconsumed loser. No Python business mutex or automatic retry.

One transaction persists redemption, Entity flags, purchase used and exactly one
`REDEMPTION_USED` event. Visibility is `owner`: actor and admin only, not other
trainers or public activity projections. Receipt/event contain IDs, effect/status
and timestamps, never identity evidence, parsed saves, moves, IVs, Auth or secrets.
Deferred event FK permits redemption-before-event insertion but requires the event
at commit. Fault injection at redemption, flag, purchase and event writes proves
complete rollback locally; no failure trigger is deployed remotely.

Migration **024_redemption_effect_boundary.sql** extends existing redemptions with
idempotency/effect/Entity-owner/revision/physical-status/timestamp/event/receipt fields,
same-season Entity FK, unique purchase and scoped idempotency index. Existing legacy
rows can retain NULL boundary fields. Duplicate historical purchase redemptions would
make the migration fail visibly; it never deletes or merges them to force acceptance.
`pokemon_entity_flags.flag_timestamp` preserves revivido_at as a timestamp, not a
fabricated boolean. The old value-shape check is extended for that exact flag;
other booleans/legacy links remain valid. Applying a new explicit effect may replace
an Entity flag's legacy link with a direct value; the legacy row itself is retained.
Migrations 001-023 are byte-unchanged. Generated bootstrap now includes 001-024;
reset_dev knows the new RPC and remains local-only/destructive.

RPC: SECURITY INVOKER, fixed empty search_path, EXECUTE only service_role/SQL owner.
024 revokes authenticated (including admin) INSERT/UPDATE/DELETE/TRUNCATE on purchases,
redemptions, pokemon_entities, pokemon_observations, pokemon_entity_flags, trainer_flags
and activity_events. Existing SELECT/RLS/view semantics remain intact. This deliberately
tightens the earlier browser-admin trainer_flags write allowance; privileged backend
administration remains possible. No service key reaches an API response or browser.

Errors: 401 auth, 403 globally disabled/inactive actor, 404 scoped purchase/season,
409 explicit business conflicts, 422 malformed inputs, 503 sanitized backend failure.
Unexpected SQL/transport errors never count as a business/security-test success.

### Demonstrated Remaining Blocker

The canonical seed 009 includes `blindar_pokemon`, `revivir_pokemon`, `robar_pokemon`,
but no `Comodin de Blindaje por Robo` code/item. Whole V2 migration/domain/repository
inspection found no authoritative alternative. Legacy creates the gift by display
name through `add_purchase(..., 0)`; V2 requires a ShopItem FK. This task explicitly
forbids inventing that catalog entry or dispatching a made-up code by name.

Consequently F40-F42 / RF12 (voucher) are NOT implemented or counted as passing;
F52-F70 / RF21-RF27 (theft) are NOT implemented or counted as passing. This is narrower
than the prompt's hoped-for three-effect subset and is reported explicitly. Shield
and revive proceed under the instruction not to block safe effects on robbery.
`robar_pokemon` and all unmapped codes fail closed without changing purchase/flags.

The cycle audit read `app/entrenadores/trainer_flags.py`: history after a watermark,
active-trainer filtering, reset when all relevant active trainers have been robbed,
then watermark advancement to the latest robbery redemption. A single permanent
robbed boolean would be incorrect. No cycle mutation or gift is half-implemented.
Future theft must atomically persist that contract plus the zero-price quantity-one
gift linked uniquely to originating redemption, with NO ledger debit. Entity owner
must remain the victim pending the future physical transfer. No physical transfer
or ownership mutation is performed by this implementation.

### Validation And Next Gate

Commands:

```powershell
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py
.\.venv-api\Scripts\python.exe -m compileall -q -x '[\\/](\.venv[^\\/]*|\.git|node_modules)[\\/]' .
.\.venv-api\Scripts\python.exe tools/generate_supabase_v2_bootstrap.py
# Same loopback-only PostgreSQL validator as 8F.0, with migrations and bootstrap builds.
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_redemptions.py --env-file .env.supabase-v2-rls.local --allow-staging-writes
git diff --check
```

New API tests cover auth, strict UUID-only body, server actor/head, sanitized errors,
receipt validation/privacy and no legacy/physical dependencies. Shared SQL/staging
fixtures exercise actual production repositories and RPCs, 19 reported check groups
(some groups cover multiple F/RF identifiers), not 77 individually passing tests.
They include same-key/different-key/same-target races and a deterministically paused
production repository request overtaken by real identity reconciliation. Local SQL
adds four forced-write rollback checks and all previous Team Lock/shop/RLS/identity
regressions. Fixture prefix is `phase8f_validation_<uuid>`, synthetic only; existing
seed item rows are read, never modified. No raw save or Storage write is required.
Explicit staging URL guard and write opt-in apply; Auth and relational fixtures are
removed in finally, with independent MCP zero-residue verification required.

Observed local results: **311 tests PASS** (295 baseline + 16 API/redemption tests,
no skips). PostgreSQL 17.11 migrations and generated-bootstrap builds PASS, each
including prior Team Lock/normal purchase/promotion/RLS fixtures, 19 identity checks,
19 redemption check groups and rollback injection at four critical writes.
Compileall, bootstrap equality and diff-check PASS. Existing Streamlit bare-runtime,
Starlette/httpx deprecation and Git LF/CRLF warnings were not suppressed. Initial
PowerShell redirection reported wrapper exit 1 despite successful Python summaries;
final explicit `$LASTEXITCODE` propagation confirmed exit 0 for suite and SQL builds.
Local RPC prosrc MD5 for staging comparison: `66b07f2154ac0d0282f949d74284d9e9`.
No original migration, protected runtime path or user guide changed.

### Observed Staging Results

Verified exact V2 `https://uwleqeuzsveqlugugzba.supabase.co`, latest 023 before this
task, no existing redemption RPC. Applied ONLY committed 024 through MCP as
`20260923172957`. RPC MD5 `66b07f2154ac0d0282f949d74284d9e9` matches local; SECURITY
INVOKER, fixed empty search_path, EXECUTE only backend/SQL owner. The seven affected
tables deny browser writes to anon/authenticated, including browser admins.

Unmodified staging validator exited 0 on its first invocation:
`RESULT ok checks=19; Auth cleanup PASS; robbery/voucher NOT SUPPORTED`.
Run: `phase8f_validation_6f90941346754e9aa1e2cd12902182c7`.
RF01-RF11 and RF13-RF20 are covered; RF12 and RF21-RF27 remain blocked, NOT passing.
No transport failure occurred in this run; previous Windows/httpx intermittency
is not claimed fixed. Endpoint tests run locally; the RPC is staged. No API deployment.

Independent MCP SQL found no fixture Auth/trainers/seasons and zero rows across
season_players, purchases, redemptions, promotions, ledger, activity, saves/parses,
entities/revisions/observations/entity flags, legacy flags and trainer flags.
Auth users/identities/sessions all zero. Original 10 trainers, 61 items and 3 Storage
objects remain. Catalog checksum `f1cbe1216934d72dd5a1096d939dbf7a`, bucket checksum
`a1bad2c31b4a666ab2a70cd1519f5a69`, view checksum `d4da4cee7449e34f3ab16eeb74819c3d`
and pre-024 function checksum `345ff0787fb03d61e710635715e284bb` all match preflight.
36/36 public tables have RLS; 37 views preserved; both 023 function checksums unchanged.
Real catalog audit also found only `blindar_pokemon` among shield/voucher candidates,
confirming the missing gift representation without changing the catalog.

Advisor retains existing findings: 24 intentional public definer projections,
one mutable search_path (`set_updated_at`) and three authenticated identity-helper
definer functions. No new 024 finding; this is NOT an Advisor-clean claim.
See the accepted exceptions/remediation links in [8F.0](phase8f0-pokemon-identity.md).
The disposable local PostgreSQL server was stopped after validation.

Full 8F remains PARTIAL. One next subphase: **8F.1 - approve the canonical robbery-voucher catalog
contract**, before implementing the remaining voucher/theft flow. Do not implement
that subphase in this task. Weighted estimate: ~55% before, **~56% after** (+1 point)
for the safe subset and reusable atomic boundary, not the missing theft feature.
Full-product scope still includes parser, React/Cloudflare,
migration/shadow/performance/cutover and full Companion safe save automation.

## Historical Pre-8F.0 Audit

Date: 2026-09-23. RESULT: **BLOCKED before implementation**.
Historical audit: [Phase 8F.0](phase8f0-pokemon-identity.md) now implements the
identity prerequisite. This audit remains unchanged as evidence of the original blocker.
Verified starting checkpoint: main, `2102682`, origin/main divergence 0/0.
Only pre-existing untracked file is the user-owned guide, untouched.

This document records evidence, not an implemented API or an approved lifecycle.
Last completed implementation remains Phase 8E. No migration 023, endpoint, RPC,
schema change, staging access, parser execution or save mutation in this task.

## Stop Condition And Safe Subset

The requested STOP for insufficient Pokemon target identity is met. All FOUR
implemented legacy redemption branches need an individual Pokemon target:
Blindar Pokemon, Comodin de Blindaje por Robo, Revivir Pokemon and Robar Pokemon.
The legacy fingerprint is not individual identity; distinct Pokemon can collide.
The bridge DTO does not expose a stronger identifier, and the domain adapter can
produce an empty Pokemon ID. Accepting such a target would make a durable effect
ambiguous, even when the future physical write is marked external_pending.

The exception allowing a safe subset was evaluated. No implemented legacy
bookkeeping-only or target-free redemption was found. Other catalog items have
purchase records/descriptions, but no executable use contract. Consuming one as
a generic delivery request would define new behavior, including missing choice
parameters for some items. No business behavior was invented to claim completion.
Creating an endpoint which rejects every demonstrated redemption would also not
meet the requested DONE gate. Only the audit/documentation is delivered.

## Identity Evidence

1. `pkmmeta.py:6` `_fingerprint_base` hashes dex, species name, OT TID/SID,
   gender, shiny and form, optionally level. `pokemon_fingerprint_stable` at
   line 27 removes level but includes no per-individual identifier. Species/form
   changes can also change the so-called stable fingerprint.
2. `Bridge/PKHeXBridge/Program.cs:224` `PkmToDto` exports species, stats, moves,
   OT, box and slot, but no PID/encryption constant or stable individual UUID.
   Existing physical bridge operations were inspected only; none was invoked.
3. `conex_pkhex.py:441` normalized output contains positional/OT/species data,
   not an individual Pokemon ID or fingerprint.
4. `app/domain/legacy.py:62` copies `fingerprint` or `id` when supplied, otherwise
   `PublicPokemon.id`/`PrivatePokemon.id` is empty (allowed by current DTOs).
5. `002_seasons.sql:90` keys pokemon_flags by season/owner/fingerprint/type.
   Its comment already defers a stronger ID to a future parser boundary. A flag
   can therefore affect both members of a colliding pair.

Read-only synthetic reproduction executed successfully using the current code:

```python
from pkmmeta import pokemon_fingerprint, pokemon_fingerprint_stable
from app.domain.legacy import pokemon_from_legacy

a = dict(dex_id=94, species="Gengar", species_name="Gengar", ot_tid=12345,
         ot_sid=6789, gender="M", is_shiny=False, form_index=0, level=50,
         nickname="Target-A", ivs={"hp": 31, "atk": 0})
b = {**a, "nickname": "Target-B", "ivs": {"hp": 1, "atk": 31}}
assert a != b
assert pokemon_fingerprint_stable(a) == pokemon_fingerprint_stable(b)
assert pokemon_fingerprint(a) == pokemon_fingerprint(b)
assert pokemon_from_legacy(a, private=True).id == ""
```

Both stable hashes: `119713fc1c1eecfc050a7afbe5672c62bb46d409`.
Both level-inclusive hashes: `4afee29bd19cbdba5f3878f8125f1f527c8d8dc0`.
This is identical hash INPUT for distinct individuals, not a theoretical SHA-1
cryptographic collision. No real Pokemon/private save data was used.

Box/slot plus a saved snapshot locates an occurrence in that exact snapshot, not
the same individual after a move, evolution, reorder or new save. Rejecting
duplicates in just today's save does not fix collisions across saves or seasons.
Generating a random ID for each parse would break persistent flag identity.
None of those shortcuts was implemented.

## Legacy Redemption Map

Primary source: `app/tienda/redeem.py:68` ownership helper and the four branches
starting at lines 104, 196, 260 and 312. Inventory allowlist:
`app/entrenadores/inventory.py:19`. Storage: `app/storage_shop.py:1166` / `1237`.

| Item | Demonstrated legacy action | Effect category | 8F disposition |
| --- | --- | --- | --- |
| Blindar Pokemon | Own team or any own box, reject already blindado; record shield, mark purchase used, set blindado | Internal competitive flag | Blocked: individual identity |
| Comodin de Blindaje por Robo | Own team/box, reject already shielded; record shield, used, blindado + blindaje_por_robo | Internal competitive flag; gift purchase originates from robbery | Blocked: identity; gift is not a separate seeded catalog item |
| Revivir Pokemon | Own Caja 8 target; record revive, used, blindado + revivido_at; invalidate ranking cache | Internal registration/competitive accounting plus save-dependent physical revival | Blocked: identity; physical revival must stay pending |
| Robar Pokemon | Other active unrobbed trainer, team/non-dead box, unshielded Pokemon; record steal, used, grant zero-price shield voucher, robbed-cycle trainer state and Pokemon robbed/shield flags | Cross-player domain state plus save-dependent transfer | Blocked: identity; cannot omit cycle/voucher or physically transfer |

Bookkeeping-only implemented redemptions: **none found**.
`app/liga/ranking.py:128-190` counts revive redemption history for death penalties;
that history is a competitive fact, not proof a physical revive happened. Do not
silently reinterpret a requested future effect as an applied revival.

Robbery details: `app/entrenadores/trainer_flags.py` derives robbed history, uses a
history watermark, and resets the cycle when all active trainers have been robbed.
It is not equivalent to simply setting one trainer boolean forever. The gift
purchase is part of the existing action, not a new debit/refund. None of these
effects was ported partially. Physical steal/revive are absent from this UI flow;
success text explicitly says the save is not modified.

### Remaining Catalog

Source: `app/tienda/catalog_data.py`, `_is_usable_item` and whole-repository search
for add_redemption/set_purchase_status call sites. All actual calls originate in
the four branches above (plus storage/repository wrappers).

- Captura Extra: described permission for another capture; no use/redemption
  branch, target/route validation or consumption contract. Special/unsupported.
- Fosil: purchase and rules describe obtaining a fossil; no redemption branch or
  fossil choice/delivery contract. Potential external delivery, unsupported now.
- Bayas: Aranja, Zidra, Zreza, Ziuela, Meloc, Safre, Perasi, Atania, Aslac, Lichi,
  Petaya, Ganlon, Apicot, Lansat, Starf, Occa, Passho, Wacan, Rindo, Yache, Shuca,
  Chople, Kebia, Coba, Payapa, Tanga, Charti, Kasib, Haban, Colbur, Babiri, Chilan.
  Catalog/inventory only; adding items to the game would be save-dependent.
- Competitivos: Gafas Elegidas, Cinta Elegida, Panuelo Elegido, Restos, Banda Focus,
  Vidasfera, Mineral Evolutivo, Casco Dentado, Globo Helio, Gemas Elementales,
  Boton Escape, Tarjeta Roja, Hierba Blanca, Roca del Rey, Periscopio, Lupa,
  Toxisfera, Llamasfera, Objeto Potenciador de Tipo. Same absence of redemption;
  some entries are categories needing a specific item choice, not one game item.
- Crianza: Capsula Habilidad, Chapa Dorada, Chapa Plateada, Menta de Naturaleza,
  Objeto Evolutivo. Save-dependent operations in concept, but target/stat/nature/
  evolution choices and use validation do not exist in the current flow.

No rare-candy mechanism is implemented by this phase. Descriptions are evidence
of intent, not authority to invent redemption input/validation for these items.
Future effect categorization must not dispatch by mutable item display names.

## Ownership And Eligibility Audit

- Legacy validates logged-in owner, purchase ID, matching item name, and rejects
  status `used`. Its helper does NOT explicitly reject every other status.
- Inventory enables use only for the own profile and an active trainer.
  `is_trainer_retired` means retired, abandoned OR disqualified, not only retired.
- There is an inconsistent secondary entry: `app/tienda/ui.py:26-30` passes an
  existing redeem_ctx straight to the flow, whose ownership helper does not check
  inactive status. Do not silently copy this bypass or call it an approved rule.
- Store Ban locks buying (`sections.py:84-89`); it is not passed into redemption.
  No demonstrated basis to block use of previously purchased goods for Store Ban.
- No current-jornada resolver is used by redemption. The robbery cycle is not
  automatically the official matchday. Do not add a matchday prerequisite.
- No explicit season lifecycle eligibility gate is present in these redemption
  paths. Active/finished/archived usage policy needs a declared contract before
  imposing purchase eligibility on redemption. No such policy was invented.
- Promo and normal purchase share the same use flow; no use rule based on origin.
- Four branches execute several independent writes and sometimes swallow flag
  failures. Legacy atomicity/double-use gaps are not a model to copy into V2.

## Events And Discord

`app/domain/activity.py` currently defines only save_uploaded, purchase_completed
and team_locked. `app/activity/events.py`/domain services have corresponding
builders/emitters, but none for redemption, shield, revive or steal. The storage
redemption insert does not emit ActivityEvent. `docs/phase2-functional-audit.md`
explicitly deferred REDEMPTION_USED pending privacy decisions.

There is therefore no existing redemption event type to claim was preserved.
A future additive event must clearly describe acceptance vs physical application,
with explicit owner/admin visibility and dedupe. Naming alone is not a blocker;
the identity stop occurs first. No fake PURCHASE_COMPLETED event is substituted.
Discord has purchase/discount notifications, not a redemption notification in the
audited flow. No Discord code was changed or called.

## Actual V2 Schema

`004_shop.sql:76`: purchases status is pending/used/cancelled/refunded. Python
PurchaseStatus currently has pending/used/cancelled. Quantity is positive; 8D/8E
create quantity 1. 021 stores economic idempotency and historical balance; 022
enforces promotional claims. These must survive future use unchanged.

`004_shop.sql:111`: redemptions columns are id, purchase_id, season_id, trainer_id,
season_player_id, shop_item_id, redemption_type (default item_use), status (default
applied), payload JSONB and redeemed_at (default now()). Valid statuses are applied,
reverted, cancelled. No idempotency key, effect status, target ID, requested_at,
applied_at or unique purchase constraint currently exists. Target/effect details
could be carried by payload but are not a validated contract today.

FKs bind purchase + season + trainer + item to the same purchase, and player +
season + trainer to the same participant. All delete actions restrict. Index 008
on (purchase_id, redeemed_at DESC) is non-unique. RLS permits owner/admin reads;
no browser insert/update policy. current_redemptions is a security-invoker/barrier
owner/admin projection. Generic payload does not by itself validate an effect.

pokemon_flags/trainer_flags have typed identity fields plus generic type/value/
payload. Existing policies permit admin flag writes, not trainer writes; any
future backend effect must account for those pre-existing permissions. No grants
were relaxed or tightened in this audit. No FK to a Pokemon entity exists.

An additive migration could distinguish accepted redemption from pending physical
effect without destructive redesign. That schema capability does NOT resolve
which actual individual a request targets. No migration is generated yet.

## Boundary Required After Unblocking

Requirements retained, not implemented or approved enum names:

- Purchase records the acquisition. Redemption consumes the single acquired right.
  Internal effect application and external physical completion are distinct facts.
- A requested external effect must remain explicitly pending, with no physical
  applied timestamp or misleading used/completed claim about the save.
- Proposed route remains POST /v1/seasons/{season_id}/shop/purchases/{purchase_id}/
  redemptions, verified self-service JWT and Idempotency-Key, strictly typed inputs
  determined by server-owned item/effect contract. No arbitrary effect JSON.
- Validate owner/season/purchase state/quantity and target identity/eligibility.
  Admin self-service cannot consume another trainer's purchase.
- Lock purchase, recognize same-key semantic replay, enforce one logical redemption
  DB-side, and commit redemption + transition + internal effect + event together.
- Reused key with different target conflicts; a lost response returns original
  owner-safe receipt. No second debit, refund or promotion stock change.
- Snapshot only validated item/effect/target references and minimal parameters;
  do not copy private parsed saves. Stable redemption_id will identify any future
  Companion operation; never trainer/species/name/date as operation identity.
- Companion must later resolve the same individual against a verified save,
  backup/write/validate/confirm separately. No queue/polling/client is added now.

The API/receipt body, effect-state enum and event contract are deliberately NOT
finalized here. They depend on resolving the demonstrated target/eligibility gaps.

## Validation And Boundaries

Executed on the unchanged runtime:

```powershell
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py
.\.venv-api\Scripts\python.exe -m compileall -q -x '[\\/](\.venv[^\\/]*|\.git|node_modules)[\\/]' .
git diff --check
```

Baseline: 255 tests PASS, including Auth, Team Lock, normal/promotional purchases,
shop, repositories and schema/bootstrap equality. Compileall PASS. These are NOT
8F success tests; no redemption endpoint exists. Synthetic collision reproduction
PASS means the BLOCKER is reproduced, not that target handling is safe.
Warnings retained: Streamlit bare runtime/cache/session and Starlette httpx
deprecation. Git may report LF/CRLF normalization notices.

New PostgreSQL concurrency/rollback/effect tests: NOT RUN, no 023 or implementation.
Real staging RF01-RF20: NOT RUN. No remote access/writes/fixtures, so no cleanup
needed. Previous 8E staging evidence remains historical, not rerun here.
001-022 and bootstrap unchanged. V1, Streamlit, parser/bridge, Discord, raw saves,
Storage, React and Companion untouched. No credentials read or printed.

## Next Checkpoint And Progress

Last completed: Phase 8E. Phase 8F: blocked after audit, not DONE or staged.
One next subphase: **8F.0 - authoritative Pokemon identity contract**. Establish
the individual identity and reconciliation rules for same-species individuals,
clones/duplicates, moves/evolution, generations and save revisions, and how flags
migrate without conflation. Scope the necessary read-only parser/DTO work before
authorizing it; this task explicitly did not modify the parser. Do not assume
PID alone is globally unique. Resolve the inactive/season usage inconsistency
when resuming the redemption contract; do not silently preserve a UI bypass.

Global progress before: ~52%. After this BLOCKED task: ~52%, change +0 points.
The audit reduces risk but ships no new final-product capability. This estimate
covers remaining API, parser, React/Cloudflare, data migration, shadow/staging/
performance/cutover, full Launcher/Companion and safe future save automation;
it is not a ratio of phase numbers. A completed 8F estimate is not claimed.

## Delivery Record

Documentation-only commit/push with subject `docs: audit phase 8f identity blockers`.
Exact final hash is reported at delivery; no functional implementation commit.
Modified documents: this audit plus project-checkpoint, architecture, security-rls,
supabase-v2 and migration-plan. Protected user guide stays untracked, SHA256:
`6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.
