# PokeApp 2.0 Phase 2.6 Freeze Audit

Audit date: 2026-08-15

Base commit audited before this documentation pass:
`f6d8fc179f8c9e021bdf6b4fa1e2687e2d7e8b2a`

Scope: final functional audit, feature freeze decision and checkpoint before
architectural migration. No mechanics, SQL, Discord behavior, React work,
Cloudflare work, parser refactor or Supabase V2 work were added in this phase.

## Verdict

PokeApp 2.0 is functionally closed enough to freeze product and start the next
architectural phase later.

No blocking half-feature was found. There is real legacy debt, mostly around
Streamlit state, broad `settings` JSON documents and a few dormant helpers, but
that debt is expected migration material. It does not prevent declaring feature
freeze.

Feature freeze status:

```text
FEATURE FREEZE FUNCIONAL POKEAPP 2.0
```

After this checkpoint, new ideas should go to `docs/post-2.0-backlog.md`.
Allowed work is limited to bugs, security, migration, architecture,
equivalence and stability.

## Final Functional Inventory

| Mechanic | What it does | Current source of truth | Main UI | Who can change it | Tests | State | Known debt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Login and PIN | Selects trainer identity and gates private views with a 4 digit PIN. | `settings` keys such as `pin:*` plus Streamlit session. | Login, sidebar PIN change. | Trainer changes own PIN through UI. | Indirect/manual. | CLOSED | Streamlit/session level only; needs server-side auth/RLS later. |
| Season config | Defines players, jornadas, A/B sizes, movement, points, coins and rule flags. | `settings.season_config_v2`. | `Temporada/Admin`, Normativa, Liga, Team Preview. | Anto only through admin guard. | `test_season_config.py`, `test_season_validation.py`, snapshot tests. | CLOSED | Officially A/B only in Streamlit; N divisions deferred. |
| League state | Tracks current jornada, active round, divisions, matches, results and movements. | `settings.league_state` plus `st.session_state` mirror. | Liga, Home, Admin, Team Preview. | Official mutations only from Admin/Liga admin mode. | `test_liga_snapshots.py`, `test_liga_rewards.py`, config tests. | CLOSED | JSON aggregate and Streamlit mirror should become domain/repository. |
| Round snapshots | Freezes closed jornadas: config version, standings, rewards, divisions and penalties. | Embedded in `settings.league_state.round_snapshots`. | Liga history/table, rewards, archive. | Created on close jornada by admin flow. | Strong coverage in `test_liga_snapshots.py`. | CLOSED | Stored inside league JSON until V2 schema exists. |
| Rewards | Awards points and league coins from frozen snapshots or current config for open legacy state. | Derived from snapshots and `season_config_v2`; purchases are in `purchases`. | Liga, Entrenadores, Tienda money. | Admin closes jornada; purchases reduce balance. | `test_liga_rewards.py`, snapshot/config tests, shop tests. | CLOSED | Open-round legacy fallback remains until full domain extraction. |
| TrainerStatus | Marks active, retired, abandoned or disqualified trainers. Inactive trainers are excluded from active competition. | `settings.trainer_flags`. | Admin, Liga, Entrenadores, Saves, Tienda, Team Preview. | Anto only through `set_trainer_status()`. | `test_trainer_status.py`. | CLOSED | Helper name `is_trainer_retired()` remains compatibility debt. |
| TrainerFlags | Tracks trainer flags such as robbed, seeded from redemptions/history. | `settings.trainer_flags` plus redemption sync. | Liga/Tabla badges. | Auto from redemption sync; admin maintenance in Admin risk area. | `test_trainer_status.py`. | CLOSED | Robbery cycle remains legacy JSON until V2. |
| Team locks | Stores the fixed team for a jornada, including late status and save reference. | `team_locks` table, Supabase or SQLite. | Entrenadores, Team Preview, notifications, archive. | Trainer can lock own team if active; read by Admin/archive. | `test_notifications.py`, `test_activity_events.py`, archive tests. | CLOSED | Atomicity and permissions should move server-side in Fase 8. |
| Saves and parser | Uploads saves, sets current save and parses teams/boxes through the PKHeX bridge/cache. | `saves` table + storage bucket/local file + parser cache. | Saves, Entrenadores, Team Preview. | Trainer uploads own save if active; retired can consult. | `test_saves_support.py`, activity tests. | CLOSED | Parser remains a bridge/black box until Fase 9. |
| Pokemon inspector | Shows private Pokemon details for owner and public data for others. | Derived from parsed save/snapshot. | Entrenadores, Team Preview. | Read-only derived UI. | Indirect/manual visual coverage. | CLOSED | Privacy is UI/domain convention now; RLS/API later must enforce it. |
| Shop catalog | Static item catalog, categories, prices and assets. | `app/tienda/catalog_data.py`. | Tienda, Normativa. | Code/config only. | Shop promotion tests indirectly. | CLOSED | Catalog should become `shop_items` in Supabase V2. |
| Shop promotions | Rotating discounts, stock and activation windows. | `shop_discounts` table plus discount selection logic. | Tienda, notifications/Discord announcements when triggered by existing flows. | Admin/close-round flow and storage RPC/local helpers. | `test_shop_promotions.py`. | CLOSED | Business rules are mixed with storage and Discord notifier. |
| Purchases | Registers completed purchases and pending/used items. | `purchases` table. | Tienda, Entrenadores inventory, notifications, money. | Trainer through Tienda; some rewards auto-create purchases. | `test_shop_promotions.py`, activity tests. | CLOSED | Must become server-side transaction/API for React. |
| Redemptions | Records item/comodin usage payloads. | `redemptions` table. | Entrenadores inventory, Tienda redeem flows, trainer flags. | Trainer through redemption flows. | Trainer/shop coverage. | CLOSED | Payload JSON should become typed per item later. |
| Pokemon flags | Tracks Pokemon-level shield/robbed/revived flags. | `pokemon_flags` table. | Entrenadores, inventory, robbery/shield flows. | Redemption flows and Admin risk maintenance. | Trainer/shop coverage. | CLOSED | Some maintenance helpers are legacy and should move behind API/Admin. |
| ActivityEvents | Stores recent product events for notifications. | `settings.activity_events_v1`. | Sidebar/home notifications. | Emitters in save upload, purchase completion and team lock. | `test_activity_events.py`, `test_notifications.py`. | CLOSED | Append-only events should become table-backed and server-side. |
| Notifications | Shows up to 5 concise visible items, preferring ActivityEvents and falling back to legacy data only if no events exist. | Derived from `ActivityEvents` or legacy saves/purchases/locks. | Sidebar/Home. | Read-only. | `test_notifications.py`. | CLOSED | Fallback should disappear after V2 data is established. |
| Season lifecycle | Moves season through active, finished, archived or discarded states. | `settings.season_lifecycle_v1`. | `Temporada/Admin`. | Anto only. | `test_season_archive.py`. | CLOSED | `draft` constant exists but no real draft UI yet. |
| SeasonArchive | Freezes final season summary, snapshots, config, statuses, Copa states and public champion team. | `settings.season_archives_v1`. | Admin history, Hall of Fame. | Anto archive flow. | `test_season_archive.py`, Hall tests. | CLOSED | Stored as JSON document until `season_archives` V2. |
| Hall of Fame | Shows automatic historical winners and frozen champion teams. Prefers archive entries. | Derived from archives/live sources plus Hall settings. | Hall of Fame. | Mostly automatic; archive makes it stable. | `test_hall_of_fame.py`, archive tests. | CLOSED | Live, not-yet-archived entries can still move before archive. |
| Copa | Runs separate cup formats: swiss/top cut, elimination and doubles. | `settings.copa_swiss_state`, `settings.copa_elim_state`, `settings.copa_dobles_state`. | Copa. | Manual Copa UI. | Archive/Hall indirect tests only. | CLOSED for 2.0 | Legacy island; needs `Cup` contract later. |
| Juicios | Creates cases, votes, verdicts and penalties. | Juicios state in `settings`. | Juicios, Tienda money/ban effects, Liga penalties. | Creator/admin-like flow depending on case action; viewer voting. | Minimal direct coverage. | CLOSED for 2.0 | Needs `Trial / Case` contract, clearer permissions and tests. |
| Admin back office | Centralizes official competition mutations. | Calls domain/storage helpers. | `Temporada/Admin`. | Anto only for critical actions. | Season/config/status/archive tests. | CLOSED | Copa/Juicios still have their own workflow UIs by product decision. |

