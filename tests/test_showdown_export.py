"""Pokémon Showdown export: private current party and public Team Lock text.

The reference fixture is the party of a public Pokémon Y save, parsed by the
PokeApp server parser and exported by PKHeX's own ShowdownSet; PokeApp must
agree on every field except EVs, which the owner fixed at 1 in each stat.
"""

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import unittest
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.read_models import PCRead
from app.application.personal_saves import PersonalSaves
from app.application.save_ingestion import GENDERS, parsed_payload
from app.application.showdown_export import ShowdownUnavailable, party_export
from app.domain.services.team_locks import snapshots_from_parsed_payload
from app.domain.showdown import EXPORT_EV, export_team
from app.domain.showdown_names import DATA
from phase9_fixtures import FakeParser
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID
from test_phase074_training import observation

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/showdown-y-party.json").read_text(encoding="utf-8")
)
STAT_KEYS = ("hp", "atk", "defense", "spa", "spd", "spe")
# The stored projection's species placeholder, exactly as ingestion writes it.
SPECIES = parsed_payload(observation(), "s", "t", "0" * 64)["party"][0]["pokemon"]["species"].split("#")[0]


def stored(species_id, *, moves=(), ivs=(31,) * 6, evs=(0,) * 6, item=0, ability=1,
           nature=0, level=50, form=0, gender="M", shiny=False, nickname="", **extra):
    """A Pokémon in the stored parsed-save projection format (see parsed_payload)."""
    value = {
        "species": f"{SPECIES}#{species_id}",
        "nickname": nickname,
        "level": level,
        "types": [],
        "item": f"Item #{item}" if item else "",
        "item_generation": 6,
        "moves": [{"name": f"Move #{m}", "pp": 5} for m in moves if m],
        "is_shiny": shiny,
        "ability": f"Ability #{ability}",
        "nature": f"Nature #{nature}",
        "ivs": dict(zip(STAT_KEYS, ivs)),
        "evs": dict(zip(STAT_KEYS, evs)),
        "gender": gender,
        "form": form,
    }
    value.update(extra)
    return value


def from_fixture(p):
    return stored(
        p["species_id"], moves=p["move_ids"], ivs=p["ivs"], evs=p["evs"], item=p["item_id"],
        ability=p["ability_id"], nature=p["nature_id"], level=p["level"], form=p["form"],
        gender=GENDERS[p["gender"]], shiny=p["shiny"], nickname=p["nickname"], is_egg=p["is_egg"],
    )


# A strict reading of the Showdown team format, in the order Showdown's
# importer reads the first line: the item after " @ ", then a trailing
# gender, then "Nickname (Species)".
SPECIES_NAME = re.compile(r"^[A-Za-z0-9 .':%\-]+$")
ITEM_NAME = re.compile(r"^[A-Za-z0-9 .'\-]+$")


def first_line(line):
    item = None
    if " @ " in line:
        line, item = line.rsplit(" @ ", 1)
        assert ITEM_NAME.match(item), item
    gender = None
    if line.endswith((" (M)", " (F)")):
        line, gender = line[:-4], line[-2]
    nick, species = None, line
    match = re.match(r"^(.+) \(([^()]+)\)$", line)
    if match:
        nick, species = match.groups()
        assert not re.search(r"[()@\[\]|]", nick), nick
    assert SPECIES_NAME.match(species), species
    return dict(nick=nick, plain=species, gender=gender, item=item)
KEYS = re.compile(
    r"^(Ability: [A-Za-z0-9 .'\-]+|Level: (100|[1-9][0-9]?)|Shiny: Yes"
    r"|EVs: \d+ HP / \d+ Atk / \d+ Def / \d+ SpA / \d+ SpD / \d+ Spe"
    r"|[A-Z][a-z]+ Nature"
    r"|IVs: \d+ HP / \d+ Atk / \d+ Def / \d+ SpA / \d+ SpD / \d+ Spe"
    r"|- [A-Za-z0-9 .,'\-\[\]]+)$"
)


def parse_showdown(text):
    sets = []
    for block in text.strip().split("\n\n"):
        lines = block.split("\n")
        first = first_line(lines[0])
        for line in lines[1:]:
            assert KEYS.match(line), line
        sets.append(dict(first, lines=lines[1:]))
    return sets


