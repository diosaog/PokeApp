"""Personal save (065): sync without an active season, «Mi PC» outside seasons."""

import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import Mock

from phase9_fixtures import FakeParser, observed
from test_api_phase8b import TRAINER_ID

from app.application.personal_saves import GAMES, PERSONAL, PersonalSaves
from app.launcher.backend import BackendError
from app.launcher.journal import LocalJournal, LocalReceipt
from app.launcher.trusted_sync import TrustedStore, deliver_trusted, save_paths
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.models import SaveFingerprint
from app.save_parser.registration import observation_digest

DATA = b"synthetic personal save bytes"
HASH = sha256(DATA).hexdigest()
ORIGIN = "https://api.invalid"


class Repo:
    def __init__(self):
        self.row = None
        self.writes = 0

    def get(self, trainer_id):
        return self.row if self.row and self.row["trainer_id"] == trainer_id else None

    def upsert(self, row):
        self.writes += 1
        self.row = row


class PersonalSaveServiceTests(unittest.TestCase):
    def setUp(self):
        self.repo, self.parser = Repo(), FakeParser()
        self.service = PersonalSaves(self.repo, self.parser)
        self.digest = observation_digest(self.parser.value, self.parser.version)

    def test_first_upload_parses_on_the_server_and_feeds_my_pc(self):
        self.assertEqual(self.service.context(TRAINER_ID), {"current_save_id": None})
        self.assertEqual(self.service.pc(TRAINER_ID).status, "no_current_save")
        receipt = self.service.receive(TRAINER_ID, HASH, self.digest, DATA)
        self.assertEqual((receipt.season_id, receipt.save_id, receipt.is_current), (PERSONAL, TRAINER_ID, True))
        self.assertEqual(self.parser.calls, 1)
        pc = self.service.pc(TRAINER_ID)
        game = self.parser.value.game if self.parser.value.game in GAMES else None  # shown only for Gen 6/7, as in seasons
        self.assertEqual((pc.status, str(pc.save.id), pc.save.game), ("ready", TRAINER_ID, game))
        self.assertTrue(all(slot.pokemon_entity_id is None for slot in pc.pokemon))
        self.assertEqual(self.service.receipt(TRAINER_ID, HASH).sha256, HASH)

    def test_same_file_again_is_an_exact_replay_without_parsing(self):
        self.service.receive(TRAINER_ID, HASH, self.digest, DATA)
        again = self.service.receive(TRAINER_ID, HASH, self.digest, DATA)
        self.assertEqual((self.parser.calls, self.repo.writes, again.is_current), (1, 1, True))

    def test_client_cannot_claim_what_the_file_does_not_hold(self):
        with self.assertRaises(SeasonAdminRejected) as wrong_digest:
            self.service.receive(TRAINER_ID, HASH, "0" * 64, DATA)
        self.assertEqual(wrong_digest.exception.code, "SAVE_PARSE_MISMATCH")
        with self.assertRaises(SeasonAdminRejected) as wrong_hash:
            self.service.receive(TRAINER_ID, "f" * 64, self.digest, DATA)
        self.assertEqual(wrong_hash.exception.code, "SAVE_HASH_MISMATCH")
        self.assertIsNone(self.repo.row)

    def test_a_newer_file_replaces_the_personal_save_and_old_receipts_are_gone(self):
        self.service.receive(TRAINER_ID, HASH, self.digest, DATA)
        newer = DATA + b" saved again in game"
        self.service.receive(TRAINER_ID, sha256(newer).hexdigest(), self.digest, newer)
        with self.assertRaises(SeasonAdminRejected) as old:
            self.service.receipt(TRAINER_ID, HASH)
        self.assertEqual(old.exception.status, 404)


class PersonalDeliveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = TrustedStore(LocalJournal(Path(temp.name) / "sync.db"))
        local = LocalReceipt("fixture", 1, SaveFingerprint(sha256=HASH, size=len(DATA)), "fixture/1", observed())
        self.store.enqueue_raw(ORIGIN, TRAINER_ID, PERSONAL, local, DATA)
        self.row = self.store.pending(ORIGIN, TRAINER_ID)
        self.receipt = {
            "status": "registered", "save_id": TRAINER_ID, "trainer_id": TRAINER_ID,
            "season_id": PERSONAL, "sha256": HASH, "parser_version": "fixture/1",
            "observation_digest": self.row["digest"], "is_current": True,
        }  # fmt: skip
        self.session = Mock()

    def test_paths(self):
        self.assertEqual(save_paths(PERSONAL), ("/v1/me/save", "/v1/me/pc"))

    def test_delivered_to_the_personal_record_and_confirmed_only_by_readback(self):
        self.session.request.side_effect = [None, {"current_save_id": None}, {"status": "not_ready", "save": None}]
        self.session.upload.return_value = self.receipt
        with self.assertRaises(BackendError):
            deliver_trusted(self.session, self.store, self.row, selected_hash=HASH)
        self.assertIsNone(self.store.receipt(ORIGIN, TRAINER_ID, PERSONAL, HASH))
        self.assertTrue(self.session.upload.call_args.args[0].startswith("/v1/me/save/raw?"))
        self.session.request.side_effect = [self.receipt, {"status": "ready", "save": {"id": TRAINER_ID}}]
        deliver_trusted(self.session, self.store, self.store.pending(ORIGIN, TRAINER_ID), selected_hash=HASH)
        self.assertEqual(self.session.request.call_args_list[-1].args, ("GET", "/v1/me/pc"))
        self.assertIsNotNone(self.store.receipt(ORIGIN, TRAINER_ID, PERSONAL, HASH))
        self.assertEqual(self.session.upload.call_count, 1)  # no duplicate upload


if __name__ == "__main__":
    unittest.main()
