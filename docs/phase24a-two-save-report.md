# Phase24A — paired save transfer, local engineering unit

2026-10-25. **PHASE24 PARTIAL. Production UNCHANGED.**
Entry `3f5d1ea92af37457baa4dced819a3c86c42a11cc`, main/origin0/0, tracked clean,
no other active agent.23D gate PASS: published report/evidence, PG results and all
source fingerprints checked at entry. Its matrices were not repeated.
[Evidence](phase24a-two-save-evidence.json) · [Live handoff](work-in-progress/phase24-live.md).

## Implemented and proven boundary

The existing native writer now derives a paired plan from two server-owned
originals. It removes exactly one unambiguous boxed Pokémon from the donor and
inserts its exact232 stored bytes into the first eligible free recipient slot.
Original OT, IVs, ability, moves and identity evidence are retained. Only that
slot, its block checksum and the required Gen7 signature may change. Both sides
are independently derived and verified; client plans, local receipts and hashes
alone cannot issue evidence.

**PASS: X→X, Y→Y, OR→OR, AS→AS, SN→SN, MN→MN, US→US, UM→UM**, on derived copies
of the retained authentic public-format fixtures. The qualified new subset is
boxes1–7, same title, non-egg, unique PID/EC and known original trainer. Party
compaction and cross-title conversions are unsupported and rejected; this is an
implementation boundary, not a change to the approved robbery rules.

Additive **057_two_save_transfer_reservations**, LOCAL ONLY, extends the existing
item-use authorization with two private RLS leg records. Reservation binds the
purchase, entity, both trainers, current saves, hashes and identity heads. It
reserves both participants, preserves uncertain reservations without timeout
reuse, and rejects conflicting sync, identity advancement and redemptions. Both
backups must be prepared locally before donor application. Recipient application
requires the independently verified donor artifact. A readiness acknowledgement
is not privileged proof that a remote disk has a backup.

The restricted23D verifier role gains one paired RPC, with no direct table DML;
normal API service, browser and Launcher cannot issue proofs. The new seam reuses
the native bridge, immutable item-use namespace and signed artifact reader.
It is not wired into public HTTP, the API container or production IPC. There is
no second generic upload system, verifier secret in the Launcher or deployment.

`EngineeringTransfer` reuses LocalWriteController, its sync gate, the SQLite
physical journal, verified backups and the existing no-replace handoff. Stable
claims/intents survive response loss and restart. It reconciles before retry and
never reapplies a verified side. The existing Launcher status area gets Spanish
paired-state notices; generic confirmation and unilateral restore are denied.
Save Copy still exports exact verified backup bytes. No separate web screen or
public initiation flow was added while finalization remains unsafe.

## Rules and why this is PARTIAL

Canonical8F.1/025 remains authoritative: enabled actor and another active
same-season participant, own pending robbery purchase, current unambiguous live
target, no shield/already-stolen state, victim cycle eligibility. No new matchday
or season-lifecycle rule. Coins are charged at purchase; the approved shield
voucher belongs to the robber.054's later physical-proof boundary delays use
consumption. This packet consumes no entitlement and grants no voucher.

**The indispensable unresolved integration is foreign-OT identity.** Existing
schema2 reconciliation deliberately marks the received Pokémon
`original_trainer_unproven`. Tests reproduce that after exact native insertion.
Changing the OT, forcing `source_trainer_match=true`, allocating another entity
or merely changing its owner would violate the trusted identity/current-save
contract. A proof-bound ownership transition must also register both resulting
saves and new identity revisions atomically, without changing the stable UUID,
original provenance or frozen history. That path is not implemented here.

Consequently, two valid proofs end at **BOTH_VERIFIED_PENDING_IDENTITY**, never
APPLIED_VERIFIED/transfer-confirmed. The purchase remains pending, owner remains
the donor, cloud current-save pointers remain unchanged, and sync/reopening remain
blocked. Exactly-once *consumption* is not claimed: consumption is unavailable.
Historical receipts are untouched. Partial physical application remains pending;
no independent restore can duplicate a Pokémon already inserted at the peer.

