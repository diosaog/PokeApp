# PokeApp Launcher — automatic updates

Status: **implemented and rehearsed end to end with private builds; the
public channel is NOT active.** It needs the owner's real signing key, an
Authenticode certificate and an authorized upload/deploy (§6). Rehearsal
report: [launcher-updates-report.md](launcher-updates-report.md).

## 1. What the player sees

1. At start the Launcher checks the feed quietly.
2. A newer version opens the update popup **once**: version, what is new,
   size, «Actualizar», «Más tarde». «Más tarde» is remembered for that
   version (no popup again at start; «Saves y Launcher › Launcher › Buscar
   actualizaciones» still shows it; a newer version asks again).
3. «Actualizar»: download with progress → verification → install → the
   Launcher restarts by itself as the new version. Session, selected save,
   backups, journal and settings stay (they live in the profile, not in the
   install folder).
4. Nothing new: «Estás utilizando la última versión».
5. Errors say what happened and offer «Reintentar»; nothing is forced.

## 2. Trust model

- The only authority is an **Ed25519-signed manifest** verified against a
  public key **pinned in the build** (`package.json › pokeappUpdate`). The
  server is not trusted: a signature or hash served by it is never a new
  authority.
- The manifest binds `channel`, `version`, `minimum_version`, `notes` and the
  installer's `url`, `sha512` and `size`. The Launcher refuses: missing or
  foreign signature, another channel, an older or equal version (downgrade /
  replay), a version that needs a newer starting point (`minimum_version`),
  a non-HTTPS URL, any unexpected field.
- The installer is streamed with a size cap, hashed (SHA-512) while it
  downloads, renamed into place only when size and hash match, and
  **re-hashed** right before it runs. A `.partial` file never survives.
- Private candidates may embed a loopback feed (`http://127.0.0.1:<port>/`)
  for rehearsal; public builds accept HTTPS only (enforced by the builder,
  the signer, the package audit and the Launcher itself).
- Channels are separate: a stable build only reads the stable feed and only
  accepts `channel: "stable"`; private likewise. Use a **different key per
  channel**.

## 3. Install safety

- One flow at a time (single flight); a verified file for the same manifest
  is reused, so a second «Actualizar» never downloads twice.
- Before installing, the core's state must be clear: no save write running
  or pending confirmation, no recovery, no robbery delivery in progress.
  Sync is waited for (up to 60 s); anything else defers the install
  («Lista para instalar. Esperando a que termine …»).
- The core is asked to stop and **waited for** (15 s, then killed) before the
  installer may replace its files; then the installer runs silently
  (`/S --updated --force-run`, per-user, no elevation) and restarts the app.
- After the update, the new version removes the downloaded installer; if
  the installer process still holds it, cleanup is retried a minute later
  and at the next start, and never blocks the Launcher from starting.
- If the Launcher dies before installing, the verified file is kept and the
  next start offers «Instalar ahora» (also offline). If the installed version
  is already the target, leftovers are removed.

## 4. Channel on Cloudflare/R2 (existing `pokeapp-web` Worker)

Read-only routes, built from a fixed channel and a validated version (no
listing, no upload, no client-supplied key):

| Route | R2 object |
| --- | --- |
| `GET /launcher/updates/stable.json` | `updates/stable.json` (no-store) |
| `GET /launcher/updates/stable/<version>.exe` | `windows/<version>/PokeApp-Launcher-Setup.exe` (immutable) |
| `GET /launcher/updates/private.json` | `updates/private.json` |
| `GET /launcher/updates/private/<version>.exe` | `private/<version>/PokeApp-Launcher-Private-Setup.exe` |

Feed URL to bake into stable builds:
`https://pokeapp-web.pokeapp-v2.workers.dev/launcher/updates/stable.json`.
The existing `/launcher/download` (first install) is unchanged.

## 5. Keys

