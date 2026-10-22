# Phase 22 - safe native save writes

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
