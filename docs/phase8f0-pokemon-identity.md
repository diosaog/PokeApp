# Phase 8F.0: Authoritative Pokemon Individual Identity

Date: 2026-09-23. Starting checkpoint: `main`, `7207014`, origin divergence 0/0.
Status: DONE local + V2 staging (2026-09-23). Phase 8F is unblocked, NOT implemented.
Staging-only resume started at `158fc1b`, `main`, origin divergence 0/0.
Implementation commit: `9aef9ac feat: add authoritative Pokemon identity and reconciliation`,
pushed to origin/main before any attempted staging SQL. No redemption implementation.
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
outputs live under ignored `.dotnet-sdk/identity-probe`; no manual binary replacement
or deployment was performed. Existing repository CI rebuilt the Linux publish binary
after the source push (`27f1865 Bridge: rebuild linux publish binary [skip ci]`).
That generated commit is preserved/integrated; no write-operation source was changed.

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

## Historical Staging Resume Blocker

The following describes the earlier blocked session, before the successful resume
below. It is not the current remote state.

No local validation was repeated after the user's request to resume staging only.
Initial MCP calls failed with `OAuth token refresh failed: Failed to parse server response`.
Default CLI OAuth registration also failed because the server rejected advertised
scopes. A login with explicit `organizations:read,projects:read,database:read,database:write`
completed successfully after the user authorized it. No API keys were changed/exposed.

The original conversation's tool client still returned `OAuth authorization required`
after the user restarted the connector. A fresh, ephemeral MCP client DID confirm:

- exact project URL: `https://uwleqeuzsveqlugugzba.supabase.co`;
- latest migration: `022_promotional_purchase_api`, version `20260922174842`;
- independent service REST read access works; that probe performed no writes.

However, its read-only SQL catalog preflight was refused by the client:
`MCP tool call requires approval, but approval policy is never`.
No attempt was made to bypass that gate. **023 was NOT applied.** Catalog counts,
remote function checksums, RI01-RI12 execution and independent cleanup verification
remain pending. No remote fixture/Auth user/raw save was created by this task.

## Staging Closure: 2026-09-23

The restored direct MCP connection confirmed **Pokeapp 2.0**, exactly
`https://uwleqeuzsveqlugugzba.supabase.co`. Git matched the approved resume:
`main`, HEAD `158fc1bf49aa369801d71c5c2a64c63f41e62327`, upstream `origin/main`,
0/0 divergence, no tracked modifications. The protected untracked guide remained
untouched. No local tests, bridge build or implementation were repeated.

SQL preflight found 32 public tables, all 32 with RLS, 37 views, no identity tables
and latest migration `022_promotional_purchase_api` / `20260922174842`.
Only the exact SQL read from `git show HEAD:supabase/v2/migrations/023_pokemon_identity.sql`
was submitted to MCP `apply_migration`; success was returned. The recorded migration
is **023_pokemon_identity / 20260923165532**. No bootstrap, reset or migration edit.
Remote PostgreSQL reports 17.6. Do NOT apply 023 a second time on this project.

### Remote Validation

The unchanged prepared command above completed with exit 0 and:
`RESULT ok checks=19; Auth cleanup PASS`.
Authoritative successful run: `phase8f0_validation_b9d33942af06432e820972d67dcb9f19`.

| Check | Observed result |
| --- | --- |
| RI01 | PASS: backend creates three distinct entities, including two clones |
| RI02 | PASS: observations and entity/location bindings persisted |
| RI03 | PASS: same-save replay returns the same receipt |
| RI04 | PASS: owner/admin read permitted private rows |
| RI05 | PASS: anon reads denied |
| RI06 | PASS: other trainer sees no private identity evidence |
| RI07 | PASS: direct browser writes and RPC denied, including admin |
| RI08 | PASS: service-role backend write path works |
| RI09 | PASS: unique legacy flag linked without copying its value |
| RI10 | PASS: colliding legacy flag retained and unresolved |
| RI11 | PASS: four concurrent workers, one initial revision/receipt |
| RI12 | PASS: all fixture rows removed and verified; Auth cleanup also PASS |

The other seven reported checks cover single-clone flags/uniqueness, observation
uniqueness, unchanged reparse, movement/evolution/ambiguity/stale-target rejection,
missing/return, out-of-order capture rejection and two competing saves producing
one CAS winner with no partial loser. Ambiguous observations have no arbitrary
entity binding. Only synthetic JSON was used, with no raw-save bytes or Storage upload.

