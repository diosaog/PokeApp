"""Administración › Avisos: the few scenarios that define the detector."""

import unittest
from dataclasses import replace
from uuid import uuid4

from fastapi.testclient import TestClient
from test_api_phase8b import TRAINER_ID, FakePrincipalRepository, FakeTokenVerifier

from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.application.save_audit import SaveAudit, snapshot_facts
from app.domain.save_audit import analyze

SEASON = "22222222-2222-4222-8222-222222222222"
TRAINER = "33333333-3333-4333-8333-333333333333"
AUTH = {"Authorization": "Bearer opaque-token"}
GOLD_CAP = "chapa_dorada"
EARLY, MIDDLE, LATE = (
    "2026-11-08T10:00:00+00:00",
    "2026-11-08T11:00:00+00:00",
    "2026-11-08T12:00:00+00:00",
)


def mon(species=25, level=30, ivs=None, ability=65, nature=3, item=0, moves=(33, 45), pid=1000, ec=2000, **extra):
    stats = dict(zip(("hp", "atk", "defense", "spa", "spd", "spe"), ivs or (10, 11, 12, 13, 14, 15)))
    return {
        "species": f"Pokémon #{species}",
        "nickname": "Nido",
        "level": level,
        "item": f"Item #{item}" if item else "",
        "moves": [{"name": f"Move #{m}", "pp": 20} for m in moves],
        "is_shiny": False,
        "gender": "M",
        "form": 0,
        "ability": f"Ability #{ability}",
        "nature": f"Nature #{nature}",
        "ivs": stats,
        "evs": dict(zip(stats, (0, 0, 0, 0, 0, 0))),
        "identity_evidence": {
            "schema_version": 2,
            "format": 6,
            "pid": pid,
            "encryption_constant": ec,
            "ot_tid": 1,
            "ot_sid": 2,
            "ot_name": "Antonio",
            "ot_gender": 0,
            "origin_version": 24,
            "language": 7,
            "met_location": 10,
            "met_level": 5,
            "met_date": "2026-10-01",
            "egg_location": 0,
            "egg_date": None,
            "ivs": list(stats.values()),
            "is_egg": False,
            "source_trainer_match": True,
        },
        **extra,
    }


def payload(party=(), boxes=()):
    return {
        "game": "X",
        "party": [
            {"slot_number": i + 1, "pokemon": party[i] if i < len(party) else None} for i in range(6)
        ],
        "boxes": [
            {
                "box_number": 1,
                "slots": [
                    {"slot_number": i + 1, "pokemon": boxes[i] if i < len(boxes) else None} for i in range(30)
                ],
            }
        ],
    }


def bag(**counts):
    items = {str(k[1:]): v for k, v in counts.items()}
    return {"items": items, "pouches": {k: "Items" for k in items}}


def compare(before, after, operations=None, *, before_bag=None, after_bag=None):
    return analyze(
        {"payload": before, "uploaded_at": EARLY, "bag": before_bag, "friendship": None},
        {"payload": after, "uploaded_at": LATE, "bag": after_bag, "friendship": None},
        operations or {},
    )


