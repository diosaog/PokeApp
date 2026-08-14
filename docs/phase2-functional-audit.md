# PokeApp 2.0 Phase 2 Functional Audit

Audit date: 2026-08-14

Scope: functional audit only. No runtime behavior, rules, data, Supabase schema,
Discord behavior, scoring or UI flow was changed by this document.

## 2.3 Update - Trainer Status And Admin Centralization

Update date: 2026-08-15

Principle adopted:

- Normal pages show and let trainers use PokeApp.
- `Temporada/Admin` changes official PokeApp state.

### Admin Control Inventory

| Page | Controls found | Classification | 2.3 outcome |
| --- | --- | --- | --- |
| Entrenadores | Mark abandonment/retirement | Official admin mutation | Moved to `Temporada/Admin > Entrenadores`. |
| Entrenadores | Team lock, bridge load, inventory use | Normal trainer actions | Kept in Entrenadores. |
| Saves | Global `Reset / Wipe` | Danger/admin | Removed from Saves and moved conceptually to `Temporada/Admin > Riesgo`. |
| Saves | Upload, set current, history, download | Normal save actions | Kept in Saves. |
| Liga | Open jornada, close jornada, cancel, edit previous round, divisions, reset Liga | Official competition/admin mutations | Render only with `admin_mode=True`, reached from `Temporada/Admin > Competicion`. |
| Liga | Refresh, standings, divisions, history, podium | Consultation/competition view | Kept in Liga normal. |
| Temporada/Admin | Season config editor | Official admin mutation | Kept and organized under Configuracion. |
| Temporada/Admin | Trainer status changes | Official admin mutation | Added under Gestion de entrenadores. |
| Temporada/Admin | Pokemon flag maintenance | Danger/admin maintenance | Added under Zona de riesgo. |
| Temporada/Admin | Discard active season | Danger/admin | Added with explicit decision and textual confirmation. |
| Tienda | Purchase, confirm purchase, redemption flows | Normal trainer/shop actions | Kept in Tienda. |
| Tienda | Reset Pokemon flags | Danger/admin maintenance | Removed from normal Tienda page and moved to Admin. |
| Copa | Create/reset/advance cup rounds | Competition-specific official mutations | Kept for now because Copa is separate from Liga and out of scope for this mini-phase. Future Admin unification should revisit it. |
| Juicios | Start/edit/vote/finish/cancel cases | Domain workflow mutations | Kept in Juicios because sanctions have their own flow. Future Admin/API should harden permissions. |
| Hall of Fame | Auto-sync historical display | Derived historical view | Not touched in 2.3. |

### TrainerStatus

`app/entrenadores/trainer_flags.py` now formalizes:

- `active`: can participate normally.
- `retired`: administrative retirement; old results remain, future active systems ignore the trainer.
- `abandoned`: abandonment of the active season; same competitive effect as retired, but historically distinct.
- `disqualified`: administrative inactive state, implemented with the same inactive effect because it is low-risk and useful for Admin.

Existing code still calls `is_trainer_retired()` in many places. In 2.3 that
function is kept as compatibility and means "inactive trainer" internally.

Inactive effects:

- Ranking: active players rank normally; inactive players are appended at the bottom with `0.0`.
- Points/coins: inactive users do not receive active league rewards.
- Divisions: inactive users are excluded from sanitized active divisions.
- Team Preview: active roster sources exclude inactive trainers where season roster is used.
- Tienda: inactive users cannot use active shop/comodin flows.
- Saves: inactive users can consult but not upload as active competitors.
- History: previous closed snapshots remain stored and are not rewritten.

No reactivation button was added because current product rules treat these states
as permanent.

### TrainerFlags

`robbed` remains a flag, not a status.

- It can coexist only with active trainers.
- It is cleared when a trainer becomes inactive.
- Historical redemption sync still seeds robbed flags, skipping inactive trainers.
- Robbed-cycle reset still works against active trainers.

### Admin Back Office

`Temporada/Admin` now has these areas:

- Estado
- Configuracion
- Entrenadores
- Competicion
- Historial
- Riesgo

The Liga console is loaded from Admin with `page_tabla(admin_mode=True)`.
The normal Liga page does not render official controls.

### Wipe / Reset

The old Saves wipe is no longer exposed there. The current safe model is:

- "Guardar en historial": visible but blocked until a complete archive flow exists.
- "Descartar temporada": allowed only for Anto, requires explicit decision and
  typing `DESCARTAR`, then calls the legacy wipe function.

This prepares the desired lifecycle:

```text
ACTIVE -> FINISHED -> ARCHIVED -> nueva DRAFT/ACTIVE
```

No `season_id` or archive tables were added in 2.3.

### Historial vs Hall Of Fame

