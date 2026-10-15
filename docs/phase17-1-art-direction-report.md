# Phase 17.1 - art direction and visual polish

Closed 2026-10-15. **STATUS: PHASE 17.1 DONE. ART DIRECTION: COMPLETE.
PRODUCT PERSONALITY: IMPROVED. PRIVACY: PRESERVED. COMPETITIVE LOGIC: UNCHANGED.
PHYSICAL SAVE WRITES: NOT STARTED.**

Entry main/origin `53e72d3c5d881e1294d4ccff9788700c87493739`, fetched 0/0,
clean tracked tree. Application source **`9207bef39ff577d9c194db72c7219c47a0a8e179`**
was committed and pushed before the single Cloudflare deployment.
[Evidence](phase17-1-art-direction-evidence.json),
[artistic decisions and handoff](work-in-progress/phase17-1-art-direction-live.md).

## Visual result

One neutral blue-black card/control system now supports 11 distinct accents:
warm coral Home, championship gold Liga, rose/violet Batallas, teal Entrenadores,
blue PC, lavender Shop, orange Copa, antique gold Hall, muted purple Juicios,
cyan Save and slate Admin. Subtle arena lines, PC grid, shop dots and quiet
section geometry replace the global green wash. No new decorative page banners,
Pokemon scenes or new product flows were introduced.

Team Preview retains six compact cards and directly visible moves. Each move
uses its canonical type family on a contrast-safe dark fill. One compact
disclosure unfolds directly beneath the activated move; type/category icon,
power/accuracy and Spanish description have separate spacing. Keyboard, Escape,
close button, tap and reduced-motion behavior are covered. Details still explicitly
reference X/Y; missing game context is not guessed. A restrained primary-type halo
emphasizes hovered/focused Pokemon without coloring the entire sprite background.

Pokemon detail is horizontal on desktop: identity/sprite, private IVs and traits,
then four static move labels. Mobile stacks those groups. IV bars preserve exact
0–31 values and show the number at the right; absent/invalid values stay unknown.
EV presentation is removed from both detail and normal Team Preview, while data
contracts remain intact. Public projections never render private IVs/ability/nature.
PC navigation is centered above the unchanged grid, with inset terminal framing.

Trainer frames/stat separators, Shop item tiles, Hall prestige details, Cup
round borders and Admin fieldsets were refined. Each autonomous choice and its
purpose/location is recorded in the handoff for individual keep/change/revert.

## Badges and boundaries

50 canonical badge images are mirrored locally from pinned PokeAPI/sprites
`ba403973fdf9d0ac59175813861e6a1f8ed5020c`: Kanto, Johto, Hoenn, Sinnoh, both
Unova variants and Kalos. BW and B2W2 use different explicit sets; Johto's Kanto
set is separate. [Provenance and limitations](../web/public/visuals/badges/v1/ATTRIBUTION.md)
and per-image source/hash are retained. Added image bytes: **583,457**.
No runtime asset hotlinks or invented badges. Hoenn artwork can identify ORAS's
same badges; this does not implement ORAS. Alola trials are not mapped to badges.

Earned, unearned and unknown remain distinct. Known game plus unknown evidence
may show a subdued, explicitly unobserved set. No game means no guessed set;
missing Unova variant uses the neutral fallback. Kalos artwork does not change
unsupported X/Y competitive progress into observed facts. Rival PC, Team Lock,
history, economy, permissions and synchronization authority are unchanged.

## Validation and delivery

**24 focused React PASS; 22 unique affected Edge cases PASS.** The first browser
run passed all 19 affected journeys; three art/contrast tests also passed. Five
screenshot cases were refreshed after the final CSS-only correction. No skipped
or flaky cases. Initial focused validation exposed a text-encoding issue and a
test-fixture type omission; both were corrected. The final focused run passes.

Desktop 1440, intermediate 900 and mobile 390 screenshots were captured and
actually reviewed across Home, Team Preview, trainers/profile, PC/detail, Shop,
Hall and Save; Liga, Cup, Juicios and Admin were reviewed too. Review caught an
inherited type background on the whole modal and corrected it before publication.
All 18 move types plus unknown meet **4.5:1** for normal move text and PP. This
is targeted contrast/accessibility evidence, not a full WCAG certification.

TypeScript/public Vite build, final Prettier, targeted builder Ruff/compile,
diff, 50 asset hashes, move-type/reference parity and Wrangler dry-run pass.
Backend/PG/parser/Launcher matrices were not invalidated and were not rerun.
Main JS is about 490.59 kB / 155.55 kB gzip; full descriptions remain lazy and
the small type lookup is local. No new API reads, wider invalidation or per-player loop.

Cloudflare deployment **`9fab9bdd-d4b8-473e-b901-8458ad45a9d6`**, version
**`681265e6-c1b0-4a37-8357-6a539f01adc1`**, 100%, exact application source above.
Public: **67 HTTP checks + 10 real headless browser visits PASS**, including exact
JS/CSS/new badge bytes, health, auth denial, CORS, security headers and SPA paths;
zero unexpected 5xx. Browser visits verified the unauthenticated login gate without
interception or credentials. Authenticated presentation/privacy proof is local
synthetic evidence; no hosted owner PIN/login or positive business mutation.

Only Cloudflare web delivery changed. Railway, Supabase, migrations, V1, Shadow,
Streamlit, Storage, installer/R2 objects and owner saves were not operated on.
This phase performed no DB baseline comparison and makes no fresh database-hash
claim; preservation rests on unchanged backend/contracts and zero business writes.
No test server remains on 5173. Screenshots/logs are retained privately under
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase17-1/20261015`; task artifacts
were moved there from the workspace. No PostgreSQL was started.

Documentation closure is a subsequent commit; obtain its exact HEAD from Git.
Explicit staging only; protected and unrelated untracked files untouched.
**NEXT: Antonio visual review. STOP.** No ORAS/Gen7 implementation, physical writes,
Launcher parity, signing or updater work started. Completion is delivery of this
visual pass, not a substitute for the owner's aesthetic approval.
