# Phase26A — Lime3DS acceptance (stopped at the owner gate)

2026-10-26. **PHASE26A BLOCKED at the owner-approval gate. No personal save was
opened, read, hashed, copied or modified. Production UNCHANGED; nothing
published; public physical writes OFF.** Entry `1450062` (25B DONE LOCAL, gate
PASS). [25B report](phase25b-launcher-report.md) ·
[Lime3DS procedure](lime3ds-certification-procedure.md) ·
[Backend procedure](restricted-backend-acceptance-procedure.md).

## Done (independent of the owner)

- **Lime3DS detected on this machine:** portable executable
  `Desktop\Lime3DS\Lime3DS\lime3ds.exe` (process name `lime3ds.exe`, already in the
  write-blocking list), user directory `%APPDATA%\Lime3DS` (no portable `user`
  folder). Azahar user directory also present; Citra absent. No emulator running
  at the time of the check.
- **Save located with the authorized Launcher discovery** (paths and sizes only):
  exactly one compatible save, Lime3DS · Pokémon Y:
  `C:\Users\Antonio\AppData\Roaming\Lime3DS\sdmc\Nintendo 3DS\00000000000000000000000000000000\00000000000000000000000000000000\title\00040000\00055e00\data\00000001\main`
- Restricted backend acceptance procedure written (not executed).
- **Private pre-release `0.23.0-rc.1`** built with the official
  `tools/build_launcher_windows.ps1 -PrivateCandidate` pipeline (fresh build root
  outside the repo, pinned Python 3.14.3, locked pip/npm/NuGet, PyInstaller core,
  self-contained parser). The post-build audit first **failed correctly**: its
  exact asar allowlist did not know the 25A files (`quantity.js`, `updater.cjs`,
  two item icons) — a 25A omission, since 25A never ran the official build. The
  allowlist now lists exactly those files and the audit reports the packaged
  version: PASS, `0.23.0-rc.1`, private, updates not configured, unsigned
  (Authenticode `NotSigned`), SHA-256 `ddfac301…dacde`, 159,236,210 bytes. Not
  distributed.
- **Installed smoke (disposable folder and profile):** silent install PASS; app
  and native core start PASS; silent uninstall removed the app and kept the
  profile PASS; owner's real private/public Launcher profiles unchanged PASS.
  Graceful close could not be verified: with the hidden test window `taskkill`
  without `/F` does not reach Electron, so the harness forced it — not counted as
  PASS. The started app likely issued a read-only `GET /health` to the API.

## Gate — what the owner must confirm before anything else

1. That the path above is the randomized Pokémon Y save, and permission to make
   a byte copy plus SHA-256 of it into an independent backup folder.
2. The scope on the COPY: Rare Candy and Heart Scale only (no robbery/revive on
   the three personal Pokémon).
3. The owner performs the in-game steps (open the copy in Lime3DS, check the bag,
   save, close, reopen); the agent cannot operate the emulator window.
4. For revive in game: a prepared Box 8 copy is required; for a real robbery: two
   participants with their own saves and Launchers.

| Gate | Result |
| --- | --- |
| PHASE 25B GATE | PASS |
| LIME3DS DETECTION | PASS (install, executable/process name, save location) |
| REAL SAVE READ | PENDING (owner approval) |
| REAL BACKUP/RESTORE | PENDING (owner approval) |
| RARE CANDY IN-GAME | PENDING |
| HEART SCALE IN-GAME | PENDING |
| NATIVE REVIVE IN-GAME | PENDING (fixtures: native/independent PASS since 23C) |
| TWO-SAVE ROBBERY | PENDING (needs two real participants; fixtures PASS in 24A/24B) |
| GAME SAVE/REOPEN PERSISTENCE | PENDING |
| RECOVERY | PARTIAL (fixtures PASS; real Lime3DS pending) |
| GEN7 SIGNATURE | KNOWN BLOCKER (fails closed; Y is Gen6, unaffected) |
| PRIVATE PRE-RELEASE BUILD | PARTIAL (built + audited; unsigned private channel; graceful close unverified headless) |
| AUTO-UPDATER | PENDING (real key, feed, Authenticode) |
| HOSTED VERIFIER | NOT DEPLOYED |
| PUBLIC PHYSICAL WRITES | DISABLED |
| PHASE26A | BLOCKED (owner gate) |
