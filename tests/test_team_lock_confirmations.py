"""083: one Discord announcement per explicit «Fijar Equipo» confirmation.

Everything external is mocked (outbox, Discord webhook, Pokepast.es): no
request leaves the process and no real Team Lock is touched.
"""

import unittest
from copy import deepcopy
from datetime import timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.application.discord_webhook import Outcome
from app.application.pokepaste import PasteOutcome
from app.domain.showdown import export_team
from team_lock_fixtures import MATCHDAY, SAVE, SEASON, MemoryAtomicTeamLocks
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier
from test_public_team_pastes import NOW, PUBLIC_TEAM, URL_1, URL_2, Harness, mon, row, text_of

FIRST_TEAM = deepcopy(PUBLIC_TEAM)
OTHER_TEAM = [mon(711, nickname="Jalowin", item=540, moves=(221,), gender="M", form=2)] + deepcopy(PUBLIC_TEAM[1:])


def confirmation(cid, team, *, replacement, minutes=0, **changes):
    value = dict(id=cid, team_lock_id="lock", season_id="s", matchday_id="day", trainer_id="t1",
                 save_file_id="save", public_team_snapshot=deepcopy(team), is_replacement=replacement,
                 confirmed_at=(NOW + timedelta(minutes=minutes)).isoformat())
    value.update(changes)
    return value


def harness(*confirmations, rows, pastes=()):
    h = Harness(*pastes, rows=rows)
    h.tables["team_lock_confirmations"] = list(confirmations)
    # The lock itself already holds the latest team; earlier rows must not use it.
    h.tables["team_locks"][0]["public_team_snapshot"] = deepcopy(confirmations[-1]["public_team_snapshot"])
    return h


class ConfirmationDeliveryTests(unittest.TestCase):
    def test_a_new_confirmation_posts_a_new_message_and_never_edits_the_old_one(self):
        sent = row(id="a0", subject={"lock_id": "lock", "confirmation_id": "c1"}, status="sent",
                   delivered_revision=1, discord_message_id="111", public_paste_url=URL_1, public_paste_revision=1)
        new = row(id="a1", subject={"lock_id": "lock", "confirmation_id": "c2"})
        h = harness(confirmation("c1", FIRST_TEAM, replacement=False),
                    confirmation("c2", FIRST_TEAM, replacement=True, minutes=5),
                    rows=[sent, new], pastes=[PasteOutcome(URL_2, "created")])
        h.run()
        self.assertEqual((len(h.webhook.posts), h.webhook.edits), (1, []))
        self.assertEqual((h.stored["status"], h.stored["discord_message_id"], h.stored["public_paste_url"]),
                         ("sent", "123", URL_2))
        self.assertEqual({k: h.outbox.rows["a0"][k] for k in ("status", "discord_message_id", "public_paste_url")},
                         {"status": "sent", "discord_message_id": "111", "public_paste_url": URL_1})
        message = text_of(h.webhook.posts[0])
        self.assertIn("confirmado de nuevo", message)
        self.assertIn(f"Ver equipo:** {URL_2}", message)

    def test_each_row_announces_its_own_immutable_snapshot(self):
        # Two quick confirmations: the first is delivered after the second replaced the lock.
        first = row(id="a1", subject={"lock_id": "lock", "confirmation_id": "c1"})
        second = row(id="a2", subject={"lock_id": "lock", "confirmation_id": "c2"})
        h = harness(confirmation("c1", FIRST_TEAM, replacement=False),
                    confirmation("c2", OTHER_TEAM, replacement=True, minutes=1),
                    rows=[first, second], pastes=[PasteOutcome(URL_1, "created"), PasteOutcome(URL_2, "created")])
        h.run()
        self.assertEqual(len(h.webhook.posts), 2)
        self.assertEqual([c["paste"] for c in h.pastes.calls],
                         [export_team(team, generation=6, projection="public").text for team in (FIRST_TEAM, OTHER_TEAM)])
        self.assertIn("Tiburón (Garchomp)", text_of(h.webhook.posts[0]))
        self.assertIn("Jalowin (Gourgeist)", text_of(h.webhook.posts[1]))
        self.assertNotIn("confirmado de nuevo", text_of(h.webhook.posts[0]))

    def test_an_uncertain_post_is_never_resent_and_does_not_block_the_next_confirmation(self):
        first = row(id="a1", subject={"lock_id": "lock", "confirmation_id": "c1"})
        second = row(id="a2", subject={"lock_id": "lock", "confirmation_id": "c2"})
        h = harness(confirmation("c1", FIRST_TEAM, replacement=False),
                    confirmation("c2", FIRST_TEAM, replacement=True, minutes=1), rows=[first, second])
        h.webhook.outcomes = [Outcome("uncertain", "response_timeout")]
        h.run()
        h.run(minutes=30)
        self.assertEqual(len(h.webhook.posts), 2)
        self.assertEqual((h.outbox.rows["a1"]["status"], h.outbox.rows["a2"]["status"]), ("uncertain", "sent"))

    def test_a_confirmation_from_another_lock_or_trainer_is_skipped(self):
        h = harness(confirmation("c1", FIRST_TEAM, replacement=False, trainer_id="t2"),
                    rows=[row(subject={"lock_id": "lock", "confirmation_id": "c1"})])
        h.run()
        self.assertEqual((h.webhook.posts, h.stored["status"], h.stored["last_error"]), ([], "skipped", "confirmation_mismatch"))


class ConfirmationKeyApiTests(unittest.TestCase):
    def setUp(self):
        self.repository = MemoryAtomicTeamLocks()
        self.client = TestClient(create_app(container=ApiContainer(
            token_verifier=FakeTokenVerifier(), principal_repository=FakePrincipalRepository(),
            team_lock_repository=self.repository)))
        self.addCleanup(self.client.close)
        self.path = f"/v1/seasons/{SEASON}/matchdays/{MATCHDAY}/team-lock"
        self.auth = {"Authorization": "Bearer x"}
        self.body = {"save_file_id": SAVE}

    def put(self, **headers):
        return self.client.put(self.path, json=self.body, headers=dict(self.auth, **headers))

    def test_the_web_key_reaches_the_confirmation_and_a_retry_repeats_it(self):
        self.assertEqual(self.put(**{"Idempotency-Key": "fijar-1"}).status_code, 200)
        self.assertEqual(self.put(**{"Idempotency-Key": "fijar-1"}).status_code, 200)
        self.assertEqual(self.put(**{"Idempotency-Key": "fijar-2"}).status_code, 200)
        self.assertEqual([m.idempotency_key for m in self.repository.mutations], ["fijar-1", "fijar-1", "fijar-2"])

    def test_without_a_key_each_request_is_its_own_confirmation(self):
        self.put()
        self.put()
        keys = [m.idempotency_key for m in self.repository.mutations]
        self.assertEqual(len(set(keys)), 2)
        self.assertTrue(all(UUID(k) for k in keys))

    def test_a_malformed_key_is_refused_before_any_write(self):
        self.assertEqual(self.put(**{"Idempotency-Key": "con espacio"}).status_code, 422)
        self.assertEqual(self.repository.mutations, [])


if __name__ == "__main__":
    unittest.main()
