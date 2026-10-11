"""Read-only HTTP measurement. Private credentials arrive on stdin, never logs."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from statistics import median
import sys
from time import perf_counter

import httpx


def main():
    config = json.load(sys.stdin)
    base = config["api"]
    assert base in (
        "http://127.0.0.1:8130",
        "https://pokeapp-api-production.up.railway.app",
    )
    output = Path(config["output"])
    assert not output.exists(), "Never overwrite measurement evidence"
    sid, tid = config["season"], config["trainer"]
    paths = {name: f"/v1/read/seasons/{sid}/{name}" for name in (
        "league", "overview", "pc", "shop", "inventory", "progress", "scouting"
    )}
    paths["preview"] = f"/v1/read/seasons/{sid}/team-preview?mode=battle&trainer_id={tid}"
    paths["admin"] = f"/v1/admin/seasons/{sid}/setup"
    paths["rules"] = f"/v1/admin/seasons/{sid}/rules"
    records = []
    result = {"started_at": datetime.now(timezone.utc).isoformat(),
              "method": "five sequential GET rounds, same order, one reused HTTP client, no retries",
              "records": records, "business_writes": 0}
    with httpx.Client(timeout=60, headers={"Origin": config["web"]}) as client:
        login = client.post(base + "/v1/auth/pin-login", json={
            "trainer_identifier": config["identifier"], "pin": config["pin"]})
        assert login.status_code == 200, "Login failed; credentials suppressed"
        session = login.json()
        assert session["trainer_id"] == tid
        client.headers["Authorization"] = "Bearer " + session["session"]["access_token"]
        for run in range(5):
            for name, path in paths.items():
                start = perf_counter()
                response = client.get(base + path)
                records.append({"run": run + 1, "flow": name,
                    "seconds": round(perf_counter() - start, 4),
                    "status": response.status_code, "decoded_bytes": len(response.content),
                    "sha256": hashlib.sha256(response.content).hexdigest(),
                    "server_timing": response.headers.get("server-timing"),
                    "request_id": response.headers.get("x-request-id")})
                output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    result["summary"] = {name: {
        "n": len(samples := [r for r in records if r["flow"] == name]),
        "median_s": round(median(r["seconds"] for r in samples), 4),
        "range_s": [min(r["seconds"] for r in samples), max(r["seconds"] for r in samples)],
        "statuses": [r["status"] for r in samples],
        "bytes": [r["decoded_bytes"] for r in samples],
    } for name in paths}
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"]), flush=True)


if __name__ == "__main__":
    main()
