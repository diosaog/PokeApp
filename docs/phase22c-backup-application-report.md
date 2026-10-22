# Phase 22C + targeted 22D - verified backups and automatic application

Observed 2026-10-23. **DONE LOCAL ENGINEERING / CONDITIONAL RELEASE. Phase22 PARTIAL.**
Entry `457bc30e15468648cb5e195b06dd1cf00f3be93a`, main/origin aligned. The owner
authorized the 22B no-replace handoff for engineering integration and disposable
tests only. Production capability remains absent. [Evidence](phase22c-backup-application-evidence.json)
and [current handoff](work-in-progress/phase22-save-writes-live.md).

## Integrated behavior

The existing `LocalWriteEngine`, SQLite journal and native PKHeX writer are reused.
Before native mutation preparation, the engine validates source hash/game/trainer
and file identity, holds protected file/ancestor handles, creates an independent
immutable-by-policy backup in the managed profile, checks length and SHA-256,
and commits its verification metadata. Backups have unique operation identifiers;
an existing copy is never overwritten. A parked source does not count as backup.
The SQLite journal retains synchronous FULL/DELETE behavior; backup bytes are
flushed and reread. This is not a power-loss certification.

The new Windows primitive holds READ+DELETE access while denying other write/delete
sharing. Both renames use supported FileRenameInfo with replacement disabled.
Journaled source/candidate identities, hashes and parking/publication intent precede
each transition. An external file created in the gap wins: publication refuses to
overwrite it and retains backup, parked original and candidate. A successful
application receives APPLIED_VERIFIED only after native readback at the selected
pathname. Replays reconcile actual identities and bytes, without another mutation.
The old replacement protocol cannot execute a new confirm/restore.

Restoration requires explicit emulator-closed and restoration confirmation,
engineering capability, valid original backup/game/trainer, and either the exact
known candidate or a proven interrupted absent-path state. A divergent current
file blocks restoration. Before parking an existing candidate, the engine also
stores its exact independently verified backup. Interrupted restore publication
can be reconciled and completed without overwriting a new external file. Partial
backup/stage creation that cannot be identified safely remains unresolved; no
last recovery copy is deleted to make retry succeed.

The Spanish Launcher interface shows backup game, date, validity and recovery
state. **Guardar copia…** opens the native save dialog and exports exact original
bytes exclusively to a new destination. It needs no cloud account, browser or
native parser, including an isolated startup with the parser missing. Corrupt or
unreadable backups are visibly disabled. No renderer-supplied destination bypasses
the native dialog; the local controller also binds requests to the selected save
and profile. Restore uses a separate native confirmation with Cancel as default.
Local write/read/cloud-sync exclusion is shared, with recovery keeping sync paused.
EXPORTED_VERIFIED remains distinct from APPLIED_VERIFIED.

The engineering mutation remains `test_marking` only. No purchase, robbery,
transfer, entitlement consumption, reward or certified-history effect is enabled.
Purchases debit coins at purchase time; backup/export/restore do not undo purchases
or acknowledge item use. Restoring bytes alone is not economic reconciliation.

## Evidence actually obtained

- **74 unique affected Python tests, combined evidence:** 29 engine, 4 export,
  16 Launcher/controller, 10 native bridge, 13 new integration boundaries and
  2 targeted runtime/network regressions. The initial 59-test run passed in
  10.229s; only invalidated/additional checks followed, not a historical full suite.
- Real Windows/NTFS tests cover ENOSPC, process death mid-backup, apply interruption
  before/between/after renames, three restore interruption boundaries, exact replay,
  corruption, independent writer/replacement attempts, gap collisions, two Launcher
  processes with same/different profiles, source identity mismatch, unsafe paths,
  explicit confirmation, selected-save/profile isolation and sync exclusion.
- **X, Y, OR, AS, SN, MN, US, UM PASS** through integrated backup, actual disposable
  original-path application, native reparse/verification, replay, parser-free copy,
  restore and restore replay. All manifest-verified authentic contributor fixtures
  remain unchanged. Original and pre-restore backups remain exact and exportable.
- **Two dev Electron/private-stdio launches PASS**, native present and missing:
  exact Save Copy bytes, source unchanged, corrupt-backup refusal, ten IPC denials,
  no browser errors. Native save-dialog choice was stubbed to an owned temporary
  destination; the real copy operation ran. Final pending-sync label/checkbox
  layout was checked separately and screenshots reviewed. This is not packaged
  or clean-install evidence. The package harness allowlist was updated for the
  new IPC surface; that packaging gate was not rerun.
- Targeted Ruff E4/E7/E9/F/I, format, compile, JS syntax, Prettier and diff pass.
  Existing native codec evidence is retained; no native rebuild, PG, parser matrix
  or backend/UI-web suite was justified by this scope.

Harness corrections are explicit: old ReplaceFileW mock points were moved to the
new transition boundaries, a module import initially duplicated old tests, two
invented runtime module names caused runner import errors before the actual two
runtime cases were selected, and an ad hoc PowerShell UI predicate lost accented
characters through stdin. Corrected affected gates passed without weaker assertions.

Private evidence is under `%LOCALAPPDATA%/PokeApp-migration-evidence/phase22c/20261023/`.
Eight-game and unit-test temporary roots were cleaned. All dev Electron/core test
processes ended. The isolated UI profile, exact copies, deliberately corrupt test
backup and screenshots remain as private evidence. Earlier cleanup residue was
not touched. No owner saves, production business data, infrastructure or installer
were changed. Public **0.20.0** and private **0.22.0-rc.2** were not replaced.

## Remaining boundaries and exact next step

No actual emulator is qualified. The earlier model child remains a model; a
process-name check, user checkbox or UI `emulator_restart_allowed=false` is not
external restart prevention. No approved pinned emulator/title test setup was
available in this packet. Ordinary runtime cannot create engineering capability,
so unknown emulator behavior cannot enable physical writes. Qualification remains
an explicit release gate, as permitted by the owner instruction.

The two-rename transaction is not atomic: the pathname may be absent during the
handoff and after process death until reconciliation. Handles exclude the tested
ordinary writers/renamers while alive, not arbitrary existing mapped writes or
hostile/privileged actors. Testing covers this Windows 11 build26300/local NTFS
host. Windows10/other builds/filesystems, system crash, power loss and storage
cache/namespace durability remain uncertified. Backups improve recoverability;
they do not convert those missing guarantees into PASS.

**Next:** qualify one pinned real emulator adapter in an isolated legal test setup:
graceful save flush/close/exit, restart denial throughout application/recovery,
and rejection of unsafe configurations. Then close platform/crash-durability and
explicit product acceptance gates, followed by private packaging, clean-machine
installation/signing and release review. No installer publication is authorized here.

Future item use additionally needs a backend-authorized immutable operation and
an idempotent acknowledgement bound to verified physical application/reconciliation.
Export, an unknown outcome, or a successful purchase must never alone consume an
item-use entitlement. Restoring an applied file needs an explicit business policy;
this packet invents none. Gen6/7 reward gates remain unchanged.

The focused commit carries code, tests and this closure; obtain its final HEAD from
Git. Explicit staging only; five unrelated untracked files preserved. Estimated
global product + Launcher completion: **about 85–90%**, engineering judgment rather
than a measured burndown; release qualification and real item application dominate
the remaining uncertainty. **No Phase23, profiles or production integration.**
