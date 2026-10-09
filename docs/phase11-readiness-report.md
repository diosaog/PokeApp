# Phase 11 — migration readiness checkpoint

Historical checkpoint. On 2026-10-09 the owner confirmed/reactivated V1 and raw
remote capture succeeded. The [source inventory](phase11-source-inventory.md)
and [live handoff](work-in-progress/phase11-live-handoff.md) supersede the access
blocker below; this dated evidence is retained unchanged.

2026-10-08. **STATUS: PHASE 11 BLOCKED — READINESS.**
**ENTRY CHECK: PHASE 10.5 DONE VERIFIED.** This records discovery, not a completed
data migration. [Live handoff](work-in-progress/phase11-live-handoff.md),
[sanitized evidence](phase11-readiness-evidence.json).

## Entry and destination

Entry main/origin `e256d5b28f751beb7c3851e58b1eb7c9c81ed8fb`, freshly fetched 0/0,
clean tracked tree. The owner explicitly authorized real migration after 10.5;
historical Phase 6 documentation about a clean-start strategy is superseded for
Phase 11. V1 must remain intact and no cutover is included.

Fresh V2 observation pins `uwleqeuzsveqlugugzba`, ACTIVE_HEALTHY, 33 migration
records through **041 = `20261008204133`**. All 59 full public/Auth/Storage table
count/hash records equal the independent final 10.5 baseline. All migration
records and separate stable owner identity/credential hashes also match. Owner
admin/enabled identity and three manual seasons are preserved, including the
active season `c6bcac5b-0b89-403f-8242-41ac58286ade`.

Fresh deployment metadata at 20:59 UTC:

- Railway `2d71ec3b-095d-49a7-aa15-31749fe67b52`, SUCCESS, PokeApp V2 /
  production / pokeapp-api; image
  `sha256:fc59ebcab95dfab6cf4eee72a962dc22f06744a0c6beafb8ebbe984fd2f461e3`.
- Cloudflare `ea9c837d-86f0-4b0a-826d-a4774371b56e`, version
  `77eea9f6-0c90-45a2-b93a-3bf9cdf5fc11`, 100%.
- Both identify source `eb4e402891cbaa02e0999229874ac3003e016ae0`.
  No deployment, restart or migration was performed.

## Source discovery and blocking evidence

The tracked V1 runtime uses raw `settings`, `saves`, `purchases`, `shop_discounts`,
`team_locks`, `redemptions`, `pokemon_flags` and a configured Storage bucket
(default `saves`). Most competitive domains are settings JSON, with independent
archives. Runtime configuration accepts Supabase environment/Streamlit secrets.
No V1 Supabase connection was found in current local configuration, global
Streamlit secrets or process/User/Machine environment. V2 credentials are present
and must not be mistaken for V1.

The accessible account's only other project is `fdtytpeyfzyssfrsulxd`, named
`diosaog's Project`, eu-north-1, created 2025-12-09, **INACTIVE**. Whether it is V1
is unproven. Management metadata GET succeeded, but a read-only catalog query
returned **HTTP 544 / connection timeout**. No schema/data inventory could be
obtained from that project. The historical `pokeapp.streamlit.app` URL redirects
to Streamlit authentication; this does not establish its database connection.

The local SQLite fallback has 12 settings, 21 save rows and 21 local save files,
10 redemptions, zero purchases, zero Team Locks, zero Pokémon flags and zero
promotions. Latest save timestamp: **2025-12-09T13:35:51Z**. All ten redemptions
lack their purchase in this local database. Its source authority and completeness
are unverified. These are local-copy observations, not a claim about remote V1.
No raw source data, PINs, keys or credential hashes are published in this report.

**Required unblock:** identify the authoritative V1 project and restore its read
access, or identify an accessible authoritative export. The owner was asked this
specific question. No routine implementation approval is needed afterward.

## Mapping findings retained for resumption