class DetectionTests(unittest.TestCase):
    def test_1_ivs_changed_without_a_cap_are_noticed(self):
        result = compare(payload([mon()]), payload([mon(ivs=(31,) * 6)]))
        notice = result["notices"][0]
        self.assertEqual((notice["severity"], notice["category"]), ("alta", "pokemon"))
        self.assertEqual(notice["title"], "Los seis IVs han pasado a 31")
        self.assertEqual(len(notice["changes"]), 6)
        first = notice["changes"][0]
        self.assertEqual((first["label"], first["before"], first["after"]), ("IV de PS", 10, 31))
        self.assertEqual(notice["origin"], "desconocido")

    def test_2_ivs_changed_with_a_recorded_cap_are_not_noticed(self):
        result = compare(
            payload([mon()]),
            payload([mon(ivs=(31,) * 6)]),
            {
                "training": [
                    {
                        "item_code": GOLD_CAP,
                        "finished_at": MIDDLE,
                        "pid": 1000,
                        "ec": 2000,
                        "operation_id": str(uuid4()),
                    }
                ]
            },
        )
        self.assertEqual(result["notices"], [])

    def test_3_objects_added_without_origin_are_noticed(self):
        result = compare(payload([mon()]), payload([mon()]), before_bag=bag(i645=0), after_bag=bag(i645=5))
        notice = result["notices"][0]
        self.assertEqual((notice["severity"], notice["category"]), ("media", "objetos"))
        change = notice["changes"][0]
        self.assertEqual(
            (change["item"], change["before"], change["after"], change["delta"], change["justified"], change["unjustified"]),
            ("Item #645", 0, 5, 5, 0, 5),
        )

    def test_4_an_object_bought_legitimately_is_justified(self):
        delivery = {
            "id": str(uuid4()),
            "game_item_id": 645,
            "status": "DELIVERED",
            "reserved_at": MIDDLE,
            "finished_at": MIDDLE,
            "item_name": "Cápsula Habilidad",
        }
        result = compare(
            payload([mon()]),
            payload([mon()]),
            {"deliveries": [delivery]},
            before_bag=bag(i645=0),
            after_bag=bag(i645=1),
        )
        self.assertEqual(result["notices"], [])
        self.assertEqual(result["credited_deliveries"], [delivery["id"]])

    def test_5_normal_play_stays_silent(self):
        before = payload(
            [mon(species=4, level=15, item=234), mon(species=25, pid=7, ec=8)],
            [mon(species=133, level=20, pid=9, ec=10)],
        )
        after = payload(
            [mon(species=25, pid=7, ec=8, moves=(33, 45, 85))],
            [
                mon(species=5, level=19, pid=1000, ec=2000, ability=66, item=0),
                mon(species=134, level=20, pid=9, ec=10, ability=11),
                mon(species=90, level=8, pid=55, ec=66),
            ],
        )
        result = compare(before, after, before_bag=bag(i17=3), after_bag=bag(i17=9, i234=1, i50=20))
        self.assertEqual(result["notices"], [])

    def test_held_object_returning_to_the_bag_is_not_an_increase(self):
        result = compare(
            payload([mon(item=234)]),
            payload([mon(item=0)]),
            before_bag=bag(),
            after_bag=bag(i234=1),
        )
        self.assertEqual(result["notices"], [])


class FakeRepository:
    def __init__(self, saves):
        self.saves, self.records, self.runs = saves, [], {}

    def pending(self, season, trainer, limit):
        return [
            {"season_id": SEASON, "trainer_id": TRAINER, "save_file_id": sid}
            for sid in self.saves
            if sid not in self.runs
        ]

    def context(self, season, trainer, save_id):
        index = list(self.saves).index(save_id)
        def side(sid):
            return {
                "save": {"id": sid, "sha256": "0" * 64, "uploaded_at": EARLY if sid == "a" else LATE,
                         "trainer_id": TRAINER, "season_id": SEASON, "storage_bucket": "raw-saves",
                         "storage_key": f"trusted/{TRAINER}/{SEASON}/{'0' * 64}.sav"},
                "payload": self.saves[sid],
                "revision": list(self.saves).index(sid) + 1,
            }
        previous = side(list(self.saves)[index - 1]) | {"bag": None, "friendship": None} if index else None
        return {"current": side(save_id), "previous": previous, "operations": {}}

    def read_raw(self, saved):
        return b"raw"

    def record(self, request):
        # The database: one analysis per save.
        if request["save_file_id"] in self.runs:
            return {"recorded": False, "notices": 0}
        self.runs[request["save_file_id"]] = request
        self.records.append(request)
        return {"recorded": True, "notices": len(request["notices"])}


class Reader:
    def audit_snapshot(self, data):
        return {
            "pouches": [{"type": "Items", "items": [{"id": 645, "count": 2}]}],
            "pokemon": [{"pid": 1000, "ec": 2000, "friendship": 70}],
        }


