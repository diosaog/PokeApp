# PokeApp 2.0 Phase 2 Functional Audit

Audit date: 2026-08-14

Scope: functional audit only. No runtime behavior, rules, data, Supabase schema,
Discord behavior, scoring or UI flow was changed by this document.

## Executive Summary

Phase 2 is partially implemented, but it is not feature-freeze ready yet.

The strongest pieces already in place are:

- `season_config_v2` as a versioned JSON setting with `effective_round`.
- A real Anto-only season editor in `app/interfaz/temporada.py`.
- Dynamic league rewards through `app/liga/rewards.py`.
- Trainer flags for `retired` and `robbed`.
- Team locks, shop discounts and purchases in dedicated tables.
- Hall of Fame auto-sync from Liga and Copa sources.
- Recent notifications derived from saves, purchases and team locks.

The largest gaps before Phase 2 can close are:

- Historic league results are not immutable enough. Positions are stored, but
  points/coins/config snapshots are not.
- The league implementation is still hard-wired to two divisions, A and B.
- Some admin-grade league controls are still available to any active trainer.
- `abandono` is a UI concept mapped to `retired`; it is not a separate state.
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
| `division_count` | Weak | Stored/validated, but UI and league logic are locked to two divisions. |
| `division_sizes` | Partly | Only first size is used for Liga A; remainder becomes Liga B. |
| `movement_count` | Yes | Used for A/B ascents and descents. |
| `points_by_position` | Yes | Used dynamically by rewards. |
| `coins_by_position` | Yes | Used dynamically by rewards. |
| `rules` | Mostly dead | Stored, but key rules are not consistently enforced by league code. |

### Hardcoded Values Still Present

- `utils.USERS` remains the real trainer registry and credentials source.
- `SECTIONS` is static in `utils.py`.
- Liga supports `A` and `B` only in `league_state`, UI, ranking and history.
- `app/interfaz/temporada.py` disables `division_count` and forces `2`.
- Last Liga B reward `Robar Pokemon` is hardcoded in `app/liga/ranking.py`,
  independent of `rules["last_b_gets_steal"]`.
- Team lock requirement is notification-based, not a hard blocker.
- Static aliases remain: `MAX_JORNADAS`, `CURRENT_POINTS_BY_POSITION`,
  `CURRENT_COINS_BY_POSITION`; they now mirror defaults but can mislead future work.

### Versioning

`save_season_version()` appends a new version and sets it active. The UI only lets
Anto save a version from the current tramo onward.

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
6. Divisions can be manually adjusted in Liga.
7. A jornada is opened with `Editar jornada`.
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
- Adjust divisions.
- Open jornada.
- Mark winners.
- Save results.
- Finalize jornada.
- Edit previous jornada.
- Reset Liga.
- Mark trainer abandonment/retirement.
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
- `trainer_flags` in `settings`: retired/robbed flags.
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

These Liga controls are currently disabled only for retired users, not restricted
to Anto:

- open/edit jornada
- finalize jornada
- cancel jornada
- edit previous jornada
- save divisions
- reset Liga

This is a high-priority Phase 2 permission gap.

### Missing Or Partial Admin Goals

- There is no explicit `start season` state separate from editing version/division
  and creating `league_state`.
- There is no formal `finish season` action beyond `tramo > max_rounds`.
- `division_count` is not actually configurable beyond 2.
- Adding new trainer names in season config does not create credentials, portrait
  assets or trainer registry entries.
- `rules` can be stored but not edited in UI and not consistently used.
- No Discord notification is attached to season config changes yet.

## 2E - Trainer States

### Retired

Storage:

- `settings.trainer_flags`
- Shape per trainer includes `retired`, `retired_at`, optional `retired_by`.
- Module: `app/entrenadores/trainer_flags.py`

Activation:

- UI: `Entrenadores -> Administracion -> Gestion de abandonos`
- Only Anto can access it.
- Disabled while a league round is active.

Effects:

- `active_users()` excludes retired trainers.
- Liga divisions are sanitized without retired trainers.
- Ranking appends retired users at the bottom with `0.0`.
- `points_from_league()` and `coins_from_league()` return 0 for retired users.
- Money breakdown returns 0 and `store_blocked=True`.
- Saves upload is disabled for retired users.
- Redeem/comodin flow is blocked for retired users.
- League page is read-only for a retired logged-in user.

Visuals:

- Sidebar status shows `Consulta`.
- Liga/table can show a `Retirado` badge.
- Entrenadores profile shows `Retirado`.
- Saves summary says consultation mode.

Reversibility:

