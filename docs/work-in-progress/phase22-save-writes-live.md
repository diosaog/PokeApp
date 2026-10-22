# Phase 22 - safe native save writes

## Current checkpoint - 22C + targeted 22D, 2026-10-23

**DONE LOCAL ENGINEERING / CONDITIONAL RELEASE. Phase22 PARTIAL; production OFF.**
Entry `457bc30e15468648cb5e195b06dd1cf00f3be93a`, fetched main/origin 0/0.
Owner instruction `5f966a98-e706-4d36-93d5-cd358cfd4c6e` authorizes the absent-path
handoff for integration/tests only. This supersedes 22B's approval stop below;
it does not approve public release, real-save writes or an unqualified emulator.

Existing engine/SQLite journal now durably records exact independent backup,
verification, source/candidate identities and no-replace parking/publication
intent. Backup precedes native mutation preparation. Application and explicit
restore validate the final pathname natively; restore also preserves the current
candidate independently. Interrupted operations reconcile hashes AND identities;
external collisions are preserved, never replaced. Legacy replacement is disabled.
Spanish backup history shows game/date/validity and recovery state. Native-dialog
**Guardar copia** works without native parser or cloud credentials. Copy does not
apply anything to the game. Restore requires explicit closure/confirmation and
engineering capability; production runtime has none. No real restart inhibition
is claimed merely from UI flags. Save/sync leases remain shared.

Fresh combined evidence: **74 unique affected Python tests** (59 existing affected,
13 new boundaries, 2 targeted runtime regressions); **8 authentic fixture-copy
games** pass backup/apply/replay/copy/restore/native validation. **Two isolated dev
Electron launches**, with/without native parser, pass exact copying, corrupt-backup
UI and ten IPC denials. Final UI delta verified separately. Compile, targeted
Ruff, Python/JS/HTML/CSS formatting, node syntax and diff pass. No historic/full
matrix, PG, package build or remote gate repeated. Test-only fault-hook/import/
stdin harness corrections are detailed in evidence; they are not hidden PASS.

[22C report](../phase22c-backup-application-report.md) and
[structured evidence](../phase22c-backup-application-evidence.json).
Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase22c/20261023/`.
Eight-game/test temporary trees removed; dev Electron/core processes ended.
The deliberately corrupt disposable UI backup/profile is retained as negative
private evidence, with its untouched source copy. Earlier cleanup residue untouched.
Five unrelated untracked files preserved. Public Launcher0.20.0/private rc.2
retained, no new package; no owner save, production, database or economy writes.

**Remaining release gates:** pinned real emulator graceful close/save flush/exit
and restart exclusion (none qualified); absent-path/recovery product acceptance;
power-loss durability policy/evidence; supported Windows/filesystem/mapped-I/O
qualification; integrated packaged/clean-machine/signing acceptance; business
item-use authorization and verified application receipt before entitlement use.
Purchases debit at purchase time; this work neither reverses nor consumes them.

**Exact next packet:** qualify one pinned real emulator adapter with a legal
owned test title/save in an isolated environment, prove restart denial during
gap/recovery and unsupported-state refusal. Do not enable production meanwhile.
No Phase23 or profiles. The focused closure commit carries this record and report;
obtain its exact HEAD from Git rather than a self-referential hash.

## Current checkpoint — 22B publication proof, 2026-10-22

**CONDITIONAL — OWNER DECISION REQUIRED. Phase 22 PARTIAL; production writes OFF.**
This supersedes the historical next actions below, including manual export as
the proposed final UX. Entry HEAD `58cf806c273fd0e551e10ae6422b2fff187fbc41`,
fetched main/origin 0/0. The interrupted 22B tool, report/evidence and two document
changes were preserved and completed; five unrelated untracked files untouched.

New tools-only proof publishes a validated candidate at the selected **disposable
original pathname**, retaining the source under a recovery name. Supported Win32
handle-based renames use no replacement; both files deny other write/delete
opens until verification. Independent writes/replacements are denied while
guarded; if an external creator wins the gap, our publication fails and preserves
its bytes. **The pair of renames is NOT atomic: the original pathname is absent
between steps and can remain absent after process death.** No weaker contract
was approved and no product writer/IPC/registry/journal was changed.

Fresh PASS: **8 native game publications** (X/Y/OR/AS/SN/MN/US/UM), **27 scenarios**
(guards, gap conflicts, four process deaths, recovery/corruption, stale intent,
competing process, replay and positive attack controls), **4 probe-control tests**,
and corrected inherited cooperative lifecycle proof. Real fixture hashes stayed
unchanged; temporary probe trees removed. Ruff/format/compile/diff pass.
Inherited **68 tests**, prior native/export/packaged matrices retained; not rerun.
The new recovery oracle is a tools experiment, not integrated SQLite recovery.
Only Windows 11 build26300/local NTFS tested; no real emulator, Windows10,
power-loss, new-method mapping, signing or clean-install certification.

Evidence: [22B report](../phase22b-architecture-feasibility-report.md),
[22B JSON](../phase22b-architecture-feasibility-evidence.json), private
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase22b/20261022/`.
No production access/deployment, owner save or economy change. Public Launcher
**0.20.0 unchanged**, private **0.22.0-rc.2 retained**; no new candidate.

