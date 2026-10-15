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
