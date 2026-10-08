# PokeApp 2.0 Project Checkpoint

Checkpoint reconciled: 2026-10-08. This file is the project index and historical
milestone record; it does not maintain a second live phase-status ledger.

## Current project position

- Active phase: **11 — real V1 → V2 data migration**, authorized after final 10.5.
  [Single live record](work-in-progress/phase11-live-handoff.md),
  [readiness checkpoint](phase11-readiness-report.md). Current execution state and
  exact resume step are maintained there. No cutover or Phase 12 is included.
- Latest completed phase: **10.5 — Functional product alignment and repair, DONE**.
  [Approved contract](phase10-5-functional-alignment.md),
  [closed execution record](work-in-progress/phase10-5-live-handoff.md).
  Owner authorized implementation on 2026-09-29 after the functional knowledge export.
  [Final alignment/closure report](phase10-5-completion-report.md): A–M and all
  seven final areas delivered, source `eb4e402`, forward 041, verified local/public
  evidence and zero owner business-data residue. At that closure Phase 11 was
  **READY FOR REVIEW**; the subsequent owner instruction authorizes its execution.
  M's intermittent hosted 503
  availability candidate remains documented; no root-cause fix is claimed.
  [M performance guard](phase10-5m-completion-report.md) remains delivered.
  [L observed badges and in-game Champion progress](phase10-5l-completion-report.md) remains delivered.
  [K public competitive scouting](phase10-5k-completion-report.md) remains delivered.
  [J Admin humanization](phase10-5j-completion-report.md) remains delivered.
  [I Shop and economy alignment](phase10-5i-completion-report.md) remains delivered.
  [H Team Lock warnings and Team Preview](phase10-5h-completion-report.md) remains delivered.
  [G participant-owned wipe revivals](phase10-5g-completion-report.md) remains delivered.
  [F final championship and frozen Hall](phase10-5f-completion-report.md) remains delivered.
  [E observed progress and initial divisions](phase10-5e-completion-report.md) remains delivered.
  [D daily sporting ranking](phase10-5d-completion-report.md) remains delivered.
  Consult the live record for deployment and the active package.

- Previous closed phase: **10 - React / public Cloudflare + Railway, DONE**.
  [Contract](phase10-react-cloudflare.md), [delivery report](phase10-completion-report.md),
  [public evidence](phase10-public-evidence.json),
  [closed handoff](work-in-progress/phase10-live-handoff.md).
- Backend 8L and parser/Launcher foundation 9 remain closed; no replay or restart.
- Weighted complete-project estimate: **~80%**, from ~79% after verified public
  hosting/auth/integration. This is not final release or V1/V2 cutover.
- V1/Streamlit remains legacy/fallback. V2 public staging is available for inspection.
  Cloud save ingestion/current-state promotion, physical save operations, final
  Launcher distribution, onboarding/roles and release polish remain later work.
- Phase 11 entry passed after owner authorization; its live record controls
  readiness, migration progress and blockers. Phase 12 and cutover are not started.
- Preserve **OWNER_TEMP_STAGING_AUTH / OWNER_TEMP_STAGING_ADMIN** for current review.
  **TEMP_STAGING_AUTH_MUST_BE_REMOVED_OR_RESET_BEFORE_RELEASE** includes role review
  and definitive secure onboarding. Do not copy a temporary staging policy to production.

Read [continuity](AI/PokeApp_Multi_AI_Continuity_Protocol.md) and
[master protocol](PokeApp_2.0_Protocolo_Maestro_MultiIA.md) before future work.
The closed handoff records existing hosting resources, owner exception, manual
season guard and resumption checks. Do not recreate infrastructure or reapply SQL.

## Historical delivery milestones — not current execution state

The following counts, PASS results, next-step notes and remote versions belong to
their named milestones. They are retained as evidence, not fresh verification of
the current repository or remote database. Current project position is indexed above.

### 2026-10-05 - Phase 10.5G CLOSED

Participants manage their own live revived-after-wipe count with JWT ownership,
CAS, idempotency and atomic audit. Existing +2 adjusted deaths / -0.4 points each,
unknown save evidence and frozen E/day/F/Hall remain safe. No physical or purchased
revive change. GENERAL has the human personal control. Source `848e7b0`,
038=`20261004222029` once, Railway then Cloudflare. Full 694 Python, 22 React, 34 Edge,
nine-group real-PG G and inherited 026-030/B-F closure PASS; exact 49-table restore,
12,175-line four-build parity. Local environment interruptions and final successful
reruns are recorded separately. Public 37 API requests/22 browser visits PASS;
55 scoped tables preserved, zero business writes and zero added/removed Advisor
ERROR/WARN. [G report](phase10-5g-completion-report.md) has exact sources, delivery,
security and limitations. STOP after G; H requires explicit continuation. Phase 11
NOT READY / NOT STARTED.

