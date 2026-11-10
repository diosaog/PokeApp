# PokeApp Multi-AI Continuity Protocol

Canonical path: `docs/AI/PokeApp_Multi_AI_Continuity_Protocol.md`.
Reconciled: 2026-09-26. Keep one copy at this path.

## Shared memory map

| Question | Maintained source |
|---|---|
| How do AI instances continue the same work? | This protocol |
| What are the project-wide constraints and roadmap? | [Master protocol](../PokeApp_2.0_Protocolo_Maestro_MultiIA.md) |
| Which phase is active and where is its memory? | [Project checkpoint](../project-checkpoint.md) |
| What is the current operational state and next action? | [Administración › Avisos live record](../work-in-progress/save-audit-notices.md) (2026-11-09: detector v2 PUBLISHED / VERIFIED: API `a15cfd4f`, rollback `336f3f05`; web `681d7e85`, rollback `983449a9`; source `f8c9a8b`; first v2 analysis with the next trainer sync. SQL 084 `20261108192609` additive, informative, never blocks or writes a save. Never reapply 084; no pending migration). [Normativa live record](../work-in-progress/normativa.md) (2026-11-09: PUBLISHED / VERIFIED, source `9f2a1fc`). Previous record: [NET/Felicidad/Discord](../work-in-progress/net-friendship-discord.md). **Continue from the tip of `origin/claude/net-friendship-discord`.** |
| What behavior was approved? | [Functional alignment contract](../phase10-5-functional-alignment.md) |
| What was implemented and what evidence exists? | Active phase evidence in its live record until closure; [previous Phase 10 report](../phase10-completion-report.md) retains historical delivery evidence |

Published continuation (2026-11-04): `codex/mid-season-enrollment` descends
from `c2e8617`, preserves the independent Pokepast.es fix and is pushed to
origin. [Enrollment record](../work-in-progress/mid-season-enrollment.md)
contains authorization, fresh 079-to-080 backup rehearsal, exact deployment
IDs, verification limits and rollback. SQL, API and web are published.
[Pokepast.es verification](../work-in-progress/public-pokepaste-format.md)
retains the renderer evidence and the limit on artificial external tests.
That historical release deployed 001-080; the current baseline is 081 as recorded above.

Sprite follow-up (2026-11-04): **PUBLISHED / VERIFIED**. Continue from the tip
of `origin/codex/gourgeist-sprite-forms` (base `85d99d4`), fix `1ab6cdb`.
[Gourgeist/Pumpkaboo record](../work-in-progress/gourgeist-sprite.md): missing
size-form catalog entries and assets; web `babf0ab2` at 100%, 29 specific
tests/build and local + hosted browser verification PASS (synthetic team,
actual published images). API `adfca5c4` unchanged. No SQL/save/League,
Team Lock, Showdown or Pokepast.es change. Previous enrollment authentication
limits remain in its own record; they are not reclassified by this visual fix.

Focused continuation (2026-11-04): continue from the tip of
`origin/codex/home-points-followup`, base `3f64ba3`, deployed fix `e57fe2c`.
[Home/points/Discord record](../work-in-progress/focused-home-points.md): small
web fixes PUBLISHED / VERIFIED, web `4f46cbcb` at 100%, 50 web / 9 API tests,
build and one local + one hosted synthetic browser test PASS. Samu and Iker
both await their own baseline confirmation (0/0/0 and 3/0/3); no data correction.
Discord per-version announcements require a new migration and are stopped
under the owner's explicit no-migration boundary. No worker/API/SQL change.

Robar y Revivir (2026-11-09, PUBLISHED): DB 001-085 (085 = `20261109203241`), API
`909765eb`, verifier `39181f7f` (image rebuilt, same 60 s cycle), web `6da892d5`, Launcher
0.26.13. Open to every valid participant, no Team Lock or matchday; the engineering
allowlist variable is gone. Global robbery round in SQL (`robbery_open_victims`,
`api_robbery_board`): a victim counts from the verifier's adjudication, trainers who cannot
be robbed do not block the round. `revive` is a coordinated production mutation over the
participant's dead box (Caja 7). No real robbery or revive has happened yet. Continue from
the tip of `claude/net-friendship-discord`. Live record:
[Robar y Revivir](../work-in-progress/robar-revivir.md).

