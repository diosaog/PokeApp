# PokeApp — Phase23C native revive and trusted verification

2026-10-25. **23C DONE LOCAL ENGINEERING. Phase23 PARTIAL / NOT DEPLOYED.**
Entry main/origin `e741822e4af5e2d06dac4338d0f27567e1754c6c`, fetched0/0,
clean tracked tree; eight unrelated untracked files preserved.
Implementation committed/pushed: `6469f75d6d2825b3c770d858b1ab621ecab6a1e4`.
[Evidence](phase23c-local-evidence.json) / [current handoff](work-in-progress/phase23-live.md).

## Contract and native effect

The existing physical contract is in `Bridge/PKHeXBridge/Program.cs`:
`FindFirstFreeSlot` and the `revive` branch move the exact Pokemon from Caja8 to
the first empty position, box-major/slot-major, in Cajas1–7. No party insertion,
HP healing, status/attribute editing or arbitrary destination selection.
The unsafe legacy writer itself is not reused.

Competitive authority remains the existing 039/redemption contract and
[8F](phase8f-redemption-effects.md), [10.5 alignment](phase10-5-functional-alignment.md):
own unambiguous current dead entity, current accepted save and identity revision;
already-shielded dead Pokemon may revive. Success consumes the purchased unit,
records revival, shield and timestamp, retaining the historical death. Same still
visible death cannot be redeemed twice. A later observed alive-then-dead event
has its existing rules. No new coin debit at use time, death scoring or rewards.

`NativeRevive` reuses the pinned PKHeX protocol. It copies the exact stored232-byte
Pokemon, clears its old slot and serializes native checksums/Gen7 signature. Both
native verification and an independent read reject any other change, including
valid-checksum money or IV alterations. Exact source SHA/game/trainer, PID/EC,
OT ownership, eggs, collisions, slot protection and first-free destination are
checked. The server additionally rechecks complete trusted identity evidence,
the persistent entity/revision and approved source ownership. Unsupported or
ambiguous evidence remains rejected. Physical engine/journal/backups are reused;
production mutation registry and public IPC remain disabled.

## Independent verification and its boundary

`TrustedItemUseVerification` obtains authority and immutable original bytes from
its server-side repository, reparses them, derives the plan itself and uses its
own native execution to verify submitted result bytes exactly. It reparses the
result too. Evidence binds trainer, season, purchase, authorization, claim, source,
result, entity, revision, native operation and plan/version digest. The client
cannot supply the original source/plan as authority or issue evidence. No client
secret, APPLIED string, local receipt or declared hash is trusted.

The actual SQL/native/Launcher integration is exercised through a **local-only
privileged recorder** with captured-context recheck under locks, immutable result
retention, compatible replay and incompatible-proof rejection. Normal service_role,
authenticated and anon cannot insert proof. Existing054 still consumes only after
private proof and completion checks, in its existing transaction.

This proves that the artifact received by the server is precisely the approved
transformation of its retained source. The separate Windows gate proves automatic
application to the selected disposable path. It cannot prove that an untrusted
player kept those bytes, launched them, or never restored an earlier save.
**Production verifier transport, restricted deployment identity and durable remote
artifact retention are not provisioned.** There is no public proof-issuance route.
The local recorder is test infrastructure, not a new privileged API escape hatch.

## Fresh tests and fixes

- **192 native checks PASS**, X/Y/OR/AS/SN/MN/US/UM. Authentic contributed format
  fixtures remain hash-identical. Copies contain an explicitly synthetic own dead
  target and a free destination: native-valid derived fixtures, not a claim about
  a naturally dead Pokemon, encounter legality or in-emulator gameplay. Full
  parser observations are identical except for the two changed locations.
- Real **PostgreSQL17.11 + PKHeX + existing Windows engine PASS for all eight**:
  source registration through the actual trusted-ingestion service/RPC, identity,
  native plan, backup/apply/readback, false-client rejection, server verification,
  proof replay, lost completion response, restart, exactly one redemption,
  blindado/revivido_at and no coin transactions. Raw object transport is an
  in-memory isolated substitute; no external Auth/Storage/HTTP claim is made.