- Historial de temporadas: future complete technical archive of one season.
- Hall of Fame: prestige/summary view of champions and achievements.

Hall may derive from season archives later, but it is not the archive itself.

### Snapshot Rule

Closed round snapshots now keep trainer status metadata inside penalty/status data.
Changing a trainer status later does not rewrite an already closed jornada.

## Executive Summary

Phase 2 is partially implemented, but it is not feature-freeze ready yet.

The strongest pieces already in place are:

- `season_config_v2` as a versioned JSON setting with `effective_round`.
- A real Anto-only season editor in `app/interfaz/temporada.py`.
- Dynamic league rewards through `app/liga/rewards.py`.
- Trainer status/flags for inactive trainers and `robbed`.
- Team locks, shop discounts and purchases in dedicated tables.
- Hall of Fame auto-sync from Liga and Copa sources.
- Recent notifications derived from saves, purchases and team locks.

The largest gaps before Phase 2 can close are:

- Historic league results are not immutable enough. Positions are stored, but
  points/coins/config snapshots are not.
- The league implementation is still hard-wired to two divisions, A and B.
- Phase 2.3 moved the highest-risk admin controls into `Temporada/Admin`; Copa
  and Juicios still keep their domain workflows in-place until a later pass.
- `abandono` is now a distinct TrainerStatus (`abandoned`) with the same current
  competitive effect as retired.
- Hall of Fame entries are automatic-ish, but their team snapshot can drift
  because it reads the current trainer snapshot instead of the locked/final team.
- Notifications are not first-class `ActivityEvent` rows; they are derived views.
- SQLite is a fallback/dev store, not an official synchronized replica.

## 2A - Current Season Configuration

### Storage

The active season configuration is stored as JSON in:

- Source: `settings`
- Key: `season_config_v2`
- Access layer: `storage.settings_get()` / `storage.settings_set()`
- Module: `app/season/config.py`

When the key is missing or invalid, the app builds a default document from
`utils.USERS`.

### Real Shape Of `season_config_v2`

Current document shape:

```json
{
  "schema_version": 1,
  "active_version_id": "default",
  "versions": [
    {
      "id": "default",
      "name": "Temporada actual",
      "effective_round": 1,
      "max_rounds": 4,
      "players": ["Anto", "Victor"],
      "division_count": 2,
      "division_sizes": [5, 5],
      "movement_count": 3,
      "points_by_position": {
        "1": 9,
        "2": 8
      },
      "coins_by_position": {
        "1": 15,
        "2": 14
      },
      "rules": {
        "team_lock_required": true,
        "last_b_gets_steal": true,
        "cup_is_separate": true
      }
    }
  ]
}
```

The real default includes all 10 positions:

- Points: `1=9, 2=8, 3=7, 4=6, 5=5, 6=5, 7=4, 8=3, 9=2, 10=1`
- Coins: `1=15, 2=14, 3=12, 4=11, 5=10, 6=11, 7=9, 8=8, 9=6, 10=4`

### Field Usage

| Field | Used today | Notes |
| --- | --- | --- |
| `schema_version` | Partly | Always coerced to `1`; no migration logic yet. |
| `active_version_id` | Yes | Used when no round is passed. |
| `versions` | Yes | Sorted by `effective_round`, then `id`. |
| `id` | Yes | Used for active version and Hall source id. |
| `name` | Yes | Shown in UI and Hall entries. |
| `effective_round` | Yes | Chooses config for a requested round. |
| `max_rounds` | Yes | Used by `max_jornadas()` / final league detection. |
| `players` | Yes | Filters `utils.USERS`; cannot create fully new trainers alone. |
| `division_count` | Yes/blocked | Streamlit 2.0 officially supports `2`; other values are rejected. |
| `division_sizes` | Yes | First size drives Liga A and second size drives Liga B. |
| `movement_count` | Yes | Used for A/B ascents and descents. |
| `points_by_position` | Yes | Used dynamically by rewards. |
| `coins_by_position` | Yes | Used dynamically by rewards. |
| `rules` | Partly functional | `team_lock_required` and `last_b_gets_steal` affect behavior; `cup_is_separate` is metadata. |

### Hardcoded Values Still Present

- `utils.USERS` remains the real trainer registry and credentials source.
- `SECTIONS` is static in `utils.py`.
- Liga supports `A` and `B` only in `league_state`, UI, ranking and history.
  This is now an explicit 2.2 product decision, not hidden configurability.
- `app/interfaz/temporada.py` disables `division_count` and forces `2` because
  N divisions are deferred to the domain/API phase.
- Last Liga B reward `Robar Pokemon` now depends on
  `rules["last_b_gets_steal"]`.
