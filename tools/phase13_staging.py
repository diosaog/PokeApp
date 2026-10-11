"""Loopback-only representative API/browser fixture. Never loads hosted credentials.

Business mutations use the real HTTP routes and PostgreSQL repositories. The only
substituted external boundary is synthetic local Auth; parsed observations enter
the existing identity service because Launcher/cloud ingestion is not complete.
"""

import argparse
from dataclasses import asdict
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import threading
import time
from uuid import NAMESPACE_URL, uuid4, uuid5

import httpx
import jwt
import uvicorn

from app.api.config import APIConfig
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.api.supabase_repository import SupabaseTrainerAuthRepository
from app.auth.credentials import build_internal_auth_credential
from app.auth.errors import InvalidCredentialsError
from app.auth.models import SupabaseAuthSession, SupabaseAuthUser
from app.auth.service import PinAuthBridge
from app.application.pokemon_identity import reconcile_parsed_save
from app.domain.pokemon_identity import CaptureOrder, PokemonIdentityEvidence
from app.domain.pokemon import StatSpread
from app.repositories.supabase.cups import SupabaseCupRepository
from app.repositories.supabase.frontend_reads import SupabaseFrontendReadRepository
from app.repositories.supabase.matchdays import SupabaseMatchdayRepository
from app.repositories.supabase.normal_purchases import SupabaseNormalPurchaseRepository
from app.repositories.supabase.participant_status import (
    SupabaseParticipantStatusRepository,
)
from app.repositories.supabase.pokemon_identity import SupabasePokemonIdentityRepository
from app.repositories.supabase.redemptions import SupabaseRedemptionRepository
from app.repositories.supabase.season_admin import SupabaseSeasonAdminRepository
from app.repositories.supabase.season_lifecycle import SupabaseSeasonLifecycleRepository
from app.repositories.supabase.team_locks import SupabaseTeamLockRepository
from app.repositories.supabase.trials import SupabaseTrialRepository
from app.repositories.supabase.wipe_revivals import SupabaseWipeRevivalsRepository
from tools.validate_supabase_v2_identity_sql import LocalClient, Query, identifier

NAMES = ("Admin", "Alia", "Bruno", "Cora", "Diego", "Elia", "Fabio", "Guest")
PEPPER = "phase13-local-synthetic-only-no-real-secrets"
PIN = "1313"


def uid(value):
    return str(uuid5(NAMESPACE_URL, "pokeapp/phase13/" + value))


class LocalQuery(Query):
    def is_(self, key, value):
        assert value == "null"
        self.filters.append(identifier(key) + " is null")
        return self


class StagingClient(LocalClient):
    legacy_season_fixtures = False

    def __init__(self, args, *a, **kw):
        if not args.database.startswith("pokeapp_v2_validation_phase13_"):
            raise ValueError("Phase13 requires its own disposable database")
        super().__init__(args, *a, **kw)

    def table(self, name):
        return LocalQuery(self, name)


class SyntheticAuth:
    """Local Auth provider: real PIN bridge plus signed, expiring fixture JWTs."""

    def __init__(self):
        self.credentials = {}
        for name in NAMES:
            credential = build_internal_auth_credential(uid(name), PIN, PEPPER)
            self.credentials[credential.email] = (
                credential.password,
                uid(name + "/auth"),
            )

    def session(self, user):
        expires = int(time.time()) + 3600
        access = jwt.encode(
            {"sub": user, "exp": expires, "aud": "phase13-local"},
            PEPPER,
            algorithm="HS256",
        )
        return SupabaseAuthSession(user, access, access, expires, 3600)

    def sign_in_with_password(self, *, email, password):
        expected, user = self.credentials.get(email, (None, None))
        if password != expected or user is None:
            raise InvalidCredentialsError()
        return self.session(user)

    def get_user(self, *, access_token):
        try:
            data = jwt.decode(
                access_token,
                PEPPER,
                algorithms=["HS256"],
                audience="phase13-local",
                options={"require": ["sub", "exp", "aud"]},
            )
            assert data["sub"] in {uid(n + "/auth") for n in NAMES}
            return SupabaseAuthUser(data["sub"])
        except (jwt.PyJWTError, AssertionError, KeyError) as exc:
            raise InvalidCredentialsError() from exc

    def refresh_session(self, *, refresh_token):
        return self.session(self.get_user(access_token=refresh_token).user_id)


