# Phase 22A - safe automatic save replacement

Observed 2026-10-22. **STATUS: BLOCKED for automatic replacement; Phase 22
remains PARTIAL.** The existing verified exporter is retained and remains the
only release-safe write-like operation. No production write capability is
enabled.

## Reconciled state

Entry and current application HEAD are `58cbe8261da0e9537f2d69e29b71c8a2e488d0be`,
with `origin/main` aligned. There were no tracked changes to recover. The
unrelated untracked files remain untouched, including the protected guide.
The current implementation already contains the native eight-game writer,
durable journal, backups, recovery, Launcher exclusion and verified new-file
export. No new code was justified in this packet.

## Safety result

The required final behavior is automatic replacement of the selected original
save. Windows sharing handles protect the opened object while held but cannot
reserve future pathname ownership. `ReplaceFileW` has no expected identity or
hash compare-and-swap parameter. Keeping strict no-delete sharing blocks our
own replacement; releasing it or allowing delete sharing permits an independent
process to replace the pathname after validation and before publication. In-place
writes lose crash atomicity, moving the original aside creates a gap, and
oplocks/process-name checks/user confirmation do not provide a universal barrier.

TxF remains a useful counterexample: the existing dummy-file experiment showed
commit, rollback and process-death isolation on this Windows 11/NTFS host. It is
not product-qualified, Microsoft discourages new TxF dependencies, and the
experiment does not establish support across target Windows/filesystem
configurations. It is therefore not adopted as a hidden dependency.

Under the required non-cooperative external-writer threat model, no defensible
software-only automatic replacement method is currently proven. Claiming
`APPLIED_VERIFIED` here would overstate the evidence, so the production mutation
registry remains empty and automatic source replacement stays disabled.

## Current validation

The affected current-HEAD matrix was executed once for this resume:

`test_phase22_safe_export test_phase22_write_engine test_phase22_native_bridge
test_phase22_launcher test_phase22_export_engine` — **68 tests PASS in 13.165 s**.

The eight-game journaled export proof, package audit and two isolated packaged
Launcher runs remain valid from `58cbe82`; they were not rerun because 22A made
no code changes. The eight supported formats remain X, Y, OR, AS, SN, MN, US and
UM. Export finishes `EXPORTED_VERIFIED` with `applied_to_source=false`; partial
or uncertain output remains `RECOVERY_REQUIRED`, and no economic or competitive
effect is inferred.

## Remaining gates and next action

A future automatic-write attempt needs a supported OS/filesystem-level
transactional or driver mechanism qualified on every target Windows/NTFS
configuration, including independent writers, rename attempts, interruptions,
restart reconciliation and exact replay. If that mechanism cannot be supported,
the Product Owner must explicitly decide whether export-only application is an
acceptable product rule; the safety criteria must not be weakened implicitly.

After a valid automatic-write design exists, clean-machine installation/signing
and post-apply parse/reverification gates remain. Any future purchase must wait
for a distinct verified applied receipt after the user-selected save has been
reparsed; export alone never consumes an entitlement.

No Railway, Cloudflare, Supabase, public Launcher, owner save or competitive
state changed. No Phase 23 is started.

[Structured evidence](phase22a-write-safety-evidence.json) · [Phase 22 live handoff](work-in-progress/phase22-save-writes-live.md)
