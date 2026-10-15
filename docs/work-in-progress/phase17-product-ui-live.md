# Phase 17 — product/UI rework

- PHASE: 17
- STATUS: IMPLEMENTING
- HEAD: entry `9efd5b324ac48dc86a54f0a9bbde519d7e5a3917`, fetched main/origin 0/0.
- CURRENT CHECKPOINT: 17D shop/inventory
- CHECKPOINTS DONE: 17A foundation/assets; 17B trainers/profile/PC; 17C battles. Deployment held for final.
- CURRENT SCREEN: visual shop and inventory cards
- NEXT SCREEN: 17E remaining pages, then F QA
- TESTS STILL VALID: foundation 25 focused React/catalog PASS; TS/Vite PASS;
  1,363 available asset hashes verified. 102 missing item images are explicit
  fallbacks. 617 exact X/Y Spanish move descriptions. No runtime external assets.
  17B collection/progress 8 React PASS; TS/build PASS; desktop/mobile 2 journeys PASS.
  Reviewed screenshots; corrected inherited accent and profile text encoding.
  17C six browser cases PASS (four privacy/lock flows + two responsive move popovers),
  TS/build PASS. Self private fields remain behind the discriminated projection.
- VISUAL DECISIONS: dark green/coral, existing sidebar, local versioned sprites;
  reuse profile photos and badge/shop art already in the project. Prefer canonical
  game assets over Showdown community sprites requiring additional permission.
- DEFERRED PRODUCT QUESTIONS: rival boxes/dead box/inventory are not authorized by
  current projections; retain privacy. Missing photos remain honest placeholders.
  Move reference must label its game version when the source team omits it.
  Hall team snapshots are absent from current read DTO; never substitute live PC.
  Final desktop should share finished React UI near release; not implemented here.
- DO NOT REPEAT: historical phases, parser/PG/installer matrices. No owner-data
  mutations, V1/Shadow/Streamlit/R2 installer writes or protected-guide access.
