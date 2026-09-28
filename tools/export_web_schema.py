"""Rebuild frontend types from this checkout's FastAPI contract; no database access."""

import json
from pathlib import Path
import subprocess
import tempfile

from app.api.config import APIConfig
from app.api.dependencies import ApiContainer
from app.api.main import create_app


def main():
    root = Path(__file__).resolve().parents[1]
    schema = create_app(container=ApiContainer(), config=APIConfig()).openapi()
    with tempfile.TemporaryDirectory(prefix="pokeapp-openapi-") as temp:
        source = Path(temp) / "openapi.json"
        source.write_text(json.dumps(schema), encoding="utf-8")
        subprocess.run(
            [
                "node",
                str(root / "web/node_modules/openapi-typescript/bin/cli.js"),
                str(source),
                "-o",
                str(root / "web/src/api/schema.d.ts"),
            ],
            check=True,
        )
        subprocess.run(
            [
                "node",
                str(root / "web/node_modules/prettier/bin/prettier.cjs"),
                "--write",
                str(root / "web/src/api/schema.d.ts"),
            ],
            check=True,
        )


if __name__ == "__main__":
    main()
