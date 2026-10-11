# Phase 13 - representative staging

Closed 2026-10-11. **STATUS: PHASE 13 DONE.**
**PHASE 14 READINESS: READY FOR PERFORMANCE.** Phase 14 not started; no cutover.
[Structured evidence](phase13-staging-evidence.json),
[live handoff](work-in-progress/phase13-live-handoff.md).

## Entry and environment

Entry main/origin `fec337cb4f04aa3c15d36582d1b536fbaa4a4ae1`, fetched 0/0 and clean
tracked tree. Phase 12 was closed. Hosted V2 has 34 migrations through
042=`20261011160629` once; the fixed private reference remains reconciled with
six receipts, 57 mappings and 135 rows. No Phase 11/12 work was restarted.

Used a new disposable PostgreSQL **17.11** database on loopback port 55439,
`pokeapp_v2_validation_phase13_20261011`, provisioned from current 001-042
bootstrap. Six synthetic participants plus Admin/outsider operated a two-day
League, four independent championship fixtures and a modern Cup scenario.
HTTP used the real FastAPI routes, services, repositories and PostgreSQL RPCs;
Edge used current React against that API, without interception. Local synthetic
signed JWTs replace the external Auth provider behind the real PIN bridge;
database principal/role checks remain active. No real credentials or owner data
were used in fixtures.

Neutral synthetic observations entered the existing parsed-save/identity service.
This proves downstream acceptance and product behavior, not native parsing,
Launcher/cloud ingestion or physical save writes. Exact decimal sanction facts
were seeded before closure in the isolated championship fixtures to produce
deterministic fractional/negative final totals.

## Representative results

| Area | Fresh proof |
| --- | --- |
| Normal League | Server-derived Medal2 A/B; participants open J1/J2, edit results, close and finish; Admin archives. Closed mutations and ordinary exceptional correction fail. J1 and initial snapshots remain identical after later observations/scenarios. |
| Team Lock | Pending, on-time and late first fixation; replacements preserve first timing. Closed locks remain identical. Self private details work; rival and Admin rival projections omit private identity/IV/EV/ability/nature metadata; PC scope stays owned. |
| Economy | Prospective badge rewards 4→5→7; prior claims unchanged. Eight badges yield 39 before Champion, valid Champion adds 13 once. Purchase 12 changes wallet 52→40; replay does not debit again. A 10-coin buyer cannot spend 12. Inventory and revive redemption work. |
| Progress | Unknown is not zero. Eight observed badges with Champion false do not award completion. Champion evidence settles once; repeated observation has no duplicate reward. |
| Death/revive | One death freezes 0.2 penalty. Purchased revive retains one historical adjusted death when the same identity is observed alive. One wipe revival adds two adjusted deaths; combined three freeze 0.6, not a duplicate penalty. Alia's two-day final total is exactly 6.4. |
| Championship | Normal Cora champion at 11.6; exactly two leaders require audited BO3; three and four leaders use fewer deaths. Residual resolution permits only minimum-death candidates, nonempty reason and Admin. Replay is one effect; chosen Bruno is not a technical fallback. Fractional leaders 5.5 and negative totals -2.1 are preserved. |
| Finish/history | Five League certificates and five League Hall rows. Finish replay issues no coins. Cora has no safe historical lock, so Hall team stays empty. Final reconciliation preserves J1, locks, initial split and original Hall after all subsequent fixtures. |
| Cup | Current elimination rounds, BO3 results, close/finalize/certificate/Hall and replay. League-DQ Alia remains an active Cup entrant. Linked Cup blocks incompatible League exits; ordinary participant cannot operate Admin Cup controls. League history/economy unchanged. |
| Freshness | Result/general/profile, purchase/wallet/inventory, lock/preview/profile, rule/subsequent reward and wipe/profile/ranking paths update through current queries without F5. |

The harness records **248 HTTP requests / 13 checkpoints**. Final read-only
database verification finds **5 League certificates, 1 Cup certificate, 6 Hall
rows**, with the expected immutable sources unchanged.

## Defect and repair

**One real defect:** closing a modern day returned 503 because `plan_close`
expanded `rules_json` into `SeasonRules`, whose constructor does not accept
`badge_reward_coins` or `game_completion_reward_coins`. The failed operation was
reconciled first: J1 still open, no official snapshot or close effect.

The planner now explicitly selects its two sporting rules. Progress reward
settlement remains separate and the complete configuration still binds review
fingerprints. Two regressions cover normal close and frozen correction, including
zero/default/custom reward settings. Fixed browser close and all subsequent
real PostgreSQL closures pass. No SQL, API shape, auth contract or UI change.

## Validation and its limits

