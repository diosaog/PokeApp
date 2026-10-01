"""Real B/C/D/E public reads and guaranteed denials, preserving manual staging data.

Run as a module with --output <fresh directory outside the repository>. Supply
{"pin": "..."} through private stdin, never a command argument. No fixture, valid
business mutation, migration, deployment, role change or cleanup is performed.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
import re
import subprocess
import sys
from time import monotonic
from uuid import uuid4

import httpx

from app.api.matchday_models import DayState
from app.api.initial_assignment_models import InitialAssignmentRead
from app.api.read_models import LeagueGeneralRead, LeagueStandingRead, OverviewRead
from tools.validate_phase10_hosted import (
    API,
    HISTORY,
    REF,
    ROOT,
    WEB,
    advisors,
    cli,
    query,
    require,
    significant,
    snapshot,
    write,
)

OWNER = "507d9c56-04d8-4801-a9da-f1e53674efb5"
OWNER_AUTH = "ac98932c-f713-43d1-8b20-600f0be3dadc"
OWNER_SEASON = "c6bcac5b-0b89-403f-8242-41ac58286ade"
MIGRATIONS = (
    "033_league_general_read",
    "034_participant_matchday_results",
    "035_daily_sporting_ranking",
    "036_observed_initial_divisions",
)


def now():
    return datetime.now(timezone.utc).isoformat()


def check_general(raw):
    """Validate wire types and exact public allowlists without retaining rows."""
    data = LeagueGeneralRead.model_validate(raw)
    require(set(raw) == {"season", "days", "rows"}, "Unexpected GENERAL fields")
    require(
        set(raw["season"])
        == {"id", "name", "status", "current_matchday_id", "initial_assignment_rule"},
        "Unexpected season fields",
    )
    fields = set(LeagueStandingRead.model_fields)
    for row in raw["rows"]:
        require(set(row) == fields, "Unexpected standing fields")
        require(isinstance(row["total_points"], str), "Points must remain strings")
        require(isinstance(row["coin_balance"], str), "Coins must remain strings")
        require(Decimal(row["total_points"]).is_finite(), "Nonfinite points")
        require(
            re.fullmatch(r"-?(0|[1-9][0-9]*)", row["coin_balance"]), "Invalid coins"
        )
        if row["dead_count_source"] == "unknown":
            require(
                row["dead_count"] is None and row["dead_count_observed_at"] is None,
                "Unknown observation represented as a count",
            )
        else:
            require(
                type(row["dead_count"]) is int
                and row["dead_count_observed_at"] is not None,
                "Incomplete known observation",
            )
    for day in raw["days"]:
        require(set(day) == {"id", "number", "status"}, "Unexpected day fields")
        require(
            day["status"] == "closed"
            or day["id"] == raw["season"]["current_matchday_id"],
            "Future day exposed as reached",
        )
    points = [row.total_points for row in data.rows]
    require(
        points == sorted(points, reverse=True), "GENERAL is not ordered by exact points"
    )
    require(
        len({row.season_player_id for row in data.rows}) == len(data.rows),
        "Duplicate roster",
    )
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    require(not out.exists(), "Use a fresh evidence directory")
    require(
        ROOT != out and ROOT not in out.parents,
        "Evidence must remain outside repository",
    )
    try:
        supplied = json.load(sys.stdin)
        pin = supplied["pin"]
        require(isinstance(pin, str) and bool(pin), "Invalid private input")
    except Exception:
        raise SystemExit(
            "Supply private stdin JSON containing pin; details suppressed"
        ) from None
    out.mkdir(parents=True)
    report = {
        "run_id": "phase10_5_public_reads_" + uuid4().hex,
        "started_at": now(),
        "status": "RUNNING",
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "project_ref": REF,
        "api": API,
        "web": WEB,
        "owner_trainer": OWNER,
        "owner_auth_user": OWNER_AUTH,
        "owner_season": OWNER_SEASON,
        "owner_auth_exception": "Only this owner's Auth activity; every public row compared",
        "business_writes": 0,
        "fixtures_created": 0,
        "checks": [],
        "requests": [],
        "failures": [],
        "limitations": [
            "Owner is admin: no public positive non-admin result mutation is claimed.",
            "No manual result changed; successful result/tie/initial assignment mutations, CAS and races use local C/D/E gates.",
            "No observed save is uploaded or invented; existing owner season remains legacy initialization.",
        ],
    }
    before = history = advisor_before = None
    stage = "preflight"

    def save():
        write(out / "result.json", report)

    def passed(name):
        report["checks"].append(name)
        save()

    save()
    try:
        require(
            (ROOT / "supabase/.temp/project-ref").read_text().strip() == REF,
            "Wrong linked project",
        )
        projects = cli(["projects", "list", "-o", "json"])
        require(
            any(p["id"] == REF and p.get("linked") for p in projects),
            "Pinned project not linked",
        )
        history = query(out, "history-before", HISTORY)
        for name in MIGRATIONS:
            rows = [row for row in history if row["name"] == name]
            require(len(rows) == 1, "Required migration absent or duplicated")
        require(
            [row["name"] for row in history[-len(MIGRATIONS) :]] == list(MIGRATIONS),
            "Unexpected latest migrations",
        )
        report["migrations"] = [row for row in history if row["name"] in MIGRATIONS]
        before = snapshot(out, "baseline-before", OWNER_AUTH)
        require(len(before) == 53, "Unexpected baseline table set")
        advisor_before = advisors(out, "advisors-before")
        owner = query(
            out,
            "owner-mapping",
            "select id,auth_user_id,slug,globally_enabled,is_admin from public.trainers "
            f"where id='{OWNER}'::uuid or auth_user_id='{OWNER_AUTH}'::uuid",
        )
        require(
            len(owner) == 1
            and owner[0]
            == dict(
                id=OWNER,
                auth_user_id=OWNER_AUTH,
                slug="anto",
                globally_enabled=True,
                is_admin=True,
            ),
            "Owner mapping changed",
        )
        seasons = query(
            out,
            "owner-season-state",
            "select id,status,current_matchday_id from public.seasons "
            f"where id='{OWNER_SEASON}'::uuid",
        )
        require(
            len(seasons) == 1 and seasons[0]["status"] == "active",
            "Expected manual active season unavailable",
        )
        passed(
            "Pinned project, applied 033-036, fresh 53-table baseline and owner identity"
        )
        stage = "public API"
        with httpx.Client(
            base_url=API, timeout=60, headers={"Origin": WEB}, follow_redirects=False
        ) as api:
            require(api.get("/health").status_code == 200, "Public health unavailable")
            for origin, expected in ((WEB, 200), ("https://untrusted.invalid", 400)):
                cors = api.options(
                    "/v1/me",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "GET",
                        "Access-Control-Request-Headers": "Authorization",
                    },
                )
                require(cors.status_code == expected, "CORS preflight mismatch")
                require(
                    cors.headers.get("access-control-allow-origin")
                    == (WEB if expected == 200 else None),
                    "CORS origin mismatch",
                )
            token = None

            def request(
                method,
                path,
                *,
                body=None,
                status=200,
                auth=True,
                invalid=False,
                key=None,
            ):
                headers = {}
                if invalid:
                    headers["Authorization"] = "Bearer invalid.phase10_5.token"
                elif auth and token:
                    headers["Authorization"] = "Bearer " + token
                if key:
                    headers["Idempotency-Key"] = key
                started = monotonic()
                response = api.request(method, path, json=body, headers=headers)
                report["requests"].append(
                    {
                        "method": method,
                        "path": path,
                        "status": response.status_code,
                        "elapsed_ms": round((monotonic() - started) * 1000, 2),
                    }
                )
                save()
                require(response.status_code == status, "Unexpected HTTP status")
                require(
                    response.headers.get("cache-control") == "no-store",
                    "Private response cache policy",
                )
                require(
                    response.headers.get("access-control-allow-origin") == WEB,
                    "Actual response CORS",
                )
                return response.json()

            login = request(
                "POST",
                "/v1/auth/pin-login",
                auth=False,
                body={"trainer_identifier": "anto", "pin": pin},
            )
            require(
                login["trainer_id"] == OWNER and login["auth_user_id"] == OWNER_AUTH,
                "Login identity mismatch",
            )
            refresh = request(
                "POST",
                "/v1/auth/refresh",
                auth=False,
                body={"refresh_token": login["session"]["refresh_token"]},
            )
            token = refresh["session"]["access_token"]
            me = request("GET", "/v1/me")
            require(
                me["trainer_id"] == OWNER and me["is_admin"] and me["globally_enabled"],
                "Owner principal mismatch",
            )
            passed(
                "Existing PIN login, real JWT refresh and same enabled admin principal"
            )
            base = f"/v1/read/seasons/{OWNER_SEASON}"
            general = check_general(request("GET", base + "/league"))
            overview = OverviewRead.model_validate(request("GET", base + "/overview"))
            initial = InitialAssignmentRead.model_validate(
                request("GET", f"/v1/seasons/{OWNER_SEASON}/initial-assignment")
            )
            require(
                str(initial.season_id) == OWNER_SEASON
                and initial.state == "legacy"
                and initial.rule is None
                and not initial.ready,
                "Existing owner initialization was reinterpreted",
            )
            passed(
                "E real typed initial-assignment read preserves owner legacy initialization"
            )
            require(
                str(general.season.id) == OWNER_SEASON
                and general.season == overview.season,
                "Read scope mismatch",
            )
            require(
                {row.season_player_id for row in general.rows}
                == {row.id for row in overview.players},
                "GENERAL lost season participants",
            )
            current = next(
                (
                    day
                    for day in general.days
                    if day.id == general.season.current_matchday_id
                ),
                None,
            )
            eligibility = query(
                out,
                "owner-current-eligibility",
                "select p.id,p.status,exists(select 1 from public.participant_memberships_at(s.id,d.number) m "
                "where m.season_player_id=p.id) as eligible from public.seasons s "
                "join public.season_players p on p.season_id=s.id "
                "join public.matchdays d on d.id=s.current_matchday_id "
                f"where s.id='{OWNER_SEASON}'::uuid and p.trainer_id='{OWNER}'::uuid",
            )
            eligible = (
                len(eligibility) == 1
                and eligibility[0]["status"] == "active"
                and eligibility[0]["eligible"]
            )
            report["general"] = {
                "rows": len(general.rows),
                "days": len(general.days),
                "unknown_dead_counts": sum(
                    row.dead_count_source == "unknown" for row in general.rows
                ),
                "exact_string_amounts": True,
                "private_fields_absent": True,
            }
            passed(
                "Real GENERAL/overview: exact strings, current roster, reached days and explicit unknown counts"
            )
            day_id = str(current.id) if current else str(uuid4())
            participant = f"/v1/seasons/{OWNER_SEASON}/matchdays/{day_id}"
            if current and eligible:
                raw = request("GET", participant)
                day = DayState.model_validate(raw)
                require(
                    set(raw) == set(DayState.model_fields),
                    "Unexpected participant state fields",
                )
                require(
                    day.season_id == general.season.id
                    and day.matchday_id == current.id,
                    "Participant state scope",
                )
                expected = {
                    (m.id, m.player_a_id, m.player_b_id, m.winner_id)
                    for m in overview.matches
                    if m.matchday_id == current.id
                }
                require(
                    {
                        (m.id, m.player_a_id, m.player_b_id, m.winner_id)
                        for m in day.matches
                    }
                    == expected,
                    "Participant state differs from current published matches",
                )
                require(
                    all(
                        set(m) == {"id", "player_a_id", "player_b_id", "winner_id"}
                        for m in raw["matches"]
                    ),
                    "Unexpected participant match fields",
                )
                passed(
                    "Real eligible participant GET and existing matches without mutation"
                )
            else:
                report["limitations"].append(
                    "Participant positive GET unavailable for current owner/day; not claimed PASS."
                )
            safe_body = {
                "expected_results_revision": 0,
                "results": [
                    {
                        "match_id": str(uuid4()),
                        "winner_season_player_id": None,
                    }
                ],
            }
            for path in (base + "/league", participant):
                request("GET", path, auth=False, status=401)
                request("GET", path, invalid=True, status=401)
            request(
                "PUT",
                participant + "/results",
                body=safe_body,
                auth=False,
                status=401,
                key="phase10-5-anon-" + uuid4().hex,
            )
            request(
                "PUT",
                participant + "/results",
                body=safe_body,
                invalid=True,
                status=401,
                key="phase10-5-invalid-" + uuid4().hex,
            )
            request(
                "PUT",
                participant + "/results",
                body=dict(safe_body, actor_trainer_id=OWNER),
                status=422,
                key="phase10-5-extra-field-" + uuid4().hex,
            )
            absent = str(uuid4())
            absence = query(
                out,
                "absent-season-guard",
                f"select not exists(select 1 from public.seasons where id='{absent}'::uuid) as absent",
            )
            require(absence == [{"absent": True}], "Absent-resource guard failed")
            initial_path = f"/v1/admin/seasons/{absent}/initial-assignment/finalize"
            initial_body = dict(
                config_version_id=str(uuid4()),
                expected_setup_revision=0,
                expected_roster_revision=0,
                input_hash="a" * 64,
            )
            request(
                "GET",
                f"/v1/seasons/{absent}/initial-assignment",
                auth=False,
                status=401,
            )
            request(
                "GET",
                f"/v1/seasons/{absent}/initial-assignment",
                invalid=True,
                status=401,
            )
            initial_denial = request(
                "POST",
                initial_path,
                body=initial_body,
                status=404,
                key="phase10-5e-absent-" + uuid4().hex,
            )
            require(
                initial_denial.get("detail", {}).get("code") == "SEASON_NOT_FOUND",
                "E absent-season denial",
            )
            request(
                "POST",
                initial_path,
                body=dict(initial_body, observed_badges=2),
                status=422,
                key="phase10-5e-forged-" + uuid4().hex,
            )
            passed(
                "E typed finalize denies verified absent season and caller-supplied progress without writes"
            )
            denial = request(
                "PUT",
                f"/v1/seasons/{absent}/matchdays/{uuid4()}/results",
                body=safe_body,
                status=404,
                key="phase10-5-absent-" + uuid4().hex,
            )
            require(
                denial.get("detail", {}).get("code") == "SEASON_NOT_FOUND",
                "Unexpected missing-season denial",
            )
            # Exercise the new typed D contract only against a verified absent season.
            # A valid decision must never be submitted against the owner's actual day.
            tie_body = dict(
                expected_results_revision=0,
                tie_resolution=dict(
                    input_hash="a" * 64,
                    orders=[
                        dict(
                            player_ids=[str(uuid4()), str(uuid4())],
                            reason="Absent-resource validation",
                        )
                    ],
                ),
            )
            tie_path = f"/v1/admin/seasons/{absent}/matchdays/{uuid4()}/close"
            tie_denial = request(
                "POST",
                tie_path,
                body=tie_body,
                status=404,
                key="phase10-5d-absent-" + uuid4().hex,
            )
            require(
                tie_denial.get("detail", {}).get("code") == "SEASON_NOT_FOUND",
                "D close absent-season denial",
            )
            request(
                "POST",
                tie_path,
                body=dict(tie_body, plan={}),
                status=422,
                key="phase10-5d-plan-" + uuid4().hex,
            )
            passed(
                "Deployed D accepts typed tie decision, denies absent resource and injected plan without writes"
            )
            passed(
                "Anonymous/invalid JWT 401, extra actor 422 and absent-season RPC 404; no valid business write"
            )
        stage = "public browser"
        browser_input = {
            "web": WEB,
            "api": API,
            "identifier": "anto",
            "pin": pin,
            "trainer_id": OWNER,
            "output": str(out),
            "league_checks": {
                "rows": len(general.rows),
                "days": [day.number for day in general.days],
                "current_day_number": current.number if current else None,
                "can_record": bool(current and current.status == "open" and eligible),
            },
        }
        browser = subprocess.run(
            ["node", "scripts/validate-public-readonly.mjs"],
            cwd=ROOT / "web",
            input=json.dumps(browser_input),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=480,
        )
        # The child writes its own sanitized evidence. Do not persist stdout/stderr
        # or input: even a future dependency error must not print credentials here.
        report["browser_exit_code"] = browser.returncode
        require(
            browser.returncode == 0,
            "Public browser failed; inspect sanitized browser-result.json",
        )
        result = json.loads((out / "browser-result.json").read_text(encoding="utf-8"))
        require(
            result["status"] == "PASS"
            and result["business_writes"] == 0
            and not result["api_interception"],
            "Browser evidence invalid",
        )
        report["browser"] = {
            "status": "PASS",
            "screen_visits": len(result["screens"]),
            "business_writes": 0,
            "api_interception": False,
        }
        passed(
            "Public React: GENERAL/current day, eleven screens desktop/mobile, admin and logout"
        )
    except BaseException as exc:
        # Exception text may contain tokens, request bodies or transport details.
        report["failures"].append(
            {"stage": stage, "type": type(exc).__name__, "details": "suppressed"}
        )
    finally:
        for label, callback in (
            ("baseline", lambda: before == snapshot(out, "baseline-after", OWNER_AUTH)),
            (
                "migration_history",
                lambda: history == query(out, "history-after", HISTORY),
            ),
            (
                "advisor",
                lambda: sorted(
                    significant(advisors(out, "advisors-after"))
                    - significant(advisor_before)
                ),
            ),
        ):
            initial = {
                "baseline": before,
                "migration_history": history,
                "advisor": advisor_before,
            }[label]
            if initial is None:
                report[label + "_comparison"] = "UNAVAILABLE: no initial evidence"
                continue
            try:
                value = callback()
                report[label + "_comparison"] = value
                require(
                    not value if label == "advisor" else value,
                    "Final state comparison failed",
                )
            except BaseException as exc:
                report["failures"].append(
                    {
                        "stage": "final " + label,
                        "type": type(exc).__name__,
                        "details": "suppressed",
                    }
                )
        report["finished_at"] = now()
        report["status"] = "FAIL" if report["failures"] else "PASS"
        save()
    print(
        "Phase 10.5 public reads: "
        + report["status"]
        + "; sanitized evidence: "
        + str(out)
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
