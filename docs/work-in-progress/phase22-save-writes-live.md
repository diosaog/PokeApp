# Phase 22 - safe native save writes

Entry 2026-10-20 Europe/Madrid: `77c2f18f9e07db19c5c6e58446fbcfd830228977`,
main/origin 0/0, clean tracked tree. **STATUS: PARTIAL / PUBLIC RELEASE BLOCKED.**
Phase 21 accepted; identity/progress rewards remain gated.

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
