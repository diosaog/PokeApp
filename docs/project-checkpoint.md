# PokeApp 2.0 Project Checkpoint

Checkpoint date: 2026-09-23 (Phase 8F.0 LOCAL DONE; remote gate blocked by MCP OAuth).

Base HEAD before original checkpoint documentation:
`f6d8fc179f8c9e021bdf6b4fa1e2687e2d7e8b2a`

The original commit containing this file was the functional freeze checkpoint.
Later architecture checkpoints are tracked below.

Latest architecture state:

- Fase 3 closed: dependency-free domain contracts in `app/domain/`.
- Fase 4 closed: pure domain services in `app/domain/services/`.
- Fase 5 closed: repository protocols, legacy implementations, mappers and
  in-memory fakes in `app/repositories/`.
- Fase 6 closed: Supabase V2 greenfield SQL schema in `supabase/v2/migrations`
  with reset/dev docs and static schema tests.
- Fase 6.1 closed: schema V2 executed against real PostgreSQL 17.11, including
  reset/rebuild and fixture introspection.
- Fase 7 closed: Supabase V2 RLS/security layer with identity helpers, safe
  projections, private storage policies and real PostgreSQL RLS validation.
- Fase 7.1 closed: real Supabase staging validator passed against
  `Pokeapp 2.0`.
- Fase 7.2 closed: `013_storage_policies` is Cloud-safe, idempotent and already
  applied in the real Supabase staging project.
- Fase 8A.1 closed: PIN UX to Supabase Auth identity bridge core.
- Fase 8B closed: isolated FastAPI skeleton for health, PIN login, refresh and
  `/v1/me` bearer identity lookup.
- Fase 8B-H closed: real SDK-compatible auth mapping, UUID/slug lookup and
  globally enabled mutation guard; `/v1/me` remains readable when disabled.
- Fase 8C DONE local + Supabase V2 staging validated: self-service Team Lock
  API, authoritative ParsedSave snapshots and atomic lock/activity RPC in 019.
- Runtime remains Streamlit legacy through wrappers.
- Phase 8D.0 DONE local + staging: 020 explicit same-season pointer, inclusive
  Store Ban windows, five remote check groups and cleanup PASS.
- Phase 8D normal purchase DONE local + staging: 021 atomic purchase/ledger/event,
  idempotency, promotion eligibility and wallet serialization. 29 remote checks
  (5 context + R01-R24) and cleanup PASS.
  Historical blocker resolved; [contract and evidence](phase8d-purchases.md).
- Phase 8E DONE local + staging: 022 atomic promotional purchase, wallet-before-stock
  locking, unique trainer claim and historical idempotent receipt. 27 real checks,
  29 8D regression checks and cleanup PASS. [Report](phase8e-completion-report.md).
  [Contract and validation](phase8e-promotional-purchases.md). Next:
  8F redemption/effect boundary, not implemented.
- Historical Phase 8F audit BLOCKED: all four implemented redemption effects require Pokemon
  identity; existing fingerprints collide for distinct individuals and normalized
  DTO IDs can be empty. No safe legacy target-free use flow found. No 023/API or
  staging work. [Evidence and effect map](phase8f-redemption-effects.md).
- Phase 8F.0 adds authoritative entities/observations, read-only PKHeX evidence,
  conservative reconciliation and safe legacy flag links in 023. Local validation
  and staging completion are tracked in [identity contract](phase8f0-pokemon-identity.md).
  No redemption endpoint, runtime connection, dual-write or physical save modification.
  295 tests PASS, PostgreSQL migrations/bootstrap PASS (19 identity checks each),
  schema dumps including grants identical. Staging 023 has NOT been applied by this
  task: MCP OAuth refresh failed. Do not mark 8F.0 fully DONE until remote validation.

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
- Fase 5: repositories.
- Fase 6: Supabase V2 greenfield schema.
- Fase 6.1: real Postgres validation of Supabase V2 SQL.
- Fase 7: RLS and security.
- Fase 7.1: real Supabase staging validation complete; full JWT/PostgREST/
  Storage validator passed with `RESULT ok checks=13`.