- Team lock requirement is notification-based, not a hard blocker.
- Static aliases remain: `MAX_JORNADAS`, `CURRENT_POINTS_BY_POSITION`,
  `CURRENT_COINS_BY_POSITION`; they now mirror defaults but can mislead future work.

### Versioning

`save_season_version()` appends a new version and sets it active. The function is
admin-only and rejects versions that would start on closed jornadas or the
current open jornada.

`season_version_for_round(document, round_no)` selects the latest version whose
`effective_round <= round_no`. This is the correct base for future immutability,
but it is not enough by itself because league results do not store the applied
version/snapshot.

## 2B - Real Season And Matchday Flow

### Current Flow

1. Login selects a trainer from static `USERS`, sorted with retired users last.
2. `Temporada` is visible only for Anto via `sections_for_user()` and checked
   again inside `render_temporada()`.
3. Anto can save a new season config version to `settings.season_config_v2`.
4. Liga state is restored from `settings.league_state` using strict Supabase mode.
5. `ensure_state()` initializes missing league data from active users.
6. Divisions can be manually adjusted from `Temporada/Admin > Competicion`.
7. A jornada is opened with `Editar jornada` from the Admin Liga console.
8. Opening a jornada creates round-robin pairings for current A/B divisions.
9. Opening a jornada triggers one missing team-lock Discord warning per round.
10. Trainers can lock their own current 6 Pokemon from `Entrenadores`.
11. Results are saved in `st.session_state.league_matches`, then persisted.
12. Closing a jornada ranks A/B, stores positions in `league_results`, gives last
    Liga B `Robar Pokemon`, applies movement, schedules shop promotions and sends
    Discord summary if enabled.
13. The league advances by incrementing `league_tramo`.
14. If `tramo > max_jornadas`, the league is treated as finalized.
15. Hall of Fame sync is called silently when final league/cup states exist.

### Manual Actions

- Configure season version.
- Adjust divisions from Admin.
- Open jornada from Admin.
- Mark winners from Admin.
- Save results from Admin.
- Finalize jornada from Admin.
- Edit previous jornada from Admin.
- Reset Liga from Admin.
- Mark trainer retired/abandoned/disqualified from Admin.
- Upload saves.
- Lock team.

### Automatic Actions

- Generate pairings for A/B.
- Rank players in each division.
- Apply ascents/descents.
- Give last Liga B a free `Robar Pokemon`.
- Schedule shop discounts after closing a non-final round.
- Expire old shop discounts when closing a round.
- Send Discord summaries if enabled.
- Sync Hall of Fame entries when final states are detected.
- Sync historical robbed trainer flags from redemptions.

### Persisted Data

- `league_state` in `settings`: active tramo, divisions, matches, results,
  movements.
- `season_config_v2` in `settings`: versioned config.
- `team_locks`: fixed teams by jornada/user.
- `purchases`: bought items and rewards.
- `shop_discounts`: promotions.
- `redemptions`: item usage events.
- `trainer_flags` in `settings`: trainer status plus robbed flag.
- `hall_of_fame_v1` in `settings`: historical entries.
- `saves`: save metadata; bytes in Supabase Storage or local files.

## 2C - Immutable History Risks

Current history is version-aware, but not immutable enough.

### What Is Safe Today

- Adding a new `SeasonVersion` with a future/current `effective_round` generally
  keeps earlier rounds interpreted by earlier versions.
- `points_for_position(round_no, pos)` and `coins_for_position(round_no, pos)`
  receive the round number.
- `movement_count(..., round_no)` and `division_a_size(..., round_no)` receive the
  round number.

### Retrospective Risk Points

- `league_results` stores only `user -> round -> position`. It does not store
  points, coins, version id, division sizes or movement count used at close time.
- If the JSON for an old version is edited directly in `settings`, old points and
  coins recalculate with the new values.
- If a version with `effective_round` in the past is inserted manually, old rounds
  can be reinterpreted.
- History rendering recalculates division split/movement from current helpers.
- `state._sanitize_results()` can shift positions when players disappear from the
  roster for a given round.
- Retired players are kept in stored results but points/coins return `0` because
  active-user checks happen before scoring.
- Hall of Fame Liga entries use computed final podium, not an immutable standings
  snapshot.
- Cup Hall entries read current cup state; team snapshots are fetched from current
  trainer snapshots, not from a final locked team.

### Proposal Without Supabase V2

Before adding new tables, add immutable snapshots inside the existing
`league_state` JSON:

```json
{
  "round_snapshots": {
    "1": {
      "version_id": "default",
      "config": {
        "points_by_position": {"1": 9},
        "coins_by_position": {"1": 15},
        "division_sizes": [5, 5],
        "movement_count": 3,
        "rules": {}
      },
      "standings": [
        {
          "user": "Anto",
          "division": "A",
          "position": 1,
          "points_awarded": 9,
          "coins_awarded": 15
        }
      ],
      "closed_at": 1780000000
    }
  }
}
```

