# Phase26A — Lime3DS acceptance

2026-10-26 continuation. **Owner authorized work on COPIES of the Pokémon Y save.
PARTIAL: everything automatable PASS on isolated copies; the in-game check is
the owner's manual step.** The original was only read once and hashed; it is
byte-identical. First stop (before authorization) preserved below.

## Continuation results (isolated copies)

- **Real save read:** Pokémon Y, Gen 6, 415,232 bytes, SHA-256 `c0e666e7…`;
  party Bagon Lv10, Zygarde Lv5, Keldeo Lv6; nothing boxed; Rare Candy 0, Heart
  Scale 0 (max 999).
- **Backup:** independent byte copy (+ `.metadata`) in the private evidence
  folder, hash-verified, restore verified byte-identical.
- **Isolated Lime3DS:** portable copy of the owner's Lime3DS binaries (no ROMs
  copied) with its own `user` folder; the owner's config/keys copied and
  `nand`/`sdmc` pinned to the isolated folders. Working copy in the isolated sdmc.
  Starting it left `%APPDATA%\Lime3DS` unchanged (snapshot compared).
- **Real process:** isolated `lime3ds.exe` running → write refused
  (`EMULATOR_RUNNING`), file unchanged; closed gracefully.
- **Quick items on the working copy (runtime commands, real native):** Rare
  Candy 0→10 and Heart Scale 0→7, verified backup, explicit confirm, native
  readback; party, boxes and trainer identical.
- **Idempotency:** re-offer of the original intent and restart → no second add.
- **Recovery (extra disposable copies):** external change after preparation →
  `REJECTED`, external bytes kept; interruption at backup → nothing written;
  interruption after publish → reconciled `APPLIED_VERIFIED`, +4 once; corrupt
  backup → `RECOVERY_REQUIRED`, file untouched; good backup → `RESTORED_VERIFIED`
  exact original.
- **Finding (release blocker for public writes):** the Phase22 no-replace handoff
  leaves the parked original `.pokeapp-<op>.displaced` (full copy) and a `.lock`
  beside the save after success, and reusing an operation id with a leftover
  displaced file correctly blocks with `DESTINATION_OCCUPIED`. The engine itself
  marks that handoff fixture-only; a retention/cleanup design is required before
  public enablement. The in-game check runs with those files present.
- **Robbery rules:** recorded in [robbery-rules.md](robbery-rules.md); the API now
  refuses victim cancellation (409 `TRANSFER_VICTIM_CANNOT_CANCEL`), proven again
  on PostgreSQL (24B harness 15/15).

## First stop (before authorization) Production UNCHANGED; nothing
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
| REAL SAVE READ | PASS |
| REAL BACKUP/RESTORE | PASS |
| RARE CANDY IN-GAME | PENDING owner check (file: 0→10 PASS) |
| HEART SCALE IN-GAME | PENDING owner check (file: 0→7 PASS) |
| NATIVE REVIVE IN-GAME | PENDING (fixtures: native/independent PASS since 23C) |
| TWO-SAVE ROBBERY | PENDING (needs two real participants; fixtures PASS in 24A/24B) |
| GAME SAVE/REOPEN PERSISTENCE | PENDING |
| RECOVERY | PASS on real-save copies (in-game recovery not applicable) |
| GEN7 SIGNATURE | KNOWN BLOCKER (fails closed; Y is Gen6, unaffected) |
| PRIVATE PRE-RELEASE BUILD | PARTIAL (built + audited; unsigned private channel; graceful close unverified headless) |
| AUTO-UPDATER | PENDING (real key, feed, Authenticode) |
| HOSTED VERIFIER | NOT DEPLOYED |
| PUBLIC PHYSICAL WRITES | DISABLED |
| THREE ORIGINAL POKÉMON | PASS (unchanged on copy; original untouched) |
| PHASE26A | PARTIAL (owner in-game step) |