### 2026-10-03 - Phase 10.5F CLOSED

Champion derives from exact accumulated official points. Two tied leaders require
audited external BO3; three use frozen authoritative adjusted deaths. Residual/4+
ties remain unresolved. Finalist stays null pending owner decision without blocking
a proven title. Finish freezes title/points/historical Team Lock; separate archive
creates League Hall from that certificate. Existing history and modern Cup remain.
Source `6b46666` pushed before 037=`20261003121543`, Railway then Cloudflare. 680
Python, 14 React, 28 Edge, F and inherited real-PG gates PASS; 12,046-line four-build
schema/grants/ownership parity. Public 29 API requests/22 browser visits PASS;
55-table scoped preservation and zero new Advisor ERROR/WARN. Positive mutations
were local only. Exact source/deployments/security/limitations in the [F report](phase10-5f-completion-report.md).
Stop here; no automatic G and no Phase 11. Phase 11 remains NOT READY.

### 2026-10-03 - Phase 10.5E CLOSED

Observed save progress distinguishes unknown from zero; J1 requires Medal 2 and
authoritative adjusted deaths before server-derived A/B with configured capacities
and boundary-only audited tie resolution. Existing manual seasons/history remain
unchanged. Migration 036 was previously applied once; no replay. Final source
`90a31fc` also recovers one dropped response for explicitly read-only frontend calls.
670 Python PASS; unchanged-source React/browser/parser/real-PG/rebuild gates verified.
Final public 21 API checks, 22 browser visits and 24 concurrent reads PASS; independent
53-table scoped equality, 28 unchanged migration records and zero new Advisor
ERROR/WARN. Full cloud save ingestion remains future work. F is the next authorized
atomic package, unstarted; Phase 11 NOT READY. Exact evidence/deployments are in
the [E report](phase10-5e-completion-report.md) and single live handoff.

### 2026-09-29 - Phase 10 public delivery CLOSED

Existing Railway FastAPI and Cloudflare React verified with actual PIN/JWT/API/
PostgREST. Anto retains his identity/PIN and explicitly authorized staging admin;
backend admin create/read/rename and React administration PASS. Final frontend
`3c83a16` corrects long-name wrapping, with nine browser tests PASS. Public business
and mutation gates are retained from earlier fixture runs; final read-only public
browser PASS covers eleven screens at desktop/mobile. Complementary gates are
explicit: no failed all-in-one run is relabelled PASS. Owner-created active/manual
seasons are preserved. Independent final 52-table comparison, zero fixture prefix
residue, history and Advisor delta PASS. 001-032 unchanged, no 033 or cutover.
Public URLs/IDs, warnings and all failed attempts are in the report/evidence.
Progress ~79% -> ~80%; Phase 11 not started.

### 2026-09-28 - Phase 10 local React/API delivery; phase remains open

Published implementation `512d239`, `c940b33`, `7a827ee`: eleven React screens,
typed frontend reads, explicit CORS, critical mutation integration and Workers
assets delivery. 565 Python, 11 React and eight browser tests PASS with source
provenance in the [report](phase10-completion-report.md) and
[evidence](phase10-validation-evidence.json). Browser APIs use synthetic fixtures;
real V2 checks were read-only. No migrations or staging writes. Public deployment
and real authenticated environment validation remain pending account/API setup.
Progress ~73% -> ~79%; Phase 10 is not DONE. Continue from its live handoff.

### 2026-09-28 — Phase 9 local parser / Launcher foundation DONE

`5474460` establishes the isolated read-only parser; `f2158ed` delivers local sync,
auth/session, queue, backup preparation, CLI and Windows read-error handling.
543 Python tests (511 + 32), 24 .NET assertions, six real binary/Launcher integration
groups and static checks pass on published `f2158ed`. Neutral DTOs reuse typed 023
identity evidence but never invent CaptureOrder or promote competitive state.
No endpoints/migration 033/staging work; 001–032 and backend/V1 unchanged.
Local sync is explicitly observed-state journaling, not a cloud upload. Progress
~70% -> ~73%. [Report](phase9-completion-report.md) and [evidence](phase9-validation-evidence.json).

