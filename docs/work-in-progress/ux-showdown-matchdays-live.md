# UX, Showdown export, Team Lock pastes and player-managed matchdays — live record

Branch `claude/ux-showdown-matchdays`, from `be7d73c` (`claude/api-session-isolation`).
**Local only. Nothing published. Production changes need explicit owner approval.**

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
| Team Lock pastes | (this block) | migration 078; `app/application/pokepaste.py`; outbox dispatcher creates/reuses the link; flag `POKEAPP_PUBLIC_TEAM_PASTES_ENABLED` |

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
