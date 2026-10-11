# Phase 12 - live execution record

Closed 2026-10-11 Europe/Madrid. **STATUS: PHASE 12 DONE.**
**PHASE 13 READINESS: READY FOR REPRESENTATIVE STAGING.**
**Phase 13 NOT STARTED. No cutover. STOP.**

[Shadow report](../phase12-shadow-report.md),
[structured evidence](../phase12-shadow-evidence.json),
[Phase 11 fixed reference](phase11-live-handoff.md),
[project checkpoint](../project-checkpoint.md).

## Final source and scope

Entry main/origin `abc57754f12a60be4dbd0c921636eb1a50a7c06a`, fetched 0/0,
tracked tree clean. Implementation, tests and structured evidence committed and
pushed as `a50497f3603fafa96a8a1fc763588255379f665e`. Documentation closure follows
in a separate commit; obtain the final HEAD from Git.

`tools/phase12_shadow.py` is a deterministic, private, read-only comparator.
It uses the fixed retained Phase 11 source, the hosted private reference and
existing V2 readers/DTOs/validation guards. All seven surviving domains were
compared. **92 MATCH / 6 EXPECTED_DIFFERENCE / 22 UNKNOWN / 8 NOT_APPLICABLE /
0 BLOCKER**, across 128 checks/facts. No product or migration defect was found.
No application, SQL, parser, UI, reward or lifecycle contract changed.

Expected differences concern isolated identity annotations, legacy day/lifecycle
semantics, save evidence versus modern acceptance, already-counted pending spend,
derived wallet versus ledger and uncertified legacy Cup. Missing facts remain
unknown; absent historical domains remain not applicable. Eight badges do not
prove Champion defeated. Private source facts are not current competitive truth.

## Verified final remote state

V2 `uwleqeuzsveqlugugzba`: 34 migrations, 042=`20261011160629` once. Run
`61e5eb57-34f5-57f9-9252-4ea8be8d8b66` remains reconciled, six receipts,
57 deterministic mappings, 135 rows in 15 `v1_shadow` tables.

Entry and final read-only observations (2026-10-11 16:24:47 and 16:32:21 UTC)
are equal: 34 migration records, all 59 original public/Auth/Storage table
count/hash records, stable owner identity/credentials, private security catalog
and complete Shadow export. The owner's active season, economy, results and
Team Locks are preserved. No reward or ledger event was created. Shadow remains
private with forced RLS and no browser/service-role table or schema access.

Ten queries total, all Management API `read_only: true`. Zero remote writes,
imports, migration replays, Auth calls, Storage-byte operations or deployments.
V1 was not contacted or changed; the fixed verified source bundle was used.
Storage metadata is exact; no fresh full hosted byte-download proof is claimed.
Advisor and hosting evidence were not rerun for this read-only tooling change.

## Validation and evidence

13 focused tests PASS. One final full Python closure **798 PASS**, including
19 pre-existing unrelated untracked map tests. Ruff/compile/diff PASS. Three
comparison outputs are byte-identical, including a fresh final hosted export;
five consumed source files match the original retained copy manifest. Final
report-file hash:
`5afd8a487471e323235e4a0d7f1241dd9d7646e7c9643894e35e20ebaef6b804`.

No React/browser/native-parser rerun: unchanged source. No PostgreSQL execution
was necessary for these pure reader/DTO/guard comparisons; Phase 11 relational
proofs remain retained evidence. Local PostgreSQL stayed stopped.

Private Phase 12 evidence, 29 copied files with verified hashes:
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase12/20261011/`.
Fixed source:
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase11/20261009/`.
Working logs: `%TEMP%/phase12-shadow-20261011/`.
Raw source settings contain credentials and must remain private.

## Exact next action

No Phase 12 work remains. Await the owner's **Phase 13 representative staging**
instruction, then reconcile the current source and remote state before acting.
Do not restart Phase 11, replay imports, promote private facts, merge identities,
invent missing history or cut over. Readiness here is for representative staging,
not release. The protected guide and unrelated untracked files remain untouched.
