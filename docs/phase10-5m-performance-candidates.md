# Phase 10.5M - Directed read guard and deferred candidates

Entry: `4a7537438ad19cdd6152d339b07caad4bd94de93` (L DONE verified).
Scope is the current General/overview, Trainers/scouting, Shop/inventory, Admin
and L progress read paths. This is not a Phase 14 load benchmark or broad audit.

## Impact map (before implementation)

- **MEASURE:** three sequential authenticated GET samples for nine existing reads;
  cold `/tienda` in separate desktop/mobile browser contexts; decoded body bytes;
  business repository call counts, excluding JWT resolution and SQL inside RPCs.
- **LIKELY BOTTLENECKS:** Inventory mounts overview solely for redemption names;
  broad overview composition; inventory's sequential rival identity reads.
- **EXPECTED WRITE:** Inventory's name lookup, focused read/request guards and docs.
- **TESTS INVALIDATED:** frontend economy/name integration and request counts.
  Backend behavior, schema, mutation matrices and parser are unchanged.
- **OUT OF SCOPE:** aggregation redesign, speculative cache, economic/sporting rules,
  cloud ingestion, global reactive state alignment and private profile expansion.

## Structural evidence and reproduction

`web/src/features/inventory.tsx` previously subscribed to overview on mount; only
the redemption target's trainer name consumed it. It now enables the existing
`/v1/read/trainers` read while a redemption is open. IDs still come exclusively
from server-approved inventory targets. Missing/loading/error names retain the
existing `Entrenador` fallback. Nothing is fetched per target; session-scoped query
keys, logout clearing, mutation bodies, retries and invalidations are unchanged.

Cold Shop requires **shop + inventory**, instead of **shop + inventory + overview**.
With no cached names, opening a redemption adds one bounded names read instead of
loading the competition overview. Its select is exactly `id,display_name` from
`public_trainers`, with a 501-row guard that fails rather than silently truncating.
The existing shared list is global public trainer names, not private profiles.

The new test in `tests/test_api_frontend_reads.py` exercises 1 and 100 participants:
overview makes 12 bounded row requests plus one observed-progress RPC, while names
make one row request. These are repository round trips, **not database statement
counts inside functions**. The removed overview represents 13 business repository
calls for a participating viewer; nonparticipants have no balance query.

Reproduce the guard with:

```text
.venv-api/Scripts/python.exe -m tools.run_unit_tests --pattern test_api_frontend_reads.py
cd web
node node_modules/@playwright/test/cli.js test e2e/performance.spec.ts e2e/economy.spec.ts
```

The browser guards start at `/tienda` before login, so Home cannot warm overview.
They cover six rival targets, exclude the own target for robbery, preserve the
selected entity while names arrive, exercise missing/failed names and cached
reopening, and preserve the existing uncertain redemption retry proof. Development
StrictMode can cancel an initial mount request; the local guard counts completed
responses. Hosted evidence measures a production build with fresh contexts.

## Phase 14 candidates, ranked

