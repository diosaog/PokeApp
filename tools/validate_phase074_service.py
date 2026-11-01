"""Real native parser/writer + virtual training service + disposable PostgreSQL.

The caller supplies an isolated synthetic native source fixture. No original is
modified; blobs stay in memory and every database fixture rolls back.
"""

from hashlib import sha256
import json
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

from app.application.save_ingestion import registration_request
from app.application.training import VirtualTraining
from app.domain.shop_item_uses import GAMES
from app.repositories.supabase.season_admin import SeasonAdminRejected
from app.save_parser.adapter import PkhexProcessParser
from app.save_parser.write_models import WriteIntent
from app.save_parser.writer import NativeWriteError, PkhexProcessWriter


def validate(pg, parser_executable, fixture_dir, *, games=GAMES, trace_folder=None):
    import psycopg
    from psycopg.types.json import Jsonb

    class RecordingNative(PkhexProcessWriter):
        trace_directory = None

        def _run(self, mode, request):
            if self.trace_directory is None:
                return super()._run(mode, request)
            import subprocess

            folder = self.trace_directory
            folder.mkdir(parents=True, exist_ok=True)
            self.trace_sequence = getattr(self, "trace_sequence", 0) + 1
            label = f"{self.trace_sequence:04d}-{mode.removeprefix('--')}"
            (folder / f"{label}.request.json").write_text(json.dumps(request), encoding="utf8")
            real_popen = subprocess.Popen
            child_pid = None

            class Tee:
                def __init__(self, stream, destination):
                    self.stream, self.destination = stream, destination.open("wb")
                def read(self, size):
                    data = self.stream.read(size)
                    self.destination.write(data)
                    self.destination.flush()
                    return data
                def close(self):
                    self.stream.close()
                    self.destination.close()
                def __getattr__(self, key): return getattr(self.stream, key)

            def popen(*args, **kwargs):
                nonlocal child_pid
                child = real_popen(*args, **kwargs)
                child_pid = child.pid
                (folder / f"{label}.process.json").write_text(json.dumps({
                    "pid": child.pid, "mode": mode, "native_path": str(self.executable),
                    "request": f"{label}.request.json", "response": f"{label}.response.json",
                    "stderr": f"{label}.stderr.txt",
                }, indent=2), encoding="utf8")
                child.stdout = Tee(child.stdout, folder / f"{label}.response.json")
                child.stderr = Tee(child.stderr, folder / f"{label}.stderr.txt")
                return child

            try:
                with patch("subprocess.Popen", popen):
                    return super()._run(mode, request)
            except Exception as error:
                (folder / "failure.json").write_text(json.dumps({"mode": mode, "error": str(error),
                    "source_sha256": request.get("intent", {}).get("expected_sha256"),
                    "native_path": str(self.executable), "native_sha256": sha256(self.executable.read_bytes()).hexdigest(),
                    "pid": child_pid, "request": f"{label}.request.json", "response": f"{label}.response.json",
                    "stderr": f"{label}.stderr.txt",
                    "intent": request.get("intent")}, indent=2), encoding="utf8")
                raise

    parser, native = PkhexProcessParser(Path(parser_executable)), RecordingNative(Path(parser_executable))
    checks = []
    for game in games:
        for family, code, change in (
            ("silver", "chapa_plateada", {"kind": "iv", "nature_id": None, "stat": "hp"}),
            ("mint", "menta_naturaleza", {"kind": "nature", "nature_id": 3, "stat": None}),
            ("gold", "chapa_dorada", {"kind": "ivs", "nature_id": None, "stat": None}),
        ):
            case_dir = Path(fixture_dir) / game / "party" / family
            if trace_folder is not None:
                native.trace_directory = Path(trace_folder) / game / family
            source = (case_dir / "source").read_bytes()
            fixture_mutation = json.loads((case_dir / "request.json").read_text("utf8"))["intent"]["mutation"]
            change = change | {"nature_id": fixture_mutation["nature_id"], "stat": fixture_mutation["stat"]}
            observed = parser.parse(source)
            sid, oldsid, tid, pid, purchase, operation = (str(uuid4()) for _ in range(6))
            raw_hash = sha256(source).hexdigest()
            initial = registration_request(sid, tid, raw_hash, None, observed, parser.version, {"head": None, "entities": []})
            with psycopg.connect(host="127.0.0.1", port=pg.port, user="supabase_admin", dbname=pg.database, autocommit=False) as connection:
                try:
                    connection.execute("insert into public.trainers(id,display_name,slug) values(%s,'074 Service Fixture',%s)", (tid, "074-service-" + tid))
                    connection.execute("insert into public.seasons(id,name,status,started_at,created_by_trainer_id,discarded_at) values(%s,'074 old purchase','discarded',now(),%s,now()),(%s,'074 native target','active',now(),%s,null)", (oldsid, tid, sid, tid))
                    connection.execute("insert into public.season_players(id,season_id,trainer_id,status) values(%s,%s,%s,'active'),(gen_random_uuid(),%s,%s,'active')", (pid, sid, tid, oldsid, tid))
                    connection.execute("insert into public.season_player_stats(season_player_id,season_id,trainer_id) select id,season_id,trainer_id from public.season_players where trainer_id=%s on conflict do nothing", (tid,))
                    connection.execute("insert into public.purchases(id,season_id,trainer_id,season_player_id,shop_item_id,quantity,unit_price,acquisition_type,status) select %s,%s,%s,p.id,i.id,1,6,'paid','pending' from public.season_players p cross join public.shop_items i where p.season_id=%s and p.trainer_id=%s and i.code=%s", (purchase, oldsid, tid, oldsid, tid, code))
                    connection.execute("select public.api_register_save(%s)", (Jsonb(initial | {"operation": "register"}),)).fetchone()
                    connection.execute("set local role service_role")
                    blobs = {initial["storage_key"]: source}

                    class Repository:
                        def execute(self, action, season_id, trainer_id, **values):
                            request = {"operation": action, "season_id": season_id, "trainer_id": trainer_id, **values}
                            with connection.transaction():
                                return connection.execute("select public.api_training_operation(%s)", (Jsonb(request),)).fetchone()[0]

                        def read_source(self, saved):
                            data = blobs[saved["storage_key"]]
                            assert sha256(data).hexdigest() == saved["sha256"]
                            return data

                        def store_raw(self, key, data, digest):
                            assert sha256(data).hexdigest() == digest
                            assert key not in blobs or blobs[key] == data
                            blobs[key] = data

                    service = VirtualTraining(Repository(), parser, native)
                    listing = service.listing(sid, tid)
                    # Native matrix fixtures deliberately clone party1/box1.
                    # The service must keep those ambiguous targets excluded;
                    # use an independently eligible party member instead.
                    target = next(t for t in listing["targets"] if t["source"] == "party"
                        and (family == "mint" or t["pokemon"]["ivs"]["hp"] < 31))
                    if family == "mint" and target["pokemon"]["nature_id"] == change["nature_id"]:
                        change = change | {"nature_id": (change["nature_id"] + 1) % 25}
                    body = {"purchase_id": purchase, "pokemon_entity_id": target["pokemon_entity_id"],
                            "source_sha256": raw_hash, "change": change}
                    reserved = service.reserve(sid, tid, operation, body)
                    assert reserved["status"] == "RESERVED" and reserved["purchase_season_id"] == oldsid
                    prepared = native.prepare(source, WriteIntent.create(**reserved["intent"]))
                    # Corruption cannot complete or consume; savepoint keeps the
                    # fixture usable after this expected native refusal.
                    corrupt = bytes([prepared.output[0] ^ 1]) + prepared.output[1:]
                    try:
                        service.complete(sid, tid, operation, corrupt)
                        raise AssertionError("corrupted native output accepted")
                    except NativeWriteError:
                        pass
                    assert connection.execute("select status from public.purchases where id=%s", (purchase,)).fetchone()[0] == "pending"
                    complete = service.complete(sid, tid, operation, prepared.output)
                    assert complete["status"] == "APPLIED"
                    assert service.complete(sid, tid, operation, prepared.output) == complete
                    assert connection.execute("select status,season_id from public.purchases where id=%s", (purchase,)).fetchone() == ("used", __import__('uuid').UUID(oldsid))
                    ctx = service.repository.execute("context", sid, tid)
                    assert any(o["pokemon_entity_id"] == target["pokemon_entity_id"] and o["source"] == "party"
                        and o["slot_number"] == target["slot_number"] for o in ctx["observations"])
                    assert ctx["save"]["sha256"] == sha256(prepared.output).hexdigest()
                    checks.append({"game": game, "effect": family, "status": "PASS", "same_entity": True,
                                   "old_purchase_preserved": True, "corrupt_refused": True, "replay_once": True})
                finally:
                    connection.rollback()
            print(f"PASS real service/native/PostgreSQL {game} {family}", flush=True)
    return {"result": "PASS", "cases": checks, "games": list(games), "count": len(checks),
            "boundary": "Synthetic fixtures only; originals read-only, output bytes in memory, SQL rolled back."}