### 2026-09-28 - 8L DONE; approved Phase 8 backend CLOSED

CLI/linked SQL verified exact V2 project and all 22 original migration records.
Canonical custom layout preserved; recorded Management API applied 031 once as
`20260928110301` and the necessary 032 duplicate-index completion as `20260928111840`.
All original history records and 001-031 source unchanged. **Do not reapply.**

A8L-01 correction `39343ea`; final schema/fixture correction `a87d395`, pushed
before 032 and final real run `phase8l_validation_3e013eb7f78749ccbed2b792a1b5b118` (exit 0). Twenty Cup/integrated groups,
L00-L08/ten races and focused 030 regression PASS. All 52 public/Auth/Storage
counts/full-row hashes restored; catalog/security/history unchanged by fixtures.
Security Advisor 24 ERROR / 4 WARN / 9 INFO; combined 24 ERROR / 4 WARN / 122 INFO;
zero new ERROR/WARN. Intermediate duplicate-index WARN removed by 032.

511 unit tests, 001-032/bootstrap double rebuild, 10,507-line parity, Cup flows,
races/nine rollback boundaries/all-public cleanup PASS. The report preserves the
failed fixture attempt and both successful real runs. [Delivery report](phase8l-completion-report.md)
and [sanitized evidence](phase8l-staging-evidence.json). No public API deployment.
Progress ~68% -> ~70%; Phase 9 remains unstarted.

### 2026-09-24 — 8K.1 DONE local + real V2 staging

Phase 8K.1 implements the approved manual Discord-result contract in additive 030.
Any eligible enabled participant records/corrects; PokeApp has no voting engine or
Discord integration. Typed sanctions, append-only correction and browser judicial
write hardening are in [the contract](phase8k1-trials-sanctions.md); delivery gates
are tracked in [the completion report](phase8k1-completion-report.md).
466 unit tests, 16 exact rollback boundaries, required concurrency, relevant
regressions, schema/grants/ownership parity (9,690 lines) and real staging PASS.
Independent cleanup: all 48 public/Auth/Storage baseline table contents unchanged.
Advisor: 24 ERROR / 4 WARN / 5 INFO; no new ERROR/WARN, one expected counter INFO.
Implementation `9e9ea65` and ACL follow-up `20f0362` pushed before their deployments.
Staging 030 schema=`20260924102756`; narrow 030 ACL completion=`20260924103256`.
Final source 030 contains both. Do not replay 029 or either 030 deployment, or run
reset/bootstrap on staging. Overall progress at that milestone ~66% → ~68%;
Cup implementation had not started at that milestone.

Phase 8J adds explicit finish/archive/logical discard in 029. No V1/runtime change,
automatic 12-coin bonus, Cup winner inference or Phase 9. [Contract](phase8j-season-finalization.md)
and [current gates](phase8j-completion-report.md). Staging 029 is applied as
`20260923232516`; 431 unit tests, migrations/bootstrap parity (8,987 lines),
19 new remote groups, previous regressions and independent zero residue PASS.
Implementation `5f77a48`, validator follow-up `d46d8a7`, both pushed. Do not reapply
029 or run reset/bootstrap on staging. Estimated overall progress ~64% -> ~66%.

Phase 8I adds the participant-status boundary in 028. Three permanent statuses,
scheduled-day reconciliation, typed historical cutoff, robbery cycle adjustment,
admin JWT/CAS/receipts. [Contract](phase8i-participant-status.md) and
[current delivery gates](phase8i-completion-report.md). 001-027 remain unchanged.
8I and 8J gates are closed. Cup Hall delivery subsequently closed in 8L, as
recorded above; 8K.1 implements Juicios/sanctions.

Phase 8H implements approved D4=A/D5=A/D6=A in additive 027: open/results/cancel,
atomic close/rewards/movement/next day and restricted revisioned correction.
[Contract](phase8h-matchday-operations.md) and [delivery gates](phase8h-completion-report.md).
8G.1/8H remain DONE local + staging. D8 remains deferred.
No Streamlit/V1 change, deployment, dual-write or cutover.

Base HEAD before original checkpoint documentation:
`f6d8fc179f8c9e021bdf6b4fa1e2687e2d7e8b2a`

