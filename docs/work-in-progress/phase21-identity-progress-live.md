# Phase 21 - identity and native progress

Observation 2026-10-20. **STATUS: SOURCE VALIDATED / NOT YET DEPLOYED.**

Entry and current published HEAD were `1c5e1a0e46af18c02e6739c9670efa12ef5b5ff7`, main/origin aligned. The implementation is locally validated and ready for a committed remote checkpoint.

Gen6/7 identity is season/trainer scoped and fail-closed for collisions, eggs, trade/incomplete origins, ambiguous clones and unsafe reappearances. Native progress is additive for eight titles: Gen6 Kalos badges and independent League/Hall/champion facts; Gen7 island progress and champion facts without fabricated badges. The server owns the read projection and React only renders it. Existing Gen3-5 reader/receipt behavior remains compatible.

Full Python: **916 PASS**. Focused identity/progress/API, compatibility, schema, React and browser gates pass. Native synthetic checks report **360 assertions PASS**; the native PostgreSQL projection gate passes. Fresh migration/bootstrap builds are identical at **54 public / 15 private tables**. Legacy identity SQL security gate passes 19 checks. Disposable databases were removed and PostgreSQL stopped.

Migrations `048_trusted_gen67_identity.sql` and `049_native_progress_read.sql` are syntactically and semantically validated locally. No production write, reward, owner mutation or deployment has occurred.

Gen6/7 rewards remain explicitly blocked as `pending_validation` / `pending_policy`; observations alone do not create awards or backfills. Gen7 does not claim gym badges. Frozen history, Team Locks, owner data, V1/Shadow and physical saves are untouched. Private native evidence remains under `%LOCALAPPDATA%/PokeApp-migration-evidence/phase21/20261018`.

## Next exact step

Commit and push the explicit source set. Then capture a fresh remote V2 migration/table/security baseline, apply only 048 and 049 once, deploy the compatible Railway API and Cloudflare web, perform read-only health/auth-denial and asset checks, compare preservation, and update this handoff to the final Phase 21 status. Do not start Phase 22.