- **FRESH PASS:** focused matchdays 35; full Python **802** once on final product
  source (783 committed-scope plus 19 pre-existing unrelated untracked map tests).
- **FRESH PASS:** React **74 / 12 files**; real Edge **7 unique cases**, desktop
  1440px and mobile 390px. Admin rules/privacy, participant results/locks,
  shop/revive/wipe, mobile late lock, close/freshness and archived history/Hall.
  Screenshots reviewed for legibility/overflow; no F5 or API interception.
- **FRESH PASS:** TypeScript/production build, compile, full web formatting and
  diff checks. Ruff passes application/new tooling/tests. The legacy matchday
  test file's 23 lint findings are identical to entry, with no new findings.
- **FRESH PASS:** final read-only verifier added after the full gate, followed by
  its execution and the two transport-safety tests. No second full run.
- **NOT RERUN / unchanged:** parser, Phase 11 migration, Phase 12 comparison,
  unrelated browser suites. **N/A:** new migration/schema parity/Advisor gate;
  no schema/auth contract changed. Existing security contracts are retained;
  role/privacy denials were freshly exercised over HTTP.

Failed development runs are retained: incomplete synthetic stat fields and an
overstrict browser season-label locator were harness issues, as was the initial
final-verifier table name. Only invalidated cases were rerun. Final seven browser
PASS results combine the still-valid Admin run, three resumed journeys, fixed
close and two final history cases; no skipped/flaky case is counted as PASS.

## Delivery, preservation and cleanup

Application source **`cea57ca5d6e25c7b073aa2dd8857152730f1a157`** was committed and
pushed before deployment. Export uploaded only **238 committed API inputs**.
Railway **`3845ce2d-6488-43ef-893a-1459c2aed0bb` SUCCESS**, same source, image
`sha256:3feba3d294bdc5448160e770a42e7203860129c2670677a34e67bbda2314e160`.
Six public probes pass: liveness, unauthenticated read/close denials, exact/rejected
CORS, unchanged frontend deep SPA/CSP/nosniff. Positive business mutations are
local only; no owner matchday was closed for hosted proof.

Cloudflare remains unchanged: deployment `ea9c837d-86f0-4b0a-826d-a4774371b56e`,
version `77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11`, 100%, source `eb4e402`.
No migration, replay, V1 call, hosted login, business fixture or Storage-byte
operation. Sixteen Management API queries were explicitly read-only.

Entry→final: **56/59 full table records identical**; only owner Auth activity
changed before deployment (refresh tokens 608→609, sessions 72→73, users still
one). Stable credential/identity hashes are identical; an independent scope query
found zero non-owner users/sessions/tokens. **Predeploy→final all five captures
are identical**, including all 59 full table records, 34 migration records,
stable credentials, private security catalog and complete private reference.
Owner/manual seasons, results, economy, locks and Storage metadata are intact.

API and Vite stopped; the exact dedicated database was dropped and its absence
verified. Other database inventory is unchanged. PostgreSQL stopped after zero
other client connections. Remote fixtures and business residue: **zero**.
Private logs/screenshots/captures have a verified 101-file copy and manifest at
`%LOCALAPPDATA%/PokeApp-migration-evidence/phase13/20261011/`.

## Remaining scope and short owner check

Launcher/cloud ingestion, physical save mutation, distribution/onboarding and
visual polish remain roadmap work. Local psql transport timings are not hosted
performance evidence. Representative latency/load profiling belongs to Phase 14.
Hall cards could distinguish repeated winners' seasons more clearly in later
visual work; no cosmetic redesign was made here.

Antonio can inspect the current public app without changing the active season:

1. Liga: General and existing official/current matchday navigation.
2. Own profile: points, wallet, visible deaths and observed/unknown progress.
3. A rival's Team Preview: public detail only, with no IV/EV/private metadata.
4. Shop and inventory: current wallet, available items and redemption state.
5. Administración: current prospective reward values; inspection needs no save.
6. Repeat profile/Liga on mobile and inspect existing Hall history.

Reusable fixture procedure: provision a new guarded local database, run `serve`,
then `prepare`, `before-browser`, the four initial browser cases, `after-browser`,
the close case, `finish-journey`, `championships`, `cup`, the two history cases and
`verify`. Use `--connect`, loopback-only browser URL and opt-in fixture flags.
These are staged procedures, not commands to blindly replay on completed data.

Changed files: sporting planner and two regressions; local staging tool and
safety tests; opt-in real browser journeys; this report, evidence, checkpoint and
handoff. Protected guide and unrelated untracked files remain untouched.
Documentation closure is a subsequent commit; obtain its exact HEAD from Git.

**NEXT: Phase 14 performance, awaiting its execution instruction. STOP.**