The original commit containing this file was the functional freeze checkpoint.
Later architecture checkpoints are tracked below.

Architecture milestones retained from earlier checkpoints:

- Fase 3 closed: dependency-free domain contracts in `app/domain/`.
- Fase 4 closed: pure domain services in `app/domain/services/`.
- Fase 5 closed: repository protocols, legacy implementations, mappers and
  in-memory fakes in `app/repositories/`.
- Fase 6 closed: Supabase V2 greenfield SQL schema in `supabase/v2/migrations`
  with reset/dev docs and static schema tests.
- Fase 6.1 closed: schema V2 executed against real PostgreSQL 17.11, including
  reset/rebuild and fixture introspection.
- Fase 7 closed: Supabase V2 RLS/security layer with identity helpers, safe
  projections, private storage policies and real PostgreSQL RLS validation.
- Fase 7.1 closed: real Supabase staging validator passed against
  `Pokeapp 2.0`.
- Fase 7.2 closed: `013_storage_policies` is Cloud-safe, idempotent and already
  applied in the real Supabase staging project.
- Fase 8A.1 closed: PIN UX to Supabase Auth identity bridge core.
- Fase 8B closed: isolated FastAPI skeleton for health, PIN login, refresh and
  `/v1/me` bearer identity lookup.
- Fase 8B-H closed: real SDK-compatible auth mapping, UUID/slug lookup and
  globally enabled mutation guard; `/v1/me` remains readable when disabled.
- Fase 8C DONE local + Supabase V2 staging validated: self-service Team Lock
  API, authoritative ParsedSave snapshots and atomic lock/activity RPC in 019.
- Runtime remains Streamlit legacy through wrappers.
- Phase 8D.0 DONE local + staging: 020 explicit same-season pointer, inclusive
  Store Ban windows, five remote check groups and cleanup PASS.
- Phase 8D normal purchase DONE local + staging: 021 atomic purchase/ledger/event,
  idempotency, promotion eligibility and wallet serialization. 29 remote checks
  (5 context + R01-R24) and cleanup PASS.
  Historical blocker resolved; [contract and evidence](phase8d-purchases.md).
- Phase 8E DONE local + staging: 022 atomic promotional purchase, wallet-before-stock
  locking, unique trainer claim and historical idempotent receipt. 27 real checks,
  29 8D regression checks and cleanup PASS. [Report](phase8e-completion-report.md).
  [Contract and validation](phase8e-promotional-purchases.md). The next step at that
  milestone was 8F redemption/effects, subsequently delivered below.
- Historical Phase 8F audit BLOCKED: all four implemented redemption effects require Pokemon
  identity; existing fingerprints collide for distinct individuals and normalized
  DTO IDs can be empty. No safe legacy target-free use flow found. No 023/API or
  staging work. [Evidence and effect map](phase8f-redemption-effects.md).
- Phase 8F.0 adds authoritative entities/observations, read-only PKHeX evidence,
  conservative reconciliation and safe legacy flag links in 023. Local validation
  and staging completion are tracked in [identity contract](phase8f0-pokemon-identity.md).
  No redemption endpoint, runtime connection, dual-write or physical save modification.
  295 tests PASS, PostgreSQL migrations/bootstrap PASS (19 identity checks each),
  schema dumps including grants identical. Staging-only resume from `158fc1b`
  applied exact committed 023 via MCP as `20260923165532`: 19 remote checks PASS,
  including RI01-RI12, both concurrency cases and independently verified cleanup.
  36/36 public tables have RLS; 37 views and all pre-existing functions are unchanged.
  Both new function checksums/grants match the contract. Earlier failed attempts
  and an intermittent Windows HTTP `ReadError / WinError 10035` are recorded in the
  identity report, not hidden; transport reliability was not changed or fixed.
  Implementation `9aef9ac` remains unchanged; local tests/bridge were not repeated.
  Existing Advisor findings are documented, not falsely reported as cleared.

## Historical validation ledger — 8I and earlier

