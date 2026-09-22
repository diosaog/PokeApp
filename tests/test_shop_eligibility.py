from copy import deepcopy
import unittest
from unittest.mock import Mock
from uuid import uuid4

from app.domain.shop_eligibility import legacy_store_ban_window, resolve_current_matchday, store_ban_applies
from app.repositories.supabase.shop_eligibility import SupabaseShopEligibilityRepository
from app.repositories.errors import PersistenceError


class ShopEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.case = dict(id="case", season_id="season", accused_trainer_id="trainer", status="resolved")
        self.penalty = dict(trial_case_id="case", season_id="season", trainer_id="trainer", penalty_type="store_ban",
                            start_matchday_number=3, end_matchday_number=4)

    def banned(self, number=3, **changes):
        return store_ban_applies({**self.penalty, **changes}, self.case, season_id="season", trainer_id="trainer",
                                 current_matchday_number=number)

    def test_sb01_no_penalty(self):
        self.assertFalse(store_ban_applies({}, None, season_id="season", trainer_id="trainer", current_matchday_number=3))

    def test_sb02_other_trainer_or_season(self):
        self.assertFalse(self.banned(trainer_id="other"))
        self.assertFalse(self.banned(season_id="other"))

    def test_sb03_only_resolved_case(self):
        for state in ("open", "dismissed", "cancelled", "finished"):
            self.case["status"] = state
            self.assertFalse(self.banned())

    def test_sb04_before_window(self):
        self.assertFalse(self.banned(2))

    def test_sb05_first_boundary(self):
        self.assertTrue(self.banned(3))

    def test_sb06_last_boundary(self):
        self.assertTrue(self.banned(4))

    def test_sb07_after_window(self):
        self.assertFalse(self.banned(5))

    def test_sb08_no_window(self):
        self.assertTrue(self.banned(99, start_matchday_number=None, end_matchday_number=None))

    def test_sb09_partial_window_matches_legacy(self):
        from app.juicios.penalties import _store_ban_active_now
        for raw in ({}, {"start_tramo": 3}, {"end_tramo": 4}, {"start_tramo": 0, "end_tramo": 4},
                    {"start_tramo": "invalid", "end_tramo": 4}, {"start_tramo": 3, "end_tramo": 4}):
            start, end = legacy_store_ban_window(raw)
            for number in (2, 3, 4, 5):
                self.assertEqual(self.banned(number, start_matchday_number=start, end_matchday_number=end),
                                 _store_ban_active_now(raw, number))

    def test_sb10_unrelated_type(self):
        self.assertFalse(self.banned(penalty_type="coins_reduction"))

    def test_sb11_resolved_timestamp_not_expiry(self):
        self.assertTrue(self.banned(resolved_at="2020-01-01T00:00:00Z"))

    def test_sb12_wrong_season_and_wrong_pointer(self):
        for day in (dict(id="day", season_id="other", number=3, status="open"),
                    dict(id="other", season_id="season", number=3, status="open")):
            with self.assertRaises(ValueError):
                resolve_current_matchday(dict(id="season", current_matchday_id="day"), day)

    def test_sb13_no_heuristic_when_pointer_missing(self):
        with self.assertRaisesRegex(ValueError, "current_matchday_required"):
            resolve_current_matchday(dict(id="season", current_matchday_id=None),
                                     dict(id="day", season_id="season", number=1, status="open"))

    def test_sb14_cancelled_rejected_scheduled_open_closed_preserved(self):
        for status in ("scheduled", "open", "closed"):
            result = resolve_current_matchday(dict(id="season", current_matchday_id="day"),
                dict(id="day", season_id="season", number=4, status=status))
            self.assertEqual(result.number, 4)
        with self.assertRaises(ValueError):
            resolve_current_matchday(dict(id="season", current_matchday_id="day"),
                dict(id="day", season_id="season", number=4, status="cancelled"))

    def test_case_identity_and_scope(self):
        for key, value in (("id", "other"), ("accused_trainer_id", "other"), ("season_id", "other")):
            original = deepcopy(self.case)
            self.case[key] = value
            self.assertFalse(self.banned())
            self.case = original
        self.case["season_id"] = None
        self.assertTrue(self.banned())

    def test_repository_calls_backend_helpers_and_validates_receipts(self):
        client = Mock()
        repo = SupabaseShopEligibilityRepository(client)
        season, trainer = str(uuid4()), str(uuid4())
        client.rpc.return_value.execute.return_value.data = True
        self.assertTrue(repo.is_store_banned(season, trainer, 3))
        client.rpc.assert_called_with("api_is_store_banned", dict(p_season_id=season, p_trainer_id=trainer, p_matchday_number=3))
        client.rpc.return_value.execute.return_value.data = [dict(id=str(uuid4()), season_id=season, number=3, status="scheduled")]
        self.assertEqual(repo.resolve_current_matchday(season).number, 3)
        client.rpc.return_value.execute.return_value.data = []
        with self.assertRaises(PersistenceError):
            repo.resolve_current_matchday(season)
        with self.assertRaises(PersistenceError):
            repo.is_store_banned(season, trainer, 3)


if __name__ == "__main__":
    unittest.main()
