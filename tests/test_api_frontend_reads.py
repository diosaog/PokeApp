"""Read privacy, scope, malformed sources and explicit cross-origin boundary."""

from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import Mock
from uuid import uuid4
import httpx
from postgrest import SyncPostgrestClient

from fastapi.testclient import TestClient
from app.api.config import APIConfig
from app.api.dependencies import ApiContainer
from app.api.main import create_app
from app.repositories.errors import PersistenceError
from app.repositories.supabase.frontend_reads import SupabaseFrontendReadRepository
from test_api_phase8b import FakePrincipalRepository, FakeTokenVerifier, TRAINER_ID

SID, PID, SAVE, DAY, DIV = [str(uuid4()) for _ in range(5)]


class ReadStore:
    def __init__(self):
        self.calls = []
        self.data = {
            "seasons": [
                dict(id=SID, name="Liga", status="active", current_matchday_id=DAY)
            ],
            "public_seasons": [
                dict(id=SID, name="Liga", status="active", metadata="SECRET")
            ],
            "public_trainers": [
                dict(id=TRAINER_ID, display_name="Antonio", auth_user_id="SECRET")
            ],
            "season_players": [
                dict(
                    id=PID,
                    season_id=SID,
                    trainer_id=TRAINER_ID,
                    current_save_file_id=SAVE,
                )
            ],
            "save_files": [
                dict(
                    id=SAVE,
                    season_id=SID,
                    trainer_id=TRAINER_ID,
                    deleted_at=None,
                    parser_status="parsed",
                    parser_version="v1",
                    uploaded_at="2026-09-28T12:00:00Z",
                    sha256="a" * 64,
                    storage_key="SECRET",
                )
            ],
            "parsed_saves": [
                dict(
                    save_file_id=SAVE,
                    parser_version="v1",
                    status="parsed",
                    schema_version=1,
                    payload=dict(
                        save_record_id=SAVE,
                        trainer_id=TRAINER_ID,
                        source_hash="a" * 64,
                        party=[
                            dict(
                                slot_number=1,
                                pokemon=dict(
                                    species="Pikachu",
                                    ability="Static",
                                    identity_evidence="SECRET",
                                    metadata="SECRET",
                                ),
                            )
                        ],
                        boxes=[],
                    ),
                )
            ],
        }

    def observed_progress(self, season_id, trainer_id=None):
        return [dict(id=p["id"], trainer_id=p["trainer_id"], game=None,
                     observed_at=None, progress=None)
                for p in self.data.get("public_season_players", [])
                if p.get("season_id") == season_id
                and (trainer_id is None or p["trainer_id"] == trainer_id)]

    def shield_targets(self, season_id, trainer_id):
        return []

    def rows(self, table, columns, *, filters=None, offset=0, limit=500, **kwargs):
        self.calls.append((table, columns, filters, offset, limit))
        return deepcopy(
            [
                r
                for r in self.data.get(table, [])
                if all(r.get(k) == v for k, v in (filters or {}).items())
            ][offset : offset + limit]
        )