- Fase 7.2: Supabase Storage Cloud compatibility fix completed and applied.
- Fase 8A.1: PIN auth bridge core.
- Fase 8B: FastAPI skeleton, JWT verification and PIN-login rate limiting.
- Fase 8B-H: authentication hardening. DONE.
- Fase 8C: Team Lock V2 API mutation. DONE + Supabase V2 staging validated.
- Fase 8D.0: current matchday and Store Ban contract. DONE local + staging.
- Fase 8D: atomic normal purchase. DONE local + staging.
- Fase 8E: atomic promotional purchase. DONE local + staging.

Historical staging validation (Phase 7, not rerun in this task):

- `py -m compileall -q .`
- `py -m unittest discover -s tests`
- `git diff --check`
- `py tools\validate_supabase_v2_rls.py` passed against real staging with
  `RESULT ok checks=13`.

Phase 8E baseline validation: 255 tests passed, zero failed/skipped, using
`.venv-api\Scripts\python.exe tools/run_unit_tests.py`. Compileall and diff-check
passed. PostgreSQL 17.11 local passed both migrations 001-022 and bootstrap,
including Store Ban, purchase receipt, promotions, rollback, roles and concurrency.
Phase 8E adds seven multi-connection stock/wallet/idempotency race scenarios.
The runner uses disposable SQLite data, not V1. See
[Phase 8C report](phase8c-team-lock.md) for exact commands and environment.

Remote 8C: migration 019 applied incrementally to `uwleqeuzsveqlugugzba`
(`Pokeapp 2.0` staging); real Auth/PostgREST + in-process FastAPI validator passed
13 checks. Owner/admin private reads, other/public reads, backend-only writes,
replacement and dedupe passed. All temporary DB/Auth fixtures were removed.
Forced post-write rollback remains locally validated, not injected into staging.

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
- `app/auth/*`: PIN UX to Supabase Auth identity bridge and provisioning core.
- `app/api/*`: isolated FastAPI transport skeleton for Phase 8.
- `app/repositories/*`: protocols, mappers, legacy repositories and in-memory
  fakes.
- `app/application/*`: first small use cases coordinating repositories and
  domain services.
- `supabase/v2/migrations/*`: greenfield SQL-first Supabase V2 schema.
- `supabase/v2/reset_dev.sql`: destructive development/staging reset for V2 only.
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

Fase 5 wrappers currently delegate selected persistence into repositories:

- `app/entrenadores/trainer_flags.py` loads/saves trainer flags through
  `LegacyTrainerRepository`.
- `app/activity/events.py` stores ActivityEvents through
  `LegacyActivityRepository` while preserving legacy dict output.
- `app/tienda/discounts.py` reads/writes promotion scheduling through
  `LegacyShopRepository` and `LegacySettingsStore`.
- `app/interfaz/hall_of_fame.py` loads/saves entries through
  `LegacyHallOfFameRepository`.

Fase 6 adds a future persistence target but does not connect runtime:

- V2 is greenfield and reproducible from SQL.
- V1 is not patched and not deleted.
- `settings` blobs are not carried forward as source of truth.
- Core competitive data is season-scoped.
- `coin_transactions` is the future money source.
- API/React/Cloudflare remain future phases.

Fase 6.1 validates that target for real:

- PostgreSQL 17.11 portable local validation database:
  `pokeapp_v2_validation`.
- `001_core.sql` through `009_seed.sql` applied successfully.
- `reset_dev.sql` then full rebuild applied successfully.
- Real introspection confirmed 32 public V2 tables, 75 FKs and 92 indexes.
- Fixtures validated current save ownership, uniques, checks, JSONB, ledger,
  archive preservation and delete restrictions.
