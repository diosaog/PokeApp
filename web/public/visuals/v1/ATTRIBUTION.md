# PokeApp visual sources

Pokémon and image contents belong to Nintendo / Game Freak / The Pokémon Company.
This fan application is not endorsed by them. Repository distribution terms do
not transfer Pokémon trademark or image ownership.

- Pokémon front images: pinned PokeAPI/sprites, original Black/White images for
  1–649, original X/Y renders for 650–721. No community-created Gen6 pixel sprites.
- Additional 722–807 images and 16 explicitly mapped alternate forms use the same
  pinned repository's default sprites. Per-file upstream URLs/hashes are recorded
  in the manifest; no new external runtime dependency. Form indices follow
  [PKHeX 24.11.11 FormConverter](https://github.com/kwsch/PKHeX/blob/24.11.11/PKHeX.Core/PKM/Util/Conversion/FormConverter.cs).
  Unsupported forms retain an explicit placeholder, never an invented base form.
- Items: the same pinned repository, resolved by explicit Gen6 game indices,
  not by assuming PokeAPI item IDs equal game item IDs. Missing images fall back.
- Physical/Special/Status: canonical Gen6 game icons from the Showdown sprite
  repository. Its README is retained; community art requiring prior permission
  is not included. Source: https://github.com/smogon/sprites.
- Move reference: pinned PokeAPI CSV, exact version-group 15 Spanish flavor text
  and X/Y mechanics with later changes reversed. Display explicitly says X/Y;
  it is not the source team's game or competitive authority. License retained.
- Type symbols: existing `assets/types`, sourced from WikiDex's type sprite
  collection under the repository's recorded CC BY-SA 3.0 attribution:
  https://www.wikidex.net/wiki/Categor%C3%ADa:Sprites_de_tipos.
  https://creativecommons.org/licenses/by-sa/3.0/ . Unmodified.
- Trainer photos, Sinnoh medals and custom shop icons: existing PokeApp project
  assets. Photo lookup matches established trainer names; no synthetic identities.

Exact pinned commits, source paths and content hashes: `manifest.json`.
Reproduce with `tools/build_product_assets.py`. `--resume` reuses files from an
interrupted download. Assets are served locally, individually and lazily;
no runtime third-party request or giant spritesheet is needed.
After the base build, run `python -m tools.build_sprite_variants` to reproduce
the Gen7/form extension and `web/src/pokemon/visual-forms.json`.
