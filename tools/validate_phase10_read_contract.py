"""Pinned V2 read-only schema compatibility gate. No fixtures or remote writes."""

import argparse
import ast
import json
from pathlib import Path

from app.api.config import APIConfig
from app.application.frontend_reads import FrontendReads
from app.repositories.supabase.frontend_reads import SupabaseFrontendReadRepository
from tools.validate_supabase_v2_rls import _load_env_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    args = parser.parse_args()
    _load_env_file(args.env_file)
    config = APIConfig.from_env()
    if (
        config.supabase_url != "https://uwleqeuzsveqlugugzba.supabase.co"
        or not config.supabase_service_role_key
    ):
        raise SystemExit("Pinned V2 configuration required")
    repo = SupabaseFrontendReadRepository.from_url_key(
        config.supabase_url, config.supabase_service_role_key
    )
    tree = ast.parse(
        (
            Path(__file__).resolve().parents[1] / "app/application/frontend_reads.py"
        ).read_text(encoding="utf-8")
    )
    selections = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "rows"
            and len(node.args) > 1
            and all(isinstance(a, ast.Constant) for a in node.args[:2])
        ):
            selections.add(tuple(a.value for a in node.args[:2]))
    # Hall uses a named column string and is checked by the typed real read below.
    for table, columns in sorted(selections):
        repo._client.table(table).select(columns).limit(0).execute()
    reads = FrontendReads(repo)
    result = dict(
        project_ref="uwleqeuzsveqlugugzba",
        read_only=True,
        static_selections=len(selections),
        tables=sorted({s[0] for s in selections}),
        seasons=len(reads.seasons().items),
        hall=len(reads.hall().items),
        trainers=len(reads.trainers()),
        mutations=0,
        fixtures=0,
        storage_operations=0,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
