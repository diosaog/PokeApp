# PokeApp Multi-AI Continuity Protocol

Canonical path: `docs/AI/PokeApp_Multi_AI_Continuity_Protocol.md`.
Reconciled: 2026-09-26. Keep one copy at this path.

## Shared memory map

| Question | Maintained source |
|---|---|
| How do AI instances continue the same work? | This protocol |
| What are the project-wide constraints and roadmap? | [Master protocol](../PokeApp_2.0_Protocolo_Maestro_MultiIA.md) |
| Which phase is active and where is its memory? | [Project checkpoint](../project-checkpoint.md) |
| What is the current operational state and next action? | The active phase's live handoff; currently [Phase 8L](../work-in-progress/phase8l-live-handoff.md) |
| What behavior was approved? | The phase contract; currently [Cup engine](../phase8l-cup-engine.md) |
| What was implemented and what evidence exists? | The phase technical/delivery report; currently [8L report](../phase8l-completion-report.md) |

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
