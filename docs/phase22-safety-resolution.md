# Phase 22 — Windows safety resolution

2026-10-20. Entry `e5cb0821b96d0f7945e2e5ff4f19a32873fe20b1`.
**STATUS: PARTIAL / public writes disabled.**
**Recommendation: integrate verified export to a new file, keeping the selected
original unchanged.** Export is not application to the game. This investigation
does not certify automatic replacement or release the Launcher candidate.
[Evidence](phase22-safety-resolution-evidence.json),
[live handoff](work-in-progress/phase22-save-writes-live.md).

## What Windows actually guarantees

The sharing checks are enforced by Windows, unlike an application mutex.
A read handle without write/delete sharing rejects conflicting ordinary file
opens; a pre-existing writable mapping also prevented acquisition in our test.
They protect the opened object while held, not future pathname ownership.
[CreateFile](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).

`ReplaceFileW` opens its target with DELETE access and accepts no expected file
identity/hash. Keeping the strict handle blocks our replacement too. Allowing
delete sharing or closing that handle let a separate process replace the target
before our replacement; the external bytes survived only in the displaced
witness. Handle-based source rename does not make destination replacement a
compare-and-swap. These races were reproduced, not inferred solely from docs.
[ReplaceFileW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew).

Oplocks coordinate caching and break notifications; they are not a universal
permission barrier. In-place writes lose atomic crash safety, and moving the
original aside before publication changes the original early and leaves a gap.
Neither is adopted as a replacement for the current safety requirements.
[Oplocks](https://learn.microsoft.com/en-us/windows/win32/fileio/opportunistic-locks).

**TxF is a real counterexample to claiming Windows cannot do this.** Acquiring a
transactional read/write handle before validation blocked independent writers
and replacers with error 6800, even after the file handle closed while the
transaction remained active. Readers saw old bytes until commit. Commit published
the candidate; rollback and forced process termination preserved the original.
This proves feasibility on this Windows 11/NTFS host, not general product support.
Microsoft discourages new TxF dependencies and warns about future availability.
[TxF isolation](https://learn.microsoft.com/en-us/windows/win32/fileio/txf-basic-concepts),
[Microsoft recommendation](https://learn.microsoft.com/en-us/windows/win32/fileio/transactional-ntfs-portal).

## Options

| Option               | Demonstrated guarantee                                                                        | UX and recovery                                                                                             | Eight-game compatibility                                                                 |
| -------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Existing replacement | Detects the reproduced race after displacement; cannot certify no lost newer pathname version | Convenient automatic application; backup/witness require recovery                                           | Existing eight-game native PASS retained; filesystem blocker remains                     |
| TxF                  | External mutation denied; commit/rollback/process-death isolation on this host                | Could support automatic application; needs OS/filesystem qualification and transaction recovery integration | Byte-oriented mechanism, but only dummy files tested here; no game integration claimed   |
| **New-file export**  | Original is read-only; publication cannot overwrite an occupied destination                   | Additional explicit user step; original remains usable, incomplete exports never count as applied           | Reuses unchanged eight-game native adapter; one real X copy validates the new connection |

## Isolated prototype and proof

`tools/phase22_safe_export.py` is fixture-only and is not imported by the Launcher.
It holds the original read-only without write/delete sharing; creates a fresh
stage with `CREATE_NEW`; writes, flushes and natively verifies it through the
same held handle; then publishes that object under a new basename without
replacement. Publication uses `NtSetInformationFile(FileRenameInformation)` with
a held destination-directory handle. There is no overwrite/copy/delete fallback.
The Win32 wrapper rejected the relative-directory operation with error 87;
the native operation passed the subsequent adversarial tests.
[Rename semantics](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_file_rename_information),
[native API](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/nf-ntifs-ntsetinformationfile).

New evidence only: **7 sharing/rename scenarios, 3 TxF scenarios, 9 distinct
export tests, and one real X fixture-copy native integration PASS**. Export tests
cover hostile write/rename/replace, occupied destination, prior writer/mapping,
two concurrent publishers, process death before/after publication, later edits
and rejection of a valid but unpublished partial file. The native test verifies
a genuine marking change, unchanged reader/digest and original bytes. The eight
initial export tests have retained tool output; only affected recovery tests
were repeated after tightening partial-file rejection. Ruff/format/compile pass.
Prior native225/Python69, eight-game and packaged gates were not rerun.

The receipt is `EXPORTED_VERIFIED`, `applied_to_source=false`. It does not consume
an entitlement, change the cloud current save or authorize later replacement.
Read-only crash inspection requires the exact retained plan/source and published
name; it never restores or reapplies automatically.

Limits: after handles close, other software may change either file. Directory
sharing is not universal protection against attribute/reparse attacks,
administrator/kernel interference or handle injection. Process-crash tests and
flushes do not prove power-loss/hardware durability. This prototype has no new
durable journal or UI integration. Later manual substitution remains outside its
guarantee; closing an emulator is advice, not proof of universal exclusion.

## Concrete next implementation

Within Phase 22, integrate an explicit **Export validated save** operation into
the existing journal, backups and native verifier. Persist the export intent,
destination and prepared hashes before publication; reconcile uncertain outcomes
read-only. Show exported and applied as different states. Preserve the original
and refuse destination collisions; do not add automatic replacement or mark a
competitive action consumed merely because export succeeded. Handle any later
application/entitlement policy as a separate contract.

No product engine, native codec, backup implementation or candidate was rebuilt.
No owner save, production, schema, economy or public Launcher 0.20.0 changed.
Research artifacts remain private; temporary test trees were cleaned and no
research helper remains. The previously documented policy-blocked build directory
was not retried. Commit this isolated evidence/prototype and stop; no Phase 23.