- `reset_dev.sql` was corrected to drop `trainer_flags` and `pokemon_flags`.

Fase 7 secures that target:

- every V2 public application table has RLS enabled;
- `trainers.auth_user_id` resolves current trainer identity;
- `trainers.is_admin` controls explicit admin permission;
- safe `public_*` and `current_*` views define client read surfaces;
- private save payloads, private team locks, purchases/redemptions and ledger
  details are owner/admin only;
- direct writes for critical flows remain server/API only;
- `raw-saves` storage policies are prepared for Supabase storage paths by
  `trainer_id`.

Fase 7.1 completed real staging validation:

- `tools/validate_supabase_v2_rls.py` validates Supabase Auth JWTs, PostgREST
  RLS and Storage policies against a real staging project.
- `.env.supabase-v2-rls.example` documents required credentials without secrets.
- Real staging project `Pokeapp 2.0` has migrations 010, 011, 012, 013, 014,
  015, 016, 017 and 018 applied through the Supabase connector.
- SQL-level checks confirmed 32 public tables, 32 RLS-enabled public tables, 82
  public policies, 37 safe views, 13 `security_invoker` views and 24 public
  definer projections.
- Storage migration 013 is now policy-only, Cloud-safe and already applied in
  staging.
- Full validator execution passed against the real staging project with
  `RESULT ok checks=13`.

Persistence:

- Supabase is the remote store when configured.
- SQLite/local files are fallback/dev.
- `settings` JSON is still heavily used for official aggregate state.
- Streamlit `session_state` is a runtime mirror, not the target architecture.

## Accepted Debt

- Many official entities still live in generic `settings` JSON.
- Streamlit UI and business rules are still coupled in several modules.
- Runtime Streamlit still uses legacy/V1 persistence; V2 is not connected yet.
- Team Lock, normal and promotional purchase are isolated V2 mutations, validated
  locally and in staging. Migrations 019-022 are applied; other critical APIs remain.
- Legacy ActivityEvents remain in settings; new V2 lock/purchase transactions
  writes V2 tables only, without dual-write or Discord delivery.
- Copa and Juicios are functional legacy islands and need contracts later.
- Parser bridge is treated as a black box but not fully isolated.
- Some legacy helper names remain, especially around wipe/revive wording.
- Visual CSS layers are acceptable for the reference app but should not be the
  long-term design system.

## Next Step

Next exact phase:

```text
Close Phase 8F.0 staging gate, then resume Phase 8F using pokemon_entity_id
```

Fase 7.1, Fase 7.2, Fase 8A.1, Fase 8B and 8B-H are closed. Fases 8C, 8D.0,
8D and 8E are DONE local + staging. Do not infer that all APIs or deployment are complete.
Do not cut over Streamlit or delete V1 without explicit approval.
The 2026-09-23 audit reproduced identity collisions without running the bridge.
The 255 baseline tests are retained alongside new identity tests. 023 is dedicated
to identity, not redemption. See the 8F.0 report for current validation counts.

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
- Fase 5: repositories. Closed.
- Fase 6: Supabase V2 greenfield schema. Closed.
- Fase 7: RLS and security. Closed.
- Fase 7.1: real Supabase staging validation complete.
- Fase 7.2: Supabase Storage compatibility fix completed and applied.
- Fase 8A.1: PIN auth bridge core. Closed.
- Fase 8B: FastAPI skeleton, JWT verification and PIN-login rate limiting.
  Closed.
- Fase 8B-H: auth hardening. Closed.
- Fase 8C: Team Lock V2 API mutation. DONE local + staging.
- Fase 8D.0 + 8D: current matchday, Store Ban and normal purchase. DONE local + staging.
- Fase 8E: promotional claim. DONE local + staging; 27 checks and 8D regression PASS.
- Fase 8F: redemption not implemented; 8F.0 identity supplies the prerequisite boundary.
- Fase 8 remaining: redemption/effects, league/season/admin/trials/Hall operations.
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
