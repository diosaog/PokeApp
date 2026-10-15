# Spanish Pokémon names

`catalog.es.json` is a data-only export of the embedded English/Spanish resources
in **PKHeX.Core 24.11.11**, the same pinned version as the isolated save reader.
Upstream: https://github.com/kwsch/PKHeX; NuGet package license expression:
`GPL-3.0-or-later`. The lockfile pins the package content hash; the JSON records
SHA-256 for each original resource, preserving its array offsets/IDs. Resource
text remains unmodified. This module does not import PKHeX types into the web.
Only the currently supported Gen3–5/X/Y ranges are shipped; limits come from
the pinned save classes (plus 25 natures and types through Fairy), keeping later
game catalogs out of the initial web bundle.

From the repository root with a .NET 8-compatible SDK:

```powershell
dotnet restore tools/PokemonCatalog --locked-mode
dotnet run --project tools/PokemonCatalog --no-restore -- web/src/pokemon/catalog.es.json
```

There is no network lookup at render time. Regeneration does not read saves,
credentials or ignored `data/` caches. The generator detects each resource's BOM
(the Gen3 Spanish item resource is UTF-16); missing/mismatched resources fail.
The generated JSON is excluded from Prettier to keep reproduction byte exact.

`localization.ts` is the only runtime resolver. It supports stable IDs, current
numeric placeholder strings and canonical English/Spanish aliases, including
slug/case/accent variants. It never changes input DTOs, nickname text, ID-based
commands, rewards, history, or public/private field selection. Current views
still choose their original fields. No missing types, forms or abilities are
inferred from species, and private PC reads are not added to rival views.

Current API strings omit game context. Gen3 item IDs have a different namespace
from Gen4+ IDs: contradictory numeric mappings show **Objeto sin identificar
(falta el juego)**. Names such as `Leftovers` and unambiguous `Item #234` resolve
to **Restos**. The optional resolver context supports later explicit generation
information; current callers do not guess it. Unknown canonical names (including
forms and custom shop products) remain neutral text; unknown technical labels
show unavailable. Natures/types retain valid ID zero; species zero is not guessed
to be a Pokémon or egg observation.

These PKHeX resources contain names, **not descriptions**. Current Pokémon web
projections/components contain no move/ability/item-description field; no new
field is added just for localization. Existing Spanish PokeApp Shop descriptions
remain the server's product descriptions (not canonical in-game flavor text).
Ignored legacy flavor caches are sparse and permit cross-version fallback; their
`xy:` labels do not prove X/Y wording. They are deliberately not imported, and
no modern description is asserted for X/Y or Gen5.

The asset can later be consumed by desktop presentation, but Launcher 0.16.2,
its installer, and final desktop parity are unchanged/deferred.
