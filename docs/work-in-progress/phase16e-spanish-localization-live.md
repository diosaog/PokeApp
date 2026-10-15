# Phase 16E — Spanish Pokémon presentation

- STATUS: VALIDATED; web deployment/closure pending.
- HEAD: entry `793a82f49228ae075c5724ad55616330e273989c`, main/origin 0/0.
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
- CURRENT STEP: commit/push validated source; deploy Cloudflare only.
- NEXT STEP: public assets/health/security checks, documentation closure, STOP.
- TESTS VALID: 40 focused React/catalog tests (39 plus final added catalog case),
  14 Python public-projection tests; 16 affected Edge cases (12 passed plus four
  corrected text-expectation cases rerun/passed). Initial 3 new Edge cases passed
  separately too. No application change after browser run; mobile reviewed.
  Locked exporter/reproduction, TS/Vite (492.32 kB JS / 153.41 kB gzip), Prettier,
  Wrangler dry-run and diff checks pass. Phase13 assertion updated to Spanish but
  its real-DB matrix NOT RERUN. Public BEFORE: 9 safe HTTP checks pass.
- DO NOT REPEAT: 16D sync/PG/parser/installer matrices, historical phases. Do not
  touch owner data, protected guide, R2 installer or physical save bytes.
