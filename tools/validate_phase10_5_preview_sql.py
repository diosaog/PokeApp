"""Loopback-only H projection/role proof using frozen Team Lock fixtures."""

import argparse
import json
import os
from pathlib import Path
import subprocess

from app.api.team_preview_models import TeamPreviewQuery
from app.application.team_preview import team_preview
from app.repositories.supabase.frontend_reads import SupabaseFrontendReadRepository
from tools.validate_supabase_v2_identity_sql import (
    LocalClient,
    Query,
    SqlError,
    identifier,
    literal,
)

ROOT = Path(__file__).resolve().parents[1]
SID = "00000000-0000-4000-8000-000000008c10"
DAY = "00000000-0000-4000-8000-000000008c12"
OWNER = "00000000-0000-4000-8000-000000008c01"
RIVAL = "00000000-0000-4000-8000-000000008c04"


class ReadQuery(Query):
    """Honor the actual repository column list, unlike the legacy fixture shim."""

    def select(self, columns):
        self.columns = ",".join(identifier(c) for c in columns.split(","))
        return self

    def execute(self):
        assert self.operation == "select"
        where = " where " + " and ".join(self.filters) if self.filters else ""
        query = (
            "select "
            + self.columns
            + " from public."
            + self.table_name
            + where
            + self.sort
            + self.lim
            + self.offset
        )
        return self.client.execute(
            "select coalesce(jsonb_agg(to_jsonb(r)),'[]') from (" + query + ") r"
        )


class ReadClient(LocalClient):
    def table(self, table):
        return ReadQuery(self, table)


