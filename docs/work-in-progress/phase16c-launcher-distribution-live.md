# Phase 16C — Windows Launcher distribution

- STATUS: **PHASE 16C DONE / WINDOWS INSTALLER READY / WEB DOWNLOAD LIVE**.
  Physical save writes NOT STARTED. No next packet started.
- HEAD: entry `5e796f68f5bdfeb03109e5c900333ff1e3cf9c6a`; shipped application
  `46cf271b0900d12b2b8fddf6d4e992b0a32597a5`. Documentation/test-harness closure
  follows; obtain its exact HEAD from Git.
- PACKAGER: electron-builder 26.15.3/NSIS per-user x64; PyInstaller 6.22.3,
  Python 3.14.3, self-contained .NET 8.0.29, existing icon. Unsigned preview.
- VERSION: package.json single source, **0.16.1**.
- ARTIFACT: `PokeApp-Launcher-Setup.exe`, 159076230 bytes, SHA-256
  `21f1e6d467ee8be4a924b9e9e6eee48d6933e5e3164bde242cf8a84c5de4d298`,
  actual Authenticode status NotSigned.
- HOSTING: private R2 `pokeapp-launcher-releases`, one versioned object,
  r2.dev disabled/no custom domains. Existing web Worker serves
  `https://pokeapp-web.pokeapp-v2.workers.dev/launcher/download`.
  Cloudflare deployment `cfeba61c-40d6-42a4-96e8-4b66dd333653`, version
  `88b39acc-8850-4e9e-ab1b-c6ce1cb98398`, 100%, committed application source.
- WEB CTA: direct **Descargar Launcher**, Windows 10/11 · v0.16.1 in Save card.
- TESTS VALID: build/content audit, hidden installed READY/CACHED with bundled
  parser and stripped dev environment; install/reinstall/uninstall/data retention
  PASS. Worker 2, React 1, local browser 2, hosted download/hash 1 PASS.
  TS/build, Ruff/compile/format/diff/dry-run PASS. Hosted account/API is simulated;
  deployed assets and installer are real and match local bytes.
- CURRENT STEP: closure. No backend, migration, owner business/save, V1/Shadow
  or Streamlit changes. No database-wide preservation recheck claimed.
- NEXT STEP: owner may remove `%TEMP%/pokeapp-phase16c-20261013`; no temporary
  executable remains, app was uninstalled. Automatic approval review rejected
  exact recursive cleanup: **blocked by policy**. Do not retry via another mechanism.
  Then wait for an authorized acceptance/distribution-hardening packet.
- DO NOT REPEAT: implementation, tests, artifact upload or deployment.
  No ORAS/Gen7, auto-updater or physical save writes.

[Report](../phase16c-launcher-distribution-report.md),
[evidence](../phase16c-launcher-distribution-evidence.json),
[build/release instructions](../launcher-windows-distribution.md).
Private verified artifact/evidence archive:
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase16c/20261013/release-46cf271`.
Unsigned/SmartScreen and no-clean-VM limits remain explicit. Protected guide and
unrelated untracked files untouched. Prior Cloudflare rollback version:
`77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11`.