class IdempotencyTests(unittest.TestCase):
    def test_6_repeated_sync_never_duplicates_a_notice(self):
        repository = FakeRepository({"a": payload([mon()]), "b": payload([mon(ivs=(31,) * 6)])})
        audit = SaveAudit(repository, Reader())
        self.assertEqual(audit.run(SEASON)["processed"], 2)
        self.assertEqual(audit.run(SEASON)["processed"], 0)  # the same saves again
        self.assertEqual(len(repository.records), 2)
        self.assertEqual(repository.runs["a"]["status"], "baseline")
        self.assertEqual(len(repository.runs["b"]["notices"]), 1)
        self.assertEqual(
            snapshot_facts(Reader().audit_snapshot(b""))[1], {"1000:2000": 70}
        )


class FakeNotices:
    def __init__(self):
        self.calls = []

    def read(self, actor, season):
        self.calls.append(("read", actor, season))
        return {
            "season_id": season,
            "season_status": "active",
            "activated_at": EARLY,
            "pending_saves": 0,
            "analyzed_saves": 0,
            "last_analyzed_at": None,
            "trainers": [],
            "notices": [],
        }

    def update(self, actor, season, notice, status, note, operation, digest):
        self.calls.append(("update", actor, season, notice, status, note, operation, digest))
        return {
            "id": notice,
            "trainer_id": TRAINER,
            "display_name": "Samu",
            "game": "X",
            "detected_at": EARLY,
            "updated_at": LATE,
            "category": "objetos",
            "severity": "media",
            "status": status,
            "title": "Objeto con aumento sin verificar",
            "summary": "s",
            "origin": "desconocido",
            "pokemon": None,
            "changes": [
                {
                    "field": "item_645",
                    "label": "Objeto",
                    "kind": "item",
                    "before": 0,
                    "after": 5,
                    "severity": "media",
                    "reason": "r",
                }
            ],
            "operations": [],
            "compared": None,
            "detector_version": 1,
            "events": [],
        }


def client(notices, admin=True):
    principals = FakePrincipalRepository()
    principals.trainer = replace(principals.trainer, is_admin=admin)
    return TestClient(
        create_app(
            container=ApiContainer(
                token_verifier=FakeTokenVerifier(),
                principal_repository=principals,
                save_audit_repository=notices,
            )
        )
    )


class AccessTests(unittest.TestCase):
    def test_7_a_trainer_without_administrator_rights_is_denied(self):
        notices = FakeNotices()
        api = client(notices, admin=False)
        base = f"/v1/admin/seasons/{SEASON}/notices"
        self.assertEqual(api.get(base, headers=AUTH).status_code, 403)
        self.assertEqual(
            api.post(
                f"{base}/{uuid4()}/status",
                json={"status": "justified", "note": "Lo consiguió jugando"},
                headers={**AUTH, "Idempotency-Key": str(uuid4())},
            ).status_code,
            403,
        )
        self.assertEqual(notices.calls, [])

    def test_administrator_reviews_a_notice_with_an_observation(self):
        notices = FakeNotices()
        api = client(notices)
        base = f"/v1/admin/seasons/{SEASON}/notices"
        self.assertEqual(api.get(base, headers=AUTH).status_code, 200)
        operation, notice = str(uuid4()), str(uuid4())
        response = api.post(
            f"{base}/{notice}/status",
            json={"status": "justified", "note": "  El entrenador confirma que las consiguió jugando  "},
            headers={**AUTH, "Idempotency-Key": operation},
        )
        self.assertEqual(response.status_code, 200)
        call = notices.calls[-1]
        self.assertEqual(call[0], "update")
        self.assertEqual(call[1], str(TRAINER_ID))
        self.assertEqual(call[4:7], ("justified", "El entrenador confirma que las consiguió jugando", operation))
        self.assertEqual(response.json()["status"], "justified")


if __name__ == "__main__":
    unittest.main()