| Priority / flow | Observed issue and likely cause | Future approach | Risk / why deferred in M |
| --- | --- | --- | --- |
| HIGH — Overview / Trainers / daily Liga | 13 sequential business repository calls for a participant. Trainers loads matches, memberships, season-wide locks and official days it does not render. `FrontendReads.overview` reads whole snapshot JSON before projecting standings. | Measure representative full seasons, then narrow trainer and snapshot projections or introduce a bounded aggregate read with explicit current/frozen sources. | Changes repository/query contracts and privacy/history validation. Needs real PostgreSQL and equivalence evidence; a small frontend name lookup does not justify that rewrite. |
| HIGH — Inventory targets | `FrontendReads.inventory` reads PC/eligibility before knowing whether any purchase needs a target. Each rival lock calls `observed_entities`: one observations query, plus one owner-scoped entities query if observations exist. Work grows with rival locks even while the modal is closed. | Split purchase listing from on-demand target preparation, or batch verified `(season, trainer, save)` pairs with bounded owner filtering. Measure real populated saves first. | Pokémon identity, public locks and private PC must stay separate; stale eligibility must still be checked transactionally at redemption. Requires query/privacy/concurrency proof beyond M. Empty hosted inventory does not benchmark the populated branch. |
| MEDIUM — Shop | Five business repository calls on an active participating season; season/current day, offers, catalog, membership and exact wallet are sequential. | Consider one bounded aggregate with exact numeric text after measuring item counts, latency and plans. | Promotion timing, authorization and post-League balance semantics cannot be cached speculatively. Current semantics remain intact. |
| MEDIUM — Scouting / Team Preview | Five bounded calls when a current day exists. Reads all current-day public locks to show the selected team(s); no per-player query loop. Own Battle adds one private self-lock read. | Evaluate narrower selected-lock reads or an aggregate while keeping the explicit public allowlist and absent-team semantics. | Shared H/K privacy boundary; no rival parsed-save fallback. Wider query changes need focused PostgreSQL/privacy proof. |
| MEDIUM — Admin refetch | `useAdminCommand` in `web/src/features/admin.tsx` uses `useCommand()` without paths; `web/src/ui.tsx` invalidates all cached queries. Participants/Competition/Risk also mount overview. | Build the mutation-to-visible-view dependency matrix first, then narrow invalidations and obsolete reads. | Blind narrowing can leave stale rules, points or balances. This overlaps the authorized future final alignment and is not solved by M. |
| LOW / NOT WORTH NOW — General, progress, Admin aggregates | General, self progress, Admin setup and championship each invoke an existing aggregate RPC. No application per-player HTTP loop was found in these directed paths. | Measure plans and full-season sources in Phase 14; retain the current bounded API calls meanwhile. | The hosted championship is incomplete and progress unknown. One sample is not evidence for new indexes, denormalization, Redis or global caches. |

## Final 10.5 product alignment findings (not implemented here)

1. **Simple Admin rules:** `admin.tsx` still presents configuration versions and
   effective rounds. Keep internal history/versioning while making prospective
   rule edits natural. Never recalculate completed days from new rules.
2. **Visible-state refresh:** establish a dependency matrix across points, coins,
   deaths, progress, rewards and Team Lock. Exact current sites to review:
   - `core.tsx` Shop command invalidates shop/inventory/overview/league.
   - `inventory.tsx` redemption invalidates inventory/overview/league/initial-assignment;
     shop, PC and progress are not in that list. Determine which redemption effects
     actually affect each view before extending it; physical save changes are pending.
   - `wipe-revivals.tsx` invalidates its counter, General, initial assignment and
     the current Admin day, but not overview. Verify whether each overview field
     is live or intentionally frozen before changing this.
   - `progress.tsx` refreshes only its own progress query; Trainers' overview has
     separate cached progress. Full ingestion is unfinished, so no cross-app sync
     guarantee should be inferred from a local Launcher journal.
   - `team-preview.tsx` combines overview invalidation with the existing preview/
     scouting invalidation path. Preserve their private/public separation.
   - `state.tsx` keys reads by authenticated trainer and path, uses a 15-second stale
     period and disables focus refetch. Keep session isolation when aligning updates.
3. **Visual trainer profiles:** `core.tsx` Trainers currently consumes overview.
   Future clickable profiles should load only needed public stats/progress/team,
   Pokemon detail and authorized own PC; never reuse raw rival save data.
4. **Shop categories:** organize the existing catalog under Comodines, Bayas,
   Competitivos and Crianza without changing eligibility, prices or wallet precision.
5. **Obvious visual product:** short copy, visual cards and clear actions. M changes
   a read dependency only; it does not redesign these flows.

Keep J's participant normal lifecycle authorization, championship 4+ / residual
tie support and reliable first-Team-Lock timing as **implementation gaps**, not
new requests for owner decisions. FINAL 10.5 PRODUCT ALIGNMENT is next after M;
it is not started by this package. Phase 11 remains NOT READY / NOT STARTED.
