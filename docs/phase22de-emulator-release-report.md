# Phase 22D/22E - real emulator and private release gates

Observed 2026-10-23. **PARTIAL. Real 3DS qualification and private release BLOCKED.**
Entry main/origin `4614cd3b7fe53bdc48df5f3f39117a0356d72fca`, fetched 0/0,
clean tracked tree. Only focused tests and continuity documentation changed;
application source remains at entry. This commit carries the results; obtain
its final HEAD from Git. [Evidence](phase22de-emulator-release-evidence.json),
[live handoff](work-in-progress/phase22-save-writes-live.md).

## Actual emulator evidence

Azahar is installed at `C:\Program Files\Azahar\azahar.exe`, version **2126.2**
from installer registry/binary string, pinned SHA-256 in evidence. It was not
launched against the owner's profile. The owner confirms there is no executable
3DS game available. Saves alone cannot qualify actual gameplay, save flush or
the emulator's restart behavior. No Azahar adapter is certified.

The owner authorized disposable DS checks without adding DS write support.
The available game identifies as **Pokemon White 2 / Blanca 2 (W2)**, despite
the filename ROMNEGRO2. Real **DeSmuME 0.9.13 x64 SSE2** loaded an isolated ROM
and copied 4-Mbit battery save twice, once paused and once running. Both runs
closed normally through WM_CLOSE, exited 0, and released resources sufficiently
for the existing exclusive handoff guard to open the copied save. No force-kill.
Between runs, existing offline LauncherCore/PKHeX performed native read, SQLite
observation, exact backup and native reparse. The backup and selected copy remain
identical after reopening. Both the DS WriteIntent and legacy apply operation
correctly reject mutation. Five source files (ROM, saves, executable and settings)
retain exact hashes, sizes and modification times. No owner's original was opened
by the emulator.

This is **ROM load/close/read/backup/reopen proof**, not an in-game Save action,
flush certification, changed-Pokemon observation, relaunch exclusion or integrated
automatic application/recovery. No APPLIED receipt was produced for DS. It does
not qualify Azahar or any 3DS game, and does not expand product support.

The first harness run was invalidated: executing DeSmuME under TEMP redirects
settings/save storage to LOCALAPPDATA/DeSmuME, so it did not use the selected copy.
The corrected run executes outside TEMP with explicit isolated paths and confirms
4-Mbit save loading without a missing-save fallback. This behavior is explicit
in [DeSmuME's GetINIPath source](https://github.com/TASEmulators/desmume/blob/release_0_9_13/desmume/src/frontend/windows/winutil.cpp).
Both logs are retained; the first is not counted as a passed save-loading test.

## New recovery evidence and retained gates

**Three new focused tests PASS** on Windows 11 build26300/local NTFS:

- An independent writable mapped view remains active after both file and mapping
  handles close. Source and candidate guards refuse it; after unmapping, the same
  objects are admitted. This closes that specific mapped-I/O evidence gap only.
- An independent process creates a conflicting file during restore's absent-path
  interval. Restarted recovery preserves it, both exact backups remain exportable,
  and recovery/restart flags fail closed. Flags are not external process control.
- A same-byte external replacement with a different file identity invalidates the
  current receipt match and blocks restore, preserving the backup.

Initial three tests: 0.850 s. Only the mapped-view case was rerun after adding its
positive control; final recorded exit 0, 0.322 s. One PowerShell stderr logging
wrapper falsely returned failure despite unittest OK; corrected subprocess capture
records the actual exit. Recovery tests use the existing fake native fixture with
real Windows filesystem/processes; the separate DS check uses actual PKHeX.
Ruff, formatting, compile and diff pass. **74 prior tests, eight authentic 3DS
fixture-copy workflows and two dev Electron journeys are retained, not rerun**;
all 16 recorded source fingerprints still match. Production code did not change.

No disposable Windows10, other Windows11 build or non-NTFS environment was
identified. No OS crash or power loss was induced; process recovery is distinct.
Mapped flush is not hardware-durability evidence, as described by
[Microsoft](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-flushviewoffile).
Hostile/privileged actors remain outside certification.

## Packaging, preservation and next gate

**22E remains gated; no new build or installer run.** An emulator-enabled private
candidate cannot be qualified before the real 3DS adapter. Existing private
**0.22.0-rc.2**, unsigned/unpublished, and public **0.20.0** remain unchanged;
rc.2 does not contain 22C. No owner installation, remote service, database,
economy, entitlement, rewards, original save or production registry changed.
No Phase23 or profiles. Five unrelated untracked files remain untouched.

The absent-path contract is already owner-approved; no repeat approval is needed.
Next prerequisite: a legal executable supported 3DS title. Then qualify pinned
Azahar with isolated save/configuration, actual save/exit/flush, restart exclusion
through application/recovery and in-game observation. Follow with platform and
durability decisions/evidence, private packaged integration, clean installation/
upgrade, signing and owner release acceptance. Do not enable writes meanwhile.
Estimated overall PokeApp + Launcher completion remains **85-90%**, a judgment,
not a measured completion metric. Phase22 cannot be declared DONE.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase22de/20261023/`.
All test emulator/child processes ended. Automatic approval review rejected the
exact disposable cleanup with **blocked by policy** before the command ran;
no alternate deletion was attempted. Manual cleanup remains for:

- `%TEMP%/pokeapp-phase22d-ds-iej_rerq`
- `%LOCALAPPDATA%/PokeApp-migration-evidence/phase22de/20261023/disposable-ds-g3e6ndq0`
- The first run's new `%LOCALAPPDATA%/DeSmuME/desmume.ini` and
  `%LOCALAPPDATA%/DeSmuME/Battery/ROMNEGRO2.dsv` (creation times and test-path
  configuration recorded privately; do not delete later unrelated user files).

The evidence JSON/scripts/logs outside those disposable trees are retained.
