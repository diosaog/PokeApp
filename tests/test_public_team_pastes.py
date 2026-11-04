"""Public Pokepast.es links for confirmed Team Locks, through the Discord outbox.

Everything external is mocked: no request ever reaches pokepast.es or Discord.
"""

import json
import unittest
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

from app.api.announcer import create_announcer
from app.api.config import APIConfig
from app.application.announcements import PASTE_ATTEMPTS, Dispatcher
from app.application.discord_webhook import Outcome
from app.application.pokepaste import CREATE_URL, PasteOutcome, Pokepaste
from app.domain.showdown import export_team
from app.repositories.supabase.announcements import (
    COLUMNS,
    PASTE_COLUMNS,
    SupabaseAnnouncementRepository,
)

NOW = datetime(2026, 11, 3, 20, 0, tzinfo=UTC)
URL_1, URL_2 = "https://pokepast.es/0123456789abcdef", "https://pokepast.es/fedcba9876543210"


def mon(species, *, nickname="", item=0, moves=(), level=50, gender="M", shiny=False, form=0):
    """A public Team Lock snapshot entry (PublicPokemon, as stored)."""
    return {
        "id": "",
        "species": f"Pokémon #{species}",
        "nickname": nickname,
        "level": level,
        "gender": gender,
        "types": [],
        "item": f"Item #{item}" if item else "",
        "moves": [{"name": f"Move #{m}", "move_id": None, "pp": 5} for m in moves],
        "sprite_url": "",
        "form_name": "",
        "form_index": form,
        "is_shiny": shiny,
        "flags": {"dead": False, "shielded": False, "stolen": False, "revived": False},
        "metadata": {},
    }


PUBLIC_TEAM = [
    mon(445, nickname="Tiburón", item=275, moves=(89, 200, 242, 14), level=78, gender="F", shiny=True),
    mon(479, item=234, moves=(85, 56), gender="N", form=2),
    mon(25, moves=(85,)),
    mon(6, moves=(53,)),
    mon(9, moves=(57,)),
    mon(3, moves=(76,)),
]
# What a private snapshot holds and a public paste must never carry.
PRIVATE_TEAM = [
    dict(m, ability="Ability #8", nature="Nature #13",
         ivs={"hp": 7, "atk": 7, "defense": 7, "spa": 7, "spd": 7, "spe": 7},
         evs={"hp": 252, "atk": 252, "defense": 4, "spa": 0, "spd": 0, "spe": 0})
    for m in PUBLIC_TEAM
]

# The owner's structural example, synthetic IDs only; never a player's save.
EXAMPLE_TEAM = [
    mon(85, nickname="TriPollo", item=239, moves=(38, 282, 438, 73), gender=""),
    mon(711, nickname="Jalowin", item=540, moves=(221, 398, 152, 38), gender=""),
    mon(73, nickname="Pulpo Pol", item=640, moves=(473, 518, 586, 338), gender=""),
    mon(637, nickname="Miguel", item=650, moves=(284, 448, 518, 204), gender=""),
    mon(24, nickname="Pollita", item=217, moves=(370, 155, 337, 226), gender=""),
    mon(36, nickname="Leffa", item=158, moves=(326, 405, 586, 229), gender=""),
]
EXAMPLE_TEXT = (Path(__file__).parent / "fixtures/public-pokepaste-example.txt").read_text(encoding="utf-8")


