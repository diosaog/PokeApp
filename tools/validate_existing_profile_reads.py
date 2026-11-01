"""Read-only public projection of genuine observations; no login or writes."""

import argparse
import json
from pathlib import Path
import re

from app.api.main import create_app  # initialize the existing API import graph
from app.application.frontend_reads import FrontendReads
from tools.production_readonly import query


class ReadOnly:
    def rows(self, table, columns, *, filters=None, offset=0, limit=500, **kwargs):
        assert table in {"seasons", "season_players", "season_player_stats",
                         "trainers", "trainer_personal_saves"}
        assert re.fullmatch("[a-z0-9_,]+", columns)
        clauses = []
        for key, value in (filters or {}).items():
            assert re.fullmatch("[a-z_]+", key)
            if value is None:
                clauses.append(key + " is null")
            else:
                literal = "true" if value is True else "false" if value is False else "'" + str(value).replace("'", "''") + "'"
                clauses.append(key + " = " + literal)
        return query("select " + columns + " from public." + table
                     + (" where " + " and ".join(clauses) if clauses else "")
                     + " limit " + str(int(limit)) + " offset " + str(int(offset)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    seasons = query("select id from public.seasons where status='draft'")
    assert len(seasons) == 1, "Select exactly one draft for the owner's requested acceptance"
    report = []
    for name in ("Iker", "Aaron", "Anto"):
        trainers = query("select id from public.trainers where display_name='" + name + "'")
        assert len(trainers) == 1
        data = FrontendReads(ReadOnly()).trainer_collection(seasons[0]["id"], trainers[0]["id"])
        assert all(key not in data.model_dump_json() for key in (
            "identity_evidence", "source_hash", "pokemon_entity_id", '"ivs"', '"ability"', "storage_key"))
        if name == "Aaron":
            assert data.status == "no_current_save" and data.reason == "no_synced_save"
        else:
            assert data.status == "ready" and data.source == "personal" and data.game == "Y"
            assert all(p.pokemon.item_generation == 6 for p in data.pokemon)
        report.append(dict(trainer=name, status=data.status, source=data.source, reason=data.reason,
            pokemon_count=len(data.pokemon), private_fields_absent=True,
            held_item_counts={str(i): sum(p.pokemon.item == f"Item #{i}" for p in data.pokemon) for i in (158, 217)}))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