class FixtureAgreementTests(unittest.TestCase):
    def test_public_y_party_matches_pkhex_except_the_owner_ev_rule(self):
        team = [from_fixture(p) for p in FIXTURE["party"]]
        before = deepcopy(team)
        result = export_team(team, generation=FIXTURE["generation"], projection="private")
        self.assertEqual(team, before)  # read-only: the projection is untouched
        self.assertEqual(result.warnings, ())
        self.assertEqual(result.count, len(FIXTURE["party"]))
        ours = result.text.strip().split("\n\n")
        for mine, reference, source in zip(ours, FIXTURE["pkhex_showdown_reference"], FIXTURE["party"]):
            mine_lines, ref_lines = mine.split("\n"), reference.split("\n")
            self.assertEqual(mine_lines[0], ref_lines[0])  # name, species, gender, item
            self.assertEqual(
                sorted(l for l in mine_lines[1:] if not l.startswith("EVs:")),
                sorted(l for l in ref_lines[1:] if not l.startswith("EVs:")),
            )
            self.assertIn("EVs: 1 HP / 1 Atk / 1 Def / 1 SpA / 1 SpD / 1 Spe", mine_lines)
            ivs = " / ".join(f"{v} {k}" for v, k in zip(source["ivs"], ("HP", "Atk", "Def", "SpA", "SpD", "Spe")))
            self.assertIn(f"IVs: {ivs}", mine_lines)
            # The save's EVs never reach the export.
            self.assertNotIn(f"{source['evs'][1]} Atk", mine.split("IVs:")[0].split("EVs:")[1])
        self.assertEqual(len(parse_showdown(result.text)), result.count)


