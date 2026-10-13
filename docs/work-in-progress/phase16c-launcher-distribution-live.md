# Phase 16C — Windows Launcher distribution

- STATUS: LOCAL VALIDATED / PUBLICATION PENDING. Entry 16B DONE verified.
- HEAD: entry main/origin `5e796f68f5bdfeb03109e5c900333ff1e3cf9c6a`, 0/0.
- PACKAGER: pinned electron-builder/NSIS, per-user x64; PyInstaller onedir core;
  self-contained .NET 8 parser. Existing icon. Unsigned preview.
- VERSION: package.json single source, 0.16.1.
- ARTIFACT: final build and content audit PASS; private workspace
  `%TEMP%/pokeapp-phase16c-20261013/final-build`. Windows PowerShell native stderr
  handling fixed in the build command; real exit codes determine build success.
- HOSTING: owner enabled R2; fresh bucket list succeeds and is empty. Use one
  private release bucket and existing web Worker. No backend/schema changes.
- WEB CTA: direct link implemented, existing Saves Launcher card only.
- TESTS VALID: content audit; direct download Worker 2, React 1, desktop/mobile
  browser 2; TypeScript/public build and Wrangler dry-run PASS. No backend change.
- CURRENT STEP: local installed runtime PASS (READY then CACHED), per-user install,
  reinstall and uninstall PASS, Start Menu/registry removed, local data retained.
  Save hash unchanged; developer PATH removed. Installer SHA-256
  `21f1e6d467ee8be4a924b9e9e6eee48d6933e5e3164bde242cf8a84c5de4d298`,
  159076230 bytes, actual Authenticode status NotSigned.
- NEXT STEP: commit/push before R2 artifact/web publication; hosted checksum/CTA
  proof and final documentation. No remote resources created yet.
- DO NOT REPEAT: 16A/16B implementation or historical suites. No Railway,
  Cloudflare unrelated changes, migration, V1/Shadow, physical save writes.

No signing certificate is available. A clean Windows VM is not available;
installation proof will use an isolated directory/profile and stripped runtime
environment on this Windows host. Protected guide and unrelated files untouched.
