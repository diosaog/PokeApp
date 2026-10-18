# Phase 18 — ORAS read/import

2026-10-18. **STATUS: PHASE 18 DONE — ORAS PUBLIC GAMEPLAY FIXTURE FOLLOW-UP PASS.**
Application source `e7833440f0c77579a82a9f00a030ab6cdd27619c` committed/pushed
before all remote writes. [Report](../phase18-oras-read-report.md),
[sanitized evidence](../phase18-oras-read-evidence.json).
Entry main/origin `08f00acd3a06a579e899c3e19454ea5be896c222`, clean tracked tree.

At initial delivery the owner had no authentic ORAS files and authorized continuing
without their tests: real-save acceptance was NOT RUN and phase status PARTIAL.
The subsequent public-fixture search and local proof below supersede that evidence
gap. A Black/White save cannot validate ORAS. No owner save was used or changed.

Native PKHeX 24.11.11 now accepts decrypted OR/AS saves, validates checksums/game/
form, emits neutral form-specific types, and preserves existing X/Y wire digests.
Existing atomic raw-save registration, CAS, replay and ownership boundaries are
reused. Forward 045 changes only two game allowlists in the service-only RPC;
044 is unchanged. Gen6 competitive identity/progress remain unsupported/UNKNOWN:
no new entities, rewards, flags, Team Locks or historical facts are synthesized.
Web shows game, forms, types and ORAS move/item names; missing form art stays
unavailable. Private fields remain self-only. Launcher 0.18.0 is built locally.

Completed focused evidence: native synthetic OR/AS/X/Y; Python 5 ORAS, 9 X/Y,
13 ingestion, 24 frontend-read tests; 33 affected React, two desktop/mobile ORAS
browser tests with screenshots reviewed. Real disposable PG: migration/bootstrap
parity through 045, four-game registration/replay/concurrency/CAS/rollback/privacy,
browser denial, exact 54-table restoration and disposable databases dropped.
Installer audit and packaged parser/core offline reads pass for all four games.
Build, targeted critical Ruff, compile and diff checks pass. No full historical
matrix was repeated. Browser API fixtures, external Auth and local object-storage
substitutes are not positive hosted-import proof.

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase18/20261018`.
Release: `%LOCALAPPDATA%/PokeApp-releases/0.18.0/release/PokeApp-Launcher-Setup.exe`,
159086220 bytes, SHA-256
`63c3c1373f6cdb32871f8101350d88e9b89da190cf774a7407960f40c0819fbb`.
Unsigned, no fresh clean-machine installer acceptance. The first packaged smoke
sample caught the network attempt still in flight; the bounded final check waited
for OFFLINE and proved local reading continues, without changing product code.

Remote entry: V2 36 records through 044=`20261014164204`; 59-table baseline and
Advisor captured. API deployment `927587fd-037e-44ad-b95f-7480d67be333` SUCCESS;
Cloudflare `b8a17250-3bdd-4bb8-a93b-41fcfb097e99`, version
`9f1704e5-872d-4688-bfed-3eb69be036e4`. This was the pre-write entry.

Delivery complete: 045 once as `20261018105158`, prior 36 records unchanged.
Railway `2253b885-dc35-43b4-8b93-773fd628656f` SUCCESS, 256 committed inputs,
image `sha256:73681da8e8128d35fb5c05fed85585cbb38f682d61c84fee5dc4bb52749fac98`.
Cloudflare `411aeb3d-a68a-4d8c-8327-22430a97ba95`, version
`e48fd707-900b-4597-a181-ca3eca114caa`, 100%, same source. Only new R2 key
`windows/0.18.0/PokeApp-Launcher-Setup.exe` uploaded; hosted size/hash match above.
12 public HTTP checks PASS, three live JS/CSS assets match the local build, no
unexpected 5xx. No PIN, hosted positive import or owner business mutation.

59/59 tables identical across immediate preapply/final baselines. Against initial
entry, 56/59 identical; only owner Auth users/sessions/refresh activity changed
before preapply, with stable credentials/identity unchanged and one Auth user.
Private inbox, business data, Storage metadata and security catalog unchanged.
Advisor 24 ERROR / 5 WARN / 171 INFO, no ERROR/WARN differences. Remote function
body matches committed SQL; invoker/fixed search_path/service-only grants pass.

Dedicated PG on 55468 stopped, its two disposable databases already dropped;
no packaged core/parser process remains. The stopped synthetic cluster directory
is retained at `%TEMP%/pokeapp-phase18-pg`; release and evidence retained privately.
Rollback remains available through prior API/web deployments and restoring the
044 function without deleting accepted saves/receipts. No rollback performed.
No V1, Shadow business data or physical save writes. Protected/unrelated files
remain untouched. Documentation closure is the subsequent commit: obtain exact
final HEAD from Git, avoiding a self-referential hash.

## Follow-up: fixture availability and release gate

Resume entry `6a219a4176048102588aae25172c71fdcd98bffc`, fetched 0/0, clean tracked.
Owner's latest instruction requires legitimate fixture discovery and blocks
unverified save-ingestion deployment; missing real saves must not block ordinary
development. This rule supersedes the initial waiver for future releases. The
earlier ORAS deployment is retained as historical fact, not relabeled as having
had real-save proof before publication. **No new remote write/deployment here.**

Three public contributor gameplay saves found: Minay's OR, Melampus's AS start
and AS current. Provenance/links/hashes in
[manifest](../../tests/fixtures/phase18-public-saves.json) and the report. These
are not PokeApp-generated saves; author-described gameplay provenance does not
attest hardware origin, lack of edits or Pokemon legality. Packaged parser/core
offline reads PASS. Final real local PG gate PASS: OR 415 occupied slots, AS
0 -> 30, replay/concurrency/rollback/ownership/privacy, no stale rewind, source
bytes unchanged, no fabricated identity/reward/locks. 54-table restoration; all
disposable DBs dropped and PG stopped. Only runner/manifest/docs changed.
Prior synthetic/parity/UI evidence remains retained, not rerun.

Private evidence: existing phase18 directory plus `fixture-review/`:
`download-results.json`, `packaged-public.json`, `pg-public-final/result.json`.
Raw files/observations stay private and outside Git. Setup/harness-only failures
and final results are documented in the report. No production fixture import.

Upstream pinned `SM Project 802.main` is available as a test resource. It is not
proof of authentic gameplay for both Sun and Moon; Ultra Moon is not a substitute.
**Sun/Moon real-save validation and dependent deployment: BLOCKED** pending
appropriate evidence/implementation. Ordinary implementation remains unblocked;
Gen7 is NOT STARTED and this follow-up does not authorize the next phase.

**NEXT: owner acceptance of the published ORAS feature.** Gen6 competitive identity,
progress mapping, bag inventory, alternate form art and full Launcher Spanish
presentation remain outside this read/import increment. No Phase 19 started.