class PrivateExportTests(unittest.TestCase):
    def export(self, *team, generation=6):
        return export_team(team, generation=generation, projection="private")

    def test_every_ev_is_exactly_one_whatever_the_save_says(self):
        self.assertEqual(EXPORT_EV, 1)
        for evs in ((0,) * 6, (252, 252, 4, 0, 0, 0), (255,) * 6):
            text = self.export(stored(25, evs=evs, moves=(85,))).text
            self.assertIn("EVs: 1 HP / 1 Atk / 1 Def / 1 SpA / 1 SpD / 1 Spe\n", text)

    def test_real_ivs_never_default_to_31(self):
        text = self.export(stored(25, ivs=(0, 1, 2, 3, 4, 5), moves=(85,))).text
        self.assertIn("IVs: 0 HP / 1 Atk / 2 Def / 3 SpA / 4 SpD / 5 Spe", text)
        missing = self.export(stored(25, ivs=(31,) * 6, moves=(85,)) | {"ivs": None})
        self.assertNotIn("IVs:", missing.text)
        self.assertEqual([w.code for w in missing.warnings], ["ivs_unavailable"])

    def test_full_set_order_and_fields(self):
        text = self.export(stored(
            445, nickname="Tiburón", item=275, ability=8, nature=13, level=78, shiny=True,
            gender="F", moves=(89, 200, 242, 14), ivs=(31, 30, 29, 28, 27, 26),
        )).text
        self.assertEqual(text, "\n".join([
            "Tiburon (Garchomp) (F) @ Focus Sash".replace("Tiburon", "Tiburón"),
            "Ability: Sand Veil",
            "Level: 78",
            "Shiny: Yes",
            "EVs: 1 HP / 1 Atk / 1 Def / 1 SpA / 1 SpD / 1 Spe",
            "Jolly Nature",
            "IVs: 31 HP / 30 Atk / 29 Def / 28 SpA / 27 SpD / 26 Spe",
            "- Earthquake",
            "- Outrage",
            "- Crunch",
            "- Swords Dance",
        ]) + "\n")

    def test_party_order_and_six_at_most(self):
        team = [stored(n, moves=(33,)) for n in (1, 4, 7, 25, 133, 143, 150)]
        result = self.export(*team)
        self.assertEqual(result.count, 6)
        self.assertEqual(
            [s["plain"] for s in parse_showdown(result.text)],
            ["Bulbasaur", "Charmander", "Squirtle", "Pikachu", "Eevee", "Snorlax"],
        )

    def test_forms_follow_the_save(self):
        cases = [
            (stored(479, form=2, gender="N"), 6, "Rotom-Wash"),
            (stored(678, form=1, gender="F"), 6, "Meowstic-F"),
            (stored(666, form=19), 6, "Vivillon-Pokeball"),
            (stored(666, form=0), 6, "Vivillon-Icy Snow"),
            (stored(710, form=3), 6, "Pumpkaboo-Super"),
            (stored(646, form=2, gender="N"), 6, "Kyurem-Black"),
            (stored(25, form=1), 6, "Pikachu-Rock-Star"),
            (stored(25, form=1), 7, "Pikachu-Original"),
            (stored(26, form=1), 7, "Raichu-Alola"),
        ]
        for pokemon, generation, expected in cases:
            with self.subTest(expected=expected):
                first = self.export(pokemon, generation=generation).text.split("\n")[0]
                self.assertEqual(first.split(" (")[0].split(" @ ")[0], expected)

    def test_unknown_or_missing_form_is_reported_never_guessed(self):
        unknown = self.export(stored(479, form=9, gender="N"))
        self.assertTrue(unknown.text.startswith("Rotom\n"))
        self.assertEqual([w.code for w in unknown.warnings], ["form_unknown"])
        missing = self.export(stored(479, gender="N") | {"form": None})
        self.assertEqual([w.code for w in missing.warnings], ["form_unavailable"])
        plain = self.export(stored(1) | {"form": None})  # no stored forms
        self.assertEqual(plain.warnings, ())

    def test_gender_only_where_it_is_a_choice(self):
        self.assertTrue(self.export(stored(25, gender="F")).text.startswith("Pikachu (F)\n"))
        self.assertTrue(self.export(stored(81, gender="N")).text.startswith("Magnemite\n"))
        self.assertTrue(self.export(stored(29, gender="F")).text.startswith("Nidoran-F\n"))
        self.assertTrue(self.export(stored(678, form=1, gender="F")).text.startswith("Meowstic-F\n"))
        unknown = self.export(stored(25) | {"gender": None})
        self.assertTrue(unknown.text.startswith("Pikachu\n"))
        self.assertEqual([w.code for w in unknown.warnings], ["gender_unavailable"])

    def test_default_names_are_not_nicknames_and_unsafe_ones_are_reported(self):
        self.assertTrue(self.export(stored(25, nickname="PIKACHU")).text.startswith("Pikachu (M)\n"))
        # The game's own default name, in any case or with accents, is not a nickname.
        self.assertTrue(self.export(stored(669, nickname="FLABÉBÉ", gender="F")).text.startswith("Flabebe\n"))
        self.assertTrue(self.export(stored(83, nickname="Farfetch’d")).text.startswith("Farfetch'd (M)\n"))
        self.assertTrue(
            self.export(stored(122, nickname="Mr. Mime")).text.startswith("Mr. Mime (M)\n")
        )
        risky = self.export(stored(25, nickname="Pika(chu)"))
        self.assertTrue(risky.text.startswith("Pikachu (M)\n"))
        self.assertEqual([w.code for w in risky.warnings], ["nickname_unsupported"])

    def test_hidden_power_type_comes_from_the_real_ivs(self):
        self.assertIn("- Hidden Power [Dark]", self.export(stored(201, moves=(237,), gender="N")).text)
        fire = (31, 30, 31, 30, 31, 30)  # HP/Atk/Def/SpA/SpD/Spe
        self.assertIn("- Hidden Power [Fire]", self.export(stored(201, moves=(237,), ivs=fire, gender="N")).text)

    def test_items_showdown_does_not_know_are_reported_not_invented(self):
        everstone = self.export(stored(25, item=229))
        self.assertTrue(everstone.text.startswith("Pikachu (M)\n"))
        self.assertEqual(
            [(w.code, w.detail) for w in everstone.warnings], [("item_not_in_showdown", "Everstone")]
        )
        unknown = self.export(stored(25, item=114))
        self.assertEqual([w.code for w in unknown.warnings], ["item_unknown"])
        self.assertIn("@ Stick", self.export(stored(83, item=259)).text)

    def test_eggs_and_unknown_species_are_skipped_with_a_reason(self):
        result = self.export(stored(25, is_egg=True), stored(25) | {"species": "Pokémon #9999"}, stored(1))
        self.assertEqual(result.count, 1)
        self.assertEqual([w.code for w in result.warnings], ["egg_skipped", "species_unknown"])
        self.assertEqual([w.slot for w in result.warnings], [1, 2])

    def test_unknown_move_ids_are_left_out(self):
        result = self.export(stored(25, moves=(85, 999)))
        self.assertEqual([l for l in result.text.split("\n") if l.startswith("- ")], ["- Thunderbolt"])
        self.assertEqual([w.code for w in result.warnings], ["move_unknown"])

    def test_legacy_named_projections_resolve_the_same(self):
        legacy = {
            "species": "Pikachu", "nickname": "", "level": 50, "item": "Light Ball",
            "moves": [{"name": "Thunderbolt"}, {"name": "Volt Tackle"}], "is_shiny": False,
            "ability": "Static", "nature": "Timid", "ivs": dict(zip(STAT_KEYS, (31,) * 6)), "gender": "♂",
        }
        self.assertEqual(
            self.export(legacy).text.split("\n")[:4],
            ["Pikachu (M) @ Light Ball", "Ability: Static", "Level: 50",
             "EVs: 1 HP / 1 Atk / 1 Def / 1 SpA / 1 SpD / 1 Spe"],
        )

    def test_never_writes_tera_or_later_generation_fields(self):
        text = self.export(*[from_fixture(p) for p in FIXTURE["party"]]).text
        for later in ("Tera Type", "Dynamax", "Gigantamax", "Happiness"):
            self.assertNotIn(later, text)


