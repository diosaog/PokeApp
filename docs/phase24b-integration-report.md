# Phase24B — robbery integration in API, Launcher and web

2026-10-25. **PHASE24 DONE LOCAL. Production UNCHANGED; deployment NOT executed.**
Entry `089eb6acb876e346e204d735041d3b2ceb933e46` (24A DONE LOCAL, gate PASS),
main/origin 0/0, only the eight unrelated untracked files present.
[Evidence](phase24b-integration-evidence.json) · [24A report](phase24a-two-save-report.md)
· [Live handoff](work-in-progress/phase24-live.md).

24A systems were reused unchanged: native transfer, foreign-OT provenance,
competitive finalization, 057/058, `EngineeringTransfer` and the two-save journal.

## What was connected

- **Additive local 059_transfer_integration_reads.** Two gaps blocked any real
  client: a participant could not discover its legs nor receive its own plan
  (plans live only in a private table), and the restricted verifier had no work
  discovery. `api_transfer_list` (service_role) returns the caller's legs with
  ONLY its own side's plan while non-terminal. `transfer_verifier` gains a
  read-only `queue` operation by wrapping 058 (same role, same single function).
  No new write path, grant to clients, or historical migration change.
- **FastAPI** (`app/api/routes/transfers.py`), absent (503 / empty reads) unless
  `POKEAPP_TRANSFER_ENGINEERING_ENABLED=true` with an exact UUID cohort. Request
  uses the UUID Idempotency-Key as operation id; **both** participants must be
  in the cohort before anything is reserved, so an outsider's sync is never
  blocked. Status-only web list, Launcher list (own plan), leg get/ready/begin/
  cancel, octet-stream result upload, requester-only web withdrawal. Trainer
  scope is always the authenticated principal. No route issues a proof,
  completes a leg or consumes anything; raw object names/proofs never returned.
- **Private worker step** (`app/application/transfer_worker.py`): queue →
  existing `TransferVerification.prepare/verify/finalize`. Rejections issue no
  proof; transient/persistence failures retry; actions are idempotent.
- **Launcher**: `AuthenticatedTransferRemote` implements the exact `leg/submit`
  seam `EngineeringTransfer` already used, with Launcher-local wire models.
  `LauncherTransfers` binds only the trainer's own server plan, which the
  native engine revalidates (game, trainer, exact bytes, target). Runtime
  commands `transfer_prepare/apply/cancel/refresh` (explicit closed-emulator
  confirmation for prepare/apply) run on the existing write queue; discovery is
  cached as status only. Without an in-process `EngineeringCapability` — which
  no production build constructs — every command fails closed with a Spanish
  notice and does not pause sync. `PRODUCTION_MUTATIONS` remains empty. The
  Electron renderer shows read-only robbery status; no new IPC action exists.
- **Web**: the existing inventory shows the robbery button only when the backend
  enables the account, then per-leg states (pending, waiting, first part applied,
  second part, verification, completed, cancelled, blocked) plus a victim notice.
  "Robo completado" appears only on server COMMITTED.
- **Lime3DS**: reported as primary qualification candidate; Lime3DS/Azahar/Citra
  processes already block physical writes. No certification claimed.

## Validation

- **Disposable PostgreSQL17 + real FastAPI + two LauncherRuntimes + native PKHeX
  (Pokémon X), PASS 15/15.** Disabled service; outsider-victim refused before
  reservation; idempotent request and conflict; outsider/foreign-trainer
  denial; status-only web reads; one plan per worker run, own-leg plans only;
  both backups prepared; out-of-order application refused with files unchanged;
  donor apply ≠ confirmation; tampered, wrong-type, wrong-claim and foreign
  uploads refused; post-apply cancellation refused; restarted Launcher replays
  without reapplying; independent per-side verification; single finalization and
  identical replayed receipt; both Launchers and web COMMITTED, gates released
  and still released after restart; owner, both current saves, PC observations,
  one consumption + one voucher, deduplicated re-sync of result bytes, no clone;
  web withdrawal before application releases the prepared Launcher and keeps file
  and purchase intact. Upgrade 001–058→059 equals bootstrap: 17,473 lines, 69
  prior table hashes preserved.
- **329 focused Python tests OK** (schema, identity, ingestion, write/journal,
  Launcher runtime, item-use, transfer, per-title parsers, new 24B seams).
  **Web: 22 files / 152 tests OK**, `tsc -b` and Prettier PASS. Ruff: no new
  findings versus HEAD; compile/diff PASS; renderer `node --check` PASS.
- Retained, not rerun: eight-title native/PG matrices and 24A closure (native
  contracts, 057 and 058 unchanged).

**Inherited failures resolved.** `test_phase16d…clears_superseded` and
`test_phase9…architecture` failed on clean `5652808`/`089eb6a`. Both came from
23B/23D: the runtime gained an `/item-uses` read that the 16D fixture never
modelled, and imported `app.api.schemas` from `app/launcher`, which the
architecture test forbids. The fixture now models absent endpoints and the
Launcher uses its own status wire model. Neither affected product behaviour.

Development: first harness run read a private table as service_role (42501,
correct denial) — harness corrected; Launcher wire models were then made local,
and the full harness and regression were rerun on the final code.

## Remaining before release (not 24 blockers)

1. Electron action UI and dialogs for the four runtime commands, and the
   capability decision, together with **Lime3DS** real certification.
2. Hosted verifier runner: signed source reads, scheduling and secrets in the
   restricted worker service (the step function exists; no runner shipped).
3. Deploy 054–059 and enable the cohort flag — separate authorized packets.
4. Party and cross-title transfers remain unqualified and rejected
   (`TRANSFER_NATIVE_SCOPE_UNQUALIFIED`); most official-team targets are party.
5. Competitive policy for a victim who never cooperates (no deadline/penalty
   rule exists; the purchase simply stays unconsumed). The recipient Launcher
   receives the target's stored bytes before completion; a manual clone is not
   credited by identity reconciliation.

| Gate | Result |
| --- | --- |
| BACKEND | PASS (local, disabled by default) |
| LAUNCHER | PASS (runtime/stdio + status UI; action UI deferred) |
| ROBBERY UI | PASS |
| POST-TRANSFER SYNC | PASS |
| TWO LAUNCHERS | PASS |
| SECURITY / RECOVERY | PASS |
| LIME3DS CERTIFICATION | PENDING |
| DEPLOYMENT | NOT EXECUTED |
| PHASE24 | DONE LOCAL |

Private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase24b/20261025/`.
Owned PG databases dropped and clusters stopped. No real saves, randomized Y,
accounts, economy, V1/Shadow, Railway, Cloudflare or Supabase touched.
