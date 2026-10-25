# PokeApp - Phase 23B integration report

2026-10-25. **PHASE 23 PARTIAL / NOT DEPLOYED.** Entry main/origin
`0c074a84a33a63588e0ff0a432dcac421ec8c451`,0/0,clean tracked tree.
The closure commit carries source and documentation; obtain exact HEAD from Git.
[Live handoff](work-in-progress/phase23-live.md) / [Evidence](phase23b-local-evidence.json).

| Boundary | Result |
| --- | --- |
| Authorizations | DONE LOCAL for the tested private verification boundary |
| Real PostgreSQL | PASS, disposable PostgreSQL17.11 |
| Launcher local | PARTIAL: existing-engine/journal integration proven with a synthetic mutation |
| Physical application certified | NO |
| Production | NO DEPLOYMENT, no remote operations |

## Corrections to the inherited foundation

The previous draft accepted a client APPLIED_VERIFIED assertion and incorrectly
expected the resulting hash to equal the source. It was not sufficient proof of
application. The environment blocker was obsolete: retained PostgreSQL17.11 and
`.venv-api` already include the dependencies. The earlier claimed five RLS tests
are not reused: that run included import failures. No full matrix repeated.

Unapplied054 now binds source save, identity revision, purchase, target,
trainer/season, operation and a single durable claimant. Preparation/claiming
never consume. A15-minute authorization expires closed; uncertain claims cannot
be reassigned. Another entitlement cannot authorize the same target observation.
Exact completed replay returns the historical receipt; conflicting claims, keys,
targets and current-save changes fail closed.

`item_use_verifications` has FORCE RLS and SELECT only for service_role. The
normal API/browser/Launcher cannot create proof; no HTTP issuance route exists.
Completion requires independently recorded proof bound to authorization, claim,
source/result hashes, identity and native plan. Result and original hashes must
DIFFER. Unexpected SQL errors roll back consumption/flags/journal together; known
post-application conflicts preserve the entitlement for reconciliation. The old
redemption route cannot bypass this, even by borrowing proof before completion.

This is a trust boundary, NOT a production verifier. SQL concurrency/negative
checks use synthetic attestations; the separate bridge checks its local native
engine/file before inserting evidence as disposable postgres. A client receipt
or a signing key embedded in the Launcher is not trusted proof. Production proof
transport and the exact native business-effect mapping remain unresolved.

## Launcher, recovery and interface

`EngineeringItemUse` extends the existing physical SQLite journal with immutable
authorization/claim/native-operation bindings. It reuses LocalWriteController,
sync exclusion, backups, native verifier and no-replace engine. It requires an
in-process engineering capability/disposable target; runtime/IPC does not
instantiate it or accept server-supplied plans. Explicit closed-game confirmation,
selected path, source hash and target must match. Claim responses may be lost
without generating a new claimant. Sync stays paused until final reconciliation.
Restart/confirmation reads existing native materials; it never blindly reapplies.
Lost acknowledgement reuses the operation and consumes once. Unprovable files
remain RECOVERY_REQUIRED/BLOCKED_UNCERTAIN with backups intact.

Its mutation is synthetic test_marking, NOT revive. The existing eight-game
native marking evidence is retained unchanged; it cannot certify revival/theft.
No actual Azahar game, OS crash, power loss, owner save or installed Launcher was
tested here. New interruption tests inject exceptions at filesystem boundaries;
they are not new forced-process-death tests.

Existing inventory shows available/pending/verified/recoverable/recovery/blocked
states. Physical revive/steal cannot use immediate redemption. Internal shields
and vouchers retain their existing server-approved flow. The Launcher displays
scoped cached states only, tolerates an old backend without the endpoint, and
never grants write capability from a response. No redesign or package release.

## Validation actually executed

- **75 unique focused Python PASS**: item-use API11, bridge8, runtime3, existing
  sync exclusion3/heartbeat1, schema15, purchase/redemption34. Open-emulator denial
  uses a process-list fixture. Eight bridge tests passed across targeted runs.
- **10 real PostgreSQL groups PASS**: concurrent prepare/replay/reservation;
  two claimants; client/direct-redemption denial; rollback after redemption;
  concurrent completion/lost response; expiry/cross-binding/stale pointer;
  RLS/grants/proof-write denial; sufficient/insufficient/concurrent purchase;
  migration/bootstrap parity; existing-engine/PG restart bridge.
- Upgrade001-054 versus bootstrap: **16,376 identical schema/ownership/grant lines**.
  **62 initialized pre054 public table hashes** preserved. This is disposable
  catalog/fixture evidence, not a production-data baseline comparison.
- **10 React**, **2 Edge journeys** at1440/390 PASS. States, disabled physical
  consumption, internal voucher flow and layout checked; screenshots reviewed.
  Browser APIs are fixtures, not hosted proof.
- OpenAPI, TS/Vite build, syntax11 files, renderer JS syntax, targeted Ruff,
  formatting/diff PASS. Existing nonfatal bundle warning retained. Ruff on
  inherited modules checked syntax/imports/undefined names; new modules full lint.

Harness corrections: an unsupported ledger seed label was changed to existing
admin_adjustment; two tests now require the actual engine safety exceptions
instead of expecting a returned state; browser fixture acquisition_type changed
from purchase to paid after TS caught it. Only invalidated gates repeated.
Private PG proof: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase23b/20261025/pg-final.json`.
Owned databases dropped and clusters stopped. Synthetic backup artifacts retained
under PG evidence roots are not owner saves.

## Supported scope and exact next unit

Revive preparation is tested, NOT physically operational. Steal preparation is
explicitly unavailable: a one-save proof cannot authorize a two-save transfer.
No new theft rules, mints, caps, capsules or unspecified native semantics.
Legacy embedded redemption receipts retain their original internal snapshot;
the authorization owns subsequent verification state. Reconcile that legacy
physical-status read contract before any production activation.

Next: an exact native revive/identity contract and independently trusted production
verification design, then authentic-copy qualification and Phase22's real Azahar
conditions. Theft requires its own approved two-save protocol. Do not deploy054 or
consume based solely on uploaded hashes/client receipts or this engineering proof.

No remote migration/service/configuration changes, real account/economy/save/history
writes, V1/Shadow access, Launcher publication or Phase24. Protected guide and eight
unrelated untracked files remain untouched. Phase23 GLOBAL remains PARTIAL.
