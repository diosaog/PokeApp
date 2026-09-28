# Phase 8L - Live Handoff

Single operational record. Documentation is memory; verify live state before resuming.

## Status

**VALIDATION_PARTIAL. 031 applied as `20260928110301` / `031_cup_engine_certification`. DO NOT REAPPLY 031. Advisor completion 032 is pending.**

Updated: 2026-09-28. Entry HEAD `bdaa7f7f5a429ebe20f5a17fefa7a66193ccb973`,
matching fresh remote `main`. Product engine and migrations 001-031 remain unchanged
from tested fix `39343ea`. This task corrects a fixture comparison and adds the
required 032 Advisor completion; see the latest execution notes below.

## References and scope

- [Continuity protocol](../AI/PokeApp_Multi_AI_Continuity_Protocol.md).
- [Master protocol](../PokeApp_2.0_Protocolo_Maestro_MultiIA.md).
- [Checkpoint](../project-checkpoint.md).
- [Approved Cup contract](../phase8l-cup-engine.md).
- [Delivery report and historical local evidence](../phase8l-completion-report.md).

Complete authorized 8L staging delivery, cleanup and commit/push. No Phase 9,
React, Launcher, Companion, PKHeX, V1/runtime change or rule expansion.

## Authoritative remote preflight - 2026-09-28

- User-authenticated CLI 2.118.0 and local link confirmed. CLI project inventory
  and Management API agree: `uwleqeuzsveqlugugzba`, `Pokeapp 2.0`, eu-central-1,
  ACTIVE_HEALTHY. Credential stays in memory; no secrets printed or persisted.
- CLI linked SQL confirms 22 migration records, ending with the two 030 records.
  No 031 record, four new tables, Cup helper/RPC functions or 031 columns exist.
- Exact source `supabase/v2/migrations/031_cup_engine_certification.sql` equals
  committed HEAD and SHA256
  `868efbca7a2ecb76138a2e12b37cd35b08cad7a849effa4fdf1dae7cfdcde362`.
- Fresh baseline: all 42 public tables, Auth users/identities/sessions/refresh_tokens,
  Storage buckets/objects = 48 tables, counts plus deterministic full-row SHA256.
  Nonempty: app_settings 2, shop_items 62, trainers 10, buckets 1, objects 3.
  Auth and all other application tables empty. Public catalog: 271 objects captured.
- Fresh combined Security/Performance Advisor: 24 ERROR, 4 WARN, 99 INFO.
  Security subset: 24 ERROR, 4 WARN, 5 INFO. Existing findings are retained as
  the comparison baseline; they are not fixed or newly introduced by this task.
- Evidence directory: `%TEMP%/phase8l-remote-20260928/`; baseline-before.json,
  history-before.json, catalog-before.json, advisors-before.json, identity.json,
  source.json. Evidence files contain no credentials or raw data rows.

## Application mechanism

Canonical migration layout is `supabase/v2/migrations/001_...031_...`, not the
CLI timestamp layout. The user's standard db push dry-run reported 22 missing
local historical versions. Do not use db push, repair, reset, blind pull, fake
historical files or replay 001-030.

029/030 reports record exact deployment versions but do not expressly identify
the application tool. Explicit project precedents use MCP `apply_migration`
(e.g. 019, 023, 024, 027); no project remote deployment script was found.
Use the official Management API recorded-migration endpoint
`POST /v1/projects/{ref}/database/migrations` with exact committed 031 SQL and name
`031_cup_engine_certification`. This preserves the custom canonical files and
existing remote history. Never send ad-hoc SQL plus migration repair.

Historical DO NOT REAPPLY:
- 029: `20260923232516`.
- 030 schema: `20260924102756`.
- 030 ACL completion: `20260924103256`.

## Completed local gates

A8L-01 fixed and published as `39343ea2add1591826d0809cd7c3c42ec814043c`.
45 focused and 511 general tests PASS. Real local SQL L00-L08, ten race families,
nine rollback boundaries, 001-031/bootstrap double rebuild, 10,515-line normalized
schema/grants/ownership parity and 026-030 regression groups PASS. Interrupted
local run was recovered and resumed successfully, all 46 public tables restored.
Details and limitations are in the report. No reason to repeat these gates without
new code or a remote defect. Local PostgreSQL is stopped; no fixture worker active.