**Exact next action:** owner accepts or rejects the temporary missing-path /
recovery-before-emulator-restart contract. If accepted, integrate this mechanism
into the existing journal/backups/sync exclusion and qualify a pinned emulator
adapter, crash/replay/IPC and Windows configurations before private packaging.
If continuous atomic pathname availability is required, automatic application
remains blocked. Export remains available engineering evidence, not the final
automatic product. Purchases debit at purchase; item application is separate.
Documentation/probe closure commit carries this checkpoint; obtain its full HEAD
from Git. **STOP before 22C integration pending that decision; no Phase23.**

Entry 2026-10-20 Europe/Madrid: `77c2f18f9e07db19c5c6e58446fbcfd830228977`,
main/origin 0/0, clean tracked tree. **STATUS: PARTIAL / PUBLIC RELEASE BLOCKED.**
Phase 21 accepted; identity/progress rewards remain gated.

## Safety resolution follow-up — 2026-10-20

Entry `e5cb0821b96d0f7945e2e5ff4f19a32873fe20b1`, fetched main/origin 0/0,
tracked tree clean. **Phase22 remains PARTIAL; public writes disabled.**
[Safety recommendation](../phase22-safety-resolution.md),
[new evidence](../phase22-safety-resolution-evidence.json).

The existing ReplaceFileW race is reproduced with independent processes.
Strict no-delete sharing blocks our own replacement; permitting it or releasing
the handle admits an external replacement. This does not prove Windows-wide
impossibility: TxF commit/rollback/process-termination isolation passed on this
Windows/NTFS host. Microsoft discourages new TxF dependencies; no release or
multi-platform qualification is claimed.

Recommended alternative: verified export to a new file, never replacement of
the selected source. An isolated tools-only prototype holds source/stage handles,
publishes through a directory-relative native rename with replacement forbidden,
and reports EXPORTED_VERIFIED / applied_to_source=false. It preserves originals,
refuses collisions and treats partial/uncertain files as read-only recovery
material. It does not grant entitlement, sync or automatic-application authority.

New PASS: sharing/rename **7 scenarios**, TxF **3 scenarios**, export **9 unique
tests**, native real-X fixture-copy integration **1**. Only affected recovery
tests were repeated; final Ruff/format/compile pass. Prior native225/Python69,
eight-game and package gates below remain retained, not rerun. Public0.20.0,
candidate0.22.0-rc.1, product code and owner data are untouched; no production
access or deployment. No new helpers remain. Private evidence:
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase22-safety-resolution`.

**Next recommended implementation:** integrate export intent/publication/recovery
into the existing durable journal and UI, with a distinct exported status and no
automatic replacement or economic consumption. Manual substitution is a separate
step, not certified by export. Close handles does not prevent later external edits;
power-loss and hostile metadata/kernel behavior remain outside this proof.
This follow-up supersedes the generic next action at the end of the historical
checkpoint below. Exact final commit is obtained from Git. **STOP; no Phase23.**

## Scope and current work

Implemented a byte-only native preparation/verification mode in the existing
pinned PKHeX worker, durable local write transactions, immutable backups,
atomic replacement, disk verification and crash reconciliation. A native
marking change is an engineering-only test; no production mutation kind, shop
redemption or cross-trainer operation is enabled. Original contributor fixtures
and owner saves remain read-only.

Eight-game public fixtures from prior phases now have new native-write and
Windows fixture-copy evidence, distinct from their earlier read certification.
Windows ReplaceFileW does not provide a compare-and-swap parameter; the exact
filesystem concurrency guarantee was not established; production writes stay
disabled. The adversarial test documents why below.

## Verified local checkpoint

Native **225 checks PASS**, all eight real contributor games; strict whole-file
and decrypted-slot preservation, native signatures/checksums, unchanged reader
DTO/digest. Self-contained pinned .NET 8.0.29 prepare/verify all eight PASS.
Python native adapter **10 PASS** plus eight-game real pinned-runtime proof.
Windows filesystem **29 PASS**, including six new-process crash boundaries,
cross-profile exclusion and adversarial external path replacement. All eight
real fixture copies pass prepare -> replace -> verify -> replay -> exact restore;
original hashes unchanged. Evidence retained privately at
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase22/20261020`.

