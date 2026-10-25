# Phase25B — Launcher closure and private pre-release preparation

2026-10-26. **PHASE25B DONE LOCAL. Production UNCHANGED; nothing published;
public physical writes OFF.** Entry `eb71598` (25A), main/origin 0/0, no other
active agent. [Evidence](phase25b-launcher-evidence.json) ·
[Lime3DS procedure](lime3ds-certification-procedure.md) ·
[Live handoff](work-in-progress/phase25-live.md).

## Robbery action UI (Launcher)

The Electron Launcher now lists the trainer's robberies with: their role
(origin/destination), the Pokémon (victim: species read from their own save at
the planned box/slot) or destination box/slot, the selected save, progress of
both sides expressed only through the shared server state, the distinction
"applied in your save" versus "robbery registered by PokeApp", emulator-closed
guidance, and an assistance notice for blocked/recovery states. Buttons expose
only the actions of the trainer's own leg (prepare, apply/resume, refresh); only
the requester may cancel, and only before any application. Each prepare/apply
needs the emulator-closed checkbox plus a main-process dialog explaining the
local effect. It reuses the 24B runtime commands; no second transfer logic, no
restore button. Without the engineering capability everything is visible and
every action is disabled.

Unsupported robberies stay blocked with a plain explanation (same title, boxes
1–7 only). **Owner decisions still needed (not implemented):**
1. *Party Pokémon* — needs a native party-compaction plan and its own
   qualification; decide whether the team is robbable and what fills the slot.
2. *Cross-title* — needs PK6↔PK7 conversion and legality policy; out of scope.
3. *Victim never cooperates* — a reservation blocks both trainers' sync until
   resolved; decide a deadline and its outcome (auto-cancel with the purchase
   intact, penalty, or admin resolution). Today the requester can only cancel
   before application; the victim gets an assistance notice, no refusal button.

## Updates

Private and stable channels stay separate (distinct app ids). The build embeds
only the public key and an HTTPS feed, together or not at all
(`electron-builder.cjs`, which also refuses a private key and limits version
overrides to private candidates). `tools/sign_launcher_update.cjs` generates the
key pair outside the repository, signs manifests with a key that must be outside
the repository and the build root, never prints it, self-checks the signature
and **refuses a stable manifest unless the installer's Authenticode status is
Valid**. `tools/build_launcher_windows.ps1` gained optional signing parameters.

**Real installed update, Windows 11 Pro 10.0.26300: PASS 7/7** with two
disposable private installers (`0.22.0-rc.90` → `0.22.0-rc.91`, built from the
current shell and the existing 10-23 runtime stage, disposable key, local HTTPS
feed): installed rc.90 per-user; over real HTTPS a tampered installer, a
downgrade and a foreign-key manifest were rejected with nothing installed; the
signed rc.91 was downloaded, re-hashed and installed over rc.90; the installed
app restarted on a disposable profile and reconciled the pending update;
journal, backups and configuration byte-identical; silent uninstall kept the
profile. The in-app button/dialog path is covered by the UI smoke, not driven
here.

**Incident during the first attempt (disclosed):** `main.cjs` launches the
installer with `--force-run`; NSIS relaunches through the shell without the
test's environment, so the new private build ran ~1 minute on the owner's
**private-candidate test profile** `%LOCALAPPDATA%/PokeApp/Launcher-Private`.
Read-only inspection afterwards: every table empty (no session, selected save,
observation or outbox), a new empty write journal (0 operations) and shell cache
created; no save read or modified, nothing uploaded; it likely made a read-only
`GET /health`. The public `Launcher` profile had no changes. Files left as-is
(harmless; deleting user files is riskier). For real users this relaunch on the
normal profile is the intended behaviour; the harness now installs silently and
starts the app itself on a disposable profile.

## Quick items

Owner decision recorded: Rare Candy and Heart Scale are free and unlimited for
every trainer, within each title's real bag limits; no coins, purchase, admin
approval, economy record or quota. Public enablement is **prepared, not active**:
`PUBLIC_READY_MUTATIONS={"add_item"}`, while `PRODUCTION_MUTATIONS` stays empty
until real Lime3DS certification. Only a kind in both sets can run without the
engineering capability; confirmation and runtime use the same check. Proven with
the real native writer and the production engine configuration (real Windows
process check): empty registry denies; switch flipped only inside the test
process applies, verifies, re-reads and survives restart; other kinds still
denied. The 281 native checks were not rerun (native code unchanged).

## Gen7 signature

**KNOWN SAFE BLOCKER.** Over 200 Moon quantities, 199 verify and 1 (`+5` new
Rare Candy stack) does not: PKHeX.Core 24.11.11's own `MemeCrypto.VerifyMemeData`
rejects the signature its re-signing just produced. The bag diff is correct and
there is no hash mismatch, so it is neither our native operation nor the format:
it is a content-dependent signing limitation of the pinned library (Gen7 only;
Gen6 has no such signature). Outputs are deterministic, so that exact change stays
rejected until the save changes. The writer fails closed with the save untouched;
the UI asks for another quantity. Revive/transfer outputs share the property. Not
changing the pinned dependency without an upstream fix and full regression.

## Lime3DS readiness

Ready for acceptance on a disposable copy: process detection (`lime3ds`,
`lime-qt` added, `azahar`, `citra`), bounded sdmc discovery, write blocking with
an open emulator, verified backup, readback, restart reconciliation, Azahar/Citra
kept. Procedure: [lime3ds-certification-procedure.md](lime3ds-certification-procedure.md).
The owner's randomized Y was not accessed.

## Pre-release coherence

Launcher `0.22.0-rc.3` (public installed 0.20.0 unchanged); new endpoints are
optional for the Launcher (absent → old backend compatible); physical writes off
in every shipped build; 054–059 and the private verifier pending separate
authorization; channels separate; journals/backups preserved across update and
uninstall; Windows 11 tested, Windows 10 pending (rerun
`node tools/validate_launcher_update_install.cjs` with two private builds).

## Validation

UI smoke (real page, Electron 44): 23/23 · signer/updater/quantity Node tests:
14/14 · installed update Win11: 7/7 · public switch with real native: PASS ·
Python affected: 254 OK · Ruff no new findings · native build 0/0.

| Gate | Result |
| --- | --- |
| LAUNCHER FUNCTIONAL INTEGRATION | DONE LOCAL |
| ROBBERY ACTION UI | PASS |
| AUTO-UPDATER | DONE LOCAL (activation needs real key, feed) |
| SIGNED UPDATE MANIFEST | PASS |
| AUTHENTICODE | PENDING |
| REAL INSTALLED UPDATE TEST | PASS Windows 11 · Windows 10 PENDING |
| RARE CANDY / HEART SCALE | DONE LOCAL; free/unlimited policy recorded; public switch prepared, OFF |
| GEN7 SIGNATURE ISSUE | KNOWN SAFE BLOCKER |
| LIME3DS READY FOR ACCEPTANCE | YES (disposable copy, owner approval required) |
| PHASE25B | DONE LOCAL |
| PRE-RELEASE READINESS | CONDITIONAL |

**External requirements:** Authenticode certificate; release key ceremony and
custody; HTTPS hosting for both feeds; Windows 10 run; deployment of 054–059 and
the private verifier (separate authorization); Lime3DS real certification; the
three robbery decisions above.
