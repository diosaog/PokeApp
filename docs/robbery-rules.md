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

**A. Team Pokémon can be stolen.** Status: **PENDING implementation.** Today
only boxes 1–7 are qualified; a team target is refused with a clear message
(`TRANSFER_NATIVE_SCOPE_UNQUALIFIED`). Not to be presented as available.

**B. Cross-title robbery is prohibited — definitive product rule.** Status:
**enforced** — the native planner refuses different titles (8 cross-title
rejections proven); no conversion will be built. Next packet adds the early
same-title check at reservation so such a request is refused immediately.

**C. No victim consent; PokeApp is the authority.** Status: **contract approved,
implementation pending.** Implemented now: the victim has no accept/refuse/cancel
control in web or Launcher, and the API refuses a victim cancellation
(`TRANSFER_VICTIM_CANNOT_CANCEL`, web and Launcher leg route; proven on
PostgreSQL). Only the requester may withdraw, and only before any application.

### Contract for C (to implement)

States, never conflated:
- **Competitive decision** (server): the authorized robbery is final for
  ownership, flags, voucher and consumption once the server can derive both
  plans from the server-held accepted saves.
- **Physical transfer pending**: each Launcher still has an obligation.
- **Physical transfer verified**: per side, only with an independently verified
  artifact — never inferred.
- **Mandatory sync**: when the victim's Launcher is next online and the emulator
  is closed, it must apply the removal before any other write or sync.
- **Reconciliation incident**: the file changed elsewhere, cannot be planned or
  cannot be verified; blocked, materials kept, admin-assisted.

Guarantees: no duplication competitively (the server owns identity; a victim
upload still containing the Pokémon is not credited and cannot be used in team
locks); no loss (the robber's insertion uses the server-held bytes and is
verified); full traceability of both saves. An offline computer cannot be changed
remotely: until its mandatory sync the victim's file still physically contains
the Pokémon, and that copy is competitively invalid.

### Exact next technical unit

1. SQL: competitive finalization decoupled from the victim's physical proof
   (server decision + per-side obligations), reservation same-title check,
   victim-side sync gating limited to the robbed entity.
2. Ingestion/team locks: robbed entity in the victim's upload → pending-removal,
   never credited; team lock rejects it.
3. Launcher: mandatory removal at startup (blocks other writes/sync until done or
   escalated), robber insertion independent of the victim's proof.
4. Native: team-source plan (party extraction and compaction, destination first
   free box slot), qualified on the eight titles.
5. Tests: offline victim for days, victim edits elsewhere, both online, lost
   replies, restarts; no duplication or loss in any order.
