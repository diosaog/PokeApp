# Phase 17.3 — final product UX

STATUS: PHASE 17.3 DONE / READY FOR FINAL VISUAL REVIEW

FINAL HEAD: `895ef42` (main/origin aligned)

DONE:

- Reusable Pokémon selector for Blindar, Revivir and Robar, with server-provided
  targets, own-party/box grouping, dead-only revive filtering, rival selection,
  visible status flags and confirmation before the existing redemption command.
- Liga jornada results use compact match cards and a winner confirmation modal.
- Sidebar navigation is grouped by product area.
- Spectator Team Preview uses a desktop `Equipo 1 VS Equipo 2` layout and a
  stacked mobile layout while preserving the existing privacy and Team Lock
  authority.
- Existing open shop items remain visibly unavailable for redemption because
  the live catalog exposes no variant/effect contract. No product or effect was
  invented; a future explicit catalog variant can be added without changing the
  Pokémon redemption authority.

TESTS VALID:

- Focused Vitest: 3 files, 14 tests passed.
- Affected browser journeys: 4 corrected legacy flows passed; product collection,
  privacy, reduced motion and Home animation journeys passed at 1440/900/390.
- TypeScript/Vite production build and Prettier/diff checks passed.

DEPLOYMENT: Cloudflare only, deployment `9f1704e5-872d-4688-bfed-3eb69be036e4`
(`Phase 17.3 product UX`), 100%. Railway, Supabase, V1, Shadow, R2 and owner
competitive data were untouched. API health returned 200 and anonymous trainer
read returned 401. The current shell could not complete a Cloudflare edge GET
because of a transient connection timeout after deployment; Wrangler reports the
deployment active at 100%.

REMAINING: Antonio's final visual review. No next packet starts from this
closure.

DO NOT REPEAT: Phase 16, historical migrations, PostgreSQL, full Phase 17.2
matrices, Launcher packaging, V1/Shadow or physical save writes.