8I DONE: 403 unit tests, compileall/diff-check, migrations/bootstrap,
8,268-line schema parity, 24 shared groups + eight exact rollback injections,
all previous regressions. Implementation `baecb8a` pushed. ONLY committed 028
applied to V2 as `20260923220301`. Real JWT/API/PostgREST: 24 participant groups,
027 matchdays 20, 026 setup 17, Team Lock 13, purchases 29, redemption/robbery 17
PASS. Independent SQL confirms zero DB/Auth residue, 40/40 RLS, 37 views (only
the two intended boundary projections changed), eight function checksums/grants
and unchanged real trainer/catalog/Storage fingerprints. Advisor unchanged:
24 existing ERROR, 4 WARN, 4 backend-only INFO; no global-security-clean claim.
Do not reapply 028 or reset/bootstrap staging. Estimated project progress ~62% -> ~64%.
Exact run ID, commands and evidence: [8I report](phase8i-completion-report.md).

Previous 8H checkpoint: 376 unit tests PASS (343 baseline + 33 focused tests). SQL migrations/bootstrap
PASS, 8,076-line schema parity, 20 groups and 17 exact rollback points. Committed
027 was applied after push `bef5c4d` as `20260923210625`. Real JWT/API/PostgREST:
20 8H groups, 17 setup groups, Team Lock 13, purchases 29, redemption/robbery 17
PASS. Independent SQL verifies zero DB/Auth residue, 40/40 RLS, 37 unchanged views,
restricted function grants/checksums and unchanged real trainer/catalog/Storage.
Advisor existing findings remain; only one expected backend no-policy INFO added.
Do not repeat 027, bootstrap or reset on staging. Global estimate ~59% -> ~62%.

Previous completed checkpoint:

Phase 8G.1 core setup/admin implementation follows the completed
[8G audit](phase8g-season-league-admin-audit.md) at `089b8d6` and approved D1=A,
D2=A, D3=B. It adds migration 026, ten `/v1/admin` routes, durable revisions/
receipts, first-round preparation and readiness-gated activation. DONE: 343 tests
PASS (318 preserved + 25 new); PostgreSQL migrations/bootstrap schema parity;
17 setup groups and nine exact-state rollback points. Staging 026 was applied
as `20260923192300`, after implementation push `178cc41`; validator fix `c6afcde`
distinguishes malformed 422 requests from business conflicts. The completed run
passed 17 setup groups, Team Lock 13 checks, purchase/context 29 checks and
redemption/robbery 17 groups. Independent SQL confirms zero fixture/Auth residue,
39/39 public tables with RLS, 37 views and unchanged real trainer/catalog/Storage
fingerprints. Existing Advisor findings remain documented, not cleared.
Weighted complete-project estimate at that checkpoint: about 57% -> 59%.

Phase 8F.1 adds the approved canonical reward-only voucher and complete atomic
robbery/cycle/gift handling in 025, staged as `20260923180416` after `4cf21bf`.
318 tests PASS; migrations/bootstrap schemas identical; staging robbery 17 groups
and shield/revive regression 19 groups PASS. Independent cleanup zero residue.
Validator transport isolation follow-up `d356bc1` also pushed. Local/staging gates are tracked in the
[full contract](phase8f1-robbery-voucher.md) and [delivery](phase8f-completion-report.md).
Runtime remains legacy Streamlit/V1; no physical save automation or API deployment.

Previous checkpoint (024, retained as evidence): Phase 8F was PARTIAL.
024 + self-service redemption API implement Blindar/Revivir,
authoritative Entity targets, private events, atomic used/internal-applied and
physical pending for revive. No Store Ban/current-day/lifecycle-active requirement.
Robbery AND its shield voucher remain unsupported: no canonical V2 gift ShopItem
code exists; none is invented. No physical operations or runtime changes.
[Current contract and remaining blocker](phase8f-redemption-effects.md).
Implementation `a36b713` pushed before 024 staging version `20260923172957`.
311 tests PASS, PostgreSQL migrations/bootstrap PASS, 19 remote check groups PASS,
independent zero-residue cleanup PASS. RF12/voucher and RF21-RF27/theft not implemented.
36/36 RLS, 37 preserved views, RPC checksum matched. No transport failure this run;
no claim that prior intermittency is fixed. [Delivery](phase8f-completion-report.md).

PokeApp 2.0 has reached functional freeze.

Closed phases recorded at the earlier 8E milestone (not an exhaustive current list):

