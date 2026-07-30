from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


class Reality1842Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.old_expansion = sys.modules.get("hero_expansion_v184")
        cls.old_live = sys.modules.get("hero_reality_v184_1")

        expansion = types.ModuleType("hero_expansion_v184")
        expansion.SHOP_ITEMS = [
            {"key": "custom_title", "price": 150_000},
            {"key": "chat_event", "price": 500_000},
            {"key": "unrelated", "price": 777},
        ]

        async def change_influence(*args, **kwargs):
            return {"balance": 100_000, "duplicate": False}

        async def purchase(*args, **kwargs):
            return {"ok": True}

        expansion.change_influence = change_influence
        expansion._purchase = purchase
        expansion._record_story = None

        live = types.ModuleType("hero_reality_v184_1")
        live._live_state = None
        live._authorized_user = None
        live._chat_id_from_request = None

        sys.modules["hero_expansion_v184"] = expansion
        sys.modules["hero_reality_v184_1"] = live

        module_path = Path(__file__).resolve().parents[1] / "hero_reality_v184_2.py"
        spec = importlib.util.spec_from_file_location("hero_reality_v184_2_tested", module_path)
        assert spec and spec.loader
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)
        cls.expansion = expansion

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.old_expansion is None:
            sys.modules.pop("hero_expansion_v184", None)
        else:
            sys.modules["hero_expansion_v184"] = cls.old_expansion
        if cls.old_live is None:
            sys.modules.pop("hero_reality_v184_1", None)
        else:
            sys.modules["hero_reality_v184_1"] = cls.old_live

    def test_existing_prices_are_halved(self) -> None:
        expected = {
            "custom_title": 75_000,
            "roast_member": 40_000,
            "extended_stats": 50_000,
            "profile_frame": 150_000,
            "sabotage_shield": 100_000,
            "mission_boost": 50_000,
            "chat_event": 250_000,
            "hide_losses": 125_000,
            "reroll_today_type": 60_000,
            "story_insurance": 200_000,
        }
        self.assertEqual(self.module.HALF_PRICE_MAP, expected)

    def test_catalog_contains_fourteen_new_items(self) -> None:
        self.assertGreaterEqual(len(self.module.COSMETIC_ITEMS), 14)
        self.assertIn("frame_crown", self.module.COSMETIC_ITEMS)
        self.assertIn("background_cosmos", self.module.COSMETIC_ITEMS)
        self.assertIn("badge_fire", self.module.COSMETIC_ITEMS)

    def test_new_items_have_valid_fields(self) -> None:
        allowed_categories = {"popular", "status", "defense", "chaos", "appearance"}
        allowed_rarities = {"common", "rare", "epic", "legendary"}
        for key, item in self.module.COSMETIC_ITEMS.items():
            self.assertTrue(key)
            self.assertGreater(int(item["price"]), 0)
            self.assertIn(item["category"], allowed_categories)
            self.assertIn(item["rarity"], allowed_rarities)
            self.assertIn(item["cosmetic_type"], {"badge", "name_style", "glow", "background", "frame"})

    def test_price_constants_only_change_known_items(self) -> None:
        self.module._apply_price_constants()
        rows = {item["key"]: item["price"] for item in self.expansion.SHOP_ITEMS}
        self.assertEqual(rows["custom_title"], 75_000)
        self.assertEqual(rows["chat_event"], 250_000)
        self.assertEqual(rows["unrelated"], 777)


if __name__ == "__main__":
    unittest.main()
