"""Phase 30 hosted acceptance, public part: GET/HEAD/OPTIONS only, no session.

``--stage before`` describes production as it is now (web a7e33476, API
501a399); ``--stage after`` what the coordinated release must show. The
signed-in checks (league, admin, economy, Cup, history...) are the owner's
read-only walk-through in the Phase 30 report: this script never signs in,
buys, robs or changes a season.

Run: python -m tools.phase30_hosted_acceptance --stage before|after [--full-download] --output <json>
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from tools.production_readonly import WEB, http

API = "https://pokeapp-api-production.up.railway.app"
INSTALLERS = {
    "0.25.0": {
        "bytes": 159293410,
        "sha256_prefix": "f02eccd0",
        "sha256_suffix": "83d3fa",
    },
    "0.26.1": {
        "bytes": 159312173,
        "sha256_prefix": "edf8d647",
        "sha256_suffix": "18d320",
    },
    "0.26.3": {
        "bytes": 159311823,
        "sha256_prefix": "7b31ad92",
        "sha256_suffix": "507bef",
    },
}
EXPECTED = {
    "before": {
        "routes": 88,
        "division_required": ["A", "B"],
        "incidents": False,
        "feed": "spa",
    },
    "after": {
        "routes": 104,
        "division_required": ["A"],
        "incidents": True,
        "feed": "absent",
    },
    # After 065/066: personal saves (108 routes); 0.26.3 is the download and
    # the stable feed's offer.
    "final": {
        "routes": 108,
        "division_required": ["A"],
        "incidents": True,
        "feed": "feed",
        "launcher": "0.26.3",
    },
}
ZERO = "00000000-0000-4000-8000-000000000000"
STABLE_KEY = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "PokeApp-release-keys/stable/pokeapp-update-public.pem"
)


def signed_by_stable_key(signature: bytes, body: bytes) -> bool:
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    try:
        load_pem_public_key(STABLE_KEY.read_bytes()).verify(signature, body)
        return True
    except Exception:  # noqa: BLE001 - any failure is "not signed by it"
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=sorted(EXPECTED), required=True)
    parser.add_argument("--full-download", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    want = EXPECTED[args.stage]
    launcher = want.get("launcher", "0.25.0")
    installer = INSTALLERS[launcher]
    checks = []

    def check(label, condition, observed=None):
        checks.append({"check": label, "pass": bool(condition), "observed": observed})
        print(
            "PASS" if condition else "FAIL",
            label,
            "" if observed is None else observed,
            flush=True,
        )

    index = http("GET", WEB + "/")
    check(
        "web answers",
        index.status_code == 200
        and "text/html" in index.headers.get("content-type", ""),
        index.status_code,
    )
    config = http("GET", WEB + "/build-config.json").json()
    check(
        "web targets the production API",
        config.get("api_base_url") == API,
        config.get("api_base_url"),
    )
    bundle_path = re.search(r'src="(/assets/index-[^"]+\.js)"', index.text)
    bundle = http("GET", WEB + bundle_path.group(1)).text if bundle_path else ""
    # Screens are lazy chunks: the download card lives in one of them.
    for chunk in sorted(set(re.findall(r"assets/[\w.-]+\.js", bundle))):
        bundle += http("GET", f"{WEB}/{chunk}").text
    versions = sorted(set(re.findall(r'version:["`](\d+\.\d+\.\d+)["`]', bundle)))
    launchers = [v for v in versions if v.startswith("0.2")]
    check(
        f"download card announces {launcher}, the installer R2 serves",
        launchers == [launcher],
        versions,
    )

    head = http("HEAD", WEB + "/launcher/download")
    size = int(head.headers.get("content-length", "0"))
    check(
        f"public installer is the {launcher} object",
        head.status_code == 200 and size == installer["bytes"],
        size,
    )
    digest = None
    if args.full_download:
        sha = hashlib.sha256()
        with __import__("httpx").stream("GET", WEB + "/launcher/download", timeout=600,
                                         headers={"User-Agent": "PokeApp-release-audit/1.0"}) as response:  # fmt: skip
            for chunk in response.iter_bytes(1 << 20):
                sha.update(chunk)
        digest = sha.hexdigest()
        check(
            f"downloaded installer hash matches the recorded {launcher} hash",
            digest.startswith(installer["sha256_prefix"])
            and digest.endswith(installer["sha256_suffix"]),
            digest,
        )
    feed = http("GET", WEB + "/launcher/updates/stable.json")
    shape = (
        "spa"
        if "text/html" in feed.headers.get("content-type", "")
        else ("absent" if feed.status_code == 404 else "feed")
    )
    check(
        f"update channel state: {want['feed']}",
        shape == want["feed"],
        [feed.status_code, shape],
    )
    if shape == "feed":
        envelope = feed.json()
        body = base64.b64decode(envelope["manifest"])
        signature = base64.b64decode(envelope["signature"])
        manifest = json.loads(body)
        check(
            "stable feed is signed by the stable key (Ed25519)",
            signed_by_stable_key(signature, body),
        )
        tampered = bytearray(body)
        tampered[-2] ^= 1
        check(
            "a tampered manifest fails the signature",
            not signed_by_stable_key(signature, bytes(tampered)),
        )
        check(
            f"stable feed offers {launcher} at its stable route, size bound",
            manifest["channel"] == "stable"
            and manifest["version"] == launcher
            and manifest["installer"]["size"] == installer["bytes"]
            and manifest["installer"]["url"]
            == f"{WEB}/launcher/updates/stable/{launcher}.exe",
            manifest["version"],
        )
        route = http("HEAD", f"{WEB}/launcher/updates/stable/{launcher}.exe")
        check(
            "stable installer route: immutable cache, exact size",
            route.status_code == 200
            and "immutable" in route.headers.get("cache-control", "")
            and int(route.headers.get("content-length", "0")) == installer["bytes"],
        )
    upload = http("GET", WEB + "/launcher/updates/stable/..%2f..%2fwindows.exe")
    check(
        "no traversal or listing through the update routes",
        "octet-stream" not in upload.headers.get("content-type", ""),
        upload.status_code,
    )

    health = http("GET", API + "/health")
    check("API health", health.status_code == 200, health.status_code)
    spec = http("GET", API + "/openapi.json").json()
    routes = len(spec.get("paths", {}))
    check(f"API exposes {want['routes']} routes", routes == want["routes"], routes)
    required = (
        spec.get("components", {})
        .get("schemas", {})
        .get("DivisionSizes", {})
        .get("required")
    )
    check("DivisionSizes structure", required == want["division_required"], required)
    incident = (
        "/v1/admin/seasons/{season_id}/incidents/robberies/{authorization_id}/cancel"
        in spec.get("paths", {})
    )
    check("robbery cancellation route", incident == want["incidents"], incident)
    for path in (
        "/v1/me",
        f"/v1/admin/seasons/{ZERO}/incidents",
        f"/v1/launcher/seasons/{ZERO}/item-uses",
    ):
        if (
            not want["incidents"]
            and "incidents" in path
            or not want["incidents"]
            and "item-uses" in path
        ):
            continue
        status = http("GET", API + path).status_code
        check(
            f"{path.split(ZERO)[0]}... refuses without a session", status == 401, status
        )
    preflight = http(
        "OPTIONS",
        API + "/v1/me",
        headers={"Origin": WEB, "Access-Control-Request-Method": "GET"},
    )
    allowed = preflight.headers.get("access-control-allow-origin")
    check("CORS admits the public web", allowed == WEB, allowed)
    foreign = http(
        "OPTIONS",
        API + "/v1/me",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    check(
        "CORS refuses another origin",
        foreign.headers.get("access-control-allow-origin") is None,
        foreign.status_code,
    )

    report = {
        "stage": args.stage,
        "captured_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "installer_sha256": digest,
        "passed": sum(c["pass"] for c in checks),
        "total": len(checks),
        "checks": checks,
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if report["passed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
