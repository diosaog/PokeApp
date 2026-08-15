# PokeApp 2.0 Pure Domain

Status: Fase 4

Checkpoint base: `f91f612 Add domain contracts`

Scope: business logic extraction only. No new mechanics, no SQL, no API,
no React, no parser refactor and no visual changes.

## Boundary

Target flow:

```text
UI / legacy service
  -> adapters
  -> pure domain services
  -> explicit result
  -> persistence outside domain
```

The domain services under `app/domain/services/` do not read or write global
app state. Values such as current matchday, current trainer, timestamps and RNG
are explicit inputs.

## New Structure

```text
app/domain/services/
    __init__.py
    activity.py
    archives.py
    hall_of_fame.py
    league.py
    rewards.py
    season.py
    shop.py
    snapshots.py
    team_locks.py
    trainers.py
    trials.py
```

Contracts remain simple data objects. Behavior lives in services.

## Extracted Logic

### Season

Pure now:

- effective `SeasonVersion` selection by matchday;
- active-version fallback selection;
- version application window validation against closed/open matchdays;
- structural validation for roster, division sizes, rewards and rules;
- change summary between versions.

Still legacy/mixed:

- `app/season/config.py` still reads/writes `season_config_v2`;
- admin permission and current league-state checks stay in legacy application
  code;
- Streamlit runtime still uses the legacy `SeasonVersion` dataclass until a
  repository/API layer exists.

### Ranking And Standings

Pure now:

- pair generation;
- match map synchronization;
- player extraction from match maps;
- all-results-filled check;
- wins/losses;
- head-to-head;
- ranking with existing tiebreak behavior;
- A/B movement calculation;
- last-B steal award intent;
- points after dead-count and judgment reductions.

Legacy wrapper connected:

- `app/liga/ranking.py` delegates ranking helpers to
  `app.domain.services.league`;
- `app/liga/divisions.py` delegates movement calculation to the pure service.

Still mixed:

- dead counts still come from save snapshots/storage before entering the pure
  ranking function;
- closing a matchday still mutates `st.session_state`;
- free purchase for `last_b_gets_steal` is still applied by legacy storage after
  the domain can express the intent.

### Rewards

Pure now:

- points for position from `SeasonVersion`;
- coins for position from `SeasonVersion`;
- `LeagueStanding` construction from A/B rankings;
- award maps from standings.

Still mixed:

- live total money still combines badges, purchases, sanctions and snapshots in
  legacy modules;
- historical official values must continue reading snapshots first.

### Promotions And Shop

Pure now:

- catalog candidate normalization;
- discount price calculation;
- mega eligibility;
- candidate priority;
- weighted selection with injected RNG;
- rotation avoiding previous round when possible;
- promotion state from explicit `now`;
- discount-purchase decision with explicit claimed promotion ids.

Legacy wrapper connected:

- `app/tienda/discounts.py` delegates selection, price, state and helper scoring
  to `app.domain.services.shop`;
- random orchestration remains outside the pure selector when runtime does not
  provide a seeded RNG.

Still mixed:

- reading purchase history, writing discounts, stock decrement, purchase insert
  and notifications remain in storage/application code;
- redemptions are still mostly mixed and should move after repositories exist.

### Trainer Status And Flags

Pure now:

- status derivation from flag dict;
- inactive status semantics;
- status labels;
- robbed-flag clearing;
- status transition payload construction;
- robbed flag marking;
- robbed cycle reset when every active trainer has been robbed.

Legacy wrapper connected:

- `app/entrenadores/trainer_flags.py` delegates status derivation, labels,
  status mutation payloads and robbed-cycle logic to
  `app.domain.services.trainers`;
- reading/writing flags and admin permission remain outside the domain.

Still mixed:

- historical robbery sync still reads redemptions;
- watermark management remains legacy because it is persistence-specific.

### Team Locks

Pure now:

- team-lock validation against trainer, participants, matchday and rules;
- `TeamLock` construction with public team data.

Still mixed:

- save parsing, current team extraction and actual upsert remain in storage/UI
  code;
- Discord/activity side effects stay outside.

### Snapshot Construction

Pure now:

- `MatchdaySnapshot` construction from explicit rankings, version, penalties,
  divisions and `closed_at`;
- points/coins/penalties maps derive from explicit standings.

Still mixed:

- legacy `app/liga/snapshots.py` still returns dict snapshots for current
  Streamlit runtime;
- persistence and snapshot lookup remain legacy.

### Season Archive And Hall

Pure now:

- `SeasonArchive` construction from explicit versions, snapshots, statuses,
  champion data and Hall entries;
- league Hall entry construction from frozen public team data.

Still mixed:

- current archive builder still reads league state, season document, team locks,
  cup states and lifecycle when values are not injected;
- cup Hall derivation remains inside legacy archive code.

### Activity Events

Pure now:

- event id and dedupe key generation;
- clean payload/context;
- save-upload, purchase-completed and team-locked event construction;
- dedupe of event streams;
- visibility check.

Still mixed:

- `app/activity/events.py` still persists legacy uppercase event dicts in
  `activity_events_v1`;