class Staging:
    def __init__(self, args):
        self.args = args
        self.db = StagingClient(args)
        self.out = args.output.resolve()
        self.out.mkdir(parents=True, exist_ok=True)
        self.path = self.out / "fixture.json"
        self.data = (
            json.loads(self.path.read_text())
            if self.path.exists()
            else {"checks": [], "observations": {}, "requests": []}
        )
        self.auth = SyntheticAuth()
        repo = SupabaseTrainerAuthRepository(self.db)
        purchase = SupabaseNormalPurchaseRepository(self.db)
        container = ApiContainer(
            auth_bridge=PinAuthBridge(trainers=repo, auth=self.auth, pepper=PEPPER),
            token_verifier=self.auth,
            session_refresher=self.auth,
            trainer_repository=repo,
            principal_repository=repo,
            team_lock_repository=SupabaseTeamLockRepository(self.db),
            purchase_repository=purchase,
            promotional_purchase_repository=purchase,
            redemption_repository=SupabaseRedemptionRepository(self.db),
            season_admin_repository=SupabaseSeasonAdminRepository(self.db),
            matchday_repository=SupabaseMatchdayRepository(self.db),
            participant_status_repository=SupabaseParticipantStatusRepository(self.db),
            season_lifecycle_repository=SupabaseSeasonLifecycleRepository(self.db),
            trial_repository=SupabaseTrialRepository(self.db),
            cup_repository=SupabaseCupRepository(self.db),
            frontend_read_repository=SupabaseFrontendReadRepository(self.db),
            wipe_revivals_repository=SupabaseWipeRevivalsRepository(self.db),
        )
        self.app = create_app(
            container=container,
            config=APIConfig(cors_origins=("http://127.0.0.1:5173",)),
        )
        self.http = httpx.Client(base_url="http://127.0.0.1:8130", timeout=90)

    def save(self):
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")

    def passed(self, name):
        if name not in self.data["checks"]:
            self.data["checks"].append(name)
        self.save()
        print("PASS " + name, flush=True)

    def rows(self, table, **where):
        query = self.db.table(table).select("*")
        for k, v in where.items():
            query = query.eq(k, v)
        return query.execute().data

    def update(self, table, row, **body):
        return self.db.table(table).update(body).eq("id", row).execute().data[0]

    def insert(self, table, body):
        return self.db.table(table).insert(body).execute().data[0]

    def api(self, method, path, body=None, actor="Admin", status=200, key=None):
        headers = {
            "Authorization": "Bearer "
            + self.auth.session(uid(actor + "/auth")).access_token
        }
        if method != "GET":
            headers["Idempotency-Key"] = key or uuid4().hex
        response = self.http.request(method, path, json=body, headers=headers)
        self.data["requests"].append(
            {
                "method": method,
                "path": path,
                "actor": actor,
                "status": response.status_code,
            }
        )
        self.save()
        assert response.status_code == status, (
            method,
            path,
            response.status_code,
            response.text,
        )
        return response.json()

    @property
    def sid(self):
        return self.data["season_id"]

    def read(self, name, actor="Alia"):
        return self.api("GET", f"/v1/read/seasons/{self.sid}/{name}", actor=actor)

    def setup(self):
        return self.api("GET", f"/v1/admin/seasons/{self.sid}/setup")

    def player(self, name):
        return self.rows("season_players", season_id=self.sid, trainer_id=uid(name))[0]

    def observe(self, name, badges=2, champion=False, deaths=0, revived_alive=False):
        """Explicit synthetic parsed-service boundary, not a cloud/parser proof."""
        seq = self.data["observations"].get(name, {}).get("sequence", 0) + 1
        source_hash = hashlib.sha256(
            f"phase13/{self.sid}/{name}/{seq}/{badges}/{champion}/{deaths}".encode()
        ).hexdigest()

        def mon(index):
            evidence = PokemonIdentityEvidence(
                1, 5, index + 100, 12345, 6789, 20, 2, name, 0, ivs=(17, 0, 0, 0, 0, 0)
            )
            return dict(
                species="Pikachu",
                nickname=f"{name}-{index}",
                level=20,
                types=["Electric"],
                nature="Timid",
                ability="Static",
                moves=[{"name": "Thunderbolt"}],
                ivs=asdict(StatSpread(hp=17)),
                evs=asdict(StatSpread(spe=12)),
                metadata={"private_marker": "PHASE13_PRIVATE"},
                identity_evidence=asdict(evidence),
                legacy_fingerprints=[f"p13-{name}-{index}"],
            )

        payload = dict(
            party=[dict(slot_number=i, pokemon=mon(i)) for i in range(1, 7)],
            boxes=[
                dict(
                    box_number=b,
                    slots=[
                        dict(
                            slot_number=i,
                            pokemon=mon(10 + i)
                            if (b == 8 and i <= deaths)
                            or (revived_alive and b == 9 and i == 1)
                            else None,
                        )
                        for i in range(1, 31)
                    ],
                )
                for b in range(1, 10)
            ],
            observed_progress=dict(
                schema_version=1,
                game="B2",
                generation=5,
                source_hash=source_hash,
                progress=None
                if badges is None
                else dict(
                    schema_version=1,
                    primary_region="unova",
                    regions=[
                        dict(region="unova", badge_flags=[i < badges for i in range(8)])
                    ],
                    champion_defeated=champion,
                ),
            ),
        )
        version = "pokeapp-reader/3;pkhex/24.11.11"
        saved = self.insert(
            "save_files",
            dict(
                season_id=self.sid,
                trainer_id=uid(name),
                storage_key=f"phase13-synthetic/{self.sid}/{name}/{seq}",
                original_filename="synthetic-no-bytes.sav",
                sha256=source_hash,
                parser_status="parsed",
                parser_version=version,
            ),
        )
        parsed = self.insert(
            "parsed_saves",
            dict(
                save_file_id=saved["id"],
                parser_version=version,
                schema_version=1,
                payload=payload,
            ),
        )
        self.update(
            "season_players", self.player(name)["id"], current_save_file_id=saved["id"]
        )
        reconcile_parsed_save(
            SupabasePokemonIdentityRepository(self.db),
            season_id=self.sid,
            trainer_id=uid(name),
            parsed_save_id=parsed["id"],
            capture_order=CaptureOrder(uid(self.sid + name), seq),
        )
        self.data["observations"][name] = dict(
            sequence=seq,
            save_id=saved["id"],
            parsed_id=parsed["id"],
            badges=badges,
            champion=champion,
            deaths=deaths,
        )
        self.save()
        return saved

    def prepare(self):
        assert not self.rows("seasons"), (
            "Only an empty dedicated database may be seeded"
        )
        for name in NAMES:
            self.insert(
                "trainers",
                dict(
                    id=uid(name),
                    display_name="Staging " + name,
                    slug="phase13-" + name.lower(),
                    auth_user_id=uid(name + "/auth"),
                    is_admin=name == "Admin",
                ),
            )
        # Actual PIN login and JWT-to-database principal resolution.
        login = self.http.post(
            "/v1/auth/pin-login",
            json={"trainer_identifier": "phase13-alia", "pin": PIN},
        )
        assert login.status_code == 200
        assert (
            self.http.get(
                "/v1/me",
                headers={
                    "Authorization": "Bearer " + login.json()["session"]["access_token"]
                },
            ).json()["is_admin"]
            is False
        )
        assert (
            self.http.get(
                "/v1/me", headers={"Authorization": "Bearer forged"}
            ).status_code
            == 401
        )
        self.data["season_id"] = self.api(
            "POST", "/v1/admin/seasons", {"name": "Phase13 Representative League"}
        )["season_id"]
        for name in NAMES[1:7]:
            state = self.setup()
            self.api(
                "POST",
                f"/v1/admin/seasons/{self.sid}/participants",
                dict(
                    trainer_id=uid(name),
                    seed_order=None,
                    expected_roster_revision=state["roster_revision"],
                ),
            )
        state = self.setup()
        body = dict(
            name="Representative two days",
            effective_from_matchday=1,
            total_matchdays=2,
            division_sizes={"A": 3, "B": 3},
            movement_count=1,
            scoring={str(i): 7 - i for i in range(1, 7)},
            coin_rewards={str(i): 10 for i in range(1, 7)},
            rules={
                "team_lock_required": True,
                "last_b_gets_steal": False,
                "badge_reward_coins": 4,
                "game_completion_reward_coins": 12,
            },
            expected_config_revision=state["config_revision"],
            expected_roster_revision=state["roster_revision"],
        )
        self.api("POST", f"/v1/admin/seasons/{self.sid}/config-versions", body)
        self.api(
            "POST",
            f"/v1/admin/seasons/{self.sid}/activate",
            {"expected_setup_revision": self.setup()["setup_revision"]},
        )
        progress = self.read("progress")
        self.data["unknown_progress"] = progress
        assert "unknown" in json.dumps(progress)
        initial = self.api(
            "GET", f"/v1/seasons/{self.sid}/initial-assignment", actor="Alia"
        )
        assert not initial["ready"] and all(
            p["observed_badges"] is None for p in initial["players"]
        )
        # Prospective rule cutover: earned 4 remains 4, next badge earns 5.
        self.observe("Alia", 1)
        old_claims = self.rows("progress_reward_claims", season_id=self.sid)
        rule = self.api("GET", f"/v1/admin/seasons/{self.sid}/rules")
        self.api(
            "PUT",
            f"/v1/admin/seasons/{self.sid}/rules",
            dict(
                expected_revision=rule["revision"],
                expected_config_revision=rule["config_revision"],
                badge_reward_coins=5,
                game_completion_reward_coins=13,
            ),
        )
        self.observe("Alia", 2)
        assert sorted(
            r["amount"] for r in self.rows("progress_reward_claims", season_id=self.sid)
        ) == [4, 5]
        assert all(
            r in self.rows("progress_reward_claims", season_id=self.sid)
            for r in old_claims
        )
        for index, name in enumerate(NAMES[2:7], 1):
            self.observe(name, 2, False, index)
        initial = self.api(
            "GET", f"/v1/seasons/{self.sid}/initial-assignment", actor="Alia"
        )
        assert initial["ready"] and initial["boundary_tie"] is None
        self.api(
            "POST",
            f"/v1/admin/seasons/{self.sid}/initial-assignment/finalize",
            dict(
                config_version_id=initial["config_version_id"],
                expected_setup_revision=initial["setup_revision"],
                expected_roster_revision=initial["roster_revision"],
                input_hash=initial["input_hash"],
            ),
        )
        self.data["day1"] = self.setup()["current_matchday_id"]
        self.data["trainers"] = {name: uid(name) for name in NAMES}
        self.passed(
            "modern six-player creation, unknown progress, Medal2 split, prospective 4/5 rewards, synthetic PIN/JWT"
        )

    def progress_checks(self):
        # 8 badges without Champion evidence cannot pay completion.
        self.observe("Alia", 8, False)
        claims = self.rows(
            "progress_reward_claims", season_id=self.sid, trainer_id=uid("Alia")
        )
        self.data["badge_claims"] = claims
        assert sum(Decimal(str(c["amount"])) for c in claims) == Decimal(39)
        self.observe("Alia", 8, True, deaths=1)
        complete = self.rows(
            "progress_reward_claims", season_id=self.sid, trainer_id=uid("Alia")
        )
        assert len(complete) == len(claims) + 1 and sum(
            Decimal(str(c["amount"])) for c in complete
        ) == Decimal(52)
        self.observe("Alia", 8, True, deaths=1)
        assert (
            self.rows(
                "progress_reward_claims", season_id=self.sid, trainer_id=uid("Alia")
            )
            == complete
        )
        self.passed(
            "8 badges distinct from Champion, one completion reward, observation replay without new claims"
        )

    def before_browser(self):
        if (
            "8 badges distinct from Champion, one completion reward, observation replay without new claims"
            not in self.data["checks"]
        ):
            self.progress_checks()
        did = self.data["day1"]
        state = self.api("GET", f"/v1/seasons/{self.sid}/matchdays/{did}", actor="Alia")
        self.api(
            "POST",
            f"/v1/seasons/{self.sid}/matchdays/{did}/open",
            {"expected_revision": state["revision"]},
            actor="Guest",
            status=403,
        )
        self.api(
            "POST",
            f"/v1/admin/seasons/{self.sid}/archive",
            {"expected_revision": self.setup()["setup_revision"]},
            actor="Alia",
            status=403,
        )
        # On-time lock through the actual team-lock API; later browser tests create a late lock.
        saved = self.data["observations"]["Alia"]["save_id"]
        lock = self.api(
            "PUT",
            f"/v1/seasons/{self.sid}/matchdays/{did}/team-lock",
            {"save_file_id": saved},
            actor="Alia",
        )
        self.data["on_time_lock"] = self.rows(
            "team_lock_first_fixations", lock_id=lock["id"]
        )[0]
        assert self.data["on_time_lock"]["timing_status"] == "on_time"
        self.save()
        self.passed(
            "nonmember lifecycle/Admin-only denials and on-time first lock through HTTP"
        )

    def day(self, did):
        return self.api("GET", f"/v1/seasons/{self.sid}/matchdays/{did}", actor="Alia")

    def results(self, did):
        state = self.day(did)
        priority = ["Cora", "Bruno", "Alia", "Diego", "Elia", "Fabio"]
        order = {self.player(n)["id"]: i for i, n in enumerate(priority)}
        body = dict(
            expected_results_revision=state["results_revision"],
            results=[
                dict(
                    match_id=m["id"],
                    winner_season_player_id=min(
                        (m["player_a_id"], m["player_b_id"]), key=order.__getitem__
                    ),
                )
                for m in state["matches"]
            ],
        )
        self.api(
            "PUT", f"/v1/seasons/{self.sid}/matchdays/{did}/results", body, actor="Alia"
        )

    def live_deaths(self, name):
        rows = (
            self.db.rpc("initial_assignment_observations", {"sid": self.sid})
            .execute()
            .data
        )
        return next(r["adjusted_deaths"] for r in rows if r["trainer_id"] == uid(name))

    def after_browser(self):
        did = self.data["day1"]
        assert (
            self.rows(
                "team_lock_first_fixations",
                lock_id=self.data["on_time_lock"]["lock_id"],
            )[0]
            == self.data["on_time_lock"]
        )
        bruno = self.rows("team_locks", season_id=self.sid, trainer_id=uid("Bruno"))[0]
        assert (
            self.rows("team_lock_first_fixations", lock_id=bruno["id"])[0][
                "timing_status"
            ]
            == "late"
        )
        for actor in ("Admin", "Bruno"):
            rival = self.read(
                "team-preview?mode=battle&trainer_id=" + uid("Alia"), actor
            )
            public = self.read("scouting?trainer_id=" + uid("Alia"), actor)
            for value in (rival, public):
                text = json.dumps(value)
                assert not any(
                    '"' + key + '"' in text
                    for key in (
                        "ivs",
                        "evs",
                        "nature",
                        "ability",
                        "identity_evidence",
                        "metadata",
                    )
                )
            # Even an injected rival selector cannot change the owned PC scope.
            pc = self.read("pc?trainer_id=" + uid("Alia"), actor)
            if actor == "Admin":
                assert pc["status"] == "no_current_save"
            else:
                assert all(
                    p["pokemon"]["nickname"].startswith("Bruno-") for p in pc["pokemon"]
                )
        self.passed(
            "first-lock timing preserved, Admin/rival private-data denial and owned PC scope"
        )
        rule = self.api("GET", f"/v1/admin/seasons/{self.sid}/rules")
        assert (rule["badge_reward_coins"], rule["game_completion_reward_coins"]) == (
            7,
            15,
        )
        old = self.rows("progress_reward_claims", season_id=self.sid)
        self.observe("Cora", 3, False, 2)
        claims = self.rows("progress_reward_claims", season_id=self.sid)
        assert all(r in claims for r in old) and len(claims) == len(old) + 1
        assert (
            sum(Decimal(str(r["amount"])) for r in claims)
            - sum(Decimal(str(r["amount"])) for r in old)
            == 7
        )
        purchases = self.rows("purchases", season_id=self.sid, trainer_id=uid("Alia"))
        assert len(purchases) == 1 and purchases[0]["status"] == "used"
        bought = purchases[0]
        before = self.rows("coin_transactions", season_id=self.sid)
        replay = self.api(
            "POST",
            f"/v1/seasons/{self.sid}/shop/purchases",
            dict(item_id=bought["shop_item_id"], confirm_base_price=True),
            actor="Alia",
            key=bought["idempotency_key"],
        )
        assert (
            replay["id"] == bought["id"]
            and self.rows("coin_transactions", season_id=self.sid) == before
        )
        self.api(
            "POST",
            f"/v1/seasons/{self.sid}/shop/purchases",
            dict(item_id=bought["shop_item_id"], confirm_base_price=True),
            actor="Bruno",
            status=409,
        )
        assert self.rows("coin_transactions", season_id=self.sid) == before
        assert self.read("shop")["balance"] == "40"
        assert self.live_deaths("Bruno") == 1 and self.live_deaths("Alia") == 3
        redemption = self.rows("redemptions", purchase_id=bought["id"])[0]
        assert redemption["physical_effect_status"] == "pending"
        # Supported service observation of the same identity outside Box8, not a physical write.
        self.observe("Alia", 8, True, deaths=0, revived_alive=True)
        assert self.live_deaths("Alia") == 3
        assert (
            next(
                r["dead_count"]
                for r in self.read("league")["rows"]
                if r["trainer_id"] == uid("Alia")
            )
            == 0
        )
        self.passed(
            "UI rule cutover pays next event only; purchase replay/no overdraft; revive 1 plus wipe 2 without double count"
        )
        self.results(did)
        self.data["day1_locks_before_close"] = self.rows("team_locks", matchday_id=did)
        self.data["initial_snapshot"] = self.rows(
            "initial_division_snapshots", season_id=self.sid
        )
        self.data["main_season_id"] = self.sid
        self.save()
        self.passed(
            "all J1 results complete through participant HTTP, ready for browser close"
        )

    def finish_journey(self):
        did = self.data["day1"]
        assert self.day(did)["state"] == "closed"
        frozen = self.rows("matchday_snapshot_revisions", matchday_id=did)
        assert len(frozen) == 1
        self.data["day1_frozen"] = frozen
        self.api(
            "PUT",
            f"/v1/seasons/{self.sid}/matchdays/{did}/results",
            dict(
                expected_results_revision=self.day(did)["results_revision"],
                results=[
                    dict(
                        match_id=self.day(did)["matches"][0]["id"],
                        winner_season_player_id=None,
                    )
                ],
            ),
            actor="Alia",
            status=409,
        )
        self.api(
            "POST",
            f"/v1/admin/seasons/{self.sid}/matchdays/{did}/correct",
            dict(
                expected_snapshot_revision=1,
                reason="Forbidden ordinary correction",
                results=[
                    dict(
                        match_id=self.day(did)["matches"][0]["id"],
                        winner_season_player_id=None,
                    )
                ],
            ),
            actor="Alia",
            status=403,
        )
        self.api(
            "PUT",
            f"/v1/seasons/{self.sid}/matchdays/{did}/team-lock",
            {"save_file_id": self.data["observations"]["Alia"]["save_id"]},
            actor="Alia",
            status=409,
        )
        assert (
            self.rows("team_locks", matchday_id=did)
            == self.data["day1_locks_before_close"]
        )
        # The frozen sporting capture proves exact death deductions, independent of live display.
        snap = self.rows("matchday_snapshots", matchday_id=did)[0]
        self.data["j1_snapshot"] = snap
        self.passed("closed result/correction/TeamLock denials and immutable J1 source")
        next_day = self.setup()["current_matchday_id"]
        self.data["day2"] = next_day
        self.api(
            "POST",
            f"/v1/seasons/{self.sid}/matchdays/{next_day}/open",
            {"expected_revision": self.day(next_day)["revision"]},
            actor="Bruno",
        )
        # Later observations can change live state, not J1 or initial frozen evidence.
        self.observe("Cora", 4, False, 2)
        assert self.rows("matchday_snapshot_revisions", matchday_id=did) == frozen
        assert (
            self.rows("initial_division_snapshots", season_id=self.sid)
            == self.data["initial_snapshot"]
        )
        self.results(next_day)
        body = {"expected_results_revision": self.day(next_day)["results_revision"]}
        key = "phase13-final-day-close"
        closed = self.api(
            "POST",
            f"/v1/seasons/{self.sid}/matchdays/{next_day}/close",
            body,
            actor="Bruno",
            key=key,
        )
        coins = self.rows("coin_transactions", season_id=self.sid)
        repeated = self.api(
            "POST",
            f"/v1/seasons/{self.sid}/matchdays/{next_day}/close",
            body,
            actor="Bruno",
            key=key,
        )
        assert (
            closed["operation_id"] == repeated["operation_id"]
            and self.rows("coin_transactions", season_id=self.sid) == coins
        )
        title = self.api("GET", f"/v1/seasons/{self.sid}/championship", actor="Alia")
        assert title["state"] == "ready" and title["resolution_type"] == "unique_points"
        assert title["champion_trainer_id"] == uid("Cora")
        finish = dict(
            expected_revision=title["setup_revision"], input_hash=title["input_hash"]
        )
        first = self.api(
            "POST",
            f"/v1/seasons/{self.sid}/finish",
            finish,
            actor="Alia",
            key="phase13-finish",
        )
        again = self.api(
            "POST",
            f"/v1/seasons/{self.sid}/finish",
            finish,
            actor="Alia",
            key="phase13-finish",
        )
        assert first["operation_id"] == again["operation_id"]
        assert self.rows("coin_transactions", season_id=self.sid) == coins
        self.api(
            "POST",
            f"/v1/admin/seasons/{self.sid}/archive",
            dict(
                expected_revision=self.setup()["setup_revision"],
                label="Phase13 frozen League",
            ),
        )
        hall = self.rows(
            "hall_of_fame_entries", season_id=self.sid, competition_type="league"
        )
        assert len(hall) == 1 and hall[0]["champion_trainer_id"] == uid("Cora")
        assert hall[0]["team_snapshot"] == [], (
            "Cora never locked a team; cannot fabricate one"
        )
        self.data["main_title"] = title
        self.data["main_hall"] = hall
        self.passed(
            "two-day League, exact-once close/rewards/participant finish, normal champion and frozen archive/Hall"
        )

    def new_scenario(self, label, deaths):
        assert not self.rows("seasons", status="active")
        sid = self.api("POST", "/v1/admin/seasons", {"name": "Phase13 " + label})[
            "season_id"
        ]
        self.data["season_id"] = sid
        self.data["observations"] = {}
        self.save()
        for name in NAMES[1:7]:
            self.api(
                "POST",
                f"/v1/admin/seasons/{sid}/participants",
                dict(
                    trainer_id=uid(name),
                    seed_order=None,
                    expected_roster_revision=self.setup()["roster_revision"],
                ),
            )
        state = self.setup()
        body = dict(
            name=label,
            effective_from_matchday=1,
            total_matchdays=1,
            division_sizes={"A": 3, "B": 3},
            movement_count=0,
            scoring={str(i): 10 for i in range(1, 7)},
            coin_rewards={str(i): 0 for i in range(1, 7)},
            rules=dict(
                team_lock_required=True,
                last_b_gets_steal=False,
                badge_reward_coins=0,
                game_completion_reward_coins=0,
            ),
            expected_config_revision=state["config_revision"],
            expected_roster_revision=state["roster_revision"],
        )
        self.api("POST", f"/v1/admin/seasons/{sid}/config-versions", body)
        self.api(
            "POST",
            f"/v1/admin/seasons/{sid}/activate",
            {"expected_setup_revision": self.setup()["setup_revision"]},
        )
        for name, count in zip(NAMES[1:7], deaths):
            self.observe(name, 2, False, count)
        review = self.api("GET", f"/v1/seasons/{sid}/initial-assignment", actor="Alia")
        assert review["ready"] and not review["boundary_tie"]
        self.api(
            "POST",
            f"/v1/admin/seasons/{sid}/initial-assignment/finalize",
            dict(
                config_version_id=review["config_version_id"],
                expected_setup_revision=review["setup_revision"],
                expected_roster_revision=review["roster_revision"],
                input_hash=review["input_hash"],
            ),
        )
        return self.setup()["current_matchday_id"]

    def championship_cases(self):
        scenarios = (
            ("bo3", 2, [0, 1, 2, 3, 4, 5]),
            ("three", 3, [0, 1, 2, 3, 4, 5]),
            ("four", 4, [0, 1, 2, 3, 4, 5]),
            ("residual", 4, [0, 0, 2, 3, 4, 5]),
        )
        for label, leaders, deaths in scenarios:
            if "championship " + label in self.data["checks"]:
                continue
            did = self.new_scenario("Championship " + label, deaths)
            # Synthetic sanctioned facts, established before closure. Do not
            # edit snapshots or supply authoritative totals to the title API.
            targets = {}
            for index, name in enumerate(NAMES[1:7]):
                target = Decimal("5.5") if index < leaders else Decimal("-2.1")
                deduction = Decimal(10) - Decimal("0.2") * deaths[index] - target
                self.insert(
                    "penalties",
                    dict(
                        season_id=self.sid,
                        trainer_id=uid(name),
                        penalty_type="points_reduction",
                        amount=0,
                        points_amount=str(deduction),
                    ),
                )
                targets[uid(name)] = target
            self.api(
                "POST",
                f"/v1/seasons/{self.sid}/matchdays/{did}/open",
                {"expected_revision": self.day(did)["revision"]},
                actor="Alia",
            )
            self.results(did)
            self.api(
                "POST",
                f"/v1/seasons/{self.sid}/matchdays/{did}/close",
                {"expected_results_revision": self.day(did)["results_revision"]},
                actor="Alia",
            )
            review = self.api(
                "GET", f"/v1/seasons/{self.sid}/championship", actor="Alia"
            )
            assert {
                p["trainer_id"]: Decimal(p["total_points"]) for p in review["players"]
            } == targets
            if label in ("bo3", "residual"):
                assert (
                    review["state"]
                    == ("bo3_required" if label == "bo3" else "residual_required")
                    and review["champion_trainer_id"] is None
                )
                self.api(
                    "POST",
                    f"/v1/seasons/{self.sid}/finish",
                    dict(
                        expected_revision=review["setup_revision"],
                        input_hash=review["input_hash"],
                    ),
                    actor="Alia",
                    status=409,
                )
                winner = self.player("Bruno")["id"]
                assert winner in review["tied_player_ids"]
                decision = dict(
                    expected_revision=review["setup_revision"],
                    input_hash=review["input_hash"],
                    winner_season_player_id=winner,
                    reason="External staging BO3 2-1"
                    if label == "bo3"
                    else "External staging residual resolution",
                )
                path = f"/v1/admin/seasons/{self.sid}/championship/" + label
                self.api("POST", path, dict(decision, reason=" "), status=422)
                self.api(
                    "POST",
                    path,
                    dict(decision, winner_season_player_id=self.player("Cora")["id"]),
                    status=409,
                )
                self.api("POST", path, decision, actor="Alia", status=403)
                resolved = self.api(
                    "POST", path, decision, key="phase13-title-resolution"
                )
                replay = self.api(
                    "POST", path, decision, key="phase13-title-resolution"
                )
                assert resolved["operation_id"] == replay["operation_id"]
                assert (
                    len(
                        self.rows("league_championship_resolutions", season_id=self.sid)
                    )
                    == 1
                )
                review = self.api(
                    "GET", f"/v1/seasons/{self.sid}/championship", actor="Alia"
                )
                assert review["champion_trainer_id"] == uid("Bruno")
            else:
                assert review["state"] == "ready" and review[
                    "champion_trainer_id"
                ] == uid("Alia")
                assert review["resolution_type"] == (
                    "triple_adjusted_deaths"
                    if label == "three"
                    else "multiple_adjusted_deaths"
                )
            self.api(
                "POST",
                f"/v1/seasons/{self.sid}/finish",
                dict(
                    expected_revision=review["setup_revision"],
                    input_hash=review["input_hash"],
                ),
                actor="Alia",
            )
            self.api(
                "POST",
                f"/v1/admin/seasons/{self.sid}/archive",
                dict(
                    expected_revision=self.setup()["setup_revision"],
                    label="Frozen " + label,
                ),
            )
            stored = self.api(
                "GET", f"/v1/seasons/{self.sid}/championship", actor="Alia"
            )
            assert (
                stored["state"] == "frozen"
                and stored["champion_trainer_id"] == review["champion_trainer_id"]
            )
            self.data.setdefault("championships", {})[label] = review
            self.passed("championship " + label)

    def cup_case(self):
        self.new_scenario("Cup boundaries", [0, 1, 2, 3, 4, 5])
        sid = self.sid
        # League DQ before Cup entry. Cup authority remains independent.
        self.api(
            "POST",
            f"/v1/admin/seasons/{sid}/participants/{self.player('Alia')['id']}/disqualify",
            dict(
                reason="Synthetic League-only DQ",
                expected_roster_revision=self.setup()["roster_revision"],
            ),
        )
        cup = self.api(
            "POST",
            f"/v1/admin/seasons/{sid}/cups",
            dict(
                name="Representative modern Cup",
                format="elimination",
                swiss_rounds=1,
                sides=[
                    dict(name="Side " + name, trainer_ids=[uid(name)])
                    for name in ("Alia", "Bruno", "Cora", "Diego")
                ],
            ),
        )
        cid = cup["cup_id"]
        base = f"/v1/admin/seasons/{sid}/cups/{cid}"

        def read():
            return self.api("GET", f"/v1/seasons/{sid}/cups/{cid}", actor="Bruno")

        detail = read()
        alia = next(
            s for s in detail["sides"] if s["members"][0]["trainer_id"] == uid("Alia")
        )
        assert alia["status"] == "active"
        self.api(
            "POST",
            f"/v1/admin/seasons/{sid}/participants/{self.player('Bruno')['id']}/disqualify",
            dict(
                reason="Must preserve linked Cup",
                expected_roster_revision=self.setup()["roster_revision"],
            ),
            status=409,
        )
        self.api(
            "POST",
            base + "/start",
            dict(expected_revision=detail["revision"]),
            actor="Bruno",
            status=403,
        )
        self.api("POST", base + "/start", dict(expected_revision=detail["revision"]))
        league = {
            t: self.rows(t, season_id=sid)
            for t in (
                "season_players",
                "matchdays",
                "matches",
                "coin_transactions",
                "matchday_snapshots",
            )
        }
        for _ in range(8):
            detail = read()
            rnd = detail["rounds"][-1]
            if rnd["phase"] == "final" and rnd["status"] == "closed":
                break
            matches = [
                dict(match_id=m["id"], score_a=2, score_b=1)
                for m in rnd["matches"]
                if m["status"] == "scheduled"
            ]
            if matches:
                self.api(
                    "PUT",
                    base + f"/rounds/{rnd['number']}/results",
                    dict(expected_revision=detail["revision"], results=matches),
                )
            self.api(
                "POST",
                base + f"/rounds/{rnd['number']}/close",
                dict(expected_revision=read()["revision"]),
            )
        else:
            raise AssertionError("Modern Cup failed to reach final")
        body = dict(expected_revision=read()["revision"])
        first = self.api("POST", base + "/finalize", body, key="phase13-cup-finalize")
        repeated = self.api(
            "POST", base + "/finalize", body, key="phase13-cup-finalize"
        )
        assert first["certificate_id"] == repeated["certificate_id"]
        assert len(self.rows("cup_certificates", cup_id=cid)) == 1
        assert all(self.rows(t, season_id=sid) == rows for t, rows in league.items())
        assert (
            self.rows(
                "hall_of_fame_entries",
                season_id=self.data["main_season_id"],
                competition_type="league",
            )
            == self.data["main_hall"]
        )
        self.data["cup"] = read()
        self.passed(
            "modern Cup rounds/final/certificate/Hall replay; League-only DQ and linked-Cup guards; League history unchanged"
        )

    def verify(self):
        """Final read-only reconciliation before destroying this disposable DB."""
        sid, did = self.data["main_season_id"], self.data["day1"]
        assert (
            self.rows("matchday_snapshot_revisions", matchday_id=did)
            == self.data["day1_frozen"]
        )
        assert self.rows("matchday_snapshots", matchday_id=did) == [
            self.data["j1_snapshot"]
        ]
        assert (
            self.rows("initial_division_snapshots", season_id=sid)
            == self.data["initial_snapshot"]
        )
        assert (
            self.rows("team_locks", matchday_id=did)
            == self.data["day1_locks_before_close"]
        )
        assert (
            self.rows("hall_of_fame_entries", season_id=sid, competition_type="league")
            == self.data["main_hall"]
        )
        snapshot = self.data["j1_snapshot"]["snapshot"]
        player_ids = {p["trainer_id"]: p["id"] for p in snapshot["inputs"]["players"]}
        standing = {p["trainer_id"]: p for p in snapshot["standings"]}
        normal = standing[player_ids[uid("Bruno")]]["penalties"]
        revived = standing[player_ids[uid("Alia")]]["penalties"]
        assert normal["dead_count"] == 1 and Decimal(
            str(normal["dead_points_penalty"])
        ) == Decimal("0.2")
        assert revived["dead_count"] == 3 and Decimal(
            str(revived["dead_points_penalty"])
        ) == Decimal("0.6")
        totals = {
            p["trainer_id"]: p["total_points"]
            for p in self.data["main_title"]["players"]
        }
        assert Decimal(totals[uid("Alia")]) == Decimal("6.4")
        assert len(self.rows("league_finalizations")) == 5
        assert len(self.rows("cup_certificates")) == 1
        assert len(self.rows("hall_of_fame_entries")) == 6
        proof = {
            "status": "PASS",
            "postgresql": "17.11",
            "database": self.args.database,
            "frozen_sources_unchanged_after_later_scenarios": True,
            "normal_death_penalty": "0.2",
            "purchased_revive_plus_wipe_penalty": "0.6",
            "two_day_alia_total": totals[uid("Alia")],
            "league_certificates": 5,
            "cup_certificates": 1,
            "hall_entries": 6,
            "http_requests": len(self.data["requests"]),
            "scenario_checks": list(self.data["checks"]),
        }
        (self.out / "local-proof.json").write_text(
            json.dumps(proof, indent=2), encoding="utf-8"
        )
        print(json.dumps(proof), flush=True)

    def serve(self):
        server = uvicorn.Server(
            uvicorn.Config(self.app, host="127.0.0.1", port=8130, log_level="warning")
        )
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        for _ in range(100):
            if server.started:
                return server, thread
            time.sleep(0.05)
        raise RuntimeError("Local API did not start")


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=(
            "prepare",
            "before-browser",
            "after-browser",
            "finish-journey",
            "championships",
            "cup",
            "verify",
            "serve",
        ),
    )
    parser.add_argument(
        "--connect", action="store_true", help="Use an already-running isolated API"
    )
    parser.add_argument("--psql", required=True)
    parser.add_argument("--database", default="pokeapp_v2_validation_phase13_20261011")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=55439)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--password", default="")
    return parser.parse_args()


def main():
    args = arguments()
    staging = Staging(args)
    server, thread = (None, None) if args.connect else staging.serve()
    try:
        if args.mode == "prepare":
            staging.prepare()
        elif args.mode == "before-browser":
            staging.before_browser()
        elif args.mode == "after-browser":
            staging.after_browser()
        elif args.mode == "finish-journey":
            staging.finish_journey()
        elif args.mode == "championships":
            staging.championship_cases()
        elif args.mode == "cup":
            staging.cup_case()
        elif args.mode == "verify":
            staging.verify()
        else:
            print("LOCAL STAGING API READY 127.0.0.1:8130", flush=True)
            while not (staging.out / "stop-api").exists():
                time.sleep(0.5)
    finally:
        if server:
            server.should_exit = True
            thread.join(timeout=10)
        staging.http.close()


if __name__ == "__main__":
    main()