- Generate on a trusted machine, outside the repository and any build root:
  `node tools/sign_launcher_update.cjs --generate-key <offline folder>`.
  The tool refuses a folder inside the repository and never overwrites.
- Keep `pokeapp-update-private.pem` offline (encrypted drive or password
  manager, with a backup). It is read only by the signer, which refuses a key
  inside the repository or the build root, prints only error codes and
  never embeds it. Only `pokeapp-update-public.pem` goes into a build; the
  builder and the audit refuse a private key in the package.
- Losing the private key means players need one manual install of a build
  with a new key; a leaked key means rotating it the same way. Keep it safe.
- The rehearsal used a **temporary** key generated for the test and deleted
  afterwards; no stable key was created.

## 6. Activating the public channel (owner)

What only the owner can provide or authorize:

1. **Stable signing key** (and a separate private-channel key), generated and
   kept as in §5.
2. **Authenticode code-signing certificate** (OV or EV). The signer refuses a
   stable manifest unless the installer's Authenticode status is `Valid`
   (existing control, kept). electron-builder signs when given
   `CSC_LINK`/`CSC_KEY_PASSWORD` (or an EV token via `signtool`); the build
   script currently sets `CSC_IDENTITY_AUTO_DISCOVERY=false` and must be run
   with the certificate configured.
3. **Authorization** to deploy the Worker routes (web deploy) and to upload
   the bridge installer and the first stable feed to R2.

### One-time transition from 0.25.0 (and any unconfigured build)

Public 0.25.0 has no key and no feed, so it cannot update itself. The first
public build made with the stable key and feed is the **bridge**: players
install it once from «Descargar Launcher» (same app id and per-user install,
so it replaces 0.25.0 in place and keeps `%LOCALAPPDATA%\PokeApp\Launcher`).
From then on every update is automatic. The 0.26.0 prepared in `12bfb79` was
never published; rebuild it (or the next version) with the key and feed to
make it the bridge.

## 7. Publishing a new version (once active)

1. Bump `companion/launcher/package.json` (+ lock) and
   `web/launcher-release.json`; commit.
2. Build (fresh build root, certificate configured):

   ```powershell
   ./tools/build_launcher_windows.ps1 -BuildRoot <fresh> -Python <py3.14.3> -Dotnet <dotnet9> `
     -UpdatePublicKeyFile <stable public pem> `
     -UpdateFeed https://pokeapp-web.pokeapp-v2.workers.dev/launcher/updates/stable.json `
     -UpdateSigningKeyFile <stable private pem, offline> `
     -UpdateDownloadUrl https://pokeapp-web.pokeapp-v2.workers.dev/launcher/updates/stable/<version>.exe `
     -UpdateMinimumVersion <bridge version> -UpdateNotes "- line one`n- line two"
   ```

   The audit must PASS; `release/stable.json` is the signed manifest.
3. Rehearse the update with private builds (`-PrivateCandidate -Rehearsal`,
   loopback feed, temporary key):
   `node tools/validate_launcher_update_e2e.mjs --a <root A> --b <root B> --va <A> --vb <B> --key <temp private pem> --out <dir>`.
4. Upload the installer **first**, never overwriting a published version:
   `npx wrangler r2 object put pokeapp-launcher-releases/windows/<version>/PokeApp-Launcher-Setup.exe --file <installer> --remote`;
   read it back and compare SHA-512 with the manifest.
5. Upload the manifest **last** — this is the switch players see:
   `npx wrangler r2 object put pokeapp-launcher-releases/updates/stable.json --file release/stable.json --content-type application/json --remote`.
6. Deploy the web if the download card changed (`web/launcher-release.json`).

### Rollback

Clients refuse older versions, so a rollback is **stop offering, then fix
forward**: put back the previous `updates/stable.json` (players not yet
updated see nothing new) and publish a corrected higher version. Installed
versions are never downgraded automatically. Versioned installers in R2 are
kept for this reason.