- Fase 0: base green, initial docs and module inventory.
- Fase 1: visual Streamlit reference mostly closed.
- Fase 2.1: immutable round snapshots and critical permissions.
- Fase 2.2: definitive configurable season for Streamlit A/B.
- Fase 2.3: TrainerStatus/TrainerFlags and Admin centralization.
- Fase 2.4: season lifecycle, SeasonArchive and stable Hall of Fame.
- Fase 2.5: ActivityEvents and NotificationView.
- Fase 2.6: final audit, backlog, checkpoint and functional freeze.
- Fase 3: domain contracts.
- Fase 4: pure domain services.
- Fase 5: repositories.
- Fase 6: Supabase V2 greenfield schema.
- Fase 6.1: real Postgres validation of Supabase V2 SQL.
- Fase 7: RLS and security.
- Fase 7.1: real Supabase staging validation complete; full JWT/PostgREST/
  Storage validator passed with `RESULT ok checks=13`.
- Fase 7.2: Supabase Storage Cloud compatibility fix completed and applied.
- Fase 8A.1: PIN auth bridge core.
- Fase 8B: FastAPI skeleton, JWT verification and PIN-login rate limiting.
- Fase 8B-H: authentication hardening. DONE.
- Fase 8C: Team Lock V2 API mutation. DONE + Supabase V2 staging validated.
- Fase 8D.0: current matchday and Store Ban contract. DONE local + staging.
- Fase 8D: atomic normal purchase. DONE local + staging.
- Fase 8E: atomic promotional purchase. DONE local + staging.

Historical staging validation (Phase 7, not rerun in this task):

- `py -m compileall -q .`
- `py -m unittest discover -s tests`
- `git diff --check`
- `py tools\validate_supabase_v2_rls.py` passed against real staging with
  `RESULT ok checks=13`.

Phase 8E baseline validation: 255 tests passed, zero failed/skipped, using
`.venv-api\Scripts\python.exe tools/run_unit_tests.py`. Compileall and diff-check
passed. PostgreSQL 17.11 local passed both migrations 001-022 and bootstrap,
including Store Ban, purchase receipt, promotions, rollback, roles and concurrency.
Phase 8E adds seven multi-connection stock/wallet/idempotency race scenarios.
The runner uses disposable SQLite data, not V1. See
[Phase 8C report](phase8c-team-lock.md) for exact commands and environment.

Remote 8C: migration 019 applied incrementally to `uwleqeuzsveqlugugzba`
(`Pokeapp 2.0` staging); real Auth/PostgREST + in-process FastAPI validator passed
13 checks. Owner/admin private reads, other/public reads, backend-only writes,
replacement and dedupe passed. All temporary DB/Auth fixtures were removed.
Forced post-write rollback remains locally validated, not injected into staging.

## What Works in the Legacy Runtime

- Trainers log in with a PIN and see their own private data.
- Saves can be uploaded, selected and parsed through the current bridge.
- Entrenadores shows current team, PC/boxes, Pokemon detail, inventory and own
  team lock controls.
- Team Preview uses fixed teams when available and respects private/public data.
- Liga A/B works with configurable players, jornada count, division sizes,
  movement count, points and coins.
- Closed jornadas freeze official standings, points, coins and penalty metadata
  through round snapshots.
- TrainerStatus supports active, retired, abandoned and disqualified states.
- TrainerFlags tracks robbed state separately from competitive status.
- Tienda supports catalog, purchases, redemptions, promotions and stock.
- Team locks are stored per jornada and can be late.
- ActivityEvents feed concise notifications for saves, purchases and team locks.
- Season lifecycle can finish, archive, prepare new active season or discard.
- SeasonArchive freezes final season data and public champion team.
- Hall of Fame prefers archived entries, so final winners do not drift after
  archive.
- Copa works as separate legacy tournament flows.
- Juicios works as separate case/penalty flow.
- `Temporada/Admin` is the central back office for official season/Liga/admin
  state.

## Current Architecture

PokeApp is still a Streamlit app.

Entry:

- `main.py`

Important layers:

- `app/domain/*`: dependency-free contracts.
- `app/domain/services/*`: pure business decisions.
- `app/auth/*`: PIN UX to Supabase Auth identity bridge and provisioning core.
- `app/api/*`: isolated V2 FastAPI transport and Phase 8 routes; not a runtime cutover.
- `app/repositories/*`: protocols, mappers, legacy repositories and in-memory
  fakes.
- `app/application/*`: first small use cases coordinating repositories and
  domain services.
- `supabase/v2/migrations/*`: greenfield SQL-first Supabase V2 schema.
- `supabase/v2/reset_dev.sql`: destructive V2 development reset; never run on the
  pinned staging project during an incremental phase delivery.
