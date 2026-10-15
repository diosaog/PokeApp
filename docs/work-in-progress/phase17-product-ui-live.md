# Phase 17 — product/UI rework

- PHASE: 17
- STATUS: IMPLEMENTING
- HEAD: entry `9efd5b324ac48dc86a54f0a9bbde519d7e5a3917`, fetched main/origin 0/0.
- CURRENT CHECKPOINT: 17B trainers/profile/PC
- CHECKPOINTS DONE: 17A foundation/assets, validated locally; deployment held for final.
- CURRENT SCREEN: trainers and bounded PC composition
- NEXT SCREEN: 17C battles, then D/E/F sequentially
- TESTS STILL VALID: foundation 25 focused React/catalog PASS; TS/Vite PASS;
  1,363 available asset hashes verified. 102 missing item images are explicit
  fallbacks. 617 exact X/Y Spanish move descriptions. No runtime external assets.
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