Then:

- On close jornada, persist `round_snapshots[tramo]`.
- Points/coins totals should prefer snapshot awards over dynamic config.
- History should prefer snapshot division sizes/movements.
- Recompute previous round should intentionally replace that round snapshot.
- Config versions can remain in `settings` until Supabase V2, but old rounds stop
  depending on mutable config reads.

## 2D - Anto Admin Panel

### Existing Anto-Only Controls

- `Temporada` section hidden from non-Anto and guarded in render.
- Season config editor:
  - name
  - effective round
  - max rounds
  - division sizes
  - movement count
  - players
  - points by position
  - coins by position
  - preview validation
  - version history
  - raw active version JSON
- `Entrenadores` abandonment/retirement expander:
  - only Anto
  - disabled while league is active
  - requires typing `RETIRAR`
- `Saves` wipe panel:
  - only Anto
  - requires typing `WIPE`
  - wipes app data and caches.

### Admin-Grade Controls Not Fully Restricted

Before 2.3, these Liga controls were visible in the normal Liga page:

- open/edit jornada
- finalize jornada
- cancel jornada
- edit previous jornada
- save divisions
- reset Liga

In 2.3 they render only through `page_tabla(admin_mode=True)`, which is opened
from `Temporada/Admin > Competicion`. Backend functions such as `finalize()` and
`recompute_round()` already require Anto.

### Missing Or Partial Admin Goals

- There is no explicit `start season` state separate from editing version/division
  and creating `league_state`.
- There is no formal `finish season` action beyond `tramo > max_rounds`.
- `division_count` is not actually configurable beyond 2.
- Adding new trainer names in season config does not create credentials, portrait
  assets or trainer registry entries.
- `rules` are editable in Admin config; current functional rules are
  `team_lock_required` and `last_b_gets_steal`.
- No Discord notification is attached to season config changes yet.

## 2E - Trainer States

### Status Model

Storage:

- `settings.trainer_flags`
- Shape per trainer includes `status`, `inactive_reason`, legacy `retired`, and
  optional audit fields such as `inactive_at`, `inactive_by`, `abandoned_at` or
  `disqualified_at`.
- Module: `app/entrenadores/trainer_flags.py`

Statuses:

- `active`
- `retired`
- `abandoned`
- `disqualified`

Activation:

- UI: `Temporada/Admin -> Entrenadores`
- Only Anto can access it.
- Disabled while a league round is active to avoid mutating the open round.

Effects:

- `active_users()` excludes inactive trainers.
- Liga divisions are sanitized without inactive trainers.
- Ranking appends inactive users at the bottom with `0.0`.
- `points_from_league()` and `coins_from_league()` return 0 for inactive users.
- Money breakdown returns 0 and `store_blocked=True`.
- Saves upload is disabled for inactive users.
- Redeem/comodin flow is blocked for inactive users.
- League page is read-only for an inactive logged-in user.

Visuals:

- Sidebar status shows `Consulta`.
- Liga/table can show the specific inactive badge.
- Entrenadores profile shows the specific inactive status.
- Saves summary says consultation mode.

Reversibility:

- No UI exists to reactivate.
- Current product rules treat inactive statuses as permanent.

Risk:

- Old results remain in `league_results`. Closed snapshots now keep status
  metadata and awards, so historical closed jornadas are not rewritten by later
  status changes.

### Robbed

Meaning:

- A trainer-level cycle flag saying this trainer has already been robbed in the
  current robbery cycle. It prevents repeated trainer targets until all active
  trainers have been robbed.

Storage:

- `settings.trainer_flags`
- Fields include `robbed`, `robbed_at`, `robbed_by`, `robbed_source`, optional
  seed/note fields.

How It Is Obtained:

- Live: using `Robar Pokemon` in `app/tienda/redeem.py`.
- Historical sync: reads `redemptions` where payload type is `steal` or item is
  `Robar Pokemon`.

Pokemon/Data Effects:

- The selected Pokemon can get `pokemon_flags` with `robado`, `robado_from`,
  `robado_at` and `blindado`.
- The victim trainer gets the trainer-level `robbed` flag.
- The robber receives a free `Comodin de Blindaje por Robo`.

Consequences:

- A robbed trainer is excluded from future robbery targets while the cycle is
  active.
- Liga/table can show a `Robado` badge.
- Entrenadores intentionally does not show `Robado` in the trainer selector/header
  via `format_trainer_with_flags()`; that function only appends `Retirado`.

Cleanup:

- `reset_robbed_cycle_if_complete(active_trainers)` clears all active trainer
  robbed flags when every active trainer has been robbed.
