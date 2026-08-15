# PokeApp 2.0 Project Checkpoint

Checkpoint date: 2026-08-15

Base HEAD before original checkpoint documentation:
`f6d8fc179f8c9e021bdf6b4fa1e2687e2d7e8b2a`

The original commit containing this file was the functional freeze checkpoint.
Later architecture checkpoints are tracked below.

Latest architecture state:

- Fase 3 closed: dependency-free domain contracts in `app/domain/`.
- Fase 4 closed: pure domain services in `app/domain/services/`.
- Runtime remains Streamlit legacy through wrappers.
- Next exact phase: Fase 5 - repositories.

## Current State

PokeApp 2.0 has reached functional freeze.

Closed phases:

- Fase 0: base green, initial docs and module inventory.
- Fase 1: visual Streamlit reference mostly closed.
- Fase 2.1: immutable round snapshots and critical permissions.
- Fase 2.2: definitive configurable season for Streamlit A/B.
- Fase 2.3: TrainerStatus/TrainerFlags and Admin centralization.
- Fase 2.4: season lifecycle, SeasonArchive and stable Hall of Fame.
- Fase 2.5: ActivityEvents and NotificationView.
- Fase 2.6: final audit, backlog, checkpoint and functional freeze.
- Fase 3: domain contracts.
- Fase 4: pure domain services.

Validation at this checkpoint:

- `py -m compileall -q .`
- `py -m unittest discover -s tests`
- `git diff --check`

Verified current suite after Fase 4: 94 tests.

## What Works

- Trainers log in with a PIN and see their own private data.
- Saves can be uploaded, selected and parsed through the current bridge.
- Entrenadores shows current team, PC/boxes, Pokemon detail, inventory and own
  team lock controls.
- Team Preview uses fixed teams when available and respects private/public data.
- Liga A/B works with configurable players, jornada count, division sizes,
  movement count, points and coins.
- Closed jornadas freeze official standings, points, coins and penalty metadata
  through round snapshots.
- TrainerStatus supports active, retired, abandoned and disqualified states.
- TrainerFlags tracks robbed state separately from competitive status.
- Tienda supports catalog, purchases, redemptions, promotions and stock.
- Team locks are stored per jornada and can be late.
- ActivityEvents feed concise notifications for saves, purchases and team locks.
- Season lifecycle can finish, archive, prepare new active season or discard.
- SeasonArchive freezes final season data and public champion team.
- Hall of Fame prefers archived entries, so final winners do not drift after
  archive.
- Copa works as separate legacy tournament flows.
- Juicios works as separate case/penalty flow.
- `Temporada/Admin` is the central back office for official season/Liga/admin
  state.

## Current Architecture

PokeApp is still a Streamlit app.

Entry:

- `main.py`

Important layers:

- `app/domain/*`: dependency-free contracts.
- `app/domain/services/*`: pure business decisions.
- `storage.py`: Supabase/SQLite/settings facade.
- `utils.py`: roster/session/save helpers and static user registry.
- `app/liga/*`: ranking, state, snapshots, rewards, divisions and UI.
- `app/season/*`: config, validation, lifecycle and archives.
- `app/entrenadores/*`: trainer page, boxes, snapshots, flags and inventory.
- `app/tienda/*`: catalog, promotions, purchase/redeem and money.
- `app/copa/*`: cup modes.
- `app/juicios/*`: cases, forms, repo, penalties and rendering.
- `app/interfaz/*`: shell, theme, home, notifications, normativa, admin and Hall.
- `app/activity/events.py`: ActivityEvent legacy store.

Fase 4 wrappers currently delegate selected logic into domain services:

- ranking helpers and points-with-penalties;
- division movements;
- shop promotion selection/pricing/state;
- trainer status and robbed flag mutations.

Persistence:

- Supabase is the remote store when configured.
- SQLite/local files are fallback/dev.
- `settings` JSON is still heavily used for official aggregate state.
- Streamlit `session_state` is a runtime mirror, not the target architecture.

## Accepted Debt

- Many official entities still live in generic `settings` JSON.
- Streamlit UI and business rules are still coupled in several modules.
- Supabase schema is V1 and not yet normalized by `season_id`.
- RLS/API is not the final security model yet.
- ActivityEvents are stored in settings, not an append-only table.
- Copa and Juicios are functional legacy islands and need contracts later.
- Parser bridge is treated as a black box but not fully isolated.
- Some legacy helper names remain, especially around wipe/revive wording.
- Visual CSS layers are acceptable for the reference app but should not be the
  long-term design system.

## Next Step

Next exact phase:

```text
Fase 5 - Repositories
```

Do not code SQL, API or React in Fase 5. First define repository interfaces and
application orchestration boundaries around the domain services.

## Do Not Do When Resuming

- Do not keep polishing Streamlit without a real bug.
- Do not add new mechanics.
- Do not start React before Fases 3-9.
- Do not migrate the database before the Supabase V2 schema exists.
- Do not add SQL patches ad hoc for new mechanics.
- Do not remove Streamlit until shadow mode and cutover are complete.
- Do not implement N divisions inside the old Streamlit A/B state.
- Do not send Discord announcements for hidden migration work.

## Remaining Planning

- Fase 3: domain contracts. Closed.
- Fase 4: pure domain extraction. Closed.
- Fase 5: repositories. Next.
- Fase 6: Supabase V2 design.
- Fase 7: RLS and security.
- Fase 8: API for critical operations.
- Fase 9: parser boundary.
- Fase 10: React / Cloudflare frontend.
- Fase 11: data migration.
- Fase 12: shadow mode.
- Fase 13: staging with cloned data.
- Fase 14: performance measurement.
- Fase 15: cutover.

## Technical Handover Summary

PokeApp is a competitive Pokemon league manager for a small private league. It
combines save uploads/parsing, trainer profiles, PC/boxes, team locks, Team
Preview, Liga A/B standings, shop economy, redemptions, Copa, Juicios, Hall of
Fame, Discord-adjacent notifications and an Anto-only admin back office.

The current app is valuable because the product behavior is now defined and
tested enough. The next risk is not product uncertainty; it is architecture.
The app should not be rewritten blindly. It should be migrated by extracting the
domain concepts that already exist and proving equivalence with tests.

The most important official historical protection is the round snapshot system:
once a jornada closes, standings/rewards/penalties are read from the snapshot.
The most important season-level protection is SeasonArchive: once archived, the
Hall of Fame should use archived data and public champion team snapshots instead
of mutable live saves.

The current weakest technical point is the broad use of `settings` JSON. That is
acceptable for Streamlit 2.0, but it must become explicit contracts, repositories
and Supabase V2 tables before React/Cloudflare becomes the main app.