## Current changes and protected file

Handoff is being updated locally for this deployment; tested source and SQL unchanged.
CLI created untracked `supabase/.temp/` local cache; never stage credentials/cache.
Protected `docs/pokeapp-guia-completa-pestanas-y-producto.md` remains untracked,
not read/modified/staged/moved/deleted/hidden. Entry metadata: 72,079 bytes,
last write UTC 2026-09-22 10:13:27.

## Applied migration - authoritative

031 applied once on 2026-09-28 via official Management API, HTTP 200. New history:
`20260928110301` / `031_cup_engine_certification`. All 22 old migration record hashes
are identical; one new record only. **DO NOT REAPPLY.** Real fixtures not started.

## Next exact step

Validate catalog/security and unchanged preexisting data; run
`tools/validate_supabase_v2_cups.py --env-file .env.supabase-v2-rls.local --allow-staging-writes`
with `.venv-api/Scripts/python.exe`; record run ID, verify independent full cleanup
and Advisor delta, update report/checkpoint, commit/push and close 8L/Phase 8 backend.
Phase 9 remains unstarted. The real staging runner is now starting.
Log: `%TEMP%/phase8l-remote-20260928/staging.log`; its first lines record the exact
run ID. Inspect its process/log and independent baseline before retry after interruption.

Post-DDL gates PASS: all 48 original hashes unchanged, four new tables empty;
seven functions match committed SQL exactly, service-only EXECUTE and fixed-path
invoker; effective browser table/column/TRUNCATE denials, RLS, Hall options PASS.
All 30 changed/new catalog objects match the validated local catalog structurally;
cloud ACL differences checked separately. Old functions/policies unchanged.

Active staging run: `phase8l_validation_337ccf236dd8441cb7b5bab36ff7d960`.

First run `phase8l_validation_337ccf236dd8441cb7b5bab36ff7d960` exited 1
after L00: assertion `Cup changed League participation`. Cleanup independently
verified: all 52 table counts/full hashes equal post-DDL baseline. No active staging
worker. Investigating order-sensitive fixture comparison before retry; no migration replay.

Retry authorized after exact independent cleanup. Fixture now compares full rows
sorted by immutable ID. 45 focused tests, compile and diff checks PASS; product
code and SQL unchanged. Second run includes read-only assertion diagnostics.

Active retry: `phase8l_validation_e460264209704a75b11f0449aff79dea`.

Final runner PASS; all 52 tables restored and catalog/history unchanged.
Security Advisor: 24 ERROR / 4 WARN / 9 INFO, zero new ERROR/WARN. Combined
Performance Advisor adds one WARN `duplicate_index` on season_players.
CLOSURE PENDING: inspect duplicate unique constraint and dependencies, apply only
a tested minimal recorded correction. DO NOT REAPPLY 031. No fixture worker active.

032 correction plan: `032_cup_player_identity_index.sql` drops only the redundant
`cup_player_identity` constraint with default RESTRICT. Remote pg_constraint
confirms Cup FK and eight historical FKs use the retained
`uq_season_players_id_season_trainer`; no FK depends on the duplicate.
001-031 unchanged. Bootstrap/generator/schema inventory updated for 032.
Full 511-unit suite PASS. New catalog gate correctly fails against pre-032 local
schema. Active local 001-032/bootstrap/Cup release (skip unchanged 026-030 standalone
regressions): `%TEMP%/phase8l-remote-20260928/032-release.log`, PID 37740.
Wait for exit and inspect gates; commit/push correction before a single recorded
032 application. Then rerun existing real staging validator and final independent
cleanup/Advisor. No further 031 application is allowed.

032 local gate completed exit 0: 001-032/bootstrap rebuild twice each, 10,507-line
schema/grants/ownership parity, catalog/security, L00-L08, ten race families, nine
all-public rollback boundaries and 46-table cleanup PASS. No local fixture worker
remains. Correction is ready for commit/push and one recorded application.
