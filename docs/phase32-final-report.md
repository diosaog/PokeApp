# POKEAPP 2.0 — PHASE 32 FINAL REPORT (PUBLISHED)

Date: 2026-10-28 (Europe/Madrid). Supersedes the earlier «blocked» version of
this report: the owner chose private distribution without Authenticode, and
the public channel is now **live**.

Status vocabulary: DONE LOCAL · PASS PACKAGED · PASS HOSTED · PENDING EXTERNAL.

## 1. Result

| Area | Status |
| --- | --- |
| Public download | **0.26.1** — `/launcher/download`, 159,312,173 bytes, SHA-256 `edf8d6479a7bf8187b76e240457eb0399d8eb36a5ac4c029face22366e18d320` (downloaded in full and hashed) — PASS HOSTED |
| Stable feed | `…/launcher/updates/stable.json` offers 0.26.1, signed with the stable Ed25519 key; a tampered byte fails the signature — PASS HOSTED |
| R2 | `windows/0.26.0/` (bridge, `0610caee…08d3`), `windows/0.26.1/` (`edf8d647…d320`), `updates/stable.json`; older 0.16.1–0.25.0 kept for rollback |
| Transition 0.25.0 → 0.26.0 with the real public installers | **PASS 8/8** (§4) |
| Automatic update 0.26.0 → 0.26.1 from the hosted feed | Detection, popup, download, Ed25519 + SHA-512, silent install, restart as 0.26.1 — PASS HOSTED (§5) |
| Packaged rehearsal (isolated identity) | 30/30 PASS PACKAGED (Phase 32 first pass) |
| Channel through the real Worker | 19/19 (local workerd) + 20/20 public checks on the deployed Worker |
| Authenticode | **Intentionally absent** (owner decision 2026-10-28, private distribution). Recorded per release as `NotSigned` / `private-distribution`; a broken or untrusted signature is still refused |
| Ed25519 + SHA-512 + downgrade/channel refusals | Unchanged in the Launcher; enforced |
| Windows 11 | PASS (10.0.26300) · Windows 10: PENDING EXTERNAL (no machine) |

## 2. Keys (permanent, outside the repository)

- `%LOCALAPPDATA%\PokeApp-release-keys\stable\` and `…\private\`: public PEM
  plus the private key **only as a DPAPI blob** (this Windows user, purpose-bound
  entropy); folder ACL owner + SYSTEM. Fingerprints (SHA-256 of the SPKI):
  stable `639e544049a6a9e0…`, private `cf29453b64eef906…`. The stable key's
  public half is embedded in 0.26.0 and 0.26.1.
- Signing decrypts in memory (`tools/sign_launcher_update.cjs`); keys survive
  reboots and builds (proved from a separate process).
- **Backup (owner, once):** set `POKEAPP_KEY_BACKUP_PASSPHRASE` (≥16 chars) in
  your own shell, then
  `node tools/sign_launcher_update.cjs --export-key "%LOCALAPPDATA%\PokeApp-release-keys\stable\pokeapp-update-private.pem.dpapi" --to E:\pokeapp-stable-key.pem`
  and keep the file offline. Restore with `--import-key <file> --to <dir>`.
  Without a backup, losing this Windows profile means one manual install of a
  build with a new key (rotation): installed Launchers only trust the old key.

## 3. Publishing a future version

1. Bump `companion/launcher/package.json` + lock; commit.
2. Build: `tools/build_launcher_windows.ps1 -BuildRoot <fresh> -Python <3.14.3> -Dotnet <dotnet9> -UpdatePublicKeyFile <keys>\stable\pokeapp-update-public.pem -UpdateFeed https://pokeapp-web.pokeapp-v2.workers.dev/launcher/updates/stable.json -UpdateSigningKeyFile <keys>\stable\pokeapp-update-private.pem.dpapi -UpdateDownloadUrl https://pokeapp-web.pokeapp-v2.workers.dev/launcher/updates/stable/<v>.exe -UpdateMinimumVersion 0.26.0 -UpdateNotes "- …" -UnsignedPolicy private-distribution`.
3. `node tools/publish_launcher_release.mjs --build <root> --manifest <root>\release\stable.json --unsigned-policy private-distribution` (dry run), then add `--apply --owner-authorized`: installer first, read-back SHA-512, manifest last.
4. Set `web/launcher-release.json` and deploy the web.
5. `python -m tools.phase30_hosted_acceptance --stage final --full-download` (update its expected installer).

Rollback: restore the previous `updates/stable.json` (clients never downgrade)
and publish a corrected higher version.

## 4. Transition from 0.25.0 — PASS 8/8

`tools/validate_launcher_public_update.mjs transition`, real public installers
(0.25.0 `f02eccd0…`, 0.26.0 `0610caee…`), the stable identity installed into an
isolated folder with LOCALAPPDATA/APPDATA redirected: 0.25.0 installed and run
on a profile with a chosen save, an encrypted session and a backup → 0.26.0
installed over it → same folder, one installed Launcher, profile byte for byte,
save untouched → 0.26.0 keeps the save chosen in 0.25.0 and reads the hosted
feed. [Evidence](evidence/phase32/public-update-transition.json).

## 5. Update 0.26.0 → 0.26.1 from the hosted feed

The installed 0.26.0 found 0.26.1 on the live feed; «Actualizar» downloaded it,
verified the manifest (Ed25519) and the installer (SHA-512), installed silently
and restarted as 0.26.1. [Evidence](evidence/phase32/public-update-update.json).

**Incident (honest record).** After installing, NSIS relaunches the app through
Explorer with the user's real environment, so the restarted 0.26.1 opened the
owner's real profile for ~70 s (07:54:28–07:55:39) before the harness stopped
it. Effects: session token refreshed (same encrypted file, new tokens),
`known-saves.json` regenerated from the owner's own saves, local observations
and Electron caches. No save could be written (0.26.1 ships no physical
mutation); `config.json` unchanged; production unchanged (every public/storage
table identical to the post-migration backup, no upload, no new session). The
harness now refuses that phase on a machine with a real profile. The
post-restart checks (selected save, config, known saves, DPAPI session, Electron
data, save bytes, installer cleanup) are covered by the packaged rehearsal with
the isolated identity (30/30) and by the transition proof that the installer
never touches the profile. For a real player the Explorer relaunch is correct:
same user, same profile.

## 6. Defects found and fixed in this phase

- Worker entry exported a string (workerd refused it) — `d8a33d0`.
- Signer test left private test keys in `%TEMP%` — `d62f673` (old folders remain; owner may delete `%TEMP%\pokeapp-sign-*`).
- The API could not start on Linux (Windows-only import on the item-use path) — `122959c`, with a portability test.
- Transfer-notice cache could hide a new notice (same mtime tick) — `d7f9659`, shipped in 0.26.1.
- Publication guard verified a bridge manifest as a 0.0.0 client — fixed; signature checked with the build's embedded key.
- Harness: asar header cache, versioned uninstall name, NSIS relaunch timing, Git Bash `/S` mangling (installers now always run through Node).

## 7. Commits

`897fbc7` keys + policy · `122959c` API portability · `d7f9659` notice cache ·
`714456e` 0.26.1 · and the commit carrying this report, the public-update
harness, the final hosted checks and the 0.26.1 card.
