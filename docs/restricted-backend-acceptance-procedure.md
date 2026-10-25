# Restricted backend acceptance — procedure (NOT executed)

Prepared in Phase26A. Every step below needs its own explicit owner
authorization; nothing here has been applied to any remote system.

1. **Baselines.** Record the remote migration history, a schema-only dump hash,
   public table row counts and grants, Storage buckets/policies, Auth settings and
   the running API/web versions. Confirm a restorable backup exists.
2. **Migrations 054–059, additive, in order.** Each file once, inside its own
   transaction. After each: compare the catalog against the local bootstrap parity
   result (`tools/validate_phase23_local.py` parity helper) and re-check that row
   counts of pre-existing tables are unchanged. 058/059 only add private tables,
   functions and wrappers; no client grant.
3. **Private verifier.** A separate container (not the API) running
   `tools/run_item_use_verifier.py`, plus a transfer runner built on
   `app/application/transfer_worker.py` (not yet shipped). Database login granted
   only `pokeapp_item_verifier`, `sslmode=verify-full`, secrets only in that
   service. Signed source reads from private Storage.
4. **Storage.** Private `raw-saves` bucket; result objects under `item-use/…`;
   signed URLs short-lived; no public listing.
5. **API flags, cohort only.** `POKEAPP_ITEM_VERIFICATION_TRANSPORT_ENABLED`
   and `POKEAPP_TRANSFER_ENGINEERING_ENABLED` with exact UUID cohorts of
   disposable, owner-authorized test trainers. Public users unaffected.
6. **Acceptance.** Disposable trainers and saves only: revive, quick items,
   two-save robbery (two real participants with their own Launchers), lost
   replies, restarts, tampering, cancellation; verify no effect outside the cohort.
7. **Rollback.** Disable the flags and stop the verifier (migrations are additive
   and are not reversed). Keep all evidence and backups.
8. **Then and only then** decide on public physical writes, after the Lime3DS
   certification and a signed Launcher release.
