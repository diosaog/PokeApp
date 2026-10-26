# Phase26D — save engine hardening

2026-10-26. **PHASE26D DONE LOCAL (physical power-loss and Windows 10 PENDING).
Production UNCHANGED; public physical writes DISABLED.** Entry `40de23d`; 26C
PARTIAL only for deploy-dependent items (flexible gate: continue).
[Recovery procedure](save-engine-recovery-procedure.md).

## Changes

- **Parked originals** (`.displaced`) and restore outputs (`.restored-output`)
  are retired after terminal verification, bound to the journal's file identity,
  byte-checked against a verified profile backup, journaled before and after,
  deleted by handle (`FileDispositionInfo`). Any doubt keeps the file with the
  reason in the journal (`KEPT_CHANGED` never retried). Inherited residue from
  older runs is retired on reconcile. Restore after retirement uses the verified
  profile backup.
- **Save lock** `.pokeapp-write-<hash>.lock` now disappears with its exclusive
  handle; a held lock still refuses another Launcher (`WRITE_ALREADY_RUNNING`).
- Launcher: clear message when another instance holds the save; backups list
  shows whether the beside-save copy was retired or kept for safety. Players never
  handle `.lock`, `.displaced` or hashes.

## Evidence (Windows 11 Pro 10.0.26300, disposable NTFS)

- New residue tests 9/9: only `main` remains after a verified apply and after a
  restore; inherited residue retired only if byte-identical; changed copy kept as
  evidence; process killed inside retirement completes on restart; unknown files
  (`main.bak`, an unjournaled `.pokeapp-*.displaced`) never touched; held lock
  blocks and survives its holder; Unicode folder applied clean; 326-character path
  applied clean; read-only original refused with bytes intact.
- Existing process-kill test at every commit boundary still PASS.
- Real native regression on the shared protocol: quick items on **eight titles**
  (now asserting nothing but `main` beside the save), PASS; robbery closure on
  disposable PostgreSQL (X) PASS with retirement in transfer legs.
- 152 focused Python tests OK; Ruff no new findings.

| Gate | Result |
| --- | --- |
| PHASE 26C | PARTIAL (deploy-dependent) |
| SAVE ENGINE HARDENING | PASS |
| BACKUP INTEGRITY | PASS |
| DISPLACED FILE MANAGEMENT | PASS |
| LOCK MANAGEMENT | PASS |
| JOURNAL RECOVERY | PASS |
| INTERRUPTION SAFETY | PASS (process kill; power loss PENDING) |
| TWO-SAVE SAFETY | PASS (current protocol) |
| CLEANUP | PASS (beside-save artifacts; profile backups: daily policy, addendum) |
| WINDOWS 11 | PASS |
| WINDOWS 10 | PENDING |
| PHYSICAL POWER-LOSS TEST | PENDING |
| PUBLIC PHYSICAL WRITES | DISABLED |
| PHASE 26D | DONE LOCAL |

Pending, not blocking the queue: Windows 10 run, power-loss test, low-disk and
antivirus-lock behaviour on real machines. Ready for **27A** (authoritative
robberies, verifier).

## Addendum — daily backup retention (owner decision 2026-10-26)

One ordinary point per save and local date (state before the day's first write),
kept 30 days; transactional backups still created and verified before each
write; older ones retired only when provably redundant. Rules in the
[recovery procedure](save-engine-recovery-procedure.md#daily-retention-owner-decision-2026-10-26).
The 26D protocol (park, publish, verify, retire residue) is unchanged.

- New tests 8/8 (`tests/test_phase26d_daily_backups.py`, real NTFS): three
  writes in a day keep the first state and only the latest transactional backup;
  date change; 29 days kept, 30 expired, clock moved back keeps the newest;
  pending, failed/recovery and pre-policy backups untouched; unrecognized,
  tampered and externally changed files untouched; crash inside retirement
  completed after restart; crash between point and manifest keeps every backup;
  restored records keep both backups.
- Launcher UI smoke 26/26 (daily row with date and game, copy only).
- Engine/Launcher regression 138 tests OK (one historical assertion now also
  expects the daily row).