class PublicProjectionTests(unittest.TestCase):
    def test_public_text_carries_only_public_fields(self):
        mon = stored(
            445, nickname="Tiburón", item=229, ability=8, nature=13, level=78, shiny=True,
            gender="F", moves=(89, 237, 242, 14), ivs=(0, 1, 2, 3, 4, 5), evs=(252,) * 6,
        )
        result = export_team([mon], generation=6, projection="public")
        self.assertEqual(result.text, "\n".join([
            "Tiburón (Garchomp) (F) @ Everstone",
            "Level: 78",
            "Shiny: Yes",
            "- Earthquake",
            "- Hidden Power",
            "- Crunch",
            "- Swords Dance",
        ]) + "\n")
        for private in ("Ability", "Nature", "IVs", "EVs", "Sand Veil", "Jolly", "[", "252"):
            self.assertNotIn(private, result.text)
        self.assertEqual(result.warnings, ())


class IngestionAndProjectionTests(unittest.TestCase):
    def test_stored_payload_keeps_gender_and_form_for_x_y(self):
        observed = observation(game="Y")
        stored_mon = parsed_payload(observed, "s", "t", "0" * 64)["party"][0]["pokemon"]
        parsed = observed.party[0]
        self.assertEqual(stored_mon["gender"], GENDERS[parsed.gender])
        self.assertEqual(stored_mon["form"], parsed.form)
        # Snapshots expose the form through the existing public form_index and
        # keep the private fields out of the public copy.
        payload = parsed_payload(observed, "s", "t", "0" * 64)
        payload["party"] = [payload["party"][0]] * 6
        payload["party"] = [dict(p, slot_number=i) for i, p in enumerate(payload["party"], 1)]
        public, private = snapshots_from_parsed_payload(payload)
        self.assertEqual(public[0]["form_index"], parsed.form)
        self.assertEqual(public[0]["gender"], GENDERS[parsed.gender])
        for key in ("ability", "nature", "ivs", "evs"):
            self.assertNotIn(key, public[0])
            self.assertIn(key, private[0])

    def pc(self, team, *, status="ready", boxes=()):
        slots = [dict(location=f"Equipo · {i}", pokemon={**p, "status_flags": []}) for i, p in team]
        slots += [dict(location=f"Caja 1 · {i}", pokemon={**p, "status_flags": []}) for i, p in boxes]
        return PCRead(
            save=dict(id=str(uuid4()), parser_status="parsed", parser_version="v",
                      uploaded_at=datetime(2026, 11, 3, tzinfo=timezone.utc), game="Y"),
            status=status, pokemon=slots if status == "ready" else [],
        )

    def test_exports_the_displayed_party_only_in_slot_order(self):
        pc = self.pc([(3, stored(7)), (1, stored(1))], boxes=[(1, stored(150, gender="N"))])
        result = party_export(pc)
        self.assertEqual((result.save_id, result.game, result.count), (pc.save.id, "Y", 2))
        self.assertEqual([s["plain"] for s in parse_showdown(result.text)], ["Bulbasaur", "Squirtle"])
        self.assertNotIn("Mewtwo", result.text)

    def test_warnings_name_the_party_slot(self):
        result = party_export(self.pc([(4, stored(25, item=229))]))
        self.assertEqual([(w.code, w.slot) for w in result.warnings], [("item_not_in_showdown", 4)])

    def test_no_ready_save_or_empty_party_is_refused(self):
        with self.assertRaises(ShowdownUnavailable) as caught:
            party_export(self.pc([], status="not_ready"))
        self.assertEqual(caught.exception.code, "SHOWDOWN_SAVE_NOT_READY")
        with self.assertRaises(ShowdownUnavailable) as caught:
            party_export(self.pc([], boxes=[(1, stored(1))]))
        self.assertEqual(caught.exception.code, "SHOWDOWN_TEAM_EMPTY")