- Six new-native interruption gates PASS: before backup, after backup, after stage
  creation, after parking, after publication and after native verification.
  Restart reconciles actual state, preserves original/candidate bytes and keeps
  unknown entitlements pending. These are injected exceptions, not power-loss
  evidence. Prior Phase22 real process-termination evidence is retained.
- Additional real-PG/Windows gates PASS: two Launcher profiles/one claim, paused
  sync, incompatible proof, forbidden evidence writers, changed context/identity,
  stale selected file and restored source before confirmation. No blind reapply.
  A final X journey rechecked the strengthened binding/recovery bookkeeping;
  the other seven native format results were not repeated.
- **57 unique focused Python checks PASS**:15 verifier/binding,26 native-bridge/
  Launcher regressions,15 schema and one production-capability denial. Two schema
  expectations still named054; updated to055 and only those two rerun. SQL identity
  policy equivalence is checked against048 with only the local variable renamed.
- Upgrade/bootstrap through055: **16,376 identical schema/grant/ownership lines**,
  **64 pre055 table hashes preserved**. No old migration changed. Owned databases
  dropped and clusters stopped. SQL54's prior full concurrency/rollback suite,
  React10/Edge2 and unrelated matrices retained, not rerun.
- Native build PASS, zero warnings/errors; Python compile, new-source Ruff and
  formatting, targeted existing-source lint and diff checks PASS. No web changes
  or new browser build. Existing generator/schema-test formatting is retained;
  dotnet-format was unavailable in the cached SDK, so no formatter PASS claimed.

The real native ingestion exposed SQLSTATE42702:048's local `evidence` collided
with an observation column. New **055_native_identity_evidence_scope** only
renames that variable; no policy, grants, rows or applied migration was rewritten.
An initial attempted implicit-label qualification failed42P01 locally and was
replaced by the verified variable rename before final tests. **054/055 remain
local, unapplied remotely.** The first harness also used a draft season (correctly
rejected by ingestion) and the wrong receipt field; both fixture issues corrected.
The cached SDK runtime lacked Numerics; the installed .NET8.0.29 runtime completed
native validation. No global installation or dependency/lock change occurred.

The bridge now binds effect/revision and cannot release sync while another binding
or native operation is pending. Its Spanish confirmation describes the exact box
move and separate server check. Existing web authorization/recovery/blocked/verified
states are reused. Historical internal redemption receipts still retain their
old physical-pending snapshot; reconcile those read projections before activation.

## Remaining release gates and state

No real Azahar executable-game qualification, gameplay save flush/reopen proof,
new Windows/platform certification or hardware-crash guarantee. These Phase22
gates are unchanged. Public Launcher and production writes remain OFF/unchanged.
No deployment, remote database read/write, owner save, randomised Y, economy,
accounts, V1 or Shadow access. Remote state is **STAGING_UNVERIFIED this session**;
UNCHANGED means this work made zero remote changes, not a fresh remote comparison.

Before deploying054/055: approve and provision the private verifier/transport and
artifact-retention boundary, reconcile physical-status reads, qualify the actual
emulator/runtime and package, then run scoped hosted acceptance with fresh remote
baselines and separately authorize activation. The eight-game local result does
not grant production capability. Full two-save theft remains unimplemented;
auto-update, Rare Candy and Heart Scale remain reserved. No Phase24.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase23c/20261025/`:
`native/native-revive.json`, `pg.json`, `security-parity.json`, `final-binding.json`.
Console test outputs are recorded in this execution; no full raw Python log is
claimed. Native fixture inputs and owned stopped-cluster test artifacts are
retained privately; their exact locations are in those JSON files. No active test
session remains. Implementation and documentation commits are recorded in Git;
the documentation commit carries this report. Explicit staging only.
