# All-vs-all League start, always-available Team Preview, «Fijar Equipo», gender check, «Mi perfil» — live record

Branch `claude/all-vs-all-league-start`, from `e237255` (tip of the published
`claude/ux-showdown-matchdays`). **PUBLISHED 2026-11-04 with the owner's
approval; verified read-only afterwards.**

| Layer | Live state |
|---|---|
| Railway API | `ef13a7ce` SUCCESS (source `f2f799c`, bundle of committed HEAD); previous `554bf854`; pastes flag `true`; 131 OpenAPI paths; `/health` 200; new routes 401 anonymous and with a bad bearer |
| Supabase | 001-079; 079 = `20261104134028`, applied once by `tools.phase30_apply_migrations` (owner-run). The owner re-ran the rehearsal with the final LF bytes (`ce57e6b7…`) on the verified backup: all PASS, preflight `problems: []` |
| Cloudflare web | `a81eb04f-ae65-4f53-821b-14e201a0a8ad` (100%), built with `VITE_API_BASE_URL=https://pokeapp-api-production.up.railway.app`; previous `0b061103`. Bundle contains the API URL, readiness/first-matchday/death-history routes, «Abrir jornada», «Fijar Equipo», provisional Team Preview, own death confirmation, profile tab CSS, gender mark, «Generar Poképaste» |
| Launcher | unchanged 0.26.11 (loads the new web) |
| Verifier | unchanged `2853bbc4`, `sleep 60` loop |
| ChampionsLocke after release | still 0 matchdays, 0 divisions, 0 initial snapshots, 0 Team Locks, no J1 preparation event, no new death resolution |

Pending real use (not simulated): a trainer preparing/opening J1, Iker
confirming 3/0/3 from his profile, ByVisan02 and Samu registering their
League saves with their own Launcher and confirming, the first «Fijar Equipo»
with its Discord/Pokepast.es announcement, and authenticated reads/refresh
cycles on `ef13a7ce` (no trainer request had reached it at verification:
1 request, no 5xx).

Production at the start (re-verified read-only 2026-11-04): Supabase 001-078,
API `554bf854`, web `0b061103`, Launcher 0.26.11. ChampionsLocke active, one
league `{"A":5}`, 4 matchdays, metadata `initial_assignment_rule=observed_deaths_v1`,
0 matchdays/divisions. Anto, Aaron: League save + confirmed history. Iker: save,
3 recorded deaths, history unconfirmed. ByVisan02, Samu: no League save.

## Owner decisions (2026-11-04)

- ChampionsLocke is all-vs-all: no A/B assignment, no allocation by deaths, no
  Administración step to create J1.
- «Abrir jornada N» is always visible below the general standings, with the
  exact reasons when it cannot open.
- Ordinary League operation never needs the administrator account.
- Team Preview never depends on a matchday or a Team Lock; a provisional team
  is never shown or published as a lock.
- «Fijar Equipo» on the own «Equipo» card, centred above the six.
- «Mi perfil»: wider, shorter, real tabs.

## Cause of the obsolete dependency

036 made every "modern" season start with the observed initial assignment
(`api_admin_finalize_initial_assignment`, admin-only): it sorts trainers by
deaths into A/B, creates the divisions, J1 and its pairs. 063 let a one-league
season use the same admin step (it then creates only «Liga»). For an
all-vs-all season the sort decides nothing, yet it was the only way to create
J1, and it also required every trainer's save, badges and death inputs BEFORE
J1 could exist. The death-history baseline (075) was admin-only as well.

## What changed