class Outbox:
    """The repository contract the dispatcher relies on, in memory."""

    def __init__(self, rows):
        self.rows = {r["id"]: r for r in rows}
        self.updates = []

    def recover(self, cutoff):
        pass

    def expire(self, cutoff):
        pass

    def due(self, now, limit):
        return [
            deepcopy(r) for r in self.rows.values()
            if (r["status"] == "pending" or (r["status"] == "sent" and r["delivered_revision"] < r["revision"]))
            and r["next_attempt_at"] <= now
        ][:limit]

    def next_due(self):
        due = [r["next_attempt_at"] for r in self.rows.values()
               if r["status"] == "pending" or (r["status"] == "sent" and r["delivered_revision"] < r["revision"])]
        return min(due) if due else None

    def claim(self, row, now):
        stored = self.rows[row["id"]]
        if stored["status"] != row["status"] or stored["attempts"] != row["attempts"]:
            return None
        stored.update(status="sending", claimed_at=now.isoformat(), attempts=row["attempts"] + 1)
        return deepcopy(stored)

    def update(self, claim, fields):
        stored = self.rows[claim["id"]]
        assert stored["status"] == "sending" and stored["claimed_at"] == claim["claimed_at"]
        self.updates.append(dict(fields))
        for key, value in fields.items():
            stored[key] = datetime.fromisoformat(value) if key == "next_attempt_at" else value


class Webhook:
    def __init__(self):
        self.posts, self.edits, self.outcomes = [], [], []

    def ready_in(self):
        return 0.0

    def post(self, payload):
        self.posts.append(payload)
        return self.outcomes.pop(0) if self.outcomes else Outcome("delivered", "delivered", message_id="123")

    def edit(self, message_id, payload):
        self.edits.append((message_id, payload))
        return Outcome("delivered", "delivered", message_id=message_id)


class Pastes:
    def __init__(self, *outcomes):
        self.calls, self.outcomes = [], list(outcomes)

    def create(self, **form):
        self.calls.append(form)
        return self.outcomes.pop(0) if self.outcomes else PasteOutcome(URL_1, "created")


def row(kind="team_locked", **changes):
    value = dict(
        id="a1", kind=kind, season_id="s", subject={"lock_id": "lock"}, status="pending",
        revision=1, delivered_revision=0, attempts=0, discord_message_id=None,
        created_at=NOW.isoformat(), claimed_at=None, next_attempt_at=NOW,
        public_paste_url=None, public_paste_revision=None, public_paste_attempt_revision=0,
        public_paste_attempts=0, public_paste_error=None,
    )
    value.update(changes)
    return value


class Harness:
    def __init__(self, *paste_outcomes, rows=None, pastes=True):
        self.reads = []
        self.tables = {
            "team_locks": [dict(
                id="lock", season_id="s", matchday_id="day", trainer_id="t1",
                public_team_snapshot=deepcopy(PUBLIC_TEAM), private_team_snapshot=deepcopy(PRIVATE_TEAM),
                is_late=False, locked_at=NOW.isoformat(), created_at=NOW.isoformat(), save_file_id="save",
            )],
            "seasons": [dict(id="s", name="ChampionsLocke", status="active")],
            "matchdays": [dict(id="day", season_id="s", number=1, status="open")],
            "season_players": [dict(id="p1", trainer_id="t1", status="active"), dict(id="p2", trainer_id="t2", status="active")],
            "trainers": [dict(id="t1", display_name="Anto"), dict(id="t2", display_name="Aaron")],
            "save_files": [dict(id="save", metadata={"save_identity": {"game": "Y", "trainer": "secret"}})],
        }
        self.outbox = Outbox(rows or [row()])
        self.webhook = Webhook()
        self.pastes = Pastes(*paste_outcomes) if pastes else None
        self.clock = NOW
        self.dispatcher = Dispatcher(outbox=self.outbox, read=self.read, webhook=self.webhook,
                                     now=lambda: self.clock, pastes=self.pastes)

    def read(self, table, columns, **filters):
        self.reads.append((table, columns))
        rows = deepcopy(self.tables.get(table, []))
        for key, value in filters.items():
            rows = [r for r in rows if key not in r or (r[key] in value if isinstance(value, list) else r[key] == value)]
        wanted = [c.strip() for c in columns.split(",")]
        return [{k: v for k, v in r.items() if k in wanted} for r in rows]

    def run(self, minutes=0):
        self.clock = self.clock + timedelta(minutes=minutes)
        self.dispatcher.run_once()

    @property
    def stored(self):
        return self.outbox.rows["a1"]