The adversarial race confirms a release blocker: Windows `ReplaceFileW` has no
atomic path/hash CAS. The displaced witness preserves both versions and forces
recovery but detects the race only after replacement. Arbitrary renamed emulator
shutdown and sudden power-loss durability also remain uncertified. Production
mutation registry stays empty; only explicit in-process fixture capability may
write. No renderer/server path can grant it.

Final Launcher integration **16 PASS**; affected sync/offline regressions **14
PASS**. The old receipt is invalidated under the exclusive write lease before
sync can resume. Confirmation is bound to the exact journaled action; state
polling remains responsive, and absent write capability preserves ordinary reads.
The candidate `0.22.0-rc.1` builds/audits successfully. Two isolated packaged
Electron runs pass; packaged native writes/read digests pass all eight games.
Overall focused Python **69 PASS**, with compile/Ruff/JS/format/diff green.
Historical matrices were not rerun.

Application source **`62822a69370e7ee34d028c607a0d2c9d2644ddb3`**. Documentation
closure is a following commit; use Git for exact final HEAD. Explicit staging
only; unrelated/protected files remain untouched.
[Final report](../phase22-save-writes-report.md),
[sanitized evidence](../phase22-save-writes-evidence.json).

No remote changes or deployment. Public Launcher remains **0.20.0**; existing
owner installation **0.16.2** untouched. Private unsigned installer:
`%LOCALAPPDATA%/PokeApp-releases/0.22.0-rc.1`,
159147043 bytes, SHA-256
`cb234fc8936c7ab4cff3c7d5af92f81e5a7e3991e382985ca76c2dac295bd48d`.
Clean-machine installer acceptance is unperformed; unpacked-package proof does
not substitute for it. No DB/schema change; 41 records through049 retained,
Gen6/7 reward gates unchanged, no owner/competitive/backfill/V1/Shadow writes.
No new full production-table comparison claimed.

Test-owned fixture trees were cleaned and candidate processes ended. Automatic
approval review rejected exact build-root deletion with **blocked by policy**:
`%TEMP%/pokeapp-phase22-package-20261020` remains for manual cleanup. Installer
and evidence are safely retained; no bypass was attempted.

**NEXT:** resolve the external path-replacement/concurrent-program safety and
clean-machine release gates within Phase22. Reuse the finished implementation
and valid gates. Production operation registry stays empty. **STOP: no Phase23.**

## Export integration continuation - 2026-10-21

**STATUS: PHASE 22 PARTIAL / EXPORT INTEGRATION VERIFIED / PUBLIC PHYSICAL WRITES BLOCKED.**
The existing native engine, SQLite journal, IPC and Launcher now include a
capability-gated new-file export path. It records intent, source/output hashes,
backup, destination and recovery state; it never replaces the selected source.
`EXPORTED_VERIFIED` is distinct from `APPLIED_VERIFIED`, and export carries
`applied_to_source=false`. Partial or uncertain files remain
`RECOVERY_REQUIRED` and reconciliation is read-only. No business mutation,
reward, coin, purchase, robbery or competitive state is reachable from export.

Focused affected validation retained **58 Python PASS**. The journaled
validator passed on disposable authentic copies of **X, Y, OR, AS, SN, MN, US and
UM**: all eight `EXPORTED_VERIFIED`, originals unchanged, zero source applies.
The private unsigned candidate **0.22.0-rc.2** passed package audit and two
isolated Electron runs with packaged read `READY`, no login, forged-write
rejection, sandbox/context isolation and no owner file access. Correct installer
SHA-256 is `95b447f7fb787a2c5bb54a3b6110d6c0adbeb15c736b3a6a4f8e7cd41e18969e`
(159253386 bytes); it is retained under `%LOCALAPPDATA%/PokeApp-releases/0.22.0-rc.2`
with `NOT-PUBLISHED.txt`.

