from app.save_parser.models import ObservedSave
import json


def pokemon(pid=123):
    return dict(species_id=25, nickname="Fixture", level=20, form=0, gender=0,
        shiny=False, is_egg=False, ability_id=9, nature_id=0, item_id=0,
        moves=[dict(id=85, pp=15)] + [dict(id=0, pp=0)] * 3, ivs=[20]*6, evs=[0]*6,
        identity=dict(schema_version=1, format=5, pid=pid, ot_tid=123, ot_sid=456,
            origin_version=22, language=2, ot_name="Fixture", ot_gender=0, ivs=[20]*6))


def observed(party=None, boxes=None):
    return ObservedSave.model_validate_json(json.dumps(dict(game="B2W2", generation=5,
        trainer=dict(name="Fixture", tid=123, sid=456, gender=0, language=2),
        party=party if party is not None else [pokemon()] + [None]*5,
        boxes=boxes if boxes is not None else [dict(number=1, slots=[None]*30)])))


class FakeParser:
    version = "fixture/1"

    def __init__(self, value=None):
        self.value = value or observed()
        self.calls = 0

    def parse(self, data):
        self.calls += 1
        return self.value