def text_of(payload):
    return json.dumps(payload, ensure_ascii=False)


class DispatcherTests(unittest.TestCase):
    def test_example_reaches_pokepaste_as_six_recognizable_sets(self):
        requests = []

        def handler(request):
            requests.append(request)
            return httpx.Response(303, headers={"Location": URL_1})

        h = Harness()
        h.tables["team_locks"][0]["public_team_snapshot"] = deepcopy(EXAMPLE_TEAM)
        h.dispatcher.pastes = transport(handler)
        h.run()
        h.run(minutes=1)
        self.assertEqual((len(requests), len(h.webhook.posts)), (1, 1))
        paste = dict(httpx.QueryParams(requests[0].content.decode()))["paste"]
        # Pokepast.es v3 syntax.go splits on these exact bytes, not splitlines().
        sets = paste.rstrip("\r\n").split("\r\n\r\n")
        self.assertEqual(len(sets), 6)
        self.assertEqual([sum(line.startswith("- ") for line in s.split("\r\n")) for s in sets], [4] * 6)
        self.assertEqual(paste.count("Level: 50\r\n"), 6)
        self.assertEqual(paste.replace("Level: 50\r\n", "").replace("\r\n", "\n"), EXAMPLE_TEXT)
        self.assertIn(URL_1, text_of(h.webhook.posts[0]))

    def test_confirmed_lock_gets_one_public_paste_and_one_announcement(self):
        h = Harness()
        h.run()
        self.assertEqual(len(h.pastes.calls), 1)
        self.assertEqual(len(h.webhook.posts), 1)
        message = text_of(h.webhook.posts[0])
        self.assertIn(f"Ver equipo:** {URL_1}", message)
        self.assertIn("Anto", message)
        self.assertIn("Jornada 1", message)
        self.assertEqual((h.stored["status"], h.stored["public_paste_url"], h.stored["public_paste_revision"]),
                         ("sent", URL_1, 1))
        # The URL was stored before Discord was called.
        self.assertEqual(h.outbox.updates[0]["public_paste_url"], URL_1)

    def test_paste_is_the_exact_locked_public_team_and_nothing_private(self):
        h = Harness()
        h.run()
        form = h.pastes.calls[0]
        self.assertEqual(form["title"], "Anto · Jornada 1")
        self.assertEqual(form["author"], "PokeApp")
        self.assertEqual(form["notes"], "Team Lock oficial · ChampionsLocke")
        paste = form["paste"]
        self.assertTrue(paste.startswith("Tiburón (Garchomp) (F) @ Focus Sash\nLevel: 78\nShiny: Yes\n- Earthquake\n"))
        self.assertIn("Rotom-Wash @ Leftovers", paste)  # form from the locked snapshot (Y)
        self.assertEqual(paste.count("\n\n"), 5)  # six sets
        for private in ("Ability", "Nature", "IVs", "EVs", "Sand Veil", "Jolly", "252", "secret"):
            self.assertNotIn(private, paste)
        # The private snapshot is never even read.
        self.assertFalse(any("private_team_snapshot" in columns for _, columns in h.reads))

    def test_private_fields_and_mutable_party_cannot_change_the_public_paste(self):
        h = Harness()
        h.tables["team_locks"][0]["public_team_snapshot"] = deepcopy(PRIVATE_TEAM)
        h.tables["parsed_saves"] = [{"payload": {"party": [mon(150, nickname="Mutable secret")]}}]
        h.run()
        expected = export_team(PUBLIC_TEAM, generation=6, projection="public").text
        self.assertEqual(h.pastes.calls[0]["paste"], expected)
        self.assertFalse(any(table == "parsed_saves" for table, _ in h.reads))

    def test_public_forms_and_gender_with_no_nicknames_or_items(self):
        team = [
            mon(678, gender="M"), mon(678, gender="F", form=1),
            mon(29, gender="F"), mon(32, gender="M"),
            mon(668, gender="F"), mon(479, gender="N", form=2),
        ]
        exported = export_team(team, generation=6, projection="public")
        self.assertEqual(exported.count, 6)
        self.assertEqual([s.splitlines()[0] for s in exported.text.strip().split("\n\n")],
                         ["Meowstic", "Meowstic-F", "Nidoran-F", "Nidoran-M", "Pyroar (F)", "Rotom-Wash"])
        self.assertNotIn("@", exported.text)
        self.assertEqual(exported.warnings, ())

    def test_discord_embed_names_the_team(self):
        h = Harness()
        h.run()
        message = text_of(h.webhook.posts[0])
        self.assertIn("Tiburón (Garchomp)", message)
        self.assertIn("@ Focus Sash", message)
        self.assertNotIn("Pokémon #", message)

    def test_retried_delivery_reuses_the_stored_link(self):
        h = Harness()
        h.webhook.outcomes = [Outcome("retry", "connect_failed")]
        h.run()
        self.assertEqual((len(h.pastes.calls), len(h.webhook.posts), h.stored["status"]), (1, 1, "pending"))
        h.run(minutes=1)
        self.assertEqual((len(h.pastes.calls), len(h.webhook.posts), h.stored["status"]), (1, 2, "sent"))
        self.assertIn(URL_1, text_of(h.webhook.posts[1]))

    def test_uncertain_post_is_never_repeated_nor_repasted(self):
        h = Harness()
        h.webhook.outcomes = [Outcome("uncertain", "response_timeout")]
        h.run()
        h.run(minutes=10)
        self.assertEqual((len(h.pastes.calls), len(h.webhook.posts), h.stored["status"]), (1, 1, "uncertain"))

    def test_transient_failures_are_bounded_then_the_lock_is_announced_without_a_link(self):
        failing = PasteOutcome(None, "pokepaste_http_503", retry=True)
        h = Harness(failing, failing, failing, failing)
        h.run()
        self.assertEqual((len(h.pastes.calls), len(h.webhook.posts), h.stored["status"]), (1, 0, "pending"))
        self.assertEqual((h.stored["public_paste_attempts"], h.stored["public_paste_error"]), (1, "pokepaste_http_503"))
        h.run(minutes=1)
        self.assertEqual((len(h.pastes.calls), len(h.webhook.posts)), (2, 0))
        h.run(minutes=1)
        self.assertEqual((len(h.pastes.calls), len(h.webhook.posts)), (PASTE_ATTEMPTS, 1))
        message = text_of(h.webhook.posts[0])
        self.assertIn("no está disponible", message)
        self.assertNotIn("pokepast.es/", message)
        self.assertEqual(h.stored["status"], "sent")
        h.run(minutes=60)
        self.assertEqual(len(h.pastes.calls), PASTE_ATTEMPTS)  # no further external requests

    def test_a_rejected_paste_does_not_hold_the_announcement(self):
        h = Harness(PasteOutcome(None, "pokepaste_http_400"))
        h.run()
        self.assertEqual((len(h.pastes.calls), len(h.webhook.posts), h.stored["status"]), (1, 1, "sent"))
        self.assertNotIn("pokepast.es/", text_of(h.webhook.posts[0]))

    def test_a_replaced_lock_gets_a_new_paste_and_never_the_old_link(self):
        h = Harness(PasteOutcome(URL_1, "created"), PasteOutcome(URL_2, "created"))
        h.run()
        h.tables["team_locks"][0]["public_team_snapshot"][2] = mon(26, moves=(85,))
        h.stored.update(revision=2)  # what the 067 trigger does on replacement
        h.run(minutes=1)
        self.assertEqual(len(h.pastes.calls), 2)
        self.assertIn("Raichu", h.pastes.calls[1]["paste"])
        self.assertEqual(len(h.webhook.edits), 1)
        edited = text_of(h.webhook.edits[0][1])
        self.assertIn(URL_2, edited)
        self.assertNotIn(URL_1, edited)
        self.assertIn("reemplazado", edited)
        self.assertEqual((h.stored["public_paste_url"], h.stored["public_paste_revision"]), (URL_2, 2))

    def test_an_unrepresentable_team_still_announces_the_lock(self):
        h = Harness()
        h.tables["team_locks"][0]["public_team_snapshot"][0]["moves"] = 5  # malformed
        h.run()
        self.assertEqual(h.pastes.calls, [])
        self.assertEqual((len(h.webhook.posts), h.stored["status"]), (1, "sent"))
        self.assertIn("no está disponible", text_of(h.webhook.posts[0]))

    def test_an_unexpected_transport_error_is_a_bounded_retry(self):
        class Broken(Pastes):
            def create(self, **form):
                self.calls.append(form)
                raise RuntimeError("boom")

        h = Harness()
        h.pastes = h.dispatcher.pastes = Broken()
        for minutes in (0, 1, 1, 1):
            h.run(minutes=minutes)
        self.assertEqual(len(h.pastes.calls), PASTE_ATTEMPTS)
        self.assertEqual((len(h.webhook.posts), h.stored["status"]), (1, "sent"))

    def test_other_announcements_never_create_pastes(self):
        h = Harness(rows=[row(kind="season_started", subject={"season_id": "s"})])
        h.tables["season_config_versions"] = [dict(version_number=1, effective_from_matchday=1, total_matchdays=4)]
        h.tables["divisions"] = []
        h.tables["division_memberships"] = []
        h.run()
        self.assertEqual(h.pastes.calls, [])
        self.assertEqual(len(h.webhook.posts), 1)

    def test_disabled_pastes_keep_the_previous_announcement(self):
        h = Harness(pastes=False)
        h.run()
        self.assertEqual(len(h.webhook.posts), 1)
        message = text_of(h.webhook.posts[0])
        self.assertNotIn("pokepast", message)
        self.assertNotIn("enlace", message)

    def test_the_lock_itself_is_never_written(self):
        h = Harness(PasteOutcome(None, "pokepaste_unreachable", retry=True))
        before = deepcopy(h.tables["team_locks"])
        for minutes in (0, 1, 1, 1):
            h.run(minutes=minutes)
        self.assertEqual(h.tables["team_locks"], before)
        self.assertTrue(all(set(u) <= {
            "public_paste_url", "public_paste_revision", "public_paste_attempt_revision",
            "public_paste_attempts", "public_paste_error", "status", "last_error", "next_attempt_at",
            "delivered_revision", "attempts", "sent_at", "discord_message_id",
        } for u in h.outbox.updates))