## Source Of Truth Snapshot

| Data | Current home | Kind | Ambiguity / risk |
| --- | --- | --- | --- |
| Active trainer session | `st.session_state.user` | Session state | Client/session only. |
| PINs | `settings.pin:*` | Settings JSON string | No real auth backend. |
| SeasonVersion | `settings.season_config_v2` | Settings JSON document | Closed history uses snapshots, not mutable current config. |
| Lifecycle | `settings.season_lifecycle_v1` | Settings JSON document | `draft` is a constant, not a full UI workflow. |
| Players | `season_config_v2.versions[*].players`, validated against `utils.USERS` | Settings + static registry | `USERS` is still the credential/name registry. |
| Divisions | `league_state.divisions` and closed `round_snapshots` | Settings JSON | Closed snapshots win for history. |
| Matches/results | `league_state.matches/results` | Settings JSON | Admin UI owns official mutations. |
| Standings | Derived from snapshots/current state | Derived | Closed standings should read snapshots first. |
| Round snapshots | `league_state.round_snapshots` | Settings JSON | Official for closed jornadas. |
| Rewards | Snapshot rows and `season_config_v2` for future/open rounds | Derived/settings | Purchases and penalties affect balances. |
| TrainerStatus | `settings.trainer_flags` | Settings JSON | Helper naming is legacy. |
| TrainerFlags | `settings.trainer_flags` + redemption sync | Settings JSON + table-derived | Robbed cycle is legacy but functional. |
| Team locks | `team_locks` table | Supabase/SQLite table | Needs server-side permission/atomicity later. |
| Purchases | `purchases` table | Supabase/SQLite table | Critical operation should move behind API/RPC. |
| Redemptions | `redemptions` table | Supabase/SQLite table | Payload is untyped JSON. |
| Pokemon flags | `pokemon_flags` table | Supabase/SQLite table | Functional, but admin maintenance should be API protected. |
| Saves | `saves` table + storage/local files | Supabase storage/table or SQLite/files | Parser output is derived. |
| Parsed Pokemon | save parser/cache/snapshots | Derived from save file | Not canonical on its own. |
| ActivityEvents | `settings.activity_events_v1` | Settings JSON list | Good legacy bridge; V2 table needed. |
| SeasonArchive | `settings.season_archives_v1` | Settings JSON list | Historical source since 2.4. |
| Hall of Fame | Archive-derived + Hall state | Derived/settings | Archive entries win over live entries. |
| Copa | `settings.copa_*_state` | Settings JSON | Legacy island. |
| Juicios | Juicios settings state | Settings JSON | Needs typed model and stronger tests. |

