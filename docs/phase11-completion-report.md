# Phase 11 — surviving V1 facts in an isolated relational destination

Closed 2026-10-11. **STATUS: PHASE 11 DONE. PHASE 12 READINESS: READY FOR SHADOW.**
[Mapping](phase11-source-inventory.md),
[validation evidence](phase11-closure-evidence.json),
[operational handoff](work-in-progress/phase11-live-handoff.md).

## Entry and approved destination

Resume entry `82d2dd841c10d2864b4c9638dad7acab49840df1`, main/origin 0/0.
Phase 10.5 was already closed. Fresh remote reconciliation found both projects
healthy, unchanged surviving V1 facts, 33 V2 migrations through 041, no private
Shadow schema or import effects, and all 59 scoped V2 hashes preserved. Existing
042 SQL was continued; missing persisted importer/rehearsal files were completed.
The approved isolated destination resolves the historical active-season conflict.

Authoritative source is `fdtytpeyfzyssfrsulxd`, diosaog's Project, eu-north-1.
Destination is `uwleqeuzsveqlugugzba`, schema **v1_shadow**. Its 15 tables have no
foreign keys into public competitive data. No V1 fact is merged into the owner's
active season. V1 remains source/reference; no cutover or Shadow execution occurs.

## Mapping, identity and truthful limits

The import preserves ten trainer names, one League context, ten memberships in
the original A/B 5/5 order, one save, two pending purchases and one eight-player
legacy Swiss Cup with four original pending pairs. Eleven raw noncredential
records accompany the typed facts. Three exclusions record the PIN and two
notification caches without copying their values. Source Auth is empty.

Fifty-seven deterministic UUIDv5 identity records explain source-to-private
entities. Existing V2 trainer UUIDs are candidate annotations only: they confer
no account ownership and do not overwrite Auth, PIN, admin role or public trainer
rows. Names, source IDs, exact original timestamp text and relational ownership
are retained. Missing season start and historical configuration timing remain
unknown. Effective legacy active status explicitly records the absent-setting
runtime fallback; it is not presented as a stored or verified deployed history.

The save's 524,410 exact bytes are stored privately as bytea and checked against
the source SHA-256. The prior neutral parser evidence reports W2, eight Unova
badges, Champion false and five Box-8 occupants. Its private progress row is not
a modern competitive observation. Nine progress rows retain null badge/death/
Champion values. Current party is not substituted for missing Team Lock history.

Anto's private wallet reconciles exactly to **32 badge earnings - 24 purchase
spend = 8 coins**, under the documented surviving legacy calculation. Both pending
purchases already count in that spend; neither is debited again. Nine other
balances remain unknown. Exact Decimal/numeric arithmetic is used. No historical
ledger events, badge payouts, completion claims, purchased-revive effects or wipe
events are manufactured. Eight badges do not prove in-game completion.

No surviving results, official rankings, locks, redemptions, promotions, sanctions,
championship, archived seasons or Hall records are reconstructed. Source cleaning
was intentional. Empty source domains remain empty; SQLite and modern V2 data are
not used to fill them. The legacy Cup retains null rules version, explicit zero
standings and null winners; no modern certificate or champion is invented.

## Atomic import and interruption recovery

Forward **042_v1_shadow_relational_destination** adds the private schema and
journal. The mapper binds the capture, parser evidence, bytes and mapping version
to a validated plan. Six dependency-ordered batches run in separate transactions.
Each holds an import advisory lock, checks every existing row against the complete
receipted prefix, inserts its facts and receipt atomically, and verifies the
result. Final certification requires all six batches. Different captures, stale
plans, missing predecessors, unexpected rows and changed facts fail closed.

After two remote batches, the Management API rejected the original batch-3 request
with HTTP 413 because the save appeared repeatedly in its SQL. A separate exact
read-only reconciliation proved only batches 1/2 existed. The transport correction
stages the plan once in a transaction-local temporary table, dropped at commit,
while retaining both complete state checks. No new migration, weakened validation
or blind retry was used. Original failure and recovery evidence remain private.

## Validation and security

Full Python **784 PASS**, including 19 pre-existing unrelated untracked map tests.
Focused mapper **12**, final renderer **9**, schema **15** pass. After the transport
correction, all **21** affected Python tests and the complete affected PostgreSQL
import proof passed again. The 784-test application run is retained from initial
source `a20deb9`; unaffected suites were not rerun or relabeled as newly executed.
Compile, targeted Ruff and diff checks pass. No UI, parser or application runtime
contract changed; unrelated React/browser/native-parser suites were not rerun.