- It sets `trainer_robbed_history_watermark` to avoid historical redemptions
  re-triggering old cycle flags.
- Making a trainer inactive removes robbed metadata from that trainer.

Dependencies:

- `redemptions`
- `purchases`
- `pokemon_flags`
- `trainer_flags`
- `active_users()`

### Abandono

`abandono` is now `status="abandoned"`.

It shares the same current competitive effect as retired, but remains
historically distinguishable in `trainer_flags` and snapshots.

## 2F - Hall Of Fame

Storage:

- `settings.hall_of_fame_v1`
- Module: `app/interfaz/hall_of_fame.py`

Entry shape:

- `id`
- `competition`
- `title`
- `season`
- `champion`
- `runner_up`
- `team`
- `notes`
- `created_at`

Creation:

- `sync_hall_of_fame_from_sources()` loads saved entries, creates automatic
  entries from current final sources, merges by id, and writes back if changed.

Automatic Sources:

- Liga: final podium once final round is closed.
- Copa Swiss: `settings.copa_swiss_state.topcut.champion`.
- Copa Eliminatoria: `settings.copa_elim_state.rounds[-1][0].winner`.
- Copa Dobles: `settings.copa_dobles_state.final` with valid BO3 score.

Idempotency:

- Merge is by entry `id`.
- Existing `created_at` is preserved when an automatic entry updates.
- Cup states use `hall_run_id` when available, otherwise a stable digest.

Current Gaps:

- Team is obtained from current trainer snapshot, not necessarily from the final
  locked team or exact save used in the competition.
- There is no dedicated `season_id`.
- Liga entry is derived from dynamic final podium, so it depends on current
  scoring calculations unless standings are snapshotted.
- `source` is encoded in `id`, not stored as a structured field.

Conclusion:

- Hall of Fame is more than manual now, but not fully immutable.

## 2G - Notifications And Activity Events

Current module:

- `app/interfaz/notifications.py`

Current UI behavior:

- `collect_notifications(..., limit=5)` returns max 5 recent useful items.
- Sources are:
  - `list_team_locks(jornada)`
  - `list_purchases(limit)`
  - `list_saves(limit)`
- Purchases with price `<= 0` are ignored.
- Empty state returns one `ok` item.

Event vs Notification today:

| Concept | Current state |
| --- | --- |
| Event | Not a first-class model. It is inferred from existing tables. |
| Notification | Derived, sorted, capped list built for UI rendering. |

Missing future event sources:

- trainer retired
- trainer robbed
- round opened
- round closed
- season config changed
- shop promotions announced
- penalties/trials changed

Recommended future direction:

- Add an `ActivityEvent` domain concept before Supabase V2.
- Initially keep it as a wrapper or append-only JSON/table, then migrate to table.
- UI notifications should read ActivityEvent, not each feature table separately.

## 2H - Current Source Of Truth By Area

| Area | Source of truth today | Ambiguity |
| --- | --- | --- |
| Trainer registry | `utils.USERS` | Season config can list players but only known users survive. |
| Login/PIN | `utils.USERS` + `settings.pin:*` | No trainer table yet. |
| Current section | `st.session_state` | Pure UI state. |
| Season config | `settings.season_config_v2` | No season id/status. |
| League official state | `settings.league_state` mirrored in `st.session_state` | Session can be stale; strict Supabase mitigates some risk. |
| Matches/results | `league_state` JSON + `round_snapshots` | Legacy paths still exist, but closed jornadas prefer snapshots. |
| Points/coins from league | Snapshot-first, dynamic fallback for open/legacy rounds | Manual DB edits can still bypass app guards. |
| Money available | Derived from league coins + badges + bonuses - purchases - penalties | Depends on snapshots/saves and purchases. |
| Purchases | `purchases` table | Supabase primary, SQLite fallback. |
| Redemptions | `redemptions` table | Used as event history for robberies/revives. |
| Pokemon flags | `pokemon_flags` table | Fingerprint stability matters. |
| Trainer status/flags | `settings.trainer_flags` | Should become entity/table later. |
| Team locks | `team_locks` table | Good candidate for V2 with `season_id`. |
| Saves metadata | `saves` table | Bytes are in Supabase Storage/local files. |
| Save parsed snapshots | `settings.trainer_snapshot:*` | Derived cache, not official source. |
| Shop promotions | `shop_discounts` table | Good candidate for V2 with `season_id`. |
| Hall of Fame | `settings.hall_of_fame_v1` | Auto-derived, but not fully immutable. |
| Notifications | Derived from tables | No persistent activity log. |
| Discard season | `app.admin.actions.discard_active_season()` -> legacy wipe | Gated in Admin but not season-scoped yet. |