## Half-Implemented Or Legacy Mechanics

No blocking half-mechanic was found.

Non-blocking debt found:

- `storage.wipe_all_app_data()` and `_wipe_local_sqlite()` still exist as legacy
  full wipe helpers. The product path uses season discard/prepare and active
  cleanup instead.
- `app/tienda/sections.py` still contains dormant `render_discord_panel()` and
  `render_flags_reset()` helpers. They are not mounted by the normal Tienda UI.
- `revived_after_wipe:*` remains a setting/key name and some UI text still says
  "Revividos tras wipe". It is a naming debt, not a current-season logic block.
- Juicios keeps `LEGACY_STATUS_MAP` for old case statuses. This is expected
  compatibility, not product contradiction.
- Normativa still mentions the current season ending after jornada 4 because the
  active product config/rules are still this season's rules.

Searches did not find active TODO/FIXME/NotImplemented blockers.

## Copa Audit

Current behavior:

- Swiss cup stores players, rounds, wins/losses/byes, history, results,
  qualified/eliminated data, manual pairings and top-cut state.
- Elimination cup stores players, rounds, current round and Hall run id.
- Doubles cup stores configured teams, rounds, final and Hall run id.

Persistence:

- `settings.copa_swiss_state`
- `settings.copa_elim_state`
- `settings.copa_dobles_state`

Manual parts:

- Pairings, results, top-cut/final state and bracket management are UI/manual.

Automatic parts:

- State serialization.
- Hall sync when a champion/final can be read.
- SeasonArchive captures Copa state snapshots.

Admin status:

- Copa is intentionally separate from Liga/Admin in 2.0. It remains its own
  tournament flow and is not expanded in this phase.

Debt:

- Needs a `Cup` contract later.
- Needs stronger direct tests.
- Archive stores Copa as raw state, not normalized entities.

## Juicios Audit

Current behavior:

- Cases can be created, edited, viewed, voted, resolved, cancelled and converted
  into penalties.
- Visibility can be public or creator-bound.
- Penalties feed money/points/store restrictions through current helpers.

Persistence:

- Juicios state lives in `settings` as JSON.

Permissions:

- Creator can edit/delete own case.
- Viewers can vote in active cases.
- Creator can proxy jury votes.
- Resolution and penalty logic is guarded by case workflow rules, but this is
  not yet a server-side authorization model.

Connection to other systems:

- Penalties affect Liga/money/store behavior.
- TrainerStatus is separate and should remain separate.

Debt:

