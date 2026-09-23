# Phase 8F.0: Authoritative Pokemon Individual Identity

Date: 2026-09-23. Starting checkpoint: `main`, `7207014`, origin divergence 0/0.
Status: LOCAL DONE; staging gate blocked by MCP OAuth refresh failure. No redemption implementation.
Protected user guide: `docs/pokeapp-guia-completa-pestanas-y-producto.md`, untouched/untracked.

## Root Cause

The legacy fingerprint uses species/dex, original-trainer numbers, gender, shiny,
form and optionally level. Different Gengar with different nickname/IVs collide.
The regression test deliberately preserves this result. Making the hash longer
does not add evidence. Position is an observation address, not identity. PID can
collide or be copied, so it is never used as an entity primary key.

## Actual PKHeX Audit

The tracked root `PKHeX.Core.dll` reports **24.11.11.0** by file version AND loaded
assembly reflection. The bridge project references package 24.11.11. The probe in
`tools/identity_bridge_probe` compiles the actual bridge source and calls ONLY its
read-only `PkmToDto` on in-memory `PK3`, `PK4`, `PK5` objects. It never opens a sav,
dispatches `Bridge.Main`, calls revive/steal, or persists a Pokemon to a save.
Tracked DLL SHA256: `16d2eee98d1e4f57a930d39adfa63219ba4d5cdf2644d52438f04320c68dbe67`.

| Evidence | PK3 | PK4 | PK5 | Identity use |
| --- | --- | --- | --- | --- |
| PID | UInt32 | UInt32 | UInt32 | Candidate bucket only; collisions allowed |
| EncryptionConstant | PID alias | PID alias | PID alias | Export null, NOT independent evidence |
| TID16 / SID16 | UInt16 | UInt16 | UInt16 | Original trainer, not competitive owner |
| OriginalTrainerName/Gender | Present | Present | Present | Normally stable; changes require review |
| Version / Language | Present | Present | Present | Normally stable; required for matching |
| Format / Context | 3 / Gen3 | 4 / Gen4 | 5 / Gen5 | Native format, not a global identity |
| MetLocation / MetLevel | Present | Present | Present | Supplemental, excluded from matching key |
| EggLocation | Stub zero | Present | Present | Null in Gen3, supplemental otherwise |
| MetDate / EggMetDate | Unavailable | Nullable | Nullable | Supplemental, null is not invented data |
| IV_HP/ATK/DEF/SPA/SPD/SPE | Present | Present | Present | Supplemental; stat edits do not allocate a new ID |
| Gender/Form/IsShiny | Present/derived | Present | Present | Existing export, excluded from identity |
| Checksum / raw PKM bytes | Present | Present | Present | Mutable and clonable; NOT stored as identity |

The evidence DTO stores format, not a duplicate generation/context field; the probe
records all three for audit. Met/egg data can change on hatch or transfer. Gender,
shiny and Gen3 forms may be derived from PID; they are not independent identity
proof. Species/form, nickname, ability/nature, level/EXP, HP, EVs, moves/PP, held
item, friendship and location are not matching inputs. Raw byte hashes would also
change under normal play and would not distinguish exact clones.

