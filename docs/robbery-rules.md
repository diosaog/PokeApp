# Robbery rules — canonical (8F.1/025) and owner decisions of 2026-10-26

Operational specification. "Implemented" means verified in code and tests;
everything else is an approved contract awaiting its own packet.

## Canonical rules (unchanged, enforced)

1. Robber: enabled trainer and active participant.
2. Victim: another active participant of the same season; never oneself.
3. Robber owns a valid, pending robbery purchase (quantity 1).
4. Target: live, current, unambiguous identity; never Box 8 (dead).
5. Not BLINDADO; never a Pokémon already flagged ROBADO.
6. Not a victim already marked ROBADO in the current cycle; the cycle resets once
   every active trainer has been robbed; history is kept.
7. The stolen Pokémon keeps its OT, UUID and history, and receives ROBADO and
   BLINDADO; the robber receives the robbery shield voucher exactly once.
8. Coins are charged at purchase only; the purchase is consumed exactly once,
   at authorized competitive finalization. No matchday or daily limits.
9. Flags ROBADO, BLINDADO and REVIVIDO display together when compatible; a
   Pokémon shielded before dying keeps the flag, and a dead Pokémon cannot be
   newly shielded.

## Owner decisions

**A. Team Pokémon can be stolen.** Status: **implemented and validated
locally (Phase26B).** Origin: party slots 1–6 or boxes 1–7; destination: first
free box slot. PKHeX compaction (later members move up, count − 1), the last
team member is never taken (`LAST_PARTY_MEMBER`), and only own-OT origins with a
unique identity qualify (clones and foreign OT are refused). Additive local
`060_transfer_party_origin.sql` widens the reservation scope only.

**B. Cross-title robbery is prohibited — definitive product rule.** Status:
**enforced at reservation (27A)** — `api_prepare_transfer` refuses different
titles (`TRANSFER_CROSS_TITLE_FORBIDDEN`) before any work, adjudication rechecks
it, and the native planner still refuses it; no conversion will be built.

**C. No victim consent; PokeApp is the authority.** Status: **implemented and
validated locally (Phase27A, migration 061).** The victim has no accept, refuse
or cancel control anywhere; only the requester may withdraw, and only before the
decision (`TRANSFER_ADJUDICATED` afterwards, for everybody).

## Definitive contract (27A)

Two things are never conflated:

- **Competitive decision** — taken once by the restricted verifier from the
  server-held accepted saves of both trainers (no Launcher, no physical proof):
  purchase consumed, canonical 025 effects (ROBADO/BLINDADO, voucher, robbery
  cycle), ownership switched to the robber, provenance recorded. Final from then
  on; the victim's absence or refusal cannot undo it.
- **Physical obligation per side** — each save is changed only by its own
  Launcher through the safe engine, and settled only by an independently verified
  artifact (or, for the victim, a verified absence).

### States and transitions

Overall (`transfer_state`):

| State | Meaning | Next |
| --- | --- | --- |
| `REQUESTED` | reservation created, nothing decided | `ELIGIBILITY_VERIFIED`, `CANCELLED` (requester) |
| `ELIGIBILITY_VERIFIED` | both plans derived from accepted saves | `COMPETITIVELY_ADJUDICATED`, `CANCELLED` (requester) |
| `COMPETITIVELY_ADJUDICATED` | decided; physical delivery pending on one or both sides | `RECONCILED`, `BLOCKED_UNCERTAIN` |
| `RECONCILED` | both sides settled; terminal | — |
| `BLOCKED_UNCERTAIN` | a side has an incident; decision unchanged | assisted recovery |
| `CANCELLED` | withdrawn before the decision; nothing consumed | — |

Per side (`transfer_obligation`), after the decision:

| Victim (`DONOR_…`) / robber (`RECIPIENT_…`) | Meaning |
| --- | --- |
| `PHYSICAL_PENDING` | waiting for this Launcher (emulator closed) |
| `RECOVERY_REQUIRED` | the current file could not be planned (e.g. full boxes, unreadable); the Launcher may offer it again |
| `VERIFIED` | verified artifact registered as this trainer's accepted save; trainer released |
| `ABSENT_VERIFIED` (victim only) | the victim's current file was proven not to hold the Pokémon and was accepted as is |
| `BLOCKED_UNCERTAIN` | ambiguous identity or another trainer's save; evidence kept, assisted |

The pre-27A states (`PREPARING` … `BOTH_VERIFIED_PENDING_IDENTITY`, `COMMITTED`)
remain readable for history only; the two-proof finalization is superseded and
refused by SQL.

### Mandatory sync (victim)

While the victim's side is pending, the server refuses the victim's ordinary
sync (`transfer_reconciliation_required`) and any team lock
(`transfer_removal_pending`); a save that still holds another trainer's Pokémon
in the party can never be locked (`team_contains_robbed_pokemon`). The Launcher
shows the obligation first, pauses ordinary sync and offers only «Aplicar
retirada obligatoria» (emulator closed). Then:

1. File equals the decided plan's source: verified backup, explicit confirm,
   native removal, upload, independent proof, registration.
2. File moved on (played, older copy, edited elsewhere, or a rejected attempt):
   the Launcher uploads its **current** bytes without changing anything; the
   verifier locates the robbed identity by its immutable evidence and re-plans on
   those bytes (new plan id), or accepts the file when the Pokémon is no longer
   there, or blocks (ambiguous/another save).
3. Restart during the removal: the engine journal decides (applied → upload;
   rejected with the original intact → fresh plan); never a guess.

An offline computer is never changed remotely: until its sync the victim's file
still physically holds the Pokémon, and that copy is competitively invalid.

### Delivery to the robber

The robber's insertion always uses the **victim's canonical accepted save** (the
bytes the decision was taken on): same PID/EC, OT, UUID entity, attributes and
history. A victim upload is never a source of Pokémon bytes. If the robber's own
file moved on, it is re-planned on the robber's current bytes with the same
canonical Pokémon. Until `RECIPIENT_VERIFIED` the Pokémon belongs to the robber
competitively but is not physically available, and it cannot be fielded (the
robber's accepted save does not contain it).

### Guarantees

Exactly once: decision, consumption, flags and voucher (idempotent verifier,
`adjudicated_at` set once, canonical 025 idempotency key); each proof and
registration once (lost replies are no-ops). No clone: the robbed identity can
only be bound to the robber; a kept victim copy is AMBIGUOUS and never
fieldable. No loss: originals are backed up before any change; the robber
receives verified canonical bytes. Two concurrent robberies on the same trainers
or Pokémon are refused (`TRANSFER_RESERVED`); a trainer is released as soon as
their own side is settled.

Foreign-OT origins stay **restricted** (only own-OT, unique identities are
robbable); a received Pokémon is proven for its new owner through provenance.