- Convert to `Trial / Case` in Fase 3.
- Add direct repository/service tests before API migration.
- Harden permissions in Fase 7/8.

## Admin Centralization Check

Centralized under `Temporada/Admin`:

- season config changes;
- trainer status changes;
- official Liga controls through `page_tabla(admin_mode=True)`;
- archive/finish/prepare/discard lifecycle;
- Pokemon flag maintenance risk area.

Normal user pages:

- Entrenadores: own team lock, own inventory/use, own save-derived data.
- Saves: upload/current/history/download.
- Tienda: purchase/redeem flows.
- Liga normal: read/refresh view, not official admin mutations.

Exceptions accepted for freeze:

- Copa remains its own tournament UI.
- Juicios remains its own workflow UI.
- Liga reset exists only inside admin mode and should be treated as legacy risk
  until lifecycle/archive fully replaces it in the future UI.

No important admin mutation was found exposed as a normal user control.

## Lifecycle Check

Implemented states:

- `active`: normal season state.
- `finished`: season is closed after a valid final closed jornada.
- `archived`: historical SeasonArchive exists.
- `discarded`: active season is intentionally discarded without Hall/archive.

Defined but not implemented as full flow:

- `draft`: constant exists, but there is no draft setup wizard yet.

Transitions:

- `active -> finished` through Anto-only finish.
- `finished -> archived` through Anto-only archive.
- `active -> archived` can auto-finish first when valid.
- `archived/discarded -> active` through prepare new active season.
- `active -> discarded` through explicit danger-zone discard.

Frozen on archive:

- config document;
- lifecycle status;
- league snapshots and final standings;
- trainer statuses;
- Copa state snapshots;
- public champion team snapshot.

Cleaned when preparing a new active season:

- active Liga state;
- active trainer flags;
- robbery watermark;
- active Copa states;
- active purchases/promos/redemptions/Pokemon flags/team locks;
- active season config reset;
- runtime session keys.

Preserved:

- saves and save files;
- users/static catalog/assets;
- Hall and SeasonArchives;
- archive/history settings.

## Immutable History Check

Closed jornada representation is protected by round snapshots. Later edits to
config, penalties, saves or active state should not rewrite closed official
standings, points or league coins when snapshots exist.

Archived season representation is protected by SeasonArchive. Hall prefers
archive-derived entries, so the champion team should not move when a new save is
uploaded after archive.

Answer:

```text
Normal app actions should not accidentally change the official representation of
a closed jornada or archived season.
```

Accepted residual risks:

- Direct manual edits to `settings` or database rows can corrupt history.
- Live Hall entries before archive can still move because they are derived.
- Copa archive state is raw legacy state, not normalized records.

## ActivityEvent Check

Implemented event types:

- `SAVE_UPLOADED`
- `PURCHASE_COMPLETED`
- `TEAM_LOCKED`

Confirmed behavior:

- Stable dedupe keys prevent repeated reruns from duplicating events.
- Recent events are sorted by timestamp/id descending.
- Notification UI shows a maximum of 5 visible items.
- Purchases with price `0` are hidden from visible notifications.
- If ActivityEvents exist but render no visible item, fallback is not mixed in.
- If no ActivityEvents exist, legacy saves/purchases/team locks are used.
- ActivityEvents survive archive/discard because they are not active competition
  rows.

Debt:

- ActivityEvents live in settings JSON and should become append-only
  `activity_events` table records emitted by server-side operations.

## Current Security Inventory

| Operation | Current protection | Accepted until |
| --- | --- | --- |
| Save season config | Backend/admin guard via `save_season_version()` plus UI guard. | Fase 7/8 RLS/API |
| Trainer status mutation | Backend/admin guard in `set_trainer_status()`. | Fase 7/8 |
| Close/open/edit jornada | UI/admin mode and league permission helpers. | Fase 8 API |
| Archive/finish/prepare/discard | Backend/admin guard via lifecycle/admin actions. | Fase 8 API |
| Purchase | UI flow plus storage/RPC/local helpers. | Fase 8 API/RPC |
| Team lock | UI ownership checks and storage upsert. | Fase 8 API/RPC |
| Save upload | UI active trainer check plus storage. | Fase 8/API and RLS |
| Juicios | Repo/workflow checks. | Fase 7/8 |
| Copa | UI workflow checks. | Fase 7/8 |
| Pokemon flags maintenance | Admin risk UI. | Fase 8 API |

Temporary acceptance:

- Streamlit is a trusted client for the current small group.
- Supabase RLS/API is not the final security layer yet.
- Sensitive Pokemon details are privacy-by-UI/domain convention until RLS/API.

