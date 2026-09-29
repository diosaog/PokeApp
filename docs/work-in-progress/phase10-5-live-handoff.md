# Phase 10.5 — live execution record

Observation: 2026-09-29 Europe/Madrid. **IN PROGRESS; Phase 11 NOT STARTED.**
[Contract](../phase10-5-functional-alignment.md),
[continuity](../AI/PokeApp_Multi_AI_Continuity_Protocol.md),
[checkpoint](../project-checkpoint.md),
[previous closed delivery](../phase10-completion-report.md).

## Verified entry and safety

Entry main `9a8620db5324104e753bb5f63b408d7b140502e8`. Fresh `git fetch origin`
succeeded; HEAD/origin/main identical, divergence 0/0, no tracked changes. Only
the protected guide is untracked; never open/inspect/hash/stage/move/delete it.
Local migrations 001–032 present. No code, database or hosting changes in A.

Remote state: **STAGING_UNVERIFIED** in this phase. Last Phase 10 report records
V2 `uwleqeuzsveqlugugzba`, 031=`20260928110301`, 032=`20260928111840`, 24 history
records. These are historical evidence, not a fresh preflight. Never replay them.
Historical backend source `6d2c66a` / frontend `3c83a16`; verify actual resources
before deploying, using [existing runbooks](../../deploy/README.md).

Preserve owner active season `c6bcac5b-0b89-403f-8242-41ac58286ade`, other manual
seasons and Anto's current staging identity/PIN/admin. No fixture cleanup is
authorized for those records. Use local disposable PG if active-season guards
prevent staging tests. Prior delivery reports retain their historical results.

No validation process started by A. Pre-existing processes/remote operations not
inspected: UNKNOWN; inspect before reusing ports or retrying remote operations.

## Alignment matrix and progress

| Package / finding verified against entry source | Classification | State |
|---|---|---|
| A: entry, contract, resumable memory | FIX NOW | Documentation complete; publication belongs to this commit. |
| B: League has daily dropdown and technical totals table, no primary GENERAL; existing 030 points view is authoritative | FIX NOW | Next. |
| C: ordinary results use admin routes/SQL authority | FIX NOW | Pending B. |
| D: two-way daily tie uses H2H before deaths; slug total order influences outcomes | FIX NOW | Pending C. |
| E: 026 requires initial manual A/B before activation | FIX NOW | Pending D; manual readiness must remain explicit. |
| F: 029 lifecycle reads final daily snapshot positions for title | FIX NOW | Pending E; structural Phase 11 blocker. |
| G: wipe counter exists in stats but lacks owned command/UI | FIX NOW | Pending F. |
| H: Preview only selects scheduled match; missing-lock presentation insufficient | FIX NOW | Pending G. |
| I: pending promotions hidden by public view; voucher canje absent in React; purchases require active season | FIX NOW | Pending H. |
| J: Admin displays technical readiness keys and ordinary results | FIX NOW | Pending I. |
| K: minimal public projection from permitted published facts | FIX NOW | Pending J; wider scope blocked below. |
| L: legacy exports badges; neutral Phase 9 parser lacks observed progress | FIX NOW | Minimal contract pending K. |
| M: overview has about 13 sequential reads; command invalidation is broad | FIX NOW | Guard every touched package; record Phase 14 work. |
| Ten unresolved rules listed in contract | OWNER_DECISION_REQUIRED | No answers inferred; defer dependent branches only. |
| Physical effects, cloud save ingestion, installer/updater | FUTURE LAUNCHER/CLOUD | Out of scope. |
| Final sprites, item art, audio and broad UI redesign | POLISH | Deferred. |
| Manual Discord judicial verdicts and modern Cup formats | INTENTIONAL V2 DIFFERENCE | Preserve; no legacy jury/Swiss restoration. |

Target evidence: `app/application/frontend_reads.py`, `web/src/features/core.tsx`,
`app/api/routes/matchdays.py`, `app/domain/services/league.py`, migrations
026/027/029/030, and Phase 9 parser contracts. Targeted review only; no repeated
full-project audit. Independent read-only B review confirmed: adjusted competitive
deaths are not visible Box 8 deaths, identity revision alone does not prove a
complete box, and disabled historical participants must not disappear.

## B implementation contract / next action

GENERAL uses official accumulated points from 030, exact decimal strings and
server ordering; no sporting rank/champion inferred from a rendering tie-break.
Include all season participants, including inactive/historical rows. Current
wallet balance is independent of frozen points. Visible dead count needs an
explicit complete current Box 8 observation; absent/incomplete data is unknown,
not zero. Current save changes never recalculate official points.

Prefer bounded aggregate reads, no per-trainer PC/ledger queries. UI defaults to
GENERAL and shows only current/completed day tabs. Keep per-day Top 3 and A/B.
Focused gates: no days, current/closed/final days, no future tabs, tied/negative/
exact-decimal totals, historical participants, unknown/verified zero/dead counts,
privacy and constant query count. Any SQL needs local PG and privilege validation.

## Evidence ledger

- A, entry source above, Windows local: Git branch/HEAD/remote/status inspection
  and fresh fetch PASS. Document links and `git diff --check` are the A gate;
  no code/database test is claimed for this documentation-only block.
- Historical Phase 10: 565 Python, 11 React and nine browser tests at the commits
  recorded in its report, not rerun or claimed as Phase 10.5 evidence.
- No new migration applied, staging mutation, deployment or fixture cleanup.

Exact next step: publish A with explicit document staging; implement and validate
B before starting C. Maintain this record after each green atomic block. Project
estimate remains ~80%; Phase 11 NOT READY and not authorized to start.
