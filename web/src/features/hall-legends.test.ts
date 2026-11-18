import { expect, it } from "vitest";
import { legendSprite, legends } from "./hall-legends";
import { catalogId } from "../pokemon/localization";
import formSprites from "../pokemon/visual-forms.json";

it("2026-11-18: in the Hall, a Pokémon holding its own Mega Stone is its Mega", () => {
  expect(legendSprite({ species: "Camerupt", item: "Cameruptite" })).toEqual({
    species: "Camerupt",
    item: "Cameruptite",
    form: 1,
    label: "Mega-Camerupt",
  });
  // Spanish item name, same stone.
  expect(legendSprite({ species: "Camerupt", item: "Cameruptita" }).form).toBe(
    1,
  );
  expect(
    legendSprite({ species: "Charizard", item: "Charizardite Y" }),
  ).toMatchObject({ form: 2, label: "Mega-Charizard Y" });
});

it("another species' stone, any other item or a Mega without art change nothing", () => {
  for (const pokemon of [
    { species: "Gyarados", item: "Cameruptite" },
    { species: "Camerupt", item: "Choice Band" },
    { species: "Camerupt" },
    // Mega Venusaur has no art in the app: never an unresolved image.
    { species: "Venusaur", item: "Venusaurite" },
    // An explicit form is kept as listed.
    { species: "Alakazam", form: 1, label: "Mega-Alakazam" },
  ])
    expect(legendSprite(pokemon)).toEqual(pokemon);
});

it("every legend resolves to known art: species, forms and held items", () => {
  for (const legend of legends)
    for (const title of legend.titles) {
      expect(title.team).toHaveLength(6);
      for (const listed of title.team) {
        const shown = legendSprite(listed);
        const id = catalogId("species", shown.species);
        expect(id, shown.species).not.toBeNull();
        if (shown.form)
          expect(`${id}:${shown.form}` in formSprites, shown.label).toBe(true);
        if (listed.item)
          expect(catalogId("item", listed.item), listed.item).not.toBeNull();
      }
    }
});