**Intermittent transport failure, not hidden:** five staging attempts were made.
The first (`31f892e26e954775bdc1220912cb675d`) stopped before RI01 with
`PersistenceError`; the third (`aa5fae1a8a244b51ae651e7d944b79fd`) stopped during
the distinct-save race. Their underlying causes were not captured. Both cleaned up.
A diagnostic-only invocation (`012fa1a214d24cbf9ebb1aa6efea7d2a`) passed all 19;
another (`c0348ea83fdc444381bd792c0d3f8a8a`) captured `load_context` failing with
`httpx.ReadError: [WinError 10035]` during concurrent socket reads, then cleaned up.
The final invocation above used the original command without instrumentation and
passed all 19. No method semantics, SQL, assertions, worker counts or dependencies
were changed; diagnostic wrappers only printed redacted exception causes and re-raised.
Do not claim that the earlier failures were definitely schema-cache errors or that
transport reliability has been fixed. Environment: Windows, Python 3.14.3,
supabase/postgrest 2.27.2, httpx 0.28.1, httpcore 1.0.9, h2 4.4.1.

### Independent Security And Cleanup

MCP catalog checks confirm **36 public tables / 36 RLS / 37 unchanged views**.
Both new functions are SECURITY INVOKER, `search_path=''`, EXECUTE for service_role
and SQL owner only; PUBLIC, anon and authenticated cannot execute them.

| Function | Remote prosrc MD5 (matches committed/local contract) |
| --- | --- |
| commit_pokemon_identity | `adf1eb39d43f2daaab1350a58c016b02` |
| check_pokemon_entity_flag | `c1b2d4a8db2294ba43362d187bdc919d` |

All four new tables grant authenticated SELECT only, constrained by the existing
owner/admin helpers. Anon has no read/write grant; authenticated has no
INSERT/UPDATE/DELETE/TRUNCATE grant. Service-role writes remain available.
No new public projection exposes identity evidence. The existing 13 invoker views
and 24 explicit public definer projections retain their definitions/options.

Before/after aggregate checksums, independently queried through MCP:

| Surface | Identical MD5 before and after |
| --- | --- |
| 37 view definitions | `d4da4cee7449e34f3ab16eeb74819c3d` |
| View options | `f2e46b68fdda3bd9634844906522fbda` |
| All pre-023 public function definitions | `306de6e6dbcb892857f1a6b22f5aecff` |
| Storage bucket records | `a1bad2c31b4a666ab2a70cd1519f5a69` |

Independent SQL after the final run found zero `phase8f0_validation_` Auth users,
trainers, seasons or save keys. Full counts were zero for seasons, season_players,
save_files, parsed_saves, pokemon_flags, all four identity tables and Auth users.
Purchases, redemptions, coin_transactions, activity_events, team_locks, Auth
identities and sessions were also zero. The pre-existing 10 trainers remain;
Storage still has 3 objects and identical bucket records. Baseline counts for the
pre-existing fixture-related tables were restored. No real trainer/save was used.

Security Advisor was **not warning-free**: it reports the existing 24 public
definer projections, the existing mutable search_path on `set_updated_at`, and
three authenticated identity-helper SECURITY DEFINER functions. Public projections
and helpers are documented existing design exceptions, not new permissions from
023. The mutable-path warning is a retained hardening concern, not fixed here.
The matching view/function baselines confirm that none was introduced by 023.
References: [definer views](https://supabase.com/docs/guides/database/database-linter?lint=0010_security_definer_view),
[mutable search_path](https://supabase.com/docs/guides/database/database-linter?lint=0011_function_search_path_mutable),
[authenticated definer functions](https://supabase.com/docs/guides/database/database-linter?lint=0029_authenticated_security_definer_function_executable).
Log inspection was unavailable with the current OAuth scope (`Insufficient scope`);
no authorization bypass or key change was attempted.

The closure change is documentation-only. Migrations 001-023, validators, bridge,
runtime, V1 and redemption remain unchanged. Protected guide SHA256 remains
`6FA3E82B6D3FDF82ACB0E95DA6715397574ACE7A134F68C2F69864909F2B934E`.
Closure checks: `git diff --check` PASS (existing LF/CRLF notices retained);
`git diff --exit-code -- . ':(exclude)docs/**'` PASS. Only five documentation
files changed; the original 295-test local result was not rerun or replaced.

## Progress And Next

Weighted global estimate: ~54% before this staging-only resume, **~55% after**
(+1 point). Local implementation previously moved ~52% to ~54%.
This is an estimate, not a measured burn-down.
This is identity infrastructure for API safety AND future Companion cross-save actions,
not a phase-count percentage. Remaining work still includes 8F/remaining API, parser
boundary, React/Cloudflare, data migration, shadow, staging/performance/cutover and full
Launcher/Companion automation with safe physical save operations.

8F.0 is DONE and Phase 8F is unblocked. Next: resume Phase 8F using current
authoritative pokemon_entity_id or explicit AMBIGUOUS rejection.
Do NOT implement redemption in this task. V1, Streamlit, economy,
Discord, UI, legacy physical write operations and historical Team Locks remain intact.
