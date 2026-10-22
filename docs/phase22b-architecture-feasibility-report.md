# Phase 22B - automatic save application feasibility

Observed 2026-10-22. **CONDITIONAL — OWNER DECISION REQUIRED. Phase 22 PARTIAL.**
The new tools-only experiment publishes a natively validated candidate at the
original pathname without overwriting a concurrent external file. It works by
two no-replace renames, so **the pathname is temporarily absent**. This is not an
atomic replacement and is not yet an approved product contract. Production
writes remain disabled; 22C integration and 22E packaging have not started.

## Current state

Entry HEAD was `58cf806c273fd0e551e10ae6422b2fff187fbc41`, with origin aligned.
The existing native writer, journal, backups, recovery, verified export and
Phase 22A evidence were reused. No owner save, production service, economy,
public Launcher or backend was changed. The new work is a tools-only proof;
it is not imported by the Launcher and does not grant production capability.

## Required guarantees separated

| Guarantee | Actual new evidence / limit |
| --- | --- |
| A. Atomic publication | Each rename publishes a complete file, but the two-step handoff is **not atomic**: readers can see no file between steps. |
| B. Ordinary external writes | Independent write opens fail while source/candidate handles deny write sharing; an already-open writer prevents entry. No cooperation is needed for these denials. |
| C. Rename/replacement | Independent move/delete/replacement attempts fail before parking and after publication while guards remain held. During the absent-path gap a new file can win; publication fails with 183 and leaves that external file intact. |
| D. Process interruption | Four forced process deaths produce classified original/candidate/absent states. A parked original can be restored without replacement; occupied or corrupted recovery is rejected. This is an isolated filesystem proof, **not integrated journal recovery**. |
| E. System crash/power loss | NOT PROVEN. Data fsync and process termination are not hardware-crash or namespace-durability certification. |
| F. Hostile/privileged actors | No guarantee against administrator/kernel, handle injection, metadata/reparse manipulation or other untested APIs. Locks end on process death. |

The interrupted assessment overstated the absence of handle protection for all
renames. The precise limitation is the old **replacement transition**, not all
handle-based renames. Our new process retains DELETE access itself while denying
others write/delete sharing. It renames the held objects without reopening them.
The documented [CreateFileW sharing contract](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)
and [FILE_RENAME_INFO non-replacement flag](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info)
support this distinction. Publication uses supported
[SetFileInformationByHandle](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle),
absolute names, RootDirectory NULL, FileRenameInfo and ReplaceIfExists FALSE;
no TxF, driver, replacement fallback or new native dependency.

## Architectures evaluated

| Architecture | Result | Reason |
| --- | --- | --- |
| Launcher-managed emulator lifecycle | **CONDITIONAL** | Needed to prevent game restart during a gap/recovery. Only a model process was tested; no real emulator adapter is qualified. Lifecycle alone does not exclude unrelated programs. |
| Emulator integration/private save directory | **CANDIDATE** | Can isolate normal emulator access, but does not reserve names against same-user processes. Archived Citra documents a portable user directory; current emulator/version qualification remains necessary. |
| Existing ReplaceFileW transition | **INSUFFICIENT, RETAINED** | Its previously demonstrated compare/replace race was not repeated. No claim that every possible user-mode architecture is impossible. |
| Handle-based no-replace handoff | **CONDITIONAL, NEW PROOF** | Preserves concurrent external files by aborting, and automatically updates the original pathname on success; sacrifices continuous pathname availability. |
| TxF or custom filesystem driver | **NOT ADOPTED** | TxF is discouraged and only host-tested; a custom driver is not realistic to maintain for this private app. |

## Isolated proof of the conditional architecture

`tools/phase22b_cooperative_lifecycle_probe.py` uses one disposable copy of a
real X save. A child process models a supported emulator and opens the copy with
an exclusive handle. The Launcher cannot acquire its lock or rename the path
while that emulator handle is live. The child acknowledges `CLOSE`, exits, and
the Launcher then acquires its lock. An independent child writer is blocked while
the Launcher lock is held, and the copied bytes remain intact.

