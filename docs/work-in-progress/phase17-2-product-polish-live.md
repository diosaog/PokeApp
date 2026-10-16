# Phase 17.2 ? live execution record

Observation 2026-10-15. **STATUS: PHASE 17.2 DONE.**

## Entry and implementation

Entry was `f692ced8e63446c5943f7e467a8af4af474ecd73`, with main/origin aligned.
The final application source is `d7eb78b66861a4bddd1d79ec3eebc93c7429d1a1`,
pushed before deployment. The packet adds the approved public current-save
collection (party, boxes and dead Box 8) with a strict privacy allowlist, moves
own inventory to the trainer profile, separates disabled from pending controls,
and applies bounded visual/art polish. Team Lock remains the official historical
team; no competitive, parser, reward, migration or physical-save semantics were
changed.

## Validation and delivery

Existing final validation is retained: **53 focused Python**, **68 affected React**
and **51 unique affected browser cases**, with build, formatting, Ruff, compile,
Wrangler dry-run and animation hashes passing. No PostgreSQL run was needed because
SQL, schema, grants and migrations were unchanged.

Railway deployment `c4ed81bf-da7f-4ea5-9b20-5a8bb4344f36` is SUCCESS with image
`sha256:ac40a3ca47df3b1198f6841c411b0e8a11b1b12018152b402940d1c2ba250ff4`.
Cloudflare deployment `a132a525-70a0-4727-b4f4-85f837379cc3`, version
`33849862-0eef-40e6-b5a7-54228e8684e2`, serves 100% with the same source. The
read-only public probe passed 31 checks and the unauthenticated browser smoke
passed 10 visits at desktop/mobile widths, with no unexpected 5xx or mutation.

The private before/after capture has 59 scoped tables and 36 migrations through
044. All public/business tables, owner-stable identity/credentials, security,
private inbox and Advisor ERROR/WARN findings are unchanged. Differences are
limited to expected Auth session/refresh activity in `auth.users`,
`auth.sessions` and `auth.refresh_tokens`. No V1, Shadow, R2, Launcher or
physical-save write occurred.

## Evidence boundaries and next state

The hosted authenticated PIN journey and positive owner-season mutation were not
run because no PIN was available; local authenticated tests and public denial
checks passed. V1 and Shadow were not accessed. Evidence is in
[phase17-2-product-polish-evidence.json](../phase17-2-product-polish-evidence.json)
and the private directory `%LOCALAPPDATA%/PokeApp-migration-evidence/phase17-2/20261015`.

**NEXT: Antonio visual acceptance.** No next packet, Gen6/7 support or physical
save writes starts from this closure.

## Post-17.2 final visual delta — 2026-10-16

**STATUS: DONE.** The public read projection now exposes only the persisted
`ROBADO`, `BLINDADO` and `REVIVIDO` states. Compact coloured labels render on
team, box, dead and scouting/profile cards, including compatible combinations;
private IVs, ability, nature and identity metadata remain excluded. Box
navigation wraps from the first box to the last and back, with one-box controls
remaining inactive. Home animates only the visible six team slots and keeps the
static/reduced-motion fallback; box grids are not animated.

Source commit `a97e8de0a000d68e9b9db2da5ac8e2f8d355e40d` is pushed. Focused checks
actually run for this delta: trainer collection **10 PASS**, Vitest collection /
presentation / Team Preview **14 PASS**, affected browser **5 PASS** (including
flags, wrap and Home/reduced-motion), targeted Ruff, Prettier, compile and public
build. The existing frontend-read API **24 PASS** and Team Preview API **13 PASS**
were retained and not repeated; no unrelated matrix was rerun.

Railway deployment `927587fd-037e-44ad-b95f-7480d67be333` is SUCCESS with image
`sha256:85832f7aca8d7877ec62fd03814a0e47d9397d868dcef3a1141238f0508f97c2`.
Cloudflare deployment `0c00e78f-843c-4a24-9823-a59f81f14654`, version
`57aeb7d6-1850-4f0f-a635-f2610262a405`, serves 100%. The read-only smoke passed
**31 HTTP checks** and **10 desktop/mobile browser visits** after deployment;
API health returned 200 and no unexpected 5xx or owner mutation occurred.

No migration, PostgreSQL run, V1/Shadow/R2/Launcher operation or physical save
write was performed. The final documentation commit records this delta; the
protected guide and unrelated untracked files remain untouched. **NEXT: Antonio
visual acceptance. STOP.**
