# Final Phase 10.5 alignment - implementation map

Entry 2026-10-08: `dd9b7b9bcf38491962ace956fd90e53fbfdd0670`, main/origin
fetched 0/0, clean tracked tree. M DONE verified. Pinned Supabase V2 freshly
observed: 32 migration records, latest 040=`20261008185548` exactly once.

| Area | Directed read / expected write | Migration expectation | Invalidated evidence |
| --- | --- | --- | --- |
| Admin | Existing config/reward settlement, Admin screen; simple current reward rules with audited prospective revision and preserved structural configuration | Private immutable live-rule history and settlement binding | I rewards/CAS/replay/races; config history; Admin UX |
| Reactive state | state/useCommand and result/wipe/shop/progress/lock actions; centralized viewer/season-scoped dependency map | None itself | Mutation refresh, unknown outcomes, isolation and M request guards |
| Trainer profile | Overview/General, K public scouting, H self detail, Mi PC; cards route to visual profile, reuse Pokemon details and own PC | Only timing projection dependency | Public/self privacy, navigation, empty states, mobile |
| Shop | Authoritative item.category and existing purchase/inventory; four simple category controls | None | I promotion/voucher/precision UI and M read guards |
| Lifecycle | Admin/participant matchday and F finish paths; add eligible participant open/close/finish and scoped SQL authority | Extend normal guards, preserve exceptional admin checks and receipts | C/D/F state/authorization/CAS/concurrency/rollback/history |
| Championship | F exact frozen totals; 3+ deaths and audited minimum-death residual resolution | Extend current certificate/resolution contracts, preserve old frozen artifacts | F title ties/decimals/replay/correction races/Hall |
| Team Lock timing | 019 upsert, matchday opening/cancellation, H/K projections; persist first fixation and first opening evidence without cutoff | Private first-event evidence and public status projection, no historical backfill | H/K/self privacy, replacement/open/cancel races, frozen history |

Reward updates take effect for subsequently accepted eligible observation events;
previous immutable claims/ledger entries are never repriced. Server transactions,
not client save timestamps, order rule updates against acceptance. Existing
structural config is protected once used. Missing cloud data stays unknown.

Legacy lock timing without sufficient first-event evidence stays explicitly
unknown. Current replacement time must never be presented as first fixation.

Out of scope: Phase 11, broad Phase 14 refactoring, full cloud ingestion, physical
save writes, finalist redesign and Cup changes. Protected guide/unrelated untracked
files untouched. Local PostgreSQL only for positive destructive fixtures.

State: VALIDATED, ready for committed-source delivery. Final local gates pass:
763 Python, 74 React, 68 unique browser cases, 16 real PostgreSQL families with
53-table restoration, four fresh identical builds (13,161 schema lines), 15-helper/
three-table security catalog, TypeScript/build/format/compile/Ruff/dry-run/diff.
See [local evidence](../phase10-5-closure-evidence.json). Public final delivery and
preservation comparison remain pending; this is not a DONE claim.