def validate(args):
    client = ReadClient(args)  # Enforces loopback and disposable database name.
    tables = client.execute(
        "select jsonb_agg(tablename order by tablename) from pg_tables where schemaname='public'"
    ).data

    def snapshot():
        return client.execute(
            "select jsonb_object_agg(name,rows) from ("
            + " union all ".join(
                "select " + literal(t) + " name,coalesce(jsonb_agg(to_jsonb(r) "
                "order by to_jsonb(r)::text),'[]') rows from public."
                + identifier(t)
                + " r"
                for t in tables
            )
            + ") x"
        ).data

    def sql(statement):
        result = subprocess.run(
            [
                args.psql,
                "-h",
                args.host,
                "-p",
                str(args.port),
                "-U",
                args.user,
                "-d",
                args.database,
                "-X",
                "-qAt",
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                "-",
            ],
            input="begin;\n" + statement + "\ncommit;",
            text=True,
            encoding="utf-8",
            capture_output=True,
            env=dict(os.environ, PGPASSWORD=args.password),
        )
        if result.returncode:
            raise RuntimeError(result.stderr)

    baseline = snapshot()
    assert all(
        s["id"] != SID and s["status"] != "active" for s in baseline["seasons"]
    ), "Fixture season collision or an active season exists"
    setup = (ROOT / "tests/sql/team_lock_setup.sql").read_text(encoding="utf-8")
    cleanup = (ROOT / "tests/sql/team_lock_cleanup.sql").read_text(encoding="utf-8")
    cleanup = (
        f"update public.seasons set current_matchday_id=null where id='{SID}';\n"
        + cleanup
    )
    groups = []
    created = False
    try:
        sql(
            setup
            + f"\nupdate public.seasons set current_matchday_id='{DAY}' where id='{SID}';"
            + """
update public.parsed_saves set payload=jsonb_build_object('party',
 (select jsonb_agg(mon || jsonb_build_object('ivs',jsonb_build_object(
  'hp',31,'atk',31,'defense',31,'spa',31,'spd',31,'spe',31),
  'nature','Bold','identity_metadata','never expose'))
 from jsonb_array_elements(payload->'party') mon))
 where save_file_id in ('00000000-0000-4000-8000-000000008c20','00000000-0000-4000-8000-000000008c21');
update pokeapp_team_lock_test.request r set parsed_payload=ps.payload,
 private_team_snapshot=ps.payload->'party' from public.parsed_saves ps where ps.id=r.parsed_save_id;
select id from pokeapp_team_lock_test.run();
"""
        )
        created = True
        repo = SupabaseFrontendReadRepository(client)

        def preview(viewer=OWNER, **params):
            return team_preview(
                repo, SID, viewer, TeamPreviewQuery(**params)
            ).model_dump(mode="json")

        frozen = snapshot()
        public = preview(trainer_id=OWNER, second_trainer_id=RIVAL)
        assert all(e["visibility"] == "public" for e in public["teams"])
        assert len(public["teams"][0]["lock"]["team"]) == 6
        assert public["teams"][1]["lock"] is None
        for secret in ("ability", "nature", "ivs", "identity_metadata"):
            assert secret not in json.dumps(public)
        groups.append("unscheduled spectator, self public, missing rival null")
        own = preview(mode="battle", trainer_id=OWNER)
        assert own["teams"][0]["lock"]["team"][0]["ivs"]["hp"] == 31
        assert own["teams"][0]["lock"]["team"][0]["ability"] == "Competitive"
        assert "identity_metadata" not in json.dumps(own)
        rival = preview(viewer=RIVAL, mode="battle", trainer_id=OWNER)
        assert rival["teams"][0]["visibility"] == "public"
        assert "ability" not in json.dumps(rival)
        assert snapshot() == frozen, "Reads changed database rows"
        groups.append("JWT-selected self whitelist, rival public, zero read writes")

        for role, uid, private_count in (
            ("authenticated", "00000000-0000-4000-8000-000000008ca1", 1),
            ("authenticated", "00000000-0000-4000-8000-000000008ca2", 0),
        ):
            reader = LocalClient(args, role, uid)
            assert (
                reader.execute(
                    f"select count(*) from public.team_locks where season_id='{SID}'"
                ).data
                == private_count
            )
            assert (
                reader.execute(
                    f"select count(*) from public.public_team_locks where season_id='{SID}'"
                ).data
                == 1
            )
            try:
                reader.execute(
                    "select private_team_snapshot from public.public_team_locks"
                )
                raise AssertionError("Private public-view column exposed")
            except SqlError as exc:
                assert exc.code == "42703"
        anon = LocalClient(args, "anon")
        try:
            anon.execute("select count(*) from public.public_team_locks")
            raise AssertionError("Anonymous preview allowed")
        except SqlError as exc:
            assert exc.code == "42501"
        assert client.execute("""select to_jsonb(bool_and(not has_function_privilege(r,
 'public.api_upsert_team_lock(uuid,uuid,uuid,uuid,uuid,text,uuid,jsonb,jsonb,jsonb)','EXECUTE')))
 from unnest(array['anon','authenticated']) r""").data
        groups.append(
            "existing RLS, public view columns and service-only mutation privileges"
        )

        sql(
            "update public.parsed_saves set payload='{}' where save_file_id in "
            "('00000000-0000-4000-8000-000000008c20','00000000-0000-4000-8000-000000008c21'); "
            f"update public.matchdays set status='closed',closed_at=now() where id='{DAY}';"
        )
        assert preview(mode="battle", trainer_id=OWNER)["teams"] == own["teams"]
        assert (
            preview(trainer_id=OWNER, second_trainer_id=RIVAL)["teams"]
            == public["teams"]
        )
        groups.append("closed frozen lock independent of later save state")
    finally:
        if created:
            sql(cleanup)
        assert snapshot() == baseline, "H fixture residue or unrelated table drift"
    return dict(
        status="PASS",
        groups=groups,
        public_tables_restored=len(tables),
        remote_writes=0,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--psql", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=55439)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="")
    parser.add_argument("--database", required=True)
    print(json.dumps(validate(parser.parse_args()), indent=2))
