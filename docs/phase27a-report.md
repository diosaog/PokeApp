# Phase27A — server-authoritative robbery, restricted verifier, backend

2026-10-26. **PHASE27A DONE LOCAL. Production UNCHANGED (054–061 not applied),
verifier not deployed, public physical writes DISABLED.** Entry `44301da`
(26D DONE LOCAL + owner's daily backup policy). Contract:
[robbery-rules.md](robbery-rules.md). Backend, migration plan, private verifier
and restricted deployment: [robbery-backend.md](robbery-backend.md).

## What changed

- **Migration `061_transfer_authoritative_adjudication.sql`** (additive): the
  verifier adjudicates from the server-held accepted saves — consumption,
  canonical 025 effects, ownership, provenance — without any Launcher; each side
  then carries a physical obligation (`PHYSICAL_PENDING` → `VERIFIED` /
  `ABSENT_VERIFIED` / `RECOVERY_REQUIRED` / `INCIDENT`). New states
  `REQUESTED`, `ELIGIBILITY_VERIFIED`, `COMPETITIVELY_ADJUDICATED`, `RECONCILED`.
  Re-planning on a trainer's current bytes, per-side settlement and release,
  early cross-title refusal, team-lock guard, two-proof finalization superseded.
- **Verifier** (`TransferVerification`): `adjudicate`, `verify` (one side),
  `settle` (registers the side's accepted save, or a verified absence),
  `rebase` (locates the robbed identity by immutable evidence; robber bytes
  always from the victim's canonical save); worker dispatches the new actions;
  `PrivateTransferStorage` and runner switch for the private worker.
- **API**: candidate upload route, obligation/pair id in reads, new messages.
- **Launcher**: obligations listed first; victim's ordinary sync paused while
  its removal is pending; `fulfil` (match → safe engine; applied → upload; moved
  on → upload current bytes for re-plan; restart → journal decides); re-binding
  only over an unapplied local attempt. Cards: «Aplicar retirada obligatoria»,
  «Recibir el Pokémon», no cancel or veto after the decision.
- **Web**: decision and per-save delivery shown separately (adjudicated,
  pending removal, pending reception — not usable yet, verified, incident);
  victim text «No necesita tu aprobación»; requester withdrawal only before the
  decision.

## Evidence (Windows 11, disposable PostgreSQL 17, real PKHeX native)

`tools/validate_phase27a_local.py` — bootstrap 001–061, real FastAPI routes,
two Launchers (real safe engine over `AuthenticatedTransferRemote`), restricted
verifier role, retained public fixtures. **16/16 PASS**:

| Scenario | Cases | Result |
| --- | --- | --- |
| A both online (X, box) | 1, 8, 11, 13, 14 | concurrent identical requests → one authority; concurrent verifiers → one decision; nobody cancels after it; emulator open blocks before any change; lost replies are no-ops; RECONCILED |
| B victim offline for days, plays first (X) | 2–6, 10, 12 | decided and delivered to the robber with the victim never online; victim sync and team lock refused; played save re-planned on current bytes, progress kept; RECONCILED |
| C victim no longer holds it (Y) | 7 | current save accepted as verified absence; no clone |
| D restart during removal (X) | 9 | crash before park keeps the original; restart re-plans once; RECONCILED |
| E concurrency, decision B | 13 | cross-title refused at reservation; second robbery refused |
| F team robbery (X, party) | A | RECONCILED |
| G manipulated material (X) | — | another trainer's file blocks only the victim side (decision kept); tampered result issues no proof |
| grants | — | only the verifier role decides/proves/settles; worker allowlist exact |
| parity | — | 001–060 + 061 ≡ bootstrap; existing data unchanged (69 tables) |

Other runs: 27A unit tests 8/8; transfer/integration unit tests OK; web 22
files / 159 tests + `tsc -b`; Launcher UI smoke 28/28; Python suite 1162 tests
with 3 failures that **also fail at the previous commit** (account capability
default, admin route count, a 0.2 s timing assertion) — not caused by 27A.

## Gates

| Gate | Result |
| --- | --- |
| PHASE 26D GATE | PASS |
| SERVER-AUTHORITATIVE ROBBERY | PASS (local) |
| NON-COOPERATIVE VICTIM LOGIC | PASS (local) |
| MANDATORY SYNC | PASS (local, engineering Launcher) |
| PARTY/BOX ROBBERY | PASS |
| PHYSICAL DELIVERY | PASS (canonical bytes only) |
| TWO-SAVE RECOVERY | PASS |
| EXACTLY-ONCE EFFECTS | PASS |
| IDENTITY/UUID | PASS |
| FOREIGN-OT CASES | RESTRICTED |
| BACKEND INTEGRATION | PASS (local) |
| WEB/LAUNCHER INTEGRATION | PASS (local; packaged Launcher not rebuilt) |
| MIGRATIONS LOCAL | PASS |
| BOOTSTRAP PARITY | PASS |
| RLS/PERMISSIONS | PASS |
| INDEPENDENT VERIFIER | PASS (local, restricted role) |
| PRIVATE WORKER BUILD | PARTIAL (no Docker on this machine; runner, storage and Dockerfile ready) |
| DISPOSABLE END-TO-END | PASS |
| REAL TWO-PLAYER ACCEPTANCE | PENDING |
| HOSTED ACCEPTANCE | PENDING |
| PRODUCTION MIGRATIONS | NOT APPLIED |
| PUBLIC PHYSICAL WRITES | DISABLED |
| PHASE 27A | DONE LOCAL |

## Limits and pending

- Real limits: an offline computer cannot be changed remotely (the decision
  stands; the copy is invalid until the mandatory sync); a local attempt that
  was prepared but not applied and then overtaken by play is kept as
  `RECOVERY_REQUIRED` (assisted); foreign-OT origins stay restricted; Gen7
  re-sign fail-closed (~1/200) unchanged.
- External only: two real players on Lime3DS, hosted acceptance (procedure
  ready), worker image build where Docker exists, Windows 10, Authenticode,
  update server, production 054–061.
- Superseded: the 24A/24B harnesses drive the two-proof completion that 061
  refuses; `validate_phase27a_local.py` replaces them.
- Release gates still open: the above plus owner activation of public physical
  writes after certification.

Next: **27B** — restricted hosted acceptance (owner-approved steps 1–18 of the
procedure), real two-player robbery on Lime3DS, worker image build, packaged
Launcher with the 27A flow.
