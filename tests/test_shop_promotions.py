from __future__ import annotations

import random
import unittest

from app.tienda.catalog_data import get_catalog
from app.tienda.discounts import _discount_price, select_shop_promotions


class ShopPromotionTests(unittest.TestCase):
    def test_prices_and_mega_exclusions(self) -> None:
        selected = select_shop_promotions(
            get_catalog(),
            closed_round=3,
            purchase_counts={1: {}, 2: {}, 3: {}},
            discount_history=[],
            rng=random.Random(17),
        )

        summary: dict[tuple[str, str], int] = {}
        for item in selected:
            key = (str(item["category"]), str(item["discount_kind"]))
            summary[key] = summary.get(key, 0) + 1

        self.assertEqual(
            summary,
            {
                ("comodines", "normal"): 1,
                ("comodines", "mega"): 1,
                ("competitivos", "normal"): 4,
                ("competitivos", "mega"): 2,
                ("crianza", "normal"): 1,
                ("crianza", "mega"): 1,
            },
        )
        self.assertFalse(
            any(
                int(item["price"]) <= 4 and item["discount_kind"] == "mega"
                for item in selected
            )
        )
        self.assertFalse(
            any(
                item["name"] == "Objeto Evolutivo"
                and item["discount_kind"] == "mega"
                for item in selected
            )
        )
        self.assertEqual(_discount_price(15, "normal", item="Chapa Dorada"), 13)
        self.assertEqual(_discount_price(15, "mega", item="Chapa Dorada"), 10)
        self.assertEqual(_discount_price(12, "mega", item="Revivir Pokemon"), 8)

    def test_rotation_avoids_previous_round_when_possible(self) -> None:
        first = select_shop_promotions(
            get_catalog(),
            closed_round=2,
            purchase_counts={1: {}, 2: {}},
            discount_history=[],
            rng=random.Random(21),
        )
        history = [
            {"item": item["name"], "jornada": 2, "discount_kind": item["discount_kind"]}
            for item in first
        ]
        second = select_shop_promotions(
            get_catalog(),
            closed_round=3,
            purchase_counts={1: {}, 2: {}, 3: {}},
            discount_history=history,
            rng=random.Random(22),
        )

        self.assertTrue(
            {str(item["name"]) for item in first}.isdisjoint(
                {str(item["name"]) for item in second}
            )
        )

    def test_historical_purchases_are_excluded(self) -> None:
        selected = select_shop_promotions(
            get_catalog(),
            closed_round=3,
            purchase_counts={1: {}, 2: {}, 3: {}},
            discount_history=[],
            purchased_items={
                "Blindar Pokemon",
                "gemas elementales",
                "Menta de Naturaleza",
            },
            rng=random.Random(1),
        )

        selected_names = {str(item["name"]) for item in selected}
        self.assertNotIn("Blindar Pokemon", selected_names)
        self.assertNotIn("Gemas Elementales", selected_names)
        self.assertNotIn("Menta de Naturaleza", selected_names)


if __name__ == "__main__":
    unittest.main()
