# Phase 11 - live execution record

Closed 2026-10-11 Europe/Madrid. **STATUS: PHASE 11 DONE.**
**PHASE 12 READINESS: READY FOR SHADOW. PHASE 12 NOT STARTED. No cutover.**
[Completion report](../phase11-completion-report.md),
[closure evidence](../phase11-closure-evidence.json),
[approved mapping](../phase11-source-inventory.md),
[project checkpoint](../project-checkpoint.md).

## Verified final state

Entry main/origin `82d2dd841c10d2864b4c9638dad7acab49840df1`, fetched 0/0.
The owner's approved isolated destination is implemented as **v1_shadow** in V2
`uwleqeuzsveqlugugzba`. V1 `fdtytpeyfzyssfrsulxd` remains source/reference.
Both projects remain ACTIVE_HEALTHY. No source facts were inferred from SQLite.

Implementation `a20deb91f86b35e7a0d861a812e0c2ca8f67ab73` was pushed before 042,
applied once as **20261011160629**. All previous 33 migration records remain exact.
Final transport/import source **8c593514c47120baabad7bc9cf7f22a07cf3e334** was pushed
before resuming imports. Documentation closure is a subsequent commit; Git is the
authority for that exact final HEAD.

Run **61e5eb57-34f5-57f9-9252-4ea8be8d8b66** is **reconciled**, with six completed
batches and 135 rows across fifteen private tables. Import finished at
2026-10-11 16:13:19 UTC. Independent read-only comparison passes all mapped facts:
fourteen exact table hashes plus complete run-row equality after precise UTC
normalization of captured_at. Only batch receipt clocks differ between executions.

V1 **13/13** source tables and V2 **59/59** original public/Auth/Storage tables
remain exact, including full Auth baseline and stable owner identity/credentials.
The active manual season, memberships, results, economy and Team Locks are intact.
No public business writes, Auth changes, Storage-byte writes or cutover occurred.

## Imported facts and boundaries

Ten trainers, one private League context, A/B 5/5 memberships, one exact save,
ten progress rows, ten private wallet rows, two pending purchases, one legacy
Swiss Cup, eight Cup members and four pending pairs. Fifty-seven identity mappings,
eleven raw noncredential source records and three explicit PIN/cache exclusions
make the mapping auditable. No account merge or credential copy occurred.

Anto's private source evidence is eight badges, Champion false, five Box-8
occupants and derived legacy balance 32 - 24 = 8. Nine missing progress/balance
observations remain unknown. These are private migration facts, not modern
competitive observations or permission to issue rewards. Pending purchases are
not charged again. Missing start dates, rules timing, Team Locks, deleted history,
championship and Hall remain absent/unknown. No physical-save mutation occurred.

## Validation, recovery and security

Full Python 784 PASS on initial meaningful source, including nineteen pre-existing
untracked map tests. After the transport-only correction, the 21 affected mapper/
renderer tests and full affected PostgreSQL proof pass again. Unaffected suites
are retained, not relabeled as newly rerun. Schema tests15, compile, Ruff and diff
checks pass; unchanged UI/parser suites were not rerun.

Real PostgreSQL: eleven final groups, thirteen table rollback boundaries plus
same-session temporary-payload cleanup, eleven relational denials, forty-eight
actual role denials, exact 53-public-table preservation/restoration, and clean
private fixture cleanup. Two full-chain/bootstrap builds have 14,026 identical
schema/grant/ownership lines. Their valid evidence was retained after transport
changes. Local PostgreSQL is stopped after confirming no active test sessions.

A real HTTP413 interrupted batch3 because its original SQL repeated the save.
Read-only reconciliation proved only batches1/2 had committed. Compact SQL reuses
one transaction-local payload without weakening checks. After commit/push and
local proof, resumption skipped batches1/2 and completed3-6. No blind replay, 042
reapplication or duplicate effects. The separate initial run-hash mismatch was
strictly explained by timezone rendering, with the same full timestamp instant;
original failure evidence is retained. Neither required changing source facts.

All fifteen remote tables have forced RLS, postgres ownership and no browser or
service_role schema/table/column privileges. No policy, function, user trigger or
external FK exposes the import. Advisor **24 ERROR / 5 WARN / 170 INFO**, with
zero added/removed ERROR/WARN; 27 added INFO describe private no-policy RLS tables
and unindexed FKs. No privileges were loosened.

Railway `2d71ec3b-095d-49a7-aa15-31749fe67b52` SUCCESS and Cloudflare
`ea9c837d-86f0-4b0a-826d-a4774371b56e` / version
`77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11` at100% remain on application source
`eb4e402891cbaa02e0999229874ac3003e016ae0`. No deployment was needed or performed.

