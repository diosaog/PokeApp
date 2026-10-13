# Phase 16C — Windows Launcher and direct web download

Closed 2026-10-13. **PHASE 16C DONE / WINDOWS INSTALLER READY / WEB DOWNLOAD LIVE.**
Physical save writes **NOT STARTED**. One temporary build directory remains because
automatic approval review rejected cleanup; application uninstall itself passed.
[Evidence](phase16c-launcher-distribution-evidence.json),
[build/release instructions](launcher-windows-distribution.md),
[live record](work-in-progress/phase16c-launcher-distribution-live.md).

Entry main/origin `5e796f68f5bdfeb03109e5c900333ff1e3cf9c6a`, 0/0, tracked tree
clean; 16B DONE verified. Application source
`46cf271b0900d12b2b8fddf6d4e992b0a32597a5` was committed/pushed before R2 creation,
upload and Cloudflare deployment. Closure adds evidence and a hosted-test fixture
origin correction without changing the shipped application.

## Installer

**PokeApp Launcher 0.16.1**, Windows 10/11 x64, per-user NSIS with Start Menu and
normal uninstall registration. Existing icon, no admin elevation or automatic launch
after installation. Electron 44.7.0, Python 3.14.3 and self-contained .NET 8.0.29 /
PKHeX 24.11.11 are bundled. No user Python, Node, npm or SDK installation is needed.
`package.json` supplies the package, installer, web label and download object version.

Pinned npm, Python and Windows parser locks plus the documented PowerShell build
command produce the complete installer. Reproducible inputs/procedure are established;
bit-identical rebuilds are not claimed. Packaging uses a narrow Python overlay so
the backend domain barrel does not import unrelated competitive modules. No server
source was changed. The asar and frozen application modules were inspected; no
tests, fixtures, private evidence, owner saves, secrets or migration tools are included.
Runtime support libraries carry notices. Covered parser source/build inputs and
upstream license are included; no whole-repository relicensing claim is made.

User config/cache/token location remains outside installation at
`%LOCALAPPDATA%/PokeApp/Launcher`, with Electron data in `shell`. Existing DPAPI code
is unchanged. Packaged mode ignores development Python/parser overrides.

Installer: **159,076,230 bytes**. SHA-256:
`21f1e6d467ee8be4a924b9e9e6eee48d6933e5e3164bde242cf8a84c5de4d298`.
Actual signature inspection: **NotSigned**. SmartScreen may warn; no certificate
was fabricated/purchased, and no auto-updater was introduced.

## Proof and delivery

Final documented build and payload audit pass. A disposable per-user install
started hidden with developer PATH removed and invalid .NET/development executable
paths. Its bundled core parsed a new synthetic X save (31 boxes, unknown progress);
a second start recovered cached state. Save hash unchanged. Sandbox/context isolation
enabled, renderer Node disabled, no page errors. Reinstall preserved local data;
uninstall removed application, Start Menu entry and HKCU registration while retaining
data. All three installer operations returned zero. This is isolated Windows-host
proof, not a clean VM or independently tested Windows 10 installation.

Focused checks: Worker **2**, React **1**, desktop/mobile browser **2**; TypeScript,
public build, Ruff/compile, formatting/diff and Wrangler dry-run pass. Hosted browser
**1** downloads the real installer through the deployed Save button and verifies
the exact hash. Hosted account/API responses are simulated to isolate distribution;
this is not a production login/owner-session proof. Live HTML, JS/CSS, SPA route,
build-config/API target, download HEAD/MIME/disposition/nosniff and API health pass.
No unrelated backend, database, parser matrices or historical suites were rerun.

The harness was corrected for PowerShell native stderr handling, versioned NSIS
registry naming and hosted fixture API origin. Before the last fix, one synthetic
PIN attempt reached the API and was rejected; no successful owner login or business
mutation occurred. Default urllib received 403; final httpx and real Edge proofs
pass. No application retry/timeout behavior was changed.

Owner enabled R2. Only one private bucket and one versioned installer object were
created: `pokeapp-launcher-releases/windows/0.16.1/PokeApp-Launcher-Setup.exe`.
r2.dev is disabled and no custom bucket domains exist. Existing Worker streams the
fixed object through [the direct HTTPS download](https://pokeapp-web.pokeapp-v2.workers.dev/launcher/download).
Save shows **Descargar Launcher** and **Windows 10/11 · v0.16.1**. No bucket listing,
upload or arbitrary object selection is exposed.

Cloudflare deployment **cfeba61c-40d6-42a4-96e8-4b66dd333653**, version
**88b39acc-8850-4e9e-ab1b-c6ce1cb98398**, 100%, exact application source above.
Previous version **77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11** is the rollback reference.
Railway was not redeployed. No migration, DB/business/Storage save write, V1, Shadow
or Streamlit operation occurred. Preservation follows the bounded operation scope;
no new database-wide hash comparison is claimed.

## Limits and next step

Unsigned preview and isolated-host proof are the distribution limits. npm reports
eight moderate advisories in the build-only electron-builder dependency chain
(sprintf-js precision DoS); those Node build modules are absent from the installer.

Release/private evidence: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase16c/20261013/release-46cf271`;
archived installer hash verified. No temporary executable process remains.
Automatic approval review rejected recursive deletion of
`%TEMP%/pokeapp-phase16c-20261013` with **blocked by policy**. It remains for owner
cleanup; no alternate deletion method was attempted. Protected guide and unrelated
untracked files untouched. Final closure HEAD is obtained from Git.

Next recommended packet: acceptance/distribution hardening on a clean Windows
machine, with real signing assessed separately. **STOP; next packet not started.**
