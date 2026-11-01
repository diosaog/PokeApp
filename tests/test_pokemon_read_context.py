"""Held IDs use the same parsed save game, without guessing or new native writes."""
import unittest
from app.application.pokemon_read_context import pokemon_context
from app.application.save_ingestion import parsed_payload
from app.repositories.errors import PersistenceError
from test_phase16b_xy import xy

class ItemContextTests(unittest.TestCase):
    def test_xy_ingestion_includes_item_generation_for_new_saves(self):
        for game in ("X", "Y"):
            payload = parsed_payload(xy().model_copy(update={"game": game}), "save", "trainer", "a"*64)
            self.assertEqual(payload["party"][0]["pokemon"]["item_generation"], 6)

    def test_existing_payload_context_preserves_actual_ids_and_empty_items(self):
        for game, generation in (("X",6),("Y",6),("OR",6),("AS",6),("SN",7),("MN",7),("US",7),("UM",7)):
            for item in ("Item #158", "Item #217", ""):
                source = dict(item=item, species="Clefable", moves=[dict(name="Move #85")])
                result = pokemon_context(source, dict(game=game, generation=generation))
                self.assertEqual(result, {**source, "item_generation": generation})
                self.assertNotIn("item_generation", source)
        self.assertNotIn("item_generation", pokemon_context(dict(item="Item #158"), {}))
        with self.assertRaises(PersistenceError):
            pokemon_context({}, dict(game="Y", generation=7))
        with self.assertRaises(PersistenceError):
            pokemon_context({}, dict(game="Y"), "SN")