class FrontendReadTests(unittest.TestCase):
    def setUp(self):
        self.store = ReadStore()
        self.principals = FakePrincipalRepository()
        self.client = TestClient(
            create_app(
                container=ApiContainer(
                    token_verifier=FakeTokenVerifier(),
                    principal_repository=self.principals,
                    frontend_read_repository=self.store,
                ),
                config=APIConfig(),
            )
        )
        self.addCleanup(self.client.close)
        self.headers = {"Authorization": "Bearer validated"}

    def get(self, path):
        return self.client.get("/v1/read/" + path, headers=self.headers)

    def test_authentication_and_disabled_guard_before_reads(self):
        self.assertEqual(self.client.get("/v1/read/seasons").status_code, 401)
        self.principals.trainer = replace(
            self.principals.trainer, globally_enabled=False
        )
        self.assertEqual(self.get("seasons").status_code, 403)
        self.assertEqual(self.store.calls, [])

    def test_public_lists_strip_credentials_and_metadata(self):
        for path in ("seasons", "trainers"):
            result = self.get(path)
            self.assertEqual(result.status_code, 200)
            self.assertNotIn("SECRET", result.text)

    def test_pc_owner_from_verified_jwt_not_query(self):
        response = self.get(f"seasons/{SID}/pc?trainer_id={uuid4()}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pokemon"][0]["pokemon"]["ability"], "Static")
        self.assertNotIn("SECRET", response.text)
        save_call = next(c for c in self.store.calls if c[0] == "save_files")
        self.assertEqual(
            save_call[2],
            dict(id=SAVE, season_id=SID, trainer_id=TRAINER_ID, deleted_at=None),
        )

    def test_pc_does_not_read_foreign_or_deleted_save(self):
        for change in (
            {"trainer_id": str(uuid4())},
            {"season_id": str(uuid4())},
            {"deleted_at": "2026-09-28"},
        ):
            with self.subTest(change=change):
                old = deepcopy(self.store.data["save_files"][0])
                self.store.data["save_files"][0].update(change)
                self.assertEqual(
                    self.get(f"seasons/{SID}/pc").json()["status"], "no_current_save"
                )
                self.store.data["save_files"][0] = old

    def test_pc_checks_parser_version_and_identity(self):
        row = self.store.data["parsed_saves"][0]
        row["parser_version"] = "old"
        self.assertEqual(self.get(f"seasons/{SID}/pc").json()["status"], "not_ready")
        row["parser_version"] = "v1"
        row["payload"]["trainer_id"] = str(uuid4())
        self.assertEqual(self.get(f"seasons/{SID}/pc").status_code, 503)

    def test_unknown_and_legacy_payload_are_explicit(self):
        row = self.store.data["parsed_saves"][0]
        row["schema_version"] = 2
        self.assertEqual(
            self.get(f"seasons/{SID}/pc").json()["status"], "unsupported_payload"
        )
        row["schema_version"] = 1
        row["payload"]["party"] = [{"species": "Pikachu"}]
        self.assertEqual(
            self.get(f"seasons/{SID}/pc").json()["status"], "unsupported_payload"
        )

    def test_missing_or_discarded_season_not_available(self):
        self.assertEqual(self.get(f"seasons/{uuid4()}/overview").status_code, 404)
        self.store.data["seasons"][0]["status"] = "discarded"
        self.assertEqual(self.get(f"seasons/{SID}/pc").status_code, 404)

    def test_official_snapshot_uses_player_identity_and_strips_inputs(self):
        self.store.data["public_matchday_snapshots"] = [
            dict(
                season_id=SID,
                matchday_id=DAY,
                revision=2,
                closed_at="2026-09-28T12:00:00Z",
                snapshot=dict(
                    schema_version=2,
                    inputs="SECRET",
                    standings=[
                        dict(
                            trainer_id=PID,
                            division_id="A",
                            position=1,
                            division_position=1,
                            points_awarded=10,
                            score="9.80",
                            penalties="SECRET",
                        )
                    ],
                ),
            )
        ]
        result = self.get(f"seasons/{SID}/overview")
        self.assertEqual(result.status_code, 200)
        self.assertNotIn("SECRET", result.text)
        row = result.json()["snapshots"][0]["standings"][0]
        self.assertEqual(row["season_player_id"], PID)
        self.assertEqual(row["score"], "9.80")

    def test_public_team_strips_private_nested_fields(self):
        self.store.data["public_team_locks"] = [
            dict(
                season_id=SID,
                trainer_id=TRAINER_ID,
                matchday_id=DAY,
                locked_at="2026-09-28T12:00:00Z",
                is_late=False,
                public_team_snapshot=[
                    dict(
                        species="Pikachu",
                        ability="SECRET",
                        ivs="SECRET",
                        metadata="SECRET",
                        moves=[dict(name="Thunder", metadata="SECRET")],
                    )
                ],
            )
        ]
        result = self.get(f"seasons/{SID}/overview")
        self.assertEqual(result.status_code, 200)
        self.assertNotIn("SECRET", result.text)

    def test_collection_capacity_fails_instead_of_partial_standings(self):
        self.store.data["public_matches"] = [
            dict(id=str(uuid4()), season_id=SID) for _ in range(501)
        ]
        self.assertEqual(self.get(f"seasons/{SID}/overview").status_code, 503)

    def test_seasons_pagination_and_invalid_offset(self):
        self.store.data["public_seasons"] *= 51
        result = self.get("seasons").json()
        self.assertEqual(len(result["items"]), 50)
        self.assertEqual(result["next_offset"], 50)
        self.assertEqual(len(self.get("seasons?offset=50").json()["items"]), 1)
        self.assertEqual(self.get("seasons?offset=-1").status_code, 422)

    def test_hall_doubles_nullable_identity_and_exact_cup(self):
        cup, side, other = [str(uuid4()) for _ in range(3)]
        self.store.data["public_hall_of_fame"] = [
            dict(
                id=str(uuid4()),
                season_id=SID,
                competition_type="cup",
                champion_trainer_id=None,
                finalist_trainer_id=None,
                finalized_at="2026-09-28T12:00:00Z",
                cup_id=cup,
                cup_certificate_id=str(uuid4()),
                champion_side_id=side,
                finalist_side_id=other,
                cup_checksum="checksum",
                cup_sides=[
                    dict(
                        id=side,
                        name="Dúo",
                        seed=1,
                        status="active",
                        members=[
                            dict(
                                trainer_id=str(uuid4()),
                                season_player_id=str(uuid4()),
                                display_name=name,
                            )
                            for name in ("Uno", "Dos")
                        ],
                    )
                ],
            )
        ]
        result = self.get("hall")
        self.assertEqual(result.status_code, 200)
        row = result.json()["items"][0]
        self.assertEqual(row["cup_id"], cup)
        self.assertIsNone(row["champion_trainer_id"])
        self.assertEqual(len(row["cup_sides"][0]["members"]), 2)

    def test_repository_bounds_null_filter_and_no_sensitive_select(self):
        client = Mock()
        client.table.return_value.select.return_value.is_.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []
        repo = SupabaseFrontendReadRepository(client)
        self.assertEqual(
            repo.rows(
                "save_files",
                "id,parser_status",
                filters={"deleted_at": None, "trainer_id": TRAINER_ID},
                offset=4,
                limit=5,
            ),
            [],
        )
        client.table.return_value.select.assert_called_once_with("id,parser_status")
        client.table.return_value.select.return_value.is_.assert_called_once_with(
            "deleted_at", "null"
        )
        client.table.return_value.select.return_value.is_.return_value.eq.return_value.order.return_value.range.assert_called_once_with(
            4, 8
        )

    def test_backend_error_is_sanitized(self):
        self.store.rows = Mock(side_effect=PersistenceError("SECRET"))
        result = self.get("seasons")
        self.assertEqual(result.status_code, 503)
        self.assertNotIn("SECRET", result.text)

    def test_sanctioned_points_use_exact_official_view_not_snapshot_score(self):
        self.store.data["public_sanctioned_points"] = [
            dict(
                season_id=SID,
                season_player_id=PID,
                earned_points="3",
                points_reduction="3.25",
                dead_points_penalty="0.2",
                sanctioned_points="-0.45",
                source_matchday_id=DAY,
            )
        ]
        result = self.get(f"seasons/{SID}/overview")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["points"][0]["sanctioned_points"], "-0.45")
        columns = next(
            c[1] for c in self.store.calls if c[0] == "public_sanctioned_points"
        )
        self.assertIn("sanctioned_points::text", columns)
        self.store.data["public_sanctioned_points"][0]["sanctioned_points"] = (
            "-12345678901234567890.12"
        )
        self.assertEqual(
            self.get(f"seasons/{SID}/overview").json()["points"][0][
                "sanctioned_points"
            ],
            "-12345678901234567890.12",
        )

    def test_pc_identity_requires_explicit_unambiguous_observation(self):
        entity = str(uuid4())
        self.store.data["pokemon_observations"] = [
            dict(
                season_id=SID,
                trainer_id=TRAINER_ID,
                save_file_id=SAVE,
                pokemon_entity_id=entity,
                source="party",
                box_number=0,
                slot_number=1,
                outcome="MATCHED",
                evidence="SECRET",
            )
        ]
        self.store.data["pokemon_entities"] = [
            dict(
                id=entity,
                season_id=SID,
                owner_trainer_id=TRAINER_ID,
                identity_status="unambiguous",
                initial_evidence="SECRET",
            )
        ]
        result = self.get(f"seasons/{SID}/pc")
        self.assertEqual(result.json()["pokemon"][0]["pokemon_entity_id"], entity)
        self.assertNotIn("SECRET", result.text)
        self.store.data["pokemon_entities"][0]["identity_status"] = "ambiguous"
        self.assertIsNone(
            self.get(f"seasons/{SID}/pc").json()["pokemon"][0]["pokemon_entity_id"]
        )

    def test_inventory_only_reads_rival_public_lock_and_never_rival_parsed_save(self):
        rival, rival_save, entity = [str(uuid4()) for _ in range(3)]
        self.store.data["team_locks"] = [
            dict(
                season_id=SID,
                matchday_id=DAY,
                trainer_id=rival,
                save_file_id=rival_save,
                public_team_snapshot=[dict(species="Eevee", ability="SECRET")],
                private_team_snapshot="SECRET",
            )
        ]
        self.store.data["pokemon_observations"] = [
            dict(
                season_id=SID,
                trainer_id=rival,
                save_file_id=rival_save,
                pokemon_entity_id=entity,
                source="party",
                box_number=0,
                slot_number=1,
                outcome="MATCHED",
                evidence="SECRET",
            )
        ]
        self.store.data["pokemon_entities"] = [
            dict(
                id=entity,
                season_id=SID,
                owner_trainer_id=rival,
                identity_status="unambiguous",
            )
        ]
        result = self.get(f"seasons/{SID}/inventory")
        self.assertEqual(result.status_code, 200)
        target = result.json()["targets"][0]
        self.assertEqual(target["pokemon_entity_id"], entity)
        self.assertEqual(target["visibility"], "public_team_lock")
        self.assertNotIn("SECRET", result.text)
        for table, columns, filters, *_ in self.store.calls:
            if table == "parsed_saves":
                self.assertEqual(filters["save_file_id"], SAVE)
            self.assertNotIn("evidence", columns)
            self.assertNotIn("private_team_snapshot", columns)

    def test_inventory_own_gift_visible_without_enabling_catalog_offer(self):
        item, owned, foreign = [str(uuid4()) for _ in range(3)]
        base = dict(
            season_id=SID,
            shop_item_id=item,
            status="pending",
            total_price=0,
            purchased_at="2026-09-28T12:00:00Z",
            metadata="SECRET",
        )
        self.store.data["purchases"] = [
            dict(base, id=owned, trainer_id=TRAINER_ID),
            dict(base, id=foreign, trainer_id=str(uuid4())),
        ]
        self.store.data["shop_items"] = [
            dict(id=item, code="robar_pokemon", name="Vale de robo", enabled=False)
        ]
        result = self.get(f"seasons/{SID}/inventory")
        self.assertEqual(result.status_code, 200)
        self.assertEqual([p["id"] for p in result.json()["purchases"]], [owned])
        self.assertEqual(result.json()["purchases"][0]["item_code"], "robar_pokemon")
        self.assertNotIn("SECRET", result.text)


