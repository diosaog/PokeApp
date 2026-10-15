# Phase 17.2 — public trainer collections and final product polish

2026-10-15. **STATUS: PHASE 17.2 DONE.**
Entry `f692ced8e63446c5943f7e467a8af4af474ecd73`, fetched main/origin 0/0,
clean tracked tree. Application `ee3efcd63567ebef1f90dd5d88bc413cb1579fa7`;
final defensive read correction `d7eb78b66861a4bddd1d79ec3eebc93c7429d1a1`.
Both were pushed before their deployments.
[Live record](work-in-progress/phase17-2-product-polish-live.md).

## Product and visibility

The owner's 17.2 decision supersedes the earlier private-box interpretation.
Authenticated enabled viewers can now inspect a trainer's current party, boxes
and dead Box 8, even without a Team Lock. The new read-only trainer collection
endpoint checks season membership, current save ownership, parser version and
available provenance. Its explicit nested DTO allowlist removes IVs, ability,
nature, EVs, identity IDs/evidence, raw metadata and Storage references. The private
PC endpoint remains bound to the verified viewer. Browser table/RPC privileges
are unchanged; no migration or new storage authority was needed.

The live collection and official Team Lock have separate labels and sources.
Neither can rewrite the other. Missing save/counter remains unknown. A partial
legacy payload without party or boxes cannot prove empty boxes. Existing progress
and actual badge positions remain authoritative; no new progress semantics.

Inventory's home is the trainer's own profile, beside the identity card on wide
screens and directly below it on smaller screens. Purchases, reward vouchers and
their existing redemption flow are retained. Shop focuses on buying and links to
the profile. Rival purchases remain private; public boxes do not expand robbery
eligibility beyond existing official-team targets. The own wipe editor is available
in an expandable profile section, and rivals' recorded counts have a read-only
projection. Existing League editing remains available.

Party slots are larger than box slots. Only visible party/team and inspected detail
opt into real animations; box/dead/list grids remain static. Offscreen and hidden-tab
animations revert to static images; reduced motion uses static assets. Horizontal
desktop detail, responsive mobile layout, self-only IV bars/ability/nature, item and
move treatments remain. Team Preview keeps its six-card structure and official locks.

## Admin diagnosis

Several forms passed an ineligible/disabled condition as `pending`, so disabled
actions showed an endless spinner without a request. `Submit` now distinguishes
in-flight from disabled, including Admin, rules, championship, initial assignment,
inventory and wipe forms. A stalled GET ends with a visible 20-second timeout;
there is no automatic timeout retry. Admin offers an explicit read retry. Business
commands retain their original idempotency, unknown-outcome handling and CAS guards.

The existing trainer flow adds an already-created account to a draft roster. There
is no unfinished public account-creation API to complete; the UI now states that
scope rather than suggesting that it creates a new identity or PIN.

## Autonomous art decisions and assets

- Original geometric SVG linework gives each section a setting: arena, League
  structure, PC terminal, shop shelving, trainer dossier, Hall arches and archive.
  Shared section colors remain. Soft ambient glow respects reduced motion; no
  large scene banner, external runtime image service or heavy rendering library.
- Profile identity/inventory form a common command area. Wipe editing stays folded
  until requested. Larger badges, party cards, PC rails, battle borders and restrained
  shadows reinforce the hierarchy while preserving readable controls.
- 721 real animations, 33,930,353 bytes stored as independent lazy assets. Gen 1–5
  use original Black/White animation; Gen 6 uses Showdown models, from pinned
  [PokeAPI/sprites](https://github.com/PokeAPI/sprites/tree/ba403973fdf9d0ac59175813861e6a1f8ed5020c).
  Hashes/source URLs and attribution are versioned; the builder verifies animation
  frames. The full set is never downloaded as a page bundle.
- Existing optimized wildcard art is reused. A catalog-code fallback maps the
  61 seeded shop products; canonical item names take precedence. Two bottle-cap
  PNGs fill the remaining gaps. These icons do not enable another game generation
  or implement physical item effects. Unknown/unavailable assets retain fallbacks.

Visual changes live principally in `product-polish.css`, the presentation helpers
and versioned assets, making the artistic layer straightforward to review/revert.

## Validation

**53 focused Python**, **68 affected React**, **51 unique affected Edge cases PASS**.
Python covers the new public allowlist, self/admin/rival parity, JWT/disabled-user
denial, season/owner/deleted-save scope, unknown versus zero, malformed provenance,
partial payloads, immutable history and bounded repository reads. Existing PC,
scouting and inventory batch regressions pass. No unrelated historical matrix was
rerun; PostgreSQL/rebuild is N/A because SQL, schema, grants and migrations are unchanged.

Browser proof covers profile/scouting without locks, live boxes/dead, self/public
detail privacy, animation scope/reduced motion, inventory relocation and redemption,
Admin guards/unknown outcomes, Team Preview, all tabs and long names. Viewports
1440/900/390 plus the retained affected responsive journeys pass. Screenshots were
reviewed for profile, detail and arena on desktop/mobile/intermediate sizes.
TypeScript/public Vite build, formatting, targeted Ruff/compile, Wrangler dry-run
and diff checks pass. All 721 local animation hashes match the manifest.

Harness corrections were limited to invalidated assumptions: full navigation lost
the in-memory login, an old voucher assertion preceded the new inventory navigation,
and late Home requests polluted a rival-only request window. Formatting triggered
one Vite reload mid-run; its 900px test was repeated on stable source and passed.
Final evidence combines passing unaffected cases with focused passing reruns.

## Delivery, preservation and boundaries

Railway is healthy at deployment `c4ed81bf-da7f-4ea5-9b20-5a8bb4344f36`, image
`sha256:ac40a3ca47df3b1198f6841c411b0e8a11b1b12018152b402940d1c2ba250ff4`,
serving final source `d7eb78b66861a4bddd1d79ec3eebc93c7429d1a1`. Cloudflare is
100% on deployment `a132a525-70a0-4727-b4f4-85f837379cc3`, version
`33849862-0eef-40e6-b5a7-54228e8684e2`, with the same source message. The final
read-only public probe passed **31 checks** and the unauthenticated browser smoke
passed **10 visits** at desktop and mobile widths. Assets, security headers, exact
CORS, API health, collection denial, animated samples, atmosphere SVGs and shop
icons match the local build. No credentials or business mutation was used.

The after capture has 59 tables and 36 migrations through 044, with history,
stable owner identity/credentials, security catalog, private inbox and Advisor
ERROR/WARN findings unchanged. Three Auth activity tables differ only by expected
owner session/refresh activity (`auth.users`, `auth.sessions`,
`auth.refresh_tokens`); all other public/business tables are byte-for-byte equal.
No SQL migration, R2 object, V1/Shadow, Launcher or physical-save write occurred.

Authenticated journeys use local browser fixtures and API TestClient principals;
they are not claimed as fresh hosted PIN login or positive owner mutations. Hosted
proof checked health, route authentication, security headers/CORS, assets and
anonymous login-gate rendering. No PIN was requested or credential bypass invented.

Known limits: current parser game/progress support is unchanged; sprites use base
species art rather than introducing form/shiny evidence. Account provisioning and
rival purchase visibility are not expanded. The animation library adds hosted
asset storage, while runtime requests remain bounded to visible teams/detail.
No representative load benchmark is claimed for the new six-read selected profile.

Next: **STOP** for Antonio's visual acceptance. No next packet, new game support or
physical writes.
