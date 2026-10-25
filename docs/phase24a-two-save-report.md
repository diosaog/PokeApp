# Phase24A — paired save transfer, local engineering unit

2026-10-25. **PHASE24A DONE LOCAL. Production UNCHANGED.**
Entry `3f5d1ea92af37457baa4dced819a3c86c42a11cc`; first unit published as
`5652808bd078f9de78ddc21f12f9867b4284ccc2` (PARTIAL), closed by the focused
finalization commit on top of it. 23D gate PASS at entry; its matrices were not
repeated. [Evidence](phase24a-two-save-evidence.json) · [Live handoff](work-in-progress/phase24-live.md).

## Implemented and proven boundary

The existing native writer now derives a paired plan from two server-owned
originals. It removes exactly one unambiguous boxed Pokémon from the donor and
inserts its exact232 stored bytes into the first eligible free recipient slot.
Original OT, IVs, ability, moves and identity evidence are retained. Only that
slot, its block checksum and the required Gen7 signature may change. Both sides
are independently derived and verified; client plans, local receipts and hashes
alone cannot issue evidence.

**PASS: X→X, Y→Y, OR→OR, AS→AS, SN→SN, MN→MN, US→US, UM→UM**, on derived copies
of the retained authentic public-format fixtures. The qualified subset is
boxes1–7, same title, non-egg, unique PID/EC and known original trainer. Party
compaction and cross-title conversions are unsupported and rejected; this is an
implementation boundary, not a change to the approved robbery rules.

Additive **057_two_save_transfer_reservations** (unchanged) reserves both
participants against the existing item-use authorization: purchase, entity,
trainers, current saves, hashes and identity heads. It blocks conflicting sync,
identity advancement and redemptions without timeout reuse. The restricted23D
verifier role issues both artifact proofs; normal API service, browser and
Launcher cannot. `EngineeringTransfer` reuses LocalWriteController, its sync gate,
the SQLite physical journal, verified backups and the no-replace handoff.

## Closure: identity, finalization and recovery (058)

Additive **058_transfer_provenance_finalization**, LOCAL ONLY, closes the gap
that kept the first unit PARTIAL. Historical migrations001–057 are unchanged.

- **Foreign-OT provenance.** Private `transfer_provenance` (forced RLS, all
  privileges revoked from every API/verifier role, one row per authorization)
  binds entity, donor, recipient, original evidence/flags, both results and both
  proofs. Ordinary ingestion consults it through `transfer_identity_proven`:
  the received Pokémon is `MATCHED` to its **original UUID** while
  `source_trainer_match` stays literally false. No OT rewrite or forged flag.
- **Atomic competitive finalization.** One verifier transaction re-checks the
  proofs, moves `owner_trainer_id`, registers BOTH accepted saves and identity
  revisions, advances both current-save pointers and applies the existing025
  effects once: purchase `used`, one redemption, one robber shield voucher,
  `blindado`/`robado` flags. A transaction-scoped `transfer_commit_permits` row
  (unforgeable by API/worker roles, empty after commit) is the only way past the
  057 reservation guards. Terminal state and receipt are stored; replay returns
  the identical receipt without re-deriving obsolete donor context.
- **Clone/history safety.** Prior revisions/observations are untouched. The
  retired donor re-uploading original bytes under another hash gets `AMBIGUOUS`
  via `transfer_foreign_collision`; an old donor receipt cannot rewind pointers.
- **Coordinated recovery.** Before any physical effect, a paired cancellation
  releases both legs (`released`), keeps originals and the unused purchase, and
  clears both Launcher gates; no physical rollback is attempted. After physical
  application, recovery is forward-only: reconciliation reports
  APPLIED_VERIFIED, unilateral cancellation/restore is denied, and finalization
  is retried idempotently. Uncertain/one-leg states stay blocked.

## Fresh closure validation

- **Real disposable PostgreSQL17 + native PKHeX + two Launcher journals, all
  eight titles: COMMITTED.** Per title: atomic owner/save/identity/025 effects,
  one immutable provenance row, empty permits, foreign-OT `MATCHED` on the
  original UUID, recipient-only proven context, lost-final-response replay
  identical, both restarted Launcher gates complete and released. Wrong proof
  hash rejected before effects.
- **X additionally:** injected failure after all effects rolls back all17
  involved tables exactly, physical receipts/backups retained, unilateral
  cancellation denied; two concurrent finalizers produce one effect and identical
  receipts; ordinary later sync keeps the foreign-OT UUID; retired-donor clone
  blocked; paired pre-apply cancellation releases both sides. These title-neutral
  SQL/journal paths were not repeated for the other seven titles.
- **058 upgrade/bootstrap parity:** 001–057 then 058 equals bootstrap,
  **17,395 schema/grant/ownership lines; 67 prior public table hashes preserved**.
  Disposable cluster only; not a production data comparison.
- **268 affected Python tests (schema, identity, ingestion, Launcher/write,
  transfer, per-title parsers): 267 PASS, 1 FAIL pre-existing** —
  `test_phase16d_save_sync…test_runtime_publishes_only_verified_readback_and_clears_superseded`
  fails identically on a clean export of `5652808`; outside 24A, not changed.
- Ruff on changed Python: no new findings (17 inherited, identical at HEAD);
  format/compile/diff PASS. The new harness was format-only reformatted after the
  run with an identical AST hash.
- **Retained, not rerun:** 176 native checks (native sources and 057 hashes
  unchanged since the first unit), first-unit tampering/concurrency/privacy gates.

Development history: the first closure X runs failed in the harness (a test
flag and an assertion), and 058/the validator were corrected; only the affected
gate was rerun, then the eight-title run. No failures or skips remain in the
reported closure evidence.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase24a/20261025/`
(`closure-x-final.json`, `closure-eight-games.json`, `closure-parity-058.json`).
Owned PG databases dropped and clusters stopped. No real saves, personal
randomized Y, remote V1/Shadow, accounts, economy, Railway, Cloudflare, Supabase
or public Launcher were accessed or changed. Physical production mutation
registry remains empty; 058 is not applied anywhere remote.

## Remaining limits (not 24A blockers)

1. Party transfer and cross-title conversion remain unqualified and rejected.
2. No public HTTP route, API container wiring, production IPC or web screen.
3. A post-apply divergence (peer save changed outside the protocol) stays
   blocked for reconciliation; there is no automatic physical rollback by design.
4. Lime3DS real lifecycle certification PENDING; Azahar/Citra detection retained.
   No OS-crash/power-loss certification. C# formatter unavailable in SDK.

| Gate | Result |
| --- | --- |
| FOREIGN-OT PROVENANCE | PASS |
| COMPETITIVE OWNERSHIP | PASS |
| ATOMIC FINALIZATION | PASS |
| COORDINATED RECOVERY | PASS (pre-apply cancel; forward-only after apply) |
| EXACTLY-ONCE CONSUMPTION | PASS |
| X/Y/OR/AS/SN/MN/US/UM | PASS ×8 |
| POSTGRESQL + 058 | PASS |
| LIME3DS CERTIFICATION | PENDING |
| PHASE24A | DONE LOCAL; no public activation |
| PHASE24B GATE | PASS |

Explicit staging only; the eight unrelated untracked files are preserved.
No next phase started.