class CorsTests(unittest.TestCase):
    def test_private_success_and_errors_are_not_cacheable(self):
        with TestClient(
            create_app(container=ApiContainer(), config=APIConfig())
        ) as client:
            self.assertEqual(
                client.get("/v1/read/seasons").headers["cache-control"], "no-store"
            )
            self.assertEqual(
                client.post("/v1/auth/pin-login", json={}).headers["cache-control"],
                "no-store",
            )

    def test_real_postgrest_transport_uses_filters_and_range(self):
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json=[])

        client = SyncPostgrestClient("https://example.invalid/rest/v1")
        client.session = httpx.Client(transport=httpx.MockTransport(respond))
        self.addCleanup(client.session.close)
        repo = SupabaseFrontendReadRepository(client)
        repo.rows(
            "save_files",
            "id,parser_status",
            filters={"season_id": SID, "trainer_id": TRAINER_ID, "deleted_at": None},
            offset=5,
            limit=10,
        )
        self.assertEqual(len(requests), 1)
        request = requests[0]
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.url.params["trainer_id"], "eq." + TRAINER_ID)
        self.assertEqual(request.url.params["season_id"], "eq." + SID)
        self.assertEqual(request.url.params["deleted_at"], "is.null")
        self.assertEqual(request.url.params["offset"], "5")
        self.assertEqual(request.url.params["limit"], "10")

    def test_explicit_preflight_allows_jwt_and_idempotency(self):
        with TestClient(
            create_app(
                container=ApiContainer(),
                config=APIConfig(cors_origins=("https://pokeapp.example",)),
            )
        ) as client:
            headers = {
                "Origin": "https://pokeapp.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
            }
            result = client.options("/v1/admin/seasons", headers=headers)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(
                result.headers["access-control-allow-origin"], "https://pokeapp.example"
            )
            self.assertNotIn("access-control-allow-credentials", result.headers)
            self.assertEqual(
                client.get(
                    "/v1/read/seasons", headers={"Origin": headers["Origin"]}
                ).status_code,
                401,
            )
            headers["Origin"] = "https://attacker.example"
            result = client.options("/v1/admin/seasons", headers=headers)
            self.assertEqual(result.status_code, 400)
            self.assertNotIn("access-control-allow-origin", result.headers)

    def test_configuration_rejects_wildcards_paths_and_plaintext_remote(self):
        for origin in (
            "*",
            "https://*.example",
            "https://example/path",
            "http://example",
            "https://user:pass@example",
            "https://example?x=1",
        ):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                APIConfig(cors_origins=(origin,))
        self.assertEqual(
            APIConfig.from_env(
                {
                    "POKEAPP_API_CORS_ORIGINS": "http://localhost:5173, https://pokeapp.example"
                }
            ).cors_origins,
            ("http://localhost:5173", "https://pokeapp.example"),
        )