## Durable recovery reference and exact next step

Verified private closure evidence (2,694 files) is under
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase11/20261011/closure-a20deb9-8c59351/`.
Original source capture is under the adjacent `20261009/` directory. Temporary
working evidence remains `%TEMP%/phase11-closure-20261011/` and the two local-proof
folders. Credentials, raw saves and credential-bearing hashes are private.

**STOP. Await the Phase 12 Shadow execution instruction.** Its first action must
reconcile Git, actual source, migration history and this completed private run.
Do not restart Phase 11, replay 042, replace this capture automatically, merge
candidate IDs, promote private progress/economy or reconstruct absent history.
The migration-owner read path remains private; no browser API is implied.
Phase 12 is ready for Shadow but has not begun. No cutover is authorized here.

## Historical checkpoints — superseded operational state

## Latest reconciliation — 2026-10-09

The resume procedure was rerun against the live projects. V1 remains
`ACTIVE_HEALTHY`; its 13 captured table count/hash records are unchanged. V2
remains at 33 migrations through 041, with the same 267-object catalog and 59
owner-excluded table hashes as the 10.5 closure. The stable owner identity and
credentials are unchanged. No journal, batch, entity map or import effect exists;
remote writes remain zero. The detailed read-only reconciliation is in the
private evidence directory `%TEMP%/phase11-reconcile-20261009-2/`. Its verified
source/V2 capture copy is under
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase11/20261009/`.

## Current resume checkpoint — 2026-10-09

- Resume HEAD/origin `dc1b1462c53ed77ddc3af9bac0aa0d9b3de74eb5`, fetched 0/0,
  tracked tree clean before this documentation update. No import/schema writes
  existed at entry. Fresh V2 history remains 33 records through 041; catalog
  267 objects identical, no import journal/effects. All 59 owner-excluded table
  hashes equal the verified 10.5 closure. Full Auth differences are confined to
  owner activity; stable credentials/identity and all public/Storage rows match.
- V1 `fdtytpeyfzyssfrsulxd`, `diosaog's Project`, eu-north-1, ACTIVE_HEALTHY.
  Owner identity confirmation is authoritative. Real catalog matches all seven
  legacy tables. One read-only statement captured all seven public tables, four
  Auth tables and Storage buckets/objects. All 13 hashes remain identical after
  discovery, metadata reads and save download. Local SQLite was not used.
- Source: ten League trainers, A/B 5/5, J1 with no results/snapshots; eight-player
  legacy Swiss Cup with four pending pairs; two pending Anto purchases; one save;
  no locks, redemptions, Pokémon flags, promotions, archived/Hall records or Auth
  users. Exact counts, semantics and absence limits are in the source inventory.
- The save's 524,410 bytes match its stored SHA-256. Local read-only parser version
  `pokeapp-reader/3;pkhex/24.11.11` observes W2, eight Unova badges, Champion false,
  five Pokémon in Box 8; source bytes unchanged. No cloud observation/reward was
  created. V1 wallet formula and live `rpc_total_spent` definition support
  32 badge earnings - 24 pending-purchase spend = 8 for Anto.
- No new migrations, helpers, journal rows, target identities, import batches or
  remote business writes. No deployment or PostgreSQL runner. Existing Railway
  and Cloudflare remain at `eb4e402`; V2 Advisor remains 24 ERROR / 5 WARN / 143 INFO.
  V1 Advisor baseline is 5 ERROR / 11 WARN / 19 INFO; V1 was not changed to fix it.

## Current material mapping blocker

`league_state.active=false` closes matchday editing, not the season. Missing
`season_lifecycle_v1` means effective ACTIVE under the tracked legacy runtime,
with no evidenced `started_at`. Do not claim the stored JSON explicitly declares
an active season or that the exact deployed legacy revision has been verified.

The current V2 catalog confirms `uq_seasons_one_active`; the owner's manual
season occupies that slot. V2 also requires an active season's start timestamp.
Relabeling V1 draft/archived, inventing its start date, merging it into the manual
season, retiring that season or changing normal lifecycle invariants is not an
approved migration mapping. Capturing raw data alone is not a completed import.

The owner was asked whether to authorize an **isolated relational import target
for Shadow**, outside V2's current competitive lifecycle, preserving both source
and manual season truth. No isolated target/schema policy has yet been approved
or implemented. Do not treat silence as approval. This is a destination scope
decision, not a naming or file-placement preference.

## Exact next action

1. Resolve the pending destination-placement decision. Source identity/access no
   longer needs reconfirmation. Reconcile Git, remote history, source capture and
   V2 baseline/journal state before resuming any write.