class ReadModelTests(unittest.TestCase):
    def test_existing_private_snapshots_with_empty_gender_still_read(self):
        from app.api.read_models import PrivatePokemonRead
        from app.api.team_preview_models import SelfPreviewLock

        _, private = snapshots_from_parsed_payload({
            "party": [{"slot_number": i, "pokemon": {"species": f"{SPECIES}#25", "moves": []}}
                      for i in range(1, 7)]
        })
        self.assertEqual(private[0]["gender"], "")  # the stored default
        lock = SelfPreviewLock(locked_at=datetime(2026, 11, 3, tzinfo=timezone.utc), is_late=False, team=private)
        self.assertIsNone(lock.team[0].gender)
        for value, expected in (("M", "M"), ("F", "F"), ("N", "N"), ("♂", None), (None, None), (0, None)):
            self.assertEqual(PrivatePokemonRead(species="x", gender=value).gender, expected)


class Repo:
    def __init__(self):
        self.row = None

    def get(self, trainer_id):
        return self.row if self.row and self.row["trainer_id"] == trainer_id else None

    def upsert(self, row):
        self.row = row


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.personal = PersonalSaves(self.repo, FakeParser(observation(game="Y")))
        self.tokens = FakeTokenVerifier()
        self.client = TestClient(create_app(container=ApiContainer(
            token_verifier=self.tokens, principal_repository=FakePrincipalRepository(),
            personal_saves=self.personal,
        )))
        self.addCleanup(self.client.close)
        self.auth = {"Authorization": "Bearer validated"}

    def test_anonymous_callers_are_refused(self):
        self.assertEqual(self.client.get("/v1/me/pc/showdown").status_code, 401)
        self.assertEqual(
            self.client.get(f"/v1/read/seasons/{uuid4()}/pc/showdown").status_code, 401
        )

    def test_no_personal_save_is_a_clear_conflict(self):
        response = self.client.get("/v1/me/pc/showdown", headers=self.auth)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "SHOWDOWN_SAVE_NOT_READY")

    def test_owner_gets_their_current_personal_party_without_any_write(self):
        from hashlib import sha256
        from app.save_parser.registration import observation_digest

        parser = self.personal.parser
        data = b"synthetic showdown export save"
        self.personal.receive(TRAINER_ID, sha256(data).hexdigest(),
                              observation_digest(parser.value, parser.version), data)
        before = deepcopy(self.repo.row)
        response = self.client.get("/v1/me/pc/showdown", headers=self.auth)
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["save_id"], TRAINER_ID)
        self.assertEqual(body["count"], 1)
        self.assertIn("EVs: 1 HP / 1 Atk / 1 Def / 1 SpA / 1 SpD / 1 Spe", body["text"])
        self.assertEqual(self.repo.row, before)  # nothing stored or changed
        self.assertEqual(parser.calls, 1)  # no re-parse to export
        # The query string cannot select another trainer.
        other = self.client.get(f"/v1/me/pc/showdown?trainer_id={uuid4()}", headers=self.auth)
        self.assertEqual(other.json()["save_id"], TRAINER_ID)


class NameTableTests(unittest.TestCase):
    def test_every_name_is_plain_ascii_and_every_save_id_is_covered(self):
        for key in ("species", "moves", "abilities", "items", "items_english", "natures"):
            for name in DATA[key]:
                if name:
                    self.assertTrue(name.isascii(), name)
        self.assertEqual(len(DATA["species"]), 808)
        self.assertTrue(all(DATA["species"][1:]))
        self.assertTrue(all(DATA["abilities"][1:]))
        self.assertEqual(len(DATA["natures"]), 25)

    def test_same_ids_as_the_web_catalog(self):
        catalog = json.loads(
            (Path(__file__).resolve().parents[1] / "web/src/pokemon/catalog.es.json").read_text(encoding="utf-8")
        )["categories"]
        to_id = lambda s: re.sub(r"[^a-z0-9]", "", s.lower())  # noqa: E731
        from app.domain.showdown import _ascii
        for n in range(1, 808):
            self.assertEqual(to_id(_ascii(catalog["species"]["en"][n])), to_id(DATA["species"][n]), n)
        for n in range(1, 234):
            self.assertEqual(to_id(_ascii(catalog["ability"]["en"][n])), to_id(DATA["abilities"][n]), n)
        mismatched = [
            n for n in range(1, 729)
            if DATA["moves"][n] and to_id(_ascii(catalog["move"]["en"][n])) != to_id(DATA["moves"][n])
        ]
        self.assertEqual(mismatched, [])


if __name__ == "__main__":
    unittest.main()
