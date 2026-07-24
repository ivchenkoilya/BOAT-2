from __future__ import annotations

import unittest
from pathlib import Path

from government_reality_v180_common import PLOTS
from government_reality_v182_common import (
    MOBILE_DISTRICTS,
    MOBILE_PLOTS,
    MOBILE_ROADS,
    MOBILE_WORLD,
    WIDE_PLOTS,
    layout_payload,
)
from government_reality_v182_map import enhance_map_state_v182

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class Reality182MapTests(unittest.TestCase):
    def test_mobile_layout_covers_every_existing_plot(self) -> None:
        expected = {str(item["plot_id"]) for item in PLOTS}
        self.assertEqual(expected, set(MOBILE_PLOTS))
        self.assertEqual(expected, set(WIDE_PLOTS))
        self.assertEqual(len(MOBILE_DISTRICTS), 5)
        self.assertGreater(MOBILE_WORLD["height"], MOBILE_WORLD["width"])
        self.assertGreaterEqual(len(MOBILE_ROADS), 5)

    def test_layout_payload_contains_mobile_and_wide_without_money(self) -> None:
        payload = layout_payload()
        self.assertEqual({"mobile", "wide"}, set(payload))
        self.assertIn("plots", payload["mobile"])
        self.assertIn("districts", payload["mobile"])
        self.assertNotIn("treasury", str(payload).lower())
        self.assertNotIn("balance", str(payload).lower())

    def test_state_enhancement_preserves_economy_and_adds_stages(self) -> None:
        base = {
            "objects": [{
                "plot_id": "ind-1", "project_id": "p1", "building_id": "",
                "status": "building", "progress": 61, "total_cost": 1_000_000,
                "funded_amount": 1_000_000,
            }],
            "districts": [{
                "key": "industrial", "x": 999, "y": 999, "width": 1, "height": 1,
                "objects": 1, "active": 0, "construction": 1, "problems": 0,
            }],
            "metrics": {"treasury": 7_000_000, "active": 0, "construction": 1},
        }
        result = enhance_map_state_v182(base, 55)
        self.assertEqual(result["metrics"]["treasury"], 7_000_000)
        self.assertEqual(result["objects"][0]["project_id"], "p1")
        self.assertEqual(result["objects"][0]["construction_stage"], "shell")
        self.assertEqual(result["objects"][0]["progress_label"], "61%")
        self.assertNotIn("x", result["districts"][0])
        self.assertNotIn("width", result["districts"][0])
        self.assertIn("mobile", result["layouts"])
        self.assertIn("wide", result["layouts"])

    def test_reality182_replaces_older_map_assets(self) -> None:
        source = read("government_reality_v182.py")
        self.assertIn("for version in (180, 181)", source)
        self.assertIn("reality-v182-map.js", source)
        self.assertIn("reality-v182-map.css", source)
        self.assertIn("enhance_map_state_v182", source)

    def test_client_has_cover_mode_fullscreen_and_working_controls(self) -> None:
        source = read("governmentapp_v127/reality-v182-map.js")
        for fragment in (
            "fitWorld('cover'", "fitWorld('contain'", "data-r182-close-fullscreen",
            "data-r182-district", "data-r182-filter", "data-r182-mini",
            "construction_stage", "selectedPlot", "requestAnimationFrame",
            "visualViewport", "load(true)", "if(animate)updateControls()",
        ):
            self.assertIn(fragment, source)
        self.assertNotIn("MutationObserver", source)
        self.assertNotIn("setInterval", source)

    def test_css_has_safe_area_distinct_buildings_and_no_black_dependency(self) -> None:
        source = read("governmentapp_v127/reality-v182-map.css")
        for fragment in (
            "--tg-content-safe-area-inset-top", ".r182-screen.r182-fullscreen",
            ".visual-factory", ".visual-hospital", ".visual-school",
            ".visual-bank", ".r182-road", ".r182-viewport:before",
            ".r182-object.selected", "prefers-reduced-motion",
        ):
            self.assertIn(fragment, source)

    def test_reality182_is_installed_after_reality181(self) -> None:
        source = read("talent_entry_v164.py")
        self.assertLess(
            source.index("install_government_reality_v181(core)"),
            source.index("install_government_reality_v182(core)"),
        )


if __name__ == "__main__":
    unittest.main()
