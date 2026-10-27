"""Phase 29 administrative robbery cancellation on a disposable PostgreSQL.

Bootstraps migrations 001-064 on an empty cluster and builds synthetic
robberies in every state the 057-061 flow can leave (requested, eligibility
verified, competitively adjudicated, physical apply started, cancelled by a
participant, committed). Proves: only an administrator, with a reason, can
cancel; only a robbery with nothing decided or physical is cancelled; the
cancellation releases both trainers, cancels the unconsumed item once and
returns its coins once (also across the purchase incident path); retries
replay, other data conflicts, concurrent attempts produce one effect; refusals
change nothing; archived seasons are immutable; grants stay closed. Synthetic
data only; transfer rows are inserted directly (the robbery engine itself is
covered by the Phase 24/27 validators).
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_accounts_local import LocalPG  # noqa: E402

HASH = "e" * 64
MIGRATIONS = len(list((Path(__file__).resolve().parents[1] / "supabase/v2/migrations").glob("*.sql")))
SHA = "{:064x}"
STATES = ("requested", "verified", "adjudicated", "applying", "participant_cancel", "committed")


class Fixture:
    def __init__(self, pg):
        self.pg = pg
        self.admin, self.player = str(uuid4()), str(uuid4())
        self.season = str(uuid4())
        pg.sql(f"""
        insert into trainers(id,display_name,slug,auth_user_id,is_admin) values
          ('{self.admin}','Admin','admin-29',gen_random_uuid(),true),
          ('{self.player}','Player','player-29',gen_random_uuid(),false);
        insert into seasons(id,name,created_by_trainer_id,status,started_at)
          values('{self.season}','Phase 29','{self.admin}','active',now());
        """)
        self.robberies = {state: self.robbery(i, state) for i, state in enumerate(STATES)}

    def scalar(self, query):
        return self.pg.sql(query).stdout.strip()

    def robbery(self, n, state):
        """A paid robbery item and the transfer rows the flow leaves in `state`."""
        robber, victim = str(uuid4()), str(uuid4())
        auth, purchase, entity = str(uuid4()), str(uuid4()), str(uuid4())
        saves = {side: str(uuid4()) for side in ("source", "destination")}
        revisions = {side: str(uuid4()) for side in saves}
        trainers = {"source": victim, "destination": robber}
        rows = []
        for side, save in saves.items():
            parsed = str(uuid4())
            rows.append(f"""
            insert into save_files(id,season_id,trainer_id,storage_key,original_filename,sha256,parser_status)
              values('{save}','{self.season}','{trainers[side]}','p29/{save}','synthetic.sav','{SHA.format(n * 10 + len(rows) + 1)}','parsed');
            insert into parsed_saves(id,save_file_id,parser_version,schema_version,payload)
              values('{parsed}','{save}','synthetic',1,'{{}}'::jsonb);
            insert into pokemon_identity_revisions(id,season_id,trainer_id,save_file_id,parsed_save_id,
              revision_number,capture_stream_id,capture_sequence,input_signature)
              values('{revisions[side]}','{self.season}','{trainers[side]}','{save}','{parsed}',1,
                gen_random_uuid(),1,'{SHA.format(900 + n * 10 + len(rows))}');""")
        plans = "null" if state == "requested" else "'{\"source\":{},\"destination\":{}}'::jsonb"
        adjudicated = "clock_timestamp()" if state in ("adjudicated", "committed") else "null"
        terminal = {"participant_cancel": "'CANCELLED'", "committed": "'COMMITTED'"}.get(state, "null")
        obligation = "'PHYSICAL_PENDING'" if state in ("adjudicated", "committed") else "null"
        status = {"participant_cancel": "FAILED_RECOVERABLE", "committed": "APPLIED_VERIFIED"}.get(state, "PREPARED")
        self.pg.sql(f"""
        insert into trainers(id,display_name,slug,auth_user_id) values
          ('{robber}','Robber {n}','robber-29-{n}',gen_random_uuid()),
          ('{victim}','Victim {n}','victim-29-{n}',gen_random_uuid());
        insert into season_players(season_id,trainer_id) values
          ('{self.season}','{robber}'),('{self.season}','{victim}');
        insert into coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type,reference_type)
          select season_id,trainer_id,id,100,'admin_adjustment','fixture' from season_players
          where season_id='{self.season}' and trainer_id in ('{robber}','{victim}');
        insert into purchases(id,season_id,trainer_id,season_player_id,shop_item_id,unit_price,status,idempotency_key)
          select '{purchase}',sp.season_id,sp.trainer_id,sp.id,i.id,i.base_price,
            '{"used" if state == "committed" else "pending"}','{purchase}'
          from season_players sp, shop_items i
          where sp.season_id='{self.season}' and sp.trainer_id='{robber}' and i.code='robar_pokemon';
        insert into coin_transactions(season_id,trainer_id,season_player_id,amount,transaction_type,reference_type,reference_id)
          select season_id,trainer_id,season_player_id,-total_price,'purchase','purchase',id
          from purchases where id='{purchase}';
        -- Fixture only: the robbery engine's own triggers are not under test here.
        set session_replication_role = replica;
        {''.join(rows)}
        insert into pokemon_entities(id,season_id,owner_trainer_id,identity_status,identity_schema_version,
          candidate_key,initial_evidence)
          values('{entity}','{self.season}','{victim}','unambiguous',1,'{SHA.format(5000 + n)}','{{}}'::jsonb);
        insert into item_use_authorizations(id,operation_id,idempotency_key,purchase_id,season_id,trainer_id,
          target_pokemon_entity_id,save_file_id,save_sha256,identity_revision_id,effect_code,status)
          values('{auth}','{auth}','{auth}','{purchase}','{self.season}','{robber}','{entity}',
            '{saves["destination"]}','{SHA.format(n * 10 + 2)}','{revisions["source"]}','steal','{status}');
        insert into item_use_transfers(authorization_id,donor_id,plans,adjudicated_at,terminal)
          values('{auth}','{victim}',{plans},{adjudicated},{terminal});
        insert into item_use_transfer_legs(authorization_id,side,season_id,trainer_id,save_file_id,
          identity_revision_id,source_sha256,apply_started,obligation,released)
        select '{auth}',side,'{self.season}',trainer::uuid,save::uuid,revision::uuid,sha,
          {"side='destination'" if state == "applying" else "false"},{obligation},
          {"true" if state in ("participant_cancel", "committed") else "false"}
        from (values ('source','{victim}','{saves["source"]}','{revisions["source"]}','{SHA.format(n * 10 + 1)}'),
                     ('destination','{robber}','{saves["destination"]}','{revisions["destination"]}','{SHA.format(n * 10 + 2)}'))
          v(side,trainer,save,revision,sha);
        set session_replication_role = origin;
        """)
        return dict(id=auth, purchase=purchase, robber=robber, victim=victim)

    def cancel(self, state, op=None, digest=HASH, actor=None, reason="Robo atascado sin decisión", ok=True):
        op = op or str(uuid4())
        result = self.pg.sql(
            f"select admin_robbery_cancel('{actor or self.admin}','{self.season}',"
            f"'{self.robberies[state]['id']}','{op}','{digest}',$r${reason}$r$);",
            ok=ok,
        )
        return (json.loads(result.stdout) if ok else result), op

    def balance(self, trainer):
        return int(self.scalar(
            f"select coalesce(sum(amount),0) from coin_transactions where "
            f"season_id='{self.season}' and trainer_id='{trainer}';"))

    def facts(self, state):
        r = self.robberies[state]
        return self.scalar(f"""
        select jsonb_build_object(
          'state',transfer_state('{r["id"]}'),
          'terminal',(select terminal from item_use_transfers where authorization_id='{r["id"]}'),
          'released',(select jsonb_agg(released order by side) from item_use_transfer_legs where authorization_id='{r["id"]}'),
          'auth',(select status||':'||coalesce(error_code,'') from item_use_authorizations where id='{r["id"]}'),
          'purchase',(select status from purchases where id='{r["purchase"]}'),
          'credits',(select count(*) from coin_transactions where reference_id='{r["purchase"]}' and amount>0),
          'audit',(select count(*) from admin_incident_commands where authorization_id='{r["id"]}'));""")

    def overview(self):
        data = json.loads(self.scalar(f"select admin_incident_read('{self.admin}','{self.season}');"))
        return {r["authorization_id"]: r for r in data["robberies"]}


def refused(result, code):
    assert result.returncode and code in result.stderr, result.stderr[-600:]


def gates(pg):
    f = Fixture(pg)
    checks = []
    view = f.overview()
    flags = {s: (view[r["id"]]["cancellable"], view[r["id"]]["reconciliation_required"])
             for s, r in f.robberies.items()}
    assert flags == {
        "requested": (True, False), "verified": (True, False),
        "adjudicated": (False, True), "applying": (False, True),
        "participant_cancel": (False, False), "committed": (False, False),
    }, flags
    assert all(view[r["id"]]["price"] > 0 for r in f.robberies.values())
    checks.append("overview tells reversible robberies from those needing reconciliation")

    # Authority and reason come first; refusals change nothing.
    before = {s: f.facts(s) for s in STATES}
    refused(f.cancel("requested", actor=f.player, ok=False)[0], "admin_required")
    refused(f.cancel("requested", reason="  no  ", ok=False)[0], "incident_reason_required")
    refused(f.cancel("adjudicated", ok=False)[0], "robbery_reconciliation_required")
    refused(f.cancel("applying", ok=False)[0], "robbery_reconciliation_required")
    refused(f.cancel("committed", ok=False)[0], "robbery_reconciliation_required")
    refused(f.cancel("participant_cancel", ok=False)[0], "robbery_already_cancelled")
    assert {s: f.facts(s) for s in STATES} == before
    checks.append("non-admin, missing reason, decided/physical/terminal robberies refused with no change")

    # A requested robbery: released, item cancelled, coins back once, audited.
    r = f.robberies["requested"]
    start = f.balance(r["robber"])
    price = view[r["id"]]["price"]
    receipt, op = f.cancel("requested")
    assert receipt["status"] == "cancelled" and receipt["amount"] == price, receipt
    assert receipt["authorization_id"] == r["id"] and receipt["purchase_id"] == r["purchase"]
    assert f.balance(r["robber"]) == start + price == receipt["balance_after"]
    facts = json.loads(f.facts("requested"))
    assert facts == {"state": "CANCELLED", "terminal": "CANCELLED", "released": [True, True],
                     "auth": "FAILED_RECOVERABLE:TRANSFER_CANCELLED", "purchase": "cancelled",
                     "credits": 1, "audit": 1}, facts
    assert f.balance(r["victim"]) == 100
    checks.append("requested robbery cancelled: both trainers released, item cancelled, price returned once, audited")

    # Retries replay; other data conflicts; no second credit by any path.
    again, _ = f.cancel("requested", op=op)
    assert again["replayed"] is True and again["ledger_id"] == receipt["ledger_id"]
    refused(f.cancel("requested", op=op, digest="d" * 64, ok=False)[0], "idempotency_conflict")
    refused(f.cancel("requested", ok=False)[0], "robbery_already_cancelled")
    refused(pg.sql(
        f"select admin_purchase_resolve('{f.admin}','{f.season}','{r['purchase']}',"
        f"'purchase_cancel','{uuid4()}','{HASH}','Doble devolución');", ok=False),
        "purchase_linked_to_save_operation")
    assert json.loads(f.facts("requested"))["credits"] == 1 and f.balance(r["robber"]) == start + price
    checks.append("same operation replays; other data conflicts; no second return by either incident path")

    # Two administrators at once on the same verified robbery: one effect.
    r = f.robberies["verified"]
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: f.cancel("verified", ok=False)[0], range(4)))
    wins = [x for x in results if x.returncode == 0]
    assert len(wins) == 1, [x.stderr[-200:] for x in results]
    assert all("robbery_already_cancelled" in x.stderr or "admin_incident_robbery_once" in x.stderr
               or "could not serialize" in x.stderr for x in results if x.returncode), \
        [x.stderr[-200:] for x in results if x.returncode]
    facts = json.loads(f.facts("verified"))
    assert facts["credits"] == 1 and facts["audit"] == 1 and facts["state"] == "CANCELLED", facts
    checks.append("four concurrent cancellations of one robbery: exactly one effect")

    view = f.overview()
    assert view[f.robberies["requested"]["id"]]["cancelled_by_admin"] is True
    assert view[f.robberies["requested"]["id"]]["cancellable"] is False
    history = json.loads(f.scalar(f"select admin_incident_read('{f.admin}','{f.season}');"))["history"]
    assert sum(h["kind"] == "robbery_cancel" for h in history) == 2
    checks.append("overview refreshes: cancelled by admin, history keeps both commands")

    # Archived seasons are immutable; the audit is append-only.
    pg.sql(f"update seasons set status='archived',archived_at=now() where id='{f.season}';")
    refused(f.cancel("adjudicated", ok=False)[0], "historical_artifact_immutable")
    pg.sql(f"update seasons set status='active',archived_at=null where id='{f.season}';")
    refused(pg.sql("update admin_incident_commands set reason='x';", ok=False), "admin_incident_immutable")
    checks.append("archived season refused; intervention history append-only")

    # Grants: only the service role reaches the command; nobody calls the helper.
    grants = f.scalar("""
    select jsonb_build_object(
      'anon',has_function_privilege('anon','public.admin_robbery_cancel(uuid,uuid,uuid,uuid,text,text)','execute'),
      'authenticated',has_function_privilege('authenticated','public.admin_robbery_cancel(uuid,uuid,uuid,uuid,text,text)','execute'),
      'service',has_function_privilege('service_role','public.admin_robbery_cancel(uuid,uuid,uuid,uuid,text,text)','execute'),
      'helper',has_function_privilege('service_role','public.admin_robbery_blocker(uuid)','execute'));""")
    assert json.loads(grants) == {"anon": False, "authenticated": False, "service": True, "helper": False}, grants
    checks.append("grants: service role only; helper closed")
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bin", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55530)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    pg = LocalPG(args.bin, args.port)
    try:
        pg.start()
        checks = gates(pg)
        version = pg.sql("show server_version;", "postgres").stdout.strip()
    finally:
        with contextlib.suppress(Exception):
            pg.stop()
    for check in checks:
        print("PASS", check)
    if args.evidence:
        args.evidence.write_text(json.dumps(
            {"postgres": version, "migrations": f"001-{MIGRATIONS:03d} bootstrap", "checks": checks},
            indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
