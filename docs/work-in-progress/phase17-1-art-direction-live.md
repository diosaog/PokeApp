# Phase 17.1 - art direction

- STATUS: VALIDATED / PUBLICATION PENDING
- HEAD: entry `53e72d3c5d881e1294d4ccff9788700c87493739`, fetched main/origin 0/0.
- DONE: all requested screens; 11 section accents/motifs, inline type moves,
  horizontal Pokemon detail, IV bars, 50 game badge assets and centered PC frame.
- CURRENT SCREEN: final visual review complete; prepare committed web delivery.
- NEXT SCREEN: production read-only smoke, exact assets and documentation closure.
- EXPLICIT OWNER CHANGES: per-tab accents/motifs; readable type moves with inline
  expansion; no scene/banner; horizontal detail; IV bars; no normal EV display;
  correct game badges; centered PC navigation and terminal frame.
- AUTONOMOUS ARTISTIC CHANGES:
  - Shared blue-black surfaces/backdrop replace the global green wash so section
    accents remain distinct; isolated in `web/src/art-direction.css` for review/revert.
  - Active navigation gets an inset section-color marker; all pages keep the same
    card geometry, control hierarchy and short focus/hover feedback.
  - Trainer photos get quiet frames; stat columns get separators; trainer cards
    get a short top accent line to strengthen identity without adding banners.
  - Shop item tiles use violet depth and inventory cards a slim left rule; prices
    retain gold so currency remains immediately recognizable.
  - Home's existing functional battle card gets a warm gradient; Hall gets a soft
    gold spotlight/photo frames; Cup gets restrained round borders; Liga totals
    get championship gold. No new components or sporting meanings introduced.
  - Admin uses slate fieldsets, neutral secondary actions and retained warning
    colors; Save uses faint scanlines. No technical data was newly exposed.
  - Inline move opening uses a 140ms fade and only one open disclosure; reduced
    motion removes animation. No scenery or new decorative page banners.
- TESTS VALID: 24 focused React PASS; 22 unique affected Edge cases PASS (19
  journeys + 3 art/contrast tests); five screenshot cases refreshed after the
  final CSS correction. TS/public build, format, dry-run, asset parity, compile,
  targeted Ruff and diff pass. Desktop 1440, intermediate 900 and mobile 390
  reviewed. Move names/PP pass 4.5:1 for all 18 types plus unknown.
- VISUAL ISSUES REMAINING: none blocking; Antonio retains final aesthetic review.
  Missing game context cannot choose Unova variant or fabricate badge evidence;
  X/Y artwork is prepared but competitive progress remains unsupported/unknown.
- DO NOT REPEAT: backend/PG/parser/Launcher or historical phases. No business,
  database, Storage or installer changes. Protected guide and unrelated files untouched.