The review located contracts; it did not invent mappings for unavailable records.
Use raw source exports: `storage.py` can fall back to SQLite and
`app/liga/state.py::restore_state` can write sanitized state while reading.
Existing legacy adapters are forgiving UI adapters, not strict import validators.

| Area                  | Established boundary; verify against actual source after access                                                                                                                                                                                                             |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Identity and journal  | No V1 business import journal/id-map exists in 001–041 or the live catalog. Launcher journal and ordinary mutation receipts serve different purposes. Use stable source identities, strict collision handling and atomic import receipts; no fuzzy owner/PIN merge.         |
| Season lifecycle      | V2 has one active season and the owner's manual season is active. If a distinct active V1 season exists, preserve both truths and resolve placement before a relational import; do not relabel either season or remove the invariant silently.                              |
| Rules and economy     | V1 configuration versions and frozen rewards take precedence over current rules. Displayed V1 balance may be clamped or blocked; it is not a proven opening ledger balance. Use exact decimals, reconcile earnings/spending/sanctions, and do not invent balancing entries. |
| Progress and revives  | Raw legacy counters are not trusted modern observations. Unknown stays unknown; a completion reward claim is not proof of Champion defeat. Reconcile visible deaths, purchased revives and wipe counts without duplicating a death or payout.                               |
| Team Lock timing      | Legacy upserts replace timestamps and can contain sentinel deadlines. Migration 041's ordinary insert triggers create first-event evidence; importing through them naively would fabricate timing. Preserve only proven original timing.                                    |
| Save promotion        | Migration 039's current-save update/normal reconciliation path can settle rewards. Migration must avoid retroactive or duplicate payouts; do not run ordinary observation mutation commands as import helpers.                                                              |
| Frozen history        | Modern GENERAL requires schema-2 snapshots with supported provenance. Preserve raw official legacy snapshots; never derive missing frozen facts from current saves. Hall/archive retain a legacy provenance branch, distinct from modern certification.                     |
| Cup and championship  | Legacy Cup formats have an explicit old-rules branch. Do not convert brackets, alphabetic legacy championship decisions or historical Hall into invented modern certificates; retain their historical provenance.                                                           |
| Inventory and Pokémon | Zero-price legacy gifts may lack mandatory modern reward provenance. Legacy fingerprints may be ambiguous. Quarantine unsupported facts instead of inventing paid prices, modern reward origins or Pokémon identity.                                                        |

These are **conditional mapping constraints**, not asserted conflicts or quarantined
remote records. Actual source inventory is still required before choosing a new
forward migration, helper design or economic reconstruction contract.

## Effects, validation and next step

**Imported entities: zero. New migrations/helpers: none. Identity map: not created.**
No remote business writes, fixtures, Storage writes, trigger suppression, privilege
changes, source restoration or cutover occurred. No interrupted/unknown import
command exists to replay. Phase 11 tooling and restart/failure-injection proof have
not been implemented; neither can be reported PASS. Economy, progress, revive,
Team Lock, Cup, championship and Hall equivalence remain **NOT VALIDATED**.

Fresh Advisor has 24 ERROR / 5 WARN / 143 INFO; the comparison with final 10.5
retains the same ERROR/WARN findings. Existing RLS/grants were not modified.
No Python/React/parser/browser/PostgreSQL suite was rerun for this documentation-only
checkpoint. Only read-only entry checks and documentation validation were needed.
Prior 10.5 tests remain historical evidence, not Phase 11 migration proof.

Changed files are this report, sanitized readiness evidence, the Phase 11 live
handoff and navigation/status references in checkpoint, continuity, closed 10.5
handoff and Supabase documentation. Protected/unrelated files remain untouched.
This checkpoint's exact documentation commit is obtained from Git; application
source and deployed source remain unchanged.

**PHASE 12 READINESS: NOT READY.** First resume source identification/access, then
raw capture and strict mapping, local deterministic restart/rollback rehearsal,
fresh remote baselines, atomic imports and reconciliation. Phase 12 Shadow follows
only a genuinely completed Phase 11 and remains **NOT STARTED**.
