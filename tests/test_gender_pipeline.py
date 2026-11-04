"""079 gender verification: the real server parser's answer, end to end.

fixtures/showdown-y-genders.json holds what the server parser (pokeapp-reader/3)
returned for two synthetic Pokémon Y saves written with PKHeX: male, female and
genderless Pokémon, forms whose identity depends on gender (Meowstic, Pyroar),
fixed-gender species and genderless forms. It also records how PKHeX's own
Showdown parser re-imported PokeApp's text. This test replays the rest of the
pipeline (ingestion payload -> PC read model -> Showdown export) from it.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest
from uuid import uuid4

from app.api.read_models import PCRead
from app.application.pokemon_read_context import pokemon_context
from app.application.save_ingestion import GENDERS, parsed_payload
from app.application.showdown_export import party_export
from app.save_parser.models import ParserResponse

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/showdown-y-genders.json").read_text(encoding="utf-8")
)
# PokeApp's first line per slot: gender only where it is a choice (Showdown style).
EXPECTED = {
    "gender-a": ["Pikachu (M) @ Light Ball", "Pikachu (F)", "Magnemite", "Meowstic",
                 "Meowstic-F", "Pyroar (F)"],
    "gender-b": ["Nidoran-F", "Nidoran-M", "Tauros", "Chansey", "Rotom-Wash", "Unown-F"],
}


def pipeline(name, strip_gender=False):
    # Strict wire model: JSON in, exactly as the parser's stdout is read.
    response = ParserResponse.model_validate_json(json.dumps(FIXTURE["saves"][name]["parser_response"]))
    observation = response.observation
    save_id = str(uuid4())
    payload = parsed_payload(observation, save_id, str(uuid4()), "0" * 64)
    if strip_gender:
        payload = deepcopy(payload)
        for slot in payload["party"]:
            slot["pokemon"].pop("gender", None)  # a projection stored before 078
    pc = PCRead(
        save=dict(id=save_id, parser_status="parsed", parser_version=response.parser_version,
                  uploaded_at=datetime.now(timezone.utc), game=payload["game"]),
        status="ready",
        pokemon=[dict(location=f"Equipo · {s['slot_number']}",
                      pokemon={**pokemon_context(s["pokemon"], payload), "status_flags": []})
                 for s in payload["party"] if s.get("pokemon")],
    )
    return observation, payload, pc, party_export(pc)


class GenderPipelineTests(unittest.TestCase):
    def test_every_layer_keeps_the_gender_pkhex_stored(self):
        for name, saves in FIXTURE["saves"].items():
            with self.subTest(save=name):
                observation, payload, pc, _ = pipeline(name)
                self.assertEqual(observation.game, "Y")
                pkhex = [(p["species"], p["form"], p["gender"]) for p in saves["pkhex"]]
                self.assertEqual([(p.species_id, p.form, p.gender) for p in observation.party], pkhex)
                self.assertEqual([(s["pokemon"]["form"], s["pokemon"]["gender"]) for s in payload["party"]],
                                 [(form, GENDERS[gender]) for _, form, gender in pkhex])
                self.assertEqual([(s.pokemon.form, s.pokemon.gender) for s in pc.pokemon],
                                 [(form, GENDERS[gender]) for _, form, gender in pkhex])

    def test_showdown_text_names_the_exact_pokemon(self):
        for name, lines in EXPECTED.items():
            with self.subTest(save=name):
                *_, export = pipeline(name)
                sets = export.text.strip().split("\n\n")
                self.assertEqual([s.splitlines()[0] for s in sets], lines)
                self.assertNotIn("gender_unavailable", [w.code for w in export.warnings])

    def test_pkhex_reimports_species_form_and_gender_from_the_text(self):
        for name, saves in FIXTURE["saves"].items():
            with self.subTest(save=name):
                *_, export = pipeline(name)
                lines = [s.splitlines()[0] for s in export.text.strip().split("\n\n")]
                for line, stored, back in zip(lines, saves["pkhex"], saves["reimported_by_pkhex"]):
                    self.assertEqual(back["line"], line)
                    gender = back["gender"] if back["gender"] is not None else back["implied"]
                    self.assertEqual((back["species"], back["form"], gender),
                                     (stored["species"], stored["form"], stored["gender"]))

    def test_an_older_projection_without_gender_warns_and_never_guesses(self):
        *_, export = pipeline("gender-a", strip_gender=True)
        lines = [s.splitlines()[0] for s in export.text.strip().split("\n\n")]
        # No (M)/(F) invented; fixed or form-bound identities are still exact.
        self.assertEqual(lines, ["Pikachu @ Light Ball", "Pikachu", "Magnemite", "Meowstic",
                                 "Meowstic-F", "Pyroar"])
        warned = [w.slot for w in export.warnings if w.code == "gender_unavailable"]
        self.assertEqual(warned, [1, 2, 6])


if __name__ == "__main__":
    unittest.main()
