"""I public boundaries: exact money, observed facts and owner-only voucher targets."""

from dataclasses import asdict, replace
import unittest
from uuid import uuid4

from pydantic import ValidationError

from app.api.schemas import NormalPurchaseResponse
from app.api.season_admin_models import FunctionalRules
import test_api_frontend_reads as reads
import test_api_purchases as purchases
from test_api_frontend_reads import SID, TRAINER_ID
from test_phase10_5e_parser_progress import progress, save_with_progress


class EconomyReadTests(unittest.TestCase):
    setUp = reads.FrontendReadTests.setUp
    get = reads.FrontendReadTests.get

    def test_exact_large_and_negative_wallet_strings(self):
        for value in ("4294967294", "9007199254740993", "-9007199254740993", "0"):
            with self.subTest(value=value):
                self.store.data["public_coin_balances"] = [
                    dict(season_id=SID, trainer_id=TRAINER_ID, balance=value)
                ]
                result = self.get(f"seasons/{SID}/shop")
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.json()["balance"], value)

    def test_malformed_balance_never_becomes_zero_or_truncated(self):
        for value in (True, 1.5, "1.5", "1e20", "01", "NaN"):
            self.store.data["public_coin_balances"] = [
                dict(season_id=SID, trainer_id=TRAINER_ID, balance=value)
            ]
            self.assertEqual(self.get(f"seasons/{SID}/shop").status_code, 503)

    def test_post_league_read_uses_only_season_wide_promotions(self):
        for status in ("finished", "archived"):
            self.store.data["seasons"][0]["status"] = status
            result = self.get(f"seasons/{SID}/shop")
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["season_status"], status)
            calls = [c for c in self.store.calls if c[0] == "public_shop_promotions"]
            self.assertIsNone(calls[-1][2]["matchday_id"])

    def test_pending_projection_excludes_admin_metadata_and_uses_real_schedule(self):
        season = self.store.data["seasons"][0]
        self.store.data["public_shop_promotions"] = [
            dict(
                id=str(uuid4()),
                shop_item_id=str(uuid4()),
                season_id=SID,
                matchday_id=season["current_matchday_id"],
                status="pending",
                effective_price=3,
                stock_total=2,
                stock_used=0,
                activates_at=None,
                ends_at=None,
                metadata="SECRET",
            )
        ]
        result = self.get(f"seasons/{SID}/shop")
        self.assertEqual(result.status_code, 200)
        self.assertNotIn("SECRET", result.text)
        self.assertEqual(result.json()["promotions"][0]["status"], "pending")
        self.assertIsNone(result.json()["promotions"][0]["activates_at"])


class EconomyReceiptTests(unittest.TestCase):
    setUp = purchases.NormalPurchaseTests.setUp
    post = purchases.NormalPurchaseTests.post

    def test_post_league_receipt_nullable_window_and_exact_large_api_balance(self):
        self.receipt = replace(
            self.receipt,
            matchday_id=None,
            matchday_number=None,
            balance_after=9007199254740993,
        )
        # The HTTP mock uses the test's receipt object when it constructs the RPC response.
        self.rpc_body = asdict(self.receipt)
        value = NormalPurchaseResponse(**asdict(self.receipt)).model_dump(mode="json")
        self.assertEqual(value["balance_after"], "9007199254740993")
        self.assertIsNone(value["matchday_id"])
        self.assertIsNone(value["matchday_number"])
        with self.assertRaises(ValueError):
            replace(self.receipt, matchday_number=1)


class ObservedRewardContractTests(unittest.TestCase):
    def test_old_badges_and_eight_badges_do_not_imply_game_completion(self):
        self.assertIsNone(
            save_with_progress(progress(flags=[True] * 8)).progress.champion_defeated
        )
        for value in (False, True, None):
            self.assertIs(
                save_with_progress(
                    progress() | {"champion_defeated": value}
                ).progress.champion_defeated,
                value,
            )
        for invalid in (1, "true", {}, []):
            with self.subTest(value=invalid), self.assertRaises(ValidationError):
                save_with_progress(progress() | {"champion_defeated": invalid})

    def test_reward_defaults_and_configurable_integer_amounts(self):
        base = dict(team_lock_required=True, last_b_gets_steal=False)
        default = FunctionalRules(**base)
        self.assertEqual(
            (default.badge_reward_coins, default.game_completion_reward_coins), (4, 12)
        )
        for badge, completion in ((0, 0), (7, 20), (2147483647, 2147483647)):
            result = FunctionalRules(
                **base,
                badge_reward_coins=badge,
                game_completion_reward_coins=completion,
            )
            self.assertEqual(
                (result.badge_reward_coins, result.game_completion_reward_coins),
                (badge, completion),
            )
        for key in ("badge_reward_coins", "game_completion_reward_coins"):
            for invalid in (-1, True, 1.5, "4", 2147483648):
                with (
                    self.subTest(key=key, value=invalid),
                    self.assertRaises(ValidationError),
                ):
                    FunctionalRules(**base, **{key: invalid})
