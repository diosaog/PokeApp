# UX, Showdown export, Team Lock pastes and player-managed matchdays — live record

Branch `claude/ux-showdown-matchdays`, from `be7d73c` (`claude/api-session-isolation`).
**PUBLISHED 2026-11-04 (~00:26 UTC) after explicit owner approval.**

| Layer | Live state |
|---|---|
| Supabase | 001-078; 078 = `20261104002034`, applied once by `tools.phase30_apply_migrations` |
| Backup | `pre-release-20261104T001816Z` (SHA-256 `4243088b…`), 123 tables; rehearsal 17/17 PASS (private folder `PokeApp-migration-evidence/ux-showdown-078`) |
| Railway API | `554bf854` (source `0c4678c`, flag `POKEAPP_PUBLIC_TEAM_PASTES_ENABLED=true`); `0766967e` was the same image before the flag; previous release `3cd6aebb` |
| Cloudflare web | `0b061103-05b7-4b69-aad0-21db084506d8`; previous `053e50cf` |
| Launcher | unchanged, stable 0.26.11 (min 0.26.0): it loads the new web |
| Checks | health 200; 128 OpenAPI paths (only decimal `pattern` annotations differ from a local build: unpinned pydantic); anonymous and bad bearer 401 on the new routes; CORS preflight OK; refresh 422; feed signed 0.26.11 |

## Owner decisions (2026-11-03, final)

- Public Pokepast.es paste of a confirmed Team Lock: only what PokeApp already
  shows everyone — species/form, nickname, gender, level, held item, moves,
  shiny. Never ability, nature, IVs, EVs or a Hidden Power type.
- Private «Generar Poképaste»: the displayed current party, everything
  including ability and real IVs; every EV exported as exactly 1.
- One synthetic live paste was authorized and created:
  `https://pokepast.es/7a00cfd5f754cb45` (six invented Pokémon, no trainer).

## Implemented (commits on the branch)

| Block | Commit | Summary |
|---|---|---|
| Points + microcopy | `1943da3` | `web/src/points.ts`: exact decimal text, no float, no `-0`, unknown `—`; home pill fixed; small redundant texts removed |
| «Mi perfil» dialog | `65e4c6a` | sidebar button opens Perfil/Seguridad/Preferencias; unsaved-input guard; trainer page loses inline settings |
| Wipe stepper | `a7b2105` | − value + Actualizar under the licence card; same API/revision; removed from Liga |
| League | `661fd44` | open below standings, close at the end of each J tab; no authority widened (SQL since 041/034); `tools/validate_player_matchdays.py` |
| Showdown export | `7b696cd` | server serializer + name table; `GET /v1/me/pc/showdown`, `GET /v1/read/seasons/{id}/pc/showdown`; payload keeps gender/form |
| Team Lock pastes | `4da598c`, `c99a4d3` | migration 078; `app/application/pokepaste.py`; outbox dispatcher creates/reuses the link; flag `POKEAPP_PUBLIC_TEAM_PASTES_ENABLED`; a link problem never blocks the announcement |
| Hardening / specs | `aa17884`, `94b7e60`, `d234202` | pre-078 private snapshots (`gender: ""`) stay readable; browser specs aligned; formatting |

## Verification (2026-11-04, branch tip)

- Python: 122 tracked modules, **1465 tests OK**.
- Web: `tsc -b` clean; Vitest **42 files / 353 tests** pass. Node: **70/70**.
- SQL (disposable PG17, 001-078): `validate_player_matchdays` PASS,
  `validate_phase078_public_pastes` PASS, `validate_phase077_trainers --upto 78` PASS.
- Showdown export of a public Pokémon Y fixture party equals PKHeX's own
  ShowdownSet except the EV line (owner rule).
- Playwright: **69 passed / 50 failed / 11 skipped**; the untouched base
  `be7d73c` gives 59 / 60 / 11. No new failure; 10 fixed. The 50 remaining
  fail identically at base (stale specs, e.g. a removed «Mi PC» link and
  duplicated «Cambio confirmado.» locators) and are outside this work.

## Release prerequisites

1. Migration **078** (`078_team_lock_public_pastes.sql`): additive columns and
   checks on `discord_announcements`; no data change. Apply before enabling
   the flag. The API selects the new columns only when the flag is `true`, so
   deploying the API before 078 is safe while the flag is off.
2. API: OpenAPI paths **126 → 128**; update the pinned hosted check.
3. Web: Cloudflare deploy (new dialog, League layout, export button).
4. Launcher: no change (it hosts the web; no new IPC).
5. After smoke checks, set `POKEAPP_PUBLIC_TEAM_PASTES_ENABLED=true` on the
   Railway API service (Railway redeploys). Unset it to switch pastes off.

## Rollback

- Web: previous Cloudflare version (`053e50cf`).
- API: previous Railway deployment (`3cd6aebb`); or only unset the flag.
- 078 needs no rollback (unused columns are inert); dropping them is optional.

## Known limitations

- Gender (all games) and form (X/Y) only exist in save projections stored
  after this release; older ones export without them and say so.
- Friendship is not read by the parser: Showdown keeps its default.
- Items unknown to Showdown (Everstone…) are left out of the private import
  with a warning; the public paste shows their real English name.
- Pokepast.es has no idempotency key: a lost answer may, at most twice per
  Team Lock revision, create an extra unreferenced paste.