Inherited result: **PASS, LIFECYCLE ONLY**. Evidence is retained at
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase22b/20261022/cooperative-lifecycle-evidence.json`.
This is a model process, not an actual emulator. Its old byte-preservation check
compared only sizes. The resumed tool now checks SHA-256 and uses a real bounded
pipe-read timeout; the corrected lifecycle run passed separately. Four new tool
control tests pass (silent child timeout, EOF rejection, acknowledgement and
rejection of repository paths as mutation roots).

## New original-path publication experiment

Earlier work already identified the moving-aside gap. The new hypothesis tests
whether held handles plus **no-replace on both renames** preserve competing
files across that gap; it does not claim to eliminate the gap.

`tools/phase22b_handoff_probe.py` reuses the pinned native writer/verifier and
existing file/path checks; it has no import from production Launcher code back
into the probe. Mutations are restricted to owned temporary copies. It prepares
`test_marking`, holds source and candidate with READ+DELETE access and only READ
sharing, pins ancestors, verifies expected hashes, renames source to a recovery
name, then renames candidate to the original pathname **without replacement**.
Both file handles remain held through verification. A separate intact backup
and the parked source preserve the original bytes. No product APPLIED receipt is
issued; native reparse and verification check the resulting candidate.

**PASS: X, Y, OR, AS, SN, MN, US, UM**, each against manifest-verified authentic
public fixtures, automatic publication at the disposable original pathname,
native verification/reparse and unchanged original/backup hashes. **27 scenarios
PASS:** eight guarded writer/replace/rename/delete denials, three competing gap
creators preserved, four forced process deaths, recovery collision, existing
writer, competing publisher, replay rejection, four unguarded attack controls,
stale source/candidate, occupied parking destination and corrupt recovery.
Barriers deliberately force the worst publication intervals; this is not a
statistical stress or arbitrary-API proof. Replay is safely rejected; exact
idempotent product receipt replay remains a 22C integration gate.

Test host: Windows 11 build **26300**, Python **3.14.3**, local NTFS. Windows 10,
other builds/filesystems, emulator save-state reloads, memory mappings for this
new method and power loss are **not certified**. The harness first encountered
two error-reporting assumptions (Python file opens omit winerror; a replacement
denial returns 5 rather than 32). It now uses CreateFileW for the independent
writer and verifies 5/32 denials plus successful unguarded controls. No product
code or safety requirement was loosened. All new temporary trees were removed.

Private final evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase22b/20261022/`:
`handoff-evidence.json` and `cooperative-lifecycle-final.json`. Structured report
embeds the sanitized results. Ruff, format and compile pass. Prior 68 focused
tests and native/export/package evidence remain unchanged-source evidence, not
new runs. No full matrix, packaging or deployment was repeated.

## Recommendation and required approval

Recommend qualifying **managed-emulator automatic application using this
no-replace handoff**, conditional on approval of the temporary missing pathname.
This is not manual export: success updates the selected path automatically.
Neither this recommendation nor a process-name check certifies an emulator.
The [archived Citra directory contract](https://citra.azahar-emu.org/wiki/user-directory/)
only establishes a configuration seam, not current Azahar lifecycle guarantees.

**Narrow owner decision:** accept that the save pathname may briefly be absent,
and after a Launcher crash remain absent until recovery, with the supported
emulator prevented from reopening until reconciliation; external conflicts
must abort and preserve both versions. If continuous atomic path availability
is mandatory, this proposal fails A and automatic application stays blocked.
The present instruction explicitly requires approval before reducing that
guarantee, so 22C/22E cannot start on this result.

If approved, 22C should extend the **existing** journal: bind original identity,
hash, native plan and candidate; durably record parking/publication intent;
reconcile actual names/file identities/hashes before retry; never overwrite a
conflict; reuse the existing sync exclusion and backup engine; issue
APPLIED_VERIFIED only after native readback at the selected pathname. Qualify a
pinned real emulator adapter, graceful close/exit/flush and restart exclusion.
Reject unknown emulators, network/cloud-synced/reparse paths and unqualified
filesystems. Then test integrated crash/replay/IPC/offline behavior and target
Windows configurations; only afterwards consider a private candidate and clean
installation/signing. Hardware durability remains a separate release gate;
[Microsoft's buffering guidance](https://learn.microsoft.com/en-us/windows/win32/fileio/file-buffering)
does not place all hardware caches under OS control.

Purchases debit coins **at purchase time**. Item use, physical application and
confirmation are separate; this experiment does not consume inventory or
entitlements. Export never confirms application. No business rule changed.

**Production writes: NO. Public Launcher change: NO. Phase 23: NOT STARTED.**

[Structured evidence](phase22b-architecture-feasibility-evidence.json) · [Live handoff](work-in-progress/phase22-save-writes-live.md)