## 2I - SQLite

SQLite exists in `storage.py` as local fallback/development persistence:

- DB path: `data/app.db`
- Created only when Supabase is not configured in `init_storage()`.
- Tables: `saves`, `settings`, `purchases`, `shop_discounts`, `team_locks`,
  `redemptions`, `pokemon_flags`.

Important behavior:

- If Supabase is configured, most write functions try Supabase first.
- Some strict operations, notably `league_state`, use `strict_remote=True` and
  intentionally do not fall back silently.
- Some read functions may fall back to SQLite if Supabase errors and strict mode is
  not used.
- There is no synchronization between Supabase and SQLite.
- If both contain data, Supabase usually wins while configured, but fallback reads
  can hide remote failures in non-critical paths.

Conclusion:

- SQLite must not be treated as production truth.
- Before Cloudflare/API, repository boundaries should make fallback behavior
  explicit and testable.

## 2J - Tests

Current test files:

- `tests/test_season_config.py`
- `tests/test_season_validation.py`
- `tests/test_liga_rewards.py`
- `tests/test_shop_promotions.py`
- `tests/test_notifications.py`
- `tests/test_hall_of_fame.py`
- `tests/test_saves_support.py`

Current coverage:

- Season version selection by `effective_round`.
- Season config validation for players/divisions/rewards.
- Default rewards and current A/B movement.
- Shop promotion quotas, exclusions and rotation.
- Notification limit/escaping/basic activity.
- Hall of Fame coercion, merge and BO3 validation.
- Saves summary retired mode.

Tests missing for Phase 2 close:

- Closing a jornada writes a complete immutable round snapshot. Covered in 2.1.
- Points/coins use stored round snapshots after config changes. Covered in 2.1/2.2.
- Editing previous round intentionally replaces only that round snapshot. Covered in 2.1.
- Division movement uses historical/configured movement count. Covered in 2.2.
- `division_count > 2` is blocked explicitly. Covered in 2.2.
- Liga controls require Anto where intended. Covered in 2.1/2.2.
- Retired trainer:
  - excluded from future rounds
  - old snapshot points remain visible if that becomes the rule
  - cannot purchase/redeem/upload/lock team
- Robbed trainer:
  - cannot be robbed twice in a cycle
  - cycle resets only after all active trainers are robbed
  - retired trainers do not count in cycle
  - historical redemptions seed flags correctly
- Abandono:
  - document as alias to retired or test as separate state after implementation.
- Hall of Fame:
  - final Liga creates one idempotent entry
  - final Copa creates one idempotent entry
  - team snapshot does not drift after trainer changes save
- Notifications/activity:
  - save upload creates event
  - purchase creates event
  - team lock creates event
  - retired/round closed/season changed events when added
  - UI still shows max 5.
- SQLite/Supabase repository behavior:
  - strict mode does not fallback
  - non-strict fallback is explicit.

## Reusable Pieces

- `SeasonVersion` dataclass and coercion helpers.
- `validate_season_version()`.
- `season_version_for_round()`.
- `points_for_position()` / `coins_for_position()`.
- `next_divisions_from_rankings()` for two-division leagues.
- `trainer_flags.py` as a starting point for trainer status rules.
- `select_shop_promotions()` as mostly pure promotion selector.
- `sync_hall_of_fame_from_sources()` merge/idempotency pattern.
- Notification HTML and max-visible behavior.
- Existing storage facades as temporary repository boundary.

## Pieces Needing Modification

- Move Copa/Juicios official workflows into Admin or formalize why they remain
  domain-owned before API migration.
- Implement complete season archive before allowing "Guardar en historial" reset.
- `division_count != 2` is now blocked explicitly in Streamlit 2.0.
- Functional `rules` are now wired where they affect current behavior.
- Persist Hall of Fame team snapshots from final/locked data.
- Introduce `ActivityEvent` concept before expanding notifications.
- Move `trainer_flags` out of generic settings in Supabase V2.
- Continue replacing dynamic historical reads with stored snapshot data where
  legacy paths remain.

## Regression Risks

- Changing active roster can sanitize old results unexpectedly.
- Making a trainer inactive can still make live totals disappear outside closed
  snapshot views.
- Direct manual edits to `season_config_v2` can still bypass app guards; normal
  app edits no longer alter closed snapshot scoring.
- League reset clears purchases through `clear_purchases()`, which is broader than
  a league-only reset.
- Discard season still calls the legacy global wipe internally; it is now gated
  in Admin but not season-scoped.
- Hall of Fame can duplicate Liga entries if source id changes after config edits.
- Any move toward multiple divisions touches Liga UI, pairing, ranking, history,
  Discord summaries and rewards.
- Supabase RPCs are required for atomic shop discount/team lock behavior in remote
  production.

