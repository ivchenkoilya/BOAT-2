from __future__ import annotations

import unittest
from pathlib import Path

from government_reality_v180_common import PLOTS
from government_reality_v181_common import (
    BUILDING_VISUALS,
    DISTRICT_BOUNDS,
    FILTERS,
    PLOT_LAYOUT,
    ROAD_PATHS,
    WORLD_HEIGHT,
    WORLD_WIDTH,
)
from government_reality_v181_map import enhance_map_state


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class Reality181MapTests(unittest.TestCase):
    def test_new_layout_covers_every_reality180_plot(self) -> None:
        self.assertEqual({str(item["plot_id"]) for item in PLOTS}, set(PLOT_LAYOUT))
        self.assertEqual(len(PLOT_LAYOUT), 30)
        self.assertTrue(all(0 < x < WORLD_WIDTH and 0 < y < WORLD_HEIGHT for x, y in PLOT_LAYOUT.values()))
        self.assertEqual(len(DISTRICT_BOUNDS), 5)
        self.assertGreaterEqual(len(ROAD_PATHS), 5)

    def test_every_building_has_compact_visual(self) -> None:
        expected = {
            "factory", "power_plant", "school", "hospital", "housing",
            "police", "culture_house", "science", "state_bank", "administration",
        }
        self.assertEqual(expected, set(BUILDING_VISUALS))
        self.assertTrue(all(item["short"] and item["class"] and item["symbol"] for item in BUILDING_VISUALS.values()))

    def test_enhancement_preserves_canonical_ids_and_money(self) -> None:
        base = {
            "objects": [{
                "plot_id": "ind-1", "project_id": "project-1", "building_id": "",
                "building_key": "factory", "district": "industrial", "status": "building",
                "maintenance_debt": 0, "total_cost": 1_000_000, "funded_amount": 1_000_000,
            }],
            "landmarks": [],
            "metrics": {"treasury": 9_000_000},
            "active_programs": [],
        }
        result = enhance_map_state(base, 123)
        item = result["objects"][0]
        self.assertEqual(item["project_id"], "project-1")
        self.assertEqual(item["total_cost"], 1_000_000)
        self.assertEqual(result["metrics"]["treasury"], 9_000_000)
        self.assertEqual((item["x"], item["y"]), PLOT_LAYOUT["ind-1"])
        self.assertTrue(item["is_construction"])

    def test_filters_cover_required_modes(self) -> None:
        self.assertEqual(
            {"all", "construction", "active", "problems", "institutions"},
            {item["key"] for item in FILTERS},
        )

    def test_reality181_replaces_old_map_assets(self) -> None:
        source = read("government_reality_v181.py")
        self.assertIn("reality-v180-map\\.css", source)
        self.assertIn("reality-v180-map\\.js", source)
        self.assertIn("reality-v181-map.js", source)
        self.assertIn("reality-v181-map.css", source)
        self.assertIn("enhance_map_state", source)

    def test_client_has_fullscreen_working_districts_and_filters(self) -> None:
        source = read("governmentapp_v127/reality-v181-map.js")
        for fragment in (
            "data-r181-fullscreen", "focusDistrict", "fitBounds", "data-r181-filter",
            "r181Minimap", "data-r181-contribute", "data-r181-fund",
            "data-r181-pay-debt", "requestAnimationFrame", "load(true)", "fitCurrent(false)",
        ):
            self.assertIn(fragment, source)
        self.assertNotIn("MutationObserver", source)
        self.assertNotIn("setInterval", source)

    def test_mobile_css_has_safe_fullscreen_and_bottom_sheet(self) -> None:
        source = read("governmentapp_v127/reality-v181-map.css")
        self.assertIn(".r181-screen.r181-fullscreen", source)
        self.assertIn("env(safe-area-inset-top)", source)
        self.assertIn("env(safe-area-inset-bottom)", source)
        self.assertIn(".r181-sheet", source)
        self.assertIn(".r181-minimap", source)
        self.assertIn("prefers-reduced-motion", source)

    def test_reality181_is_installed_after_reality180(self) -> None:
        source = read("talent_entry_v164.py")
        self.assertLess(
            source.index("install_government_reality_v180(core)"),
            source.index("install_government_reality_v181(core)"),
        )


if __name__ == "__main__":
    unittest.main()