def transport(handler):
    return Pokepaste(client=httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False))


class TransportTests(unittest.TestCase):
    def test_creates_with_the_documented_form_and_reads_the_303_location(self):
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(303, headers={"Location": "/0123456789abcdef"})

        outcome = transport(handler).create(paste="Pikachu\n- Thunderbolt\n", title="T", author="PokeApp", notes="N")
        self.assertEqual(outcome, PasteOutcome(URL_1, "created"))
        request = seen[0]
        self.assertEqual((request.method, str(request.url)), ("POST", CREATE_URL))
        form = dict(httpx.QueryParams(request.content.decode()))
        self.assertEqual(form, {"paste": "Pikachu\r\n- Thunderbolt\r\n", "title": "T", "author": "PokeApp", "notes": "N"})

    def test_line_endings_are_normalized_once_in_the_http_form(self):
        expected = "Pikachu\r\n- Thunderbolt\r\n\r\nRaichu\r\n- Surf\r\n"
        for paste in (expected, expected.replace("\r\n", "\n"), expected.replace("\r\n", "\r"),
                      "Pikachu\r\n- Thunderbolt\n\nRaichu\r- Surf\n"):
            with self.subTest(paste=repr(paste)):
                requests = []
                client = transport(lambda r, requests=requests: requests.append(r) or httpx.Response(303, headers={"Location": URL_1}))
                self.assertEqual(client.create(paste=paste, title="", author="", notes="").url, URL_1)
                self.assertEqual(dict(httpx.QueryParams(requests[0].content.decode()))["paste"], expected)

    def test_response_url_is_restricted_to_the_exact_public_pokepaste_path(self):
        for location in ("//evil.example/0123456789abcdef", "http://pokepast.es/0123456789abcdef",
                         "https://pokepast.es.evil.example/0123456789abcdef",
                         "https://user@pokepast.es/0123456789abcdef", "/0123456789abcdef/raw",
                         "/0123456789abcdef?x=y", "/0123456789abcde", ""):
            with self.subTest(location=location):
                client = transport(lambda r, location=location: httpx.Response(303, headers={"Location": location}))
                self.assertEqual(client.create(paste="Pikachu", title="", author="", notes=""),
                                 PasteOutcome(None, "pokepaste_unexpected_location"))

    def test_failures_are_classified_and_never_invent_a_url(self):
        cases = [
            (lambda r: httpx.Response(400), PasteOutcome(None, "pokepaste_http_400")),
            (lambda r: httpx.Response(503), PasteOutcome(None, "pokepaste_http_503", retry=True)),
            (lambda r: httpx.Response(429), PasteOutcome(None, "pokepaste_http_429", retry=True)),
            (lambda r: httpx.Response(200, text="<html>"), PasteOutcome(None, "pokepaste_http_200")),
            (lambda r: httpx.Response(303, headers={"Location": "https://evil.example/0123456789abcdef"}),
             PasteOutcome(None, "pokepaste_unexpected_location")),
        ]
        for handler, expected in cases:
            with self.subTest(expected=expected.code):
                self.assertEqual(transport(handler).create(paste="x", title="", author="", notes=""), expected)

    def test_network_errors_are_retryable(self):
        def refuse(request):
            raise httpx.ConnectError("down", request=request)

        def lost(request):
            raise httpx.ReadTimeout("lost", request=request)

        self.assertEqual(transport(refuse).create(paste="x", title="", author="", notes="").code, "pokepaste_unreachable")
        self.assertTrue(transport(lost).create(paste="x", title="", author="", notes="").retry)

    def test_empty_or_oversized_text_is_not_sent(self):
        calls = []
        client = transport(lambda r: calls.append(r) or httpx.Response(303))
        self.assertEqual(client.create(paste=" ", title="", author="", notes="").code, "pokepaste_invalid_paste")
        self.assertEqual(client.create(paste="x" * 7000, title="", author="", notes="").code, "pokepaste_invalid_paste")
        self.assertEqual(calls, [])


