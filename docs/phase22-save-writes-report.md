# Phase 22 - native save-write foundation

2026-10-20. **STATUS: PARTIAL. Engineering implementation validated; public
physical-write activation/release BLOCKED.** No Phase 23.
[Evidence](phase22-save-writes-evidence.json),
[live handoff](work-in-progress/phase22-save-writes-live.md).

Entry `77c2f18f9e07db19c5c6e58446fbcfd830228977`, main/origin aligned, clean
tracked tree. Application commit `62822a69370e7ee34d028c607a0d2c9d2644ddb3`.
Documentation closure follows separately; obtain its exact HEAD from Git.

## Implemented and verified

The pinned PKHeX.Core 24.11.11 worker adds byte-only prepare/verify modes.
The existing reader protocol and observation/identity digests are unchanged.
Only an explicit engineering capability, restricted to disposable fixture roots,
allows the nontrivial `test_marking` operation. The production operation registry
is empty. Renderer, remote server, entitlement or JSON parameters cannot grant
that capability. No items, nature changes, purchases or transfers are implemented.

The local engine binds game, trainer, source SHA-256, exact mutation and a
deterministic operation ID. It validates local NTFS paths, rejects unsafe links,
hardlinks, UNC/ADS, stale bytes, permissions, known emulator processes and file
locks. It creates a unique verified original backup before preparation, operates
on a clone, and writes/flushed output in the target directory. Own-engine
operations serialize across threads, profiles and the same target pathname.
Replacement uses Windows `ReplaceFileW`; there is no copy-over-original fallback.

Native verification checks the complete unprojected save. Permitted differences
are one encrypted Pokémon slot, its block checksum fields, and Gen7's native
signature. Within the decrypted slot, only the marking and Pokémon checksum
may change. Trainer, party/PC contents, inventory, identity/progress and all
other bytes remain preserved. Native serialization and a separate verification
process validate checksums/signatures, game, trainer and expected result.

The SQLite FULL-synchronous local journal records prepared, awaiting confirmation,
verified application, rejection and recovery states. Final disk bytes are verified
before success. Replay reconciles the durable receipt instead of applying again.
Recovery reads never blindly write; explicit engineering restore requires the
known result and restores the exact backup. Later edits are preserved.

| Game           | Native fixture-copy write, verify, replay, restore |
| -------------- | -------------------------------------------------- |
| X              | PASS                                               |
| Y              | PASS                                               |
| Omega Ruby     | PASS                                               |
| Alpha Sapphire | PASS                                               |
| Sun            | PASS                                               |
| Moon           | PASS                                               |
| Ultra Sun      | PASS                                               |
| Ultra Moon     | PASS                                               |

These are real retained public contributor snapshots bound to the existing
manifest, not owner saves or synthetic read-only roundtrips. Original hashes
remain unchanged. They establish the tested native formats, not gameplay
legitimacy or every possible save variation.

## Launcher and safety

The local UI shows a precise Spanish action, requires confirmation that the
game/emulator is closed, and uses a separate native confirmation dialog. Only an
opaque existing local operation ID crosses IPC. Production has no pending action
provider. Success/rejection/recovery are human-readable; hashes and journal
parameters remain private.

Reads and sync can coexist, but neither overlaps a physical write. Recovery
uncertainty pauses sync. The verified write invalidates the old observation and
cloud receipt while still holding its exclusive lease, forcing reparse before
upload. A slow native operation does not block state polling. Unsupported write
infrastructure with no prior journal does not disable ordinary offline reading.
The candidate remains read-only to users.

## Validation and local package

Focused Python: **29 Windows filesystem + 10 native bridge + 16 Launcher
integration + 14 affected sync regressions = 69 PASS**. Windows tests use actual
NTFS operations and six `os._exit` subprocess interruption boundaries: prepared,
backup verified, stage verified, before replacement, after replacement and after
verification. New-process recovery, disk-full/short write, wrong ownership,
corruption, external edits, locks and unsafe paths are covered.

Native **225 checks PASS**. All eight games also pass the complete Windows
engine/native adapter path with exact restoration. The final self-contained
packaged native executable independently passes all eight games, including
unchanged reader DTO and digest. Two isolated packaged Electron runs pass local
read/restart, sandbox/context isolation, absent developer runtimes, forged-write
denial and the new status rendering. Rendering fixtures are explicitly separate
from real IPC denial evidence. No positive production write was performed.

Compile, targeted Ruff, JavaScript syntax, Prettier, diff, PyInstaller,
self-contained .NET 8.0.29, NSIS and package audit PASS. Full historical suites,
React/web, PostgreSQL and migrations were not rerun because those surfaces did
not change. An incomplete ambient .NET runtime initially failed Gen7 tooling;
the complete pinned self-contained runtime supersedes that harness failure.

Private candidate **0.22.0-rc.1**, **159147043 bytes**,
SHA-256 `cb234fc8936c7ab4cff3c7d5af92f81e5a7e3991e382985ca76c2dac295bd48d`.
Authenticode: **NotSigned**. Retained under
`%LOCALAPPDATA%/PokeApp-releases/0.22.0-rc.1`, with a NOT-PUBLISHED notice.
No public installer was replaced. Owner-installed 0.16.2 was not touched.

## Genuine release blockers and preservation

Windows `ReplaceFileW` has no atomic target-path/hash compare-and-swap.
An adversarial test replaces the target between the last check and our replace.
The engine preserves the original backup and displaced external bytes and refuses
to certify success or automatically restore, but detection happens after the
external version has been displaced. This does **not** satisfy the required
guarantee of never overwriting a newer legitimate change. Public writes remain
disabled until a safe design and corresponding proof close this gap.

Known-process checks also cannot certify that arbitrary renamed/custom emulators
are closed. Process-crash tests do not certify sudden power loss or hardware
durability. Backups are immutable to this application, not to malicious same-user
ACL changes. Clean-machine installer/upgrade acceptance remains unperformed:
replacing the owner's installation for testing was not allowed. These limitations
are not converted into PASS.

No database/schema migration, Railway, Cloudflare, R2, V1/Shadow, owner-save or
competitive mutation occurred. Public Launcher remains 0.20.0. Phase21 production
source/deployments and 41 migrations through 049 are retained; Gen6/7 rewards stay
`pending_validation` / `pending_policy`. No fresh full-table comparison is claimed
for this local-only phase. Existing production authorization/history remain unchanged
by Phase22.

All test-owned disposable Windows trees were cleaned by the runners; no candidate
process remains. Private evidence is under
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase22/20261020`.
Automatic approval review rejected deletion of
`%TEMP%/pokeapp-phase22-package-20261020` with **blocked by policy**.
That exact build directory remains for manual cleanup; no alternate deletion was
attempted. The protected guide and unrelated files were untouched.

**Next:** resolve the physical-write exclusion and release-certification blockers
within Phase22, preserving these passed gates. Return to Antonio for acceptance.
Do not enable production mutations or start Phase23.