2. Finalize mappings against the approved destination, preserving unknown legacy
   timing and current owner identities. Economic opening-snapshot/high-water
   design is a documented candidate, not implemented historical reward replay.
3. Implement journaled deterministic imports; prove restart, rollback and exact
   state on disposable PostgreSQL before committed/pushed remote migration.
4. Fresh source/destination baselines, verified atomic imports, reconciliation,
   security checks and genuine Phase 11 closure. **Phase 12 remains NOT READY /
   NOT STARTED.** No cutover.

Private capture/evidence: `%TEMP%/phase11-resume-20261009/v1/` and `v2/`.
Verified private copy and manifest also live at
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase11/20261009/`.
Raw settings contain credentials and remain private. The native parse is source
evidence, not a full parser regression suite or cloud ingestion claim.

## Historical initial entry and effects — 2026-10-08

- Entry main/origin: `e256d5b28f751beb7c3851e58b1eb7c9c81ed8fb`, fetched 0/0,
  clean tracked tree. Final 10.5 DONE / Phase 11 READY FOR REVIEW verified from
  Git, final report, handoff and current source. New owner instruction authorizes
  Phase 11; the older instruction to wait for authorization is superseded.
- V2 `uwleqeuzsveqlugugzba` is ACTIVE_HEALTHY. Fresh history has 33 records through
  `041_final_product_alignment` = `20261008204133`, once. Local chain is 001–041.
  No migration/import journal or Phase 11 tooling exists. No new forward SQL,
  identity map, import batch, schema change or business mutation was attempted.
- All 59 full table count/hash records equal the independent 10.5 closure;
  all 33 migration records and stable owner Auth/credential hashes also equal it.
  Owner identity/admin, three manual seasons including active
  `c6bcac5b-0b89-403f-8242-41ac58286ade`, results, economy, locks and Storage
  metadata remain intact. No Storage object bytes were written.
- Advisor: 24 ERROR / 5 WARN / 143 INFO. Existing Railway and Cloudflare both
  still identify application source `eb4e402891cbaa02e0999229874ac3003e016ae0`.
  Exact deployment identifiers are in the report/evidence. No deployment needed
  or performed for this documentation-only readiness checkpoint.

## Historical source-access blocker — resolved on 2026-10-09

V1 connection configuration is absent from repository/global Streamlit secrets
and process/User/Machine environment. The accessible Supabase account lists V2
and `fdtytpeyfzyssfrsulxd` (`diosaog's Project`, eu-north-1, INACTIVE). Its identity
as V1 is **UNPROVEN**. A read-only catalog query returned HTTP 544:
`Failed to run sql query: Connection terminated due to connection timeout`.
The historical Streamlit URL redirects to Streamlit authentication, and does not
establish a database source. No restore, unpause, restart or source write occurred.

Local `data/app.db` is an unverified fallback: 21 save records/files, 12 settings,
10 redemptions, zero purchases/locks/flags/promotions. All ten redemptions lack a
local purchase. Latest save metadata is 2025-12-09. These observations do not prove
remote data is corrupt or absent; they prove this local copy cannot silently be
selected as the authoritative complete source.

At this historical checkpoint the owner question was pending: identify V1 and
restore read access, or identify an authoritative export. The subsequent owner
confirmation and successful capture above supersede this access blocker.

## Historical resume point — superseded above

1. Reconcile Git, this handoff, real migration history, V1/V2 state and any
   journal/remote effects again. This checkpoint performed only remote reads.
2. Resolve source identity/access; capture raw source tables/settings/Storage
   metadata privately. Never invoke legacy runtime readers as an exporter:
   some write sanitized state or silently fall back to SQLite.
3. Establish actual per-domain mappings and conflicts from that capture. The
   report records conditional schema hazards; none is a proven source conflict
   until real V1 is readable. In particular, do not deactivate the owner season
   or change the one-active-season invariant to accommodate an assumed V1 season.
4. Only then implement the smallest private journal/id-map/import mechanism,
   prove deterministic restart/rollback on disposable PostgreSQL, commit/push,
   capture fresh remote baselines and execute verified atomic imports.
5. Reconcile and close Phase 11; stop before Phase 12. **Phase 12 NOT READY.**

Private evidence: `%TEMP%/phase11-entry-20261008/`. No migration outcome is unknown:
none was attempted. No local PostgreSQL runner was started. No application,
React or parser tests were rerun because no implementation changed. Documentation
checks accompany this checkpoint; this is not a migration completion report.

Protected guide and unrelated untracked ZIP/AI-map/validator files remain untouched.
Explicit staging only. V1 remains source/reference; no cutover, reset, cleanup,
Phase 12–15 or physical save writes are authorized by this checkpoint.
