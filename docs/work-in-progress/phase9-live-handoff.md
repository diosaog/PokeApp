# Phase 9 — live handoff

Updated: 2026-09-28. **IN PROGRESS**.
Follow [continuity](../AI/PokeApp_Multi_AI_Continuity_Protocol.md),
[contract](../phase9-parser-launcher.md), [checkpoint](../project-checkpoint.md).

Entry main/remote: `30d670a50a990b92d37620d90290463e594dcd78`, 0/0, tracked clean.
Only expected untracked file is the protected guide; never read/stage/change it.
No Phase 8 audit/reopening. 8L DONE and approved Phase 8 backend CLOSED.

Bounded entry audit completed: reusable private DTOs, identity evidence/reconciliation,
Team Lock snapshot isolation and auth routes. Legacy bridge includes mutations and
mtime-only caches: reference only. Ignored Electron prototype wraps Streamlit and
has no Companion core. New isolated read-only parser process + UI-free Python core.
Current uncommitted work: Phase 9 contract/handoff and subsequent implementation.

Tool setup: existing .dotnet-sdk has an incomplete SDK; portable official SDK 8
downloaded with verified official SHA512 under %TEMP%/pokeapp-phase9-tools/dotnet.
SDK 8.0.425 and tagged source ready; no package/binary added to Git.
Parser block VERIFIED: 12 Python tests pass (exit 0), .NET 24 generated-save
checks pass (exit 0), real Python subprocess + DTO integration Gen3/4/5 pass.
Source: entry HEAD plus parser/docs/tests diff in the first Phase 9 commit.
Commands: unit runner --pattern test_phase9_parser.py; dotnet run --project
companion/parser/PokeApp.Parser.Checks -c Release -- <temporary fixtures folder>.
Windows discrepancy found/fixed: stat(path).ctime differs from fstat(handle).ctime;
compare size/mtime/device/inode plus content hashes instead. No weakened hash check.

Next: implement discovery/config, local durable sync and queue, session/auth,
backup/write refusal, CLI composition and focused/final gates. Full Python regression
is pending until the complete base is stable. No known failing checks.
No backend ingestion/current promotion: 023 requires trusted capture provenance.
No migration 033; no remote actions. Historical 031=`20260928110301`,
032=`20260928111840`: **DO NOT REAPPLY**. Staging untouched by Phase 9;
last verified 8L evidence remains in its closed report.
