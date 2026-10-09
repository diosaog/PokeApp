# Phase 11 — live execution record

Observation: 2026-10-09 Europe/Madrid. **STATUS: PHASE 11 BLOCKED at MAPPING.**
The original source-access blocker is resolved: the owner confirmed V1 and
reactivated it; raw remote capture and content verification succeeded. The current
blocker is placement of the legacy competition alongside the protected active V2
manual season. This is the single current operational record.
[Source inventory and mapping checkpoint](../phase11-source-inventory.md),
[current sanitized evidence](../phase11-source-evidence.json),
[historical readiness report](../phase11-readiness-report.md),
[historical evidence](../phase11-readiness-evidence.json),
[checkpoint](../project-checkpoint.md),
[closed 10.5 handoff](phase10-5-live-handoff.md).

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