- `storage.py`: Supabase/SQLite/settings facade.
- `utils.py`: roster/session/save helpers and static user registry.
- `app/liga/*`: ranking, state, snapshots, rewards, divisions and UI.
- `app/season/*`: config, validation, lifecycle and archives.
- `app/entrenadores/*`: trainer page, boxes, snapshots, flags and inventory.
- `app/tienda/*`: catalog, promotions, purchase/redeem and money.
- `app/copa/*`: cup modes.
- `app/juicios/*`: cases, forms, repo, penalties and rendering.
- `app/interfaz/*`: shell, theme, home, notifications, normativa, admin and Hall.
- `app/activity/events.py`: ActivityEvent legacy store.

Fase 4 wrappers currently delegate selected logic into domain services:

- ranking helpers and points-with-penalties;
- division movements;
- shop promotion selection/pricing/state;
- trainer status and robbed flag mutations.

Fase 5 wrappers currently delegate selected persistence into repositories:

- `app/entrenadores/trainer_flags.py` loads/saves trainer flags through
  `LegacyTrainerRepository`.
- `app/activity/events.py` stores ActivityEvents through
  `LegacyActivityRepository` while preserving legacy dict output.
- `app/tienda/discounts.py` reads/writes promotion scheduling through
  `LegacyShopRepository` and `LegacySettingsStore`.
- `app/interfaz/hall_of_fame.py` loads/saves entries through
  `LegacyHallOfFameRepository`.

Fase 6 adds a future persistence target but does not connect runtime:

- V2 is greenfield and reproducible from SQL.
- V1 is not patched and not deleted.
- `settings` blobs are not carried forward as source of truth.
- Core competitive data is season-scoped.
- `coin_transactions` is the future money source.
- The isolated V2 API has progressed through Phase 8; React/Cloudflare deployment
  and runtime cutover remain future work.

Fase 6.1 validates that target for real:

- PostgreSQL 17.11 portable local validation database:
  `pokeapp_v2_validation`.
- `001_core.sql` through `009_seed.sql` applied successfully.
- `reset_dev.sql` then full rebuild applied successfully.
- Real introspection confirmed 32 public V2 tables, 75 FKs and 92 indexes.
- Fixtures validated current save ownership, uniques, checks, JSONB, ledger,
  archive preservation and delete restrictions.
- `reset_dev.sql` was corrected to drop `trainer_flags` and `pokemon_flags`.

Fase 7 secures that target:

- every V2 public application table has RLS enabled;
- `trainers.auth_user_id` resolves current trainer identity;
- `trainers.is_admin` controls explicit admin permission;
- safe `public_*` and `current_*` views define client read surfaces;
- private save payloads, private team locks, purchases/redemptions and ledger
  details are owner/admin only;
- direct writes for critical flows remain server/API only;
- `raw-saves` storage policies are prepared for Supabase storage paths by
  `trainer_id`.

Fase 7.1 completed real staging validation:

- `tools/validate_supabase_v2_rls.py` validates Supabase Auth JWTs, PostgREST
  RLS and Storage policies against a real staging project.
- `.env.supabase-v2-rls.example` documents required credentials without secrets.
- Real staging project `Pokeapp 2.0` has migrations 010, 011, 012, 013, 014,
  015, 016, 017 and 018 applied through the Supabase connector.
- SQL-level checks confirmed 32 public tables, 32 RLS-enabled public tables, 82
  public policies, 37 safe views, 13 `security_invoker` views and 24 public
  definer projections.
- Storage migration 013 is now policy-only, Cloud-safe and already applied in
  staging.
- Full validator execution passed against the real staging project with
  `RESULT ok checks=13`.

Persistence:

- Supabase is the remote store when configured.
- SQLite/local files are fallback/dev.
- `settings` JSON is still heavily used for official aggregate state.
- Streamlit `session_state` is a runtime mirror, not the target architecture.

## Accepted Debt

- Many official entities still live in generic `settings` JSON.
- Streamlit UI and business rules are still coupled in several modules.
- Runtime Streamlit still uses legacy/V1 persistence; V2 is not connected yet.
- V2 mutation deliveries through 032 are recorded in the phase reports.
  Cup delivery is closed in the 8L report; future remote actions still require
  fresh verification of project, migration history and source.
- Legacy ActivityEvents remain in settings; new V2 lock/purchase transactions
  writes V2 tables only, without dual-write or Discord delivery.