- No UI exists to unretire.
- It can only be reversed manually by editing `trainer_flags`.

Risk:

- Old results remain in `league_results`, but totals become 0 because scoring
  rejects users not in `active_users()`. If the desired rule is "historical
  points remain visible but no new points accrue", this needs a snapshot fix.

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
- Retiring a trainer removes robbed metadata from that trainer.

Dependencies:

- `redemptions`
- `purchases`
- `pokemon_flags`
- `trainer_flags`
- `active_users()`

### Abandono

There is no separate `abandono` entity/state today.

Current behavior:

- UI calls it "Gestion de abandonos" / "Marcar abandono".
- Implementation calls `set_trainer_retired()`.
- Therefore today `abandono == retired` functionally.

If 2.0 needs `retirado != abandono`, a new field is required, for example:

- `status: active | retired | abandoned`
- or separate booleans with clear precedence.

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
| Matches/results | `league_state` JSON | No immutable standings snapshot. |
| Points/coins from league | Dynamic functions over `league_results` + season config | Old totals can change if config changes. |
| Money available | Derived from league coins + badges + bonuses - purchases - penalties | Depends on snapshots/saves and purchases. |
| Purchases | `purchases` table | Supabase primary, SQLite fallback. |
| Redemptions | `redemptions` table | Used as event history for robberies/revives. |
| Pokemon flags | `pokemon_flags` table | Fingerprint stability matters. |
| Trainer flags | `settings.trainer_flags` | Should become entity/table later. |
| Team locks | `team_locks` table | Good candidate for V2 with `season_id`. |
| Saves metadata | `saves` table | Bytes are in Supabase Storage/local files. |
| Save parsed snapshots | `settings.trainer_snapshot:*` | Derived cache, not official source. |
| Shop promotions | `shop_discounts` table | Good candidate for V2 with `season_id`. |
| Hall of Fame | `settings.hall_of_fame_v1` | Auto-derived, but not fully immutable. |
| Notifications | Derived from tables | No persistent activity log. |
| Wipe | `storage.wipe_all_app_data()` | Deletes settings and data; not season-scoped. |

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

- Closing a jornada writes a complete immutable round snapshot.
- Points/coins use stored round snapshots after config changes.
- Editing previous round intentionally replaces only that round snapshot.
- Division movement uses historical movement count.
- `division_count > 2` is either blocked explicitly or fully supported.
- Liga controls require Anto where intended.
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

- Add immutable `round_snapshots` before relying on configurable seasons.
- Restrict Liga admin actions to Anto or a formal admin permission.
- Decide whether `abandono` is just retired or a separate status.
- Either block `division_count != 2` clearly or implement N divisions end-to-end.
- Make `rules` operational or remove from editable expectations.
- Persist Hall of Fame team snapshots from final/locked data.
- Introduce `ActivityEvent` concept before expanding notifications.
- Move `trainer_flags` out of generic settings in Supabase V2.
- Replace dynamic historical scoring with stored awards.

## Regression Risks

- Changing active roster can sanitize old results unexpectedly.
- Retiring a trainer can make old totals disappear from the general table.
- Direct edits to `season_config_v2` can alter old scoring.
- League reset clears purchases through `clear_purchases()`, which is broader than
  a league-only reset.
- Wipe deletes all settings and generated data globally, not per season.
- Hall of Fame can duplicate Liga entries if source id changes after config edits.
- Any move toward multiple divisions touches Liga UI, pairing, ranking, history,
  Discord summaries and rewards.
- Supabase RPCs are required for atomic shop discount/team lock behavior in remote
  production.

## Recommended Phase 2 Implementation Order

1. Lock down permissions.
   - Restrict Liga admin-grade actions to Anto first. This prevents accidental
     state corruption while implementing deeper changes.

2. Define trainer status semantics.
   - Decide if `abandono` remains an alias of `retired` or becomes its own status.
     This affects active roster, ranking, money, saves, shop and robbery cycles.

3. Add immutable round snapshots inside current `league_state`.
   - This is the highest leverage fix and does not require Supabase V2 yet.
   - Store version id, config subset, positions, points and coins on close.

4. Refactor scoring reads to prefer snapshots.
   - Points/coins/history/Hall should read closed snapshots when present and only
     use dynamic config for open/current previews.

5. Make SeasonVersion rules real or intentionally hidden.
   - `last_b_gets_steal`, `team_lock_required`, and future rules should be used by
     close/open flows or removed from UI expectations.

6. Decide the division scope for 2.0 Streamlit.
   - Conservative option: officially support exactly 2 divisions until React/API.
   - Larger option: implement N divisions fully before feature freeze.

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