- event persistence remains a repository concern for Fase 5.

### Copa

Pure now:

- no broad Copa rewrite.

Still mixed:

- Swiss, elimination and doubles remain Streamlit/application islands;
- only future clean rules should be extracted incrementally.

### Juicios

Pure now:

- jury majority calculation;
- vote counts;
- verdict from votes;
- allowed status transitions.

Still mixed:

- case persistence, permission checks, forms and UI stay in legacy modules.

## Audit Classification

| Area / function group | Classification after Fase 4 | Notes |
| --- | --- | --- |
| `app/season/config.default/coerce/select` | PURE WITH SMALL EXTRACTION | Pure service exists; legacy still owns document IO. |
| `app/season/config.save_season_version` | MIXED DOMAIN + STORAGE | Permission, lifecycle check and write remain legacy. |
| `app/season/validation.validate_season_version` | PURE ALREADY | Domain equivalent added for contracts. |
| `app/liga/ranking._gen_pairs` | PURE NOW | Delegates to domain. |
| `app/liga/ranking._sync_match_map` | PURE NOW | Delegates to domain. |
| `app/liga/ranking._wins_losses/_h2h/_rank` | PURE NOW | Dead-count lookup remains outside before calling pure ranking. |
| `app/liga/ranking.finalize/recompute_round` | MIXED DOMAIN + STREAMLIT | Mutates state, writes snapshots, awards item. |
| `app/liga/ranking.points_from_league` | MIXED DOMAIN + STREAMLIT | Snapshot-first behavior preserved; total math extracted. |
| `app/liga/rewards` | PURE-ish | Domain rewards service added; legacy still resolves active config. |
| `app/liga/divisions.next_divisions_from_rankings` | PURE NOW | Delegates movement to domain after config lookup. |
| `app/liga/snapshots.build_matchday_snapshot` | PURE WITH SMALL EXTRACTION | Domain contract builder added; legacy dict builder retained. |
| `app/liga/state` | STREAMLIT/STORAGE | Serialization and restore only; not domain. |
| trainer status/flags | MIXED DOMAIN + STORAGE | Pure mutations extracted; IO and permission remain legacy. |
| team locks | MIXED DOMAIN + STORAGE | Pure validation/builders added; upsert remains storage. |
| shop discounts | MIXED DOMAIN + STORAGE | Selection/pricing/state pure; scheduling/persist/notify legacy. |
| shop purchase validation | MIXED DOMAIN + STORAGE | Pure decision exists; atomic transaction remains legacy/RPC. |
| redemptions | MIXED REMAINING | Validation still embedded in redeem flow. |
| ActivityEvent construction/dedupe | PURE WITH STORAGE WRAPPER | Pure service exists; legacy persistence remains. |
| Hall/archive merging | MIXED REMAINING | Pure builders added; live/archive merge still legacy UI. |
| Copa | STREAMLIT/MIXED | Deferred except documented boundaries. |
| Juicios | MIXED DOMAIN + STORAGE | Small vote/status rules extracted. |

## Parity Strategy

- Existing tests around ranking, snapshots, shop promotions and trainer status
  remain active as regression coverage.
- New tests exercise pure services directly.
- Legacy wrappers were only connected where the pure implementation mirrors the
  existing behavior exactly and has nearby tests.
- Snapshot-first invariant is preserved: closed matchdays read official
  snapshots instead of recalculating historical awards.

## Time And Random

- Pure services never call the clock internally.
- `now`/`closed_at`/`created_at` are explicit inputs.
- Shop selection requires an RNG argument in the pure function.
- The legacy shop wrapper may choose the runtime RNG because that orchestration
  is not domain logic.

## Error Model

- Domain services return explicit result dataclasses where the caller must make
  a decision (`PurchaseDecision`, `VersionApplicationDecision`,
  `TeamLockValidation`, `RobbedFlagResult`).
- Validation functions return issue objects.
- Existing legacy functions may still raise UI/application errors while runtime
  is Streamlit.

## Remaining Side Effects

Still outside domain:

- state mutation;
- save parsing;
- purchase insert;
- stock update;
- redemptions;
- notifications;
- permission checks;
- cache invalidation;
- archive persistence;
- Hall persistence.

## What Fase 5 Can Assume

- `app/domain/services/` is the place for business decisions.
- Repositories should feed explicit data into these services and persist the
  returned result.
- Application services can wrap old Streamlit flows around domain calls while
  repositories are introduced.
- No repository should be invented inside domain.

## Approximate Decoupling

Business logic is not fully migrated, but the most portable core is now present:

- ranking/tiebreak/movement/rewards: mostly extractable now;
- shop promotion selection/pricing: mostly extractable now;
- trainer status/robbed semantics: mostly extractable now;
- snapshots/activity/team locks/archive/Hall: builders available, persistence
  still legacy;
- Copa/redemptions/money and save parsing: still mostly mixed.

Rough estimate: around 45-55% of the business-rule surface identified for
Fase 4 now has pure equivalents, while the remaining high-risk parts are mainly
orchestration, persistence, parser and UI coupling.