Supplemental source inspection: tagged upstream [PK3](https://raw.githubusercontent.com/kwsch/PKHeX/24.11.11/PKHeX.Core/PKM/PK3.cs),
[PK4](https://raw.githubusercontent.com/kwsch/PKHeX/24.11.11/PKHeX.Core/PKM/PK4.cs),
[PK5](https://raw.githubusercontent.com/kwsch/PKHeX/24.11.11/PKHeX.Core/PKM/PK5.cs).
The executable reflection probe, not an assumed property name, is the local authority.

The old OT display export uses older property names and may be zero/empty on this
assembly. It is deliberately unchanged for legacy compatibility; the NEW evidence
uses verified `TID16`, `SID16`, `OriginalTrainerName`. Unknown/missing required
evidence is rejected by V2 rather than silently substituted with zero. PID=0 itself
is a valid UInt32 value, not a missing sentinel.

## Contracts And Persistence

`PokemonIdentityEvidence`: typed, schema version 1, private explicit field (not metadata).
`PokemonEntity`: durable PokeApp UUID, season scoped, current owner separate from OT.
`PokemonObservation`: one occupied location in a specific save/revision, raw evidence,
signature, candidate IDs, outcome and optional authoritative entity ID.
`PokemonIdentityRevision`: explicit predecessor, capture order, source parsed ID,
input signature, identity schema/reconciliation versions (both 1).

Migration **023_pokemon_identity.sql** adds four tables:

- `pokemon_entities`: current identity status and initial evidence, no full duplicated Pokemon.
- `pokemon_identity_revisions`: immutable receipts/linear predecessor chain, one per save.
- `pokemon_observations`: unique save+location and save+entity, ambiguity represented by NULL binding plus candidate IDs.
- `pokemon_entity_flags`: new individual flags OR a link to a retained legacy flag.

It adds a composite parsed-save uniqueness constraint for the observation source FK.
No table/data removed, no 001-022 modification, no economy or Team Lock history rewrite.
The generated bootstrap includes 001-023 in order. `reset_dev.sql` additionally knows
these new objects solely for isolated local rebuilds; it is NEVER applied remotely.

An initial entity UUID is allocated deterministically with UUIDv5 using save UUID
and first observation address. This is allocation, NOT subsequent matching: moved
Pokemon keep the persisted entity UUID. Reparse does not create a new save UUID;
the existing save-file hash uniqueness prevents duplicate uploads in the same scope.
Owner is not encoded in entity UUID; future audited ownership transfer can update
the current owner, while observations and flag provenance retain their old owner.
No ownership-transfer command exists in this phase.

## Reconciliation Version 1

Pure `reconcile_pokemon` receives the current owner/season's persisted head state,
including retained missing entities, and the incoming observations. No SQL, SDK,
Streamlit or FastAPI in this function. It does not scan arbitrary global history.

1. No prior PID candidate: allocate one NEW entity per occurrence, including clones.
2. Exactly one prior AND one incoming PID occurrence: MATCHED only if the versioned
   format/PID/OT IDs/name/gender/origin/language key matches and the entity was not ambiguous.
3. Multiple candidates/occurrences, changed core evidence, or prior ambiguity:
   AMBIGUOUS, NULL binding, explicit candidates. No slot-continuity tiebreaker.
4. Prior entities not observed/candidates: MISSING, retained, never inferred dead/deleted.
5. A unique missing entity returning with compatible evidence recovers the same UUID.

This intentionally treats even same-PID individuals with different IVs conservatively
after initial allocation. It does not pretend IVs, nickname, checksum, unchanged slot,
or probability can prove clone continuity. No confidence score or species/evolution
table is used. Gastly -> Haunter -> Gengar tests pass for all three actual PKM formats.
Format transfer/hatching/core-evidence changes sharing PID require review, not a new
guessed match. Completely externally rewritten evidence is outside automatic continuity
guarantees; a trusted capture chain is not proof that a user never edited a save.

Ambiguity remains sticky until an explicit audited decision is implemented. Merely
removing one clone does not silently make the survivor identifiable. `IdentityResolutionDecision`
defines actor, observation, target entity, expected head, reason and evidence reference.
Future execution must validate scope/candidates/exclusivity under the same lock and
append an audit record/new version. No resolving UI, heuristic or admin mutation is shipped.

## Ordering, Idempotency And Concurrency

`CaptureOrder(stream_id, sequence)` is a **backend attestation** from a trustworthy
capture chain. There is no new browser field/endpoint accepting it. Existing uploads
do NOT establish such a chain. Without a trusted order, the application refuses
current-state promotion. Future Companion/import boundary must supply/prove it; do
not assign sequence by HTTP arrival order to old saves.

Within a stream, sequence must increase and uploaded_at must also exceed the last
accepted save's uploaded_at. Different streams, lower/equal sequence or old upload
timestamps are rejected. The deterministic predecessor is the explicitly loaded
highest revision_number, validated by compare-and-swap (CAS) inside the transaction.
An old save may remain in save_files/parsed_saves as historical raw/parser data, but
receives no authoritative identity revision and cannot replace current state.

`commit_pokemon_identity(jsonb)` locks the season_players row FOR UPDATE. It rechecks
owner/save/parser payload/version, source evidence/occupied count, predecessor/order,
matching uniqueness and source scope. It atomically persists entities, observations,
revision and safe legacy links. Concurrent identical saves return the same persisted
receipt. Competing different saves on the same predecessor yield one winner and one
conflict; caller must reload, never blindly overwrite. Pagination prevents truncating
the previous entity state at PostgREST's default row limit.

Same-file reparse with identical identity observations reuses the original receipt,
even under a newer parser version. Changed evidence/algorithm is NOT silently rebound:
the old receipt is immutable and review/versioned migration is required.

## Legacy Flags

The legacy fingerprint algorithm, rows and unique constraint remain untouched.
A flag links automatically only if its fingerprint has exactly one entity across
this owner/season chain's retained observations, with no ambiguous observation.
Collision/no candidate/constraint conflict leaves the original row unresolved.
Never assign to the first Pokemon or copy a flag to all candidates.

The mapping alternative avoids weakening legacy fingerprint uniqueness to support
two new flags on two clones. Entity flags have unique(season, entity, type), nullable
legacy_flag_id unique, and owner/legacy-scope validation. For linked flags the value
stays in the original `pokemon_flags` row (`flag_value` NULL in link); future reads
must join that row, not cache a copied boolean. Standalone new flags carry their own
value and require no invented legacy fingerprint. No existing flags are eagerly
migrated by SQL installation; links arise during this opt-in backend reconciliation.

## Privacy And Future Effect Boundary

All four tables: RLS on, anon denied, authenticated owner/admin SELECT only,
service_role writes. Even browser admins cannot bind entities, resolve ambiguities,
insert/update/delete identity rows or execute the RPC. Both functions are SECURITY
INVOKER with empty fixed search_path and backend-only EXECUTE. No new public views.

`PrivatePokemon.identity_evidence` is optional/backward compatible and omitted by
`to_public()`. New Public/Private Pokemon can carry a reconciled UUID in existing `id`.
`bind_parsed_save` produces a new private ParsedSave; ambiguous IDs remain empty and
status is in its reconciliation plan. Legacy empty IDs still work for display.
The repository's `authoritative_target` accepts only a current, unambiguous observation
with current ownership. It is a read boundary, NOT effect authorization: 8F must
recheck the head/owner/status inside its atomic effect transaction under the same lock.
Public Team Lock projection/history is unchanged; adding UUIDs to new snapshots is a
future parser-boundary concern, never a historical rewrite.

## Validation And Reproduction

Local commands (Windows, disposable V1 fixture isolation in unit runner):

```powershell
.\.venv-api\Scripts\python.exe tools/run_unit_tests.py
.\.venv-api\Scripts\python.exe -m compileall -q -x '[\\/](\.venv[^\\/]*|\.git|node_modules)[\\/]' .
.\.venv-api\Scripts\python.exe tools/generate_supabase_v2_bootstrap.py
git diff --check
```

Set `POKEAPP_DOTNET` to a .NET 9 SDK executable if not on PATH. This environment uses
a temporary Microsoft SDK 9.0.318 ZIP verified against the release SHA512. Probe
outputs live under ignored `.dotnet-sdk/identity-probe`; no tracked bridge binaries
are replaced or deployed. Source builds must be regenerated when V2 parser is wired.

Real PostgreSQL 17.11 validator: loopback only, database `pokeapp_v2_validation*`,
explicit `--allow-destructive-reset`. Run `tools/validate_supabase_v2_schema.py` with
`--build-source migrations`, then `--build-source bootstrap`. Both run all previous
Auth/RLS/Team Lock/shop rollback/concurrency checks and shared identity fixtures.

Coverage mapping: I01-03 actual PK3/4/5; I04-09/17-18 synthetic mutation/evolution;
I10-16/19-24 pure assignment/missing/return/clones; I25-31 legacy/link/target/privacy;
I32-35 sequence/reparse/idempotence; I36 PostgreSQL simultaneous initial allocation.
Local/remote shared fixtures also test same-head competing different saves, DB uniqueness,
real role isolation, stale-target rejection, flags and scoped cleanup. See final results below.

Staging command, ONLY after implementation commit/push and exact project verification:

```powershell
.\.venv-api\Scripts\python.exe tools/validate_supabase_v2_pokemon_identity.py --env-file .env.supabase-v2-rls.local --allow-staging-writes
```

Exact allowed project: `https://uwleqeuzsveqlugugzba.supabase.co` (Pokeapp 2.0).
Apply ONLY 023 incrementally, never bootstrap/reset. Fixtures use a unique
`phase8f0_validation_<uuid>` prefix, draft season, synthetic JSON and temporary Auth
users. No Storage upload, real trainer or raw save is needed. Cleanup removes all
associated identity/flag/parser/save/player/season/trainer/Auth fixtures and verifies
absence. Independent MCP inspection must confirm zero residue and SQL definitions.

## Observed Local Results

- Full suite: **295 PASS, zero failures/skips** (255 retained + 40 new identity tests).
- PKHeX probe: actual PK3/PK4/PK5 exports, mutable changes and two evolutions PASS.
- PostgreSQL 17.11 migrations build: PASS, including 19 identity fixture checks.
- PostgreSQL 17.11 bootstrap build: PASS, including the same 19 checks.
- Schema-only dumps including grants: identical after excluding pg_dump's random
  `\\restrict`/`\\unrestrict` client safety tokens. No schema differences hidden.
- Identity races: 4 workers allocating the same first save return ONE receipt;
  2 different saves on the same predecessor produce ONE CAS winner.
- All fixture cleanup PASS in both local builds; existing SQL/RLS/shop regressions PASS.
- compileall, generated bootstrap equality and git diff --check: PASS.
- Warnings observed: existing Streamlit bare-runtime/session/cache warnings,
  Starlette/httpx deprecation and Git LF/CRLF notices; not suppressed as test failures.
  The probe's initial MSBuild output-path warning was fixed using Directory.Build.props.

Remote: MCP `get_project_url` and `list_migrations` failed before any remote write:
`OAuth token refresh failed: Failed to parse server response`. Reconnect supabase-v2,
then verify the exact target, apply only committed 023 and run the prepared validator.
No remote fixture has been created by this task and remote PASS is NOT claimed.
Until that gate passes, overall 8F.0 remains PARTIAL, not DONE.

## Progress And Next

Weighted global estimate: ~52% before, ~54% now with local implementation (+2 points),
~55% after the full local+staging gate. This is an estimate, not a measured burn-down.
This is identity infrastructure for API safety AND future Companion cross-save actions,
not a phase-count percentage. Remaining work still includes 8F/remaining API, parser
boundary, React/Cloudflare, data migration, shadow, staging/performance/cutover and full
Launcher/Companion automation with safe physical save operations.

Next: resume Phase 8F using current authoritative pokemon_entity_id or explicit
AMBIGUOUS rejection. Do NOT implement redemption in this task. V1, Streamlit, economy,
Discord, UI, legacy physical write operations and historical Team Locks remain intact.
