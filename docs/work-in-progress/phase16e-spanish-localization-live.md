# Phase 16E — Spanish Pokémon presentation

- STATUS: **PHASE 16E DONE** — 2026-10-15. WEB SPANISH LOCALIZATION: COMPLETE
  FOR CURRENT SUPPORTED DATA. PRIVACY: UNCHANGED. [Evidence](../phase16e-spanish-localization-evidence.json).
- HEAD: entry `793a82f49228ae075c5724ad55616330e273989c`; application
  `29aecbcfe11f92b076224a9e6684e8194001d905` pushed before deployment.
  Documentation closure follows separately; obtain its exact HEAD from Git.
- SOURCE USED: pinned PKHeX.Core 24.11.11 embedded EN/ES resources; generated
  catalog SHA-256 `ed60ed38d59930dc25eefe0cd4d7c3dec743bd589481eb2813d8f6921d87b54d`.
  [Source/reproduction](../../web/src/pokemon/README.md); 14 resource hashes and
  locked package, byte-exact regeneration proven. Gen3–5/X/Y ranges only.
- CATEGORIES DONE: species, moves, abilities, items, types, natures; existing stat
  labels. IDs/domain calculations/nicknames unchanged; one shared web resolver.
- SURFACES DONE: PC/party/boxes/search/dialogs, own/rival profiles, scouting,
  Team Preview, Shop/inventory names and target selectors. Hall currently exposes
  no Pokémon detail fields and needed no change. Privacy unchanged.
- MISSING DATA: no Pokémon description fields or proven version-aware flavor
  source; existing Spanish Shop descriptions retained. Ambiguous numeric Gen3 vs
  Gen4+ items without game context explicitly unavailable; no guessed mapping.
  Launcher 0.16.2/final desktop parity deferred; physical save writes not started.
- CURRENT STEP: closure complete. Cloudflare deployment
  `be29d897-ac38-403a-8b78-8fa2acdc8c8c`, version
  `0d9eeea0-0081-448f-b330-701678e5ee94`, 100%, application source above.
  Only new HTML/JS assets uploaded. API, SQL, projections, Launcher/R2 unchanged;
  no owner-data requests/mutations, no database work. No listener on 5173 remains.
- NEXT STEP: **OWNER PRODUCT REVIEW / EXTRA REQUESTS. STOP.**
- TESTS VALID: 40 focused React/catalog tests (39 plus final added catalog case),
  14 Python public-projection tests; 16 affected Edge cases (12 passed plus four
  corrected text-expectation cases rerun/passed). Initial 3 new Edge cases passed
  separately too. No application change after browser run; mobile reviewed.
  Locked exporter/reproduction, TS/Vite (492.32 kB JS / 153.41 kB gzip), Prettier,
  Wrangler dry-run and diff checks pass. Phase13 assertion updated to Spanish but
  its real-DB matrix NOT RERUN. Public BEFORE/AFTER: 9 safe HTTP checks each pass;
  live JS/CSS equal final build, API health, SPA/security headers and exact CORS /
  unauthenticated denial pass; zero unexpected 5xx. Hosted authenticated positive
  UX not claimed; browser proof uses local synthetic API fixtures. Raw logs and
  screenshots: `%LOCALAPPDATA%/PokeApp-migration-evidence/phase16e/20261015`.
- DO NOT REPEAT: 16D sync/PG/parser/installer matrices, historical phases. Do not
  touch owner data, protected guide, R2 installer or physical save bytes.
