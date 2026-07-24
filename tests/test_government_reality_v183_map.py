from __future__ import annotations

import unittest
from pathlib import Path

from government_reality_v183_common import CLIENT_BUILD, DISTRICT_BUILDINGS, development_tier
from government_reality_v183_map import enhance_map_state_v183

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class Reality183MapTests(unittest.TestCase):
    def test_state_preserves_economy_and_adds_live_city_data(self) -> None:
        base = {
            "metrics": {"treasury": 4_500_000, "development": 64},
            "objects": [{"plot_id": "ind-1", "district": "industrial"}],
            "empty_plots": [{"plot_id": "ind-2", "district": "industrial"}],
            "active_programs": [{"key": "festival", "title": "Фестиваль", "district": "culture"}],
        }
        construction = {
            "can_propose": True,
            "catalog": [{
                "key": "factory", "emoji": "🏭", "title": "Завод", "effect": "Доход",
                "cost": 1_000_000, "duration": 3600, "count": 1, "available": True,
                "sources": [{"key": "state_treasury", "title": "Казна", "balance": 4_500_000}],
            }],
        }
        result = enhance_map_state_v183(base, construction)
        self.assertEqual(result["metrics"]["treasury"], 4_500_000)
        self.assertEqual(result["map_client_version"], CLIENT_BUILD)
        self.assertEqual(result["development"]["level"], 4)
        self.assertEqual(result["empty_plots"][0]["building_keys"], list(DISTRICT_BUILDINGS["industrial"]))
        self.assertEqual(result["program_events"][0]["event_class"], "festival")
        self.assertTrue(result["can_propose"])

    def test_development_tiers_are_bounded(self) -> None:
        self.assertEqual(development_tier(0)["level"], 1)
        self.assertEqual(development_tier(100)["level"], 5)

    def test_integration_replaces_all_old_map_assets_and_serves_sprite(self) -> None:
        source = read("government_reality_v183.py")
        self.assertIn("for version in (180, 181, 182)", source)
        self.assertIn("reality-v183-map-20260724.js", source)
        self.assertIn("reality-v183-map-20260724.css", source)
        self.assertIn("reality-v183-buildings-20260724.svg", source)
        self.assertIn("map_client_version", read("government_reality_v183_map.py"))

    def test_client_has_compact_controls_empty_plots_events_and_initial_fit(self) -> None:
        source = read("governmentapp_v127/reality-v183-map-20260724.js")
        for fragment in (
            "data-r183-district-menu", "data-r183-empty", "data-r183-event",
            "construction_propose", "program_events", "developmentDecor",
            "fitWorld('contain'", "miniVisible=false", "MAP ${esc(data.map_client_version",
            "reality-v183-buildings-20260724.svg", "requestAnimationFrame",
        ):
            self.assertIn(fragment, source)
        self.assertNotIn("Объектов с выбранным фильтром нет", source)
        self.assertNotIn("MutationObserver", source)
        self.assertNotIn("setInterval", source)

    def test_svg_has_distinct_building_symbols(self) -> None:
        source = read("governmentapp_v127/reality-v183-buildings-20260724.svg")
        for symbol in (
            "factory", "power_plant", "school", "hospital", "housing", "police",
            "culture_house", "science", "state_bank", "administration",
            "presidency", "duma", "finance", "court", "oversight",
            "construction_plan", "construction_foundation",
        ):
            self.assertIn(f'id="{symbol}"', source)

    def test_css_has_lighter_city_safe_fullscreen_and_collapsed_minimap(self) -> None:
        source = read("governmentapp_v127/reality-v183-map-20260724.css")
        for fragment in (
            ".r183-screen.r183-fullscreen", "--tg-content-safe-area-inset-top",
            ".r183-empty-plot", ".r183-event", ".r183-sprite",
            ".road-access", ".dev-tier-5", ".r183-minimap.hidden",
            "prefers-reduced-motion",
        ):
            self.assertIn(fragment, source)

    def test_reality183_is_installed_after_reality182(self) -> None:
        source = read("talent_entry_v164.py")
        self.assertLess(
            source.index("install_government_reality_v182(core)"),
            source.index("install_government_reality_v183(core)"),
        )


if __name__ == "__main__":
    unittest.main()
