# Phase 8F: Redemption / Effect Boundary Audit

Date: 2026-09-23. RESULT: **BLOCKED before implementation**.
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
