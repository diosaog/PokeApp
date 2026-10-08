"""K uses H's disposable local PG fixtures and exact preservation/security checks."""

import argparse
import json

from tools.validate_phase10_5_preview_sql import validate


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--psql", required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=55439)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="")
    parser.add_argument("--database", required=True)
    print(json.dumps(validate(parser.parse_args(), check_scouting=True), indent=2))
