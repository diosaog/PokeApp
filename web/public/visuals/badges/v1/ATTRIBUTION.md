# Game badge artwork

Canonical Pokemon game badge images mirrored from
[PokeAPI/sprites](https://github.com/PokeAPI/sprites/tree/ba403973fdf9d0ac59175813861e6a1f8ed5020c/sprites/badges).
Original Pokemon imagery belongs to Nintendo / Creatures / GAME FREAK. This is
not commissioned or AI-generated artwork, and no ownership claim is made.
The upstream [licence notice](../../v1/POKEAPI-SPRITES-LICENCE.txt) is retained.
Each downloaded original has its exact source and SHA-256 in `manifest.json`.

IDs 1–8 Kanto; 9–16 Johto; 17–24 Hoenn; 25–32 Sinnoh; 33–42 the ten
distinct Unova badges; 43–50 Kalos. The upstream correction
`e1d237e02b8c0b385c644f184f26720909a82132` identifies Toxic=35 and Bolt=37.
BW uses 33,34,36,37,38,39,40,41; B2W2 uses 34,35,36,37,38,39,41,42.
UI indices mean the observed badge positions, not inferred chronological wins.
Johto's Kanto set remains separate. Hoenn art identifies the same badges for
RSE/ORAS; it is not represented as an ORAS-specific rendering. Kalos and ORAS
art lookup is presentation preparation only, not new parser/progress support.
Alola has trials, not these gym badges: no badge set is invented.

Unknown game variants or unsupported/mismatched contexts use the neutral fallback.
Unknown progress is visually and textually distinct from unearned badges.
Reproduce: `tools/build_badge_assets.py` using the project Python environment.