## Recommended Phase 2 Implementation Order

1. Lock down permissions.
   - Completed for the main Liga/Trainer/Saves/Tienda danger controls in 2.3.

2. Define trainer status semantics.
   - Completed in 2.3 with `active`, `retired`, `abandoned` and
     `disqualified`.

3. Add immutable round snapshots inside current `league_state`.
   - Completed in 2.1 and extended in 2.3 with trainer status metadata.

4. Refactor scoring reads to prefer snapshots.
   - Points/coins/history/Hall should read closed snapshots when present and only
     use dynamic config for open/current previews.

5. Make SeasonVersion rules real or intentionally hidden. Completed in 2.2 for
   existing rules.
   - `last_b_gets_steal` and `team_lock_required` are functional.
   - `cup_is_separate` remains metadata because Copa is already separate.

6. Decide the division scope for 2.0 Streamlit. Completed in 2.2.
   - Streamlit 2.0 officially supports exactly 2 divisions until domain/API work.

7. Finalize Hall of Fame immutability.
   - Build entries from final snapshots and locked teams; keep merge idempotency.

8. Introduce ActivityEvent abstraction.
   - Start with save uploaded, purchase completed, team locked.
   - Then add trainer retired, round closed and season changed.

9. Expand tests around the closed mechanics.
   - Especially immutable scoring after config changes and permissions.

10. Update architecture docs for Supabase V2 after the above behavior is fixed.
    - Only then design tables/repositories/API with confidence.

## Bottom Line

PokeApp already has the skeleton needed for Phase 2, but it should not enter
feature freeze until historical scoring, permissions, trainer status semantics,
Hall snapshots and activity events are closed. The safest next implementation is
not more UI: it is locking admin actions and making closed rounds immutable.

## Phase 2.1 Implementation Notes

Status: implemented on top of the current Streamlit/settings architecture.

### Cause Fixed

Before 2.1, `league_state.results` stored positions only. Points and coins were
reconstructed later through `season_config_v2`, so a future config change could
reinterpret a closed round.

### Snapshot Structure

Closed matchdays now persist snapshots in `settings.league_state` under:

```json
{
  "round_snapshots": {
    "1": {
      "schema_version": 1,
      "round_no": 1,
      "closed_at": 1780000000,
      "season_config_version": {},
      "division_snapshot": {"A": [], "B": []},
      "standings": [],
      "points_awarded": {},
      "coins_awarded": {},
      "penalties": {},
      "metadata": {
        "source": "finalize",
        "config_version_id": "default",
        "snapshot_schema_version": 1
      }
    }
  }
}
```

The implementation lives in `app/liga/snapshots.py`. It freezes:

- round number;
- close timestamp;
- applied season config copy and config id;
- A/B division composition at close time;
- official standings;
- league points awarded by trainer;
- league coins awarded by trainer;
- relevant penalty metadata at close time: dead count, dead point penalty,
  point reduction, coin reduction and store block state.

### Creation Policy

- `app/liga/ranking.finalize()` creates a snapshot when Anto closes a jornada.
- `app/liga/ranking.recompute_round()` regenerates the snapshot when Anto edits a
  closed previous jornada.
- Recompute preserves the previous snapshot config if it exists. Therefore editing
  official results can change history, but changing future config does not
  indirectly alter older awards.

### Snapshot-First Reads

- `points_from_league()` reads `round_snapshots` first.
- `coins_from_league()` reads `round_snapshots` first.
- Liga history UI reads closed standings from the snapshot when present.
- Legacy fallback remains for old `league_state` data without snapshots.

Current known limitation:

- Shop/economy sanctions (`coins_reduction`, `store_blocked`) remain live because
  they are active administrative sanctions, not closed league awards. League coins
  awarded by position are snapshot-first.

### Backward Compatibility

Legacy `league_state` without `round_snapshots` still loads. The app adds an empty
snapshot map when serializing state, but does not invent historic awards for old
rounds.

### Idempotency

`finalize()` now refuses to close a round if:

- the round already has a snapshot; or
- legacy official results already exist for that round.

Official edits must go through `recompute_round()`.

### League Permissions

Added `app/liga/permissions.py`.

Admin user for Phase 2.1 is still the current real admin: `Anto`.

Critical Liga mutations are restricted in UI and critical backend functions:

- finalize jornada;
- save results;
- cancel jornada;
- open/edit jornada;
- modify previous jornada;
- save divisions;
- reset Liga;
- `finalize()`;
- `recompute_round()`.

Read-only league views remain available to normal trainers.

### Tests Added

`tests/test_liga_snapshots.py` covers:

- snapshot freezes config version;
- snapshot freezes points;
- snapshot freezes coins;
- snapshot stores penalty metadata;
- snapshot-first points ignore later dynamic config;
- snapshot-first coins ignore later dynamic config;
- closed standings are read from snapshot;
- open/legacy rounds keep dynamic fallback behavior;
- legacy state without snapshots loads without error;
- finalize rejects existing snapshots;
- finalize rejects legacy recorded results without snapshot;
- non-admin cannot finalize;
- Anto passes the admin guard.

## Phase 2.2 - Configurable Season Closure

Phase 2.2 closes `season_config_v2` as the functional season config for the
current Streamlit architecture.

### Decision: A/B Only In Streamlit 2.0

The audit measured the blast radius of N divisions. Current production code is
modelled around exactly two divisions:

- `league_state.divisions` stores `A` and `B`;
- `league_state.matches` stores `A` and `B`;
- result editing, ranking, movements and history render `A` and `B`;
- Home, sidebar, topbar, Team Preview and Discord summaries read A/B labels.

Supporting 3+ divisions would require changing state shape, match generation,
ranking, historical rendering, multiple UIs and notifications together. That is
a major domain/API phase, not a safe 2.2 patch.

Therefore Streamlit 2.0 officially supports Liga A and Liga B only. This is no
longer false configurability: `division_count != 2` is rejected by validation,
while A/B sizes and movement count remain configurable.

### Season Config Fields Now Consolidated

`SeasonVersion` remains the versioned source for:

- active players;
- `effective_round`;
- `max_rounds`;
- A/B `division_sizes`;
- `movement_count`;
- `points_by_position`;
- `coins_by_position`;
- `rules`.

Version selection stays round-based: closed snapshots keep their frozen config,
and open/future rounds use `season_version_for_round()`.

### Config Mutation Policy

`save_season_version()` is now protected by the Anto admin guard.

It appends a new version and refuses to create versions that apply to:

- any closed jornada detected in `league_state.round_snapshots` or legacy
  `league_state.results`;
- the currently open jornada when `league_state.active == true`.

This prevents future config edits from mutating closed official history.

### Operational Rules

Known rules are completed with defaults for legacy configs:

- `team_lock_required`: functional. If false, opening a jornada does not trigger
  the missing team lock Discord warning.
- `last_b_gets_steal`: functional. If false, the last trainer in Liga B does not
  receive the free `Robar Pokemon` purchase on close.
- `cup_is_separate`: retained as normative/product metadata. The Copa code was
  already separate and is not refactored in this phase.

### Participants

`utils.league_users_for_round()` uses the explicit player list from
`season_config_v2` and still filters against the global `USERS` credential
registry. Unknown names are rejected by the admin panel validation instead of
being silently treated as participants.

Team Preview now receives the configured roster for the current jornada instead
of `USERS` global.

### Rewards, Rounds And Movements

- `points_for_league_position()` and `coins_for_league_position()` continue to
  delegate to `SeasonVersion`.
- `max_jornadas()` delegates to configured `max_rounds`.
- `division_a_size_for_count()` and `next_divisions_from_rankings()` use
  configured A/B sizes and movement count.
- Closed snapshots remain the source of truth for historical standings, points
  and league coins.

### Penalties Snapshot-First

`current_points_total()` now uses the latest closed snapshot penalty metadata
for a trainer when snapshots exist. This freezes dead-count and point-reduction
effects for the official closed table without consulting mutable save/juicio
state afterward.

Legacy/open rounds keep the old live fallback.

### Admin Panel

`app/interfaz/temporada.py` now exposes:

- participants;
- A/B sizes;
- total jornadas;
- points;
- coins;
- movement count;
- rules;
- version history.

The UI keeps divisions locked to `2` and validates against the supported A/B
model.

### Normativa

Normativa is not redesigned in 2.2, but its Liga chapter is generated from the
active season config for:

- player count;
- A/B sizes;
- total jornadas;
- ascensos/descensos;
- last-B Robar Pokemon rule;
- points and coins tables.

The logic does not depend on Normativa strings.

### Tests Added

2.2 extends coverage for:

- legacy rule defaults;
- admin-only season save;
- blocked config edits for closed/open jornadas;
- explicit season roster;
- two-division support decision;
- unknown trainer validation;
- rule boolean validation;
- configured `max_rounds`;
- configured A/B sizes and movement count;
- configurable last-B steal reward;
- snapshot-first point penalties.

### Remaining Debt After 2.2

- True N-division support belongs to a larger domain/API phase.
- `cup_is_separate` remains metadata because Copa is already separated but not
  driven by a formal season contract.
- Explicit season lifecycle (`draft/active/finished/archived`) still belongs to
  Supabase V2/domain work.
- Economy sanctions remain live administrative state; league coin awards are
  snapshot-first.