No Railway/Cloudflare/Supabase deployment or migration occurred. Public
Launcher 0.20.0, owner installation, saves, competitive history, economy and
rewards are unchanged. Automatic source replacement remains blocked because
Windows pathname replacement has no required external-writer CAS guarantee;
clean-machine installation and power-loss/arbitrary emulator certification also
remain open. A future purchase needs explicit user substitution, post-apply
parse/reverification and a separate committed applied receipt before consuming
any entitlement. Export alone never consumes.

[Export report](../phase22-export-integration-report.md) · [Evidence](../phase22-export-integration-evidence.json)

## Phase 22A resume - 2026-10-22

**STATUS: BLOCKED at safe automatic replacement; PHASE 22 remains PARTIAL.**
Current HEAD `58cbe8261da0e9537f2d69e29b71c8a2e488d0be`, origin aligned. The
interrupted session left no tracked code changes to recover. Existing native
write, journal, recovery and verified export implementation is preserved.

The current focused matrix was run once on this HEAD:
`test_phase22_safe_export test_phase22_write_engine test_phase22_native_bridge
test_phase22_launcher test_phase22_export_engine` -> **68 PASS, 13.165 s**.
No broader suites, database, deployment or owner data access were needed.

The blocker is unchanged and now explicitly closed for this packet: Windows
sharing handles protect the opened object, but `ReplaceFileW` has no expected
identity/hash CAS for the target pathname. Strict no-delete sharing prevents our
own replacement; releasing it or permitting delete sharing permits an external
replacement after validation. In-place writes, oplocks, process-name checks and
user confirmation do not provide the required universal guarantee. TxF passed a
limited dummy-file experiment on this host but is not product-qualified and is
not adopted as a dependency.

No defensible automatic replacement method is therefore proven under the
non-cooperative external-writer threat model. Production mutation registry,
`APPLIED_VERIFIED` for ordinary users, Railway/Cloudflare/Supabase, public
Launcher 0.20.0 and owner saves remain unchanged. `EXPORTED_VERIFIED` remains
safe within its tested scope, never modifies the selected source, and never
consumes a purchase/reward/coin or competitive effect.

First incomplete step: qualify a supported transactional/driver-level Windows
publication mechanism across target configurations, with adversarial writer,
interruption and restart proof. If none is supportable, obtain an explicit
product decision about export-only semantics; do not weaken the current gate.

[22A report](../phase22a-write-safety-report.md) · [22A evidence](../phase22a-write-safety-evidence.json)

## Historical interrupted Phase 22B assessment - superseded above

**DECISION: CONDITIONAL. PHASE 22 remains PARTIAL; production writes DISABLED.**
A generic Windows user-mode automatic replacement is still not defensible under
non-cooperative external writers. A narrower architecture is plausible for
explicitly supported emulators whose lifecycle the Launcher controls.

Guarantees are now separated: `ReplaceFileW` supplies atomic publication only on
a quiescent local NTFS path; a strict Launcher handle blocks ordinary cooperative
writers; independent rename/replacement is not protected; journal/backup gates
cover process interruption; power-loss durability and privileged actors remain
unproven/out of scope.

The tools-only PoC `tools/phase22b_cooperative_lifecycle_probe.py` passed on one
disposable real X save copy. The cooperative emulator opened exclusively, the
Launcher lock and rename were blocked while it was open, the close handshake
released the file, and an independent writer was blocked during the Launcher
lock. Bytes remained intact. Evidence:
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase22b/20261022/cooperative-lifecycle-evidence.json`.
No automatic publication or production capability was enabled.

**First incomplete step:** obtain Product Owner approval for a per-emulator
cooperative support boundary, then qualify the first adapter with process
ownership, close handshake, save-path ownership, journaled apply, post-apply
parse/reverification and adversarial interruption tests. Unknown/uncontrolled
emulators remain export-only. If the boundary is not accepted, automatic
application is NOT VIABLE under the universal contract.

[22B report](../phase22b-architecture-feasibility-report.md) · [22B evidence](../phase22b-architecture-feasibility-evidence.json)