| Layer | Change |
|---|---|
| DB 079 `079_all_vs_all_first_matchday.sql` | `league_all_vs_all(sid)` (modern + J1 config without B). `api_league_prepare_first_matchday`: any active participant (or admin) prepares J1 once: one «Liga», every participant, every pair, snapshot rule `all_vs_all_v1` (constraint widened additively), audit event; idempotent by state, serialized on the season row, unique (season, number). `initial_assignment_inputs` answers `not_required` for all-vs-all (two-league seasons unchanged). `league_open_readiness` / `api_league_readiness`: season and per-trainer reasons mirroring the open/freeze checks. `api_participant_death_history`: the trainer's own state and confirmation of exactly the observed values (first baseline or the wipe counter they set); everything else stays administrative. No existing row is rewritten. |
| API | `GET /v1/seasons/{id}/league/readiness`, `POST /v1/seasons/{id}/league/first-matchday`, `GET`/`PUT /v1/seasons/{id}/death-history` (128 → **131** OpenAPI paths). Team Preview: entries for every selected trainer; without an official lock an active season shows `provisional` (the profile's public collection; own private details only to the owner in battle mode) or `unavailable_reason`. Team Lock refusals carry `detail.reason` (allowlisted). |
| Web | Liga › General: «Abrir jornada N» always present; unprepared J1 is prepared and opened by one confirmation; per-trainer reasons; own «Confirmar mi historial». Own profile: death-history card under the licence; «Fijar Equipo» centred over the gap between Pokémon 3 and 4 (prepares J1 if needed, confirms the six of the official save, PUT team-lock). Team Preview: official vs provisional labels, J1-less preview, empty states. ♂/♀ on the own team and own Pokémon card. «Mi perfil»: 880 px max, ≤700 px tall, identity+tabs header, two-column Perfil/Seguridad, only the selected panel renders (a `display:grid` rule overrode `hidden`). |
| Launcher | none (hosts the web) |

Unchanged: victories, segment deaths, penalties, rewards, ranking, freezing at
open, exactly-once close, corrections, final championship adjudication, the
private Showdown export, the public Pokepast.es paste (only after a confirmed
Team Lock), Railway verifier, sessions.

## Verification (2026-11-04)

- SQL, disposable PG17, 001-079: `validate_phase079_all_vs_all` PASS (incl. 3
  concurrent preparations → one J1); 075 deaths/four matchdays/two divisions/
  legacy/guards, 076 championship, 077 false deaths, player matchdays: all PASS.
- Rehearsal on a fresh read-only production backup
  `pre-release-20261104T114551Z` (private folder
  `PokeApp-migration-evidence/all-vs-all-079`): **17/17 PASS**; 101 tables
  byte-identical, 104 reads identical, upgraded copy equals a fresh 001-079
  build. On the restored ChampionsLocke (rolled back): Iker (non-admin)
  prepared J1 with 10 pairs; Iker self-confirmed **3/0/3**; still missing:
  ByVisan02 and Samu (save + baseline); opening refused
  (`initial_assignment_not_ready`), no snapshot written.
- Gender, end to end with the real server parser (win-x64 build) on two
  synthetic Pokémon Y saves written by PKHeX: Pikachu ♂/♀, Magnemite,
  Meowstic ♂ (form 0) / ♀ (form 1), Pyroar ♀, Nidoran♀/♂, Tauros, Chansey,
  Rotom-Wash, Unown-F. Parser = PKHeX for all 12; payload M/F/N; read model
  kept; export `Pikachu (M) @ Light Ball`, `Pikachu (F)`, `Magnemite`,
  `Meowstic`, `Meowstic-F`, `Pyroar (F)`, `Nidoran-F`…; PKHeX's ShowdownSet
  re-imports species, form and gender exactly. A projection without gender
  exports no (M)/(F) and warns. No code change was needed below the web.
  Fixture `tests/fixtures/showdown-y-genders.json`, test `test_gender_pipeline`.
- Python **1479 tests OK** (124 modules). Web: `tsc -b` clean, Vitest
  **44 files / 372 tests**. Node **70/70**.
- Playwright (136 tests): **75 passed / 50 failed / 11 skipped**; the previous
  tip gave 69 / 50 / 11 of 130. The 6 new `league-start.spec.ts` tests pass
  (real CSS: dialog proportions and tab panels at 1280/1440/390 px, «Abrir
  jornada 1» with reasons, «Fijar Equipo» centred within 6 px of the 3|4 gap
  and above the cards, provisional Team Preview); the rewritten Team Preview
  spec now passes. 49 failures are the previous tip's stale specs, unchanged.
  `economy › archived wallet` fails only after the preceding specs (the app
  restores the session on reload); it fails identically at `e237255` with
  the same preceding specs and passes in its own file: pre-existing,
  order-dependent.
- Visual inspection of the screenshots: «Mi perfil» 880 px, one row of
  identity + tabs, each tab its own content; Liga › General blockers; the
  «Equipo» header; the «Fijar Equipo» confirmation; provisional Team Preview.

## Release (done 2026-11-04 in this order)

1. Re-capture and rehearse (`tools.phase30_backup_rehearsal`; pins are now
   DEPLOYED ≤078, PENDING 079, sha256 `ce57e6b7…` of the LF bytes in git;
   the 2026-11-04 rehearsal ran the same SQL with CRLF line endings, `d5292204…`).
2. API first (safe on 078: the three new routes answer 503 until 079; Team
   Preview provisional and lock reasons need no DB change): commit+push,
   `tools.build_api_deploy_bundle`, `railway up`. Check: health, 131 paths,
   anonymous 401 on the new routes.
3. Migration 079: `tools.phase30_apply_migrations --apply --owner-authorized --backup <manifest>`.
4. Web: `npm run build` + `npm run deploy`.
5. No Launcher release.

Rollback: web → Cloudflare `0b061103`; API → Railway `554bf854` (now listed REMOVED: redeploy its image); 079 can stay
(additive). With the old API on 079, only the obsolete admin initial-assignment
review answers 503 for ChampionsLocke. A J1 prepared after release is
permanent (it ends the "discard before competition" window, as the admin
step did).

## Known limitations

- Self-confirmation only acknowledges observed values; pre-tracking deaths,
  false deaths, box changes, observation gaps and wipe counters larger than
  the deaths stay administrative.
- Readiness mirrors the server checks; the opening stays authoritative.
- Gender is shown only in the trainer's own views; public views keep their
  approved fields (gender already travels in the public Pokepast.es paste).
- ByVisan02 and Samu must register their League saves with their own Launcher;
  then each confirms their own history from the profile.
