# Phase26B — complete robberies (PARTIAL)

2026-10-26. **PHASE26B PARTIAL. Production UNCHANGED; physical writes OFF.**
Entry `f300c8b`. Rules: [robbery-rules.md](robbery-rules.md).

## 26A closure (real Pokémon Y, isolated Lime3DS)

Owner check PASS. Re-read of the copy he used: in-game save at 01:23, SHA-256
`e9d13c65…`, **Heart Scale 7, Rare Candy 8, Bagon Lv 12** (was 10/Lv 10);
Bagon's identity is byte-identical and only its level changed, Zygarde and Keldeo
identical — consistent with 2 Rare Candies used in game, i.e. the added items were
real, usable and persisted. Original `c0e666e7…` unchanged; journal: both
operations `APPLIED_VERIFIED`, original backup verified. **Certified: Pokémon Y
inventory read/write/persistence in Lime3DS.** Not certified: revive, real
two-player robberies, Windows 10, release.

## Block B — team robbery: PASS (local)

- Native `NativeTransfer`: party origin with PKHeX compaction; exact checks that
  earlier members are identical, later ones shifted by one, boxes identical, the
  individual gone, and only the party block, its checksum and the Gen7 signature
  changed. **500 native checks across X/Y/OR/AS/SN/MN/US/UM** (every position up
  to 6), last member, full destination, clone/foreign-OT, cross-title, stale and
  tampered output refused. Box path regression: 168 + 8 PASS.
- Server: verifier derives party plans; local `060` widens the reservation.
- **Disposable PostgreSQL + native + two Launcher journals, X from party slot 2:
  12/12 PASS** (reservation, plans, independent proofs, atomic owner/save/
  identity/025 effects once, injected failure rollback, concurrent finalizers,
  replay, later sync, retired-donor clone blocked, pre-apply cancellation,
  060 bootstrap parity). Box-origin regression 11/11 PASS.

## Block C — server authority without victim cooperation: PARTIAL

Implemented: the victim cannot cancel or refuse (409, web and Launcher), no
accept button anywhere, cross-title refused. **Not implemented:** competitive
finalization still waits for both physical proofs, so an absent victim leaves the
robbery pending (nothing duplicated or lost, nothing completed). The exact unit is
in robbery-rules.md: decoupled finalization with per-side obligations, victim
uploads containing the robbed entity never credited and rejected in team locks,
mandatory removal at Launcher start, robber insertion from server-held bytes,
and tests for offline victims, external edits, restarts, lost replies and
concurrent robberies.

| Gate | Result |
| --- | --- |
| REAL LIME3DS INVENTORY CERTIFICATION | PASS (Pokémon Y) |
| PARTY POKÉMON ROBBERY | PASS (local) |
| BOX POKÉMON ROBBERY | PASS |
| SAME-TITLE RESTRICTION | PASS |
| SERVER-AUTHORITATIVE ROBBERY | PARTIAL |
| NON-COOPERATIVE VICTIM | PARTIAL (veto refused; completion still needs the victim) |
| MANDATORY SYNC | PARTIAL (not implemented) |
| EXACTLY-ONCE REDEMPTION | PASS (current contract) |
| FOREIGN-OT/UUID PRESERVATION | PASS |
| PHYSICAL VERIFICATION | PASS |
| TWO-SAVE RECOVERY | PASS (current contract) |
| WEB/LAUNCHER INTEGRATION | PARTIAL (party shown; new states pending block C) |
| PROD PHYSICAL WRITES | DISABLED |
| PHASE26B | PARTIAL |
