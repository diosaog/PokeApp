# POKEAPP 2.0 — PHASE 32 FINAL REPORT

Date: 2026-10-28 (Europe/Madrid). Scope: turn the certified updater into a
public, safe update channel; no reimplementation, no redesign. **Nothing was
published**: R2, the update feeds, Cloudflare, Railway and the public
Launcher are unchanged. The public channel is **BLOCKED on two external
inputs** (an Authenticode certificate and the owner's stable signing key) and
on the Phase 30 release.

Status vocabulary: DONE LOCAL · PASS PACKAGED · PASS HOSTED · PENDING RELEASE ·
PENDING EXTERNAL · BLOCKED.

## 0. State recovered

| Item | Verified |
| --- | --- |
| Phase 30 | Release readiness complete ([report](phase30-release-readiness-report.md)); its production steps await the owner's authorization. Production = before Phase 30 |
| Git | `main` = `origin/main` before this phase (`f85eaef`); eight foreign untracked files kept |
| Public Launcher | 0.25.0 (R2 `windows/0.25.0/`, SHA-256 `f02eccd0…e983d3fa`), no key, no feed: it cannot update itself |
| R2 | 0.16.1–0.20.0, 0.25.0; no 0.26.0; no `updates/stable.json` or `updates/private.json` |
| Cloudflare | `a7e33476`: the live Worker has no `/launcher/updates/*` routes yet |
| Keys | No stable or private release key exists. Only throwaway test keys (see §3) |
| Authenticode | **No code-signing certificate** in the user or machine store; Windows SDK `signtool` absent |
| Updater code | Unchanged since its 28/28 rehearsal (`2ceffc5`); this phase did not modify it |

## 1. Results

| Area | Status |
| --- | --- |
| Definitive version | **0.26.0** chosen as the bridge (§4) — DONE LOCAL |
| Real update A → B from the current code | **PASS PACKAGED 30/30** (§5) |
| Channel through the real Worker (workerd, local R2) | PASS LOCAL 19/19 (§6) |
| Stable channel | BLOCKED — PENDING EXTERNAL (certificate, key, authorization) |
| Private channel | Ready in code and Worker; its own key not generated — PENDING EXTERNAL |
| Ed25519 stable/private keys | PENDING EXTERNAL — owner generates and keeps them (§3) |
| Authenticode | BLOCKED — no certificate (§3); requirement kept |
| Publication guard (stable manifest only with a Valid-signed installer) | DONE LOCAL (§7) |
| Windows 11 | PASS PACKAGED (10.0.26300) |
| Windows 10 | PENDING EXTERNAL — no Windows 10 machine here |
| Transition 0.25.0 → bridge over a real install | PENDING EXTERNAL — needs a clean Windows user or VM; never the owner's install (§8) |
| PASS HOSTED | Not claimed: nothing published |

## 2. Defects found and fixed

1. **Worker refused by workerd** (`d8a33d0`). `web/worker/launcher.mjs` exported
   a string (`artifactKey`) beside its handler; workerd treats every named
   export of the main module as an entrypoint, so `wrangler dev` could not
   start it. The deployed runtime tolerates it today, but the Phase 30 web
   deploy should not depend on that. Keys moved unchanged to
   `release-keys.mjs`; tests 4/4, dry-run bundles.
2. **Signer test left private keys in `%TEMP%`** (`d62f673`). Each run
   generated keys in `pokeapp-sign-*` folders and never removed them. Fixed;
   new runs leave nothing. **The 44 old folders are still there**: deleting
   them was refused to me by the session's safety policy. They hold
   throwaway test keys no build trusts. Owner action:
   `Remove-Item "$env:TEMP\pokeapp-sign-*" -Recurse -Force`.
3. (Phase 30, `2c14341`) the new web hid 0.25.0's native panels — fixed there.

## 3. Keys and Authenticode

**Ed25519 (owner, once per channel, never by chat).** On this PC, to an
encrypted or offline folder outside the repository and any build root:

```powershell
node tools/sign_launcher_update.cjs --generate-key E:\PokeApp-keys\stable
node tools/sign_launcher_update.cjs --generate-key E:\PokeApp-keys\private
```

Back up both `pokeapp-update-private.pem` files (password manager or second
encrypted drive). Only `pokeapp-update-public.pem` goes into a build
(`-UpdatePublicKeyFile`); the builder, signer and audit refuse a private key
in the repository, the build root or the package. Never reuse the rehearsal
keys: the one generated for §5 was deleted after the run.

**Authenticode.** None available. The stable requirement stays (the signer
and the new publication guard refuse anything but `Valid`); no self-signed
certificate is presented as equivalent. Legitimate options:

- An OV code-signing certificate from a public CA (e.g. Sectigo, DigiCert,
  SSL.com, Certum — Certum offers lower-cost certificates for individual open
  source developers). Since 2023 the private key must live on a hardware
  token or a cloud HSM, so signing goes through `signtool` (or the CA's cloud
  signing tool), not a `.pfx` file.
- Microsoft Trusted Signing (Azure): check eligibility for an individual in
  Spain before choosing it.
- EV certificates also give immediate SmartScreen reputation; OV builds
  reputation with downloads.

What the owner provides: the certificate on its token/cloud account and the
Windows SDK (`signtool`). Then the build step that signs is configured for that
mechanism (`tools/build_launcher_windows.ps1` currently disables auto-discovery
on purpose) — a small, mechanism-specific change made once the certificate
exists; the package audit and `Get-AuthenticodeSignature` must then read
`Valid`.

## 4. Version

**0.26.0** is the bridge and first definitive public version: it is already in
`companion/launcher/package.json`, it was never published (absent from R2),
it is higher than 0.25.0, and the 0.26.0 pre-releases (`-preview.*`, `-test.*`)
were private, isolated identities that never reach the stable channel. The
download card stays **0.25.0 until the 0.26.0 installer is in R2** (Phase 30
`2c14341`); it changes to 0.26.0 in the same release that uploads it, so the
web never shows a version R2 does not serve. A different number (e.g. 1.0.0)
is a one-line change if the owner prefers it.

## 5. Real update between two packaged versions — PASS PACKAGED 30/30

`tools/validate_launcher_update_e2e.mjs` on two private rehearsal builds made
from the current code (`f85eaef`), isolated identity «PokeApp Launcher
UpdateTest», loopback feed, throwaway key, synthetic save, no account.
[Evidence](evidence/phase32/update-e2e.json) and captures in
`docs/evidence/phase32/`.

| Build | Version | Installer SHA-256 | Audit |
| --- | --- | --- | --- |
| A | 0.26.0-test.3 | `5018ee6d…d69ed61e` (159,311,381 bytes) | PASS, private, unsigned |
| B | 0.26.0-test.4 | `f59307e4…d1b0778b` (159,312,208 bytes) | PASS, private, unsigned |

Covered, in the real app: real NSIS install of A · start-up check and «Estás
utilizando la última versión» · save chosen automatically · forged signature,
downgrade, incompatible jump and wrong channel refused with nothing downloaded ·
forged IPC ticket refused · corrupted bytes refused by SHA-512 · dropped
connection (partial removed, «Reintentar») · popup by itself with notes ·
«Más tarde» remembered, no repeat at start · progress · single download ·
install deferred during a real core recovery · Launcher killed before
installing, recovered offline with «Instalar ahora» · core stopped, silent
install, automatic restart as B · installer cleaned · B up to date · selected
save, config, known saves, DPAPI session (still decrypts) and Electron data
kept · **new:** the game save byte-identical across the update · **new:** B
finds the next release (0.26.0-test.5) without downloading it. Cleanup: no
install folder, profile or uninstall entry left; the owner's Launcher profile
unchanged (hash checked).

This is a packaged rehearsal with a throwaway key, **not** the certification
of a signed stable installer.

## 6. Channel on Cloudflare/R2 — PASS LOCAL 19/19

`tools/validate_launcher_channel_worker.mjs` runs the committed Worker in
workerd (`wrangler dev --local`) with a disposable local R2 seeded like a
release: manifest route (exact bytes, JSON, `no-store`, `nosniff`); stable
feed 404 until published; installer route (exact bytes, octet-stream,
immutable cache, private file name); HEAD; POST/PUT/DELETE/PATCH 405; no
listing or traversal (6 paths → 404); unpublished version 503 `no-store`;
`/launcher/download` serves the version the card shows; a signed manifest
fetched, verified (Ed25519) and downloaded (SHA-512) by the shipped updater
through the Worker; a stable Launcher refuses the private feed.
[Evidence](evidence/phase32/channel-worker.json). The private channel has no
public link and requires a private build with the private key; its installers
are only reachable by exact version.

## 7. Publication (once unblocked and authorized)

`tools/publish_launcher_release.mjs` (dry-run by default) refuses unless:
Authenticode `Valid`; public stable build with a passing audit; manifest
verified with the key embedded in that build, channel stable, same version,
exact size and SHA-512 at `…/launcher/updates/stable/<version>.exe`; nothing in
R2 for that version. `--apply --owner-authorized` uploads the installer, reads
it back through the public route and compares SHA-512, and only then uploads
`updates/stable.json`. Checked on rehearsal build B: four refusals, no upload.

Order: **Phase 30 release first** (0.26.0 uses API routes that exist only in
the new API, and its hub pairs with the new web) → stable key + certificate →
build 0.26.0 signed, with the stable key and feed → audit → private rehearsal
of the same code → `publish_launcher_release` (installer, read-back,
`stable.json`) → set `web/launcher-release.json` to 0.26.0 and deploy the web →
download from the public page, hash, install on a clean user → PASS HOSTED.
Note: `stable.json` for the bridge only matters to later versions; it must
announce a version higher than the one installed for the popup to appear.

**Rollback:** clients never downgrade. Stop offering (restore the previous
`updates/stable.json` or remove it), keep `/launcher/download` on the last good
version (card + deploy), and publish a corrected higher version. Versioned
installers stay in R2.

## 8. Players on 0.25.0

0.25.0 has no key and no feed: **it cannot update itself**. Each player
installs 0.26.0 once from «Descargar Launcher». Same app id and per-user
install, so it replaces 0.25.0 in place; the profile in
`%LOCALAPPDATA%\PokeApp\Launcher` (encrypted session, chosen and known saves,
backups, journal) stays because it is outside the install folder; saves are
never touched by the installer. From then on updates arrive from the Launcher.
The in-place replacement of a real 0.25.0 install is PENDING EXTERNAL: verify it
on a clean Windows user or VM before announcing, never on the owner's install.

## 9. Tests

| Gate | Result |
| --- | --- |
| Real update A → B (packaged) | 30/30 |
| Channel through the Worker (workerd) | 19/19 |
| Launcher node (updater, webview, confirmations, quantity, design, signer) | 35/35 |
| Worker | 4/4 · deploy dry-run OK |
| Publication guard on a private build | refuses (4 reasons), no upload |
| Phase 30 gates (Vitest 185, Python 1199, Playwright 112/0, SQL) | unchanged by this phase except the Worker split (re-tested) |

## 10. Blockers and owner actions

1. Authenticode certificate + `signtool` (or the CA's signing tool) — BLOCKED.
2. Stable and private Ed25519 keys, generated and kept by the owner (§3).
3. Authorize the Phase 30 release (its report §11).
4. Then authorize: building the signed 0.26.0, uploading it, publishing
   `updates/stable.json`, deploying the web with the 0.26.0 card.
5. A clean Windows user or VM (and Windows 10 if supported) for the transition test.
6. Delete the 44 old `%TEMP%\pokeapp-sign-*` folders (§2).

## 11. Commits

`d8a33d0` Worker entry exports only its handler · `d62f673` signer test
cleanup, save and next-update checks, real-Worker channel check · `d504f52`
guarded stable publication · this report. Base: `f85eaef` (Phase 30).