class WiringTests(unittest.TestCase):
    def config(self, **flags):
        return APIConfig(
            supabase_url="https://example.supabase.co",
            supabase_service_role_key="service",
            discord_webhook_url="https://discord.com/api/webhooks/1/" + "a" * 30,
            **flags,
        )

    def test_off_by_default_and_without_migration_078_columns(self):
        self.assertFalse(APIConfig.from_env({}).public_team_pastes_enabled)
        self.assertTrue(APIConfig.from_env({"POKEAPP_PUBLIC_TEAM_PASTES_ENABLED": "true"}).public_team_pastes_enabled)
        announcer = create_announcer(self.config())
        self.assertIsNone(announcer._dispatcher.pastes)
        self.assertNotIn("public_paste", announcer._dispatcher.outbox._columns)

    def test_enabled_reads_and_writes_078_columns(self):
        announcer = create_announcer(self.config(public_team_pastes_enabled=True))
        self.assertIsInstance(announcer._dispatcher.pastes, Pokepaste)
        self.assertEqual(announcer._dispatcher.outbox._columns, COLUMNS + PASTE_COLUMNS)
        self.assertEqual(
            SupabaseAnnouncementRepository(object(), public_pastes=False)._columns, COLUMNS
        )


if __name__ == "__main__":
    unittest.main()
