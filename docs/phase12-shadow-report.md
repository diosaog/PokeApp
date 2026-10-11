# Phase 12 - Private Shadow comparison

Closed 2026-10-11 Europe/Madrid. **STATUS: PHASE 12 DONE.**
**PHASE 13 READINESS: READY FOR REPRESENTATIVE STAGING.**
[Structured comparison and preservation evidence](phase12-shadow-evidence.json),
[live handoff](work-in-progress/phase12-live-handoff.md).

## Entry reconciliation

Entry main/origin `abc57754f12a60be4dbd0c921636eb1a50a7c06a`, fetched 0/0,
clean tracked tree. The current Phase 11 report, handoff, mapping and direct code
dependencies were used; the migration was not restarted or rebuilt.

V2 `uwleqeuzsveqlugugzba` still has 34 migrations, with 042 applied once as
`20261011160629`. Private run `61e5eb57-34f5-57f9-9252-4ea8be8d8b66` remains
reconciled: six batch receipts, 57 deterministic mappings and 135 rows across
15 `v1_shadow` tables. All 59 original public/Auth/Storage table count/hash records
and stable owner credentials match the Phase 11 final baseline.

## Implementation and comparison

[Comparator](../tools/phase12_shadow.py) is private, read-only tooling. It compares
a single-statement export of the fixed Shadow reference against the retained
verified Phase 11 source bundle. It validates identity, provenance, source bytes,
unknown values and journal completeness, then exercises current V2 pure readers,
DTOs and validation boundaries. It does not invoke imports, migration rendering,
legacy runtime readers, rewards or competitive mutations.

The seven surviving domains receive explicit classifications: trainer identities,
League context and A/B memberships, save continuity, progress, economy, pending
purchases and legacy Cup. There are **128 classified checks/facts**:

| Classification      | Count |
| ------------------- | ----: |
| MATCH               |    92 |
| EXPECTED_DIFFERENCE |     6 |
| UNKNOWN             |    22 |
| NOT_APPLICABLE      |     8 |
| BLOCKER             |     0 |

MATCH includes integrity checks as well as business facts. Current V2 behavior is
exercised through `TrainerRead`, `SeasonLifecycle`, `ObservedSave`, progress
readers, `ShopRead`, `PurchaseStatus`, Cup value objects and the modern Cup rules
validator. This proves interpretation at those boundaries, not live competitive
settlement or certification of absent history.

The six expected differences preserve supported truth:

- Private trainer UUIDs and candidate V2 annotations do not merge accounts or copy credentials.
- The legacy day-editing flag and documented lifecycle fallback remain outside the public active-season lifecycle; missing start dates stay null.
- The exact private save and neutral parser observation do not allocate modern Pokémon identities, accept a competitive current save or create a Team Lock.
- Pending V1 purchases already contribute to legacy spending; they are not debited again or treated as redeemed.
- The private wallet is a derived opening snapshot, not a reconstructed modern ledger or permission to issue rewards.
- The legacy Cup has no modern rules version. The current certification validator correctly rejects that input with `UNSUPPORTED_RULES`; no champion or certificate is invented.

Anto's surviving evidence remains eight Unova badges, Champion false, five Box-8
occupants and private balance `32 - 24 = 8`. Badges do not imply Champion defeated.
The 22 UNKNOWN findings cover nine missing progress observations, nine missing
balances, League start/rule timing, save-upload timezone, historical adjusted-death
contributions and missing purchase mapping/timing history. Explicit zero Cup
standings remain observed zero.

The eight NOT_APPLICABLE domains are results, official rankings, Team Locks,
redemptions, promotions, sanctions, championship and Hall/archive. No deleted
history was reconstructed. No migration defect or current V2 product defect was
found; there was no product fix, schema change or runtime deployment.

## Validation

[Focused tests](../tests/test_phase12_shadow.py): **13 PASS**. They cover invalid
references, altered identities/owners/divisions/save/economy/purchases/Cup,
unknown versus zero or false, exact decimal mismatch detection, current-reader
regressions, timestamp equivalence, deterministic ordering, input immutability
and sanitized output. Migration-reference defects are explicitly distinguished
from current V2 interpretation defects; neither is silently repaired.

One final complete Python run: **798 PASS**, including 19 existing unrelated
untracked repository-map tests. Ruff, compilation and diff checks pass. Three
executions, including the final live read-only export, produce byte-identical
comparison files: SHA-256
`5afd8a487471e323235e4a0d7f1241dd9d7646e7c9643894e35e20ebaef6b804`.
All five consumed source files still match the retained Phase 11 copy manifest.

No frontend or parser source changed, so browser/React/native-parser suites were
not rerun. No relational execution was needed for the surviving reader/DTO/guard
comparisons; Phase 11 PostgreSQL rebuild, rollback and replay evidence is retained,
not presented as newly executed. Local PostgreSQL remained stopped.

## Remote preservation and privacy

Ten Management API database queries were executed, all with `read_only: true`:
five at entry, five at closure. Entry `2026-10-11T16:24:47.548861+00:00` and final
`2026-10-11T16:32:21.096619+00:00` captures agree exactly for migration history,
the 59 original table records, owner identity/credentials, private security and
the full 15-table Shadow export, including receipt timestamps and saved bytes.
No rewards, ledger entries or public/manual competitive data changed.

No V1 requests, Auth operations or Storage byte operations were performed.
Storage metadata remains exact; this is not a claim of fresh downloads of every
hosted Storage object. The retained V1 source/save bytes are unchanged. All
15 private tables retain forced RLS and postgres ownership; PUBLIC, anon,
authenticated and service_role still have no schema/table/column access. No new
policy, function, trigger, external foreign key or browser API exposes Shadow.

Raw evidence remains private at
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase12/20261011/`; all 29 copied files
were verified against their original hashes. Committed evidence contains no
credentials, raw save bytes or private Pokémon metadata. Advisor and deployment
observations from Phase 11 are retained, not claimed as freshly rerun. No Railway
or Cloudflare deployment was needed or performed.

## Git and next step

Implementation/tests/structured evidence committed and pushed as
**`a50497f3603fafa96a8a1fc763588255379f665e`**. This report, the live handoff and
checkpoint are carried by a subsequent documentation closure commit; Git records
its exact final HEAD, avoiding a self-referential hash. Explicit staging only;
the protected guide and unrelated untracked files remain untouched.

**NEXT: PHASE 13 REPRESENTATIVE STAGING**, after its own execution instruction.
Phase 13 is **NOT STARTED**. Shadow validates only surviving fixed facts; live
synchronization, representative gameplay and release/cutover remain outside this
closure. No cutover occurred. Stop here.