## Supabase / SQLite / Settings

Supabase is used when configured for:

- `saves`
- `purchases`
- `redemptions`
- `pokemon_flags`
- `shop_discounts`
- `team_locks`
- `settings`
- save storage bucket

SQLite/local files are fallback/development for the same core tables and local
save files.

Settings JSON currently contains official state for:

- league state;
- season config;
- trainer flags;
- lifecycle;
- archives;
- ActivityEvents;
- Copa;
- Juicios;
- Hall derived/manual state;
- PINs and miscellaneous settings.

Precedence:

- Supabase wins when configured.
- SQLite/local is fallback/dev.
- Streamlit `session_state` mirrors UI/runtime state and should not be treated
  as the official source for closed history.

Main risk:

- `settings` is a flexible JSON bucket. It made 2.0 possible without schema
  churn, but Fases 3-8 must replace it with contracts, repositories, V2 tables,
  RLS and critical API endpoints.

## Test Audit

Current test files:

- `test_activity_events.py`
- `test_hall_of_fame.py`
- `test_liga_rewards.py`
- `test_liga_snapshots.py`
- `test_notifications.py`
- `test_saves_support.py`
- `test_season_archive.py`
- `test_season_config.py`
- `test_season_validation.py`
- `test_shop_promotions.py`
- `test_trainer_status.py`

Well covered:

- season config validation/versioning;
- snapshot immutability and snapshot-first rewards;
- trainer status/flags;
- shop promotions and atomic discount behavior;
- ActivityEvent and notifications;
- Hall/archive stability;
- saves support helpers.

Medium/minimal coverage:

- save parser integration;
- Entrenadores visual/privacy rendering;
- Tienda UI rendering;
- Copa behavior;
- Juicios behavior.

Critical missing tests before migration, not before freeze:

- direct Juicios repo/workflow tests;
- direct Copa state/Hall tests per format;
- storage repository equivalence tests once repositories exist;
- API/RLS tests once those layers exist.

No artificial coverage expansion was added in 2.6.

Freeze validation:

- `py -m compileall -q .`: passed.
- `py -m unittest discover -s tests`: passed, 72 tests.
- `git diff --check`: passed.

## Visual Regression Check

No visual bug was changed in this phase.

Known non-blocking visual debt:

- Streamlit CSS layers still stack from `theme.py`, `champions_skin.py`,
  `premium_phase2.py` and `final_polish.py`.
- Some old names/text remain, especially "wipe" naming around revived counters.
- Component extraction is still pending for cards/tiles/menus.

The visual product is considered good enough for 2.0 freeze; further redesign is
not allowed before migration unless it fixes a real bug.

## Feature Freeze Criteria

Freeze criteria:

- Product mechanics are defined.
- Liga A/B Streamlit model is closed.
- Season config is versioned and admin-only.
- Closed jornadas have immutable snapshots.
- Rewards use snapshots where official history exists.
- TrainerStatus and TrainerFlags are formalized.
- Admin back office centralizes official Liga/season mutations.
- Season lifecycle and SeasonArchive exist.
- Hall of Fame prefers frozen archive entries.
- ActivityEvents and NotificationView exist.
- Saves/team locks/shop core flows are functional.
- Tests and compile checks are green.
- Documentation, checkpoint and backlog are updated.
- No critical half-mechanic remains.

Result: passed.

## Frozen Decisions

- Streamlit 2.0 supports exactly Liga A and Liga B.
- N divisions are not implemented before migration.
- Copa remains separate from Liga.
- Juicios remains a separate workflow.
- Supabase remains the current remote store.
- No React/Cloudflare work starts before Fases 3-9.
- No new mechanics after this freeze.

## Gaps

Critical blockers:

- None found.

Non-critical gaps:

- settings JSON is overused;
- Streamlit session mirrors official state;
- security is not final RLS/API;
- Copa/Juicios need typed contracts and tests;
- dormant legacy helpers remain;
- CSS layers need design-system extraction later;
- parser bridge remains coupled to current app.

## Next Step

Next planned phase:

```text
Fase 3 - Contratos de Dominio
```

Do not start it inside this checkpoint. Fase 3 should define contracts only:
Pokemon/PublicPokemon/PrivatePokemon, Trainer, Season, SeasonVersion, Division,
Matchday, Match, LeagueStanding, ShopItem, ShopPromotion, Purchase, ParsedSave,
TeamLock, TrainerFlags, ActivityEvent, HallOfFameEntry, Cup and Trial/Case.