Coordinated abort/rollback and reservation release are also unfinished. Backups
are recoverable/exportable and conflicts preserved, but operators must not clear
reservations or independently restore either side as an improvised repair. This
engineering-only unit is unsuitable for user activation in its present state.

## Fresh validation

- **176 native checks PASS:**168 boxed paired checks across eight titles plus8
  explicit cross-title denials. Wrong target/slot, stale input, clone collision,
  full destination, dead box, unintended money changes, integrity and exact PKM
  preservation included. New C# build: no warnings/errors; pinned dependencies.
- **46 unique Python/static checks PASS:**10 new journal tests,21 affected
  Launcher/write regressions and15 schema checks, combined final evidence. New
  coverage includes explicit confirmation, lost ready/begin/upload responses,
  restart after publication, independent writer and gap creator, corrupt binding,
  Lime process denial, stale source, generic-IPC/restore denial, exact Save Copy
  and restart/selection sync exclusion. Native semantics in these10 tests are a
  synthetic fixture; the separate eight-game journey uses real PKHeX.
- **Real disposable PostgreSQL + native + two Launcher journals:** all eight
  same-title workflows reach both-artifacts-verified with both backups intact,
  unchanged owner, no redemption/consumption, restart and replay. Additional X
  gate proves concurrent reservation, second robbery rejection, later shield/
  stolen flags, disabled peer, tampered artifact rejection, private grants,
  exact two-function worker allowlist and old completion API denial.
- **057 migration/bootstrap parity:17,077 schema/grant/ownership lines;65 prior
  public table hashes preserved** across the forward migration. Disposable reset
  removes the adjunct while preserving the local Shadow schema. This is not a
  production data comparison.
- Python formatting, targeted Ruff, syntax and diff PASS. Installed SDK lacks
  `dotnet-format`; no C# formatter PASS is claimed. No React/browser/build matrix,
  packaging, hosted Auth/Storage or emulator certification was repeated.

Early development found a trigger referencing a field absent from an identity
row; product SQL now branches by table. The harness used an obsolete `price`
field; corrected to `base_price`. A completion-denial assertion initially passed
with wrong RPC argument order; it was invalidated and replaced by the real
repository claim/complete call, which returns BLOCKED_UNCERTAIN without consuming.
The final schema test was adjusted for two new explicit RLS tables. Only affected
gates were repeated; no failures/skips remain in the reported final evidence.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase24a/20261025/`.
Owned PG databases dropped and clusters stopped. Test journals/backups in the
recorded temporary clusters and derived fixture evidence are retained; no blanket
cleanup of unrelated paths. No real saves, personal randomized Y, remote V1/Shadow,
accounts, economy, Railway, Cloudflare, Supabase or public Launcher were accessed
or changed. Physical production mutation registry remains empty.

## Exact next unit and classification

1. Add proof-bound transferred-identity provenance and accepted-save reconciliation
   for both parties; prove ordinary subsequent sync preserves the same entity/OT
   and rejects clones or ambiguous observations.
2. Atomically register both authoritative results and finalize the existing025
   competitive effects once; fault-test every step, lost response and replay.
3. Implement paired abort/rollback authority and reservation release without
   restoring a donor while recipient state is unknown. Extend party/cross-title
   qualification separately; unsupported combinations remain unavailable.
4. Then expose the existing screens/IPC to the approved flow and qualify real
   lifecycle/application with **Lime3DS**, the owner's primary emulator. Retain
   Azahar/Citra detection. Owner's randomized Y remains reserved, never tested here.

| Gate | Result |
| --- | --- |
| PHASE23D GATE | PASS |
| TWO-SAVE PROTOCOL | PARTIAL — durable coordinated physical unit proven |
| NATIVE TRANSFER | PARTIAL — eight same-title boxed workflows proven |
| SERVER VERIFICATION | PARTIAL — both artifact proofs PASS; ownership finalization absent |
| RECOVERY | PARTIAL — reconciliation/backups/conflicts PASS; paired rollback absent |
| LIME3DS CERTIFICATION | PENDING |
| PHASE24 | PARTIAL; no public activation |

The focused closure commit carries implementation and this evidence; derive its
exact final HEAD from Git. Explicit staging only, eight unrelated untracked files
preserved. No next phase started.
