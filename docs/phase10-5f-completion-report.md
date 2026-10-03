# Phase 10.5F - League championship, finish and frozen Hall

Implementation checkpoint, 2026-10-03. **LOCAL GREEN; public delivery pending.**
This report will be superseded with observed remote closure evidence.

## Entry and scope

Entry `dc326b38e8695af104745ef04b8cd1ec0e638c4f`, main/origin 0/0, clean tracked
tree. E was complete. Fresh pinned Supabase V2 observation: 28 migration records,
036=`20261001165951` once, 53 scoped tables, owner identity/admin intact; Advisor
24 ERROR / 5 WARN / 125 INFO. Railway `6aa70f72-f0cb-41a1-86d6-7b4227803392`
SUCCESS, source `90a31fc`; compatible Cloudflare `3d829325-66fc-4da4-88f4-b7bd4967f8d7`,
version `0224318e-38d6-4178-ae3a-646384328eb8`, source `0215f73`.

## Implementation and authority

New forward migration **037_league_championship** adds private immutable BO3
resolutions and finish certificates. No applied migration or historical season is
rewritten. Championship review derives exact accumulated official points from
the existing numeric view: awarded points across closed days minus the latest
frozen sanction/death capture, once. It validates the official snapshots and
relational sources before accepting those totals. API totals remain decimal
strings; React never ranks or selects the champion.

One leader wins by points. Exactly two tied leaders require an explicitly selected
external BO3 winner and nonempty reason, bound to all official source revisions.
Exactly three use fewer frozen authoritative adjusted deaths. Unknown deaths,
residual minimum-death ties and four or more tied leaders remain unresolved.
Names, IDs, rendering order, old matches and final daily positions never decide
the title. Existing final-day eligibility and irreversible exit cutoffs remain.

Finalist is null with **OWNER_DECISION_REQUIRED**. No finalist rule is invented;
this does not prevent a proven champion from being certified or archived.

## Lifecycle and historical safety

Final-day close, season finish and archive remain separate. Finish freezes the
champion, exact points, source revisions and public team. Archive consumes that
certificate, creates one League Hall row and never recalculates from current save
or counters. Team comes from the last valid six-Pokemon closed Team Lock, falling
back to an earlier valid closed lock; absent safe history remains empty. Cup Hall
and its independent modern certification are unchanged. Finish/archive issue no
new League points, coins or penalties. Post-League shop repairs remain package I.

Pre-F finished seasons without a certificate are not automatically reinterpreted;
new archive attempts fail closed. Exact prior successful finish/archive receipts
can replay. A hashless finish may recover an old receipt only; a new command needs
the current championship fingerprint. Frozen modern J1 initialization remains a
required historical source, while current progress observations are not reread.

## API, React and security

Admin championship review is one aggregate read. Explicit BO3 and finish commands
use verified JWT/admin identity, strict bodies, idempotency, revision and source
fingerprint checks. Unknown outcome retry preserves the original key/body;
mutations have no automatic retry. Stale evidence clears the decision and refreshes
review. UI uses human championship/BO3 language and omits undefined League finalist.
Existing C/D/E flows and the bounded read-only ReadError recovery remain intact.

Both new tables enable RLS and revoke browser table/column access. Helpers use
SECURITY INVOKER with fixed search_path and service-only execution. The retained
old lifecycle function is guarded to allow only draft discard. Certificate and
BO3 updates are forbidden. Concurrency shares existing season/participant locks.

## Validation and delivery

Full Python **680 PASS**, React **14 PASS**, Edge **28 PASS**. Compile, targeted
Ruff, Prettier, public production build and deployment dry-run pass. Real local
PostgreSQL 17.11: F **8 groups / 15 rollback boundaries**, exact 49-table
restoration; four fresh migration/bootstrap builds give **12,046 identical lines**
of schema, grants and ownership. B/C/D/E and modern Cup regressions pass with
49-table restoration per family. The complete relevant 026-030 regressions pass,
including 17/20/24/19/8 scenario groups and 9/17/8/10/16 rollback boundaries,
respectively. See [closure evidence](phase10-5f-closure-evidence.json).
Remote positive finish/BO3/archive/Hall actions will not be tested on owner data;
their proof is local only. Public delivery requires committed/pushed source, a
fresh full baseline and Advisor baseline, migration 037 once, compatible Railway
then Cloudflare, safe authenticated reads/absent-resource denials and final exact
data comparisons. Current remote writes for F: **zero**.

## Remaining work and performance

No per-player HTTP loop or broad new query invalidation. Review uses one database
RPC; frozen seasons return their stored certificate. Existing overview latency
remains a Phase 14 candidate. Full cloud ingestion, physical save writes, shop
repairs and visual redesign are outside F.

Outstanding decisions retain their existing scope: residual championship ties,
4+ leaders, finalist policy, badge/completion economy, normal lifecycle operator,
future game milestones, purchased revive, Team Lock cutoff, scouting and League
DQ/Cup interaction. None is replaced with an invented rule.

Phase 10.5 remains **IN PROGRESS**. Phase 11 **NOT READY / NOT STARTED**.
Finish and document F, then STOP; do not start G automatically.