Real PostgreSQL 17.11 final import proof: eleven groups, thirteen injected rollback boundaries, eleven
relational denial cases and forty-eight actual role denials. Clean and interrupted
imports match exactly, excluding only batch completion clocks; full replay also
preserves those clocks. Concurrent final-batch replay has one effect. A separate
same-session failure proves temporary payload cleanup after rollback; cleanup also
passes after commit. All 53 public
tables, including a local active manual-season fixture, remain exact and are
restored after cleanup. All private test fixtures are removed. Migration-chain
and bootstrap builds yield **14,026 identical schema/grant/ownership lines**.
An embedded BOM in the previously unapplied 042 was corrected; only the failed
bootstrap path was rerun. The valid schema builds were retained for the later
transport correction's affected import proof.

All fifteen tables have forced RLS. PUBLIC, anon, authenticated and service_role
have no schema/table/column authority. No browser RPC, policy, privilege bypass or
permanent migration function is exposed. Execution uses migration authority.
Private raw evidence, source credentials and save contents are not committed.

## Remote result and preservation

Application/migration source `a20deb91f86b35e7a0d861a812e0c2ca8f67ab73` was pushed
before the first remote write. 042 was applied once as **20261011160629**; all
33 previous migration records were retained. The transport fix source
**8c593514c47120baabad7bc9cf7f22a07cf3e334** was committed/pushed before resumption.
The runner first reconciled the existing prefix and skipped batches 1/2 without
writes; batches 3–6 then succeeded. Run
**61e5eb57-34f5-57f9-9252-4ea8be8d8b66** was certified **reconciled** at
2026-10-11 16:13:19 UTC. All six receipts exist exactly once. The destination has
135 rows across 15 tables, including the run and six journal receipts.

Independent read-only verification confirms exact V1 preservation (**13/13**
tables), all original V2 public/Auth/Storage data (**59/59**, full and owner-excluded
baselines), stable owner credentials/identity, and all previous migration records.
The active manual season, memberships, results, economy and Team Locks are intact.
No public business row, Auth identity or Storage object was written by this phase.

All private data reconciles: fourteen raw table hashes equal the local rehearsal,
and the full run row matches after converting `captured_at` to the same precise
UTC instant. Only batch completion clocks are excluded from cross-run equality.
The initial textual run-hash mismatch came from local/hosted timezone rendering;
the failed initial comparison and the strict normalization proof are retained.
No historical timestamp was changed or ignored to obtain PASS.

Remote security catalogs pass for all fifteen private tables. Advisor is
**24 ERROR / 5 WARN / 170 INFO**, with zero added or removed ERROR/WARN. The 27
added INFO findings concern fifteen private RLS tables without policies and twelve
unindexed foreign keys; they do not grant access. Existing production findings
were not modified. No temporary migration privileges or permanent helpers remain.

Railway and Cloudflare remain at existing application source
`eb4e402891cbaa02e0999229874ac3003e016ae0`; this package changes neither application
contract and requires no deployment. No owner login or competitive mutation is
used to validate the migration. Fresh final deployment identifiers remain Railway
`2d71ec3b-095d-49a7-aa15-31749fe67b52` SUCCESS and Cloudflare
`ea9c837d-86f0-4b0a-826d-a4774371b56e`, version
`77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11`, 100%. Local PostgreSQL was safely stopped
after confirming no test runners or client sessions; no database/directory was
deleted.

Private evidence has a hash-verified durable copy (**2,694 files**) under
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase11/20261011/closure-a20deb9-8c59351/`.
The original authoritative source bundle remains in the adjacent `20261009/`
directory. No raw credentials, save bytes or credential-bearing source hashes
are committed. The historical source-evidence timestamp was corrected from an
incorrect midnight placeholder to its verified exact reconciliation time.

Files changed: forward 042 and generated bootstrap; deterministic mapper, atomic
SQL renderer and local PG harness; their focused/schema tests and bootstrap list;
source mapping, sanitized evidence, completion report, checkpoint and handoff.
No unresolved conflicting records remain. The three intentional exclusions,
unknown observations/dates and absent deleted history are documented limitations,
not silently repaired or hidden quarantines. The protected guide and unrelated
pre-existing untracked files remain untouched. Documentation closure is a separate
commit after final implementation `8c593514c47120baabad7bc9cf7f22a07cf3e334`; obtain
its exact HEAD from Git rather than a self-referential commit hash.

## Phase 12 handoff

Use the reconciled private run, identity map, source records, receipts, manifest
and exclusions as the fixed migration reference. Access remains migration-owner
only; a future Shadow reader must retain that private boundary. Candidate IDs,
save facts and private economic snapshots are not authority to merge identities,
issue modern rewards or rewrite public history. Later source changes require
explicit comparison; this runner does not implement live synchronization or
replace an existing capture automatically.

**NEXT: PHASE 12 SHADOW, awaiting its explicit execution instruction.** Read the
final live handoff before any further action. Phase 11 is DONE; Phase 12 is READY
FOR SHADOW and NOT STARTED. No cutover, release or physical-save write occurred.