- Legacy Copa and Juicios remain in the runtime. Their V2 contracts now exist:
  [Trials/sanctions](phase8k1-trials-sanctions.md) and [Cup engine](phase8l-cup-engine.md).
  Both deliveries are closed; neither implies a frontend cutover.
- Parser bridge is treated as a black box but not fully isolated.
- Some legacy helper names remain, especially around wipe/revive wording.
- Visual CSS layers are acceptable for the reference app but should not be the
  long-term design system.

## Next Step

Phase 8L and the approved Phase 8 backend inventory are closed. Consult the
[completion report](phase8l-completion-report.md) for final evidence and the
[closed handoff](work-in-progress/phase8l-live-handoff.md#next) for continuity.
No delivery retry or migration replay is pending.

Phase 9 (parser boundary and base Launcher/Companion) is planned next work only;
**do not start it automatically**. Follow its separately authorized scope when
requested. React/visual polish, deployment and V1/V2 cutover remain later work.
D1-D7 remain approved and D8 deferred. The documentation-only Phase 8K audit's
judicial T1-T5 proposals remain superseded by the approved manual Discord-result
contract delivered in 8K.1. No new mechanics or physical save writes are implied.
Do not cut over Streamlit or delete V1 without explicit approval.

## Do Not Do When Resuming

- Do not keep polishing Streamlit without a real bug.
- Do not add new mechanics.
- Do not start React before Fases 3-9.
- Do not migrate the database before the Supabase V2 schema exists.
- Do not add SQL patches ad hoc for new mechanics.
- Do not remove Streamlit until shadow mode and cutover are complete.
- Do not implement N divisions inside the old Streamlit A/B state.
- Do not send Discord announcements for hidden migration work.

## Remaining Planning

- Fase 3: domain contracts. Closed.
- Fase 4: pure domain extraction. Closed.
- Fase 5: repositories. Closed.
- Fase 6: Supabase V2 greenfield schema. Closed.
- Fase 7: RLS and security. Closed.
- Fase 7.1: real Supabase staging validation complete.
- Fase 7.2: Supabase Storage compatibility fix completed and applied.
- Fase 8A.1: PIN auth bridge core. Closed.
- Fase 8B: FastAPI skeleton, JWT verification and PIN-login rate limiting.
  Closed.
- Fase 8B-H: auth hardening. Closed.
- Fase 8C: Team Lock V2 API mutation. DONE local + staging.
- Fase 8D.0 + 8D: current matchday, Store Ban and normal purchase. DONE local + staging.
- Fase 8E: promotional claim. DONE local + staging; 27 checks and 8D regression PASS.
- Fase 8F: all four effects DONE local + staging; physical save execution remains future Companion work.
- Fase 8G: season/league administration contract audit DONE, documentation only.
- Fase 8G.1: core setup/admin DONE local + staging; 026 applied, cleanup PASS.
- Fases 8H, 8I, 8J and 8K.1: matchdays, participant status, lifecycle/League Hall
  and trials/sanctions DONE local + staging; evidence is in their phase reports.
- Fase 8L: DONE local + real V2 staging; approved Phase 8 backend CLOSED.
  In-process FastAPI with real Auth/PostgREST; no public API deployment.
- Fase 9: parser boundary.
- Fase 10: React / Cloudflare frontend.
- Fase 11: data migration.
- Fase 12: shadow mode.
- Fase 13: staging with cloned data.
- Fase 14: performance measurement.
- Fase 15: cutover.

## Technical Handover Summary

PokeApp is a competitive Pokemon league manager for a small private league. It
combines save uploads/parsing, trainer profiles, PC/boxes, team locks, Team
Preview, Liga A/B standings, shop economy, redemptions, Copa, Juicios, Hall of
Fame, Discord-adjacent notifications and an Anto-only admin back office.

The current app is valuable because the product behavior is now defined and
tested enough. The next risk is not product uncertainty; it is architecture.
The app should not be rewritten blindly. It should be migrated by extracting the
domain concepts that already exist and proving equivalence with tests.

The most important official historical protection is the round snapshot system:
once a jornada closes, standings/rewards/penalties are read from the snapshot.
The most important season-level protection is SeasonArchive: once archived, the
Hall of Fame should use archived data and public champion team snapshots instead
of mutable live saves.

The current weakest technical point is the broad use of `settings` JSON. That is
acceptable for Streamlit 2.0, but it must become explicit contracts, repositories
and Supabase V2 tables before React/Cloudflare becomes the main app.