Launcher sync incident (2026-11-10, PUBLISHED, API only): `bdff9a8`, API `4af3e38a`
(rollback `909765eb`). A row accepted for a season discarded later wedged the FIFO
`trusted_save_outbox`: receipt 200, readback 404, reported as offline, so newer League and
personal copies never went up. The receipt now answers 404 for a discarded season and
installed Launchers close the row. "Víctor" has no production record; ByVisan02 is an
inference awaiting the owner. Live confirmation pending. Record:
[discarded-season sync](../work-in-progress/launcher-discarded-season-sync.md).

Normativa (2026-11-09): static rulebook at `/normativa`, content in
`web/src/features/normativa-content.ts`. A rule change is an edit there, its
`rulebookUpdated` date and a web deploy. Revivir and Robar are shown as available
since the 085 release.

Avisos detector v2 (2026-11-09): object notices cover only competitive and breeding
gear (`WATCHED_ITEMS` in `app/domain/save_audit.py`, owner decision), from one unit,
over total possession (bag plus every Pokémon's held item).

Administración › Avisos (2026-11-08): successive-save comparison on its own worker
after each accepted sync; it never writes a save, blocks or sanctions. Release tools
pin DEPLOYED ≤084 with nothing pending. The native reader gained a read-only
`--audit-snapshot` mode (server side; the Launcher does not call it).

NET/Felicidad/Discord (2026-11-05): see the live record above. 082 replaces only
`league_death_totals`; 083 adds an immutable per-confirmation table and outbox row
and drops the 067 edit trigger. Fresh backup rehearsal 19/19, both applied once;
release tools now pin DEPLOYED ≤083 with nothing pending. Trainer data are valid
as recorded (owner instruction): never question or alter them.

Latest owner clarification (2026-11-04): players must not confirm death history
to obtain observable points. Continue from `codex/automatic-observed-points`
(base `87d56b7`). [Automatic points record](../work-in-progress/automatic-observed-points.md)
contains the one-function SQL proposal, tested automatic 0/-0.3 results,
prepared web removal of confirmation controls and SQL authorization boundary.
Owner subsequently authorized SQL + web with si. Release completed: 081
`20261104165722`, web `0eef4feb` at 100%, actual observed NET Samu 0 / Iker -0.3.
Fresh backup/rehearsal 17/17 and focused SQL 13 PASS; 104 data tables unchanged.
No pending migration. Do not repeat any player-confirmation instruction.
Do not repeat the superseded player-confirmation instructions.

The live handoff is the single maintained operational record for an active phase.
Other documents link to it instead of maintaining competing live Git, test or
staging snapshots. Reports retain dated evidence; checkpoints retain explicitly
labelled historical milestones. Documentation never replaces verification.
The 8L contract and delivery report cover the existing technical report material;
do not create a second report containing the same information.

All rules below apply equally to ChatGPT, Codex, Gemini, Antigravity and future
agents. The named sections describe continuity, not different quality standards
or a division of responsibility. The current user instruction controls task scope:
an audit or documentation-only request does not authorize implementation or staging.

## Purpose

This document defines how multiple AI systems (ChatGPT, Codex, Gemini,
Antigravity or future agents) must work on PokeApp.

The objective is not to create a team where one AI abandons unfinished
work for another.

The objective is:

> One developer. Multiple AI instances. Shared memory.

When an AI changes, responsibility does not change. The next AI
continues as the same developer.

------------------------------------------------------------------------

# SECTION A --- CODEX MODE

## Context

PokeApp 2.0 is a long-term project developed with multiple AI systems.

Read the [checkpoint](../project-checkpoint.md) to locate the active phase, then
read its live handoff, contract and delivery evidence. Do not maintain a second
phase-status snapshot in this protocol.

Do not assume previous reports are correct.

Your first responsibility is auditing reality.

------------------------------------------------------------------------

## Codex workflow

Before continuing:

1.  Read project documentation.
2.  Check Git status and commits.
3.  Inspect actual code.
4.  Verify migrations.
5.  Verify relevant test evidence; run checks justified by changes or uncertainty
    within the current task's scope. A documentation-only update needs document
    checks, not a database rebuild.
6.  Compare documentation with reality.

------------------------------------------------------------------------

## Phase audit

Verify:

### Implementation

-   Endpoints.
-   Services.
-   Database contracts.
-   Permissions.
-   Certification logic.
-   Hall logic.

### Tests

-   Real passing tests.
-   No skipped validations.
-   Compile checks.

### Database

-   Migration state.
-   Schema consistency.
-   Security.

### Git

-   Commits.
-   Push state.
-   Uncommitted changes.
-   Protected files.

### Staging

-   Remote migration status.
-   Pending validations.
-   Possible blockers.

------------------------------------------------------------------------

## Codex objective

Do not preserve previous AI mistakes.

Find problems, explain them, and improve the project.

Report: - problem; - impact; - cause; - solution.

------------------------------------------------------------------------

# SECTION B --- GEMINI / ANTIGRAVITY MODE

## Working philosophy

You are the current developer.

You are not preparing work for another AI.

Other AI systems may have worked before you, but you inherit full
responsibility.

Correct workflow:

AI A works.

AI A reaches quota limit.

AI A documents state.

AI B continues.

AI B reviews previous work.

AI B fixes issues.

AI B completes the phase.

------------------------------------------------------------------------

## Never think:

Wrong: "Another AI will finish this."

Wrong: "I only need to prepare the next handoff."

Correct: "I need to understand, validate and finish the current work."

------------------------------------------------------------------------

# Documentation rules

Documentation is memory, not authority.

Choose evidence according to the question; there is no universal ordering that
makes a Git commit proof of a deployment or a passing test proof of product intent:

| Question | Evidence to verify |
|---|---|
| Repository contents and publication | Actual files, working-tree diff, commits and remote refs |
| Implemented behavior | Actual code and reproducible tests tied to that source and environment |
| Applied migrations and deployed behavior | The identified remote project's migration history, schema, grants and real validation |
| Intended behavior and allowed scope | Current user instructions and the approved product contract |

Contemporaneous, directly verified evidence overrides stale reports and chat for
observed facts. A code defect does not supersede an approved product rule. If
evidence conflicts or cannot be checked, record the uncertainty and investigate;
do not silently turn a previous report into a current PASS.

If documentation differs from reality, investigate and correct.

------------------------------------------------------------------------

# Required documentation

For important phases maintain:

## Technical report

Contains: - objective; - implementation; - decisions; - files changed; -
problems; - solutions; - tests; - limitations.

## Live handoff

Contains: - current state; - completed work; - pending work; -
blockers; - next action.

The live handoff is not permission to abandon unfinished work.

## Evidence and resumption rules

- Record the observation date, source commit, relevant uncommitted changes,
  environment, command, result/exit code and evidence location for each validation.
  Mark missing provenance explicitly. Preserve a useful result summary in the
  report even if raw logs are temporary or unavailable in another checkout.
- Distinguish VERIFIED, HISTORICAL/REPORTED and UNKNOWN. An unknown remote state
  is not evidence that a migration is absent. Use `STAGING_UNVERIFIED` until
  preflight establishes one of the master's verified staging states.
- Record active processes/run IDs, fixture prefixes and incomplete operations;
  use UNKNOWN if not inspected. Check their outcomes before retrying work after
  interruption. Never reapply a migration just because a prior reply is missing.
- Discover available tools in the current session. A model name does not imply
  access to Supabase MCP or any other capability. Report actual limitations
  without assigning unfinished work to a named replacement AI.
- Before authorized staging writes, verify the pinned project, migration history,
  committed migration source, fresh baseline and Advisor inventory. Follow the
  master's staging procedure; never infer these checks from an old handoff.
- Use relative repository links. Keep continuity documents versioned when a
  coherent documentation change is committed; until then list them as local and
  uncommitted. Do not assume another checkout has received them. Exclude protected
  files from reading, staging, moving or cleanup.

------------------------------------------------------------------------

# Token limit protocol

When approaching quota limits:

Do not simply stop.

Document:

-   exact current state;
-   completed work;
-   unfinished work;
-   errors;
-   tests;
-   commands;
-   next action.

The next AI continues as the same developer.

------------------------------------------------------------------------

# Phase completion standard

A phase is DONE only when:

-   implementation is complete;
-   tests pass;
-   database is validated;
-   security is checked;
-   documentation is updated;
-   Git is correct;
-   staging is validated when required.

------------------------------------------------------------------------

# PokeApp principles

Prioritize:

-   reliability;
-   explicit contracts;
-   safe migrations;
-   reproducible tests;
-   traceability.

Avoid:

-   inventing requirements;
-   bypassing validation;
-   hiding failures;
-   trusting previous work blindly.

------------------------------------------------------------------------

# Final principle

Different AI models.

Same developer.

Same responsibility.

Same quality standard.

The goal is continuity, not handoff.
